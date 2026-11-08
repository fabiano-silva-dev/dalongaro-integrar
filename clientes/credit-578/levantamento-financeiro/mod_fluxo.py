"""Fluxo acumulado pelos balancetes; partidas de 2025 são detalhe opcional.

Os débitos/créditos do disponível são movimentos contábeis brutos, com
transferências internas incluídas. Não são apresentados como fluxos externos.
"""
from pathlib import Path
from decimal import Decimal
from collections import defaultdict
from datetime import datetime
import re
import unicodedata
from openpyxl import load_workbook

D=Decimal
def money(s):
    if isinstance(s,(int,float,Decimal)): return D(str(s))
    return D(re.sub(r'[^0-9,.-]','',str(s)).replace('.','').replace(',','.'))

def ecd(base):
    path=base/'fiscal/dominio/sped_diario00578.txt'
    plan={}; entries=[]; balances=[]; cur=None; period=''
    if not path.exists():
        return plan,entries,balances
    for line_no,line in enumerate(path.read_bytes().decode('latin1').splitlines(),1):
        p=line.split('|')
        if len(p)<3:continue
        if p[1]=='I050':plan[p[6]]={'parent':p[7],'name':p[8],'type':p[4]}
        elif p[1]=='I150':period=p[2][4:]+p[2][2:4]
        elif p[1]=='I155':balances.append((period,p))
        elif p[1]=='I200':
            cur={'id':p[2],'date':datetime.strptime(p[3],'%d%m%Y').date().isoformat(),'lines':[],'line':line_no};entries.append(cur)
        elif p[1]=='I250' and cur is not None:
            cur['lines'].append({'code':p[2],'value':money(p[4]),'side':p[5],'hist':p[8] if len(p)>8 else '', 'line':line_no})
    return plan,entries,balances

def ancestor(code,target,plan):
    seen=set()
    while code and code not in seen:
        if code==target:return True
        seen.add(code);code=plan.get(code,{}).get('parent','')
    return False

def normalized(value):
    return ''.join(c for c in unicodedata.normalize('NFD',str(value)) if not unicodedata.combining(c)).upper()

def category(code,plan,classifications=None):
    """Classifica no namespace da ECD, enriquecido pelo balancete do mesmo ano.

    Nome pessoal não revela se a conta é mútuo passivo ou empréstimo no ativo;
    nesse caso a classificação do BP prevalece sobre o histórico textual.
    """
    name=normalized(plan.get(code,{}).get('name',''))
    cl=(classifications or {}).get(code,'')
    if cl.startswith('1.2.5') or 'EMPRESTIMO A SOCIOS' in name or 'EMPRESTIMOS A SOCIOS' in name:return 'Empréstimos a sócios'
    if ancestor(code,'12',plan):return 'Recebimentos/compra de direitos creditórios'
    if cl.startswith('2.1.7') or ancestor(code,'160',plan):return 'Captação / baixa de debêntures'
    if any(x in name for x in ['JANE HARTMANN','LAIR JOSE']) and ancestor(code,'149',plan):return 'Recursos de Jane e Lair'
    if 'AUMENTO DE CAPITAL' in name or ancestor(code,'243',plan):return 'Aportes / AFAC'
    if any(x in name for x in ['ALUGU','CONDOM','ENERGIA']):return 'Ocupação'
    if cl.startswith('3.2.2.01') or any(x in name for x in ['SALAR','FGTS','INSS','FERI','RESCIS','VALE TRANSP','ESTAGIO','ASSISTENCIA MEDICA']):return 'Pessoal e encargos'
    if ancestor(code,'367',plan) or any(x in name for x in ['TARIFA','DESPESAS BANCARIAS','IOF','JUROS','APLICAC','RENDIMENTO','DESCONTO']):return 'Financeiro / rendimentos'
    if ancestor(code,'170',plan) or any(x in name for x in ['IRPJ','CSLL','COFINS','PIS','ISS','IRRF','IMPOST','TRIBUT','CONTRIBUICAO SOCIAL','MULTAS','TAXAS','EMOLUMENTOS','CARTORIO']):return 'Tributos'
    if any(x in name for x in ['SOFTWARE','INTERNET','TELEFONE']):return 'Tecnologia'
    if any(x in name for x in ['MIDIA','PROPAGANDA','BRINDES','PUBLICIDADE']):return 'Comercial / vendas'
    if any(x in name for x in ['TERCEIROS','LEGAIS E JUDICIAIS','CONTABIL','ADVOCAT']):return 'Serviços de terceiros'
    if 'INDEDUT' in name:return 'Indedutíveis'
    if any(x in name for x in ['COMPRA DE SESSAO','COMPRA DE RECEB','CESSAO']):return 'Compra de créditos / operação'
    if 'VIA CAPITAL' in name or 'HBI SOCIEDADE DE CREDITO' in name:return 'Pagamentos/recebimentos de originadoras'
    if ancestor(code,'164',plan):return 'Fornecedores'
    if ancestor(code,'1',plan):return 'Outros ativos / créditos'
    if ancestor(code,'149',plan):return 'Outras obrigações'
    return 'Outras contrapartidas identificadas'

def _check(test,year,calculated,reference,source):
    difference=calculated-reference
    return dict(teste=test,ano=year,calculado=float(calculated),referencia=float(reference),
                diferenca=float(difference),status='OK' if abs(difference)<=D('.01') else 'DIVERGÊNCIA',fonte=source)


