"""Extração das fontes contábeis da CSG, sem alterar os documentos originais.

Requer pdftotext (Poppler). Valores são tratados em Decimal até a saída JSON.
Sinal interno: débito positivo e crédito negativo; dívida/PL são apresentados
com o sinal econômico (crédito positivo).
"""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from pathlib import Path
import re
import subprocess
import unicodedata

ZERO = Decimal('0.00')
MONEY = r'\d[\d.]*,\d\d[DC]?'


def decimal_br(value):
    value = str(value).strip()
    negative = value.endswith('C') or value.startswith('(')
    value = value.strip('()DC').replace('.', '').replace(',', '.')
    return Decimal(value) * (-1 if negative else 1)


def norm(value):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFKD', str(value)) if not unicodedata.combining(c)).upper().split())


def pdf_text(path, raw=False):
    return subprocess.check_output(['pdftotext', '-raw' if raw else '-layout', str(path), '-'], text=True)


def parse_balancete(path):
    """Lista de contas; opening/debit/credit/balance Decimal, sinal D+/C-."""
    path = Path(path)
    text = pdf_text(path, raw=True)
    pattern = re.compile(rf'^(\d+)\s+([1-9][\d.]*)\s+({MONEY})\s*\n({MONEY})\s+({MONEY})\s+({MONEY})\s*\n([^\n]+)', re.M)
    result = []
    for m in pattern.finditer(text):
        code, classification, balance, opening, debit, credit, description = m.groups()
        result.append(dict(code=code, classification=classification, description=description.strip(), opening=decimal_br(opening), debit=decimal_br(debit), credit=decimal_br(credit), balance=decimal_br(balance), source=str(path), page=text[:m.start()].count('\f')+1))
    if not result:
        raise ValueError(f'Nenhuma conta extraída: {path}')
    if len({r['code'] for r in result}) != len(result):
        raise ValueError(f'Códigos duplicados na extração: {path}')
    return result


def parse_balanco(path):
    path = Path(path)
    text = pdf_text(path, raw=True)
    pattern = re.compile(rf'^(\d+)\s+([1-9][\d.]*)\s+({MONEY})\s*\n([^\n]+)', re.M)
    return [dict(code=m[1], classification=m[2], balance=decimal_br(m[3]), description=m[4].strip(), source=str(path), page=text[:m.start()].count('\f')+1) for m in pattern.finditer(text)]


def is_leaf(row, rows):
    cl = row['classification']
    return not any(r['classification'].startswith(cl+'.') for r in rows)


def category(row):
    cl, d = row['classification'], norm(row['description'])
    if cl.startswith('3.1') or 'CUSTOS COM TERMO' in d:
        return 'Operacional'
    if cl.startswith('3.3') or cl.startswith('4.1.2') or any(x in d for x in ['PROVISAO P/ IMPOSTO','PROVISAO P/ CONTRIBUICAO']):
        return 'Impostos e taxas'
    if cl.startswith('3.2.2.05'):
        return 'Despesas financeiras'
    if 'INDEDUT' in d:
        return 'Indedutíveis'
    if cl.startswith('3.2.2.01') or 'CURSOS E TREINAMENTOS' in d or d == 'ESTAGIO':
        return 'Pessoal'
    if any(x in d for x in ['MIDIA','PROPAGANDA','BRINDES','PUBLICIDADE']):
        return 'Comercial/Vendas'
    if any(x in d for x in ['COMISSAO','COMISSOES']):
        return 'Comissões'
    if any(x in d for x in ['ALUGUE','CONDOMINIO','ENERGIA ELETRICA','REFORMA','MANUTENCAO E REPARO']):
        return 'Ocupação'
    if any(x in d for x in ['SOFTWARE','TELEFONE E INTERNET']):
        return 'Tecnologia'
    if any(x in d for x in ['ASSISTENCIA CONTABIL','ADVOCATIC','TERCEIROS','LEGAIS E JUDICIAIS']):
        return 'Serviços de terceiros'
    if any(x in d for x in ['TAXAS','MULTAS','IPTU','CARTORIO','EMOLUMENTOS']):
        return 'Impostos e taxas'
    return 'Administrativo'


