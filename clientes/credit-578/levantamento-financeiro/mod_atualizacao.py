"""Comparação documental das duas versões do balancete de jan-set/2026.

As diferenças são revisões do mesmo período, não novos fluxos. Não atribui
causa às alterações sem o razão atualizado e preserva ausências como ausências.
"""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from mod_contabilidade import parse_balancete

D = Decimal
ZERO = D('0.00')
OLD = 'Balancete 2026- posicao em 30-09.pdf'
NEW = 'balancetes/Balancete-ja-set-2026.pdf'


def brl(v):
    text = f'{abs(v):,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    return '(' + text + ')' if v < 0 else text


def metrics_for(rows):
    by = {r['code']: r for r in rows}
    value = lambda code: by[code]['balance']
    result = -value('402') - value('269')
    financial = -value('642') - value('1113') - value('639')
    return {
        'ativo': value('1'),
        'disponivel': value('3'),
        'carteira': value('12'),
        'outros_creditos': value('18'),
        'emprestimos_socios': value('1928'),
        'emprestimos_arthur': value('1930'),
        'emprestimos_gustavo': value('2388'),
        'exigivel': -value('150'),
        'fornecedores': -value('164'),
        'tributarias': -value('169'),
        'trabalhistas_previdenciarias': -value('185'),
        'outras_obrigacoes': -value('200'),
        'jane': -value('1113'),
        'lair': -value('639'),
        'debentures': -value('642'),
        'juros_debentures': value('369'),
        'pl_registrado': -value('242'),
        'resultado': result,
        'pl_com_resultado': -value('242') + result,
        'receita_bruta': -next(r['balance'] for r in rows if r['classification'] == '4.1.1'),
        'deducoes': next(r['balance'] for r in rows if r['classification'] == '4.1.2'),
        'receitas_grupo4': -value('402'),
        'custos_grupo3': value('269'),
        'operacao_credito': next(r['balance'] for r in rows if r['classification'] == '3.1'),
        'despesas_operacionais': next(r['balance'] for r in rows if r['classification'] == '3.2'),
        'divida_financeira': financial,
        'divida_financeira_liquida': financial - value('3'),
    }


