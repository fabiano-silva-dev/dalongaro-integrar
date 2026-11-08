#!/usr/bin/env python3
"""Versão de leitura para a administração, com dados do levantamento conciliado.

Executar após gerar_levantamento_csg.py. Não relê nem altera documentos originais.
Gera Word editável e PDF com o mesmo conteúdo, usando o renderizador do runtime.
"""
from __future__ import annotations
import argparse
from decimal import Decimal, ROUND_HALF_UP
import json
import os
from pathlib import Path
import shutil
import subprocess

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt, RGBColor

HERE=Path(__file__).resolve().parent
RUNTIME=Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies'
SKILL=Path.home()/'.codex/plugins/cache/openai-primary-runtime/documents/26.1105.12137/skills/documents'
STEM='Relatorio_Executivo_CSG'
YEARS=['2022','2023','2024','2025','2026']
HEADERS=['Descrição','2022','2023','2024','2025','2026 jan a set','Acumulado']
D=Decimal

def dec(x):return x if isinstance(x,D) else D(str(x))
def brl(x):
    v=dec(x).quantize(D('.01'),rounding=ROUND_HALF_UP)
    text=f'{abs(v):,.2f}'.replace(',','X').replace('.',',').replace('X','.')
    return '('+text+')' if v<0 else text
def pct(x,digits=1):
    v=(dec(x)*100).quantize(D(1).scaleb(-digits),rounding=ROUND_HALF_UP)
    text=f'{abs(v):,.{digits}f}'.replace(',','X').replace('.',',').replace('X','.')+'%'
    return '('+text+')' if v<0 else text
def total(values):return sum((dec(x) for x in values),D(0))

def setup_document(emissao):
    doc=Document();sec=doc.sections[0]
    doc.settings.odd_and_even_pages_header_footer=False
    sec.different_first_page_header_footer=False
    sec.page_width=Mm(210);sec.page_height=Mm(297)
    sec.top_margin=Mm(18);sec.bottom_margin=Mm(17);sec.left_margin=Mm(18);sec.right_margin=Mm(18)
    sec.header_distance=Mm(8);sec.footer_distance=Mm(8)
    for name in ['Normal','Title','Subtitle','Heading 1','Heading 2','Heading 3','List Bullet','List Number']:
        s=doc.styles[name];s.font.name='Arial';s.font.color.rgb=RGBColor(0,0,0)
        s._element.get_or_add_rPr().rFonts.set(qn('w:hAnsi'),'Arial')
    for border in list(doc.styles.element.iter(qn('w:pBdr'))):border.getparent().remove(border)
    body=doc.styles['Normal'];body.font.size=Pt(10.3);body.paragraph_format.line_spacing=1.12;body.paragraph_format.space_after=Pt(7)
    body.paragraph_format.widow_control=True
    title=doc.styles['Title'];title.font.size=Pt(25);title.font.bold=True;title.paragraph_format.space_after=Pt(10)
    sub=doc.styles['Subtitle'];sub.font.size=Pt(12);sub.paragraph_format.space_after=Pt(7)
    for name,size in [('Heading 1',15),('Heading 2',11.5)]:
        s=doc.styles[name];s.font.size=Pt(size);s.font.bold=True;s.paragraph_format.keep_with_next=True;s.paragraph_format.space_before=Pt(9);s.paragraph_format.space_after=Pt(7)
    for name in ['Small','Source']:
        if name not in doc.styles:doc.styles.add_style(name,1)
        s=doc.styles[name];s.font.name='Arial';s.font.color.rgb=RGBColor(0,0,0);s.font.size=Pt(8.1 if name=='Source' else 9.1)
        s.paragraph_format.space_after=Pt(6);s.paragraph_format.line_spacing=1.05
    h=sec.header.paragraphs[0];h.text='CSG   ESCRITÓRIO DAL ONGARO';h.style=doc.styles['Small']
    f=sec.footer.paragraphs[0];f.alignment=WD_ALIGN_PARAGRAPH.RIGHT
    r=f.add_run(f'Base 30/09/2026  |  Emissão {emissao}  |  Página ');r.font.name='Arial';r.font.size=Pt(8);r.font.color.rgb=RGBColor(0,0,0)
    field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),'PAGE');f._p.append(field)
    doc.core_properties.title='Levantamento financeiro da CSG'
    doc.core_properties.subject='Resumo dos seis relatórios e pendências de conclusão econômica'
    doc.core_properties.author='Escritório Dal Ongaro'
    return doc

def paragraph(doc,text,style=None,bold=False):
    p=doc.add_paragraph(style=style)
    p.add_run(text).bold=bold
    return p
def source(doc,text):return paragraph(doc,'Fonte: '+text,'Source')
def heading(doc,text,newpage=False):
    if newpage:doc.add_page_break()
    return doc.add_heading(text,level=1)