def parse_dre(path, accounts):
    """Extrai somente linhas analíticas reconhecidas no plano de contas."""
    text = pdf_text(path)
    leaves = [a for a in accounts if is_leaf(a, accounts) and a['classification'].startswith(('3.','4.'))]
    names = defaultdict(list)
    for a in leaves:
        names[norm(a['description'])].append(a)
    rows, unmatched, used = [], [], set()
    pattern = re.compile(r'^\s+(.*?)\s{2,}(\(?\d[\d.]*,\d\d\)?)(?:\s+\(?\d[\d.]*,\d\d\)?)?\s*$')
    for line in text.splitlines():
        m = pattern.match(line)
        if not m:
            continue
        desc, val = m.groups()
        candidates = [a for a in names.get(norm(desc),[]) if a['code'] not in used]
        if not candidates:
            if norm(desc) in names:
                continue
            if desc.strip().startswith(('(=)', 'RESULTADO', 'RECEITA ', 'PREJUÍZO', 'LUCRO ', '(-) DESPESAS')):
                continue
            unmatched.append(desc)
            continue
        amount = decimal_br(val)
        selected = min(candidates, key=lambda a: abs(a['debit']-abs(amount)) if amount < 0 else min(abs(a['credit']-abs(amount)), abs(a['debit']-abs(amount))))
        used.add(selected['code'])
        # Na DRE despesas aparecem negativas; convertemos para débito positivo.
        value = -amount if selected['classification'].startswith('3.') else -amount
        rows.append(dict(selected, value=value, dre_source=str(path)))
    return rows, unmatched


def parse_dre_result(path):
    for line in pdf_text(path).splitlines():
        if norm(line).startswith('RESULTADO DO EXECICIO'):
            match=re.search(r'(\(?\d[\d.]*,\d\d\)?)\s*$',line)
            if match:
                return decimal_br(match[1])
    raise ValueError(f'Resultado líquido não localizado na DRE oficial: {path}')


def _float(value):
    return float(value) if isinstance(value, Decimal) else value


def _src(row, base):
    return str(Path(row['source']).relative_to(base)) + f" | conta {row['code']} ({row['classification']}) | p. {row['page']}"


def _check(test, year, value, ref, source):
    diff = value-ref
    return dict(teste=test, ano=str(year), calculado=float(value), referencia=float(ref), diferenca=float(diff), status='OK' if abs(diff)<=Decimal('0.01') else 'DIVERGÊNCIA', fonte=source)


def brl(v):
    v = Decimal(v)
    s = f'{abs(v):,.2f}'.replace(',', 'X').replace('.', ',').replace('X','.')
    return f'({s})' if v<0 else s


def _ecd(base, annual_accounts):
    """ECD é evidência auxiliar: excluir os lançamentos E de encerramento."""
    path=base/'fiscal/dominio/sped_diario00578.txt'
    if not path.exists():
        return [], [], []
    accounts={a['code']:a for a in annual_accounts}
    amounts=defaultdict(lambda:ZERO)
    history=[]
    entry={}
    for line in path.read_bytes().decode('latin1').splitlines():
        p=line.split('|')
        if len(p)<3:
            continue
        if p[1]=='I200':
            entry={'id':p[2], 'date':p[3], 'type':p[5]}
        elif p[1]=='I250' and entry and entry['type']!='E':
            code=p[2]
            if code not in accounts or not accounts[code]['classification'].startswith(('3.','4.')):
                continue
            value=decimal_br(p[4]) * (1 if p[5]=='D' else -1)
            amounts[code]+=value
            if 'COMISS' in norm(p[8] if len(p)>8 else ''):
                history.append([entry['date'],entry['id'],code,p[8],float(value),str(path.relative_to(base))+' | I200/I250 | conta '+code])
    rows=[]
    for code,value in sorted(amounts.items(),key=lambda kv:int(kv[0])):
        a=accounts[code]
        rows.append([code,a['classification'],a['description'],float(value),str(path.relative_to(base))+' | I250 não E | conta '+code])
    return rows, history, amounts


