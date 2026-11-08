"""Leitura compartilhada dos razões anuais CSG e conciliação com balancetes.

Fontes anuais são exclusivas: não acrescentar ECD nem outros razões sobrepostos.
Valores internos dos eventos são inteiros em centavos, conforme o parser comum.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal
import argparse
import hashlib
import json
from pathlib import Path
import pickle
import re
import sqlite3
import tempfile
import unicodedata

import indexar_razao_geral as parser

VERSION = "1.0.0"
_MEMORY = {}


def _hash(path):
    return parser.sha256(Path(path))


def _rel(path, base):
    try:
        return str(Path(path).resolve().relative_to(Path(base).resolve()))
    except ValueError:
        return str(Path(path).resolve())


def _money(cents):
    return None if cents is None else float(Decimal(cents) / 100)


def _totals(sections):
    rows = []
    for s in sections:
        t = s['total_fonte']
        if t is None:
            continue
        dd = s['debito_centavos'] - t['debito_centavos']
        dc = s['credito_centavos'] - t['credito_centavos']
        rows.append(dict(secao_id=s['secao_id'], codigo_conta=s['codigo_conta'],
                         aba=t['aba'], linha=t['linha'], debito_centavos=s['debito_centavos'],
                         credito_centavos=s['credito_centavos'],
                         referencia_debito_centavos=t['debito_centavos'],
                         referencia_credito_centavos=t['credito_centavos'],
                         diferenca_debito_centavos=dd, diferenca_credito_centavos=dc,
                         status='OK' if dd == dc == 0 else 'DIVERGÊNCIA'))
    return rows


def load(base: Path, out: Path) -> dict:
    """Return {years, events, accounts, source, quality}; year keys are strings.

    years[year] is parse_workbook's complete result plus source/quality.
    accounts[year][code] is a list of source account sections (no hidden merge).
    events retain all parser fields and gain source, ano_fonte, id_local and a
    global id. The returned shared object is read-only by convention.
    Cache invalidation uses SHA-256 of original, converted and parser source.
    """
    base, out = Path(base), Path(out)
    files = []
    parser_hash = _hash(Path(parser.__file__))
    for year in range(2022, 2027):
        original = base / 'balancetes' / f'Razão{year}.xls'
        converted = out / 'qa' / 'razoes_anuais' / f'Razão{year}.xlsx'
        if not original.exists() or not converted.exists():
            raise FileNotFoundError(f'Razão anual ou conversão ausente: {original}; {converted}')
        original_hash, converted_hash = _hash(original), _hash(converted)
        key = hashlib.sha256((original_hash + converted_hash + parser_hash + VERSION).encode()).hexdigest()
        files.append((str(year), original, converted, original_hash, converted_hash, key))
    memory_key = (str(base.resolve()), str(out.resolve()), tuple(f[-1] for f in files))
    if memory_key in _MEMORY:
        return _MEMORY[memory_key]
    cache = out / 'qa' / 'razoes_anuais' / 'cache'
    cache.mkdir(parents=True, exist_ok=True)
    result = dict(years={}, events=[], accounts={}, source=[], quality={})
    global_id = 0
    for year, original, converted, original_hash, converted_hash, key in files:
        cachepath = cache / f'razao-{year}-{key[:20]}.pickle'
        if cachepath.exists():
            with cachepath.open('rb') as f:
                stored = pickle.load(f)
            if stored.get('key') != key:
                raise ValueError(f'Cache com chave inconsistente: {cachepath}')
            p = stored['parsed']
        else:
            p = parser.parse_workbook(converted)
            with tempfile.NamedTemporaryFile(dir=cache, prefix=cachepath.stem+'-', suffix='.tmp', delete=False) as f:
                temporary = Path(f.name)
                pickle.dump(dict(key=key, parsed=p), f, protocol=pickle.HIGHEST_PROTOCOL)
            temporary.replace(cachepath)
        # The shared parser intentionally reports unknown non-financial rows.
        # Annual exports add an identifiable signature block after the last
        # total. Preserve it as metadata instead of treating it as lost data.
        signatures, unknown = [], []
        for row in p['unknown']:
            text = '\n'.join(row['celulas'].values())
            if 'JANE HARTMANN HUNING' in text and 'VALDECIR DAL ONGARO' in text and 'CRC' in text and not any(k in row['celulas'] for k in ('9','10','11','14')):
                signatures.append(row)
            else:
                unknown.append(row)
        p['unknown'] = unknown
        p['metadata']['assinaturas'] = signatures
        p['row_types']['assinatura'] = len(signatures)
        p['row_types']['nao_classificada'] = len(unknown)
        totals = _totals(p['sections'])
        missing_totals = [s['secao_id'] for s in p['sections'] if s['total_fonte'] is None]
        outside_year = [e['id'] for e in p['events'] if str(e['ano']) != year]
        limit = any(s['linhas'] >= 65536 for s in p['sheets'])
        groups = sorted({e['grupo_1'] for e in p['events']})
        source = dict(ano=year, source=_rel(original, base), sha256=original_hash,
                      bytes=original.stat().st_size, convertido=_rel(converted, base),
                      convertido_sha256=converted_hash, parser_sha256=parser_hash,
                      cache_sha256=key)
        quality = dict(eventos=p['source_events'], secoes=len(p['sections']),
                       contas=len({s['codigo_conta'] for s in p['sections']}),
                       abas=p['sheets'], limite_65536=limit,
                       secoes_sem_total=missing_totals, totais_verificados=len(totals),
                       totais_divergentes=sum(t['status'] != 'OK' for t in totals),
                       totais_divergentes_detalhes=[t for t in totals if t['status'] != 'OK'],
                       saldos_verificados=p['balance_checks'],
                       saldos_divergentes=len(p['balance_failures']),
                       saldos_divergentes_detalhes=p['balance_failures'],
                       linhas_nao_classificadas=len(p['unknown']),
                       linhas_nao_classificadas_detalhes=p['unknown'],
                       eventos_fora_ano_fonte=outside_year,
                       conta_642_presente=any(e['codigo_conta'] == '642' for e in p['events']),
                       grupos_presentes=groups,
                       cabecalhos_rodapes=p['row_types'].get('cabecalho_rodape', 0),
                       assinaturas_finais=len(signatures),
                       sem_contrapartida=sum(not e['contrapartida'] for e in p['events']),
                       inicio=min((e['data'] for e in p['events']), default=None),
                       fim=max((e['data'] for e in p['events']), default=None),
                       debito_centavos=sum(e['debito_centavos'] for e in p['events']),
                       credito_centavos=sum(e['credito_centavos'] for e in p['events']))
        implantations = {}
        for e in p['events']:
            text = ''.join(c for c in unicodedata.normalize('NFD', e['historico']) if not unicodedata.combining(c)).upper()
            is_opening = bool(re.search(r'SALDO\s+(?:FINAL|INICIAL)\s+EM|IMPLANTA[ÇC]AO|REIMPLANTA|BALANCO\s+DE\s+ABERTURA', text))
            e['tipo_evento_cobertura'] = 'IMPLANTAÇÃO/SALDO' if is_opening else 'MOVIMENTO REGISTRADO'
            if is_opening:
                k = (e['data'], e['lote'], e['historico'])
                d = implantations.setdefault(k, dict(data=e['data'], lote=e['lote'], historico=e['historico'], eventos=0, contas=set(), debito_centavos=0, credito_centavos=0, origens=[]))
                d['eventos'] += 1
                d['contas'].add(e['codigo_conta'])
                d['debito_centavos'] += e['debito_centavos']
                d['credito_centavos'] += e['credito_centavos']
                d['origens'].append(dict(aba=e['aba'], linha=e['linha'], conta=e['codigo_conta']))
        quality['implantacoes_saldos'] = [{**d, 'contas': sorted(d['contas'], key=int)} for d in implantations.values()]
        quality['cobertura_observacao'] = ('Há lançamentos de implantação/saldos; arquivo íntegro não implica detalhamento econômico de todos os movimentos anteriores. Não converter esses registros em recebimentos/pagamentos.' if implantations else 'Datas e movimentos conforme arquivo; completude documental depende da cobertura por conta.')
        bad = limit or missing_totals or quality['totais_divergentes'] or p['balance_failures'] or p['unknown'] or outside_year
        quality['status'] = 'DIVERGÊNCIA / REVISAR COBERTURA' if bad else 'APURADO / SEM INDÍCIO DE CORTE'
        if not bad and implantations:
            quality['status'] = 'APURADO / COM IMPLANTAÇÃO DE SALDOS'
        account_map = defaultdict(list)
        for section in p['sections']:
            account_map[section['codigo_conta']].append(section)
        for e in p['events']:
            global_id += 1
            e['id_local'], e['id'] = e['id'], global_id
            e['ano_fonte'], e['source'] = year, source['source']
            e['arquivo'], e['arquivo_sha256'] = source['source'], original_hash
            e['convertido'], e['convertido_sha256'] = source['convertido'], converted_hash
        p['source'], p['quality'], p['total_checks'] = source, quality, totals
        result['years'][year] = p
        result['events'].extend(p['events'])
        result['accounts'][year] = dict(account_map)
        result['source'].append(source)
        result['quality'][year] = quality
    _MEMORY[memory_key] = result
    return result


def _check(test, year, calculated, reference, source, status=None):
    difference = calculated - reference
    return dict(teste=test, ano=str(year), calculado=_money(calculated),
                referencia=_money(reference), diferenca=_money(difference),
                status=status or ('OK' if difference == 0 else 'DIVERGÊNCIA'), fonte=source)


def _account_positions(p):
    """One record per section; repeated sections are flagged, never summed blindly."""
    endings = {}
    for e in p['events']:
        endings[e['secao_id']] = e
    rows = []
    for s in p['sections']:
        opening = s['saldo_anterior_fonte']
        end = endings.get(s['secao_id'])
        rows.append(dict(code=s['codigo_conta'], classification=s['classificacao'],
                         name=s['nome_conta'], section=s['secao_id'],
                         opening=opening['saldo_centavos'] if opening else None,
                         debit=s['debito_centavos'], credit=s['credito_centavos'],
                         balance=end['saldo_centavos'] if end else opening['saldo_centavos'] if opening else None,
                         origin=s['cabecalhos'][0]))
    return rows


def build(base: Path, out: Path) -> dict:
    from mod_contabilidade import parse_balancete, is_leaf
    base, out = Path(base), Path(out)
    data = load(base, out)
    coverage, reconciliation, checks, issues = [], [], [], []
    details = []
    positions_by_year = {}
    reconciliation_metrics = {}
    for year, p in data['years'].items():
        q, source = p['quality'], p['source']['source']
        coverage.append([int(year), q['inicio'], q['fim'], len(p['sheets']),
                         max(s['linhas'] for s in p['sheets']), q['eventos'], q['contas'],
                         q['totais_verificados'], q['secoes_sem_total'].__len__(),
                         'Sim' if q['conta_642_presente'] else 'Não', ', '.join(q['grupos_presentes']),
                         _money(q['debito_centavos']), _money(q['credito_centavos']),
                         q['sem_contrapartida'], q['status'], source])
        for t in p['total_checks']:
            src = f"{source} | {t['aba']}:{t['linha']} | conta {t['codigo_conta']}"
            checks.append(_check('Razão: soma dos movimentos = total da conta — débitos', year, t['debito_centavos'], t['referencia_debito_centavos'], src))
            checks.append(_check('Razão: soma dos movimentos = total da conta — créditos', year, t['credito_centavos'], t['referencia_credito_centavos'], src))
        checks.append(_check('Razão: diferenças nas recorrências individuais de saldo', year,
                             sum(abs(r['diferenca_centavos']) for r in p['balance_failures']), 0,
                             f"{source} | {p['balance_checks']} linhas verificadas individualmente; detalhes no catálogo"))
        if q['status'].startswith('DIVERGÊNCIA'):
            issues.append(dict(item=f'Cobertura/consistência razão {year}', motivo=json.dumps(q, ensure_ascii=False), fonte=source))
        path = base / ('balancetes/Balancete-ja-set-2026.pdf' if year == '2026' else f'publicacao-balancos/DOCUMENTOS CREDIT/BALANCETE CREDIT {year}.pdf')
        balances = parse_balancete(path)
        leaves = {a['code']: a for a in balances if is_leaf(a, balances)}
        all_balances = {a['code']: a for a in balances}
        positions = _account_positions(p)
        positions_by_year[year] = positions
        grouped = defaultdict(list)
        for r in positions:
            grouped[r['code']].append(r)
            if r['opening'] is not None and r['balance'] is not None:
                checks.append(_check('Razão: abertura + débitos − créditos = final por conta', year,
                                     r['opening']+r['debit']-r['credit'], r['balance'],
                                     f"{source} | {r['origin']['aba']}:{r['origin']['linha']} | conta {r['code']} | seção {r['section']}"))
        stats = Counter()
        for account, rr in grouped.items():
            if len(rr) != 1:
                stats['contas_com_multiplas_secoes'] += 1
                for r in rr:
                    reconciliation.append([int(year), account, r['classification'], r['name'], 'Seções repetidas: revisão de filial/reimplantação', _money(r['opening']), None, None, _money(r['debit']), None, None, _money(r['credit']), None, None, _money(r['balance']), None, None, f"{source} | {r['origin']['aba']}:{r['origin']['linha']} | seção {r['section']}"])
                continue
            r = rr[0]
            a = all_balances.get(account)
            src = f"{source} | {r['origin']['aba']}:{r['origin']['linha']} | conta {account} ({r['classification']}); {_rel(path,base)} | p. {a['page'] if a else '?'}"
            if a is None:
                stats['contas_ausentes_balancete'] += 1
                vals = []
                for k in ('opening', 'debit', 'credit', 'balance'):
                    vals += [_money(r[k]), None, None]
                reconciliation.append([int(year), account, r['classification'], r['name'], 'Conta do razão ausente no balancete', *vals, src])
                details.append(dict(ano=year, conta=account, status='AUSENTE NO BALANCETE', fonte=src))
                continue
            different_class = a['classification'] != r['classification']
            vals, diffs = [], []
            for k, label in (('opening', 'abertura'), ('debit', 'débitos'), ('credit', 'créditos'), ('balance', 'saldo final')):
                ref = int(a[k] * 100)
                value = r[k]
                diff = None if value is None else value - ref
                vals += [_money(value), _money(ref), _money(diff)]
                if value is not None:
                    checks.append(_check(f'Razão × balancete por conta — {label}', year, value, ref, src))
                    diffs.append(diff)
            status = 'OK' if diffs and all(d == 0 for d in diffs) else 'DIVERGÊNCIA'
            if different_class:
                status += f" / classificação do balancete: {a['classification']}"
                stats['classificacao_diferente'] += 1
            stats['contas_comparadas'] += 1
            stats['contas_sem_diferenca' if all(d == 0 for d in diffs) else 'contas_com_diferenca'] += 1
            reconciliation.append([int(year), account, r['classification'], r['name'], status, *vals, src])
            details.append(dict(ano=year, conta=account, classificacao_razao=r['classification'], classificacao_balancete=a['classification'], opening=r['opening'], debit=r['debit'], credit=r['credit'], balance=r['balance'], diferencas_centavos=dict(zip(['opening','debit','credit','balance'], [None if r[k] is None else r[k]-int(a[k]*100) for k in ['opening','debit','credit','balance']])), status=status, fonte=src))
        for account, a in leaves.items():
            if account not in grouped:
                stats['contas_balancete_sem_razao'] += 1
                src = f"{_rel(path,base)} | conta {account} ({a['classification']}) | p. {a['page']}"
                reconciliation.append([int(year), account, a['classification'], a['description'], 'Conta do balancete sem seção no razão', None, float(a['opening']), None, None, float(a['debit']), None, None, float(a['credit']), None, None, float(a['balance']), None, src])
        reconciliation_metrics[year] = dict(stats)
    # Carry-over differences are disclosed; closing entries and branch changes
    # are not invented to force year-to-year agreement.
    continuity = []
    for previous, year in zip(['2022','2023','2024','2025'], ['2023','2024','2025','2026']):
        before = defaultdict(list); after = defaultdict(list)
        for r in positions_by_year[previous]: before[r['code']].append(r)
        for r in positions_by_year[year]: after[r['code']].append(r)
        for account in sorted(set(before) & set(after), key=lambda v: int(v)):
            if len(before[account]) == len(after[account]) == 1:
                a, b = before[account][0], after[account][0]
                if a['balance'] is not None and b['opening'] is not None:
                    diff = b['opening'] - a['balance']
                    if diff:
                        continuity.append(dict(ano_anterior=previous, ano=year, conta=account, classificacao_anterior=a['classification'], classificacao_atual=b['classification'], saldo_anterior_centavos=a['balance'], abertura_atual_centavos=b['opening'], diferenca_centavos=diff, observacao='Verificar encerramento, alteração de plano, filial ou reimplantação; sem ajuste presumido.'))
    export = out / 'razoes-anuais'
    export.mkdir(parents=True, exist_ok=True)
    parser.dump_json(export / 'conciliacao.json', dict(por_ano=reconciliation_metrics, detalhes=details, continuidade_divergente=continuity))
    catalog = _persist(data, export)
    metrics = dict(coverage=data['quality'], reconciliation=reconciliation_metrics,
                   continuity_differences=continuity, source=data['source'],
                   index_directory=_rel(export,base), events=len(data['events']),
                   status='RAZÕES ANUAIS INDEXADOS; DIVERGÊNCIAS PRESERVADAS')
    return dict(sheets=[dict(name='Razões cobertura', headers=['Ano','Primeiro movimento','Último movimento','Abas','Máximo linhas/aba','Eventos','Contas','Totais de conta','Sem total','Conta 642','Grupos','Débitos brutos','Créditos brutos','Sem contrapartida','Status','Fonte'], rows=coverage),
                        dict(name='Razões conciliação', headers=['Ano','Conta','Classificação razão','Nome','Status','Abertura razão','Abertura balancete','Dif. abertura','Débitos razão','Débitos balancete','Dif. débitos','Créditos razão','Créditos balancete','Dif. créditos','Final razão','Final balancete','Dif. final','Fonte'], rows=reconciliation)],
                metrics=metrics, checks=checks, pendencias=issues,
                report=[dict(title='Razões anuais — cobertura e conciliação', paragraphs=[f"Os cinco arquivos anuais foram indexados em {len(data['events']):,} eventos de razão, com origem rastreável por arquivo, aba e linha. As diferenças contra os balancetes estão discriminadas por conta; não foram feitos ajustes para forçar fechamento. Os razões detalham os registros e não substituem os valores oficiais dos balancetes.", 'Cada linha pertence a uma conta; o mesmo lote pode aparecer em contas recíprocas. A base não soma ECD, razão do disponível, passivo ou razão geral parcial aos anuais, evitando duplicação. A DRE anual e acumulada já está apurada.'])])


def _persist(data, output):
    """Regenerable local search index; no presentation workbook is produced."""
    events = data['events']
    # The existing writer expects source sections with unique IDs. In this
    # consolidated database each section retains its source year in its JSON.
    sections = []
    for year, p in data['years'].items():
        for s in p['sections']:
            sections.append({**s, 'secao_id_local': s['secao_id'], 'secao_id': len(sections)+1, 'ano_fonte': year, 'source': p['source']['source']})
    database = output / 'razoes_anuais.sqlite'
    parser.write_sqlite(database, events, sections, dict(fontes=data['source'], versao=VERSION))
    # Add annual provenance to the shared writer's schema and section linkage.
    with sqlite3.connect(database) as con:
        con.execute('ALTER TABLE eventos ADD COLUMN ano_fonte TEXT')
        con.execute('ALTER TABLE eventos ADD COLUMN id_local INTEGER')
        con.execute('ALTER TABLE eventos ADD COLUMN source TEXT')
        con.execute('ALTER TABLE eventos ADD COLUMN tipo_evento_cobertura TEXT')
        con.executemany('UPDATE eventos SET ano_fonte=?,id_local=?,source=?,tipo_evento_cobertura=? WHERE id=?', [(e['ano_fonte'],e['id_local'],e['source'],e['tipo_evento_cobertura'],e['id']) for e in events])
        con.execute('CREATE INDEX idx_ano_fonte_conta ON eventos(ano_fonte,codigo_conta,data)')
        con.execute('CREATE TABLE secao_origem (ano_fonte TEXT,secao_id_local INTEGER,secao_id INTEGER,PRIMARY KEY(ano_fonte,secao_id_local))')
        con.executemany('INSERT INTO secao_origem VALUES (?,?,?)', [(s['ano_fonte'],s['secao_id_local'],s['secao_id']) for s in sections])
        con.execute('ALTER TABLE eventos ADD COLUMN secao_global INTEGER')
        con.execute('UPDATE eventos SET secao_global=(SELECT s.secao_id FROM secao_origem s WHERE s.ano_fonte=eventos.ano_fonte AND s.secao_id_local=eventos.secao_id)')
        sqlite_count, sd, sc = con.execute('SELECT COUNT(*),SUM(debito_centavos),SUM(credito_centavos) FROM eventos').fetchone()
        integrity = con.execute('PRAGMA integrity_check').fetchone()[0]
    for old in output.glob('eventos-????-parte-*.jsonl'):
        old.unlink()
    chunks = []
    json_count = jd = jc = 0
    for year, p in data['years'].items():
        ev = p['events']
        for start in range(0,len(ev),parser.CHUNK_SIZE):
            chunk = ev[start:start+parser.CHUNK_SIZE]
            path = output / f'eventos-{year}-parte-{start//parser.CHUNK_SIZE+1:03}.jsonl'
            with path.open('w',encoding='utf-8',newline='\n') as f:
                for e in chunk:
                    f.write(json.dumps(e,ensure_ascii=False,separators=(',',':'))+'\n')
            chunks.append(dict(arquivo=path.name,eventos=len(chunk),ano=year,sha256=_hash(path),bytes=path.stat().st_size))
            # Independent read-back detects missing/truncated fragment rows.
            with path.open(encoding='utf-8') as f:
                for line in f:
                    e=json.loads(line);json_count+=1;jd+=e['debito_centavos'];jc+=e['credito_centavos']
    original_count=sum(p['source_events'] for p in data['years'].values())
    total_d=sum(e['debito_centavos'] for e in events);total_c=sum(e['credito_centavos'] for e in events)
    ok=original_count==len(events)==sqlite_count==json_count and total_d==sd==jd and total_c==sc==jc and integrity=='ok'
    catalog=dict(schema_versao=1,parser_versao=VERSION,modulo_sha256=_hash(__file__),gerado_em_utc=datetime.now(timezone.utc).isoformat(),
                 fontes=data['source'],qualidade=data['quality'],metadados={year:p['metadata'] for year,p in data['years'].items()},eventos=len(events),
                 por_ano=parser.aggregate(events,['ano_fonte']),
                 por_grupo=parser.aggregate(events,['ano_fonte','grupo_1','grupo_2','grupo_3']),
                 por_conta=parser.aggregate(events,['ano_fonte','codigo_conta','classificacao','nome_conta']),
                 verificacoes=dict(status='OK' if ok else 'DIVERGÊNCIA',eventos_origem=original_count,eventos_sqlite=sqlite_count,eventos_jsonl=json_count,debito_centavos=total_d,credito_centavos=total_c,sqlite_integrity=integrity),
                 arquivos_jsonl=chunks,avisos=['Fontes anuais são mutuamente exclusivas por período; não somar com ECD nem outros razões sobrepostos.','Razão por conta não é diário completo; contrapartida ausente é nula, sem inferência.','Sinal numérico de saldo preservado e conferido pela recorrência D+/C−; formato visual também preservado.','Diferenças frente ao balancete e entre exercícios são mantidas em conciliacao.json, sem ajustes presumidos.'])
    parser.dump_json(output/'catalogo.json',catalog)
    files=[database,output/'catalogo.json',output/'conciliacao.json']
    parser.dump_json(output/'manifesto.json',dict(versao=VERSION,fontes=data['source'],arquivos=[dict(arquivo=p.name,sha256=_hash(p),bytes=p.stat().st_size) for p in files]+chunks))
    (output/'.gitignore').write_text('*.sqlite\n*.sqlite-*\neventos-*.jsonl\n__pycache__/\n',encoding='utf-8')
    (output/'README.md').write_text(f'''# Razões anuais CSG — índice e controles

Fontes preservadas: `balancetes/Razão2022.xls` a `Razão2026.xls`; conversões em `qa/razoes_anuais/RazãoYYYY.xlsx`. São {len(events):,} eventos de conta, divididos em {len(chunks)} fragmentos JSONL de até 5.000 eventos. Valores em centavos inteiros, histórico integral e origem por arquivo/SHA-256, aba/linha/folha. O ano da fonte é sempre explícito; classificação pertence à época do arquivo.

Os cinco arquivos têm totais finais de todas as contas, assinaturas ao final e menos de 65.536 linhas por aba, sem indício do corte observado no razão geral anterior. **Em 2024 há 479 linhas de implantação, envolvendo 477 contas, no lote23308 de31/12/2024, histórico SALDO FINAL EM31/12/2024.** Débitos e créditos desse lote são R$4.381.414,59 cada. Esses registros são preservados e marcados em `tipo_evento_cobertura`; não equivalem a fluxo econômico identificado nem demonstram as operações anteriores à implantação. Detalhes e contas afetadas constam de `qualidade.2024.implantacoes_saldos` no catálogo.

`catalogo.json` apresenta cobertura, presença da conta 642 e grupos, contagens/totais por ano/grupo/conta, metadados e QA. `conciliacao.json` compara abertura, débitos, créditos e final por código de conta aos balancetes oficiais de cada ano; preserva mudanças de classificação, contas sem correspondência e continuidade divergente. Contas com seções repetidas são sinalizadas sem soma automática. A comparação identifica diferenças; encerramentos, filiais e reimplantação não são ajustados por suposição.

`razoes_anuais.sqlite` tem tabelas `eventos`, `contas`, `secoes`, `secao_origem`, `fonte` e busca FTS5 `busca`. `eventos.secao_id` é local ao ano; `secao_global` liga à tabela `secoes`, cujo JSON inclui `ano_fonte` e `secao_id_local`. Cada evento tem `source`, `ano_fonte`, `id_local`, identificador global, conta/classificação/nome, data/lote, histórico completo/partes, contrapartida bruta/código, débitos/créditos/saldos em centavos, formato e sinal de saldo, e origem. Arrays ficam serializados em colunas `_json` no SQLite.

**Não somar esta base à ECD, aos razões de disponível/ativo/passivo ou ao razão geral parcial**, que são sobrepostos. Cada evento pertence a uma conta e não equivale a uma partida completa. Transferências internas e contrapartidas recíprocas continuam nos valores brutos. Campo Cta.C.Part. ausente fica nulo; não é preenchido por inferência. Não se somam saldos de datas distintas. A DRE anual e acumulada já está apurada.

Regerar, após converter os XLS em XLSX preservando as fontes:

```sh
cd clientes/credit-578/levantamento-financeiro
python mod_razoes.py
```

Requer Python 3, openpyxl e Poppler (`pdftotext`, para balancetes). `load(base,out)` usa cache por SHA-256 original+convertido+parser em `qa/razoes_anuais/cache` e memoização no processo; não é necessário repetir a extração para cada módulo. `build(base,out)` gera controles e este índice. Os argumentos opcionais são `--base` e `--out`. SQLite/JSONL são ignorados no Git; script, README, catálogo, conciliação e manifesto são versionáveis. Nenhum serviço remoto é acessado, nem são modificadas fontes/relatórios.

QA de gravação: origem = memória = SQLite = JSONL; totais D/C iguais; integridade SQLite `{integrity}`; resultado **{'OK' if ok else 'DIVERGÊNCIA'}**. Verificações de saldo e totais de conta constam no catálogo por fonte. Datas globais não garantem cobertura de toda conta: consulte a linha correspondente no catálogo.
''',encoding='utf-8')
    if not ok:
        raise RuntimeError('QA do índice anual falhou; veja catalogo.json')
    return catalog


if __name__=='__main__':
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--base',type=Path,default=Path(__file__).resolve().parent.parent)
    cli.add_argument('--out',type=Path,default=Path(__file__).resolve().parent)
    args=cli.parse_args()
    result=build(args.base,args.out)
    print(json.dumps(dict(events=result['metrics']['events'],coverage=result['metrics']['coverage'],reconciliation=result['metrics']['reconciliation']),ensure_ascii=False))