def _position(row):
    opening,debit,credit,balance=(D(row[k]) for k in ['opening','debit','credit','balance'])
    return dict(opening=opening,debit=debit,credit=credit,net=debit-credit,balance=balance)


def _serial(position):
    return {key:float(value) if isinstance(value,D) else value for key,value in position.items()}


def _recursos_socios_2025(plan,entries,source):
    """Identifica financiamento em banco sem reutilizar as partidas expandidas.

    Uma linha pessoal só recebe efeito bancário quando todas as contrapartidas
    estão do lado oposto e sua soma fecha o lançamento. Créditos contra outras
    obrigações, sem banco CSG, não são dinheiro recebido pela companhia.
    """
    people={'1113':'Jane','639':'Lair'}
    fields=['entradas','saidas','liquido','emprestimo_descrito','afac_descrito','outros_creditos']
    totals={person:{key:D(0) for key in fields} for person in people.values()}
    noncash={person:dict(creditos=D(0),debitos=D(0)) for person in people.values()}
    banks={code for code,info in plan.items() if info['type']=='A' and ancestor(code,'7',plan)}
    events=[];capital_events=[];noncash_events=[];unallocated=[];capital=D(0)
    for entry in entries:
        if not entry['date'].startswith('2025-'):
            continue
        personal=[line for line in entry['lines'] if line['code'] in people]
        capital_lines=[line for line in entry['lines'] if line['code']=='247' and 'JANE' in normalized(line['hist'])
                       and 'CAPITAL' in normalized(line['hist'])]
        if not personal and not capital_lines:
            continue
        bank=[line for line in entry['lines'] if line['code'] in banks]
        bank_net=sum((line['value']*(1 if line['side']=='D' else -1) for line in bank),D(0))
        other=[line for line in entry['lines'] if line['code'] not in banks]
        opposite='C' if bank_net>0 else 'D'
        exact=bool(bank_net and other and all(line['side']==opposite for line in other)
                   and sum((line['value'] for line in other),D(0))==abs(bank_net))
        for line in personal:
            person=people[line['code']]
            description=line['hist']
            provenance=(f'{source} | I200 {entry["id"]}, linha {entry["line"]}; '
                        f'I250 conta {line["code"]}, linha {line["line"]}')
            if not bank:
                noncash[person]['creditos' if line['side']=='C' else 'debitos']+=line['value']
                noncash_events.append(dict(date=entry['date'],entry=entry['id'],pessoa=person,
                                           credito=float(line['value']) if line['side']=='C' else 0.0,
                                           debito=float(line['value']) if line['side']=='D' else 0.0,
                                           description=description,source=provenance))
                continue
            if not exact:
                unallocated.append(dict(date=entry['date'],entry=entry['id'],pessoa=person,
                                        description=description,source=provenance,
                                        motivo='Lançamento bancário composto sem atribuição individual exata; não rateado'))
                continue
            amount=line['value']
            incoming=amount if bank_net>0 else D(0)
            outgoing=amount if bank_net<0 else D(0)
            totals[person]['entradas']+=incoming;totals[person]['saidas']+=outgoing
            history=normalized(description)
            if incoming:
                if re.search(r'\bAFAC\b',history) or ('ADIANTAMENTO' in history and 'CAPITAL' in history):
                    nature='AFAC descrito no histórico; crédito na conta pessoal'
                    totals[person]['afac_descrito']+=incoming
                elif 'EMPRESTIMO' in history:
                    nature='Empréstimo descrito no histórico'
                    totals[person]['emprestimo_descrito']+=incoming
                else:
                    nature='Outro crédito bancário na conta pessoal; instrumento não definido'
                    totals[person]['outros_creditos']+=incoming
            else:
                nature='Saída bancária contra a conta pessoal; não presumida amortização contratual'
            bank_source='; I250 banco '+','.join(f'{b["code"]} linha {b["line"]}' for b in bank)
            events.append(dict(date=entry['date'],entry=entry['id'],pessoa=person,conta=line['code'],
                               entrada=float(incoming),saida=float(outgoing),description=description,
                               natureza=nature,source=provenance+bank_source))
        if exact and bank_net>0:
            for line in capital_lines:
                capital+=line['value']
                capital_events.append(dict(date=entry['date'],entry=entry['id'],pessoa='Jane',conta='247',
                                           entrada=float(line['value']),saida=0.0,description=line['hist'],
                                           natureza='Integralização de capital; separada das contas 1113 e 639',
                                           source=f'{source} | I200 {entry["id"]}, linha {entry["line"]}; I250 conta 247, linha {line["line"]}; '
                                                  +'I250 banco '+','.join(f'{b["code"]} linha {b["line"]}' for b in bank)))
    for values in totals.values():
        values['liquido']=values['entradas']-values['saidas']
    income=sum((values['entradas'] for values in totals.values()),D(0))
    payments=sum((values['saidas'] for values in totals.values()),D(0))
    result=dict(por_pessoa={person:_serial(values) for person,values in totals.items()},
                entradas=float(income),saidas=float(payments),liquido=float(income-payments),
                capital_jane_fora_1113=float(capital),fonte=source+' | I200/I250, bancos sob 1.1.1.02; contas 1113/639; capital 247 separado',
                eventos=events,eventos_capital_jane=capital_events,
                movimentos_sem_caixa_csg={person:_serial(values) for person,values in noncash.items()},
                eventos_sem_caixa_csg=noncash_events,eventos_a_classificar=unallocated)
    return result