def build(base: Path, out: Path):
    base = Path(base)
    old_rows = parse_balancete(base / OLD)
    new_rows = parse_balancete(base / NEW)
    old = {r['code']: r for r in old_rows}
    new = {r['code']: r for r in new_rows}
    old_m = metrics_for(old_rows)
    new_m = metrics_for(new_rows)
    checks = []
    fields = [('opening', 'Saldo anterior D+/C-'), ('debit', 'Débitos'),
              ('credit', 'Créditos'), ('balance', 'Saldo final D+/C-')]
    diff_rows = []
    changed_codes = set()
    added, removed = sorted(new.keys() - old.keys()), sorted(old.keys() - new.keys())
    for code in sorted(old.keys() | new.keys(), key=int):
        before, after = old.get(code), new.get(code)
        account = after or before
        old_source = f'{OLD} | conta {code} ({before["classification"]}) | p.{before["page"]}' if before else 'Conta não consta na versão anterior'
        new_source = f'{NEW} | conta {code} ({after["classification"]}) | p.{after["page"]}' if after else 'Conta não consta na versão atualizada'
        if before is None or after is None:
            state = 'INCLUÍDA NA VERSÃO' if before is None else 'NÃO CONSTA NA VERSÃO ATUALIZADA'
            for field, label in fields:
                diff_rows.append([code, account['classification'], account['description'], label,
                                  float(before[field]) if before else None,
                                  float(after[field]) if after else None,
                                  None, state + ' - motivo PENDENTE', old_source, new_source])
            continue
        for field, label in fields:
            if before[field] != after[field]:
                changed_codes.add(code)
                diff_rows.append([code, account['classification'], account['description'], label,
                                  float(before[field]), float(after[field]), float(after[field] - before[field]),
                                  'EXPLICADO: comparação de versões; motivo do lançamento PENDENTE', old_source, new_source])
        for field, label in [('classification', 'Classificação da conta'), ('description', 'Descrição da conta')]:
            if before[field] != after[field]:
                changed_codes.add(code)
                diff_rows.append([code, account['classification'], account['description'], label,
                                  before[field], after[field], None,
                                  'EXPLICADO: alteração de cadastro entre versões', old_source, new_source])

    for label, rows, source, metric in [('anterior', old_rows, OLD, old_m), ('atualizada', new_rows, NEW, new_m)]:
        failures = [r for r in rows if r['opening'] + r['debit'] - r['credit'] != r['balance']]
        checks.append({'teste': f'Atualização 2026: contas com anterior + D - C diferente do final ({label})',
                       'ano': '2026 jan-set', 'calculado': len(failures), 'referencia': 0, 'diferenca': len(failures),
                       'status': 'OK' if not failures else 'DIVERGÊNCIA', 'fonte': source + ' | todas as contas extraídas'})
        checks.append({'teste': f'Atualização 2026: códigos únicos ({label})', 'ano': '2026 jan-set',
                       'calculado': len({r['code'] for r in rows}), 'referencia': len(rows),
                       'diferenca': len({r['code'] for r in rows}) - len(rows),
                       'status': 'OK' if len({r['code'] for r in rows}) == len(rows) else 'DIVERGÊNCIA',
                       'fonte': source + ' | coluna Código'})
        calculated = metric['exigivel'] + metric['pl_com_resultado']
        delta = metric['ativo'] - calculated
        checks.append({'teste': f'Atualização 2026: Ativo = exigível + PL incluindo resultado ({label})',
                       'ano': '30/09/2026', 'calculado': float(metric['ativo']), 'referencia': float(calculated),
                       'diferenca': float(delta), 'status': 'OK' if delta == 0 else 'DIVERGÊNCIA',
                       'fonte': source + ' | contas 1,150/2.1,242/2.4,269/3 e402/4'})
    bridge_difference = ((new_m['pl_com_resultado'] - old_m['pl_com_resultado'])
                         - (new_m['ativo'] - old_m['ativo'] - new_m['exigivel'] + old_m['exigivel']))
    checks.append({'teste': 'Atualização 2026: variação do PL conciliada à variação do ativo e exigível',
                   'ano': '30/09/2026, comparação de versões',
                   'calculado': float(new_m['pl_com_resultado'] - old_m['pl_com_resultado']),
                   'referencia': float(new_m['ativo'] - old_m['ativo'] - new_m['exigivel'] + old_m['exigivel']),
                   'diferenca': float(bridge_difference),
                   'status': 'OK' if bridge_difference == 0 else 'DIVERGÊNCIA',
                   'fonte': OLD + '; ' + NEW + ' | 1,2.1,2.4,3/4; revisão do mesmo período, não fluxo adicional'})

    specs = [
        ('Ativo total', 'ativo', '1 / código1'), ('Disponível', 'disponivel', '1.1.1 / código3'),
        ('Carteira / clientes', 'carteira', '1.1.2 / código12'), ('Outros créditos', 'outros_creditos', '1.1.3 / código18'),
        ('Empréstimos a sócios - ativo', 'emprestimos_socios', '1.2.5 / código1928'),
        ('Empréstimo a Arthur - ativo', 'emprestimos_arthur', '1.2.5.01.001 / código1930'),
        ('Empréstimo a Gustavo - ativo', 'emprestimos_gustavo', '1.2.5.01.002 / código2388'),
        ('Passivo exigível', 'exigivel', '2.1 / código150'), ('Fornecedores', 'fornecedores', '2.1.3 / código164'),
        ('Obrigações tributárias', 'tributarias', '2.1.4 / código169'),
        ('Obrigações trabalhistas/previdenciárias', 'trabalhistas_previdenciarias', '2.1.5 / código185'),
        ('Outras obrigações', 'outras_obrigacoes', '2.1.6 / código200'),
        ('Dívida com Jane', 'jane', '2.1.6.02.001 / código1113'), ('Dívida com Lair', 'lair', '2.1.6.02.001 / código639'),
        ('Debêntures', 'debentures', '2.1.7 / código642'),
        ('Juros de debêntures jan-set', 'juros_debentures', '3.2.2.05.001 / código369'),
        ('PL registrado no grupo2.4', 'pl_registrado', '2.4 / código242'),
        ('Resultado jan-set ainda em aberto', 'resultado', '4 líquido menos3 / códigos402,269'),
        ('PL incluindo resultado jan-set', 'pl_com_resultado', '2.4 + resultado4 menos3 / códigos242,402,269'),
        ('Receita bruta', 'receita_bruta', '4.1.1'), ('Deduções da receita', 'deducoes', '4.1.2'),
        ('Receitas líquidas do grupo4', 'receitas_grupo4', '4 / código402'),
        ('Custos/despesas do grupo3', 'custos_grupo3', '3 / código269'),
        ('Custo líquido da operação de crédito', 'operacao_credito', '3.1'),
        ('Despesas operacionais', 'despesas_operacionais', '3.2'),
        ('Dívida financeira', 'divida_financeira', '642 +1113 +639 / debêntures e mútuos'),
        ('Dívida financeira líquida', 'divida_financeira_liquida', '642 +1113 +639 menos3 / dívida menos disponível'),
    ]
    summary = [[label, float(old_m[key]), float(new_m[key]), float(new_m[key] - old_m[key]), OLD, NEW, account,
                'Posições alternativas do mesmo período; não somar. Causa dos ajustes PENDENTE de razão atualizado.']
               for label, key, account in specs]
    summary.append(['Caixa geral credor da versão anterior', float(old['5']['balance']) if '5' in old else None,
                    'Conta não consta no novo PDF' if '5' not in new else float(new['5']['balance']), None,
                    OLD, NEW, '1.1.1.01.001 / código5',
                    'Alerta antigo substituído pela leitura da versão atualizada; ausência da conta não comprova recebimento ou liquidação.'])
    report = [{'title': 'Atualização da fonte de2026 - comparação das versões', 'paragraphs': [
        f'O arquivo atualizado cobre exatamente 01/01/2026 a 30/09/2026, consolidado 578/592. Substitui a versão anteriormente usada para essa mesma data-base; as diferenças não representam um novo período nem devem ser somadas aos fluxos. Fontes: {OLD} e {NEW}, cabeçalhos e contas por código; CNPJ 46.788.467/0001-49.',
        f'O ativo passou de R$ {brl(old_m["ativo"])} para R$ {brl(new_m["ativo"])} e o exigível de R$ {brl(old_m["exigivel"])} para R$ {brl(new_m["exigivel"])}. O resultado jan-set passou de R$ {brl(old_m["resultado"])} para R$ {brl(new_m["resultado"])}. O PL contábil incluindo o resultado é agora R$ {brl(new_m["pl_com_resultado"])}. Fontes: {OLD} e {NEW}, contas1,150/2.1,242/2.4,269/3 e402/4.',
        f'A dívida com Jane aumentou R$ {brl(new_m["jane"] - old_m["jane"])}; debêntures e juros de debêntures não mudaram. O disponível passou para R$ {brl(new_m["disponivel"])} e a carteira para R$ {brl(new_m["carteira"])}. Fontes: {OLD} e {NEW}, contas1113,642,369,3/1.1.1 e12/1.1.2.',
        f'As principais alterações no resultado estão na receita de cessão (conta605), na amortização de cessão (272), e nas despesas operacionais (grupo3.2). O custo líquido do grupo3.1 caiu de R$ {brl(old_m["operacao_credito"])} para R$ {brl(new_m["operacao_credito"])}; isso não prova economia de caixa, pois houve revisão simultânea da receita e da amortização. O motivo de cada lançamento depende do razão atualizado. Fontes: {OLD} e {NEW}, mesmas contas; detalhamento na aba Diferenças contas2026.',
        f'Foram extraídas {len(old_rows)} contas na versão anterior e {len(new_rows)} na versão atualizada. {len(changed_codes)} códigos comuns apresentam alteração de valor ou cadastro; {len(added)} códigos constam apenas no novo arquivo e {len(removed)} apenas no anterior. O saldo credor de Caixa Geral do relatório anterior não consta no novo PDF e não deve continuar sendo apresentado como saldo da versão atualizada. Isso não autoriza presumir liquidação. Fontes: {OLD} e {NEW}, coluna Código e contas 4/5; a versão atualizada fecha por bancos e aplicações de 1.1.1.'
    ]}]
    pending = [{'item': 'Razão atualizado e lançamentos que explicam a revisão do balancete de2026',
                'motivo': 'Identificar a causa das mudanças de receita de cessão, amortização, despesas, dívida com Jane, créditos da carteira e desaparecimento da rubrica Caixa Geral; comparar versões não prova novo ingresso/pagamento.',
                'fonte': OLD + '; ' + NEW + ' | contas605,272,3.2,1113,1.1.2 e4/5'}]
    return {'sheets': [
        {'name': 'Atualização 2026', 'headers': ['Medida', 'Versão anterior R$', 'Versão atualizada R$', 'Diferença R$', 'Fonte anterior', 'Fonte atualizada', 'Contas', 'Método / ressalva'], 'rows': summary},
        {'name': 'Diferenças contas 2026', 'headers': ['Código', 'Classificação', 'Descrição', 'Campo comparado', 'Valor anterior R$ / texto', 'Valor atualizado R$ / texto', 'Diferença R$', 'Situação', 'Fonte anterior', 'Fonte atualizada'], 'rows': diff_rows},
    ], 'checks': checks, 'pendencias': pending, 'report': report,
        'metrics': {'old': {k: float(v) for k, v in old_m.items()}, 'new': {k: float(v) for k, v in new_m.items()},
                    'difference': {k: float(new_m[k] - old_m[k]) for k in new_m},
                    'old_account_count': len(old_rows), 'new_account_count': len(new_rows),
                    'changed_common_codes': len(changed_codes), 'added_codes': added, 'removed_codes': removed,
                    'comparison_rows': len(diff_rows), 'old_source': OLD, 'new_source': NEW}}
