import sys
import csv
import re
from PyPDF2 import PdfReader
import datetime
import pandas as pd

if len(sys.argv) < 2:
    print("Uso: python gerar_planilha_extrato.py <arquivo.pdf>")
    sys.exit(1)

pdf_path = sys.argv[1]
csv_path = pdf_path.rsplit('.', 1)[0] + '.csv'

reader = PdfReader(pdf_path)

lancamentos = []
processar = False
cabecalho_seq = ['Data', 'Lançamento', 'Nome']
cabecalho_idx = 0
saldo_inicial_valor = None
saldo_final_valor = None

for page in reader.pages:
    text = page.extract_text()
    if not text:
        continue
    lines = text.split('\n')
    # print('--- Linhas extraídas desta página ---')
    # for l in lines:
    #      print(l)
    # print('----------------------------------------------')
    for i in range(len(lines)):
        linha = lines[i].strip()
        # Detecta a sequência do cabeçalho
        if not processar:
            if linha == cabecalho_seq[cabecalho_idx]:
                cabecalho_idx += 1
                if cabecalho_idx == len(cabecalho_seq):
                    # print('Cabeçalho encontrado (sequência):', cabecalho_seq)
                    processar = True
                    continue
            else:
                cabecalho_idx = 0
            continue
        # Identifica linhas de lançamento (começam com data)
        if re.match(r"\d{2}/\d{2}/\d{4}( \d{2}:\d{2})?", linha):
            data = linha
            lancamento = lines[i+1].strip() if i+1 < len(lines) else ''
            nome = ''
            valor = ''
            j = i+2
            nome_partes = []
            encontrou_num = False
            while j < len(lines):
                ltest = lines[j].strip()
                # Se encontrar valor, para
                if re.match(r"^-?R\$ [\d\.,]+", ltest):
                    valor = ltest
                    encontrou_num = True
                    break
                # Se encontrar número de banco/agência/conta (só dígitos ou hífen, 3-12 caracteres), para nome, mas continua buscando valor
                if re.match(r"^[\d\-]{3,12}$", ltest):
                    encontrou_num = True
                    break
                nome_partes.append(ltest)
                j += 1
            nome = ' '.join(nome_partes).strip()
            # Se parou em campo numérico, continua buscando valor
            if encontrou_num and valor == '':
                while j < len(lines):
                    ltest = lines[j].strip()
                    if re.match(r"^-?R\$ [\d\.,]+", ltest):
                        valor = ltest
                        break
                    j += 1
            # Ignora linhas de saldo inicial/final
            if 'SALDO FINAL' in lancamento or 'SALDO INICIAL' in lancamento:
                continue
            # Só adiciona se data for exatamente no formato esperado
            if not re.fullmatch(r"\d{2}/\d{2}/\d{4}( \d{2}:\d{2})?", data):
                continue
            # Se for tarifa de conta, adiciona TARIFA BANCARIA ao nome
            if lancamento == "Tarifas de conta":
                nome = "TARIFA BANCARIA"
            lancamentos.append([data, lancamento, nome, valor])
        # Extrai saldo inicial
        if 'SALDO INICIAL' in linha:
            # Procura valor na mesma linha ou na próxima
            m = re.search(r'R\$ [\d\.,]+', linha)
            if m:
                saldo_inicial_valor = m.group(0).replace('R$ ', '').replace('.', '').replace(',', '.')
            elif i+1 < len(lines):
                m2 = re.search(r'R\$ [\d\.,]+', lines[i+1])
                if m2:
                    saldo_inicial_valor = m2.group(0).replace('R$ ', '').replace('.', '').replace(',', '.')
        # Extrai saldo final
        if 'SALDO FINAL' in linha:
            m = re.search(r'R\$ [\d\.,]+', linha)
            if m:
                saldo_final_valor = m.group(0).replace('R$ ', '').replace('.', '').replace(',', '.')
            elif i+1 < len(lines):
                m2 = re.search(r'R\$ [\d\.,]+', lines[i+1])
                if m2:
                    saldo_final_valor = m2.group(0).replace('R$ ', '').replace('.', '').replace(',', '.')

# Função para converter data para ordenação
def parse_data(data):
    try:
        return datetime.datetime.strptime(data, "%d/%m/%Y %H:%M")
    except ValueError:
        try:
            return datetime.datetime.strptime(data, "%d/%m/%Y")
        except ValueError:
            return datetime.datetime(1900, 1, 1)

# Ordena os lançamentos por data crescente
lancamentos.sort(key=lambda x: parse_data(x[0]))

# Remove 'R$' do valor, mantendo o sinal
for l in lancamentos:
    l[3] = l[3].replace('R$ ', '').replace('R$', '').replace('.', '').replace(',', '.')
    l[3] = l[3].strip()
    
    # Adiciona tipo e histórico
    try:
        valor_float = float(l[3])
        if valor_float > 0:
            tipo = "ENTRADA"
            historico = f"RCTO REF {l[2].upper()}"
        else:
            tipo = "SAIDA"
            historico = f"PGTO REF {l[2].upper()}"
    except:
        tipo = ""
        historico = ""
    
    l.extend([tipo, historico])

# Cria uma cópia dos lançamentos originais para o arquivo agrupado
lancamentos_originais = [l.copy() for l in lancamentos]

# Agrupa por nome do extrato, mantendo apenas a primeira ocorrência
lancamentos_agrupados = {}
for l in lancamentos:
    nome = l[2]  # Nome do extrato
    if nome not in lancamentos_agrupados:
        # Primeira ocorrência: mantém todos os dados originais
        lancamentos_agrupados[nome] = l.copy()

