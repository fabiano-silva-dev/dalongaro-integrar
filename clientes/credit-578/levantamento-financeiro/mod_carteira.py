"""Carteira CSG: documentos de aquisição e calendário contratual, sem aging presumido.

Os XLSX são somente lidos. As parcelas não conciliadas com baixas permanecem de
situação desconhecida; ausência de baixa NÃO significa inadimplência.
"""
from __future__ import annotations

import calendar
import csv
import io
import hashlib
import re
import subprocess
import unicodedata
import zipfile
from collections import defaultdict, Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from openpyxl import load_workbook


def norm(x):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(x or '')) if not unicodedata.combining(c)).upper().strip()


def money(x):
    if x is None or x == '':
        return None
    if isinstance(x, str):
        x = x.replace('R$', '').replace(' ', '')
        if ',' in x:
            x = x.replace('.', '').replace(',', '.')
    return Decimal(str(x)).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)


def val(x):
    return float(x) if x is not None else None


def br(x):
    if x is None:
        return 'PENDENTE'
    s = f'{abs(x):,.2f}'.replace(',','X').replace('.',',').replace('X','.')
    return '(' + s + ')' if x < 0 else s


def dt(x):
    if isinstance(x, datetime):
        return x.date()
    if isinstance(x, date):
        return x
    if not x:
        return None
    for fmt in ('%d/%m/%Y', '%Y-%m-%d'):
        try:
            return datetime.strptime(str(x), fmt).date()
        except ValueError:
            pass
    return None


def iso(x):
    return x.isoformat() if x else None


def cpf(x):
    return re.sub(r'\D', '', str(x or ''))


def read_rows(p):
    w = load_workbook(p, read_only=True, data_only=True)
    s = w.active
    rows = list(s.values)
    w.close()
    return rows


def pdf_text(p):
    return subprocess.check_output(['/usr/bin/pdftotext', '-layout', str(p), '-'], stderr=subprocess.DEVNULL).decode('utf-8', errors='replace')


def find(pattern, text, flags=re.I):
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else None


def parse_ccb(p, text=None):
    t = text if text is not None else pdf_text(p)
    # Fields are extracted from the contractual Quadro II, not from historical
    # natural-language references later in the document.
    start = t.find('CARACTERÍSTICAS DA OPERAÇÃO')
    quadro = t[start:] if start >= 0 else t
    if not quadro:
        quadro = t
    q = quadro[:quadro.find('QUADRO III')] if 'QUADRO III' in quadro else quadro[:6500]
    ident = find(r'C[ÉE]DULA DE CR[ÉE]DITO BANC[ÁA]RIO\s+N[º°o.]\s*([\w/-]+)', t)
    n = find(r'N[úu]mero de Parcelas\s*:\s*(\d+)', q)
    endorsement_start = t.find('TERMO DE ENDOSSO')
    endorsement = t[endorsement_start:] if endorsement_start >= 0 else ''
    return {'kind': 'CCB', 'doc': ident, 'name': find(r'Nome\s*:\s*([^\n]+?)(?:\s*\(["“]?EMITENTE|\s*$)', t, re.I | re.M),
            'cpf': cpf(find(r'CPF\s*:\s*([\d.\-/]+)', t)),
            'city': find(r'Cidade\s*:\s*(.+?)\s+UF\s*:', t),
            'credit': money(find(r'Valor do Cr[ée]dito\s*:\s*R\$\s*([\d.,]+)', q)),
            'delivered': money(find(r'Valor Entregue ao Emitente\s*:\s*R\$\s*([\d.,]+)', q)),
            'installment': money(find(r'Valor da Parcela\s*:\s*R\$\s*([\d.,]+)', q)),
            'n': int(n) if n else None,
            'first': dt(find(r'Vencimento da Primeira Parcela\s*:\s*(\d{2}/\d{2}/\d{4})', q)),
            'last': dt(find(r'Vencimento da [ÚUu]ltima Parcela\s*:\s*(\d{2}/\d{2}/\d{4})', q)),
            'face': money(find(r'Valor Total das Parcelas\s*:\s*R\$\s*([\d.,]+)', q)),
            'release': dt(find(r'Data de libera[çc][ãa]o do recurso\s*:\s*(\d{2}/\d{2}/\d{4})', q)),
            'acquisition_date': dt(find(r'Data de Aquisi[çc][ãa]o\s*:\s*(\d{2}/\d{2}/\d{4})', endorsement)),
            'acquisition_price': money(find(r'Pre[çc]o de Aquisi[çc][ãa]o\s*:\s*R\$\s*([\d.,]+)', endorsement)),
            'endorsement_face': money(find(r'Valor de Face do T[íi]tulo\s*:\s*R\$\s*([\d.,]+)', endorsement)),
            'csg_cnpj': bool(re.search(r'46\.?788\.?467\s*/?\s*0001\s*-?\s*49', t)),
            'via_cnpj': bool(re.search(r'48\.?632\.?754\s*/?\s*0001\s*-?\s*90', t)),
            'source': p}


def add_months(d, n):
    m = d.month - 1 + n
    y = d.year + m // 12
    m = m % 12 + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def parse_recebivel(p, text=None):
    t = text if text is not None else pdf_text(p)
    declaration = find(r'Declara[çc][ãa]o de Recebimento\s+N[ºo.]\s*([\w/-]+)', t)
    origin = find(r'ORIGINADORA\s*:\s*([^\n]+)', t)
    origin_cpf = cpf(find(r'CNPJ/CPF\s*:\s*([\d.\-/]+)', t))
    # The original master agreement's date is NOT the acquisition date.
    # Only the acquisition register, when found, supplies that field.
    acquisition = money(find(r'Valor l[íi]quido\s+R\$\s*([\d.,]+)', t))
    face = money(find(r'Total do Border[ôo]\s+R\$\s*([\d.,]+)', t))
    discount = money(find(r'\(-\) Des[áa]gio\s+R\$\s*([\d.,]+)', t))
    installments = []
    start = t.find('Nome do DEVEDOR')
    end = t.find('As condições da declaração')
    table = t[start:end] if start >= 0 and end > start else ''
    for line in table.splitlines():
        m = re.match(r'^\s*(\S+)\s+(.+?)\s+(\d{2}/\d{2}/\d{4})\s+([\d.,]+)\s*$', line)
        if m:
            installments.append({'title': m[1], 'debtor': m[2].strip(), 'due': dt(m[3]), 'value': money(m[4])})
    return {'kind':'Recebível', 'doc': declaration, 'origin': origin, 'origin_cpf': origin_cpf, 'acquisition': acquisition,
            'face': face, 'discount': discount, 'installments': installments, 'source': p,
            'csg_cnpj': bool(re.search(r'46\.?788\.?467\s*/?\s*0001\s*-?\s*49', t))}


def parse_document(p):
    text = pdf_text(p)
    # The June/2026 Darciano document is named CCB but is a direct receivable.
    # Document content, rather than filename, determines the instrument type.
    if re.search(r'Declara[çc][ãa]o de Recebimento\s+N[ºo.]', text[:500]):
        return parse_recebivel(p, text)
    return parse_ccb(p, text)


