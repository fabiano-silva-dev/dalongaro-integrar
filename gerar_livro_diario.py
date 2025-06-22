import sys
import pandas as pd
import re
import os

# Função para converter o valor para float
def valor_para_float(valor):
    if pd.isna(valor):
        print(f"Valor NaN encontrado: {valor}")
        return 0.0
    valor = str(valor).replace('R$', '').replace('.', '').replace(',', '.').strip()
    try:
        return float(valor)
    except ValueError:
        print(f"Erro ao converter valor: {valor}")
        return 0.0

# Função para extrair o nome após ' para ' em caixa alta
def extrair_nome_para(historico):
    if pd.isna(historico):
        print(f"Histórico NaN encontrado: {historico}")
        return ''
   
    match = re.search(r' para ([A-Z0-9 \-\.]+)', historico)
    if match:
        return match.group(1).strip()
    return ''

def formatar_conta(cl, nome, nome_extra):
    if str(cl).startswith(('1', '2')) and nome_extra:
        return f"{cl} - {nome} - {nome_extra}"
    else:
        return f"{cl} - {nome}"

def processar_lancamentos(csv_path, conta_filtro, csv_filtro):
    df = pd.read_csv(csv_path)
    print(f"Total de registros no arquivo original: {len(df)}")
    
    # Colunas obrigatórias
    colunas_obrigatorias = [
        'partidas_conta',
        'partidas_classificacao_da_conta',
        'partidas_tipo',
        'lançamentos_data',
        'partidas_valor'
    ]
    
    # Verificar valores NaN apenas nas colunas obrigatórias
    print("\nVerificando valores NaN nas colunas obrigatórias:")
    for coluna in colunas_obrigatorias:
        nan_count = df[coluna].isna().sum()
        if nan_count > 0:
            print(f"\nColuna '{coluna}': {nan_count} valores NaN")
            print("Exemplos de linhas com NaN nesta coluna:")
            print(df[df[coluna].isna()][colunas_obrigatorias].head())
            print("\nLinhas completas com NaN:")
            print(df[df[coluna].isna()].head())

    lancamentos = []
    i = 0
    while i < len(df):
        # Lê primeira linha
        linha1 = df.iloc[i]
        data = linha1['lançamentos_data']
        historico = linha1['lançamentos_histórico'] if not pd.isna(linha1['lançamentos_histórico']) and str(linha1['lançamentos_histórico']).strip() != '' else 'VLR REF'
        documento = linha1['lançamentos_documento'] if not pd.isna(linha1['lançamentos_documento']) else ''
        valor1 = valor_para_float(linha1['partidas_valor'])
        conta1_tipo = linha1['partidas_tipo']
        conta1_cl = linha1['partidas_classificacao_da_conta']
        conta1_nome = linha1['partidas_conta']
        nome_extra = extrair_nome_para(historico)

        # Verifica se tem próxima linha
        if i+1 >= len(df):
            break

        # Lê segunda linha
        linha2 = df.iloc[i+1]
        valor2 = valor_para_float(linha2['partidas_valor'])
        conta2_tipo = linha2['partidas_tipo']
        conta2_cl = linha2['partidas_classificacao_da_conta']
        conta2_nome = linha2['partidas_conta']

        # Caso 1x1: valores iguais
        if abs(valor1 - valor2) < 0.01:
            if conta1_tipo == 'Credito':
                conta_credito = formatar_conta(conta1_cl, conta1_nome, nome_extra)
                conta_debito = formatar_conta(conta2_cl, conta2_nome, nome_extra)
            else:
                conta_credito = formatar_conta(conta2_cl, conta2_nome, nome_extra)
                conta_debito = formatar_conta(conta1_cl, conta1_nome, nome_extra)
            
            lancamentos.append({
                'Data': data,
                'Complemento Histórico': historico,
                'Valor Pagar/Receber': valor1,
                'Conta Crédito': conta_credito,
                'Conta Débito': conta_debito,
                'Documento': documento,
                'Terceiro': nome_extra
            })
            i += 2
        else:
            # Caso 1 para vários
            # Identifica qual é o crédito
            if conta1_tipo == 'Credito':
                conta_credito = formatar_conta(conta1_cl, conta1_nome, nome_extra)
                valor_credito = valor1
                # Primeiro débito já está na linha2
                conta_debito = formatar_conta(conta2_cl, conta2_nome, nome_extra)
                valor_debito = valor2
                i += 2
            else:
                conta_credito = formatar_conta(conta2_cl, conta2_nome, nome_extra)
                valor_credito = valor2
                # Primeiro débito já está na linha1
                conta_debito = formatar_conta(conta1_cl, conta1_nome, nome_extra)
                valor_debito = valor1
                i += 2

            # Adiciona o primeiro débito
            lancamentos.append({
                'Data': data,
                'Complemento Histórico': historico,
                'Valor Pagar/Receber': valor_debito,
                'Conta Crédito': conta_credito,
                'Conta Débito': conta_debito,
                'Documento': documento,
                'Terceiro': nome_extra
            })

            # Soma dos débitos já processados
            soma_debitos = valor_debito

            # Continua processando débitos até fechar o valor do crédito
            while i < len(df) and abs(soma_debitos - valor_credito) > 0.01:
                linha_debito = df.iloc[i]
                if linha_debito['partidas_tipo'] == 'Credito':
                    break

                valor_debito = valor_para_float(linha_debito['partidas_valor'])
                conta_debito = formatar_conta(
                    linha_debito['partidas_classificacao_da_conta'],
                    linha_debito['partidas_conta'],
                    nome_extra
                )

                lancamentos.append({
                    'Data': data,
                    'Complemento Histórico': historico,
                    'Valor Pagar/Receber': valor_debito,
                    'Conta Crédito': conta_credito,
                    'Conta Débito': conta_debito,
                    'Documento': documento,
                    'Terceiro': nome_extra
                })

                soma_debitos += valor_debito
                i += 1

    df_saida = pd.DataFrame(lancamentos)
    print(f"Total de registros processados: {len(df_saida)}")
    
    # Limpar o Complemento Histórico
    df_saida['Complemento Histórico'] = df_saida['Complemento Histórico'].str.replace("  para #pessoa#", "")
    
    # Adiciona coluna de ID
    df_saida['ID'] = range(1, len(df_saida) + 1)
    
    # Reordena as colunas para manter uma ordem lógica
    colunas = ['Data', 'Complemento Histórico', 'Valor Pagar/Receber', 'Conta Crédito', 'Conta Débito', 'Documento', 'Terceiro', 'ID']
    df_saida = df_saida[colunas]
    
    # Ordena por data
    df_saida['Data'] = pd.to_datetime(df_saida['Data'], format='%d/%m/%Y')
    df_saida = df_saida.sort_values('Data')
    df_saida['Data'] = df_saida['Data'].dt.strftime('%d/%m/%Y')
    
    # Gerar nome do arquivo de saída baseado no nome do arquivo de entrada
    base_name = os.path.basename(csv_path)
    nome_sem_ext = os.path.splitext(base_name)[0]
    nome_saida = f"livro-diario-{nome_sem_ext}.xlsx"
    df_saida.to_excel(nome_saida, index=False)

    # Criar segundo arquivo com filtros
    registros_filtrados = []
    ids_filtrados = set()
    
    # Filtro 1: Conta específica
    if conta_filtro:
        df_conta = df_saida[
            df_saida['Conta Crédito'].str.contains(conta_filtro, na=False) |
            df_saida['Conta Débito'].str.contains(conta_filtro, na=False)
        ]
        print(f"Registros com a conta {conta_filtro}: {len(df_conta)}")
        registros_filtrados.extend(df_conta.to_dict('records'))
        ids_filtrados.update(df_conta['ID'].tolist())
    
    # Filtro 2: Documento + Terceiro
    if csv_filtro and os.path.exists(csv_filtro):
        df_chaves = pd.read_csv(csv_filtro)
        print(f"Total de registros no arquivo de chaves: {len(df_chaves)}")
        
        # Limpar espaços nas colunas do segundo arquivo
        df_chaves['dados_principais_documento'] = df_chaves['dados_principais_documento'].str.strip()
        df_chaves['dados_principais_fornecedor/comprador'] = df_chaves['dados_principais_fornecedor/comprador'].str.strip()
        
        # Criar chaves para comparação
        df_saida['chave'] = df_saida['Documento'].str.strip() + '|' + df_saida['Terceiro'].str.strip()
        df_chaves['chave'] = df_chaves['dados_principais_documento'] + '|' + df_chaves['dados_principais_fornecedor/comprador']
        
        # Filtrar apenas registros onde Documento e Terceiro não são vazios
        df_chaves_filtrado = df_saida[
            (df_saida['Documento'].notna() & df_saida['Documento'].str.strip() != '') &
            (df_saida['Terceiro'].notna() & df_saida['Terceiro'].str.strip() != '')
        ]
        print(f"Registros com Documento e Terceiro não vazios: {len(df_chaves_filtrado)}")
        
        # Filtrar por chaves presentes no segundo arquivo
        df_chaves_filtrado = df_chaves_filtrado[df_chaves_filtrado['chave'].isin(df_chaves['chave'])]
        print(f"Registros encontrados no arquivo de chaves: {len(df_chaves_filtrado)}")
        
        # Adicionar ao conjunto de registros filtrados
        registros_filtrados.extend(df_chaves_filtrado.to_dict('records'))
        ids_filtrados.update(df_chaves_filtrado['ID'].tolist())
    
    # Converter para DataFrame e remover duplicatas
    df_filtrado = pd.DataFrame(registros_filtrados)
    if not df_filtrado.empty:
        df_filtrado = df_filtrado.drop_duplicates(subset=['ID'])
        print(f"Total de registros filtrados (após remover duplicatas): {len(df_filtrado)}")
        
        # Ordena por data
        df_filtrado['Data'] = pd.to_datetime(df_filtrado['Data'], format='%d/%m/%Y')
        df_filtrado = df_filtrado.sort_values('Data')
        df_filtrado['Data'] = df_filtrado['Data'].dt.strftime('%d/%m/%Y')
    
    # Salvar arquivo filtrado
    nome_saida_filtrado = f"livro-diario-filtrado-{nome_sem_ext}.xlsx"
    df_filtrado.to_excel(nome_saida_filtrado, index=False)

    # Criar terceiro arquivo com registros não filtrados
    if not df_filtrado.empty:
        # Filtrar registros que não estão no arquivo filtrado usando o ID
        df_nao_filtrado = df_saida[~df_saida['ID'].isin(ids_filtrados)].copy()
        
        print(f"Total de registros não filtrados: {len(df_nao_filtrado)}")
        print(f"Soma dos filtrados e não filtrados: {len(df_filtrado) + len(df_nao_filtrado)}")
        
        # Ordena por data
        df_nao_filtrado['Data'] = pd.to_datetime(df_nao_filtrado['Data'], format='%d/%m/%Y')
        df_nao_filtrado = df_nao_filtrado.sort_values('Data')
        df_nao_filtrado['Data'] = df_nao_filtrado['Data'].dt.strftime('%d/%m/%Y')
        
        # Salvar arquivo não filtrado
        nome_saida_nao_filtrado = f"livro-diario-nao-filtrado-{nome_sem_ext}.xlsx"
        df_nao_filtrado.to_excel(nome_saida_nao_filtrado, index=False)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python gerar_livro_diario.py <caminho_arquivo_csv> [conta_filtro] [csv_filtro]")
        sys.exit(1)
    
    conta_filtro = sys.argv[2] if len(sys.argv) > 2 else None
    csv_filtro = sys.argv[3] if len(sys.argv) > 3 else None
    
    processar_lancamentos(sys.argv[1], conta_filtro, csv_filtro) 