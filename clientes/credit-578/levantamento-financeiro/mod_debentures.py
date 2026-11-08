"""Levantamento documental e contábil das debêntures, sem presumir integralização.

As contas reduzidas das importações não são o plano de contas da ECD.
Valores são processados em Decimal; a conversão para float ocorre só na saída.
"""
from __future__ import annotations

import calendar
import hashlib
import json
import re
import subprocess
import unicodedata
import zipfile
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from xml.etree import ElementTree

D = Decimal
ZERO = D('0')
CENT = D('.01')
YEARS = [str(x) for x in range(2022, 2027)]
MONEY = r'\d[\d.]*,\d{2}'


def money(s):
    return D(str(s).strip().replace('.', '').replace(',', '.'))


def num(x):
    return None if x is None else float(x.quantize(CENT, rounding=ROUND_HALF_UP))


def brl(x):
    if x is None:
        return 'PENDENTE'
    v = f'{abs(x):,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    return f'R$ ({v})' if x < 0 else f'R$ {v}'


def normal(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if not unicodedata.combining(c)).upper()


def pdf_text(p):
    return subprocess.check_output(['pdftotext', '-layout', str(p), '-']).decode('utf-8')


def docx_text(p):
    ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
    with zipfile.ZipFile(p) as z:
        root = ElementTree.fromstring(z.read('word/document.xml'))
        return '\n'.join(''.join(t.text or '' for t in e.iter(ns + 't')) for e in root.iter(ns + 'p'))


def debt_position(t):
    for line in t.splitlines():
        if re.match(r'\s*642\s+2\.1\.7', line):
            vals = re.findall(MONEY, line)
            if len(vals) >= 4:
                return tuple(money(v) for v in vals[-4:])
    raise ValueError('Conta 642 / 2.1.7 não localizada no balancete')


def parse_ecd(p):
    entries = []
    current = None
    balances = []
    period = None
    account_names = {}
    for no, line in enumerate(p.read_bytes().decode('latin-1').splitlines(), 1):
        a = line.split('|')
        if len(a) < 2:
            continue
        if a[1] == 'I050':
            account_names[a[6]] = a[8]
        elif a[1] == 'I150':
            period = a[2]
        elif a[1] == 'I155' and a[2] == '642':
            balances.append((period, a, no))
        elif a[1] == 'I200':
            current = {'id': a[2], 'date': a[3], 'lines': [], 'line': no}
            entries.append(current)
        elif a[1] == 'I250' and current is not None:
            current['lines'].append(a)
    return entries, balances, account_names


def extract_export(p):
    """Uma linha por fato de interesse, preservando repetições legítimas no arquivo."""
    events, c_estorno, pending = [], set(), []
    for no, line in enumerate(p.read_bytes().decode('latin-1').splitlines(), 1):
        a = line.split('|')
        if len(a) < 8 or a[1] != '6100':
            continue
        h = normal(a[7])
        if 'DEB' not in h or 'NTUR' not in h:
            continue
        m = re.fullmatch(r'(\d{2})/(\d{2})/(\d{2}|\d{4})', a[2])
        if not m:
            continue
        dd, mm, yy = m.groups()
        yy = yy if len(yy) == 4 else '20' + yy
        date = f'{dd}/{mm}/{yy}'
        v = money(a[5])
        typ = 'ESTORNO' if 'ESTORN' in h else 'INTEGRALIZACAO' if 'INTEGRAL' in h else 'IRRF' if 'IRRF' in h else 'RENDIMENTO' if 'RENDIMENTO' in h else 'OUTROS'
        ev = {'date': date, 'ym': f'{yy}-{mm}', 'type': typ, 'value': v,
              'debit': a[3], 'credit': a[4], 'history': a[7], 'line': no}
        if typ == 'ESTORNO':
            if a[4] == '369':
                events.append(ev)
                c_estorno.add((date, v))
            elif a[3]:
                pending.append(ev)
        elif typ == 'RENDIMENTO':
            if a[3] == '369':
                events.append(ev)
        elif a[3]:
            events.append(ev)
    events += [e for e in pending if (e['date'], e['value']) not in c_estorno]
    return events