# Converte de volta para lista, mantendo a ordem original
lancamentos_agrupados_lista = list(lancamentos_agrupados.values())

print(f"Lançamentos originais: {len(lancamentos)} registros")
print(f"Lançamentos agrupados por nome: {len(lancamentos_agrupados_lista)} registros únicos")

# Calcula totais de entrada e saída
entrada = 0.0
saida = 0.0
for l in lancamentos:
    try:
        valor = float(l[3])
        if valor > 0:
            entrada += valor
        else:
            saida += valor
    except Exception:
        pass

def format_brl(valor):
    return f'{valor:,.2f}'.replace('.', 'X').replace(',', '.').replace('X', ',')

print(f"Total de entradas: {format_brl(entrada)}")
print(f"Total de saídas: {format_brl(saida)}")
if saldo_inicial_valor is not None:
    try:
        saldo_inicial_float = float(saldo_inicial_valor)
        print(f"Saldo inicial do extrato: {format_brl(saldo_inicial_float)}")
    except Exception:
        saldo_inicial_float = None
        print(f"Saldo inicial do extrato: {saldo_inicial_valor}")
else:
    saldo_inicial_float = None
if saldo_final_valor is not None:
    try:
        saldo_final_float = float(saldo_final_valor)
        print(f"Saldo final do extrato: {format_brl(saldo_final_float)}")
    except Exception:
        saldo_final_float = None
        print(f"Saldo final do extrato: {saldo_final_valor}")
else:
    saldo_final_float = None
print(f"Saldo final calculado: {format_brl(saida)}")

# Conferência do saldo
if saldo_inicial_float is not None and saldo_final_float is not None:
    saldo_esperado = saldo_inicial_float + entrada - abs(saida)
    print(f"Saldo esperado (inicial + entradas - saídas): {format_brl(saldo_esperado)}")
    if abs(saldo_esperado - saldo_final_float) < 0.01:
        print("\033[92mSaldo FECHOU corretamente!\033[0m")
    else:
        print("\033[91mSaldo NÃO FECHOU!\033[0m")

# Função para limpar CPF/CNPJ do histórico
def limpar_cpf_cnpj(texto):
    # Remove CPF mascarado (formato: ***.XXX.XXX-** ou ***.XXX.XXX- **)
    texto = re.sub(r'\*{3}\.\d{3}\.\d{3}-\s*\*{1,2}', '', texto)
    # Remove CPF (formato: XXX.XXX.XXX-XX)
    texto = re.sub(r'\d{3}\.\d{3}\.\d{3}-\d{2}', '', texto)
    # Remove CNPJ (formato: XX.XXX.XXX/XXXX-XX ou XX.XXX.XXX/XXXX- XX)
    texto = re.sub(r'\d{2}\.\d{3}\.\d{3}/\d{4}-\s*\d{1,2}', '', texto)
    # Remove CPF/CNPJ sem formatação (apenas números)
    texto = re.sub(r'\b\d{11}\b', '', texto)  # CPF
    texto = re.sub(r'\b\d{14}\b', '', texto)  # CNPJ
    # Remove espaços extras e limpa
    return re.sub(r'\s+', ' ', texto).strip()

# Gera arquivo CSV original
with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
    writer = csv.writer(csvfile, delimiter=';')
    writer.writerow(['Data', 'Código Filial', 'Fornecedor/Cliente', 'Valor (R$)', 'Histórico'])
    for l in lancamentos:
        valor_brl = l[3]
        try:
            valor_brl = format_brl(float(l[3]))
        except Exception:
            pass
        data_sem_hora = l[0].split(' ')[0]
        historico_limpo = limpar_cpf_cnpj(l[5])
        writer.writerow([data_sem_hora, l[2], l[2], valor_brl, historico_limpo])

print(f'CSV estruturado gerado em: {csv_path}')

# Gera arquivo XLSX original
xlsx_path = csv_path.rsplit('.', 1)[0] + '.xlsx'
linhas_xlsx = []
for l in lancamentos:
    valor_brl = l[3]
    try:
        valor_brl = format_brl(float(l[3]))
    except Exception:
        pass
    data_sem_hora = l[0].split(' ')[0]
    linhas_xlsx.append({
        'Data': data_sem_hora,
        'Lançamento': l[1],
        'Nome': l[2],
        'Valor (R$)': valor_brl,
        'Tipo': l[4],
        'Histórico': l[5]
    })
df = pd.DataFrame(linhas_xlsx)
df.to_excel(xlsx_path, index=False)
print(f'Planilha Excel gerada em: {xlsx_path}')

# Gera arquivo XLSX agrupado
xlsx_agrupado_path = csv_path.rsplit('.', 1)[0] + '_agrupado.xlsx'
linhas_xlsx_agrupado = []
for l in lancamentos_agrupados_lista:
    valor_brl = l[3]
    try:
        valor_brl = format_brl(float(l[3]))
    except Exception:
        pass
    data_sem_hora = l[0].split(' ')[0]
    linhas_xlsx_agrupado.append({
        'Data': data_sem_hora,
        'Lançamento': l[1],
        'Nome': l[2],
        'Valor (R$)': valor_brl,
        'Tipo': l[4],
        'Histórico': l[5]
    })
df_agrupado = pd.DataFrame(linhas_xlsx_agrupado)
df_agrupado.to_excel(xlsx_agrupado_path, index=False)
print(f'Planilha Excel agrupada gerada em: {xlsx_agrupado_path}')
