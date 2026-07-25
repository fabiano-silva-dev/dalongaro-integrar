import pandas as pd
import os
import sys
from datetime import datetime

def limpar_nome_conta(conta, terceiro):
    # Remove o conteúdo do terceiro do nome da conta
    if pd.notna(terceiro) and terceiro in conta:
        return conta.replace(terceiro, '').strip(' -')
    return conta

def extrair_grupo(conta):
    # Extrai o primeiro número da conta (grupo)
    try:
        return int(conta.split('.')[0])
    except:
        return 0

def gerar_balancete(arquivo_entrada):
    # Lê o arquivo XLSX
    df = pd.read_excel(arquivo_entrada)
    
    # Limpa os nomes das contas
    df['Conta Débito'] = df.apply(lambda x: limpar_nome_conta(x['Conta Débito'], x['Terceiro']), axis=1)
    df['Conta Crédito'] = df.apply(lambda x: limpar_nome_conta(x['Conta Crédito'], x['Terceiro']), axis=1)
    
    # Converte a coluna de valor para numérico
    df['Valor Pagar/Receber'] = pd.to_numeric(df['Valor Pagar/Receber'], errors='coerce')
    
    # Cria DataFrames separados para débito e crédito
    debitos = df.groupby('Conta Débito')['Valor Pagar/Receber'].sum().reset_index()
    creditos = df.groupby('Conta Crédito')['Valor Pagar/Receber'].sum().reset_index()
    
    # Renomeia as colunas para padronização
    debitos.columns = ['Conta', 'Débito']
    creditos.columns = ['Conta', 'Crédito']
    
    # Faz o merge dos DataFrames
    balancete = pd.merge(debitos, creditos, on='Conta', how='outer').fillna(0)
    
    # Adiciona coluna de grupo
    balancete['Grupo'] = balancete['Conta'].apply(extrair_grupo)
    
    # Ordena por grupo e conta
    balancete = balancete.sort_values(['Grupo', 'Conta'])
    
    # Formata os valores para 2 casas decimais
    balancete['Débito'] = balancete['Débito'].round(2)
    balancete['Crédito'] = balancete['Crédito'].round(2)
    
    # Calcula totais por grupo
    totais_grupo = balancete.groupby('Grupo').agg({
        'Débito': 'sum',
        'Crédito': 'sum'
    }).reset_index()
    
    # Prepara o DataFrame final
    resultado = []
    
    # Para cada grupo
    for grupo in sorted(balancete['Grupo'].unique()):
        # Adiciona as contas do grupo
        contas_grupo = balancete[balancete['Grupo'] == grupo]
        for _, row in contas_grupo.iterrows():
            resultado.append({
                'Conta': row['Conta'],
                'Débito': row['Débito'],
                'Crédito': row['Crédito']
            })
        
        # Adiciona o total do grupo
        total_grupo = totais_grupo[totais_grupo['Grupo'] == grupo].iloc[0]
        resultado.append({
            'Conta': f'Total Grupo {grupo}',
            'Débito': total_grupo['Débito'],
            'Crédito': total_grupo['Crédito']
        })
    
    # Adiciona o total geral
    resultado.append({
        'Conta': 'Total Geral',
        'Débito': balancete['Débito'].sum(),
        'Crédito': balancete['Crédito'].sum()
    })
    
    # Cria o DataFrame final
    balancete_final = pd.DataFrame(resultado)
    
    # Gera nome do arquivo de saída
    data_atual = datetime.now().strftime('%Y%m%d')
    nome_arquivo = f'balancete-{data_atual}.xlsx'
    
    # Salva o balancete em um novo arquivo Excel
    with pd.ExcelWriter(nome_arquivo, engine='openpyxl') as writer:
        balancete_final.to_excel(writer, sheet_name='Balancete', index=False)
        
        # Ajusta a largura das colunas
        worksheet = writer.sheets['Balancete']
        worksheet.column_dimensions['A'].width = 40  # Conta
        worksheet.column_dimensions['B'].width = 15  # Débito
        worksheet.column_dimensions['C'].width = 15  # Crédito
    
    print(f'Balancete gerado com sucesso: {nome_arquivo}')
    return nome_arquivo

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Uso: python gera-balancete.py <arquivo_entrada>")
        sys.exit(1)
    
    arquivo_entrada = sys.argv[1]
    
    if os.path.exists(arquivo_entrada):
        gerar_balancete(arquivo_entrada)
    else:
        print(f'Arquivo {arquivo_entrada} não encontrado!')
