#!/usr/bin/env python3
"""Levantamento CSG 14/06/2022 a 30/09/2026, com trilha de fontes.

Uso: python3 gerar_levantamento_csg.py [--inventario] [--somente-dados]
As fontes são lidas na pasta pai. Nenhum documento original é alterado.
O autor da planilha é gerar_planilha.mjs (Artifact Tool); este script o executa.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from datetime import date
from collections import defaultdict
from decimal import Decimal
from xml.sax.saxutils import escape

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
YEARS=[str(x) for x in range(2022,2027)]
RUNTIME=Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies'

def brl(v):
    s=f'{abs(v):,.2f}'.replace(',','X').replace('.',',').replace('X','.')
    return f'({s})' if v<0 else s

def dump(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,default=lambda x:float(x) if isinstance(x,Decimal) else str(x)),encoding='utf8')

def inventory():
    rows=[];groups=defaultdict(list);exports=[]
    for p in sorted(BASE.rglob('*')):
        if not p.is_file() or HERE in p.parents or p.name.startswith(('.', '~')) or '__pycache__' in p.parts:continue
        if p.suffix.lower() not in ['.pdf','.txt','.xlsx','.xlsm','.xls','.docx','.csv','.py','.ods']:continue
        data=p.read_bytes();sha=hashlib.sha256(data).hexdigest();rel=str(p.relative_to(BASE));groups[sha].append(rel)
        dates=[]
        if p.name.upper().startswith('CONTABIL'):
            text=data.decode('latin1')
            for d in re.findall(r'\|6100\|(\d{2}/\d{2}/\d{2,4})\|',text):
                dd,mm,yy=d.split('/');dates.append(f'{yy if len(yy)==4 else "20"+yy}-{mm}-{dd}')
            exports.append((rel,min(dates) if dates else '',max(dates) if dates else '',sha))
        kind='Fonte auxiliar'
        if '/DOCUMENTOS CREDIT/' in '/'+rel:kind='Demonstração anual Domínio'
        elif rel=='balancetes/Balancete-ja-set-2026.pdf':kind='Posição contábil atualizada 30/09/2026: fonte adotada'
        elif p.name=='Balancete 2026- posicao em 30-09.pdf':kind='VERSÃO ANTERIOR: somente comparação; não compõe os saldos atuais'
        elif 'sped_diario' in p.name:kind='ECD 2025: plano, saldos e lançamentos'
        elif rel.startswith('ccb/') or rel.startswith('_arquivo/zips/CCB CLIENTES'):kind='Documentos de crédito; aquisições até 09/2026 integradas; outubro fora da data-base'
        elif p.name in ['05.2026.xlsx','06.2026.xlsx']:kind='Extrato bancário parcial + cobranças liquidadas'
        elif 'CONTABIL' in p.name.upper():kind='Arquivo de importação; não equivale ao diário completo'
        elif p.name.startswith(('DFC','DMPL')):kind='Referência; não usar como validação'
        rows.append([rel,kind,len(data),sha,min(dates) if dates else '',max(dates) if dates else '',''])
    for row in rows:
        row[-1]='ÚNICO' if len(groups[row[3]])==1 else 'Mesmo conteúdo: '+'; '.join(groups[row[3]])
    coverage=[
        ['2022','BP, DRE, balancete anual e certificados de debêntures; conciliação bancária confirmada pelo escritório','Exportar razão analítico para classificar fluxos; carteira UY3; escritura original e vínculo dos títulos aos lançamentos','publicacao-balancos/DOCUMENTOS CREDIT/*2022.pdf; outras informações; Premissas_confirmadas.json'],
        ['2023','BP, DRE, balancete anual e certificados históricos; conciliação bancária confirmada','Razão analítico para classificar as movimentações e posição de carteira por parcela; primeiro aditamento','publicacao-balancos/DOCUMENTOS CREDIT/*2023.pdf; outras informações'],
        ['2024','BP, DRE, balancete anual, aditamentos e boletins com importância realizada','Vincular documentos aos lançamentos por titular e data; razão analítico para abertura dos fluxos; carteira por parcela','publicacao-balancos/DOCUMENTOS CREDIT/*2024.pdf; outras informações'],
        ['2025','BP, DRE, balancete, ECD completa, custos gerenciais; CCBs desde abril; bancos conciliados conforme escritório','Posição de parcelas em aberto; histórico de aquisições jan-mar/2025; abertura pontual de lançamentos mistos','fiscal/dominio/sped_diario00578.txt; ccb/; fiscal/planilhas/CONTROLE - CUSTOS 2025.xlsx'],
        ['2026 jan-set','Balancete fechado; importações de todos os meses; CCBs jan-set inclusive pacotes arquivados; bancos conciliados','Razão analítico para classificar fluxos e vincular plano de importação ao plano final; posição aberta por parcela','balancetes/Balancete-ja-set-2026.pdf; CONTABIL*; ccb/; _arquivo/zips/; Premissas_confirmadas.json'],
        ['2026 outubro','Nenhum fechamento de outubro identificado nas fontes','Balancete fechado e razão de outubro, se já concluídos','CONTABIL de 20/10/2026 contém lançamentos até setembro; data de exportação não altera data-base']]
    report=['# Inventário das fontes - CSG','', 'Data-base mantida em 30/09/2026. A fonte de 2026 é balancetes/Balancete-ja-set-2026.pdf, indicado pelo cliente como atualizado. O arquivo anterior é mantido somente para comparar revisões do mesmo período. A data da exportação não é a data dos lançamentos.','']
    for period,have,missing,source in coverage:report+=['## '+period,have,'PENDENTE: '+missing,'Fonte: '+source,'']
    report+=['## Integridade e duplicatas',f'{len(rows)} arquivos inventariados; hashes SHA-256 e cópias idênticas na aba Fontes. Arquivos de importação não são somados a lançamentos da ECD no mesmo período.','DFC e DMPL do Domínio são referência; não controlam o levantamento.','Identificação: CNPJ 46.788.467/0001-49; NIRE correto 43.300.068.854. O NIRE divergente do cabeçalho não foi utilizado.']
    (HERE/'Inventario_fontes.md').write_text('\n\n'.join(report),encoding='utf8')
    return [dict(name='Cobertura',headers=['Período','Fontes presentes','Lacunas','Fonte'],rows=coverage),dict(name='Fontes',headers=['Arquivo','Cobertura / uso','Tamanho bytes','SHA256','Primeiro lançamento','Último lançamento','Duplicidade de conteúdo'],rows=rows)]

def synthesis(accounting):
    m=accounting['metrics']['years'];v=m['2026']
    annual=[['Ativo total','ativo','1'],['Disponível','disponivel','1.1.1'],['Carteira contábil','carteira','1.1.2'],['Debêntures','debentures','2.1.7'],['Dívida com partes relacionadas (mútuos)','partes_relacionadas','2.1.6'],['Outras obrigações','outras_obrigacoes','2.1.6'],['Fornecedores','fornecedores','2.1.3'],['Passivo exigível total','exigivel','2.1 + eventual 2.2'],['PL registrado','pl_registrado','2.4'],['Resultado do período','resultado','3 e 4 / DRE'],['PL incluindo resultado do período','pl_com_resultado','2.4 e resultado em aberto']]
    headers=['Item','2022','2023','2024','2025','2026 jan-set','Acumulado / posição atual','Fonte e conta','Ressalva']
    rows=[]
    for label,key,acc in annual:
        vals=[m[y][key] for y in YEARS];accum=sum(vals) if key=='resultado' else vals[-1]
        rows.append([label,*vals,accum,'BP/balancetes e DRE de cada ano; '+acc,'Saldos patrimoniais: coluna final é posição de 30/09/2026; resultado: soma dos períodos'])
    rows.extend([
        ['Custo histórico por competência',*[m[y]['custo_total'] for y in YEARS],sum(m[y]['custo_total'] for y in YEARS),'DRE anuais + balancete2026; grupo3 e deduções4.1.2','Despesa reconhecida; não é total de caixa gasto nem soma de aquisições de ativos'],
        ['Receita bruta acumulada',*[m[y]['receita_bruta'] for y in YEARS],sum(m[y]['receita_bruta'] for y in YEARS),'DRE anuais + balancete2026; 4.1.1','Não confundir com recebimentos'],
        ['Receitas totais antes de deduções',*[m[y]['receitas_totais'] for y in YEARS],sum(m[y]['receitas_totais'] for y in YEARS),'DRE anuais + balancete2026; grupo4 antes de deduções4.1.2','Inclui financeiras e outras; menos custo histórico = resultado acumulado'],
    ])
    from mod_contabilidade import parse_balancete, norm
    current_accounts=parse_balancete(BASE/'balancetes/Balancete-ja-set-2026.pdf')
    loan=next(r for r in current_accounts if r['classification']=='1.2.5')
    gus=next(r for r in current_accounts if r['classification']=='1.2.5.01.002')
    pdd=[r for r in current_accounts if re.search(r'PDD|DUVIDOS|PERDA.*CREDIT|CREDIT.*PERDA|PERDA.*ESPERAD',norm(r['description']))]
    commission_sources=[];commission_count=0;seen=set()
    for p in [BASE/'fiscal/dominio/sped_diario00578.txt',*sorted(BASE.rglob('CONTABIL*.TXT')),*sorted(BASE.rglob('CONTABIL*.txt'))]:
        sha=hashlib.sha256(p.read_bytes()).hexdigest()
        if sha in seen:continue
        seen.add(sha);lines=p.read_bytes().decode('latin1').splitlines()
        count=sum('COMISS' in norm(line) for line in lines if line.startswith(('|I050|','|I250|','|6100|')))
        commission_count+=count;commission_sources.append(str(p.relative_to(BASE)))
    diagnostic=[['Empréstimos a sócios: saldo anterior R$',float(loan['opening']),'balancetes/Balancete-ja-set-2026.pdf p.15','1928 / 1.2.5','Ativo, não dívida da empresa'],['Empréstimos a sócios: débitos jan-set R$',float(loan['debit']),'balancetes/Balancete-ja-set-2026.pdf p.15','1928 / 1.2.5','Movimentação contábil; não presumir toda como desembolso bancário sem razão'],['Empréstimos a sócios: créditos jan-set R$',float(loan['credit']),'balancetes/Balancete-ja-set-2026.pdf p.15','1928 / 1.2.5','Créditos não provam recebimento em caixa'],['Empréstimos a sócios: saldo final R$',float(loan['balance']),'balancetes/Balancete-ja-set-2026.pdf p.15','1928 / 1.2.5','Arthur: saldo final; Gustavo: movimentos compensados'],['PDD / perdas de crédito: conta explícita','Não localizada' if not pdd else '; '.join(r['description'] for r in pdd),'balancetes/Balancete-ja-set-2026.pdf; plano completo extraído','1.1.2; grupos de resultado','Ausência de rubrica explícita não comprova perda zero ou ausência de compensação em outra conta'],['Comissões: pesquisa documental',f'{commission_count} linhas com COMISS nos planos/históricos disponíveis','; '.join(commission_sources),'I050/I250 e 6100; categorias grupo3','Comissões embutidas em serviços e anos sem razão completo: PENDENTE; zero na categoria não prova ausência econômica']]
    final=[]
    def add(item,value,source,note=''):final.append([item,value,source,note])
    src='balancetes/Balancete-ja-set-2026.pdf'
    add('Caixa e aplicações no disponível R$',v['disponivel'],src+' | 1.1.1','Saldo conciliado conforme confirmação do escritório; ver Premissas_confirmadas.json')
    add('Carteira contábil R$',v['carteira'],src+' | 1.1.2','Saldo não equivale a valor recuperável confirmado')
    add('Carteira recuperável real R$','PENDENTE',src+' | 1.1.2; carteira e baixas','Sem posição completa por parcela e premissas de perda sustentadas')
    add('Outros ativos contábeis R$',round(v['ativo']-v['disponivel']-v['carteira'],2),src+' | 1 menos1.1.1 menos1.1.2','Inclui ativos sem liquidez imediata; realizabilidade a comprovar')
    add('Ativo realizável real R$','PENDENTE','Caixa + carteira recuperável + outros créditos realizáveis','Não calculado sem prova de recuperabilidade')
    add('Dívida contábil total R$',v['exigivel'],src+' | passivo exigível','Saldo contábil; juros contratuais adicionais e exigibilidade real PENDENTES')
    add('Dívida contratual atualizada real R$','PENDENTE','Escrituras/controle debêntures e contratos de mútuo','Não presumir saldo contábil igual a obrigação contratual recalculada')
    add('PL contábil com resultado de 2026 R$',v['pl_com_resultado'],src+' | 2.4 + resultado grupos 3/4','Resultado jan-set ainda em aberto no balancete')
    add('PL ajustado real R$','PENDENTE','Ativo realizável real menos dívida contratual atualizada','Déficit econômico real não quantificável com fontes atuais')
    add('Déficit patrimonial contábil R$',max(0,-v['pl_com_resultado']),src+' | ativo menos exigível','Antes de perdas adicionais da carteira e ajustes contratuais; não é orçamento de aporte')
    add('Falta para quitar debêntures + mútuos usando só disponível R$',v['debentures']+v['partes_relacionadas']-v['disponivel'],src+' | 2.1.7 + mútuos2.1.6 menos1.1.1','Comparação de saldos; não representa valor vencido hoje')
    add('Carteira contábil + disponível menos debêntures e mútuos R$',v['carteira']+v['disponivel']-v['debentures']-v['partes_relacionadas'],src+' | 1.1.1+1.1.2-2.1.7-mútuos2.1.6','Antes dos demais passivos; carteira sem desconto de perdas')
    add('Prazo médio carteira x dívida','PENDENTE','Cronogramas por parcela e por titular/contrato','Amostra contratual não representa estoque atual')
    add('Ponto de equilíbrio mensal simplificado R$',round((v['estrutura']-v['deducoes']-v['ir_csll']+v['juros_debentures'])/9,2),src+' | estrutura menos deduções4.1.2 e IR/CSLL + JUROS DEBÊNTURES','ESTIMADO: média jan-set; antes de tributos sobre receita, custos variáveis e perdas; não é ponto de equilíbrio completo')
    add('Ponto de equilíbrio completo R$','PENDENTE','Margem de contribuição e perdas da carteira','Faltam mix e perdas sustentadas')
    # Indicadores preservam seus denominadores; recuperabilidade não é substituída por carteira bruta.
    indicators=[]
    specs=[('Dívida / ativo',lambda a:a['exigivel']/a['ativo'],'Exigível / ativo total'),('Dívida / carteira contábil',lambda a:a['exigivel']/a['carteira'],'Exigível / carteira sem PDD validada'),('Liquidez imediata contábil',lambda a:a['disponivel']/a['exigivel'],'Disponível / exigível (todo classificado circulante no Domínio)'),('Liquidez corrente pelo Domínio',lambda a:a['ativo_circulante']/a['exigivel'],'AC / passivo circulante; prazo real PENDENTE'),('Dívida financeira líquida R$',lambda a:a['divida_financeira']-a['disponivel'],'Debêntures + mútuos menos disponível'),('Cobertura nominal de dívida pela carteira',lambda a:a['carteira']/a['exigivel'],'Carteira contábil / exigível; não é cobertura recuperável')]
    for label,fn,rule in specs:
        vals=[fn(m[y]) for y in YEARS];indicators.append([label,*vals,vals[-1],src+' e BP/balancetes anuais |1;1.1.1;1.1.2;2.1',rule])
    indicators.append(['Cobertura da dívida pela carteira recuperável',*(['PENDENTE']*6),'Relatório de carteira por parcela |1.1.2','Sem base para perdas esperadas'])
    indicators.append(['Custo médio contratual da dívida',*(['PENDENTE']*6),'Contratos de mútuo e escritura/controle debêntures |2.1.6;2.1.7','Não substituir custo de toda dívida pela taxa das debêntures'])
    # Ponte patrimonial exata: não finge uma DFC operacional sem eliminar eventos não monetários.
    loan_diff=float(loan['opening']+loan['debit']-loan['credit']-loan['balance'])
    bridge=[];checks=[dict(teste='Empréstimos a sócios: anterior + débitos - créditos = final',ano='2026 jan-set',calculado=float(loan['opening']+loan['debit']-loan['credit']),referencia=float(loan['balance']),diferenca=loan_diff,status='OK' if abs(loan_diff)<.01 else 'DIVERGÊNCIA',fonte='balancetes/Balancete-ja-set-2026.pdf | 1928 /1.2.5')];prev={'disponivel':0,'ativo':0,'exigivel':0,'pl_com_resultado':0}
    for y in YEARS:
        a=m[y];result=a['resultado'];other_assets=a['ativo']-a['disponivel'];old_other=prev['ativo']-prev['disponivel']
        delta_assets=other_assets-old_other;delta_liab=a['exigivel']-prev['exigivel'];other_pl=a['pl_com_resultado']-prev['pl_com_resultado']-result
        calc=prev['disponivel']+result-delta_assets+delta_liab+other_pl
        bridge.append([int(y),prev['disponivel'],result,-delta_assets,delta_liab,other_pl,calc,a['disponivel'],round(calc-a['disponivel'],2),'Ponte patrimonial; sem segregação operacional/investimento/financiamento',f'BP/balancete {y}; 1,1.1.1,2.1,2.4,grupos 3/4'])
        checks.append(dict(teste='Ponte patrimonial indireta = disponível (não DFC completa)',ano=y,calculado=calc,referencia=a['disponivel'],diferenca=round(calc-a['disponivel'],2),status='OK' if abs(calc-a['disponivel'])<.011 else 'DIVERGÊNCIA',fonte=f'BP/balancete {y}; 1,1.1.1,2.1,2.4,3/4'))
        prev=a
    economic=[]
    for label,key in [('Resultado contábil','resultado')]:economic.append([label,*[m[y][key] for y in YEARS],sum(m[y][key] for y in YEARS),'DRE2022-25 e balancete2026 | grupos 3/4','Confirmado por competência'])
    for label,note in [('(-) Perda esperada adicional da carteira','PENDENTE: posição por parcela, recuperações e premissas de perda'),('(-) Juros contratuais não apropriados','PENDENTE: controle individual e recálculo contratual'),('(=) Resultado econômico ajustado','Não igualar ao resultado contábil enquanto faltam ajustes')]:economic.append([label,*(['PENDENTE']*6),'Carteira1.1.2; debêntures2.1.7; mútuos2.1.6',note])
    report=[{'title':'Cruzamento final - situação patrimonial e financeira','paragraphs':[
        f'Em 30/09/2026, o ativo contábil de R$ {brl(v["ativo"])} é inferior ao passivo exigível de R$ {brl(v["exigivel"])}. O déficit patrimonial contábil é de R$ {brl(-v["pl_com_resultado"])}. Fonte: {src}, contas 1,2.1 e 2.4, com inclusão do resultado em aberto dos grupos 3/4.',
        f'Debêntures de R$ {brl(v["debentures"])} e mútuos de R$ {brl(v["partes_relacionadas"])} somam mais que o disponível de R$ {brl(v["disponivel"])}. A diferença para liquidar essas dívidas usando apenas o disponível é de R$ {brl(v["debentures"]+v["partes_relacionadas"]-v["disponivel"])}. Fonte: {src}, contas 2.1.7,2.1.6 e 1.1.1. Isso não prova que todo esse montante esteja vencido hoje.',
        'A empresa apresenta insuficiência patrimonial na base contábil. A solvência econômica, a capacidade de pagar nas datas contratadas e o déficit real permanecem PENDENTES: falta validar a carteira recuperável e recalcular as obrigações por contrato. Não se pode afirmar solvência apenas porque existe carteira registrada.',
        'O PL ajustado real não foi calculado com perda zero presumida. A falta de conta explícita de provisão não prova ausência de perdas econômicas. Também não se presumiram juros dos mútuos iguais a zero por falta de contrato.',
        'O ponto de equilíbrio simplificado usa a média de estrutura e juros de debêntures de janeiro a setembro. Está marcado ESTIMADO e não inclui margem de contribuição, tributos variáveis, perdas de crédito nem eventuais encargos dos mútuos. O ponto de equilíbrio completo é PENDENTE.'
        ,f'O passivo exigível passou de R$ {brl(m["2022"]["exigivel"])} em 2022 para R$ {brl(v["exigivel"])} em setembro de 2026. O PL melhorou em 2024 e 2025, mas voltou a piorar com o prejuízo de 2026. Alterações de PL também incluem aportes e ajustes; não representam apenas lucro ou caixa. Fonte: BALANÇO/BALANCETE CREDIT 2022,2023,2024,2025.pdf e balancetes/Balancete-ja-set-2026.pdf, contas 2.1 e 2.4; DRE de cada período, grupos 3/4.'
        ,f'As receitas totais acumuladas antes de deduções são R$ {brl(sum(m[y]["receitas_totais"] for y in YEARS))}; os custos/despesas e deduções acumulados são R$ {brl(sum(m[y]["custo_total"] for y in YEARS))}. A diferença é o prejuízo acumulado das DREs de R$ {brl(sum(m[y]["resultado"] for y in YEARS))}. Fonte: DRE CREDIT 2022,2023,2024,2025.pdf e balancetes/Balancete-ja-set-2026.pdf, grupos 3 e 4, incluindo deduções 4.1.2. A receita bruta sozinha não fecha essa conta, pois há receitas financeiras e outras receitas.'
    ]},{'title':'Fluxo indireto e resultado gerencial: alcance','paragraphs':[
        'A aba Fluxo indireto confere a variação do disponível pela equação patrimonial: resultado menos aumento de ativos fora do disponível, mais aumento do exigível, mais alterações de PL que não vieram do resultado. Esta ponte inclui operações sem caixa que se compensam na identidade; não substitui uma DFC indireta com ajustes de depreciação, juros capitalizados e segregação das atividades. A DFC indireta completa por atividade permanece PENDENTE.',
        'O custo histórico é apresentado por competência. Aquisição de carteira e empréstimo a sócios podem formar ativos, e a mesma operação pode gerar custos e receitas reconhecidos em momentos distintos. Somar despesas, compras de carteira, débitos bancários e juros capitalizados produziria dupla contagem. O relatório de custos por categoria, ano e acumulado está apurado na base contábil. A abertura de pagamentos por finalidade será complementada com o razão de disponibilidades, considerando a conciliação bancária já confirmada pelo escritório.',
        'Para perdas esperadas, a referência metodológica é o CPC48, item5.5.17: probabilidades, valor do dinheiro no tempo e informações razoáveis e sustentáveis. Fonte primária: https://www.cpc.org.br/Arquivos/Documentos/530_CPC_48_rev_21.pdf (consulta07/11/2026). Não foram aplicadas taxas arbitrárias de perda por atraso nem presumida incidência automática de regra prudencial bancária à securitizadora.'
    ]}]
    report.append({'title':'Outros pontos que exigem confirmação','paragraphs':[
        f'A conta de empréstimos a sócios no ativo iniciou 2026 com R$ {brl(float(loan["opening"]))}, recebeu débitos de R$ {brl(float(loan["debit"]))} e créditos de R$ {brl(float(loan["credit"]))}, encerrando com R$ {brl(float(loan["balance"]))}. Arthur mantém o saldo final; Gustavo teve débitos de R$ {brl(float(gus["debit"]))} e créditos de R$ {brl(float(gus["credit"]))}. Isso exige contratos e comprovantes, sem presumir que toda movimentação contábil seja dinheiro transferido. Fonte: balancetes/Balancete-ja-set-2026.pdf, página 15, contas 1928/1.2.5,1930/1.2.5.01.001 e 2388/1.2.5.01.002.',
        ('Não foi localizada rubrica explícita de PDD ou perdas esperadas no plano do balancete de setembro de 2026. A existência de ajustes em outras rubricas depende de confirmação. Não se conclui que a carteira não tenha perdas. Fonte: balancetes/Balancete-ja-set-2026.pdf, plano extraído, conta1.1.2 e grupos3/4.' if not pdd else 'Contas de perdas localizadas: '+str(pdd)),
        f'A busca por COMISS nos planos e históricos I050/I250 da ECD2025 e nos6100 das exportações disponíveis, eliminando arquivos de conteúdo idêntico, encontrou {commission_count} linhas. Não há categoria segregada com valor identificado nas DREs analisadas. Comissões embutidas em serviços e períodos sem razão completo permanecem PENDENTES. Fonte: arquivos listados na aba Diagnósticos, conta de controle grupo3. O zero da categoria corresponde à ausência de identificação contábil específica, e não a prova de que nunca houve comissão.'
    ]})
    sheets=[dict(name='Síntese anual',headers=headers,rows=rows),dict(name='Situação real',headers=['Item em 30/09/2026','Valor R$ / situação','Fonte e conta','Ressalva'],rows=final),dict(name='Indicadores',headers=headers,rows=indicators),dict(name='Fluxo indireto',headers=['Ano','Caixa inicial R$','Resultado R$','(-) aumento outros ativos R$','(+) aumento exigível R$','(+) outras alterações PL R$','Caixa calculado R$','Disponível BP R$','Diferença R$','Alcance','Fonte e contas'],rows=bridge),dict(name='Diagnósticos',headers=['Assunto','Valor R$ / constatação','Fonte','Conta','Limitação'],rows=diagnostic)]
    return dict(sheets=sheets,report=report,checks=checks,pendencias=[dict(item='Detalhamento complementar do fluxo por finalidade',motivo='Movimentação anual e acumulada de caixa, bancos e aplicações apurada nos balancetes, com saldos conciliados conforme o escritório. O razão permitirá detalhar finalidades e eliminar transferências internas dos valores brutos; isso não impede apresentar os totais dos balancetes.',fonte='1.1.1; BP/balancetes anuais; Premissas_confirmadas.json')])

def create_pdf(data):
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4,landscape
    from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,KeepTogether
    from reportlab.lib.units import mm
    font='/usr/share/fonts/truetype/dejavu'
    pdfmetrics.registerFont(TTFont('DejaVu',font+'/DejaVuSans.ttf'));pdfmetrics.registerFont(TTFont('DejaVu-Bold',font+'/DejaVuSans-Bold.ttf'))
    pdfmetrics.registerFontFamily('DejaVu',normal='DejaVu',bold='DejaVu-Bold')
    styles=getSampleStyleSheet()
    for name in ['Normal','BodyText','Heading1','Heading2','Title']:styles[name].fontName='DejaVu';styles[name].textColor=colors.HexColor('#243449')
    styles['Normal'].fontSize=9;styles['Normal'].leading=14;styles['Normal'].spaceAfter=7
    styles['Title'].fontSize=24;styles['Title'].leading=31
    styles['Heading1'].fontSize=15;styles['Heading1'].leading=21;styles['Heading1'].spaceBefore=8
    styles['Heading2'].fontSize=11;styles['Heading2'].leading=15
    styles['Heading1'].keepWithNext=True;styles['Heading2'].keepWithNext=True
    styles['Normal'].allowOrphans=0;styles['Normal'].allowWidows=0
    styles.add(ParagraphStyle(name='SmallCSG',fontName='DejaVu',fontSize=7.5,leading=11,textColor=colors.HexColor('#526176')))
    styles.add(ParagraphStyle(name='TableCSG',fontName='DejaVu',fontSize=7.0,leading=10))
    styles.add(ParagraphStyle(name='TableHeaderCSG',fontName='DejaVu-Bold',fontSize=7,leading=10,textColor=colors.white))
    W,H=landscape(A4);width=W-32*mm;story=[]
    def para(s,style='Normal'):return Paragraph(escape(str(s)).replace('\n','<br/>'),styles[style])
    def percent(x):
        text=f'{abs(x)*100:,.1f}'.replace(',','X').replace('.',',').replace('X','.')+'%'
        return '('+text+')' if x<0 else text
    def ratio(x):
        text=(f'{abs(x):,.4f}' if 0<abs(x)<.01 else f'{abs(x):,.2f}').replace(',','X').replace('.',',').replace('X','.')+'x'
        return '('+text+')' if x<0 else text
    def table(headers,rows,widths=None,padding=6):
        values=[[para(x,'TableHeaderCSG') for x in headers]]
        for row in rows:
            values.append([para(brl(x) if isinstance(x,(int,float)) else ('' if x is None else str(x)),'TableCSG') for x in row])
        t=Table(values,colWidths=widths or [width/len(headers)]*len(headers),repeatRows=1,hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#263E59')),('VALIGN',(0,0),(-1,-1),'TOP'),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F1F4F7')]),('LINEBELOW',(0,0),(-1,0),.5,colors.HexColor('#263E59')),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),padding),('BOTTOMPADDING',(0,0),(-1,-1),padding)]))
        if rows and str(rows[-1][0])=='TOTAL' and len(rows)>1:t.setStyle(TableStyle([('NOSPLIT',(0,len(values)-2),(-1,len(values)-1)),('FONTNAME',(0,-1),(-1,-1),'DejaVu-Bold')]))
        return t
    story+=[Spacer(1,12*mm),para('CSG | Levantamento financeiro','Title'),para('14/06/2022 a 30/09/2026','Heading1'),para('Credit Saint Germain Securitizadora de Crédito S/A | CNPJ 46.788.467/0001-49 | NIRE 43.300.068.854'),para('Escritório Dal Ongaro | Contador: Valdecir Dal Ongaro'),Spacer(1,5*mm),para('Escopo e conclusão executiva','Heading1')]
    for p in data['executive']:story.append(para(p))
    story.append(para('Leitura dos estados: CONFIRMADO = registro localizado e conciliado; ESTIMADO = premissa explícita; PENDENTE = documento ou conciliação insuficiente. A conciliação dos saldos bancários foi confirmada pelo escritório. Recuperabilidade da carteira e exigibilidade contratual têm conferência própria.','SmallCSG'))
    story.append(PageBreak())
    # Cada relatório tem quadro anual e discussão; detalhamento auditável fica no Excel.
    desired=[('Fontes e cobertura','Cobertura'),('Revisão do balancete de 2026','Atualização 2026'),('1. Custos e despesas acumulados','Custos'),('2. Debêntures','Debêntures'),('3. Carteira de créditos','Carteira'),('4. Endividamento total','Endividamento'),('5. Fluxo de caixa acumulado pelos balancetes','Fluxo acumulado'),('6. DRE anual e acumulada','DRE'),('Cruzamento final e indicadores','Síntese anual')]
    byname={s['name']:s for s in data['sheets']}
    # Aliases são resolvidos por palavras quando os módulos usam nomes mais específicos.
    for title,key in desired:
        story.append(para(title,'Heading1'))
        sh=byname.get(key)
        if key=='Endividamento':
            original=byname['Balanço por ano'];sh=dict(original,rows=[r for r in original['rows'] if any(x in str(r[0]).lower() for x in ['exig','debênt','obriga','fornec','tribut','trabalh','mútu'])])
        if key=='Debêntures':sh=byname.get('2_Debentures')
        if key=='Carteira':sh=byname.get('3 Carteira')
        if sh is None:
            sh=next((s for s in data['sheets'] if s['name'].lower().startswith(key.lower())),None)
        if sh:
            # quadros anuais: item +5 anos+acumulado, fonte citada abaixo; estoque final não é soma.
            if len(sh['headers'])>=7 and all(any(y in str(h) for h in sh['headers']) for y in ['2022','2023','2024','2025','2026']):
                idx=[0]+[i for i,h in enumerate(sh['headers']) if any(y in str(h) for y in ['2022','2023','2024','2025','2026']) or 'acumulado' in str(h).lower()]
                idx=idx[:7]
                selected=sh['rows'][:30]
                rendered=[]
                for n,r in enumerate(selected,1):
                    pct=any(x in str(r[0]).lower() for x in ['margem',' / receita','/receita','% sobre',' / total'])
                    rr=[r[i] for i in idx];rr[0]=str(rr[0])+f' [{n}]'
                    if pct:rr=[percent(x) if isinstance(x,(float,int)) else x for x in rr]
                    if '(quantidade)' in str(r[0]).lower():rr=[f'{x:,.0f}'.replace(',','.') if isinstance(x,(float,int)) else x for x in rr]
                    rendered.append(rr)
                story.append(table([sh['headers'][i] for i in idx],rendered,[width*.28]+[width*.72/(len(idx)-1)]*(len(idx)-1)))
                story.append(para('Valores em R$; negativos entre parênteses. Acumulados de fluxo são somados; saldos patrimoniais referem-se à posição final. Referências das linhas:','SmallCSG'))
                source_idx=next((i for i,h in enumerate(sh['headers']) if 'fonte' in str(h).lower()),None)
                source_groups=defaultdict(list)
                for n,r in enumerate(selected,1):
                    source=r[source_idx] if source_idx is not None else 'Ver síntese contábil e contas do relatório correspondente'
                    conta_idx=next((i for i,h in enumerate(sh['headers']) if str(h).lower()=='conta'),None)
                    if conta_idx is not None:source=str(source)+' | conta '+str(r[conta_idx])
                    source_groups[str(source)].append(n)
                if key=='Síntese anual':
                    refs='; '.join('['+', '.join(map(str,refs))+'] '+source for source,refs in source_groups.items())
                    story.append(para('Arquivos: BALANÇO/BALANCETE CREDIT 2022,2023,2024,2025.pdf; DRE CREDIT de cada ano; balancetes/Balancete-ja-set-2026.pdf. Contas por linha: '+refs,'SmallCSG'))
                else:
                    for source,refs in source_groups.items():story.append(KeepTogether([para('['+', '.join(map(str,refs))+'] '+source,'SmallCSG')]))
            elif key=='Cobertura':story.append(table(sh['headers'],sh['rows'],[width*.1,width*.3,width*.32,width*.28]))
            elif key=='Atualização 2026':
                selected=[r[:4] for r in sh['rows'] if r[0] in ['Ativo total','Disponível','Carteira / clientes','Passivo exigível','Dívida com Jane','Debêntures','Resultado jan-set ainda em aberto','PL incluindo resultado jan-set','Receita bruta','Custo líquido da operação de crédito']]
                story.append(table(sh['headers'][:4],selected,[width*.43,width*.19,width*.19,width*.19]))
                story.append(para('Fonte anterior: Balancete 2026- posicao em 30-09.pdf. Fonte adotada: balancetes/Balancete-ja-set-2026.pdf. Ambos cobrem janeiro a setembro de 2026, consolidado 578/592. Contas: 1; 1.1.1; 1.1.2; 2.1; 1113/2.1.6; 642/2.1.7; 2.4; 3; 4; 4.1.1 e 3.1. Diferença = versão atualizada menos anterior. São revisões do mesmo período, sem soma de saldos ou fluxos. Comparação completa por código e campo nas abas Atualização 2026 e Diferenças contas 2026. A causa dos ajustes depende do razão atualizado.','SmallCSG'))
            elif key=='Caixa saldos':story.append(table([sh['headers'][i] for i in [0,1,2,3,4,5,6]],[[str(r[0])]+r[1:7] for r in sh['rows']],[width*.07]+[width*.93/6]*6))
        if key=='Fluxo acumulado':
            cash=data['metrics']['mod_fluxo'];a=cash['acumulado']
            story.append(para('Apuração concluída nos cinco balancetes: saldo inicial da abertura + débitos acumulados - créditos acumulados = saldo final de setembro de 2026. Débitos e créditos são movimentos brutos do disponível e incluem transferências internas. A soma de movimentos é distinta da posição de saldo, que não é somada entre anos.','SmallCSG'))
            story.append(para('Conferência acumulada','Heading2'))
            story.append(table(['Saldo inicial R$','Débitos acumulados R$','Créditos acumulados R$','Movimento líquido R$','Saldo final R$'],[[a[k] for k in ['opening','debit','credit','net','balance']]],[width/5]*5))
            app=cash['aplicacoes_fora_disponivel_por_ano']
            story.append(para('Aplicações classificadas fora do disponível','Heading2'))
            story.append(table(['Conta','2022','2023','2024','2025','2026 jan-set','Acumulado'],[['1.1.4: saldo por data',*[app[y]['balance'] for y in YEARS],'N/A - saldos por data']],[width*.28]+[width*.12]*6))
            story.append(para('Fonte: os mesmos balancetes, grupo 1.1.4 quando presente. Valores preservados em separado do grupo 1.1.1. As abas Caixa saldos e Caixa por conta identificam os movimentos, contas analíticas, páginas e a continuidade anual. A abertura por finalidade e a eliminação de transferências dos totais brutos são detalhamentos complementares.','SmallCSG'))
            indirect=byname['Fluxo indireto'];story.append(para('Conferência indireta: ponte patrimonial','Heading2'))
            story.append(table(indirect['headers'][:9],[[str(r[0])]+r[1:9] for r in indirect['rows']],[width*.06]+[width*.94/8]*8))
            story.append(para('Fonte: BP/balancetes de cada ano, contas 1,1.1.1,2.1,2.4 e grupos3/4. A ponte confere a identidade patrimonial; não é uma DFC indireta completa por atividades. Fontes/contas e alcance por ano constam na aba Fluxo indireto.','SmallCSG'))
        if key=='Endividamento':
            debt=byname['Endividamento'];ix=[2,7,8,9,10,11,12]
            story.append(para('Obrigações por credor/tributo e ano','Heading2'))
            story.append(table([debt['headers'][i] for i in ix],[[r[i] for i in ix] for r in debt['rows']],[width*.28]+[width*.12]*6))
            story.append(para('Fonte: BALANCETE CREDIT 2022,2023,2024,2025.pdf e balancetes/Balancete-ja-set-2026.pdf, contas analíticas do grupo 2.1. Códigos, classificação, natureza, partes relacionadas e fontes por linha na aba Endividamento. Prazo real, tributos vencidos e parcelamentos: PENDENTES de documentação. A coluna Acumulado não soma saldos.','SmallCSG'))
        # Todo texto produzido por especialistas é incluído adiante, evitando omissões.
        if key=='Carteira':story.append(para('A carteira contábil não foi apresentada como totalmente recuperável. Aging, perdas esperadas e posição de parcelas abertas em 30/09/2026 continuam PENDENTES; aquisições e cronogramas documentados são bases parciais.'))
        if key=='Síntese anual':
            final=byname['Situação real'];story.append(para('Quadro final em 30/09/2026','Heading2'));story.append(table(final['headers'],final['rows'],[width*.30,width*.13,width*.26,width*.31],padding=4))
            ind=byname['Indicadores'];annual=[]
            for r in ind['rows']:
                rr=r[:7]
                if 'R$' not in str(r[0]):rr=[ratio(x) if isinstance(x,(float,int)) else x for x in rr]
                annual.append(rr)
            story.append(para('Indicadores contábeis por ano','Heading2'));story.append(table(ind['headers'][:7],annual,[width*.28]+[width*.12]*6))
            story.append(para('Fonte: BALANÇO/BALANCETE CREDIT 2022,2023,2024,2025.pdf e balancetes/Balancete-ja-set-2026.pdf; contas 1,1.1.1,1.1.2,2.1,2.1.6 e 2.1.7. Fórmulas e ressalvas por indicador na aba Indicadores; x indica vezes. A cobertura recuperável e os prazos reais continuam PENDENTES.','SmallCSG'))
        story.append(PageBreak())
    story.append(para('Análise e ressalvas com trilha de fontes','Heading1'))
    for section in data['report']:
        story.append(para(section['title'],'Heading2'))
        for p in section['paragraphs']:story.append(para(p))
    story.append(Spacer(1,4*mm));story.append(para('Conciliações obrigatórias','Heading1'))
    for r in data['checks']:
        if r['status']!='OK':story.append(para(f'{r["teste"]} | {r["ano"]}: {r["status"]}. Fonte: {r["fonte"]}','SmallCSG'))
    ok=sum(x['status']=='OK' for x in data['checks']);story.append(para(f'{ok} verificações fecham dentro da tolerância de R$0,01. A relação completa, inclusive diferenças e testes pendentes, está na aba Conciliação. Conciliação contábil não confirma recuperabilidade nem liquidação contratual.'))
    story.append(para('Pendências a solicitar ao cliente','Heading1'))
    for i,p in enumerate(data['pendencias'],1):story.append(para(f'{i}. {p["item"]}: {p["motivo"]} Fonte/conta: {p["fonte"]}','SmallCSG'))
    story.append(para('Reprodução','Heading1'));story.append(para('Executar python3 gerar_levantamento_csg.py na pasta levantamento-financeiro. O script inventaria fontes, elimina cópias idênticas nas rotinas de importação, reprocessa bases e gera dados, Excel e PDF. Dependências e limitações estão em LEIA-ME.md.','SmallCSG'))
    def footer(c,doc):
        c.setStrokeColor(colors.HexColor('#C7D0D8'));c.line(16*mm,13*mm,W-16*mm,13*mm)
        c.setFont('DejaVu',7);c.setFillColor(colors.HexColor('#526176'));c.drawString(16*mm,9*mm,'CSG | Data-base 30/09/2026 | Elaborado 08/11/2026 | Valores em R$');c.drawRightString(W-16*mm,9*mm,str(doc.page))
    pdf=HERE/'Relatorio_Situacao_Financeira_CSG.pdf'
    SimpleDocTemplate(str(pdf),pagesize=(W,H),rightMargin=16*mm,leftMargin=16*mm,topMargin=15*mm,bottomMargin=19*mm,title='Situação Financeira CSG -30/09/2026',author='Dal Ongaro | Levantamento de fontes').build(story,onFirstPage=footer,onLaterPages=footer)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--inventario',action='store_true');parser.add_argument('--somente-dados',action='store_true');args=parser.parse_args()
    inventory_sheets=inventory();print('Inventário concluído: Inventario_fontes.md',flush=True)
    if args.inventario:return
    import mod_contabilidade,mod_debentures,mod_carteira,mod_fluxo,mod_atualizacao,mod_revisao_documental
    modules_build=[mod_contabilidade,mod_debentures,mod_carteira,mod_fluxo,mod_atualizacao,mod_revisao_documental]
    results=[]
    for module in modules_build:
        print('Processando '+module.__name__,flush=True);result=module.build(BASE,HERE);results.append(result);dump(HERE/(module.__name__+'_dados.json'),result)
    syn=synthesis(results[0]);sheets=syn['sheets']+sum([r.get('sheets',[]) for r in results],[])+inventory_sheets
    checks=sum([r.get('checks',[]) for r in results],[])+syn['checks'];pending=sum([r.get('pendencias',[]) for r in results],[])+syn['pendencias'];report=sum([r.get('report',[]) for r in results],[])+syn['report']
    required=[('Escritura original da 1ª emissão e primeiro aditamento, com vínculo dos documentos já existentes aos lançamentos','Certificados históricos e boletins realizados já estão disponíveis. Falta resolver sobreposição de cautelas e vincular série, titular, data e lançamento; não repetir a conciliação bancária.','2.1.7; Certificados históricos; Integralizações declaradas'),('Contratos de mútuo com Jane e Lair; transferências e saldos assinados','Confirmar prazo, encargos, vencimentos e posição atual de partes relacionadas.','2.1.6'),('Carteira VIA CAPITAL, cobrança e UY3/2022 por parcela na data-base','Identificar paga, aberta, vencida, renegociações e recebimentos; permitir aging e perdas esperadas.','1.1.2'),('CCBs e planilhas anteriores a 04/2025 não localizadas no conjunto analisado','Documentos de abril/2025 a setembro/2026 foram localizados, inclusive nos arquivos extraídos. Completar apenas o histórico anterior e a posição aberta por parcela.','ccb/; _arquivo/zips/;1.1.2'),('Razão analítico de caixa bancos e aplicações de 06/2022 a 09/2026','Classificar entradas e saídas por finalidade, eliminar transferências e vincular contratos. Saldos já conciliados com extratos conforme confirmação do escritório.','1.1.1;1.1.4; Premissas_confirmadas.json'),('Política de crédito/cobrança, renegociações e perdas reconhecidas','Fundamentar valor recuperável e ajuste de perdas esperadas.','1.1.2; CPC48')]
    pending=[dict(item=a,motivo=b,fonte=c) for a,b,c in required]+pending
    # Exigências que permanecem abertas não recebem diferença zero artificial.
    for test in ['Carteira gerencial aberta =1.1.2 em 30/09/2026','Detalhamento complementar: finalidades e transferências internas dos movimentos brutos','Debêntures pelo contrato = saldo contábil em 30/09/2026','Dívida com prazo contratual real segregado em curto/longo']:
        checks.append(dict(teste=test,ano='30/09/2026 / histórico',calculado=None,referencia=None,diferenca=None,status='PENDENTE',fonte='Ver Pendências;1.1.1;1.1.2;2.1.6;2.1.7'))
    premises=json.loads((HERE/'Premissas_confirmadas.json').read_text(encoding='utf8'))
    sheets.append(dict(name='Premissas confirmadas',headers=['Informação','Status','Fonte','Tratamento'],rows=[['Conciliação bancária dos balancetes usados',premises['conciliacao_bancaria']['status'],'Escritório contábil no atendimento de '+premises['data_do_esclarecimento']+'; Premissas_confirmadas.json',premises['conciliacao_bancaria']['tratamento']],['Custos e despesas por categoria ano e acumulado','APURADOS NA BASE CONTÁBIL','DREs anuais; balancete atualizado; contas de resultado',premises['custos_e_despesas']['tratamento']],['Fluxo de caixa anual e acumulado','APURADO PELOS BALANCETES','Balancetes 2022 a setembro de 2026; grupo 1.1.1',premises['fluxo_de_caixa']['tratamento']]]))
    sheets.extend([dict(name='Conciliação',headers=['Teste','Ano/data','Calculado R$','Referência R$','Diferença R$','Status','Fonte e conta'],rows=[[r.get(k) for k in ['teste','ano','calculado','referencia','diferenca','status','fonte']] for r in checks]),dict(name='Pendências',headers=['Item solicitado','Por que é necessário','Fonte/conta'],rows=[[p['item'],p['motivo'],p['fonte']] for p in pending])])
    v=results[0]['metrics']['years']['2026']
    executive=[f'O passivo exigível contábil supera o ativo em R$ {brl(-v["pl_com_resultado"])} em 30/09/2026. O PL registrado de R$ {brl(v["pl_registrado"])} precisa ser lido junto com o resultado parcial de R$ {brl(v["resultado"])}; o PL contábil incluindo esse resultado é R$ {brl(v["pl_com_resultado"])}. Fonte: balancetes/Balancete-ja-set-2026.pdf, contas 1,2.1,2.4 e grupos 3/4.',f'Dívida contábil: R$ {brl(v["exigivel"])}. Debêntures: R$ {brl(v["debentures"])}. Mútuos de partes relacionadas: R$ {brl(v["partes_relacionadas"])}. Fonte: balancetes/Balancete-ja-set-2026.pdf, contas 2.1,2.1.7 e 2.1.6. Contratos e vencimentos reais ainda precisam de confirmação.',f'Carteira registrada: R$ {brl(v["carteira"])}; disponível: R$ {brl(v["disponivel"])}. Fonte: mesmo balancete, contas 1.1.2 e 1.1.1. O valor recuperável e o déficit real permanecem PENDENTES. O material não sustenta uma conclusão afirmativa de solvência econômica.']
    executive.append('O escritório confirmou que os balancetes e DREs estão fechados com os extratos bancários. Essa conciliação é considerada concluída; o processamento adicional dos razões serve para abrir os fluxos por finalidade e vincular operações a contratos. Fonte: Premissas_confirmadas.json.')
    data=dict(sheets=sheets,checks=checks,pendencias=pending,report=report,executive=executive,premissas=premises,metrics={module.__name__:res.get('metrics',{}) for module,res in zip(modules_build,results)})
    names=[s['name'] for s in sheets]
    if len(names)!=len(set(names)):raise ValueError('Abas duplicadas: '+str(names))
    dump(HERE/'dados_levantamento.json',data)
    if args.somente_dados:return
    create_pdf(data)
    node=os.environ.get('CSG_NODE') or str(RUNTIME/'node/bin/node')
    modules=RUNTIME/'node/node_modules'
    link=HERE/'node_modules'
    if not link.exists() and modules.exists():link.symlink_to(modules,target_is_directory=True)
    subprocess.run([node,str(HERE/'gerar_planilha.mjs')],check=True,cwd=HERE)
    client_script=HERE/'gerar_relatorio_cliente_csg.py'
    if client_script.exists():
        subprocess.run([str(RUNTIME/'python/bin/python3'),str(client_script)],check=True,cwd=HERE)
    print('Excel e PDF gerados. Conciliações: '+str(len(checks))+'; pendências: '+str(len(pending)),flush=True)

if __name__=='__main__':main()