def annual_ledger(base, out):
    """Classifica a conta 642 nos razões anuais, sem presumir caixa em lotes de saldos.

    O lote só resolve partidas compostas quando contém exclusivamente bancos e
    debêntures e fecha exatamente. Lotes de implantação nunca viram captação.
    """
    from mod_razoes import load
    data = load(base, out)
    annual, detail, monthly, checks, evidence = {}, [], defaultdict(lambda: defaultdict(lambda: ZERO)), [], []
    for year, parsed in sorted(data['years'].items()):
        events = parsed['events']
        by_lot = defaultdict(list)
        names = {e['codigo_conta']: e['nome_conta'] for e in events}
        classes = {e['codigo_conta']: e['classificacao'] for e in events}
        for e in events:
            by_lot[(e['data'], e['lote'])].append(e)
        stats = {k: ZERO for k in ('capital', 'capitalized', 'prior_interest', 'transfer_debit', 'transfer_credit',
                                  'implantation', 'other', 'bank_payments', 'interest_paid_direct', 'debit', 'credit')}
        source = parsed.get('source', f'balancetes/Razão{year}.xls')
        if isinstance(source, dict):
            source = source['source']
        def location(e):
            return f'{source} | {e["aba"]}!linha {e["linha"]}; lote {e["lote"]}; conta {e["codigo_conta"]}'
        for e in events:
            if e['codigo_conta'] != '642':
                continue
            debit, credit = D(e['debito_centavos']) / 100, D(e['credito_centavos']) / 100
            change = credit - debit
            stats['debit'] += debit
            stats['credit'] += credit
            lot = by_lot[(e['data'], e['lote'])]
            own = [q for q in lot if q['codigo_conta'] == '642']
            others = [q for q in lot if q['codigo_conta'] != '642']
            cp = e.get('contrapartida_codigo')
            history = normal(e['historico'])
            own_d = sum(q['debito_centavos'] for q in own)
            own_c = sum(q['credito_centavos'] for q in own)
            transfer = (len(own) > 1 and own_d == own_c and own_d > 0 and not others
                        and all('TRANSFERENCIA ENTRE CONTAS' in normal(q['historico']) for q in own))
            cash_others = [q for q in others if q['classificacao'].startswith('1.1.1.')]
            compound_cash = (others and len(cash_others) == len(others)
                             and sum(q['debito_centavos'] - q['credito_centavos'] for q in cash_others) == own_c-own_d
                             and (own_d == 0 or own_c == 0))
            linked = [q for q in lot if q is not e and (not cp or q['codigo_conta'] == cp)]
            if 'SALDO FINAL' in history or 'IMPLANTACAO' in history:
                kind = 'Implantação/ajuste de saldo; composição econômica pendente'
                stats['implantation'] += change
                # Centenas de contas podem compartilhar esse lote. Não são
                # contrapartidas atribuíveis individualmente à debênture.
                linked = []
            elif transfer:
                kind = 'Transferência entre contas sem efeito no consolidado e sem caixa'
                stats['transfer_debit'] += debit
                stats['transfer_credit'] += credit
            elif cp == '369':
                kind = 'Juros do período incorporados à dívida'
                stats['capitalized'] += change
                monthly[e['data'][:7]]['interest'] += change
            elif cp and classes.get(cp, '').startswith('2.4.') and 'JUROS' in history:
                kind = 'Juros reconhecidos contra ajustes de exercícios anteriores'
                stats['prior_interest'] += change
            elif (cp and classes.get(cp, '').startswith('1.1.1.')) or compound_cash:
                if change >= 0:
                    kind = 'Captação bancária identificada; série/titular a vincular'
                    stats['capital'] += change
                    monthly[e['data'][:7]]['capital'] += change
                else:
                    kind = 'Pagamento bancário de debêntures; principal/juros a distinguir'
                    stats['bank_payments'] -= change
            else:
                kind = 'Movimento com natureza pendente'
                stats['other'] += change
            cp_text = (cp + ' ' + names.get(cp, '')) if cp else ('Partida composta banco/debêntures fechada' if compound_cash else 'Sem contrapartida individual informada')
            linked_source = '; '.join(location(q) for q in linked) if linked else ''
            row = [year, e['data'], e['lote'], kind, num(debit), num(credit), num(change), cp_text,
                   e['historico'], location(e) + ('; vínculos: ' + linked_source if linked_source else ''), '642 / 2.1.7.01.01']
            detail.append(row)
            if cp != '369':
                evidence.append(row)
        # Procura juros pagos fora da própria conta 642. Encerramento para 473
        # não é pagamento e não entra nesta medida.
        for e in events:
            if e['codigo_conta'] != '369':
                continue
            cp = e.get('contrapartida_codigo')
            if cp and classes.get(cp, '').startswith('1.1.1.'):
                stats['interest_paid_direct'] += D(e['debito_centavos'] - e['credito_centavos']) / 100
                evidence.append([year, e['data'], e['lote'], 'Juros pagos diretamente por banco',
                                 e['debito_centavos']/100, e['credito_centavos']/100, 0.0,
                                 cp+' '+names.get(cp, ''), e['historico'], location(e), '369 / '+e['classificacao']])
        sections = [s for s in parsed['sections'] if s['codigo_conta'] == '642']
        stats['opening'] = -sum((D(s['saldo_anterior_fonte']['saldo_centavos'])/100 for s in sections), ZERO)
        stats['closing'] = stats['opening'] + stats['credit'] - stats['debit']
        stats['source'] = source
        annual[year] = stats
    return annual, detail, monthly, evidence