def discover_monthly_sources(base):
    """Discover only customer-owned sources, with archived newer packages last."""
    found = [(p.name, p) for p in (base/'ccb').iterdir()
             if p.is_dir() and re.fullmatch(r'\d{4}-\d{2}', p.name)]
    archive = base/'_arquivo/zips'
    if archive.exists():
        for p in archive.rglob('relatorio_resumido*.xlsx'):
            m = re.search(r'(\d{4}-\d{2})', p.name)
            if m and '2022-06' <= m[1] <= '2026-09':
                found.append((m[1],p.parent))
    return sorted(set(found),key=lambda z:(z[0], '_arquivo' in z[1].parts, str(z[1])))


def inspect_archive_sources(base):
    """Record what was actually inspected; acquisition PDFs are not payment logs."""
    rows, open_position_candidates = [], []
    archive = base/'_arquivo'
    for p in sorted(archive.rglob('*.zip')):
        with zipfile.ZipFile(p) as z:
            names = [n for n in z.namelist() if not n.endswith('/')]
            table_names = [n for n in names if n.lower().endswith(('.xlsx','.xlsm','.xls','.csv'))]
            if 'CCB CLIENT' in p.name.upper():
                note = 'Pacote de contratos/aquisições; nomes dos arquivos inspecionados. Não é posição de parcelas pagas/abertas.'
                if '10.2026' in p.name:
                    note += ' Outubro/2026 fora da data-base de 30/09; não somado.'
            elif p.name == 'ConjuntoDeDados.zip':
                note = 'XML de leiaute Domínio para Clientes/Fornecedores, não registro de carteira/baixas.'
            elif table_names:
                note = 'Modelo fiscal/importação; não é posição de carteira.'
            else:
                note = 'Inventário de nomes e extensões; sem arquivo de posição aberta identificado.'
            rows.append([str(p.relative_to(base)),len(names),len([n for n in names if n.lower().endswith('.pdf')]),'; '.join(table_names) or 'Nenhuma planilha no ZIP',note])
    for p in sorted(archive.rglob('*.xlsx')):
        records = read_rows(p)
        header = ' | '.join(str(x or '') for x in records[0]) if records else ''
        normalized = norm(header)
        is_open = any(key in normalized for key in ['SALDO EM ABERTO','VALOR EM ABERTO','SITUACAO DA PARCELA','PARCELAS PAGAS','DATA DE PAGAMENTO','DATA DA BAIXA'])
        if is_open:
            open_position_candidates.append(str(p.relative_to(base)))
        rows.append([str(p.relative_to(base)),max(0,len(records)-1),0,header,'Possível posição/baixa: processamento específico necessário' if is_open else 'Cabeçalho de aquisição/fiscal/divergências; não é posição aberta/paga'])
    return rows, open_position_candidates


def parse_balance(p):
    """Use fixed position of the four monetary columns, preserving D/C sign."""
    # Share the main accounting reader, which avoids duplicated display text
    # in some Domínio PDFs. The fallback keeps this module independently usable.
    try:
        from mod_contabilidade import parse_balancete
        return [{'code': x['code'], 'account': x['classification'],
                 'name': x['description'], 'initial': x['opening'],
                 'debit': x['debit'], 'credit': x['credit'], 'balance': x['balance']}
                for x in parse_balancete(p)]
    except ImportError:
        pass
    t = pdf_text(p)
    rows = []
    amount = re.compile(r'\d[\d.]*,\d{2}[DC]?')
    for line in t.splitlines():
        m = re.search(r'\b(\d+)\s+(1(?:\.\d+)+)\s+', line)
        if not m:
            continue
        vals = list(amount.finditer(line[m.end():]))
        if len(vals) < 4:
            continue
        vals = vals[-4:]
        desc = line[m.end():m.end() + vals[0].start()].strip()
        amounts = []
        for x in vals:
            z = x.group()
            sign = -1 if z.endswith('C') else 1
            amounts.append(money(z.rstrip('DC')) * sign)
        rows.append({'code': m[1], 'account': m[2], 'name': desc, 'initial': amounts[0],
                     'debit': amounts[1], 'credit': amounts[2], 'balance': amounts[3]})
    return rows