def _balancetes(base):
    """Totais e contas analíticas, com controles independentes da ECD."""
    from mod_contabilidade import parse_balancete,is_leaf
    periods={};outside={};accounts_by_year={};control=[];analytical=[];checks=[]
    previous_groups={};previous_accounts={}
    fields=['opening','debit','credit','balance']
    for year in range(2022,2027):
        path=base/('balancetes/Balancete-ja-set-2026.pdf' if year==2026 else f'publicacao-balancos/DOCUMENTOS CREDIT/BALANCETE CREDIT {year}.pdf')
        relative=str(path.relative_to(base));accounts=parse_balancete(path);accounts_by_year[year]=accounts
        for prefix in ['1.1.1','1.1.4']:
            scope='Disponível 1.1.1' if prefix=='1.1.1' else 'Aplicações 1.1.4 fora do disponível'
            groups=[r for r in accounts if r['classification']==prefix]
            leaves=[r for r in accounts if r['classification'].startswith(prefix+'.') and is_leaf(r,accounts)]
            if len(groups)>1:
                raise ValueError(f'Grupo {prefix} duplicado em {relative}')
            if not groups:
                if prefix=='1.1.1' or leaves:
                    raise ValueError(f'Grupo {prefix} não localizado em {relative}')
                # O grupo de aplicações encerrado deixa de constar no balancete;
                # essa ausência é exposta, sem incorporá-lo ao disponível.
                position={key:D(0) for key in ['opening','debit','credit','net','balance']}
                position.update(source=relative,page=None,account=prefix,present=False,
                                note='Grupo 1.1.4 não consta neste balancete; zero na apresentação, separado de 1.1.1')
                outside[str(year)]=position
                if prefix in previous_groups:
                    old=previous_groups[prefix]
                    checks.append(_check('Continuidade 1.1.4 sem rubrica no ano: abertura apresentada = saldo anterior',year,
                                         position['opening'],old['balance'],relative+' | 1.1.4 não consta; '+old['source']+' | 1.1.4'))
                previous_groups[prefix]=position
                continue
            group=groups[0];position=_position(group)
            source=f'{relative} | p. {group["page"]} | conta {group["code"]} ({prefix})'
            position.update(source=relative,page=group['page'],account=prefix,present=True,
                            note='Movimentação bruta; transferências internas incluídas' if prefix=='1.1.1' else 'Aplicações fora de 1.1.1; não somadas ao disponível')
            if prefix=='1.1.1':
                periods[str(year)]=position
                opening,debit,credit,balance=(position[k] for k in fields)
                control.append([year,float(opening),float(debit),float(credit),float(opening+debit-credit),float(balance),float(opening+debit-credit-balance),
                                'APURADO pelos balancetes; bruto, com transferências internas incluídas; não equivale a entradas/saídas externas',relative,prefix])
            else:
                outside[str(year)]=position
            checks.append(_check(f'Balancete {prefix}: abertura + débitos - créditos = saldo final',year,
                                 position['opening']+position['debit']-position['credit'],position['balance'],source))
            if not leaves:
                raise ValueError(f'Contas analíticas de {prefix} não localizadas em {relative}')
            for field in fields:
                checks.append(_check(f'Soma das contas analíticas {prefix}: {field}',year,
                                     sum((D(r[field]) for r in leaves),D(0)),position[field],source+'; contas analíticas da aba Caixa por conta'))
            if prefix in previous_groups:
                old=previous_groups[prefix]
                checks.append(_check(f'Continuidade {prefix}: abertura = saldo final do ano anterior',year,
                                     position['opening'],old['balance'],source+'; '+old['source']+' | mesmo grupo'))
            previous_groups[prefix]=position
            for row in leaves:
                value=_position(row)
                row_source=f'{relative} | p. {row["page"]} | conta {row["code"]} ({row["classification"]})'
                analytical.append([year,scope,row['code'],row['classification'],row['description'],
                                   *[float(value[k]) for k in ['opening','debit','credit','net','balance']],
                                   'D positivo / C negativo nos saldos; movimentos de débito/crédito positivos',row_source])
                checks.append(_check('Conta analítica: abertura + débitos - créditos = saldo final',year,
                                     value['opening']+value['debit']-value['credit'],value['balance'],row_source))
                key=(prefix,row['code'])
                old=previous_accounts.get(key)
                if old and old['year']==year-1:
                    checks.append(_check('Continuidade da conta analítica entre anos',year,value['opening'],old['balance'],row_source+'; '+old['source']))
                previous_accounts[key]=dict(year=year,balance=value['balance'],source=row_source)
    accumulated=dict(opening=periods['2022']['opening'],
                     debit=sum((p['debit'] for p in periods.values()),D(0)),
                     credit=sum((p['credit'] for p in periods.values()),D(0)),
                     net=sum((p['net'] for p in periods.values()),D(0)),
                     balance=periods['2026']['balance'])
    source='; '.join(f'{p["source"]} | p. {p["page"]} | 1.1.1' for p in periods.values())
    checks.append(_check('Fluxo acumulado dos balancetes: abertura + débitos - créditos = posição final','2022 a set/2026',
                         accumulated['opening']+accumulated['debit']-accumulated['credit'],accumulated['balance'],source))
    checks.append(_check('Fluxo acumulado dos balancetes: variação = saldo final - saldo inicial','2022 a set/2026',
                         accumulated['net'],accumulated['balance']-accumulated['opening'],source))
    labels=[('Saldo inicial do disponível R$','opening'),('Débitos no disponível: movimentos contábeis R$','debit'),
            ('Créditos no disponível: movimentos contábeis R$','credit'),('Variação líquida do disponível R$','net'),('Saldo final do disponível R$','balance')]
    notes={'opening':'Acumulado = saldo inicial de 2022; não soma saldos de abertura.',
           'debit':'Soma dos débitos de 1.1.1; inclui transferências internas e não equivale a entradas externas.',
           'credit':'Soma dos créditos de 1.1.1; inclui transferências internas e não equivale a saídas externas.',
           'net':'Débitos menos créditos; acumulado = soma das variações de cada período.',
           'balance':'Acumulado = posição final de setembro/2026; não soma saldos de encerramento.'}
    flow_rows=[[label,*[float(periods[str(y)][key]) for y in range(2022,2027)],float(accumulated[key]),source,notes[key]] for label,key in labels]
    return dict(periods=periods,outside=outside,accumulated=accumulated,accounts=accounts_by_year,
                control=control,analytical=analytical,checks=checks,flow_rows=flow_rows,source=source)


