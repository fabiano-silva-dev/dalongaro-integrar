"""Revisão das debêntures: separar documentos históricos e lacunas específicas.

Não altera a dívida contábil nem presume que documentos de datas diferentes
sejam novas entradas de caixa. A conciliação bancária informada pelo contador
é premissa aceita; o trabalho remanescente é identificar lançamento/titular/série.
"""
from pathlib import Path
from decimal import Decimal
import json
import re
from mod_debentures import pdf_text, docx_text, normal

D=Decimal
MONTHS={'janeiro':1,'fevereiro':2,'março':3,'abril':4,'maio':5,'junho':6,'julho':7,'agosto':8,'setembro':9,'outubro':10,'novembro':11,'dezembro':12}

def br_money(x):return D(x.replace('.','').replace(',','.'))
def dated(flat):
    m=re.search(r'Porto Alegre(?:/RS)?,?\s*(\d{1,2}) de (\w+) de (\d{4})',flat,re.I)
    return f'{m[3]}-{MONTHS[m[2].lower()]:02d}-{int(m[1]):02d}' if m else None

def build(base:Path,out:Path):
    base,out=Path(base),Path(out)
    folder=base/'publicacao-balancos/outras informações'
    rel=lambda p:str(p.relative_to(base))
    documents=[];certificate_rows=[];boletim_rows=[];evidence=[]
    cert_total=D(0);declared_total=D(0)
    for p in sorted(folder.iterdir()):
        if p.suffix.lower() not in ('.pdf','.docx'):continue
        text=pdf_text(p) if p.suffix.lower()=='.pdf' else docx_text(p)
        flat=' '.join(text.split());n=normal(flat)
        if 'CERTIFICADO REPRESENTATIVO' in n:
            qty=int(re.search(r'Certificado representativo de\s+(\d+)',flat,re.I)[1])
            serie=int(re.search(r'da\s+(\d+)[ºª°]\s*S[ÉE]RIE',flat,re.I)[1])
            holder=re.search(r'confere a\s+(.*?)(?:,?\s*CPF)',flat,re.I)[1].strip(' ,')
            caution=re.search(r'Cautela nº\s+Quantidade de Debêntures:\s+(\d+)',flat,re.I)[1]
            unit=br_money(re.search(r'valor unitário de R\$\s*([\d.,]+)',flat,re.I)[1])
            nominal=D(qty)*unit;cert_total+=nominal
            overlap=serie==1 and 'LAIR' in normal(holder) and qty==700
            note='Cautelas 1 e 2: mesmo titular/quantidade, datas diferentes; verificar qual permanece ativa' if overlap else 'Certificado histórico; vincular ao lançamento/controle já conciliado'
            row=[serie,holder,caution,qty,float(nominal),dated(flat),note,rel(p)+' | p.1','2.1.7']
            certificate_rows.append(row)
            documents.append(dict(source=rel(p),kind='Certificado',page=1,serie=serie,holder=holder,caution=caution,quantity=qty,nominal=float(nominal),date=dated(flat),evidence=' '.join(re.findall(r'Este Certificado.*?(?:asseguram\.)',flat,re.I))))
        elif p.suffix.lower()=='.docx':
            serie=int(re.search(r'debêntures da\s+(\d+)[ªº°]',flat,re.I)[1])
            nominal=br_money(re.search(r'no valor de R\$\s*([\d.,]+)',flat,re.I)[1])
            qty=int(re.search(r'representado por\s+(\d+)',flat,re.I)[1])
            holder=re.search(r'\((Affonso|Arthur|Gustavo|Jane)\)',p.name,re.I)[1]
            declares=('IMPORTANCIA REALIZADA' in n and 'A VISTA' in n and 'NA DATA DA SUBSCRICAO' in n)
            if declares:declared_total+=nominal
            loc=rel(p)+' | quadro Importância Realizada e fecho do boletim'
            boletim_rows.append([serie,holder,dated(flat),qty,float(nominal),'Integralização declarada à vista na data da subscrição' if declares else 'Descrição a conferir','Vincular ao lançamento e titular; sem exigir reconfirmação bancária genérica',loc,'2.1.7'])
            documents.append(dict(source=rel(p),kind='Boletim de subscrição',location='quadro Importância Realizada e fecho',serie=serie,holder=holder,quantity=qty,nominal=float(nominal),date=dated(flat),declares_integralization=declares,evidence=re.search(r'R\$[^.]*?à vista.*?subscrição\.',flat,re.I)[0] if re.search(r'R\$[^.]*?à vista.*?subscrição\.',flat,re.I) else 'Importância Realizada (R$); à vista, mediante aporte em moeda corrente nacional na data da subscrição.'))
        else:
            documents.append(dict(source=rel(p),kind='Aditamento registrado',pages=len([x for x in text.split('\f') if x.strip()])))
    second=base/'entrada/2024 08 29 Segundo Aditamento Escritura de Emissao  Credit Saint Germain  vf Registrado (JUCISRS).pdf'
    third=folder/'2024 11 05  Terceiro Adto a Escritura de Emissao  Credit Saint Germain vf Registrada (JUCISRS).pdf'
    st,tt=pdf_text(second),pdf_text(third)
    for serie,p,t,qty,formal in [(4,second,st,50,'2024-08-29'),(5,third,tt,500,'2024-11-05')]:
        flat=' '.join(t.split())
        assert f'Foram emitidas {qty}' in flat
        assert re.search(r'120%\s+do CDI',flat)
        assert re.search(r'60\s*\(sessenta\)\s*meses',flat)
        evidence.append(dict(source=rel(p),page=4,serie=serie,quantity=qty,nominal=float(D(qty)*1000),formalization_date=formal,remuneration='120% do CDI',subscription='Em até 20 meses contados da emissão',maturity='Em até 60 meses; a 5ª cita expressamente a Data de Emissão',specific_gap='Definição contratual de Data de Emissão, carência e fórmula integral dependem da escritura original; não usar automaticamente data do boletim como início'))
    # As duas cautelas de Lair são documentos diferentes, não duplicatas binárias.
    lair=[r for r in certificate_rows if r[0]==1 and 'LAIR' in normal(r[1])]
    assert len(lair)==2 and sorted(r[2] for r in lair)==['1','2']
    bruto=cert_total+D(50+500)*1000
    without_overlap=bruto-D(700000)
    condition_rows=[['Escritura original citada nos aditamentos','06/10/2022','Referência expressa; documento integral não está na pasta revisada',rel(second)+' | p.3; '+rel(third)+' | p.3','2.1.7'],['Primeiro aditamento citado','28/08/2023','Formalizou 2ª e 3ª séries; documento integral não está na pasta revisada',rel(second)+' | p.3; '+rel(third)+' | p.3','2.1.7']]
    for e in evidence:condition_rows.append([f'{e["serie"]}ª série',e['remuneration'],f'{e["quantity"]} títulos; subscrição {e["subscription"]}; vencimento {e["maturity"]}. {e["specific_gap"]}',e['source']+' | p.4','2.1.7'])
    checks=[dict(teste='Revisão documental: boletins 5ª série = nominal emitido no 3º aditamento',ano='2024',calculado=float(declared_total),referencia=500000.0,diferenca=float(declared_total-D(500000)),status='OK' if declared_total==D(500000) else 'DIVERGÊNCIA',fonte=rel(third)+' | p.4; quatro boletins | quadro Importância Realizada; 2.1.7')]
    result=dict(sheets=[dict(name='Certificados históricos',headers=['Série','Titular','Cautela','Quantidade','Nominal R$','Data do certificado','Conferência específica','Fonte','Conta'],rows=certificate_rows),dict(name='Integralizações declaradas',headers=['Série','Titular','Data do boletim','Quantidade','Valor declarado R$','Declaração documental','Trabalho remanescente','Fonte','Conta'],rows=boletim_rows),dict(name='Condições documentadas',headers=['Item','Condição ou data','Alcance e lacuna específica','Fonte','Conta'],rows=condition_rows)],checks=checks,pendencias=[dict(item='Conciliação específica das cautelas de Lair da 1ª série',motivo='Cautelas 1 e 2 são diferentes, de 27/10/2022 e 25/10/2022, ambas com 700 títulos. Confirmar substituição/cancelamento ou justificar ambos os registros; não somar automaticamente nem chamar de duplicata binária.',fonte='FRL300 (5).pdf; 1°SERIE DA 1°EMISSÃO - LAIR.pdf | p.1; 2.1.7'),dict(item='Vínculo dos boletins da 5ª série ao controle e aos lançamentos contábeis',motivo='Os quatro boletins declaram importância realizada em 11/11/2024. Identificar os lançamentos/INTs e eventuais diferenças de data/classificação; a conciliação bancária informada pelo contador é premissa aceita.',fonte='quatro DOCX de subscrição da 5ª série | quadro Importância Realizada; 2.1.7')],report=[dict(title='Documentação histórica das debêntures',paragraphs=['A pasta contém certificados datados de 2022 e 2023, boletins de 2024 e o terceiro aditamento registrado. A documentação existente permite entregar o histórico de séries, titulares, quantidades, valores nominais e datas documentais. Não é correto caracterizar essa documentação como restrita a 2025 e 2026. Fontes: Certificados históricos e Integralizações declaradas; conta 2.1.7.','Os quatro boletins da quinta série declaram R$ 500.000,00 como Importância Realizada, à vista na data da subscrição, em 11/11/2024. É informação documental de integralização que deve ser apresentada, com vinculação aos lançamentos e ao controle por titular. Fontes: os quatro boletins, quadro Importância Realizada e fecho; conta 2.1.7.','Os aditamentos documentam as séries quarta e quinta e a remuneração de 120% do CDI, com prazo de até 60 meses. O vencimento definitivo depende da definição de Data de Emissão e das regras da escritura original, não localizadas no conjunto revisado. Fontes: segundo e terceiro aditamentos, páginas 3 e 4; conta 2.1.7.'])],metrics=dict(document_count_in_folder=len(documents),certificate_count=len(certificate_rows),boletim_count=len(boletim_rows),nominal_bruto_sem_eliminar_potencial_sobreposicao=float(bruto),nominal_sem_uma_das_duas_cautelas_lair=float(without_overlap),declared_integralization_fifth=float(declared_total),documents=documents,contractual_evidence=evidence))
    out.mkdir(parents=True,exist_ok=True)
    (out/'qa').mkdir(parents=True,exist_ok=True)
    (out/'qa/revisao_debentures.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    return result

if __name__=='__main__':
    here=Path(__file__).resolve().parent
    r=build(here.parent,here)
    print(json.dumps({k:v for k,v in r['metrics'].items() if k not in ['documents','contractual_evidence']},ensure_ascii=False,indent=2))