def subheading(doc,text):return doc.add_heading(text,level=2)
def table(doc,headers,rows,widths=None,size=8.3,total_rows=()):
    widths=widths or [174/len(headers)]*len(headers)
    t=doc.add_table(rows=1,cols=len(headers));t.alignment=WD_TABLE_ALIGNMENT.CENTER;t.autofit=False
    props=t._tbl.tblPr
    borders=OxmlElement('w:tblBorders')
    for edge in ['top','left','bottom','right','insideH','insideV']:
        e=OxmlElement('w:'+edge);e.set(qn('w:val'),'single');e.set(qn('w:sz'),'4');e.set(qn('w:color'),'D9D9D9');borders.append(e)
    props.append(borders)
    for cell,w in zip(t.rows[0].cells,widths):cell.width=Mm(w)
    for j,w in enumerate(widths):t.columns[j].width=Mm(w)
    for i,rowvalues in enumerate([headers]+rows):
        row=t.rows[0] if i==0 else t.add_row()
        cant=OxmlElement('w:cantSplit');row._tr.get_or_add_trPr().append(cant)
        if i==0:
            repeat=OxmlElement('w:tblHeader');row._tr.get_or_add_trPr().append(repeat)
        for j,(cell,value) in enumerate(zip(row.cells,rowvalues)):
            cell.width=Mm(widths[j]);cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            tc=cell._tc.get_or_add_tcPr();margin=OxmlElement('w:tcMar')
            for edge,value_twips in [('top',70),('bottom',70),('left',65),('right',65)]:
                e=OxmlElement('w:'+edge);e.set(qn('w:w'),str(value_twips));e.set(qn('w:type'),'dxa');margin.append(e)
            tc.append(margin)
            fill='263E59' if i==0 else ('E9EEF3' if i-1 in total_rows else ('F4F6F8' if i%2==0 else 'FFFFFF'))
            shade=OxmlElement('w:shd');shade.set(qn('w:fill'),fill);tc.append(shade)
            p=cell.paragraphs[0];p.paragraph_format.space_after=Pt(0);p.paragraph_format.space_before=Pt(0);p.paragraph_format.line_spacing=1.03
            p.alignment=WD_ALIGN_PARAGRAPH.CENTER if i==0 else (WD_ALIGN_PARAGRAPH.LEFT if j==0 or not isinstance(value,(int,float,D)) else WD_ALIGN_PARAGRAPH.RIGHT)
            r=p.add_run(brl(value) if isinstance(value,(int,float,D)) else str(value));r.font.name='Arial';r.font.size=Pt(size);r.font.bold=(i==0 or i-1 in total_rows);r.font.color.rgb=RGBColor.from_string('FFFFFF' if i==0 else '000000')
    paragraph(doc,'','Source')
    return t