def _category_annual(event):
    cl=event['classificacao'];code=event['codigo_conta'];name=normalized(event['nome_conta'])
    if cl.startswith('1.2.5'):return 'Créditos com sócios'
    if cl.startswith('1.1.4'):return 'Aplicações fora do disponível'
    if cl.startswith('1.1.2'):return 'Recebimentos e operações da carteira'
    if cl.startswith('2.1.7'):return 'Captação e liquidação de debêntures'
    if code in ['1113','639']:return 'Recursos de Jane e Lair'
    if cl.startswith('2.4') or code=='1328':return 'Capital AFAC e outras movimentações do PL'
    if code=='651' or cl.startswith('2.1.4'):return 'Tributos e retenções'
    if cl.startswith('2.1.5') or cl.startswith('3.2.2.01'):return 'Pessoal e encargos'
    if cl.startswith('2.1.3'):
        return 'Originadoras de crédito' if any(x in name for x in ['VIA CAPITAL','UY3','HBI SOCIEDADE']) else 'Fornecedores'
    if cl.startswith('3.1') or 'CUSTOS COM TERMO' in name:return 'Aquisição e custos de créditos'
    if cl.startswith(('3.2.2.05','4.1.3','4.2.1.04')):return 'Financeiro e rendimentos'
    if any(x in name for x in ['ALUGU','CONDOM','ENERGIA']):return 'Ocupação'
    if any(x in name for x in ['SOFTWARE','INTERNET','TELEFONE']):return 'Tecnologia'
    if any(x in name for x in ['MIDIA','PROPAGANDA','BRINDES','PUBLICIDADE']):return 'Comercial e vendas'
    if any(x in name for x in ['IMPOST','IRPJ','CSLL','COFINS','PIS','ISS','IRRF','MULTAS','TAXAS','CARTORIO']):return 'Tributos e retenções'
    if any(x in name for x in ['CONTABIL','ADVOCAT','TERCEIROS','LEGAIS E JUDICIAIS']):return 'Serviços de terceiros'
    if 'INDEDUT' in name:return 'Indedutíveis'
    if cl.startswith('1.'):return 'Outros ativos e créditos'
    if cl.startswith('2.'):return 'Outras obrigações'
    if cl.startswith('3.'):return 'Demais despesas da operação'
    if cl.startswith('4.'):return 'Outras receitas e recebimentos'
    return 'Outras contrapartidas identificadas'