def build(base: Path, out: Path):
    sheets, checks, pendencias, reports = [], [], [], []
    rel = lambda p: str(p.relative_to(base))
    inventory, summaries, fiscal, incoming = [], {}, {}, {}
    exceptions, dedup_rows, validation_rows = [], [], []
    monthly = discover_monthly_sources(base)
    coverage_start, coverage_end = monthly[0][0], monthly[-1][0]
    months_new = [m for m,p in monthly if '_arquivo' in p.parts and m >= '2026-06']
    month_stats = {}
    for month_key, month in monthly:
        p = month / f'relatorio_resumido{month_key}.xlsx'
        if not p.exists():
            p = base / 'saida' / p.name
        if p.exists():
            rr = read_rows(p)
            inventory.append([rel(p), 'Resumo de aquisições CCB', month_key, len(rr)-1, 'Não é posição de parcelas abertas; pacotes de _arquivo têm prioridade sobre cópias anteriores', '1.1.2'])
            for rownum, r in enumerate(rr[1:], 2):
                if not r[0]:
                    exceptions.append(['Linha sem documento no resumo', f'{rel(p)}:linha {rownum}', 'Não somada como CCB; PDFs são classificados pelo conteúdo para recuperar recebíveis diretos'])
                    continue
                doc = str(r[0])
                if doc in summaries:
                    old = summaries[doc]
                    same = (old['name'],old['date'],old['cost'],old['discount'],old['n']) == (str(r[1]),dt(r[2]),money(r[3]),money(r[4]),int(r[5]))
                    dedup_rows.append(['Resumo por contrato', doc, f'{rel(p)}:linha {rownum}', old['source'], 'Idêntico' if same else 'Dados diferentes: prevalece pacote mais recente', 'Não somado novamente'])
                summaries[doc] = {'doc': doc, 'name': str(r[1]), 'date': dt(r[2]), 'cost': money(r[3]),
                                  'discount': money(r[4]), 'n': int(r[5]), 'source': f'{rel(p)}:linha {rownum}', 'month': month_key}
        p = month / f'relatorio_fiscal{month_key}.xlsx'
        if not p.exists():
            p = base / 'saida' / p.name
        if not p.exists() and month_key == '2025-04':
            p = base / 'saida/relatorio_fiscal.xlsx'
        if p.exists():
            rr = read_rows(p)
            inventory.append([rel(p), 'Cadastro/valor de face fiscal', month_key, len(rr)-1, 'Cadastro histórico, não estoque atual', '1.1.2'])
            for rownum, r in enumerate(rr[1:], 2):
                if len(r) > 13 and r[5]:
                    fiscal[str(r[5])] = {'cpf': cpf(r[0]), 'city': str(r[3] or ''), 'name': str(r[1]), 'face': money(r[13]), 'source': f'{rel(p)}:linha {rownum}'}
        p = month / f'relatorio_fiscal_entradas_{month_key}.xlsx'
        if p.exists():
            rr = read_rows(p)
            inventory.append([rel(p), 'Compra junto à originadora', month_key, len(rr)-1, 'Custo de aquisição fiscal', '1.1.2'])
            for rownum, r in enumerate(rr[1:], 2):
                if r[5]:
                    incoming[str(r[5])] = {'origin': str(r[1]), 'cpf': cpf(r[0]), 'value': money(r[13]), 'date': dt(r[7]), 'source': f'{rel(p)}:linha {rownum}'}

    all_pdf_files = [p for _,folder in monthly for p in sorted(folder.glob('*.pdf'))]
    # Newer archive sources are retained when byte-identical copies exist.
    hashes = {}
    for p in all_pdf_files:
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        if digest in hashes:
            dedup_rows.append(['PDF por conteúdo SHA256',digest,rel(p),rel(hashes[digest]),'Idêntico','Não somado novamente'])
        hashes[digest] = p
    documents = list(ThreadPoolExecutor(max_workers=8).map(parse_document, hashes.values()))
    parsed = [p for p in documents if p['kind']=='CCB']
    rec_parsed = [p for p in documents if p['kind']=='Recebível']
    ccb_files = [p['source'] for p in parsed]
    pdfs = {}
    for p in parsed:
        if not p['doc']:
            exceptions.append(['PDF sem número extraível', rel(p['source']), 'Revisar leitura do PDF'])
        elif '_arquivo' in p['source'].parts and not p['csg_cnpj']:
            exceptions.append(['Vínculo CSG não validado no PDF', rel(p['source']), 'CNPJ da securitizadora não extraído; contrato do arquivo não integrado automaticamente'])
        elif p['doc'] in pdfs:
            previous = pdfs[p['doc']]
            same = all(p.get(k)==previous.get(k) for k in ['cpf','face','n','first','last','acquisition_price','acquisition_date'])
            dedup_rows.append(['CCB por contrato',p['doc'],rel(p['source']),rel(previous['source']),'Idêntico nos campos contratuais' if same else 'Versões diferentes; prevalece fonte posterior','Não somado novamente'])
            if not same:
                exceptions.append(['Versões diferentes da mesma CCB',p['doc'],f'Prevalece {rel(p["source"])}; anterior {rel(previous["source"])}; verificar divergências de termos'])
            pdfs[p['doc']] = p
        else:
            pdfs[p['doc']] = p
    for doc in list(summaries):
        s = summaries[doc]
        if s['source'].startswith('_arquivo/') and (doc not in pdfs or not pdfs[doc]['csg_cnpj']):
            exceptions.append(['Resumo de arquivo sem PDF CSG validado',doc,s['source']+'; não integrado à base de aquisições'])
            del summaries[doc]
        elif s['date'] and s['date'] > date(2026,9,30):
            exceptions.append(['Aquisição fora da data-base',doc,s['source']+'; data '+iso(s['date'])+' não integrada em 30/09/2026'])
            del summaries[doc]
    # A missing row in a generated summary does not make the original purchase
    # term unavailable. Recover documentary purchases from Quadro I of the
    # endorsement when all acquisition facts and the CSG identity are explicit.
    recovered_endorsements = []
    for doc,p in pdfs.items():
        if doc not in summaries and p['csg_cnpj'] and p.get('acquisition_price') is not None and p.get('acquisition_date') and p['acquisition_date'] <= date(2026,9,30) and p.get('face') is not None and p.get('n'):
            summaries[doc] = {'doc':doc,'name':p['name'],'date':p['acquisition_date'],'cost':p['acquisition_price'],'discount':p['face']-p['acquisition_price'],'n':p['n'],'source':rel(p['source'])+' | TERMO DE ENDOSSO, Quadro I','month':p['acquisition_date'].strftime('%Y-%m')}
            recovered_endorsements.append(doc)
    for month_key in sorted({x[0] for x in monthly}):
        month_values = [s for s in summaries.values() if s['month']==month_key]
        month_stats[month_key] = {'contratos':len(month_values),'custo':val(sum((s['cost'] for s in month_values),Decimal(0))),'desagio':val(sum((s['discount'] for s in month_values),Decimal(0))),'face':val(sum((s['cost']+s['discount'] for s in month_values),Decimal(0)))}
    for p in documents:
        origin_ok = p.get('via_cnpj') if p['kind']=='CCB' else bool(p.get('origin_cpf'))
        status = 'CSG CNPJ validado' if p['csg_cnpj'] else 'CNPJ CSG não localizado no texto'
        validation_rows.append([p['kind'],p.get('doc'),rel(p['source']),p['csg_cnpj'],origin_ok,p.get('origin_cpf') or ('48632754000190' if p.get('via_cnpj') else None),status,'1.1.2'])
    inventory.append(['ccb/AAAA-MM/*.pdf; _arquivo/zips/CCB CLIENTES MM.AAAA-*/*/*.pdf', 'Contratos classificados pelo conteúdo e deduplicados', f'{coverage_start} a {coverage_end}', len(all_pdf_files), f'{len(pdfs)} números CCB únicos; calendário não informa pagamento; vínculo dos novos PDFs validado pelo CNPJ CSG', '1.1.2'])

    # relatorio_operacoes is an auxiliary extraction of Apr/2025 PDFs. It is
    # never summed with the authoritative contracts (would double count them).
    opsp = base / 'saida/relatorio_operacoes.xlsx'
    ops = read_rows(opsp)
    inventory.append([rel(opsp), 'Extração auxiliar das CCBs', '2025-04', len(ops)-1, 'Conferida com PDFs; não somada novamente', '1.1.2'])
    ops_check_rows = []
    for i, r in enumerate(ops[1:], 2):
        matches = [p for p in parsed if p['source'].name == str(r[14]) and p['source'].parent.name == '2025-04']
        if len(matches) == 1:
            p = matches[0]
            diff = (p['face'] or Decimal(0)) - (money(r[13]) or Decimal(0))
            ops_check_rows.append([str(r[0]), p['doc'], val(money(r[13])), val(p['face']), val(diff), 'OK' if diff == 0 else 'DIVERGENTE', f'{rel(opsp)}:linha {i}; {rel(p["source"])}', '1.1.2'])
        else:
            ops_check_rows.append([str(r[0]), None, val(money(r[13])), None, None, 'PENDENTE - vínculo por arquivo', f'{rel(opsp)}:linha {i}', '1.1.2'])

    contract_rows, installments = [], []
    year_totals = defaultdict(lambda: {'n': 0, 'cost': Decimal(0), 'discount': Decimal(0), 'face': Decimal(0)})
    endorsement_totals = defaultdict(lambda: {'n':0,'price':Decimal(0),'difference':Decimal(0),'discount':Decimal(0)})
    city_totals, origin_totals = defaultdict(lambda: [0, Decimal(0), Decimal(0)]), defaultdict(lambda: [0, Decimal(0), Decimal(0)])
    price_diffs = []
    for doc, s in sorted(summaries.items(), key=lambda z: (iso(z[1]['date']) or '', z[0])):
        p, f, inc = pdfs.get(doc, {}), fiscal.get(doc, {}), incoming.get(doc, {})
        face = s['cost'] + s['discount']
        source = '; '.join(x for x in [s['source'], f.get('source'), inc.get('source'), rel(p['source']) if p else None] if x)
        city = f.get('city') or p.get('city') or 'PENDENTE'
        person = f.get('cpf') or p.get('cpf') or None
        origin = inc.get('origin') or ('VIA CAPITAL - SCD' if p else 'PENDENTE')
        status = 'Calendário contratual; situação de cobrança PENDENTE'
        contract_rows.append(['CCB', doc, s['name'], person, iso(s['date']), val(s['cost']), val(face), val(s['discount']), s['n'], val(p.get('installment')), iso(p.get('first')), iso(p.get('last')), origin, city, status, source, '1.1.2'])
        y = str(s['date'].year) if s['date'] else 'PENDENTE'
        if p.get('acquisition_price') is not None:
            endorsement_totals[y]['n'] += 1
            endorsement_totals[y]['price'] += p['acquisition_price']
            endorsement_totals[y]['difference'] += p['acquisition_price']-s['cost']
            endorsement_totals[y]['discount'] += face-p['acquisition_price']
        year_totals[y]['n'] += 1
        for k, v in [('cost', s['cost']), ('discount', s['discount']), ('face', face)]:
            year_totals[y][k] += v
        for g, key in [(city_totals, norm(city)), (origin_totals, origin)]:
            g[key][0] += 1
            g[key][1] += s['cost']
            g[key][2] += face
        for label, other in [('Face fiscal', f.get('face')), ('Face CCB', p.get('face')), ('Preço fiscal entrada', inc.get('value')), ('Preço no termo de endosso',p.get('acquisition_price')), ('Face no termo de endosso',p.get('endorsement_face'))]:
            expected = s['cost'] if label.startswith('Preço') else face
            if other is not None and other != expected:
                price_diffs.append([doc, s['name'], label, val(expected), val(other), val(other - expected), 'DIVERGENTE', source, '1.1.2'])
        n, first, last, v = p.get('n'), p.get('first'), p.get('last'), p.get('installment')
        if n and first and last and v is not None and add_months(first, n-1) == last and n == s['n'] and p.get('face') == face:
            rounding_note = ''
            if v*n != face:
                rounding_note = f'; soma das parcelas difere do face em R$ {br(v*n-face)}; última parcela a confirmar'
                exceptions.append(['Arredondamento contratual a confirmar', doc, f'Parcela declarada × quantidade=R$ {br(v*n)}; face declarado=R$ {br(face)}; diferença=R$ {br(v*n-face)}; não ajustada a última parcela; fonte={source}'])
            for j in range(n):
                installments.append(['CCB', doc, s['name'], person, j+1, iso(add_months(first, j)), val(v), 'PENDENTE - sem posição completa de baixas', None, source, '1.1.2', 'Mensal, dia contratual; limitado ao último dia do mês quando necessário' + rounding_note])
        else:
            exceptions.append(['Calendário CCB não gerado', doc, f'Campos ausentes ou divergentes; parcelas={n}; 1º={iso(first)}; último={iso(last)}; fonte={source}'])

    orphan_ccb = sorted(set(pdfs) - set(summaries))
    for doc in orphan_ccb:
        p = pdfs[doc]
        source = rel(p['source'])
        contract_rows.append(['CCB sem registro de aquisição', doc, p['name'], p['cpf'], None, None, val(p['face']), None, p['n'], val(p['installment']), iso(p['first']), iso(p['last']), 'VIA CAPITAL - SCD', p['city'], 'PENDENTE - confirmar aquisição/titularidade; não somado às aquisições', source, '1.1.2 - vínculo PENDENTE'])
        exceptions.append(['CCB sem registro nos resumos de aquisição', doc, f'Existe PDF contratual, mas preço e data de aquisição pela CSG não localizados; não somado às aquisições. Fonte={source}'])
        n, first, last, v = p['n'], p['first'], p['last'], p['installment']
        if n and first and last and v is not None and add_months(first,n-1) == last:
            for j in range(n):
                installments.append(['CCB com aquisição PENDENTE',doc,p['name'],p['cpf'],j+1,iso(add_months(first,j)),val(v),'PENDENTE - aquisição e cobrança',None,source,'1.1.2 - vínculo PENDENTE','Mensal conforme contrato; sem comprovação de compra pela CSG'])

    # Direct receivable declarations form a distinct documented acquisition
    # sample; explicit table dates are used instead of inventing periodicity.
    rec_files = [p['source'] for p in rec_parsed]
    seen_rec = set()
    rec_sources, rec_count, rec_face, rec_cost = [], 0, Decimal(0), Decimal(0)
    rec_origin_totals = defaultdict(lambda: [0, Decimal(0), Decimal(0)])
    for p in rec_parsed:
        key = (p['origin_cpf'], p['doc'])
        if '_arquivo' in p['source'].parts and not p['csg_cnpj']:
            exceptions.append(['Recebível sem vínculo CSG validado',rel(p['source']),'CNPJ da securitizadora não extraído; não integrado'])
            continue
        if not p['doc'] or not p['installments']:
            exceptions.append(['Recebível sem tabela completa extraível', rel(p['source']), 'Não incluído no calendário; revisão documental PENDENTE'])
            continue
        if key in seen_rec:
            exceptions.append(['Declaração repetida', rel(p['source']), f'Originadora/documento={key}; incluída só uma vez'])
            continue
        seen_rec.add(key)
        table_sum = sum((x['value'] for x in p['installments']), Decimal(0))
        source = rel(p['source'])
        rec_sources.append(source)
        if p['face'] is None or table_sum != p['face']:
            exceptions.append(['Tabela de recebível não confere com total', source, f'Tabela=R$ {br(table_sum)}; borderô=R$ {br(p["face"])}; não integrada'])
            continue
        rec_count += 1
        rec_face += p['face']
        if p['acquisition'] is not None:
            rec_cost += p['acquisition']
        rec_origin_totals[p['origin']][0] += 1
        rec_origin_totals[p['origin']][1] += p['acquisition'] or Decimal(0)
        rec_origin_totals[p['origin']][2] += p['face']
        contract_rows.append(['Recebível direto', p['doc'], 'Múltiplos títulos: ver Parcelas CSG', None, None, val(p['acquisition']), val(p['face']), val(p['discount']), len(p['installments']), None, iso(min(x['due'] for x in p['installments'])), iso(max(x['due'] for x in p['installments'])), p['origin'], 'PENDENTE', 'Aquisição exata e CPF dos sacados PENDENTES; não somado às CCBs', source, '1.1.2'])
        for j, x in enumerate(p['installments'], 1):
            installments.append(['Recebível direto', f'{p["doc"]}/{x["title"]}', x['debtor'], None, j, iso(x['due']), val(x['value']), 'PENDENTE - posição de cobrança', None, source, '1.1.2', 'Vencimento explícito da declaração; CPF sacado PENDENTE'])
    inventory.append(['ccb/AAAA-MM/*.pdf; _arquivo/zips/CCB CLIENTES*/*/*.pdf (classificação pelo conteúdo)', 'Recebíveis de originadoras diretas', f'{coverage_start} a {coverage_end}', len(rec_files), f'{rec_count} declarações com total de títulos conferido; sem posição atual de cobrança', '1.1.2'])

    # Both import TXT files encode the same economic events. Entradas is the
    # canonical source for the observed records, not proof of cash settlement.
    baixap = base/'Importacao_Baixas_Entradas/baixa_ent.txt'
    raw = baixap.read_bytes()
    try:
        text = raw.decode('utf-8-sig')
    except UnicodeDecodeError:
        text = raw.decode('cp1252')
    baixas = list(csv.reader(io.StringIO(text), delimiter=';'))
    if baixas and not dt(baixas[0][2]):
        baixas = baixas[1:]
    baixa_rows, baixa_dates, baixa_total = [], [], Decimal(0)
    baixa_events = Counter()
    missing_doc = 0
    for line, r in enumerate(baixas, 2):
        if len(r) < 8 or not dt(r[3]):
            continue
        signature = tuple(r[:8])
        if signature in baixa_events:
            exceptions.append(['Potencial duplicidade de baixa', f'{rel(baixap)}:linha {line}', 'Linha idêntica anterior; mantida no total bruto de importação. Sem documento não se distingue repetição de dois títulos distintos. Conferência PENDENTE'])
        baixa_events[signature] += 1
        amount = money(r[4])
        baixa_total += amount
        baixa_dates.append(dt(r[3]))
        if not r[0]:
            missing_doc += 1
        baixa_rows.append([r[0] or None, cpf(r[1]), iso(dt(r[2])), iso(dt(r[3])), val(amount), val(money(r[5])), val(money(r[6])), val(money(r[7])), 'Importação observada; vínculo ao contrato/parcela PENDENTE', f'{rel(baixap)}:linha {line}', '1.1.2'])
    sai = base/'Importacao_Baixas_Saidas/baixa_sai.txt'
    sai_events = Counter()
    for r in csv.reader(io.StringIO(sai.read_bytes().decode('cp1252')), delimiter=';'):
        if len(r) >= 8 and dt(r[3]):
            sai_events[tuple(r[:8])] += 1
    overlap = sum((baixa_events & sai_events).values())
    inventory.append([rel(baixap), 'Registros de baixa importados', f'{min(baixa_dates)} a {max(baixa_dates)}' if baixa_dates else 'PENDENTE', len(baixa_rows), f'{missing_doc} sem número do documento; não comprovam posição de setembro', '1.1.2'])
    inventory.append([rel(sai), 'Outro formato de importação de baixas', '2026-06', sum(sai_events.values()), f'{overlap} linhas coincidem com entradas; não somadas novamente', '1.1.2'])
    for rp in [base/'Importacao_Baixas_Entradas/BaixaEntradas.xlsm', base/'Importacao_Baixas_Saidas/BaixaSaidas.xlsm']:
        rr = read_rows(rp)
        inventory.append([rel(rp), 'Modelo de importação', 'Exemplos de 2019', max(0, len(rr)-1), 'Exemplos não tratados como recebimentos CSG', 'Não aplicável'])

    # Do not allocate a payment to one of several contracts by FIFO, by debtor
    # alone, or by guessing its installment amount.
    exact_matches = 0
    for i in installments:
        if not i[3]:
            continue
        candidates = [b for b in baixa_rows if b[0] == i[1] and b[1] == i[3] and b[2] == i[5] and b[4] == i[6]]
        if len(candidates) == 1:
            i[7] = 'RECEBIMENTO IDENTIFICADO NO TXT; saldos bancários conciliados conforme cliente'
            i[8] = candidates[0][3]
            exact_matches += 1

    bank_matches, bank_count = [], 0
    for bank in (base/'05.2026.xlsx', base/'06.2026.xlsx'):
        w = load_workbook(bank, read_only=True, data_only=True)
        records = list(w['BOLETOS'].values)
        for line, r in enumerate(records[1:], 2):
            if len(r) < 11 or not r[2] or not dt(r[4]):
                continue
            bank_count += 1
            docpart = str(r[6] or '').split('/')[0].lstrip('0')
            candidates = [x for x in installments if x[0] == 'CCB' and str(x[1]).lstrip('0') == docpart and x[3] == cpf(r[2]) and x[5] == iso(dt(r[4])) and money(x[6]) == money(r[9])]
            if len(candidates) == 1 and norm(r[7]) == 'LIQUIDADO':
                x = candidates[0]
                x[7] = 'RECEBIDO - boleto com documento, CPF, vencimento e valor coincidentes'
                x[8] = iso(dt(r[8]))
                x[9] += f'; {rel(bank)}:BOLETOS linha {line}'
                bank_matches.append([x[1],x[2],x[3],x[4],x[5],x[6],x[8],val(money(r[10])),f'{rel(bank)}:BOLETOS linha {line}','1.1.2'])
        w.close()
        inventory.append([rel(bank)+':BOLETOS','Liquidações de boletos','2026-05' if bank.name.startswith('05') else '2026-06',len(records)-1,'Seu Número somente ligado à CCB quando número, CPF, vencimento e valor coincidem','1.1.2'])

    bp = base/'balancetes/Balancete-ja-set-2026.pdf'
    accounts = parse_balance(bp)
    portfolio = next(a['balance'] for a in accounts if a['account'] == '1.1.2')
    duplicates = next(a['balance'] for a in accounts if a['account'] == '1.1.2.01')
    rights = next(a['balance'] for a in accounts if a['account'] == '1.1.2.02')
    analytic = [a for a in accounts if a['account'].startswith('1.1.2.') and len(a['account'].split('.')) == 5]
    debtor_agg = defaultdict(lambda: {'balance': Decimal(0), 'codes': [], 'accounts': []})
    for a in analytic:
        key = norm(a['name'])
        debtor_agg[key]['balance'] += a['balance']
        debtor_agg[key]['codes'].append(a['code'])
        debtor_agg[key]['accounts'].append(a['account'])
    top = sorted(((k, v) for k, v in debtor_agg.items() if not k.startswith('DIREITOS CREDITORIOS')), key=lambda x:x[1]['balance'], reverse=True)[:20]
    top_rows = [[j, name or 'PENDENTE - nome da conta', ','.join(x['codes']), val(x['balance']), float(x['balance']/portfolio), rel(bp), ','.join(sorted(set(x['accounts']))), 'Por nome contábil normalizado; CPF da conta não disponível'] for j,(name,x) in enumerate(top,1)]
    top_rows.append([None, 'DIREITOS CREDITÓRIOS SEM ABERTURA NOMINAL', '1435', val(rights), float(rights/portfolio), rel(bp), '1.1.2.02.001', 'Não é um único devedor; excluído do ranking nominal'])
    analytic_sum = sum((a['balance'] for a in analytic), Decimal(0))
    checks.append({'teste':'Soma analítica da carteira = conta 1.1.2', 'ano':'2026', 'calculado':val(analytic_sum), 'referencia':val(portfolio), 'diferenca':val(analytic_sum-portfolio), 'status':'OK' if analytic_sum == portfolio else 'DIVERGENTE', 'fonte':f'{rel(bp)}; contas 1.1.2.01.001 e 1.1.2.02.001'})
    checks.append({'teste':'Carteira gerencial aberta = conta 1.1.2', 'ano':'2026', 'calculado':None, 'referencia':val(portfolio), 'diferenca':None, 'status':'PENDENTE - falta posição de contratos/parcelas abertas e composição de direitos creditórios', 'fonte':f'{rel(bp)}; conta 1.1.2; ccb/; {rel(baixap)}'})

    stock_sources = []
    stocks = {}
    for year in range(2022,2026):
        p = base/'publicacao-balancos/DOCUMENTOS CREDIT'/f'BALANCETE CREDIT {year}.pdf'
        acc = parse_balance(p)
        a = next((a for a in acc if a['account'] == '1.1.2'), None)
        stocks[str(year)] = val(a['balance']) if a else None
        stock_sources.append(f'{rel(p)}; conta 1.1.2')
    stocks['2026'] = val(portfolio)
    stock_sources.append(f'{rel(bp)}; conta 1.1.2')
    summary_sources = '; '.join(sorted({s['source'].split(':linha')[0] for s in summaries.values()}))
    years = [str(y) for y in range(2022,2027)]
    endorsement_sources = 'ccb/AAAA-MM/*.pdf; _arquivo/zips/CCB CLIENTES MM.AAAA-*/*/*.pdf | TERMO DE ENDOSSO, Quadro I. Relação nominal de cada arquivo e contrato na aba Contratos CSG, colunas Fonte e Preço contratual endosso; conta 1.1.2'
    endorsement_count = sum(v['n'] for v in endorsement_totals.values())
    endorsement_difference = sum((v['difference'] for v in endorsement_totals.values()),Decimal(0))
    summary_rows = [
        ['Saldo contábil da carteira', *[stocks[y] for y in years], 'Não somar estoques', 'CONTÁBIL', '; '.join(stock_sources), '1.1.2'],
        ['Aquisições CCB - preço na base de planilhas', *[val(year_totals[y]['cost']) if y in year_totals else None for y in years], val(sum((z['cost'] for z in year_totals.values()),Decimal(0))), f'BASE {coverage_start} a {coverage_end}; planilhas e termos recuperados; não é desembolso nem posição aberta; comparar com preço nos endossos', summary_sources, '1.1.2'],
        ['Aquisições CCB - preço explícito nos endossos', *[val(endorsement_totals[y]['price']) if y in endorsement_totals else None for y in years], val(sum((z['price'] for z in endorsement_totals.values()),Decimal(0))), f'CONTRATUAL: {endorsement_count} documentos com preço explícito; sem presumir desembolso ou ajuste contábil',endorsement_sources,'1.1.2'],
        ['Aquisições CCB - deságio pelo preço do endosso', *[val(endorsement_totals[y]['discount']) if y in endorsement_totals else None for y in years], val(sum((z['discount'] for z in endorsement_totals.values()),Decimal(0))), 'CÁLCULO DOCUMENTAL: face contratual menos preço expresso no endosso; não é receita apropriada no período',endorsement_sources,'1.1.2'],
        ['Diferença preço endosso menos base de planilhas', *[val(endorsement_totals[y]['difference']) if y in endorsement_totals else None for y in years], val(endorsement_difference),'DIFERENÇA DOCUMENTAL: comparar com lançamentos e razão; não adicionada automaticamente aos custos da DRE',endorsement_sources+'; '+summary_sources,'1.1.2'],
        ['Aquisições CCB documentadas - face', *[val(year_totals[y]['face']) if y in year_totals else None for y in years], val(sum((z['face'] for z in year_totals.values()),Decimal(0))), 'FACE ORIGINAL; não é saldo a receber', summary_sources, '1.1.2'],
        ['Aquisições CCB - deságio na base de planilhas', *[val(year_totals[y]['discount']) if y in year_totals else None for y in years], val(sum((z['discount'] for z in year_totals.values()),Decimal(0))), 'Diferença face menos preço da base; comparar com deságio pelo preço do endosso; apropriação atual PENDENTE', summary_sources, '1.1.2'],
        ['Contratos CCB nos resumos (quantidade)', *[year_totals[y]['n'] if y in year_totals else None for y in years], len(summaries), 'QUANTIDADE', summary_sources, '1.1.2'],
        ['Carteira a vencer e aging de vencidos', *['PENDENTE']*6, 'Não inferido a partir do calendário original', f'{rel(baixap)}; posição incompleta', '1.1.2'],
        ['Perda esperada e valor recuperável', *['PENDENTE']*6, 'Sem percentuais arbitrários; avaliação de risco e posição aberta necessárias', 'CPC 48 §5.5.17; carteira atual por parcela ausente', '1.1.2'],
    ]
    sheets.append({'name':'3 Carteira', 'headers':['Indicador','2022','2023','2024','2025','2026 jan-set','Acumulado','Situação/método','Fonte','Conta'], 'rows':summary_rows})
    for row in contract_rows:
        contractual = pdfs.get(row[1],{}).get('acquisition_price') if row[0].startswith('CCB') else None
        row.extend([val(contractual),val(contractual-money(row[5])) if contractual is not None and row[5] is not None else None,val(money(row[6])-contractual) if contractual is not None and row[6] is not None else None])
    sheets.append({'name':'Contratos CSG', 'headers':['Tipo','Documento','Devedor','CPF/CNPJ','Data aquisição','Preço na base planilha R$','Face original R$','Deságio na base R$','Nº parcelas','Parcela contratual R$','Primeiro vencimento','Último vencimento','Originadora','Município','Situação','Fonte','Conta','Preço contratual endosso R$','Diferença endosso x base R$','Deságio pelo preço do endosso R$'], 'rows':contract_rows})
    sheets.append({'name':'Parcelas CSG','headers':['Tipo','Documento/título','Devedor','CPF/CNPJ','Parcela','Vencimento contratual','Valor R$','Situação recebimento','Data baixa identificada','Fonte','Conta','Método'], 'rows':installments})
    sheets.append({'name':'Top20 carteira','headers':['Posição','Devedor/conta','Códigos','Saldo R$','% carteira total','Fonte','Conta','Observação'], 'rows':top_rows})
    concentration_rows = []
    total_face = sum((v['face'] for v in year_totals.values()),Decimal(0))
    for label, groups in [('Município',city_totals),('Originadora',origin_totals)]:
        for key, a in sorted(groups.items(),key=lambda x:x[1][2],reverse=True):
            concentration_rows.append([label,key,a[0],val(a[1]),val(a[2]),float(a[2]/total_face) if total_face else None,f'AQUISIÇÕES CCB {coverage_start} a {coverage_end}; não concentração do estoque em setembro',summary_sources,'1.1.2'])
    for key,a in sorted(rec_origin_totals.items(),key=lambda x:x[1][2],reverse=True):
        concentration_rows.append(['Originadora recebíveis diretos',key,a[0],val(a[1]),val(a[2]),float(a[2]/rec_face) if rec_face else None,'AMOSTRA DISTINTA de declarações; % sobre face original dos recebíveis diretos documentados; não estoque de setembro','; '.join(rec_sources),'1.1.2'])
    sheets.append({'name':'Concentração aquisições','headers':['Dimensão','Grupo','Contratos','Preço aquisição R$','Face original R$','% face da amostra','Escopo','Fonte','Conta'],'rows':concentration_rows})
    sheets.append({'name':'Baixas observadas','headers':['Documento','CPF/CNPJ','Vencimento','Data baixa','Valor informado R$','Juros R$','Multa R$','Desconto R$','Situação','Fonte','Conta'],'rows':baixa_rows})
    if bank_matches:
        sheets.append({'name':'Parcelas recebidas banco','headers':['Contrato CCB','Devedor','CPF','Parcela','Vencimento','Parcela R$','Liquidação','Valor liquidado R$','Fonte','Conta'],'rows':bank_matches})
    sheets.append({'name':'Fontes carteira','headers':['Fonte','Tipo','Cobertura','Registros','Limitação','Conta'],'rows':inventory})
    sheets.append({'name':'Conferência operações','headers':['Devedor','Documento CCB','Face planilha R$','Face PDF R$','Diferença R$','Situação','Fonte','Conta'],'rows':ops_check_rows})
    if price_diffs:
        sheets.append({'name':'Divergências carteira','headers':['Documento','Devedor','Comparação','Resumo R$','Outra fonte R$','Diferença R$','Situação','Fonte','Conta'],'rows':price_diffs})
    if exceptions:
        sheets.append({'name':'Exceções carteira','headers':['Ocorrência','Documento/fonte','Detalhe'],'rows':exceptions})
    sheets.append({'name':'Vínculos CSG documentos','headers':['Instrumento','Documento','Fonte','CNPJ CSG localizado','Originadora identificada','CNPJ/CPF originadora','Validação','Conta'],'rows':validation_rows})
    if dedup_rows:
        sheets.append({'name':'Duplicatas carteira','headers':['Chave','Documento/hash','Fonte escolhida','Fonte anterior','Comparação','Tratamento'],'rows':dedup_rows})
    archive_rows, open_position_candidates = inspect_archive_sources(base)
    sheets.append({'name':'Revisão arquivo carteira','headers':['Fonte','Itens/registros','PDFs','Planilhas/cabeçalhos','Conclusão da inspeção'],'rows':archive_rows})
    sheets.append({'name':'Aquisições mensais CCB','headers':['Mês do pacote','Contratos CCB','Custo aquisição R$','Deságio R$','Face original R$','Fonte e conta'],'rows':[[m,v['contratos'],v['custo'],v['desagio'],v['face'],summary_sources+' | conta 1.1.2'] for m,v in sorted(month_stats.items())]})
    unmapped = base/'saida/parcelas_por_nota_35_42_49.xlsx'
    rr = read_rows(unmapped)
    next(s for s in sheets if s['name']=='Fontes carteira')['rows'].append([rel(unmapped),'Parcelas por nota e título','Calendário 2025–2026',len(rr)-1,'Sem CNPJ da securitizadora e sem ligação documental verificada ao saldo CSG; não incorporado ao estoque','PENDENTE'])

    pendencias.extend([
        {'item':'Posição da carteira VIA CAPITAL, UY3 e cobrança em 30/09/2026','motivo':'Entregar por contrato/parcela: CPF, número, vencimento, valor, saldo, pagamentos, renegociação, garantias e status. Sem isso não há aging, inadimplência nem recuperabilidade confiáveis.','fonte':'ccb/; Importacao_Baixas_Entradas/baixa_ent.txt; conta 1.1.2'},
        {'item':'Composição nominal dos direitos creditórios','motivo':f'Conta 1.1.2.02.001 mantém R$ {br(rights)} sem abertura por sacado no balancete. Identificar origem, contratos, vencimentos e baixas.','fonte':f'{rel(bp)}; conta 1.1.2.02.001'},
        {'item':'Complementar histórico anterior a abril/2025','motivo':'Aquisições de abril/2025 a setembro/2026 foram processadas, incluindo pacotes de _arquivo/zips antes não utilizados. Aquisições anteriores a abril/2025 não identificadas nos conjuntos de contratos inspecionados; verificar complemento histórico.','fonte':'ccb/; _arquivo/zips/; conta 1.1.2'},
        {'item':'Política de perdas esperadas, cobrança e renegociação','motivo':'Avaliar perdas com informação sustentável e probabilidades conforme CPC 48 §5.5.17. Não adotados percentuais arbitrários nem aplicada automaticamente norma prudencial bancária.','fonte':'https://www.cpc.org.br/Arquivos/Documentos/530_CPC_48_rev_21.pdf; conta 1.1.2'},
        {'item':'Vínculo das baixas com contrato/parcela e controle de duplicidade','motivo':f'{missing_doc} linhas de importação sem número de documento; {overlap} coincidem nos TXT entradas e saídas. Identificar contratos/parcelas e evitar dupla baixa. Saldos bancários conciliados conforme informação do cliente; não se solicita reconfirmação genérica.','fonte':f'{rel(baixap)}; {rel(sai)}; conta 1.1.2'},
        {'item':'Tabela de correspondência entre Seu Número do boleto e número CCB','motivo':f'Examinados {bank_count} boletos de maio/junho; somente {len(bank_matches)} vínculos inequívocos com o calendário de CCBs. Os demais números não foram inferidos por nome ou valor.','fonte':'05.2026.xlsx e 06.2026.xlsx, aba BOLETOS; conta 1.1.2'},
        {'item':'Identificar origem da planilha parcelas_por_nota_35_42_49','motivo':'Cabeçalho não identifica a CSG; é necessário vínculo documental antes de somá-la à carteira.','fonte':rel(unmapped)},
    ])
    metrics = {'saldo_contabil_2026':val(portfolio),'duplicatas_2026':val(duplicates),'direitos_2026':val(rights),'carteira_recuperavel_2026':None,'perda_esperada_2026':None,'aging_disponivel':False,'ccb_contratos':len(summaries),'ccb_pdfs_unicos':len(pdfs),'ccb_aquisicao_pendente':len(orphan_ccb),'parcelas_calendario':len(installments),'baixas_importadas':len(baixa_rows),'baixas_registros_distintos':len(baixa_events),'baixas_valor_informado':val(baixa_total),'baixas_sem_documento':missing_doc,'baixas_coincidentes_txt':overlap,'baixas_contrato_identificadas':exact_matches,'boletos_contrato_identificados':len(bank_matches),'recebiveis_declaracoes':rec_count,'recebiveis_face_original':val(rec_face),'recebiveis_liquido_documentado':val(rec_cost),'saldos_anuais':stocks,'aquisicoes_ccb':{y:{k:val(v) if isinstance(v,Decimal) else v for k,v in z.items()} for y,z in year_totals.items() if z['n']},'top20_saldo':val(sum((x['balance'] for _,x in top),Decimal(0))),'divergencias_precos':len(price_diffs),'excecoes_calendario':len(exceptions),'cobertura_inicio':coverage_start,'cobertura_fim':coverage_end,'meses_integrados_arquivo':sorted(set(months_new)),'aquisicoes_mensais':month_stats,'ccb_recuperadas_termo_endosso':recovered_endorsements,'documentos_novos_arquivo':sum('_arquivo' in p['source'].parts for p in documents),'documentos_novos_csg_validado':sum('_arquivo' in p['source'].parts and p['csg_cnpj'] for p in documents),'duplicatas_conteudo_ou_contrato':len(dedup_rows),'arquivos_posicao_aberta_identificados':open_position_candidates,'bancos_conciliados_informacao_cliente':True}
    metrics['precos_endosso'] = {y:{k:val(v) if isinstance(v,Decimal) else v for k,v in z.items()} for y,z in endorsement_totals.items() if z['n']}
    metrics['diferenca_precos_endosso_planilhas'] = val(endorsement_difference)
    reports.append({'title':'3. Carteira de créditos: saldo contábil e limite documental','paragraphs':[
        f'A carteira contábil é R$ {br(portfolio)}: R$ {br(duplicates)} em duplicatas nominativas e R$ {br(rights)} em direitos creditórios sem abertura por sacado. Fonte: {rel(bp)}, contas 1.1.2, 1.1.2.01 e 1.1.2.02. A soma das contas analíticas foi conciliada ao grupo 1.1.2.',
        f'A base processada documenta {len(summaries)} aquisições CCB entre {coverage_start} e {coverage_end}, além de {rec_count} declarações de recebíveis diretos. Foram incorporados os pacotes de junho, julho, agosto e setembro/2026 existentes em _arquivo/zips, antes não utilizados no levantamento. Os PDFs novos foram identificados pelo CNPJ da CSG 46.788.467/0001-49; as entradas de CCBs identificam VIA CAPITAL, CNPJ 48.632.754/0001-90. A planilha relatorio_operacoes.xlsx é extração auxiliar de abril/2025 e não foi somada novamente. Fontes: ccb/; saida/relatorio_resumido2025-04.xlsx e 2025-05.xlsx; _arquivo/zips/CCB CLIENTES MM.2026-*; conta de controle 1.1.2.',
        f'A classificação usa o conteúdo do PDF, inclusive a declaração nº 660592 de Darciano Dalla Lana, arquivada com nome iniciado por CCB. Cópias idênticas são eliminadas por SHA256 e contratos repetidos não são somados novamente; havendo versões diferentes, a origem posterior é mantida e a diferença fica registrada. {len(recovered_endorsements)} aquisição(ões) sem linha nos resumos foram recuperadas do termo de endosso quando preço, data e CNPJ CSG estavam explícitos. Fontes: Vínculos CSG documentos, Duplicatas carteira e contratos/PDFs nela relacionados; conta 1.1.2.',
        f'A leitura dos termos de endosso localizou {len(price_diffs)} comparações com diferença de preço em relação às planilhas geradas. O preço contratual excede a base das planilhas em R$ {br(endorsement_difference)} no conjunto; a abertura por contrato está em Divergências carteira e os dois preços estão lado a lado em Contratos CSG. Esse contraste documental não foi convertido em pagamento presumido nem em ajuste automático da DRE. Fontes: PDFs/Quadro I do TERMO DE ENDOSSO identificados em cada linha e relatórios resumidos/fiscais; conta de controle 1.1.2.',
        f'Foram observadas {len(baixa_rows)} linhas de importação de baixa ({len(baixa_events)} combinações distintas), com valor bruto informado de R$ {br(baixa_total)}, em junho/2026; {missing_doc} não informam número do documento. Existe linha idêntica adicional cuja duplicidade econômica é PENDENTE; ambas foram mantidas na base bruta. Os TXT de entradas e saídas compartilham {overlap} linhas e não foram somados. Fonte: {rel(baixap)} e {rel(sai)}; vínculo à conta 1.1.2 a confirmar. Os XLSM de exemplo de 2019 foram excluídos.',
        f'Os saldos bancários foram informados como conciliados pelo cliente. A restrição da carteira diz respeito ao vínculo individual entre recebimentos e contratos/parcelas: nas abas BOLETOS de 05.2026.xlsx e 06.2026.xlsx, {len(bank_matches)} correspondência(s) simultânea(s) de número CCB, CPF, vencimento e valor foram identificadas. Os TXT de baixa não informam o número contratual. Esses conjuntos de pagamentos não equivalem à posição completa de parcelas abertas em 30/09. Fontes: BOLETOS e TXT de baixa; controle 1.1.2. Não se solicita reconfirmação genérica dos saldos bancários.',
        'A inspeção adicional dos pacotes ZIP de _arquivo/zips e dos cabeçalhos das planilhas extraídas localizou contratos, resumos de aquisição, arquivos fiscais e relatórios de divergência de extração. Não foi identificado nesse conjunto relatório de posição aberta/paga por contrato ou nova base de baixas. O ZIP de outubro/2026 contém contratos fora da data-base e não foi somado a setembro; sua existência não comprova fechamento contábil de outubro. A lista efetivamente inspecionada consta na aba Revisão arquivo carteira.',
        'PENDENTE: aging, inadimplência, perda esperada, valor recuperável e prazo médio da carteira aberta. Vencimento contratual não prova que uma parcela continua aberta; ausência de baixa nesta amostra não foi tratada como atraso. As faixas solicitadas serão calculadas quando houver posição completa por parcela. A avaliação seguirá informação de crédito sustentável e ponderação de probabilidades (CPC 48, §5.5.17); não foram usados percentuais arbitrários de perda.',
        f'O top 20 considera devedores nominativos do balancete e agrupa nomes normalizados, pois não há CPF ligado a cada conta. Os direitos creditórios de R$ {br(rights)} foram mostrados separadamente e não tratados como um devedor. A concentração por município e originadora refere-se somente às aquisições CCB documentadas, não ao estoque de setembro. Fontes: {rel(bp)}, contas 1.1.2.01.001/1.1.2.02.001; planilhas fiscais mensais em ccb/.',
        'A diferença entre face original adquirida e saldo contábil atual não é uma perda apurada: os escopos e datas são distintos. O complemento histórico anterior a abril/2025 e o vínculo individual dos pagamentos/saldo de deságio por contrato não foram identificados nos conjuntos de carteira processados. As aquisições de junho a setembro/2026 estão integradas; informação antes não processada não é tratada como documento ausente. A conciliação da posição aberta continua PENDENTE de um controle de parcelas em aberto. A planilha parcelas_por_nota_35_42_49.xlsx foi inventariada sem vínculo documental verificado com a CSG.'
    ]})
    return {'sheets':sheets,'metrics':metrics,'checks':checks,'pendencias':pendencias,'report':reports}


if __name__ == '__main__':
    import json
    b = Path(__file__).resolve().parent.parent
    result = build(b, Path(__file__).resolve().parent)
    p = Path(__file__).resolve().parent/'carteira_resultado.json'
    p.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result['metrics'],ensure_ascii=False,indent=2))
