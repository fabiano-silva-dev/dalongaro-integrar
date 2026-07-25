#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para processar dados de produtividade do arquivo CSV
e criar uma tabela estruturada para relatórios
"""

import pandas as pd
import re
from datetime import datetime
import json
import os

def limpar_e_estruturar_dados(arquivo_csv):
    """
    Limpa e estrutura os dados do CSV de produtividade
    """
    print(f"Processando arquivo: {arquivo_csv}")
    
    # Tentar diferentes codificações
    codificacoes = ['utf-8', 'latin1', 'iso-8859-1', 'cp1252']
    df = None
    
    for codificacao in codificacoes:
        try:
            print(f"Tentando codificação: {codificacao}")
            df = pd.read_csv(arquivo_csv, header=None, encoding=codificacao)
            print(f"Sucesso com codificação: {codificacao}")
            break
        except Exception as e:
            print(f"Falha com codificação {codificacao}: {e}")
            continue
    
    if df is None:
        raise Exception("Não foi possível ler o arquivo com nenhuma codificação")
    
    print(f"Forma original: {df.shape}")
    
    # Mostrar primeiras linhas para análise
    print("Primeiras 10 linhas:")
    print(df.head(10).to_string())
    
    dados_estruturados = []
    atividades = []
    clientes = []
    cliente_atual = None
    
    for idx, row in df.iterrows():
        # Juntar todas as células não vazias da linha
        linha = ' '.join([str(cell) for cell in row if pd.notna(cell) and str(cell).strip()])
        
        # Pular linhas vazias ou cabeçalhos
        if not linha.strip():
            continue
            
        # Pular cabeçalhos específicos
        if any(termo in linha for termo in ['Relação de Clientes', 'Período:', 'Hora:', 'Página:']):
            continue
            
        # Pular cabeçalho de colunas
        if 'Sistema' in linha and 'Usuário' in linha and 'Data' in linha and 'Tempo Gasto' in linha:
            continue
            
        # Detectar cliente
        if 'Cliente:' in linha:
            # Extrair código e nome do cliente
            match = re.search(r'Cliente:\s*(\d+)', linha)
            if match:
                codigo = match.group(1).strip()
                # Extrair nome do cliente (tudo após o código)
                nome_parte = linha.split(codigo, 1)[1].strip()
                # Limpar o nome
                nome = re.sub(r'\.0\s*', '', nome_parte).strip()
                
                cliente_atual = {
                    'codigo': codigo,
                    'nome': nome,
                    'atividades': []
                }
            continue
            
        # Detectar total do cliente
        if 'Total do Cliente:' in linha:
            match = re.search(r'Total do Cliente:\s*(\d{2}:\d{2}:\d{2})', linha)
            if match and cliente_atual:
                cliente_atual['tempo_total'] = match.group(1)
                clientes.append(cliente_atual.copy())
                cliente_atual = None
            continue
            
        # Detectar linha de atividade
        if cliente_atual and not 'Cliente:' in linha and not 'Total do Cliente:' in linha:
            # Procurar por padrões de data e tempo
            data_pattern = r'\d{2}/\d{2}/\d{4}'
            tempo_pattern = r'\d{2}:\d{2}:\d{2}'
            
            data_match = re.search(data_pattern, linha)
            tempo_match = re.search(tempo_pattern, linha)
            
            if data_match and tempo_match:
                # Extrair sistema e usuário
                sistema = None
                usuario = None
                
                # Procurar por sistemas conhecidos
                sistemas_conhecidos = ['Folha', 'Contabilidade', 'Escrita', 'Patrimonio', 'Atualizar', 'Registro']
                for sis in sistemas_conhecidos:
                    if sis in linha:
                        sistema = sis
                        break
                
                # Procurar por usuários conhecidos
                usuarios_conhecidos = ['PAMELA', 'GERENTE', 'VIVIANE', 'RAYANE', 'VANEZA', 'MARIA', 'DUDA', 'CRISTINA', 'MATIAS']
                for usr in usuarios_conhecidos:
                    if usr in linha:
                        usuario = usr
                        break
                
                if sistema and usuario:
                    atividade = {
                        'codigo_cliente': cliente_atual['codigo'],
                        'nome_cliente': cliente_atual['nome'],
                        'sistema': sistema,
                        'usuario': usuario,
                        'data': data_match.group(),
                        'tempo_gasto': tempo_match.group()
                    }
                    atividades.append(atividade)
                    cliente_atual['atividades'].append(atividade)
    
    # Adicionar todas as atividades aos dados estruturados
    dados_estruturados.extend(atividades)
    
    # Adicionar clientes com suas atividades
    dados_estruturados.extend(clientes)
    
    return dados_estruturados, atividades, clientes

def criar_dataframe_estruturado(dados_estruturados):
    """
    Cria um DataFrame pandas estruturado a partir dos dados processados
    """
    # Separar clientes e atividades
    clientes = []
    atividades = []
    
    for item in dados_estruturados:
        if 'tempo_total' in item:  # É um cliente
            clientes.append(item)
        else:  # É uma atividade
            atividades.append(item)
    
    # Criar DataFrame de atividades
    df_atividades = pd.DataFrame(atividades)
    
    # Criar DataFrame de clientes
    df_clientes = pd.DataFrame(clientes)
    
    return df_atividades, df_clientes

def gerar_relatorios(df_atividades, df_clientes):
    """
    Gera vários relatórios a partir dos dados estruturados
    """
    relatorios = {}
    
    # 1. Relatório por Cliente
    if not df_atividades.empty:
        relatorio_cliente = df_atividades.groupby(['codigo_cliente', 'nome_cliente']).agg({
            'tempo_gasto': 'count',
            'sistema': lambda x: ', '.join(x.unique()),
            'usuario': lambda x: ', '.join(x.unique())
        }).reset_index()
        relatorio_cliente.columns = ['Código', 'Cliente', 'Total Atividades', 'Sistemas Utilizados', 'Usuários']
        relatorios['por_cliente'] = relatorio_cliente
    
    # 2. Relatório por Sistema
    if not df_atividades.empty:
        relatorio_sistema = df_atividades.groupby('sistema').agg({
            'codigo_cliente': 'nunique',
            'usuario': 'nunique',
            'tempo_gasto': 'count'
        }).reset_index()
        relatorio_sistema.columns = ['Sistema', 'Clientes Únicos', 'Usuários Únicos', 'Total Atividades']
        relatorios['por_sistema'] = relatorio_sistema
    
    # 3. Relatório por Usuário
    if not df_atividades.empty:
        relatorio_usuario = df_atividades.groupby('usuario').agg({
            'codigo_cliente': 'nunique',
            'sistema': 'nunique',
            'tempo_gasto': 'count'
        }).reset_index()
        relatorio_usuario.columns = ['Usuário', 'Clientes Únicos', 'Sistemas Únicos', 'Total Atividades']
        relatorios['por_usuario'] = relatorio_usuario
    
    # 4. Relatório por Data
    if not df_atividades.empty:
        relatorio_data = df_atividades.groupby('data').agg({
            'codigo_cliente': 'nunique',
            'sistema': 'nunique',
            'usuario': 'nunique',
            'tempo_gasto': 'count'
        }).reset_index()
        relatorio_data.columns = ['Data', 'Clientes Únicos', 'Sistemas Únicos', 'Usuários Únicos', 'Total Atividades']
        relatorios['por_data'] = relatorio_data
    
    return relatorios

def salvar_relatorios(relatorios, diretorio_saida):
    """
    Salva todos os relatórios em arquivos CSV
    """
    os.makedirs(diretorio_saida, exist_ok=True)
    
    for nome_relatorio, df_relatorio in relatorios.items():
        nome_arquivo = f"relatorio_{nome_relatorio}.csv"
        caminho_completo = os.path.join(diretorio_saida, nome_arquivo)
        
        df_relatorio.to_csv(caminho_completo, index=False, encoding='utf-8-sig')
        print(f"Relatório salvo: {caminho_completo}")
        
        # Mostrar resumo do relatório
        print(f"  - {nome_relatorio}: {len(df_relatorio)} registros")

def main():
    """
    Função principal
    """
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from runtime import setup_workspace
    setup_workspace()

    arquivo_csv = "produtividade/ClienteTempo Gasto.csv"
    
    if not os.path.exists(arquivo_csv):
        print(f"Arquivo CSV não encontrado: {arquivo_csv}")
        return
    
    print("Iniciando processamento dos dados de produtividade...")
    
    # Processar e estruturar dados
    dados_estruturados, atividades, clientes = limpar_e_estruturar_dados(arquivo_csv)
    
    if not dados_estruturados:
        print("Nenhum dado foi extraído")
        return
    
    print(f"\nTotal de registros extraídos: {len(dados_estruturados)}")
    
    # Criar DataFrames estruturados
    df_atividades, df_clientes = criar_dataframe_estruturado(dados_estruturados)
    
    print(f"\nDataFrame de Atividades: {df_atividades.shape}")
    print(f"DataFrame de Clientes: {df_clientes.shape}")
    
    # Mostrar amostra dos dados
    if not df_atividades.empty:
        print("\nAmostra das Atividades:")
        print(df_atividades.head(10).to_string())
    
    if not df_clientes.empty:
        print("\nAmostra dos Clientes:")
        print(df_clientes.head(5).to_string())
    
    # Gerar relatórios
    print("\nGerando relatórios...")
    relatorios = gerar_relatorios(df_atividades, df_clientes)
    
    # Salvar relatórios
    diretorio_relatorios = "produtividade/relatorios/basicos"
    salvar_relatorios(relatorios, diretorio_relatorios)
    
    # Salvar dados estruturados principais
    if not df_atividades.empty:
        df_atividades.to_csv("dados_atividades_estruturados.csv", index=False, encoding='utf-8-sig')
        print(f"\nDados de atividades salvos: dados_atividades_estruturados.csv")
    
    if not df_clientes.empty:
        df_clientes.to_csv("dados_clientes_estruturados.csv", index=False, encoding='utf-8-sig')
        print(f"Dados de clientes salvos: dados_clientes_estruturados.csv")
    
    print(f"\nProcessamento concluído com sucesso!")
    print(f"Relatórios salvos em: {diretorio_relatorios}/")

if __name__ == "__main__":
    main()