def _annual_cash(base,out,principal):
    """Compensa as linhas do disponível por lote sem inventar rateios.

    A implantação de saldos fica fora dos recebimentos/pagamentos. Linhas
    de mesma data/lote só são abertas por contrapartida quando o lançamento
    inteiro fecha e todas as contrapartidas estão no lado oposto ao caixa.
    """
    import mod_razoes
    annual=mod_razoes.load(base,out)
    checks=[];groups=defaultdict(lambda:defaultdict(lambda:[0,0]));periods={};exceptions=[];transitions=[]
    source_by_year={}
    for year,data in annual['years'].items():
        batches=defaultdict(list)
        for e in data['events']:batches[(e['data'],e['lote'])].append(e)
        source='balancetes/Razão'+year+'.xls';source_by_year[year]=source
        p=dict(debit=0,credit=0,incoming=0,outgoing=0,transition_net=0,zero_debit=0,zero_credit=0,
               cash_batches=0,zero_batches=0,mixed_batches=0,transition_batches=0)
        def assign(cat,net):groups[cat][year][0 if net>0 else 1]+=abs(net)
        for (day,lot),events in batches.items():
            cash=[e for e in events if e['classificacao'].startswith('1.1.1.')]
            if not cash:continue
            p['cash_batches']+=1
            de=sum(e['debito_centavos'] for e in cash);cr=sum(e['credito_centavos'] for e in cash);net=de-cr
            p['debit']+=de;p['credit']+=cr
            non=[e for e in events if not e['classificacao'].startswith('1.1.1.')]
            lines=','.join(str(e['linha']) for e in cash)
            provenance=f'{source} | aba Razão, linhas de disponível {lines}; lote {lot}; contrapartidas no índice dos razões anuais'
            if not net:
                p['zero_batches']+=1;p['zero_debit']+=de;p['zero_credit']+=cr
                continue
            implanted=any(normalized(e['historico']).strip().startswith(('SALDO FINAL EM','SALDO INICIAL EM')) for e in events)
            if implanted:
                p['transition_net']+=net;p['transition_batches']+=1
                transitions.append([year,day,str(lot),len(events),de/100,cr/100,net/100,
                                    'Implantação/ajuste de saldos; não apresentado como captação, recebimento ou pagamento',provenance])
                continue
            p['incoming']+=max(net,0);p['outgoing']+=max(-net,0)
            balanced=sum(e['debito_centavos']-e['credito_centavos'] for e in events)==0
            side='credito_centavos' if net>0 else 'debito_centavos';other='debito_centavos' if net>0 else 'credito_centavos'
            exact=balanced and bool(non) and all(not e[other] for e in non) and sum(e[side] for e in non)==abs(net)
            if exact:
                for e in non:
                    if e[side]:assign(_category_annual(e),e[side] if net>0 else -e[side])
                continue
            discounts=[e for e in non if normalized(e['nome_conta']).strip()=='DESCONTOS FINANCEIROS OBTIDOS' and e['credito_centavos'] and not e['debito_centavos']]
            expenses=[e for e in non if e not in discounts]
            kinds={_category_annual(e) for e in expenses}
            exact_discount=(balanced and net<0 and discounts and expenses and len(kinds)==1
                            and all(e['classificacao'].startswith('3.') and not e['credito_centavos'] for e in expenses)
                            and sum(e['debito_centavos'] for e in expenses)-sum(e['credito_centavos'] for e in discounts)==abs(net))
            if exact_discount:
                assign(next(iter(kinds)),net);continue
            kinds={_category_annual(e) for e in non}
            if balanced and len(kinds)==1:
                assign(next(iter(kinds)),net);continue
            p['mixed_batches']+=1
            assign('Partidas mistas com finalidade individual a detalhar',net)
            exceptions.append([year,day,str(lot),net/100,len(non),
                               'Lote composto: efeito líquido preservado; não rateado entre finalidades' if balanced else 'Partida sem abertura completa no conjunto exportado',
                               provenance])
        actual=principal['periods'][year]
        p['net']=p['debit']-p['credit'];p['source']=source
        periods[year]=p
        for label,key in [('débitos','debit'),('créditos','credit'),('variação líquida','net')]:
            checks.append(_check('Razão anual disponível × balancete: '+label,year,D(p[key])/100,actual[key],source+' | 1.1.1; '+actual['source']))
        classified=sum(v[year][0]-v[year][1] for v in groups.values())
        checks.append(_check('Movimentos compensados + implantação = variação do disponível',year,
                             D(classified+p['transition_net'])/100,actual['net'],source+' | lotes e grupo 1.1.1'))
    years=[str(y) for y in range(2022,2027)]
    source='; '.join(source_by_year.values())
    netrows=[];grossrows=[]
    for cat,values in sorted(groups.items()):
        netrows.append([cat,*[(values[y][0]-values[y][1])/100 for y in years],sum(values[y][0]-values[y][1] for y in years)/100,source,
                        'Movimentos líquidos por lote; implantação de saldos separada; não rateia partidas mistas'])
        grossrows.append([cat,*[v/100 for y in years for v in values[y]],sum(values[y][0] for y in years)/100,sum(values[y][1] for y in years)/100])
    yearrows=[[int(y),principal['periods'][y]['opening'],p['incoming']/100,p['outgoing']/100,p['transition_net']/100,p['net']/100,
               principal['periods'][y]['balance'],p['zero_debit']/100,p['cash_batches'],p['mixed_batches'],p['source']] for y,p in periods.items()]
    sheets=[dict(name='Fluxo por finalidade',headers=['Finalidade identificada','2022','2023','2024','2025','2026 jan-set','Acumulado','Fonte','Tratamento'],rows=netrows),
            dict(name='Fluxo por período',headers=['Ano','Saldo inicial R$','Entradas compensadas por lote R$','Saídas compensadas por lote R$','Implantação e ajustes R$','Variação total R$','Saldo final R$','Débitos em lotes de efeito zero R$','Lotes com disponível','Lotes mistos','Fonte'],rows=yearrows),
            dict(name='Fluxo entradas saídas',headers=['Finalidade',*[f'{y} {label} R$' for y in years for label in ['entradas','saídas']],'Entradas acumuladas R$','Saídas acumuladas R$'],rows=grossrows),
            dict(name='Fluxo transição',headers=['Ano','Data','Lote','Linhas no lote','Débitos disponível R$','Créditos disponível R$','Efeito líquido R$','Tratamento','Fonte'],rows=transitions),
            dict(name='Fluxo exceções',headers=['Ano','Data','Lote','Efeito líquido disponível R$','Contrapartidas','Tratamento','Fonte'],rows=exceptions)]
    serial={y:{k:(v/100 if k in ['debit','credit','incoming','outgoing','transition_net','zero_debit','zero_credit','net'] else v) for k,v in p.items()} for y,p in periods.items()}
    totals={k:sum(p[k] for p in periods.values())/100 for k in ['incoming','outgoing','transition_net','net','debit','credit']}
    return dict(sheets=sheets,checks=checks,metrics=dict(years=serial,accumulated=totals,source=source,mixed_batches=len(exceptions),transition_batches=len(transitions)),
                pendencias=[dict(item='Finalidade individual de partidas mistas dos razões anuais',motivo=f'{len(exceptions)} lotes preservam efeito líquido de caixa, mas exigem abertura específica da finalidade das contrapartidas; valores e fontes na aba Fluxo exceções.',fonte=source)] if exceptions else [])