def build(base: Path, out: Path):
    from mod_contabilidade import parse_balancete
    base, out = Path(base), Path(out)
    official = base / 'publicacao-balancos/DOCUMENTOS CREDIT'
    docs = base / 'publicacao-balancos/outras informações'
    rel = lambda p: str(p.relative_to(base))
    sheets, checks, pending, report = [], [], [], []
    texts = {}
    positions, interest, sources = {}, {}, {}
    for y in YEARS:
        p = base / 'balancetes/Balancete-ja-set-2026.pdf' if y == '2026' else official / f'BALANCETE CREDIT {y}.pdf'
        t = texts.setdefault(p, pdf_text(p))
        positions[y] = debt_position(t)
        if y == '2026':
            lines = [line for line in t.splitlines() if 'JUROS DEBENTURES' in normal(line) and re.findall(MONEY, line)]
            if len(lines) != 1:
                raise ValueError('Conta 369 ambígua em 2026')
            vals = re.findall(MONEY, lines[0])
            interest[y] = money(vals[-1])
        else:
            dp = official / f'DRE CREDIT {y}.pdf'
            dt = texts.setdefault(dp, pdf_text(dp))
            lines = [line for line in dt.splitlines() if 'JUROS DEBENTURES' in normal(line)]
            interest[y] = money(re.findall(MONEY, lines[0])[0]) if lines else ZERO
        codes={a['code']:a for a in parse_balancete(p)}
        sources[y] = rel(p) + ' | 642 / '+codes['642']['classification']+'; ' + (rel(official / f'DRE CREDIT {y}.pdf') if y != '2026' else rel(p)) + ' | 369 / '+codes.get('369',{}).get('classification','3.2.2.05.001')

    # Fontes de importação: hash elimina cópias idênticas; por mês escolhe o arquivo
    # com maior cobertura de fatos de debêntures, como no gerador legado do cliente.
    groups = defaultdict(list)
    for p in sorted(base.rglob('CONTABIL_DOMINIO*.TXT')):
        groups[hashlib.sha256(p.read_bytes()).hexdigest()].append(p)
    candidates = defaultdict(list)
    duplicates = []
    for sha, paths in groups.items():
        paths.sort(key=lambda p: ('fiscal' in p.parts, len(str(p)), str(p)))
        p = paths[0]
        for q in paths:
            duplicates.append([rel(q), sha, rel(p), 'REPRESENTANTE' if q == p else 'DUPLICATA EXCLUÍDA', 'Conteúdo binário idêntico; namespace de contas da importação'])
        ev = extract_export(p)
        for ym in sorted({e['ym'] for e in ev}):
            if ym <= '2026-09':
                rows = [e for e in ev if e['ym'] == ym]
                candidates[ym].append((len(rows), rel(p), rows))
    monthly_exports = {}
    for ym, options in sorted(candidates.items()):
        options.sort(key=lambda x: (-x[0], x[1]))
        _, source, ev = options[0]
        totals = defaultdict(lambda: ZERO)
        for e in ev:
            totals[e['type']] += e['value']
        monthly_exports[ym] = {'source': source, 'events': ev, 'totals': totals}
    sheets.append({'name': 'Deb_Hashes', 'headers': ['Arquivo', 'SHA256', 'Representante', 'Tratamento', 'Observação'], 'rows': duplicates})

    # ECD 2025 prevalece sobre importações e históricos textuais imprecisos.
    ep = base / 'fiscal/dominio/sped_diario00578.txt'
    entries, ecd_balances, account_names = parse_ecd(ep)
    ecd_month = defaultdict(lambda: defaultdict(lambda: ZERO))
    ecd_detail, capitalization = [], ZERO
    for en in entries:
        debt_lines = [a for a in en['lines'] if a[2] == '642']
        if not debt_lines:
            continue
        ym = en['date'][4:] + '-' + en['date'][2:4]
        others = [a for a in en['lines'] if a[2] != '642']
        for a in debt_lines:
            v = money(a[4])
            sign = 1 if a[5] == 'C' else -1
            if any(q[2] == '369' for q in others):
                nature = 'Juros capitalizados (líquidos de ajustes contábeis)'
                ecd_month[ym]['interest'] += sign * v
                capitalization += sign * v
            elif all(q[2] in ('8', '15') for q in others) and sign == 1:
                nature = 'Captação identificada em banco conciliado; vincular o lançamento à série e ao titular'
                ecd_month[ym]['capital'] += v
            else:
                nature = 'PENDENTE - natureza da movimentação'
                ecd_month[ym]['other'] += sign * v
            ecd_month[ym]['credit' if sign == 1 else 'debit'] += v
            ecd_detail.append([en['date'][:2] + '/' + en['date'][2:4] + '/' + en['date'][4:], en['id'], nature,
                               num(v) if sign == 1 else -num(v), ', '.join(q[2] + ' ' + account_names.get(q[2], '') for q in others),
                               a[8], rel(ep) + f' | I200 {en["id"]}; I250 linha {en["line"]}', 'ECD 642 / 2.1.7.01.01'])
    capt_2025 = sum((m['capital'] for m in ecd_month.values()), ZERO)
    debit_2025 = sum((m['debit'] for m in ecd_month.values()), ZERO)
    ledger, ledger_detail, ledger_month, key_events = annual_ledger(base, out)
    detail_headers = ['Ano', 'Data', 'Lote', 'Natureza', 'Débito R$', 'Crédito R$', 'Variação da dívida R$',
                      'Contrapartida / método', 'Histórico original', 'Fonte e vínculos', 'Conta']
    sheets.append({'name': 'Deb_Movimentos', 'headers': detail_headers, 'rows': ledger_detail})
    sheets.append({'name': 'Deb_Eventos_chave', 'headers': detail_headers, 'rows': key_events})
    for year in YEARS:
        for measure, idx in [('opening', 0), ('debit', 1), ('credit', 2), ('closing', 3)]:
            value, ref = ledger[year][measure], positions[year][idx]
            checks.append({'teste': 'Debêntures razão anual × balancete: '+measure, 'ano': year,
                           'calculado': num(value), 'referencia': num(ref), 'diferenca': num(value-ref),
                           'status': 'OK' if value == ref else 'DIVERGENTE',
                           'fonte': ledger[year]['source']+'; '+sources[year]})
    checks.append({'teste': 'Captação razão anual 2025 × ECD', 'ano': '2025', 'calculado': num(ledger['2025']['capital']),
                   'referencia': num(capt_2025), 'diferenca': num(ledger['2025']['capital']-capt_2025),
                   'status': 'OK' if ledger['2025']['capital'] == capt_2025 else 'DIVERGENTE',
                   'fonte': ledger['2025']['source']+'; '+rel(ep)+'; fontes comparadas, não somadas'})
    mrows = []
    for ym in sorted(set(ledger_month) | set(monthly_exports)):
        em = ledger_month.get(ym)
        ex = monthly_exports.get(ym)
        bt = ex['totals'] if ex else None
        gross = bt['RENDIMENTO'] if bt is not None else None
        rev = bt['ESTORNO'] if bt is not None else None
        net = gross - rev if bt is not None else None
        source = (ledger[ym[:4]]['source'] + ' | 642/369; Deb_Movimentos' if em else '') + ('; ' + ex['source'] + ' | importação D369-C369; IRRF por histórico' if ex else '')
        mrows.append([ym, num(em['interest']) if em else None, num(em['capital']) if em else None,
                      num(gross), num(rev), num(net), num(bt['IRRF']) if bt is not None else None,
                      num(bt['INTEGRALIZACAO']) if bt is not None else None, source,
                      'Razão anual é a fonte da movimentação; ECD/importações são conferência, não somar fontes. IRRF não equivale a juros pagos.'])
        if em and net is not None:
            delta = em['interest'] - net
            checks.append({'teste': 'Juros razão anual × importação deduplicada', 'ano': ym, 'calculado': num(em['interest']), 'referencia': num(net), 'diferenca': num(delta), 'status': 'OK' if abs(delta) < CENT else 'DIVERGENTE', 'fonte': source})
    sheets.append({'name': 'Deb_Mensal', 'headers': ['Mês', 'Juros incorporados razão R$', 'Captação razão R$', 'Rendimento bruto importado R$', 'Estorno importado R$', 'Juros líquidos importados R$', 'DARF IRRF com referência a debêntures R$', 'Integralização importada R$', 'Fonte e conta', 'Critério'], 'rows': mrows})

    # Inventário de títulos: certificado não é prova de depósito nem saldo aberto.
    title_rows, holder_nominal, cert_totals = [], defaultdict(lambda: ZERO), defaultdict(lambda: ZERO)
    cert_qty = defaultdict(int)
    for p in sorted(docs.glob('*.pdf')):
        if not any(w in p.name for w in ('SERIE', 'FRL300')):
            continue
        t = texts.setdefault(p, pdf_text(p))
        flat = ' '.join(t.split())
        qty_match = re.search(r'Este Certificado representativo de\s+(\d+)', flat)
        series_match = re.search(r'da\s+(\d+)º\s*S[ÉE]RIE', flat)
        if not qty_match or not series_match:
            raise ValueError('Certificado sem quantidade/série: ' + str(p))
        qty, serie = int(qty_match[1]), int(series_match[1])
        unit = money(re.search(r'valor unitário de R\$\s*(' + MONEY + ')', flat)[1])
        holder = re.search(r'confere a\s+(.+?),\s*CPF', flat)[1].strip()
        date = re.search(r'Porto Alegre/RS,\s+(.+?)\.', flat)[1]
        value = qty * unit
        caveat = 'DOCUMENTAL; integralização e saldo por titular PENDENTES'
        if p.name == 'FRL300 (5).pdf':
            caveat = 'PENDENTE - potencial sobreposição das cautelas 1 e 2 de Lair (mesmo titular, série e 700 títulos); cautela 1 excluída provisoriamente do subtotal até esclarecer substituição ou cancelamento'
        else:
            holder_nominal[holder] += value
            cert_totals[serie] += value
            cert_qty[serie] += qty
        title_rows.append([serie, holder, date, qty, num(unit), num(value), 'Certificado / cautela',
                           'PENDENTE', 'PENDENTE', 'PENDENTE', caveat, rel(p), '2.1.7 (sem desdobramento contábil por titular)'])
    bulletin_total, bulletin_qty, bulletin_declared_total = ZERO, 0, ZERO
    for p in sorted(docs.glob('*.docx')):
        if 'Boletim' not in p.name:
            continue
        t = docx_text(p)
        flat = ' '.join(t.split())
        serie = int(re.search(r'da\s+(\d+)ª', flat)[1])
        # O corpo prevalece sobre o nome errado de um dos arquivos.
        qty = int(re.search(r'representado por\s+(\d+)', flat)[1])
        unit = money(re.search(r'valor nominal unitário de R\$\s*(' + MONEY + ')', flat)[1])
        holder = re.search(r'(AFFONSO BERNARDO HÜNING|ARTHUR GERMANO HÜNING|GUSTAVO MATIAS HÜNING|Jane Hartmann Hüning)', flat)[1].upper()
        date = re.search(r'Porto Alegre/RS,\s+([^_]+?)(?:\s{2}|\n|$)', t)
        value = qty * unit
        holder_nominal[holder] += value
        bulletin_total += value
        bulletin_qty += qty
        declares=('IMPORTANCIA REALIZADA' in normal(flat) and 'A VISTA' in normal(flat) and 'NA DATA DA SUBSCRICAO' in normal(flat))
        if declares:bulletin_declared_total+=value
        warning = 'Integralização declarada no quadro Importância Realizada, à vista em 11/11/2024; vincular aos lançamentos e ao titular'
        if p.name.startswith('2023'):
            warning += '; nome do arquivo 2023 diverge do corpo: 5ª série e 11/11/2024'
        if 'Gustavo' in p.name:
            warning += '; texto contém 5ª (Quarta), inconsistência ordinal'
        title_rows.append([serie, holder, '11 de novembro de 2024 (corpo do boletim)', qty, num(unit), num(value), 'Boletim de subscrição', '120% do CDI (3º aditamento)', 'PENDENTE', 'PENDENTE', warning, rel(p), '2.1.7 (sem vínculo titular/importação)'])

    second = base / 'entrada/2024 08 29 Segundo Aditamento Escritura de Emissao  Credit Saint Germain  vf Registrado (JUCISRS).pdf'
    third = docs / '2024 11 05  Terceiro Adto a Escritura de Emissao  Credit Saint Germain vf Registrada (JUCISRS).pdf'
    st, tt = pdf_text(second), pdf_text(third)
    for t in (st, tt):
        if not re.search(r'120%\s+do CDI', t):
            raise ValueError('Índice contratual não confirmado no aditamento')
    q4 = int(re.search(r'Foram emitidas\s+(\d+)', st)[1])
    q5 = int(re.search(r'Foram emitidas\s+(\d+)', tt)[1])
    # Unitário confirmado em certificados e boletins da mesma emissão; a escritura
    # original é necessária para confirmação contratual transversal.
    title_rows.append([4, 'PENDENTE', '29/08/2024 (data do 2º aditamento)', q4, 1000.0, float(q4 * 1000), '2º aditamento registrado', '120% do CDI', 'Juros Mensais Devidos; periodicidade de desembolso PENDENTE', 'Até 60 meses; termo inicial e data final PENDENTES', 'Titular, boletim, integralização, carência e fórmula diária PENDENTES', rel(second) + ' | cláusulas 3.5.7, 3.12.5, 3.13.5 e 3.16.6', '2.1.7; nominal unitário dos certificados da 1ª emissão'])
    sheets.append({'name': 'Deb_Titulos', 'headers': ['Série', 'Titular', 'Data documental', 'Quantidade títulos', 'Valor unitário R$', 'Nominal documental R$', 'Documento', 'Remuneração', 'Periodicidade / carência', 'Vencimento', 'Status e ressalva', 'Fonte', 'Conta'], 'rows': title_rows})
    series_rows = []
    for serie in range(1, 6):
        qty = cert_qty[serie] if serie < 4 else q4 if serie == 4 else q5
        value = cert_totals[serie] if serie < 4 else D(q4 * 1000) if serie == 4 else D(q5 * 1000)
        source = '; '.join(r[11] for r in title_rows if r[0] == serie)
        if serie == 5:
            source += '; ' + rel(third) + ' | cláusulas 3.5.8, 3.12.6, 3.13.6 e 3.16.7'
        series_rows.append([serie, qty, num(value), num(bulletin_declared_total) if serie==5 else None, None, 'Ver Integralizações declaradas; vincular documentos ao saldo atual por titular',
                            '120% do CDI' if serie in (4, 5) else 'PENDENTE - escritura original / 1º aditamento',
                            'Até 60 meses; data final exata PENDENTE' if serie in (4, 5) else 'PENDENTE', source, '2.1.7'])
    sheets.append({'name': 'Deb_Series', 'headers': ['Série', 'Quantidade com exclusão provisória de sobreposição', 'Nominal com exclusão provisória R$', 'Integralização declarada nos boletins R$', 'Saldo devedor por série R$', 'Status', 'Remuneração contratual', 'Vencimento', 'Fonte', 'Conta'], 'rows': series_rows})
    holder_rows = [[h, num(v), None, 'Nominal documental; ver declarações de realização e vínculo aos lançamentos conciliados', '; '.join(r[11] for r in title_rows if r[1] == h), '2.1.7'] for h, v in sorted(holder_nominal.items())]
    holder_rows.append(['PENDENTE - titular da 4ª série', float(q4 * 1000), None, 'PENDENTE - nominal da série; titular e integralização não documentados', rel(second), '2.1.7'])
    sheets.append({'name': 'Deb_Titulares', 'headers': ['Titular', 'Nominal com exclusão provisória R$', 'Saldo atualizado individual R$', 'Status', 'Fonte', 'Conta'], 'rows': holder_rows})

    known_cap = {y: ledger[y]['capital'] for y in YEARS}
    capitalized = {y: ledger[y]['capitalized'] for y in YEARS}
    prior_interest = {y: ledger[y]['prior_interest'] for y in YEARS}
    implantations = {y: ledger[y]['implantation'] for y in YEARS}
    payments = {y: ledger[y]['bank_payments'] for y in YEARS}
    residual, annual_status = {}, {}
    for y in YEARS:
        initial, debits, credits, final = positions[y]
        calc = (initial + known_cap[y] + capitalized[y] + prior_interest[y] + implantations[y]
                + ledger[y]['transfer_credit'] - ledger[y]['transfer_debit'] - payments[y])
        residual[y] = final - calc
        annual_status[y] = ('DIVERGENTE' if residual[y] else
                            'EXPLICADO - implantação de saldo; composição econômica PENDENTE' if implantations[y] else
                            'OK - movimento contábil identificado')
        checks.append({'teste': 'Debêntures: ponte histórica com captação, juros, ajustes e transferências', 'ano': y,
                       'calculado': num(calc), 'referencia': num(final), 'diferenca': num(calc-final),
                       'status': annual_status[y], 'fonte': ledger[y]['source']+'; '+sources[y]})
        checks.append({'teste': 'Juros incorporados no razão × DRE do período', 'ano': y,
                       'calculado': num(capitalized[y]), 'referencia': num(interest[y]),
                       'diferenca': num(capitalized[y]-interest[y]),
                       'status': 'OK' if capitalized[y] == interest[y] else 'DIVERGENTE',
                       'fonte': ledger[y]['source']+' | 642/369; '+sources[y]})
    annual_rows = []
    def annual(label, values, accumulated=None, note=''):
        annual_rows.append([label] + [num(values[y]) for y in YEARS] + [num(accumulated), note, '; '.join(sources.values())+'; razões: '+'; '.join(ledger[y]['source'] for y in YEARS)])
    annual('Saldo inicial da dívida', {y: positions[y][0] for y in YEARS}, note='Estoque: acumulado não aplicável')
    annual('Captações identificadas nos lançamentos bancários conciliados', known_cap, sum(known_cap.values(), ZERO), 'Somente entradas bancárias vinculadas à dívida. Em 2024 o lançamento de saldo não permite abrir captação e demais componentes; zero identificado não prova ausência de captação no período implantado.')
    annual('Integralização declarada nos boletins localizados', {y:bulletin_declared_total if y=='2024' else None for y in YEARS}, bulletin_declared_total, '5ª série: quatro boletins com Importância Realizada em 11/11/2024. Não somar como entrada adicional à movimentação contábil; vincular lançamento e titular.')
    annual('Juros apropriados na DRE / grupo 3', interest, sum(interest.values(), ZERO), '369 / 3.2.2.05.001; 2022 sem linha de juros na DRE')
    annual('Juros do período incorporados à dívida', capitalized, sum(capitalized.values(), ZERO), 'Débitos em 369 contra créditos em 642; fonte única razão anual, ECD/importações apenas conferem.')
    annual('Juros contra ajustes de exercícios anteriores', prior_interest, sum(prior_interest.values(), ZERO), '2023: R$ 27.796,48 em 02/01, contra 657 / ajustes de exercícios anteriores. Não somar à DRE de 2023 nem presumir pagamento.')
    annual('Implantação/ajuste de saldo com composição econômica pendente', implantations, sum(implantations.values(), ZERO), '2024: R$ 343.213,30 em 31/12, lote 23308, SALDO FINAL EM 31/12/2024. Identificado contabilmente; não convertido em captação ou juros presumidos.')
    annual('Transferências internas - créditos na própria conta', {y:ledger[y]['transfer_credit'] for y in YEARS}, note='2023: lote 3432 de 02/01; crédito e débito de R$ 1 milhão se anulam no consolidado, sem caixa.')
    annual('Transferências internas - débitos na própria conta', {y:ledger[y]['transfer_debit'] for y in YEARS}, note='Mesma transferência acima; não é amortização. Não subtrair novamente da ponte líquida.')
    annual('Débitos totais registrados na conta da dívida', {y: positions[y][1] for y in YEARS}, sum((positions[y][1] for y in YEARS), ZERO), 'O único débito, R$ 1 milhão em 2023, é a transferência interna identificada, não saída bancária.')
    annual('Créditos totais registrados na conta da dívida', {y: positions[y][2] for y in YEARS}, sum((positions[y][2] for y in YEARS), ZERO), 'Movimentos brutos do balancete; não equivalem a captação')
    annual('Pagamentos bancários identificados contra a conta 642', payments, sum(payments.values(), ZERO), 'Nenhuma saída bancária identificada contra 642. A parcela de 2024 implantada em saldo não permite excluir pagamentos embutidos na sua composição.')
    annual('Juros pagos diretamente por banco contra 369', {y:ledger[y]['interest_paid_direct'] for y in YEARS}, note='Busca também fora da conta 642; encerramentos de resultado não são pagamento. Zero significa nenhum pagamento identificado no detalhamento disponível.')
    annual('Amortizações identificadas em saídas bancárias', {y:ZERO if not payments[y] else None for y in YEARS}, note='Transferência interna excluída. A composição do saldo implantado de 2024 permanece pendente; IRRF isolado não prova amortização.')
    annual('Residual da ponte contábil não explicado', residual, None, 'Implantação de 2024 apresentada separadamente, sem forçar sua classificação econômica. Não transformar residual em captação.')
    annual('Saldo final contábil', {y: positions[y][3] for y in YEARS}, note='Saldo em cada data; não somar os estoques')
    irr = {y: sum((v['totals']['IRRF'] for k, v in monthly_exports.items() if k[:4] == y), ZERO) if y in ('2025', '2026') else None for y in YEARS}
    annual('DARF IRRF com referência a debêntures (cobertura parcial)', irr, None, '2025 maio–dezembro; 2026 janeiro–setembro. Não é retenção por competência/titular confirmada; não adicionar ao saldo de debêntures.')
    annual('Estornos de rendimentos nas importações (cobertura parcial)', {y: sum((v['totals']['ESTORNO'] for k,v in monthly_exports.items() if k[:4] == y), ZERO) if y in ('2025','2026') else None for y in YEARS}, None, 'Estorno da despesa importada; juros acima já líquidos, não subtrair novamente')
    sheets.append({'name': '2_Debentures', 'headers': ['Movimento / medida', '2022', '2023', '2024', '2025', '2026 jan–set', 'Acumulado', 'Premissa / pendência', 'Fonte e conta'], 'rows': annual_rows})
    checks.append({'teste': 'Juros capitalizados ECD 2025 × DRE', 'ano': '2025', 'calculado': num(capitalization), 'referencia': num(interest['2025']), 'diferenca': num(capitalization-interest['2025']), 'status': 'OK' if capitalization == interest['2025'] else 'DIVERGENTE', 'fonte': rel(ep) + '; ' + sources['2025']})
    sum26 = sum((v['totals']['RENDIMENTO'] - v['totals']['ESTORNO'] for k,v in monthly_exports.items() if k.startswith('2026')), ZERO)
    checks.append({'teste': 'Aumento das debêntures × juros líquidos importados', 'ano': '2026 jan–set', 'calculado': num(positions['2026'][3]-positions['2026'][0]), 'referencia': num(sum26), 'diferenca': num(positions['2026'][3]-positions['2026'][0]-sum26), 'status': 'OK' if positions['2026'][3]-positions['2026'][0] == sum26 else 'DIVERGENTE', 'fonte': sources['2026'] + '; importações selecionadas em Deb_Mensal'})

    # Projeção agregada pedida, sem inventar vencimentos ou alocar principal.
    sep = monthly_exports['2026-09']['totals']['RENDIMENTO'] - monthly_exports['2026-09']['totals']['ESTORNO']
    sep_open = positions['2026'][3] - sep
    rate = sep / sep_open
    projection, balance = [], positions['2026'][3]
    for month_offset in range(1, 13):
        mindex = 2026 * 12 + 8 + month_offset
        yy, mi = divmod(mindex, 12)
        mm = mi + 1
        date = f'{calendar.monthrange(yy,mm)[1]:02d}/{mm:02d}/{yy}'
        charge = (balance * rate).quantize(CENT, rounding=ROUND_HALF_UP)
        closing = balance + charge
        projection.append([date, num(balance), float(rate), num(charge), num(closing), 'ESTIMADO - taxa efetiva mensal agregada de set/2026 mantida; sem captação, amortização ou juros pagos; não é cronograma contratual', sources['2026'] + '; ' + monthly_exports['2026-09']['source'] + ' | 369 importação; conta 2.1.7'])
        balance = closing
    sheets.append({'name': 'Deb_Projecao', 'headers': ['Data de referência (não é vencimento)', 'Saldo inicial estimado R$', 'Taxa mensal efetiva estimada', 'Juros estimados R$', 'Saldo final estimado R$', 'Premissa', 'Fonte e conta'], 'rows': projection, 'percent_columns': [2]})

    pending += [
        {'item': 'Escritura original de 06/10/2022, AGE de 22/09/2022 e 1º aditamento de 28/08/2023', 'motivo': 'Confirmar taxas das séries 1–3, fórmula CDI/dias úteis, periodicidade de pagamento, carência, datas de emissão e vencimentos de todas as séries. Certificados dizem subordinadas e aditamentos quirografárias.', 'fonte': rel(second) + '; ' + rel(third) + '; Deb_Titulos | 2.1.7'},
        {'item': 'Vínculo do controle de debenturistas e documentos históricos aos lançamentos por série e titular', 'motivo': 'Há documentos históricos e boletins com importância realizada. Falta vincular INTs e lançamentos a titular, série, principal e juros. As duas cautelas de Lair exigem resolução específica de substituição/cancelamento. A conciliação bancária foi confirmada pelo escritório.', 'fonte': 'publicacao-balancos/outras informações/ | 2.1.7'},
        {'item': 'Composição do saldo implantado de debêntures em 31/12/2024', 'motivo': 'O razão identifica R$ 343.213,30 no lote 23308 como SALDO FINAL EM 31/12/2024. Abrir os componentes econômicos do período substituído por saldo: captações, juros e eventuais pagamentos. Vincular os R$ 500 mil declarados nos boletins, sem somá-los como nova entrada. O débito de R$ 1 milhão de 2023 já foi esclarecido como transferência interna.', 'fonte': ledger['2024']['source']+' | conta 642, linha 13931; Deb_Eventos_chave'},
        {'item': 'Memória contratual de cálculo de juros, CDI diário e retenções/pagamentos por titular', 'motivo': 'Recálculo independente do contrato e diferenças PENDENTES: faltam fórmula integral, datas/base individual e série CDI. DARFs que citam amortização precisam comprovantes da operação com titular; sem prova não deduzir da dívida.', 'fonte': 'Deb_Mensal; Deb_Projecao | importações 369/1327 e históricos de IRRF; ECD 642/369'},
        {'item': 'Boletins assinados e emissão da 4ª série; confirmação do boletim Arthur e ordinal Gustavo da 5ª', 'motivo': '4ª série: titular não documentado. Arquivo Arthur nomeado 2023 contém 5ª série e 11/11/2024; Gustavo contém 5ª (Quarta). Confirmar datas de subscrição e pagamentos.', 'fonte': 'Deb_Titulos | publicacao-balancos/outras informações; 2.1.7'},
    ]
    nominal_total = sum((D(str(r[2])) for r in series_rows), ZERO)
    report.append({'title': '2. Debêntures: dívida contábil e documentação', 'paragraphs': [
        'O saldo contábil em 30/09/2026 é ' + brl(positions['2026'][3]) + '. O aumento de ' + brl(sum26) + ' em 2026 coincide com os juros líquidos importados e não há débito na conta 642: a dívida registrada cresce por capitalização. Fonte: ' + sources['2026'] + '; Deb_Mensal (exportações deduplicadas).',
        'Em 2025, a dívida passou de ' + brl(positions['2025'][0]) + ' para ' + brl(positions['2025'][3]) + ': ' + brl(known_cap['2025']) + ' de entradas bancárias e ' + brl(capitalized['2025']) + ' de juros incorporados, sem débito na conta da dívida. Os históricos de oito captações dizem rendimento, mas as contrapartidas são bancos; não são despesas de juros. O razão anual e a ECD conferem e são fontes alternativas, não valores adicionais. Fonte: '+ledger['2025']['source']+'; ' + rel(ep) + ', I200/I250, 642, 369, 8 e 15; Deb_Movimentos.',
        'O débito de R$ 1 milhão de 2023 foi esclarecido: em 02/01/2023, lote 3432, a conta 642 recebeu crédito e débito de R$ 1 milhão com histórico TRANSFERENCIA ENTRE CONTAS. O par se anula no consolidado e não envolve banco; não é amortização. A dívida de 2023 fecha com R$ 1 milhão inicial, R$ 750 mil de entradas bancárias, R$ 190.038,40 de juros do ano e R$ 27.796,48 de juros contra ajustes de exercícios anteriores (conta 657). Fonte: '+ledger['2023']['source']+' | linhas 6409–6414, lotes 3432 e 3633–3636; captações 2908, 3399 e 2916; Deb_Eventos_chave.',
        'Os juros apropriados nas DREs desde 2022 somam ' + brl(sum(interest.values(), ZERO)) + ' e os razões identificam esse mesmo valor incorporado à dívida. Outros R$ 27.796,48 foram reconhecidos em 2023 contra ajustes de exercícios anteriores, fora da DRE daquele ano. Não há saída bancária identificada contra 642 nem pagamento direto de juros por banco contra 369. A composição do saldo implantado em 2024 e o vínculo por titular ainda limitam a conclusão de que todos os juros históricos permanecem em aberto. Fonte: razões anuais, 642/369/657; DRE CREDIT 2022–2025.pdf; balancete set/2026.',
        'As séries documentadas são 1ª a 5ª. O nominal documental, retirando a possível sobreposição das duas cautelas de Lair na 1ª série, é ' + brl(nominal_total) + '; representa títulos e boletins, não captação comprovada nem saldo atual. Séries 4ª e 5ª preveem 120% do CDI, subscrição em até 20 meses e vencimento em até 60 meses. O termo inicial exato e a alocação individual precisam da escritura completa. Fonte: Deb_Titulos / Deb_Series; 2º aditamento cláusulas 3.5.7, 3.12.5, 3.13.5 e 3.16.6; 3º aditamento 3.5.8, 3.12.6, 3.13.6 e 3.16.7; conta 2.1.7.',
        'Há inconsistências relevantes: certificados dizem espécie subordinada e aditamentos quirografária; duas cautelas de Lair trazem os mesmos 700 títulos da 1ª série; um boletim Arthur nomeado 2023 contém 5ª série e novembro de 2024. A 2ª série contém duas cautelas Arthur distintas (250 e 25), mantidas no inventário. Fonte: Deb_Titulos, respectivos arquivos; conta 2.1.7.',
        'Em 2024, o razão identifica R$ 168.630,81 de juros contra 369 e R$ 343.213,30 em 31/12/2024, lote 23308, histórico SALDO FINAL EM 31/12/2024. Essa segunda parcela é implantação/ajuste de saldo, compartilhando lote com numerosas contas; não pode ser tratada como captação nem vinculada a um banco específico do lote. A ponte contábil fecha, mas a composição econômica dessa parcela ainda precisa de abertura para reconciliar os boletins realizados de R$ 500 mil e eventuais outros movimentos. Fonte: '+ledger['2024']['source']+' | conta 642, linha 13931; Deb_Eventos_chave; boletins da 5ª série.',
        'DARFs de IRRF citam amortização, mas não demonstram pagamento ao debenturista nem redução de 2.1.7. O controle de IRRF por competência/titular é PENDENTE. Não se confundem os códigos reduzidos da ECD com os códigos das importações. Fonte: Deb_Mensal, históricos das exportações e ECD I050/I250.',
        'O cronograma contratual por série/titular, principal separado de juros e recálculo independente pelo CDI permanecem PENDENTES. A aba Deb_Projecao mostra apenas uma projeção agregada ESTIMADA: taxa de setembro dividida pelo saldo de abertura de setembro, sem entradas ou pagamentos e sem representar vencimento. Fonte: balancete set/2026, 2.1.7 / 642; exportação de setembro, D369 / C1327.'
    ]})
    result = {'sheets': sheets, 'metrics': {'debt_balances': {y: num(positions[y][3]) for y in YEARS},
        'debt_interest': {y: num(interest[y]) for y in YEARS}, 'interest_total': num(sum(interest.values(), ZERO)),
        'capital_inflow_2025': num(capt_2025), 'capitalized_interest_2025': num(capitalization),
        'capitalized_interest_2026': num(sum26), 'unexplained_net_movement': {y:num(residual[y]) for y in YEARS},
        'capital_inflow_by_year': {y:num(known_cap[y]) for y in YEARS},
        'capital_inflow_identified_total': num(sum(known_cap.values(), ZERO)),
        'capitalized_interest_by_year': {y:num(capitalized[y]) for y in YEARS},
        'prior_period_interest_by_year': {y:num(prior_interest[y]) for y in YEARS},
        'balance_implantation_by_year': {y:num(implantations[y]) for y in YEARS},
        'bank_payments_by_year': {y:num(payments[y]) for y in YEARS},
        'interest_paid_direct_by_year': {y:num(ledger[y]['interest_paid_direct']) for y in YEARS},
        'internal_transfer_debit_by_year': {y:num(ledger[y]['transfer_debit']) for y in YEARS},
        'internal_transfer_credit_by_year': {y:num(ledger[y]['transfer_credit']) for y in YEARS},
        'economic_composition_pending': {y:num(implantations[y]+ledger[y]['other']) for y in YEARS},
        'annual_ledger_status': annual_status,
        'nominal_documental': num(nominal_total), 'nominal_documental_bruto': num(sum((D(str(r[5])) for r in title_rows),ZERO)), 'integralizacao_declarada_2024':num(bulletin_declared_total), 'principal_current': None, 'contractual_adjustment': None,
        'last_monthly_effective_rate': float(rate), 'estimated_12m_balance': num(balance),
        'monthly_irrf': {ym:num(v['totals']['IRRF']) for ym,v in monthly_exports.items()},
        'source_2026': sources['2026']}, 'checks': checks, 'pendencias': pending, 'report': report}
    out.mkdir(parents=True, exist_ok=True)
    (out / 'debentures_dados.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    directory = Path(__file__).resolve().parent
    result = build(directory.parent, directory)
    print(json.dumps(result['metrics'], ensure_ascii=False, indent=2))