def make_report(data,emissao='08/11/2026'):
    metrics=data['metrics'];m=metrics['mod_contabilidade']['years'];v=m['2026'];deb=metrics['mod_debentures'];car=metrics['mod_carteira'];cash=metrics['mod_fluxo']
    assert data['premissas']['conciliacao_bancaria']['status']=='CONFIRMADA PELO ESCRITÓRIO'
    sheets={s['name']:s for s in data['sheets']};costs=metrics['mod_contabilidade']['cost_categories']
    accumulated_cost=total(m[y]['custo_total'] for y in YEARS);accumulated_revenue=total(m[y]['receitas_totais'] for y in YEARS);accumulated_result=total(m[y]['resultado'] for y in YEARS)
    assert abs(accumulated_revenue-accumulated_cost-accumulated_result)<D('.01')
    assert not [c for c in data['checks'] if c['status'].startswith('DIVERG')], 'Há conciliação não resolvida na base'
    assert abs(dec(v['ativo'])-dec(v['exigivel'])-dec(v['pl_com_resultado']))<D('.01')
    doc=setup_document(emissao)
    paragraph(doc,'Levantamento financeiro da CSG','Title')
    paragraph(doc,'De 14 de junho de 2022 a 30 de setembro de 2026','Subtitle')
    paragraph(doc,'Credit Saint Germain Securitizadora de Crédito S/A\nCNPJ 46.788.467/0001-49\nEscritório Dal Ongaro   Contador Valdecir Dal Ongaro','Small')
    subheading(doc,'Resumo executivo')
    paragraph(doc,'Este relatório reúne os seis levantamentos solicitados e explica o que os números significam para a administração. O último fechamento disponível é setembro de 2026. Os saldos foram conciliados com a contabilidade; parte da conclusão econômica ainda depende de documentos da carteira e das dívidas.')
    paragraph(doc,f'A CSG apresenta patrimônio líquido contábil negativo de R$ {brl(abs(v["pl_com_resultado"]))}. As obrigações registradas superam os ativos registrados. O déficit econômico real ainda é PENDENTE, porque precisamos confirmar quanto da carteira será recuperado e os valores e prazos das obrigações por contrato.')
    table(doc,['Posição em 30 de setembro de 2026','Valor em R$'],[
        ['Ativos registrados',v['ativo']],['Obrigações registradas',v['exigivel']],['Patrimônio líquido com o resultado de 2026',v['pl_com_resultado']],['Prejuízo de janeiro a setembro de 2026',v['resultado']]
    ],[123,51],size=10,total_rows=(2,))
    source(doc,'F5, contas 1, 2.1, 2.4 e grupos 3 e 4. O resultado de 2026 foi incluído no patrimônio líquido, pois ainda está em aberto no balancete.')
    table(doc,['Relatório','Situação da apuração'],[
        ['1 Custos e despesas','Apurados por categoria por ano e no acumulado'],['2 Debêntures','Saldo contábil apurado; controle completo por titular PENDENTE'],['3 Contas a receber','Saldo contábil apurado; atraso e recuperação PENDENTES'],['4 Endividamento','Saldo contábil apurado; vencimentos reais PENDENTES'],['5 Fluxo de caixa','Movimentação anual e acumulada apurada nos balancetes'],['6 DRE','Resultado contábil apurado; ajustes econômicos PENDENTES']
    ],[51,123],size=8.7)
    paragraph(doc,'Os documentos F1 a F9 estão identificados no final. O Excel de apoio contém contas, contratos, parcelas, credores e conciliações. PENDENTE indica informação ainda insuficiente; ESTIMADO identifica uma premissa, quando utilizada.','Small')

    heading(doc,'1 Custos e despesas acumulados',True)
    paragraph(doc,f'Desde a abertura, a CSG reconheceu R$ {brl(accumulated_cost)} em custos, despesas e deduções tributárias. O quadro abaixo organiza esse valor por finalidade e por ano.')
    costrows=[]
    for category,values in costs.items():
        label={'Operacional':'Operação de crédito líquida','Comercial/Vendas':'Comercial e vendas','Impostos e taxas':'Impostos e taxas','Indedutíveis':'Despesas indedutíveis'}.get(category,category)
        vals=[dec(values[y]) for y in YEARS]
        if category=='Comissões':costrows.append(['Comissões sem segregação',*['n.i.']*6])
        else:costrows.append([label,*vals,total(vals)])
    costrows.append(['Total',*[m[y]['custo_total'] for y in YEARS],accumulated_cost])
    table(doc,HEADERS,costrows,[42]+[22]*6,size=8.0,total_rows=(len(costrows)-1,))
    source(doc,'Por coluna: 2022 F1, 2023 F2, 2024 F3, 2025 F4 e 2026 F5; grupo 3 e deduções 4.1.2. O acumulado soma os períodos. Códigos por categoria: Excel, aba Mapeamento contas.')
    paragraph(doc,'O relatório de custos e despesas está apurado pela movimentação líquida das contas de resultado, sem os lançamentos de encerramento, e conferido às DREs. Os saldos bancários são considerados conciliados conforme o escritório. A classificação dos pagamentos por finalidade é tratada na seção 5, sobre o fluxo de caixa.','Small')
    composition=[]
    for label,key in [('Operação de crédito líquida','operacao'),('Estrutura demais despesas e tributos','estrutura'),('Despesas financeiras','financeiras')]:
        amount=total(m[y][key] for y in YEARS);composition.append([label,amount,pct(amount/accumulated_cost,digits=2)])
    table(doc,['Composição do total acumulado','R$','Participação'],composition,[104,44,26],size=8.8)
    source(doc,'F1 a F5, mesmo mapa de custos. Financeiro: grupo 3.2.2.05. Operação: contas 272, 506, 509, 516 e 525 conforme o ano; estrutura é o restante, inclusive tributos.')
    paragraph(doc,'n.i. significa não identificado separadamente. Comissões eventualmente incluídas em outros serviços dependem de confirmação. Despesas indedutíveis são gastos com restrição de dedução fiscal. O custo líquido de crédito resulta de compras, amortizações e devoluções contabilizadas; o valor residual de 2026 exige explicação pelo razão atualizado.','Small')

    heading(doc,'2 Debêntures',True)
    paragraph(doc,'As debêntures representam dinheiro tomado de investidores, com obrigação de devolução e remuneração conforme os contratos. Precisamos distinguir o valor dos títulos documentados, o dinheiro recebido e a dívida que permanece registrada.')
    table(doc,['Medida','Apuração'],[
        ['Nominal bruto dos documentos localizados','R$ '+brl(deb['nominal_documental_bruto'])+'  Inclui duas cautelas de Lair a resolver'],['Nominal se uma cautela de Lair for substituição','R$ '+brl(deb['nominal_documental'])+'  Hipótese documental a confirmar'],['Integralização declarada nos boletins da quinta série','R$ '+brl(deb['integralizacao_declarada_2024'])+'  Declarada em 11/11/2024'],['Captação contábil identificada em 2025','R$ '+brl(deb['capital_inflow_2025'])+'  Contra bancos conciliados'],['Captação e amortização por titular no histórico','Vincular documentos e contrapartidas dos lançamentos'],['Juros reconhecidos desde a emissão','R$ '+brl(deb['interest_total'])],['Saldo contábil em setembro de 2026','R$ '+brl(v['debentures'])],['Principal e juros em aberto por titular','PENDENTE da conciliação individual'],['Cronograma definitivo de vencimentos','PENDENTE da escritura original e primeiro aditamento']
    ],[80,94],size=9.0,total_rows=(6,))
    source(doc,'Nominais e realização declarada: F7, certificados, quatro boletins com Importância Realizada e aditamentos, controle 2.1.7. Captação de 2025: F6, conta 642 contra bancos 8 e 15. Juros: F1 a F5, 369. Saldo atual: F5, 642/2.1.7. Não somar a declaração dos boletins como entrada adicional aos lançamentos.')
    paragraph(doc,'Há certificados históricos de 2022 e 2023 e boletins realizados em 2024. As duas cautelas de Lair exigem verificar se houve substituição ou cancelamento. A tarefa é vincular documentos e lançamentos por titular e data, considerando a conciliação bancária já confirmada pelo escritório.','Small')
    rows=[['Saldo devedor em cada data',*[deb['debt_balances'][y] for y in YEARS],'n.a.'],['Juros reconhecidos no período',*[deb['debt_interest'][y] for y in YEARS],deb['interest_total']]]
    table(doc,HEADERS,rows,[42]+[22]*6,size=8.2)
    source(doc,'F1 a F5: saldos 2.1.7 e juros 369. Para o saldo devedor, acumulado não se aplica; cada coluna apresenta a posição da data. Juros são somados por período.')
    subheading(doc,'O que já está confirmado')
    paragraph(doc,f'Em 2025, R$ {brl(deb["capitalized_interest_2025"])} de juros foram incorporados à dívida; em 2026 até setembro, mais R$ {brl(deb["capitalized_interest_2026"])}. Não houve débito na conta da dívida nesses dois períodos. Pagamentos fora dessa conta ainda precisam de conferência.')
    source(doc,'F6, I200 e I250, conta 642 com contrapartida 369; F5, conta 642, débitos e créditos de 2026.')
    paragraph(doc,'Os juros acumulados são a despesa contabilizada ao longo dos anos. O valor ainda em aberto depende de identificar os pagamentos de todo o histórico. As séries documentadas e as condições disponíveis estão no Excel; faltam a escritura original, o primeiro aditamento e o controle completo por titular.','Small')

    heading(doc,'3 Contas a receber',True)
    paragraph(doc,f'A carteira registrada é de R$ {brl(car["saldo_contabil_2026"])}. Esse é o valor contábil dos créditos; a quantia que será recebida depende dos pagamentos, atrasos, renegociações e perdas de cada contrato.')
    table(doc,['Composição contábil atual','R$'],[['Contas nominativas de devedores',car['duplicatas_2026']],['Direitos creditórios sem abertura por devedor',car['direitos_2026']],['Total da carteira',car['saldo_contabil_2026']]],[123,51],size=10,total_rows=(2,))
    source(doc,'F5, contas 1.1.2, 1.1.2.01 e 1.1.2.02. O saldo sem abertura nominal foi excluído do ranking de devedores, pois não representa um único cliente.')
    table(doc,HEADERS,[['Carteira registrada em cada data',*[car['saldos_anuais'][y] for y in YEARS],'n.a.']],[42]+[22]*6,size=8.2)
    source(doc,'F1 a F5, conta 1.1.2. Acumulado não se aplica a saldos de datas diferentes.')
    table(doc,['Posição da carteira na data base','Situação'],[['Valores a vencer','PENDENTE'],['Valores vencidos','PENDENTE'],['Valores inadimplentes','PENDENTE'],['Perda esperada','PENDENTE'],['Valor efetivamente recuperável','PENDENTE']],[123,51],size=9.5)
    paragraph(doc,'Para concluir essa separação, precisamos da posição de todas as parcelas na data-base, com identificação do contrato, vencimento, valor pago, valor aberto e renegociação. Os contratos disponíveis permitem organizar o calendário original; a ausência de uma baixa nessa amostra não prova atraso.')
    source(doc,'F8, documentos de aquisição e arquivos de baixas, controle 1.1.2. O vínculo entre os recebimentos disponíveis e as parcelas não é suficiente para fechar o estoque aberto.')
    paragraph(doc,'A avaliação de recuperação deverá considerar risco de crédito e informações sustentadas de cobrança. Nenhuma taxa arbitrária de perda foi aplicada. Concentração por devedor contábil e por aquisições documentadas consta no Excel; a amostra de aquisições não representa toda a carteira atual.','Small')
    paragraph(doc,'Em 470 contratos de 2025, os preços nos endossos superam os valores usados nas planilhas em R$ '+brl(car['diferenca_precos_endosso_planilhas'])+'. A diferença está discriminada no Excel para confronto com os lançamentos, sem presumir comissão, pagamento, perda ou ajuste do resultado.','Small')

    heading(doc,'4 Endividamento total',True)
    paragraph(doc,f'As obrigações registradas somam R$ {brl(v["exigivel"])}. A maior parte está nas debêntures e nos valores a pagar a Jane e Lair. Essas contas incluem recursos recebidos dos sócios e outros movimentos; a composição deve ser identificada por lançamento.')
    debt=sheets['Endividamento']['rows']
    def debt_sum(predicate,y):return total(r[7+YEARS.index(y)] for r in debt if predicate(r))
    groups=[('Debêntures',lambda r:r[0]=='642'),('Valores a pagar a Jane',lambda r:r[0]=='1113'),('Valores a pagar a Lair',lambda r:r[0]=='639'),('Fornecedores',lambda r:r[1].startswith('2.1.3.')),('Tributos em contas específicas',lambda r:r[1].startswith('2.1.4.')),('Tributos federais em conta conjunta',lambda r:r[0]=='651'),('Salários INSS e FGTS',lambda r:r[0] in ['187','191','192']),('Adiantamentos de clientes',lambda r:r[0]=='1595')]
    debtrows=[[label,*[debt_sum(predicate,y) for y in YEARS],'n.a.'] for label,predicate in groups]
    for j,y in enumerate(YEARS):assert abs(total(r[j+1] for r in debtrows)-dec(m[y]['exigivel']))<D('.01'),f'Passivo não coberto em {y}'
    debtrows.append(['Total das obrigações',*[m[y]['exigivel'] for y in YEARS],'n.a.'])
    table(doc,HEADERS,debtrows,[42]+[22]*6,size=8.0,total_rows=(len(debtrows)-1,))
    source(doc,'Por ano: F1 a F5. Contas 642/2.1.7, 1113 e 639/2.1.6, fornecedores 2.1.3, tributos 2.1.4, conta conjunta 651/2.1.5, pessoal 187, 191 e 192, adiantamentos 1595/2.1.6. Os saldos não são somados entre datas.')
    paragraph(doc,'A conta Tributos Federais está agrupada no passivo de encargos e precisa de abertura. Por isso, a linha de tributos em contas específicas não representa, sozinha, todos os impostos e encargos da empresa. A classificação acima preserva essa distinção.','Small')
    subheading(doc,'O saldo da dívida e a data de pagamento')
    paragraph(doc,'O total registrado não informa quanto está vencido nem quanto será cobrado imediatamente. Contratos e confirmações dos credores são necessários para separar valores vencidos, de curto prazo e de longo prazo.')
    paragraph(doc,'O Domínio apresenta as obrigações no circulante. Essa classificação ainda precisa ser confrontada com os prazos reais das debêntures e dos mútuos. Não foi identificado saldo separado de empréstimo bancário nas contas analisadas. Os saldos de bancos são considerados conciliados conforme o escritório.')
    source(doc,'F5, grupo 2.1 e plano analítico; contratos e controle individual indicados em F7. Credores e obrigações por conta constam na aba Endividamento do Excel.')

    heading(doc,'5 Fluxo de caixa acumulado',True)
    paragraph(doc,'A movimentação de caixa, bancos e aplicações do disponível foi apurada diretamente nos balancetes de cada ano. Os débitos mostram as entradas contábeis e os créditos mostram as saídas contábeis dessas contas. O quadro abaixo apresenta os cinco períodos e o acumulado desde a abertura.')
    assert cash['main_source']=='BALANCETES' and cash['status']=='APURADO'
    annual_cash=cash['balancetes_por_ano'];accumulated_cash=cash['acumulado']
    flowrows=[[label,*[annual_cash[y][key] for y in YEARS],accumulated_cash[key]] for label,key in [('Saldo inicial','opening'),('Entradas contábeis brutas','debit'),('Saídas contábeis brutas','credit'),('Movimentação líquida','net'),('Saldo final do disponível','balance')]]
    for y in YEARS:
        a=annual_cash[y]
        assert abs(dec(a['opening'])+dec(a['debit'])-dec(a['credit'])-dec(a['balance']))<D('.01')
        assert abs(dec(a['balance'])-dec(m[y]['disponivel']))<D('.01')
    assert abs(dec(accumulated_cash['opening'])+dec(accumulated_cash['debit'])-dec(accumulated_cash['credit'])-dec(accumulated_cash['balance']))<D('.01')
    table(doc,HEADERS,flowrows,[42]+[22]*6,size=8.2)
    source(doc,'Por ano: F1 a F5, balancetes, grupo 1.1.1 e suas contas analíticas. Os movimentos são somados no acumulado; saldo inicial é o da abertura e saldo final é o de setembro de 2026. Fontes por página e por conta nas abas Fluxo acumulado, Caixa saldos e Caixa por conta do Excel.')
    subheading(doc,'Fechamento desde a abertura')
    table(doc,['Conferência acumulada dos balancetes','R$'],[['Saldo inicial',accumulated_cash['opening']],['Mais entradas contábeis brutas',accumulated_cash['debit']],['Menos saídas contábeis brutas',-dec(accumulated_cash['credit'])],['Saldo final conciliado',accumulated_cash['balance']]],[123,51],size=10,total_rows=(3,))
    paragraph(doc,'Os valores brutos incluem transferências entre contas da própria CSG. Uma transferência entre banco e aplicação dentro do disponível aparece como saída de uma conta e entrada em outra, sem alterar o saldo total. Por isso, os totais brutos não representam exclusivamente dinheiro recebido de terceiros ou pago a terceiros.','Small')
    paragraph(doc,'A apuração anual e acumulada está concluída pelos balancetes e considera a conciliação bancária confirmada pelo escritório. O detalhamento por finalidade, como captações, compras de créditos e despesas pagas, e a eliminação das transferências internas podem ser complementados pelas contrapartidas do razão.','Small')
    applications=cash['aplicacoes_fora_disponivel_por_ano']
    table(doc,HEADERS,[['Aplicações fora do disponível',*[applications[y]['balance'] for y in YEARS],'n.a.']],[42]+[22]*6,size=8.0)
    source(doc,'F1 a F5, grupo 1.1.4 quando existente. As aplicações de 2022 estavam fora de 1.1.1 e foram mantidas separadas para preservar a classificação da fonte. Não se somam saldos de anos diferentes.')

    heading(doc,'6 DRE anual e acumulada',True)
    paragraph(doc,'A DRE mostra receitas e despesas reconhecidas em cada período, mesmo quando o pagamento ou o recebimento ocorre em outra data. O resultado contábil acumulado foi conciliado com as demonstrações anuais e com o balancete de 2026.')
    original={r[0]:r for r in sheets['DRE']['rows']}
    def dreval(label):return [dec(x) for x in original[label][1:7]]
    gross=dreval('Resultado bruto');before=dreval('Resultado operacional antes do financeiro')
    dre_summary=[['Receita bruta',*dreval('Receita bruta')],['Menos deduções e tributos sobre receita',*dreval('(-) Deduções da receita')],['Receita líquida',*dreval('Receita líquida')],['Menos custo líquido da operação de crédito',*dreval('(-) Custo da operação (grupo 3.1)')],['Resultado bruto',*gross],['Menos despesas operacionais',*[-(a-b) for a,b in zip(gross,before)]],['Resultado antes do financeiro',*before],['Mais receitas financeiras e outras',*[a+b for a,b in zip(dreval('(+) Receitas financeiras'),dreval('(+) Outras receitas'))]],['Menos despesas financeiras',*[-dec(m[y]['financeiras']) for y in YEARS],-total(m[y]['financeiras'] for y in YEARS)],['Menos IR e CSLL',*dreval('(-) IR/CSLL')],['Lucro ou prejuízo',*dreval('Lucro / (prejuízo) líquido')]]
    for j in range(6):assert abs(dre_summary[6][j+1]+dre_summary[7][j+1]+dre_summary[8][j+1]+dre_summary[9][j+1]-dre_summary[10][j+1])<D('.01')
    table(doc,HEADERS,dre_summary,[42]+[22]*6,size=8.0,total_rows=(2,4,6,10))
    source(doc,'Por ano: F1 a F5. Receitas: 4.1.1; deduções: 4.1.2; custo: 3.1; despesas operacionais: demais contas de 3, exceto financeiro e IR/CSLL; financeiro: 4.1.3, 4.2.1.04 e 3.2.2.05. Reclassificação sem alteração do resultado; contas na aba DRE do Excel.')
    paragraph(doc,'Em 2024, o crédito de devolução de compra reduziu o custo, por isso a linha de custo aparece positiva. Fonte F3, conta 509, grupo 3.1.','Small')
    paragraph(doc,f'No acumulado, as receitas totais antes de deduções são R$ {brl(accumulated_revenue)}; os custos, despesas e deduções são R$ {brl(accumulated_cost)}. A diferença é o prejuízo de R$ {brl(abs(accumulated_result))}. Os juros de debêntures, incluídos nas despesas financeiras, representam R$ {brl(deb["interest_total"])}.')
    source(doc,'F1 a F5, grupos 3 e 4, deduções 4.1.2 e juros 369. Os juros já fazem parte do total; não devem ser somados novamente.')
    paragraph(doc,'A rubrica despesas operacionais da DRE tem composição diferente da divisão de custos da seção 1: aqui as deduções da receita e o IR/CSLL aparecem separadamente. Os totais são os mesmos, apresentados em etapas distintas.','Small')
    paragraph(doc,'A visão econômica ajustada ainda é PENDENTE. Ela deverá incluir perdas esperadas da carteira e eventuais juros contratuais ainda não reconhecidos. O ano de 2026 cobre apenas janeiro a setembro; 2022 começa na abertura da empresa.','Small')

    heading(doc,'7 Cruzamento patrimonial e financeiro',True)
    paragraph(doc,'A comparação abaixo reúne os recursos registrados e as obrigações. A coluna contábil já pode ser apurada; a coluna econômica depende de verificar recuperação dos créditos, realizabilidade dos demais ativos e atualização dos contratos.')
    other=dec(v['ativo'])-dec(v['disponivel'])-dec(v['carteira'])
    table(doc,['Componente em setembro de 2026','Contábil em R$','Validação econômica'],[['Caixa bancos e aplicações',v['disponivel'],'Saldo conciliado conforme escritório'],['Carteira de créditos',v['carteira'],'Recuperação PENDENTE'],['Outros ativos',other,'Realização PENDENTE'],['Total dos ativos',v['ativo'],'Ativo realizável real PENDENTE'],['Obrigações totais',v['exigivel'],'Atualização e prazos PENDENTES'],['Patrimônio líquido com o resultado de 2026',v['pl_com_resultado'],'Patrimônio ajustado PENDENTE']],[76,43,55],size=9.0,total_rows=(3,5))
    source(doc,'F5, contas 1, 1.1.1, 1.1.2, 2.1, 2.4 e grupos 3 e 4. Outros ativos = ativo total menos disponível e carteira. A conciliação bancária foi confirmada pelo escritório em F9. A recuperação dos créditos e a atualização contratual das dívidas são análises específicas.')
    subheading(doc,'O que os saldos permitem concluir')
    paragraph(doc,f'Os ativos registrados são insuficientes para cobrir as obrigações registradas, com déficit patrimonial contábil de R$ {brl(abs(v["pl_com_resultado"]))}. Isso exige avaliar a recuperação dos créditos e os vencimentos das dívidas antes de definir medidas financeiras ou eventual aporte.')
    paragraph(doc,f'As debêntures e as obrigações com Jane e Lair somam R$ {brl(v["divida_financeira"])}. O disponível cobre {pct(dec(v["disponivel"])/dec(v["exigivel"]))} de todas as obrigações registradas. Essa relação compara saldos; os vencimentos reais ainda precisam ser confirmados.')
    source(doc,'F5, contas 2.1.7, 1113 e 639/2.1.6 e 1.1.1. Cobertura do disponível = conta 1.1.1 dividida pelo exigível de 2.1.')
    paragraph(doc,'O prejuízo acumulado das DREs difere do patrimônio líquido, porque o patrimônio também recebe aportes e outros ajustes. O déficit patrimonial, por sua vez, não determina sozinho o dinheiro necessário em uma data: isso depende do calendário de recebimentos e pagamentos.')
    paragraph(doc,'A conclusão sobre solvência econômica e necessidade de caixa permanece PENDENTE. Ainda não há suporte para tratar toda a carteira como recebimento garantido nem para declarar todas as dívidas integralmente atualizadas pelos contratos.')

    if cash.get('recursos_socios_2025'):
        financing=cash['recursos_socios_2025'];people=financing['por_pessoa']
        heading(doc,'8 Recursos de Jane e Lair',True)
        paragraph(doc,'Os registros mostram que os recursos de Jane e Lair financiaram o caixa da CSG. Esse financiamento pode sustentar compras de créditos da carteira, pagamentos da operação e a manutenção de recursos disponíveis. A razão de cada solicitação e a destinação de cada entrada precisam ser distinguidas do saldo total a pagar.')
        subheading(doc,'Recursos que passaram pelos bancos em 2025')
        financing_rows=[]
        for label,key in [('Entradas descritas como empréstimo','emprestimo_descrito'),('Entradas descritas como adiantamento de capital','afac_descrito'),('Outros créditos recebidos','outros_creditos'),('Total das entradas','entradas'),('Saídas contra as contas dos sócios','saidas'),('Recursos líquidos recebidos','liquido')]:
            financing_rows.append([label,people['Jane'][key],people['Lair'][key],financing[key] if key in financing else total(people[x][key] for x in ['Jane','Lair'])])
        table(doc,['Descrição','Jane em R$','Lair em R$','Total em R$'],financing_rows,[80,31,31,32],size=9.0,total_rows=(3,5))
        source(doc,'F6, bancos do grupo 1.1.1 contra as contas 1113 e 639. A classificação das entradas preserva o histórico do lançamento; não comprova, sozinha, um instrumento contratual. Eventos, datas e linhas de origem na aba Recursos dos sócios do Excel.')
        paragraph(doc,f'Além desses valores, Jane integralizou R$ {brl(financing["capital_jane_fora_1113"])} no capital, em lançamentos separados contra a conta 247. Esse aporte não foi incluído novamente nas entradas da tabela. Movimentos das contas dos sócios sem passagem pelos bancos também ficaram fora dos totais de caixa.','Small')
        subheading(doc,'Relação com a operação da empresa')
        growth=dec(m['2025']['carteira'])-dec(m['2024']['carteira'])
        table(doc,['Movimento observado em 2025','R$'],[['Aumento da carteira contábil',growth],['Recursos líquidos recebidos de Jane e Lair',financing['liquido']],['Aumento do disponível',dec(m['2025']['disponivel'])-dec(m['2024']['disponivel'])],['Resultado contábil do ano',m['2025']['resultado']]],[123,51],size=9.5)
        source(doc,'Carteira e disponível: F3 e F4, contas 1.1.2 e 1.1.1. Resultado: F4, DRE de 2025. Recursos dos sócios: F6, mesmas contas e critérios da tabela anterior. Crescimento da carteira é variação de saldo, não um desembolso presumido.')
        paragraph(doc,'Esses movimentos são compatíveis com necessidade de financiamento para sustentar a carteira e o giro da empresa. O valor recebido dos sócios não representa, por si, um prejuízo nem demonstra que cada entrada foi usada para pagar uma despesa específica. O dinheiro pode permanecer no caixa ou financiar ativos que serão recebidos depois.','Small')

    heading(doc,'9 Documentos necessários para concluir',True)
    paragraph(doc,'A administração deverá reunir os documentos abaixo. Cada solicitação está ligada à conclusão que ainda precisa ser confirmada. Não é necessário aguardar todos os itens para iniciar as conciliações que já possam ser feitas.')
    requests=[
        ('Carteira por parcela na data base','Solicitar à VIA CAPITAL, ao sistema de cobrança e à UY3 para o histórico inicial: contrato, devedor, vencimento, valor original, parcelas pagas e abertas, atrasos, renegociações e recuperações. Permite separar valores a vencer, vencidos, inadimplentes e recuperáveis.'),
        ('Controle completo das debêntures','Complementar o conjunto já existente com a escritura original e o primeiro aditamento ainda não localizados. Vincular certificados, boletins realizados e lançamentos por titular, resolver as cautelas de Lair e classificar as movimentações históricas. Permite fechar principal, juros e vencimentos.'),
        ('Contratos e confirmação dos mútuos','Obter os contratos de Jane, Lair e outras partes relacionadas, com comprovantes, prazo, encargos e saldo confirmado. Permite calcular a dívida contratual e o calendário de pagamento.'),
        ('Razão analítico de disponibilidades desde a abertura','Exportar os lançamentos de caixa, bancos e todas as aplicações de junho de 2022 a setembro de 2026, incluindo contas encerradas ou zeradas e as contrapartidas. Permite concluir o fluxo por finalidade, sem repetir a confirmação dos saldos conciliados.'),
        ('Razão atualizado de 2026 e composição dos tributos','Apresentar os lançamentos que explicam a revisão do balancete e a composição da conta Tributos Federais, com impostos, encargos, atrasos e parcelamentos. Permite explicar as diferenças e verificar exigibilidade.'),
        ('Política de crédito cobrança e perdas','Fornecer critérios de inadimplência, histórico de recuperação, garantias, renegociações e perdas já reconhecidas. Complementar as aquisições anteriores a abril de 2025 e esclarecer documentos específicos sem vínculo. Permite fundamentar a perda esperada e o valor recuperável.'),
        ('Créditos com sócios e outros ativos','Confirmar contratos, movimentações e recuperação dos empréstimos a sócios e dos demais créditos. Permite decidir quais valores podem compor o ativo realizável.')]
    for title,body in requests:
        subheading(doc,title);paragraph(doc,body)
    paragraph(doc,'Os custos, a DRE e a movimentação anual e acumulada do disponível estão apurados pelos demonstrativos contábeis; a conciliação bancária foi confirmada pelo escritório. O detalhamento do fluxo por finalidade é complementar. A conclusão econômica depende da recuperação da carteira e das obrigações contratuais.','Small')

    heading(doc,'10 Fontes e critérios de leitura',True)
    paragraph(doc,'Os valores estão em reais. Parênteses indicam valores negativos; PENDENTE indica informação não concluída, n.i. significa não identificado separadamente e n.a. significa não aplicável. Custos, receitas e juros são somados no acumulado; saldos patrimoniais são posições de datas específicas.')
    paragraph(doc,'Os caminhos abaixo são relativos à pasta do cliente credit-578. As demonstrações anuais de F1 a F4 estão em publicacao-balancos/DOCUMENTOS CREDIT. Os códigos e classificações usados em cada valor estão no Excel de apoio.','Small')
    for y,code in zip(YEARS[:4],['F1','F2','F3','F4']):
        subheading(doc,code+' Ano de '+y)
        paragraph(doc,f'BALANÇO CREDIT {y}.pdf, BALANCETE CREDIT {y}.pdf e DRE CREDIT {y}.pdf. Saldos patrimoniais: grupos 1 e 2; receitas e despesas: grupos 3 e 4; deduções: 4.1.2. Datas de posição: 31 de dezembro de cada ano.','Source')
    subheading(doc,'F5 Janeiro a setembro de 2026')
    paragraph(doc,'balancetes/Balancete-ja-set-2026.pdf. Consolidado 578 e 592, de 01/01/2026 a 30/09/2026. Ativo 1; disponível 1.1.1; carteira 1.1.2; exigível 2.1; PL 2.4; resultado grupos 3 e 4. Essa versão foi indicada como atualizada e substitui a anterior nos saldos e no resultado.','Source')
    subheading(doc,'F6 Lançamentos contábeis de 2025')
    paragraph(doc,'fiscal/dominio/sped_diario00578.txt. ECD 2025: I050, plano de contas; I155, saldos; I200 e I250, lançamentos. Caixa 1.1.1, debêntures 642 e juros 369. Os códigos das importações são tratados separadamente dos códigos da ECD.','Source')
    subheading(doc,'F7 Documentação das debêntures e sua conciliação')
    paragraph(doc,'levantamento-financeiro/levantamento_financeiro_CSG_2022-06_a_2026-09.xlsx, abas Deb_Titulos, Deb_Series, Deb_Titulares, Deb_Razao2025, Certificados históricos e Integralizações declaradas. Cada linha identifica o certificado, boletim ou aditamento e seu arquivo original, em entrada/ e publicacao-balancos/outras informações/. Conta de controle 2.1.7. Separados nominal documental, integralização declarada e vínculo aos lançamentos.','Source')
    subheading(doc,'F8 Contratos de crédito e arquivos de recebimentos')
    paragraph(doc,'ccb/AAAA-MM, _arquivo/zips/CCB CLIENTES de junho a setembro de 2026 e saida/relatorio_operacoes.xlsx; relatórios resumidos e fiscais; Importacao_Baixas_Entradas/baixa_ent.txt e Importacao_Baixas_Saidas/baixa_sai.txt; arquivos 05.2026.xlsx e 06.2026.xlsx. Aquisições documentadas de abril/2025 a setembro/2026. Conta 1.1.2; a posição aberta por parcela ainda requer o controle da cobrança.','Source')
    subheading(doc,'F9 Premissas confirmadas pelo escritório')
    paragraph(doc,'Premissas_confirmadas.json. Em esclarecimento neste atendimento, o escritório informou que os balancetes e as DREs estão fechados com os extratos bancários. Essa informação foi incorporada como confirmação da conciliação; o razão será usado para classificar os fluxos por finalidade e vincular contratos.','Source')
    subheading(doc,'Rastreabilidade e limites')
    paragraph(doc,'O Excel de apoio contém o mapa de contas, contratos e parcelas documentados, credores, fontes, conciliações e pendências. A comparação das versões de 2026 está nas abas Atualização 2026 e Diferenças contas 2026. As versões do mesmo período não foram somadas.','Small')
    paragraph(doc,'DFC e DMPL do Domínio não foram usadas para forçar fechamento. O relatório não presume perda zero na carteira nem juros zero em contratos ausentes. O prazo contábil do passivo depende de conferência contratual.','Small')
    return doc

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--somente-docx',action='store_true');parser.add_argument('--emissao',default='08/11/2026');args=parser.parse_args()
    data_path=HERE/'dados_levantamento.json'
    if not data_path.exists():raise SystemExit('Execute primeiro gerar_levantamento_csg.py para apurar e conciliar as fontes.')
    data=json.loads(data_path.read_text(encoding='utf8'))
    doc=make_report(data,args.emissao);docx_path=HERE/(STEM+'.docx');doc.save(docx_path)
    if not args.somente_docx:
        output=HERE/'qa'/'cliente';env=dict(os.environ);env['PATH']='/usr/bin:'+env.get('PATH','')
        render_args=[str(SKILL/'render_docx.py'),str(docx_path),'--output_dir',str(output),'--emit_pdf']
        # O LibreOffice empacotado exige GLIBC mais nova neste computador.
        # Manter o renderizador canônico, usando explicitamente o LibreOffice
        # instalado como fallback; nenhum arquivo do runtime é modificado.
        command=[str(RUNTIME/'python/bin/python3'),*render_args]
        rendered=subprocess.run(command,env=env,capture_output=True,text=True)
        if rendered.returncode:
            if not Path('/usr/bin/soffice').exists():
                raise RuntimeError(rendered.stderr)
            wrapper='import importlib.util,sys; spec=importlib.util.spec_from_file_location("csg_docx_renderer",sys.argv[1]); r=importlib.util.module_from_spec(spec); sys.modules[spec.name]=r; spec.loader.exec_module(r); r._resolve_soffice=lambda:"/usr/bin/soffice"; sys.argv=sys.argv[1:]; r.main()'
            print('Renderizador canônico usando LibreOffice instalado; runtime incompatível com a biblioteca do sistema.',flush=True)
            subprocess.run([str(RUNTIME/'python/bin/python3'),'-c',wrapper,*render_args],check=True,env=env)
        shutil.copy2(output/(STEM+'.pdf'),HERE/(STEM+'.pdf'))
    print('Relatório para cliente gerado: '+str(docx_path),flush=True)

if __name__=='__main__':main()