def build(base:Path,out:Path):
    base=Path(base)
    principal=_balancetes(base)
    plan,entries,balances=ecd(base)
    ecd_available=(base/'fiscal/dominio/sped_diario00578.txt').exists()
    classes={r['code']:r['classification'] for r in principal['accounts'][2025]}
    src='fiscal/dominio/sped_diario00578.txt'
    cashcodes={c for c,v in plan.items() if v['type']=='A' and ancestor(c,'3',plan)}
    detail=[]; groups=defaultdict(lambda:[D(0),D(0)]); excluded=0; opened=0; mixed=0; discounts_net=0
    def append_detail(e,cash,non,cat,value,method):
        groups[cat][0 if value>0 else 1]+=abs(value)
        accounts='; '.join(sorted({l['code']+' '+plan.get(l['code'],{}).get('name','') for l in non}))
        lines=','.join(str(l['line']) for l in non)
        source=f'{src}: I200 linha {e["line"]}; I250 contrapartida linhas {lines}; {method}'
        detail.append([e['date'],e['id'],cat,float(max(value,D(0))),float(max(-value,D(0))),accounts,' | '.join(dict.fromkeys(l['hist'] for l in non+cash)),source,'1.1.1 / ECD '+','.join(sorted({l['code'] for l in cash}))])
    for e in entries:
        cash=[l for l in e['lines'] if l['code'] in cashcodes]
        if not cash:continue
        net=sum((l['value']*(1 if l['side']=='D' else -1) for l in cash),D(0))
        if not net:excluded+=1;continue
        non=[l for l in e['lines'] if l['code'] not in cashcodes]
        kinds={category(l['code'],plan,classes) for l in non}
        # Só repartir o efeito de caixa quando todas as contrapartidas estão
        # no lado oposto e sua soma reconcilia exatamente. Um desconto debitado
        # contra recebimento não vira uma saída de dinheiro fictícia.
        opposite='C' if net>0 else 'D'
        can_open=non and all(l['side']==opposite for l in non) and sum((l['value'] for l in non),D(0))==abs(net)
        if len(non)>1 and can_open:
            opened+=1
            assigned=D(0)
            for line in non:
                value=line['value']*(1 if net>0 else -1)
                append_detail(e,cash,[line],category(line['code'],plan,classes),value,'Partida composta aberta por contrapartida; mesmo lado, soma exata')
                assigned+=value
            if assigned!=net:raise ValueError('Alocação de caixa não fecha: I200 '+e['id'])
        else:
            # Desconto financeiro obtido reduz o pagamento da mesma despesa;
            # o crédito da receita não é uma entrada bancária separada.
            discount=[l for l in non if normalized(plan.get(l['code'],{}).get('name',''))=='DESCONTOS FINANCEIROS OBTIDOS' and l['side']=='C']
            expense=[l for l in non if l not in discount]
            expense_kinds={category(l['code'],plan,classes) for l in expense}
            exact_discount=(net<0 and discount and expense and all(l['side']=='D' and classes.get(l['code'],'').startswith('3.') for l in expense)
                            and len(expense_kinds)==1 and sum((l['value'] for l in expense),D(0))-sum((l['value'] for l in discount),D(0))==abs(net))
            if exact_discount:
                discounts_net+=1
                append_detail(e,cash,non,next(iter(expense_kinds)),net,'Pagamento líquido de desconto obtido; desconto sem entrada bancária própria')
                continue
            cat=next(iter(kinds)) if len(kinds)==1 else 'Contrapartidas mistas - classificação PENDENTE'
            if len(kinds)>1:mixed+=1
            append_detail(e,cash,non,cat,net,'Efeito líquido preservado; sem repartição presumida')
    ecd_open=D(0);ecd_close=D(0)
    for per,p in balances:
        if p[2] in cashcodes:
            if per=='202501':ecd_open+=money(p[4])*(1 if p[5]=='D' else -1)
            if per=='202512':ecd_close+=money(p[8])*(1 if p[9]=='D' else -1)
    net=sum((a-b for a,b in groups.values()),D(0))
    checks=list(principal['checks'])
    if ecd_available:
        checks.append(_check('Complemento 2025: abertura + entradas - saídas = saldo auxiliar',2025,ecd_open+net,ecd_close,src+' | conta 1.1.1 / I050 descendentes de 3'))
        for label,value,key in [('Saldo inicial',ecd_open,'opening'),('Variação líquida',net,'net'),('Saldo final',ecd_close,'balance')]:
            checks.append(_check('Complemento 2025 × balancete: '+label,2025,value,principal['periods']['2025'][key],src+'; '+principal['periods']['2025']['source']+' | 1.1.1'))
    resources=_recursos_socios_2025(plan,entries,src) if ecd_available else None
    if resources is not None:
        ledger={r['code']:r for r in principal['accounts'][2025]}
        for code,person in [('1113','Jane'),('639','Lair')]:
            values=resources['por_pessoa'][person];without_cash=resources['movimentos_sem_caixa_csg'][person]
            provenance=resources['fonte']+'; '+principal['periods']['2025']['source']+' | conta '+code
            checks.append(_check('Recursos de '+person+': tipos descritos = entradas bancárias',2025,
                                 sum((D(str(values[k])) for k in ['emprestimo_descrito','afac_descrito','outros_creditos']),D(0)),
                                 D(str(values['entradas'])),provenance))
            if not any(e['pessoa']==person for e in resources['eventos_a_classificar']):
                checks.append(_check('Conta '+code+': créditos = entradas em banco + créditos sem caixa CSG',2025,
                                     D(str(values['entradas']))+D(str(without_cash['creditos'])),ledger[code]['credit'],provenance))
                checks.append(_check('Conta '+code+': débitos = saídas em banco + débitos sem caixa CSG',2025,
                                     D(str(values['saidas']))+D(str(without_cash['debitos'])),ledger[code]['debit'],provenance))
        for label,key,index in [('Entradas','entradas',0),('Saídas','saidas',1)]:
            checks.append(_check('Recursos de Jane e Lair: '+label+' por evento = complemento de caixa',2025,
                                 D(str(resources[key])),groups.get('Recursos de Jane e Lair',[D(0),D(0)])[index],resources['fonte']))
    flow=[];control=principal['control'];bankrows=[]
    for cat,(inc,pay) in sorted(groups.items()):
        flow.append([cat,'Fora deste complemento','Fora deste complemento','Fora deste complemento',float(inc-pay),'Fora deste complemento','Complemento de 2025',float(inc),float(pay),src+' I200/I250','1.1.1; ver Fluxo detalhes','Detalhe auxiliar opcional por finalidade de 2025; totais de todos os períodos em Fluxo acumulado'])
    for filename in ['05.2026.xlsx','06.2026.xlsx']:
        if not (base/filename).exists():
            continue
        wb=load_workbook(base/filename,read_only=True,data_only=True)
        for sh in wb.worksheets:
            for row_no,row in enumerate(sh.values,1):
                if row_no==1:continue
                if sh.title=='PIX' and row[0] is not None:
                    amount=None
                    try:amount=float(money(row[8]))
                    except Exception:pass
                    day=row[0].date().isoformat() if hasattr(row[0],'date') else str(row[0])
                    hist=str(row[7] or '');side=str(row[9] or '')
                    kind='SALDO (não fluxo)' if 'SALDO' in hist.upper() else ('Transação com D/C' if side in ['D','C'] else 'PENDENTE: sinal bancário não identificado')
                    bankrows.append([filename,sh.title,row_no,day,hist,side,amount,str(row[5] or ''),str(row[10] or ''),kind,'1.1.1: conta de origem a vincular; saldo conciliado pelo escritório'])
                elif sh.title=='BOLETOS' and row[1]:
                    try:amount=float(money(row[10]))
                    except Exception:amount=None
                    bankrows.append([filename,sh.title,row_no,str(row[8] or ''),str(row[1]),str(row[7] or ''),amount,str(row[6] or ''),'Nosso número: '+str(row[5] or ''),'Detalhe de cobrança: não somar aos créditos do extrato','1.1.2 / 1.1.1: vínculo contábil PENDENTE'])
        wb.close()
    sheets=[{'name':'Fluxo acumulado','headers':['Indicador','2022','2023','2024','2025','2026 jan-set','Acumulado','Fonte e conta','Critério'],'rows':principal['flow_rows']},
      {'name':'Caixa por conta','headers':['Ano','Escopo','Código','Classificação','Conta analítica','Saldo anterior R$','Débitos R$','Créditos R$','Variação líquida R$','Saldo final R$','Convenção de sinais','Fonte / página / conta'],'rows':principal['analytical']},
      {'name':'Fluxo direto','headers':['Natureza auxiliar de 2025 (líquido R$)','2022','2023','2024','2025','2026 jan-set','Acumulado','Entradas 2025','Saídas 2025','Fonte','Conta','Limitação'],'rows':flow},
      {'name':'Fluxo detalhes','headers':['Data','Lançamento','Natureza','Entrada R$','Saída R$','Contrapartidas ECD','Histórico','Fonte','Conta caixa'],'rows':detail},
      {'name':'Caixa saldos','headers':['Ano','Saldo anterior R$','Débitos R$','Créditos R$','Saldo calculado R$','Disponível R$','Diferença R$','Método','Fonte','Conta'],'rows':control},
      {'name':'Extratos parciais','headers':['Arquivo','Aba','Linha','Data','Histórico/devedor','Sinal/situação','Valor R$','Documento','Detalhe','Tratamento','Conta'],'rows':bankrows}]
    if resources is not None:
        sheets.append({'name':'Recursos dos sócios','headers':['Data','Pessoa / conta','Entrada R$','Saída R$','Descrição','Fonte e lançamento'],
                       'rows':[[e['date'],e['pessoa']+' / '+e['conta'],e['entrada'],e['saida'],
                                e['description']+' | '+e['natureza'],e['source']] for e in resources['eventos']]})
    accumulated=principal['accumulated']
    report=[{'title':'5. Fluxo de caixa acumulado - base nos balancetes','paragraphs':[
        f'APURADO para todos os períodos pelos balancetes: saldo inicial de R$ {brl(accumulated["opening"])}, débitos acumulados de R$ {brl(accumulated["debit"])}, créditos acumulados de R$ {brl(accumulated["credit"])}, variação líquida de R$ {brl(accumulated["net"])} e saldo final de R$ {brl(accumulated["balance"])}. Fonte: {principal["source"]}. A aba Fluxo acumulado apresenta cada ano e o acumulado; a aba Caixa por conta traz as contas analíticas e suas páginas de origem.',
        'Os débitos e créditos representam a movimentação contábil bruta do disponível, com transferências internas incluídas. Portanto, não são denominados entradas e saídas externas. Somam-se os débitos, créditos e variações de cada ano; o saldo inicial acumulado é o da abertura do primeiro período e o saldo final acumulado é a posição de setembro de 2026. Não se somam saldos patrimoniais de datas diferentes. Fonte: balancetes anuais de 2022 a 2025 e balancete de janeiro a setembro de 2026, grupo 1.1.1.',
        'A soma das contas analíticas foi conferida aos respectivos grupos, assim como abertura mais débitos menos créditos igual ao saldo final e continuidade entre os anos. Os saldos bancários foram confirmados como conciliados pelo escritório. A classificação por finalidade e a eliminação das transferências internas são detalhamentos complementares e não impedem a apuração dos totais acima.',
        'As aplicações classificadas em 1.1.4 estão apresentadas separadamente na aba Caixa por conta e nas métricas por ano; não foram somadas automaticamente ao disponível 1.1.1. O grupo deixa de constar nos balancetes após seu encerramento; nesses anos a apresentação separada informa zero e a ausência da rubrica. Fonte: balancetes de cada ano, grupos 1.1.1 e 1.1.4.'
    ]}]
    pending=[{'item':'Detalhamento complementar por finalidade e eliminação de transferências internas',
              'motivo':'Os totais de saldo inicial, débitos, créditos, variação e saldo final por ano e no acumulado já estão APURADOS pelos balancetes. O razão com contrapartidas permite separar finalidades e transferências; não se solicita repetir a conciliação dos saldos nem condicionar a entrega dos totais a outra fonte.',
              'fonte':'Balancetes 2022-2025 e balancetes/Balancete-ja-set-2026.pdf | 1.1.1; aba Fluxo acumulado'}]
    if ecd_available and mixed:
        pending.append({'item':f'Detalhamento auxiliar de {mixed} partidas compostas de 2025',
                        'motivo':'Classificar a finalidade de contrapartidas em lados mistos, mantendo o efeito líquido já reconciliado. É complemento de classificação; não é pendência da apuração dos totais dos balancetes.',
                        'fonte':src+' | I200/I250; aba Fluxo detalhes'})
    metrics={'main_source':'BALANCETES','status':'APURADO' if all(c['status']=='OK' for c in principal['checks']) else 'APURADO COM DIVERGÊNCIAS',
             'balancetes_por_ano':{y:_serial(p) for y,p in principal['periods'].items()},
             'aplicacoes_fora_disponivel_por_ano':{y:_serial(p) for y,p in principal['outside'].items()},
             'acumulado':_serial(accumulated),'auxiliary_2025_available':ecd_available,
             'recursos_socios_2025':resources,
             'ecd_cash_open':float(ecd_open) if ecd_available else None,'ecd_cash_close':float(ecd_close) if ecd_available else None,
             'ecd_cash_net':float(net) if ecd_available else None,'ecd_in':float(sum(a for a,b in groups.values())) if ecd_available else None,
             'ecd_out':float(sum(b for a,b in groups.values())) if ecd_available else None,
             'compound_entries_opened':opened if ecd_available else None,'discounted_expense_payments':discounts_net if ecd_available else None,
             'mixed_entries_pending':mixed if ecd_available else None}
    if all((base/f'balancetes/Razão{y}.xls').exists() for y in range(2022,2027)):
        refined=_annual_cash(base,out,principal)
        sheets.extend(refined['sheets']);checks.extend(refined['checks']);metrics['annual_details']=refined['metrics']
        pending=refined['pendencias']
        report[0]['paragraphs'][2]='Os cinco razões anuais foram recebidos e conferidos aos balancetes. A abertura por finalidade e a compensação dos movimentos de caixa por lote estão nas abas Fluxo por finalidade e Fluxo por período. Lotes de implantação de saldos estão separados de recebimentos e pagamentos; partidas mistas mantêm o efeito líquido sem rateio presumido.'
        r=refined['metrics'];a=r['accumulated']
        report[0]['paragraphs'].append(f'A abertura pelos razões identifica R$ {brl(a["incoming"])} de entradas e R$ {brl(a["outgoing"])} de saídas compensadas por lote, além de R$ {brl(a["transition_net"])} de efeito de implantação/ajustes do disponível. A soma desses movimentos explica a variação de R$ {brl(a["net"])}. Existem {r["mixed_batches"]} lotes com finalidade individual a detalhar, preservados nas contas. Fonte: razões anuais 2022–2026, aba Fluxo exceções. Os números são movimentos contábeis do disponível e não devem ser confundidos com receita ou despesa da DRE.')
    return dict(sheets=sheets,metrics=metrics,checks=checks,pendencias=pending,report=report)

def brl(v):
    s=f'{abs(v):,.2f}'.replace(',','X').replace('.',',').replace('X','.')
    return '('+s+')' if v<0 else s