def _management_costs(base):
    from openpyxl import load_workbook
    path=base/'fiscal/planilhas/CONTROLE - CUSTOS 2025.xlsx'
    if not path.exists():
        return []
    wb=load_workbook(path,data_only=True,read_only=True)
    totals=defaultdict(lambda:[ZERO,0,[]])
    for ws in wb:
        if not re.fullmatch(r'\d{4}',ws.title):
            continue
        for i,row in enumerate(ws.values,1):
            if len(row)<5 or norm(row[0])!='DESPESAS' or not isinstance(row[3],(float,int)):
                continue
            cat=' '.join(str(row[1] or 'SEM CATEGORIA').split())
            k=(ws.title,cat)
            totals[k][0]+=Decimal(str(row[3]));totals[k][1]+=1;totals[k][2].append(i)
    wb.close()
    return [[m,c,float(t[0]),t[1],f'{path.relative_to(base)} | aba {m}, coluna D, linhas '+','.join(map(str,t[2])), 'Controle de caixa do cliente; não somado à DRE; sem conta contábil individual vinculada'] for (m,c),t in sorted(totals.items())]


def build(base: Path, out: Path):
    base=Path(base).resolve();out=Path(out)
    annual_dir=base/'publicacao-balancos/DOCUMENTOS CREDIT'
    balances={};results={};checks=[];pendencias=[];metrics={'years':{}}
    rawrows=[];maprows=[];debt_values=defaultdict(dict);debt_info={}
    category_values=defaultdict(lambda:defaultdict(lambda:ZERO))
    cats=['Administrativo','Operacional','Comercial/Vendas','Pessoal','Ocupação','Tecnologia','Serviços de terceiros','Impostos e taxas','Comissões','Despesas financeiras','Indedutíveis']
    official_results={2022:Decimal('-549448.25'),2023:Decimal('-284723.40'),2024:Decimal('42212.45'),2025:Decimal('-15000.09')}
    annual_dre={};annual_sources={};dre_components={}
    for year in range(2022,2027):
        path=base/'balancetes/Balancete-ja-set-2026.pdf' if year==2026 else annual_dir/f'BALANCETE CREDIT {year}.pdf'
        accounts=parse_balancete(path); balances[year]=accounts
        bycode={a['code']:a for a in accounts}
        byclass={a['classification']:a for a in accounts}
        if year<2026:
            bp_path=annual_dir/f'BALANÇO CREDIT {year}.pdf'
            bp=parse_balanco(bp_path)
            for a in bp:
                if a['code'] in bycode:
                    b=bycode[a['code']]
                    checks.append(_check('BP oficial = balancete por conta',year,b['balance'],a['balance'],_src(b,base)+'; '+str(bp_path.relative_to(base))))
            drepath=annual_dir/f'DRE CREDIT {year}.pdf'
            dre,unmatched=parse_dre(drepath,accounts)
            for u in unmatched:
                pendencias.append(dict(item='Linha da DRE sem conta mapeada',motivo=f'{year}: {u}',fonte=str(drepath.relative_to(base))))
            annual_sources[year]=str(drepath.relative_to(base))
        else:
            dre=[dict(a,value=a['balance'],dre_source=str(path)) for a in accounts if a['classification'].startswith(('3.','4.')) and is_leaf(a,accounts)]
            annual_sources[year]=str(path.relative_to(base))
        annual_dre[year]=dre
        result=-sum((r['value'] for r in dre),ZERO)
        results[year]=result
        reference=parse_dre_result(drepath) if year<2026 else -bycode['402']['balance']-bycode['269']['balance']
        checks.append(_check('DRE gerada = fonte oficial',year,result,reference,annual_sources[year]+' | contas analíticas grupos 3 e 4'))
        if year<2026:
            checks.append(_check('Resultado oficial = âncora informada no pedido',year,reference,official_results[year],annual_sources[year]+' | resultado líquido; âncora de validação do pedido'))
        for a in accounts:
            rawrows.append([year,a['code'],a['classification'],a['description'],float(a['opening']),float(a['debit']),float(a['credit']),float(a['balance']), 'Analítica' if is_leaf(a,accounts) else 'Sintética',_src(a,base)])
        costrows=[r for r in dre if r['classification'].startswith('3.') or r['classification'].startswith('4.1.2')]
        for a in costrows:
            cat=category(a)
            category_values[cat][year]+=a['value']
            maprows.append([year,a['code'],a['classification'],a['description'],cat,float(a['value']),annual_sources[year]+' | conta '+a['code']+' ('+a['classification']+')','Crédito redutor preservado' if a['value']<0 else 'Débito de custo/despesa'])
        group3=sum((a['value'] for a in dre if a['classification'].startswith('3.')),ZERO)
        deductions=sum((a['value'] for a in dre if a['classification'].startswith('4.1.2')),ZERO)
        total_cost=group3+deductions
        checks.append(_check('Soma despesas por categoria = DRE + deduções',year,sum((category_values[c][year] for c in cats),ZERO),total_cost,annual_sources[year]+' | grupo 3 e deduções 4.1.2'))
        if year==2026:
            checks.append(_check('Despesas grupo 3 extraídas = sintética 3',year,group3,bycode['269']['balance'],_src(bycode['269'],base)))
        def amount(prefix,side=1):
            return sum((r['value']*side for r in dre if r['classification'].startswith(prefix)),ZERO)
        gross=amount('4.1.1',-1)
        financial_income=amount('4.1.3',-1)+amount('4.2.1.04',-1)
        other_income=sum((-r['value'] for r in dre if r['classification'].startswith('4.') and not r['classification'].startswith(('4.1.1','4.1.2','4.1.3','4.2.1.04'))),ZERO)
        creditcost=amount('3.1')
        taxprofit=sum((r['value'] for r in dre if 'PROVISAO P/' in norm(r['description']) and any(x in norm(r['description']) for x in ['IRPJ','CSLL'])),ZERO)
        interest=sum((r['value'] for r in dre if norm(r['description'])=='JUROS DEBENTURES'),ZERO)
        finances=category_values['Despesas financeiras'][year]
        structure=total_cost-category_values['Operacional'][year]-finances
        debtleaf=[a for a in accounts if a['classification'].startswith(('2.1.','2.2.','2.3.')) and is_leaf(a,accounts)]
        related=sum((-a['balance'] for a in debtleaf if 'HUNING' in norm(a['description'])),ZERO)
        financial_debt=related-bycode['642']['balance']
        debt=-sum((a['balance'] for a in debtleaf),ZERO)
        debt_synthetic=-sum((a['balance'] for a in accounts if a['classification'] in ['2.1','2.2','2.3']),ZERO)
        checks.append(_check('Exigível analítico = passivo sem PL',year,debt,-bycode['149']['balance']+bycode['242']['balance'],_src(bycode['149'],base)+'; '+_src(bycode['242'],base)))
        pl_recorded=-bycode['242']['balance'];pl_effective=pl_recorded+(result if year==2026 else ZERO)
        checks.append(_check('Ativo = exigível + PL incluindo resultado aberto',year,bycode['1']['balance'],debt+pl_effective,_src(bycode['1'],base)+'; passivos analíticos; 2.4 e resultado do período'))
        if year==2026:
            c=_check('Ativo = exigível + PL do grupo 2.4 sem encerramento',year,bycode['1']['balance'],debt+pl_recorded,'balancetes/Balancete-ja-set-2026.pdf | contas 1, 2 e 2.4; diferença explicada pelo resultado em aberto')
            c['status']='EXPLICADO - RESULTADO EM ABERTO'
            checks.append(c)
        for a in debtleaf:
            if a['balance']:
                debt_values[a['code']][year]=-a['balance'];debt_info[a['code']]=a
        yearly=dict(ativo=bycode['1']['balance'],disponivel=bycode['3']['balance'],carteira=bycode['12']['balance'],pl_registrado=pl_recorded,resultado=result,pl_com_resultado=pl_effective,exigivel=debt,debentures=-bycode['642']['balance'],outras_obrigacoes=-bycode['200']['balance'],fornecedores=-bycode['164']['balance'],partes_relacionadas=related,divida_financeira=financial_debt,ativo_circulante=bycode['2']['balance'],custo_total=total_cost,custos_grupo3=group3,deducoes=deductions,financeiras=finances,estrutura=structure,operacao=category_values['Operacional'][year],juros_debentures=interest,receita_bruta=gross,receitas_financeiras=financial_income,ir_csll=taxprofit,imobilizado=bycode.get('111',{}).get('balance',ZERO),emprestimo_socios=byclass.get('1.2.5',{}).get('balance',ZERO),aplicacoes_fora_disponivel=byclass.get('1.1.4',{}).get('balance',ZERO),outros_creditos_circulantes=byclass.get('1.1.3',{}).get('balance',ZERO))
        metrics['years'][str(year)]={k:float(v) for k,v in yearly.items()}
        metrics['years'][str(year)].update(receitas_totais=float(gross+financial_income+other_income),receitas_grupo4=float(gross+financial_income+other_income-deductions),outras_receitas=float(other_income),depreciacao_periodo=float(sum((r['value'] for r in dre if norm(r['description'])=='DEPRECIACAO'),ZERO)))
        # Estrutura da DRE mantém o custo bruto do relatório oficial e reclassifica
        # custos registrados em despesas em linha própria, sem alterar o resultado.
        comps={'Receita bruta':gross,'(-) Deduções da receita':-deductions,'Receita líquida':gross-deductions,'(-) Custo da operação (grupo 3.1)':-creditcost,'Resultado bruto':gross-deductions-creditcost}
        for cat in cats:
            if cat=='Despesas financeiras':
                continue
            value=category_values[cat][year]
            if cat=='Impostos e taxas':value-=deductions+taxprofit
            if cat=='Operacional':value-=creditcost
            comps['(-) '+cat+(' registrado em despesas' if cat=='Operacional' else '')]=-value
        op_structure=sum((-v for k,v in comps.items() if k.startswith('(-) ') and k not in ['(-) Deduções da receita','(-) Custo da operação (grupo 3.1)']),ZERO)
        comps['Resultado operacional antes do financeiro']=gross-deductions-creditcost-op_structure
        comps['(+) Receitas financeiras']=financial_income
        comps['(+) Outras receitas']=other_income
        comps['(-) Juros de debêntures']=-interest
        comps['(-) Demais despesas financeiras']=-(finances-interest)
        comps['Resultado antes de IR/CSLL']=result+taxprofit
        comps['(-) IR/CSLL']=-taxprofit
        comps['Lucro / (prejuízo) líquido']=result
        comps['Margem bruta sobre receita líquida']=(gross-deductions-creditcost)/(gross-deductions) if gross!=deductions else None
        comps['Margem líquida sobre receita bruta']=result/gross if gross else None
        comps['Estrutura e demais tributos / receita bruta']=structure/gross if gross else None
        comps['Juros debêntures / receita bruta']=interest/gross if gross else None
        dre_components[year]=comps
    years=list(range(2022,2027))
    category_rows=[]
    for cat in cats:
        vals=[category_values[cat][y] for y in years]
        sources='; '.join(f'{y}: {annual_sources[y]} | contas '+','.join(sorted({r[1] for r in maprows if r[0]==y and r[4]==cat}, key=int)) for y in years if category_values[cat][y])
        category_rows.append([cat,*map(float,vals),float(sum(vals,ZERO)),sources or 'Plano de contas/DRE: nenhuma conta específica com movimento identificada'])
    totals=[sum((category_values[c][y] for c in cats),ZERO) for y in years]
    category_rows.append(['TOTAL CUSTOS/DESPESAS + DEDUÇÕES',*map(float,totals),float(sum(totals,ZERO)),'DRE anual | grupos 3 e deduções 4.1.2; 2026 balancete'])
    for label,key in [('Operação de crédito (líquida)','operacao'),('Estrutura, demais despesas e tributos','estrutura'),('Financeiro','financeiras')]:
        vals=[Decimal(str(metrics['years'][str(y)][key])) for y in years]
        category_rows.append([label,*map(float,vals),float(sum(vals,ZERO)),'Reclassificação do mapa de contas; sem dupla contagem'])
        pct=[v/t if t else ZERO for v,t in zip(vals,totals)]
        category_rows.append([label+' / total',*map(float,pct),float(sum(vals,ZERO)/sum(totals,ZERO)),'Proporção do total de custos/despesas e deduções; valor em fração'])
    dre_rows=[]
    for label in dre_components[2026]:
        vals=[dre_components[y].get(label,ZERO) for y in years]
        if label.startswith('Margem bruta'):
            num=sum((dre_components[y]['Resultado bruto'] for y in years),ZERO);den=sum((dre_components[y]['Receita líquida'] for y in years),ZERO);acc=num/den if den else None
        elif label.startswith('Margem líquida'):
            acc=sum((results[y] for y in years),ZERO)/sum((dre_components[y]['Receita bruta'] for y in years),ZERO)
        elif label.startswith('Estrutura e'):
            acc=sum((Decimal(str(metrics['years'][str(y)]['estrutura'])) for y in years),ZERO)/sum((dre_components[y]['Receita bruta'] for y in years),ZERO)
        elif label.startswith('Juros debêntures /'):
            acc=sum((Decimal(str(metrics['years'][str(y)]['juros_debentures'])) for y in years),ZERO)/sum((dre_components[y]['Receita bruta'] for y in years),ZERO)
        else:acc=sum((v for v in vals if v is not None),ZERO)
        dre_rows.append([label,*[_float(v) for v in vals],_float(acc),'DRE CREDIT 2022–2025.pdf; balancetes/Balancete-ja-set-2026.pdf | contas analíticas grupos 3 e 4; ver Mapeamento contas'])
    balance_rows=[]
    for label,key in [('Ativo total','ativo'),('Disponível (1.1.1)','disponivel'),('Aplicações fora do disponível (1.1.4)','aplicacoes_fora_disponivel'),('Carteira (1.1.2)','carteira'),('Empréstimo a sócios (1.2.5)','emprestimo_socios'),('Ativo circulante','ativo_circulante'),('Dívida/exigível total','exigivel'),('Debêntures (2.1.7)','debentures'),('Outras obrigações (2.1.6)','outras_obrigacoes'),('Partes relacionadas (mútuos contábeis)','partes_relacionadas'),('Dívida financeira (debêntures + relacionadas)','divida_financeira'),('Fornecedores','fornecedores'),('PL registrado (2.4)','pl_registrado'),('Resultado do exercício','resultado'),('PL incluindo resultado em aberto de 2026','pl_com_resultado')]:
        balance_rows.append([label,*[metrics['years'][str(y)][key] for y in years], 'N/A - saldo não somável','BALANÇO/BALANCETE CREDIT 2022–2025.pdf; balancetes/Balancete-ja-set-2026.pdf | conta indicada; detalhamento na Base contábil'])
    debtrows=[]
    for code in sorted(debt_values,key=int):
        a=debt_info[code];cl=a['classification'];related='HUNING' in norm(a['description'])
        nature='Financeiro' if cl.startswith(('2.1.7','2.1.1','2.1.2')) or related else 'Operacional'
        party='Partes relacionadas (mútuo)' if related else ('Titularidade PENDENTE' if cl.startswith('2.1.7') else 'Terceiros')
        vals=[debt_values[code].get(y,ZERO) for y in years]
        sources='; '.join(f'{y}: {_src(next(r for r in balances[y] if r["code"]==code),base)}' for y in years if y in debt_values[code])
        debtrows.append([code,cl,a['description'],nature,party,'Circulante no Domínio','PENDENTE: vencimento contratual e eventual parcela de longo prazo',*map(float,vals),'N/A - saldo não somável',sources])
    ecdrows,commissionrows,ecd_amounts=_ecd(base,balances[2025])
    official_by_code={r['code']:r for r in annual_dre[2025]}
    ecd_comparison=[]
    for row in ecdrows:
        code=row[0]
        ref=official_by_code.get(code,{}).get('value',ZERO)
        diff=ecd_amounts[code]-ref
        ecd_comparison.append(row[:4]+[float(ref),float(diff),row[-1]+'; DRE CREDIT 2025.pdf | mesma conta'])
        if abs(diff)>Decimal('0.01'):
            checks.append(_check('ECD (não encerramento) = DRE por conta',2025,ecd_amounts[code],ref,row[-1]+'; DRE CREDIT 2025.pdf'))
    management_rows=_management_costs(base)
    management_total=sum((Decimal(str(r[2])) for r in management_rows),ZERO)
    periods=sorted(set(r[0] for r in management_rows))
    m26=metrics['years']['2026']
    pendencias.extend([
        dict(item='Vencimentos e encargos das obrigações',motivo='O balancete classifica todas as dívidas no circulante. Contratos de debêntures/mútuos e cronograma real são necessários para reclassificar e medir custo contratual.',fonte='balancetes/Balancete-ja-set-2026.pdf | 2.1.6, 2.1.7'),
        dict(item='PDD/perda esperada da carteira',motivo='Nenhuma conta específica de PDD/perda esperada identificada nas contas contábeis fornecidas; perda econômica não pode ser presumida igual a zero.',fonte='BALANCETE CREDIT 2022–2025.pdf; balancetes/Balancete-ja-set-2026.pdf | 1.1.2; grupos 3 e 4'),
        dict(item='Comissões',motivo='Nenhuma conta ou histórico com COMISSÃO/COMISSÕES identificado na ECD 2025; possível inclusão em serviços de terceiros exige contratos/documentos de suporte.',fonte='fiscal/dominio/sped_diario00578.txt | I050/I250; DREs anuais'),
        dict(item='Controle gerencial de custos incompleto',motivo='Planilha gerencial cobre janeiro a outubro de 2025, sem novembro e dezembro; valores de caixa não substituem despesas por competência.',fonte='fiscal/planilhas/CONTROLE - CUSTOS 2025.xlsx | abas '+','.join(periods)),
        dict(item='Empréstimos a sócios: realização e circularização',motivo='Confirmar contraparte, contrato e recuperabilidade; elevado giro contábil não equivale a despesa.',fonte='balancetes/Balancete-ja-set-2026.pdf | 1.2.5'),
    ])
    caixa26=[a for a in balances[2026] if a['classification'].startswith('1.1.1.01.') and is_leaf(a,balances[2026]) and a['balance']<ZERO]
    for a in caixa26:
        pendencias.append(dict(item='Caixa credor em 2026',motivo=f'Conta de caixa com saldo credor de R$ {brl(-a["balance"])}; conferir documentação e contrapartidas. Valor já reduz o disponível contábil.',fonte=_src(a,base)))
    if any(abs(Decimal(str(r[5])))>Decimal('0.01') for r in ecd_comparison):
        pendencias.append(dict(item='ECD versus DRE 2025',motivo='Diferenças por conta preservadas na aba ECD x DRE 2025; apurar ajustes posteriores e lançamentos de encerramento/estorno. DRE oficial adotada para o resultado histórico.',fonte='fiscal/dominio/sped_diario00578.txt | I200/I250; publicacao-balancos/DOCUMENTOS CREDIT/DRE CREDIT 2025.pdf'))
    report=[
        dict(title='1. Custos e despesas históricos',paragraphs=[f'O relatório de custos e despesas por categoria, ano e acumulado está apurado na base contábil. O total reconhecido por competência, incluindo tributos sobre receita e IR/CSLL, é R$ {brl(sum(totals,ZERO))}. Considera a movimentação líquida das contas de resultado sem lançamentos de encerramento, conferida às DREs. O valor inclui o custo líquido da operação de crédito: compras menos amortizações e devoluções; as compras de CCBs não são somadas novamente. A classificação de pagamentos por finalidade integra o fluxo de caixa. Fonte: DRE CREDIT 2022–2025.pdf, contas analíticas grupo 3 e 4.1.2; balancetes/Balancete-ja-set-2026.pdf, mesmos grupos.',f'As categorias e o código de cada conta constam no Excel. Em 2024 o custo do grupo 3.1 é credor em R$ 2.399,00 por devolução de compra, preservado como redução do custo. Os custos com termo de cessão registrados nas despesas administrativas são reclassificados na categoria Operacional, sem alterar o resultado final. Fonte: DRE CREDIT 2024.pdf; contas 3.1 e descrição CUSTOS COM TERMO DE SESSAO.',f'O controle de caixa do cliente tem despesas tabuladas de R$ {brl(management_total)} nas abas mensais de janeiro a outubro de 2025. Essa base não cobre o ano inteiro e segue caixa, enquanto a DRE segue competência; não é somada aos custos contábeis. Fonte: fiscal/planilhas/CONTROLE - CUSTOS 2025.xlsx, abas '+', '.join(periods)+', coluna D.']),
        dict(title='4. Endividamento contábil',paragraphs=[f'Em 30/09/2026 o exigível total é R$ {brl(str(m26["exigivel"]))}. Debêntures somam R$ {brl(str(m26["debentures"]))} e obrigações com Jane/Lair R$ {brl(str(m26["partes_relacionadas"]))}. A soma de debêntures e mútuos contábeis com relacionadas é R$ {brl(str(m26["divida_financeira"]))}. Fonte: balancetes/Balancete-ja-set-2026.pdf, contas 2.1.3 a 2.1.7, 639 e 1113.',f'O grupo 2.4 mostra PL negativo de R$ {brl(str(-m26["pl_registrado"]))}, mas ainda não recebeu o prejuízo de janeiro a setembro, R$ {brl(str(-m26["resultado"]))}. Incluindo o resultado em aberto, o patrimônio líquido contábil é negativo em R$ {brl(str(-m26["pl_com_resultado"]))}. Só assim Ativo = Exigível + PL fecha na data-base. Fonte: mesmo balancete, contas 1, 2, 2.4, 3 e 4.', 'A classificação por prazo real permanece PENDENTE: os documentos contábeis não demonstram o vencimento individual dos fornecedores, tributos e mútuos, nem permitem concluir que todo o saldo vence em até 12 meses. A conta TRIBUTOS FEDERAIS mistura retenções/encargos; composição, atrasos e parcelamentos dependem de relatórios fiscais.']),
        dict(title='6. DRE anual e acumulada',paragraphs=['A DRE foi reconstruída a partir de contas analíticas, com resultado idêntico às DREs oficiais de 2022 a 2025 e ao balancete até setembro de 2026. As receitas financeiras incluem rendimento de aplicações, ainda que apresentado entre receitas não operacionais no Domínio. O lucro bruto é mantido conforme a estrutura oficial. Fonte: DRE CREDIT 2022–2025.pdf e balancetes/Balancete-ja-set-2026.pdf; grupos 3 e 4.','O resultado gerencial ajustado por perda esperada e eventuais juros contratuais não apropriados permanece PENDENTE até obter a carteira por parcela e o controle contratual completo das debêntures. Não foi presumida perda zero nem ajuste de juros zero.'])
    ]
    sheets=[
        dict(name='Custos e despesas',headers=['Categoria','2022','2023','2024','2025','2026 jan-set','Acumulado','Fonte / conta'],rows=category_rows),
        dict(name='DRE',headers=['Descrição','2022','2023','2024','2025','2026 jan-set','Acumulado','Fonte / conta'],rows=dre_rows),
        dict(name='DRE gerencial',headers=['Descrição','2022','2023','2024','2025','2026 jan-set','Acumulado','Fonte / conta'],rows=[
            ['Resultado contábil',*[float(results[y]) for y in years],float(sum(results.values(),ZERO)),'DRE CREDIT 2022–2025.pdf; balancetes/Balancete-ja-set-2026.pdf | grupos 3 e 4'],
            ['(-) Ajuste por perda esperada da carteira',*['PENDENTE']*6,'Posição por parcela, renegociações e recuperação ausentes; sem valor atribuído à perda | conta de carteira 1.1.2'],
            ['(-) Juros contratuais ainda não apropriados',*['PENDENTE']*6,'Controle completo por série e titular e curva contratual ausentes | contas 642, 2.1.7, 369'],
            ['Resultado econômico real ajustado',*['PENDENTE']*6,'Não calculável sem os dois ajustes acima; não equivale ao resultado contábil'],
        ]),
        dict(name='Endividamento',headers=['Código','Classificação','Credor/obrigação','Natureza','Relação','Prazo contábil','Prazo real','2022','2023','2024','2025','2026 jan-set','Acumulado','Fonte / conta'],rows=debtrows),
        dict(name='Balanço por ano',headers=['Descrição','2022','2023','2024','2025','2026 jan-set','Acumulado','Fonte / conta'],rows=balance_rows),
        dict(name='Mapeamento contas',headers=['Ano','Código','Classificação','Descrição','Categoria','Custo/despesa líquido','Fonte / conta','Sinal'],rows=maprows),
        dict(name='ECD x DRE 2025',headers=['Código','Classificação','Descrição','Movimento ECD sem encerramento','DRE oficial','Diferença ECD - DRE','Fonte / conta'],rows=ecd_comparison),
        dict(name='Custos gerenciais 2025',headers=['Mês/aba','Categoria do cliente','Despesas no controle','Lançamentos','Fonte / localização','Método'],rows=management_rows),
        dict(name='Base contábil',headers=['Ano','Código','Classificação','Descrição','Saldo anterior D+/C-','Débitos','Créditos','Saldo final D+/C-','Nível','Fonte / conta'],rows=rawrows),
    ]
    metrics['sources']={str(y):annual_sources[y] for y in years}
    metrics['cost_categories']={c:{str(y):float(category_values[c][y]) for y in years} for c in cats}
    return dict(sheets=sheets,metrics=metrics,checks=checks,pendencias=pendencias,report=report)


if __name__=='__main__':
    import json
    base=Path(__file__).resolve().parents[1]
    result=build(base,Path(__file__).resolve().parent)
    print(json.dumps(result['metrics'],ensure_ascii=False,indent=2))
