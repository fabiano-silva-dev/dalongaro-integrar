#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para extrair dados do arquivo ClienteTempo Gasto.xls
e gerar uma tabela estruturada para relatórios
"""

import pandas as pd
import os
from datetime import datetime
import json

def extrair_dados_produtividade(arquivo_xls):
    """
    Extrai dados do arquivo Excel de produtividade
    """
    try:
        # Tentar diferentes métodos de leitura para arquivos Excel antigos
        print(f"Lendo arquivo: {arquivo_xls}")
        
        # Método 1: Tentar com engine='xlrd'
        try:
            print("Tentando com engine='xlrd'...")
            df = pd.read_excel(arquivo_xls, sheet_name=None, engine='xlrd')
            print("Sucesso com xlrd!")
        except Exception as e1:
            print(f"Falha com xlrd: {e1}")
            
            # Método 2: Tentar com engine='openpyxl'
            try:
                print("Tentando com engine='openpyxl'...")
                df = pd.read_excel(arquivo_xls, sheet_name=None, engine='openpyxl')
                print("Sucesso com openpyxl!")
            except Exception as e2:
                print(f"Falha com openpyxl: {e2}")
                
                # Método 3: Tentar ler como CSV se for um arquivo de texto
                try:
                    print("Tentando ler como arquivo de texto...")
                    # Verificar se é um arquivo de texto
                    with open(arquivo_xls, 'r', encoding='utf-8') as f:
                        primeira_linha = f.readline().strip()
                    
                    if '\t' in primeira_linha:
                        print("Arquivo parece ser TSV (separado por tab)")
                        df = pd.read_csv(arquivo_xls, sep='\t', sheet_name=None)
                    else:
                        print("Arquivo parece ser CSV")
                        df = pd.read_csv(arquivo_xls, sheet_name=None)
                    print("Sucesso com leitura de texto!")
                except Exception as e3:
                    print(f"Falha com leitura de texto: {e3}")
                    raise Exception("Não foi possível ler o arquivo com nenhum método")
        
        # Mostrar todas as abas disponíveis
        print(f"Abas encontradas: {list(df.keys())}")
        
        dados_estruturados = {}
        
        for nome_aba, dados_aba in df.items():
            print(f"\nProcessando aba: {nome_aba}")
            print(f"Forma dos dados: {dados_aba.shape}")
            print(f"Colunas: {list(dados_aba.columns)}")
            
            # Limpar dados (remover linhas vazias)
            dados_limpos = dados_aba.dropna(how='all')
            
            # Converter para dicionário para facilitar manipulação
            dados_dict = dados_limpos.to_dict('records')
            
            dados_estruturados[nome_aba] = {
                'colunas': list(dados_aba.columns),
                'dados': dados_dict,
                'total_registros': len(dados_dict)
            }
            
            # Mostrar primeiras linhas para análise
            print(f"Primeiras 3 linhas da aba {nome_aba}:")
            print(dados_limpos.head(3).to_string())
            print("-" * 80)
        
        return dados_estruturados
        
    except Exception as e:
        print(f"Erro ao ler arquivo: {e}")
        return None

def salvar_dados_json(dados, arquivo_saida):
    """
    Salva os dados extraídos em formato JSON
    """
    try:
        with open(arquivo_saida, 'w', encoding='utf-8') as f:
            json.dump(dados, f, ensure_ascii=False, indent=2, default=str)
        print(f"Dados salvos em: {arquivo_saida}")
    except Exception as e:
        print(f"Erro ao salvar JSON: {e}")

def salvar_dados_csv(dados, diretorio_saida):
    """
    Salva cada aba como um arquivo CSV separado
    """
    try:
        os.makedirs(diretorio_saida, exist_ok=True)
        
        for nome_aba, dados_aba in dados.items():
            if dados_aba['dados']:
                # Criar DataFrame a partir dos dados
                df_temp = pd.DataFrame(dados_aba['dados'])
                
                # Nome do arquivo CSV
                nome_arquivo = f"{nome_aba.replace(' ', '_').replace('/', '_')}.csv"
                caminho_completo = os.path.join(diretorio_saida, nome_arquivo)
                
                # Salvar CSV
                df_temp.to_csv(caminho_completo, index=False, encoding='utf-8-sig')
                print(f"CSV salvo: {caminho_completo}")
                
    except Exception as e:
        print(f"Erro ao salvar CSVs: {e}")

def gerar_relatorio_resumo(dados):
    """
    Gera um relatório resumo dos dados extraídos
    """
    print("\n" + "="*80)
    print("RELATÓRIO RESUMO DOS DADOS EXTRAÍDOS")
    print("="*80)
    
    total_abas = len(dados)
    total_registros_geral = 0
    
    for nome_aba, dados_aba in dados.items():
        print(f"\nAba: {nome_aba}")
        print(f"  - Colunas: {len(dados_aba['colunas'])}")
        print(f"  - Registros: {dados_aba['total_registros']}")
        print(f"  - Colunas: {', '.join(dados_aba['colunas'][:5])}{'...' if len(dados_aba['colunas']) > 5 else ''}")
        
        total_registros_geral += dados_aba['total_registros']
    
    print(f"\nRESUMO GERAL:")
    print(f"  - Total de abas: {total_abas}")
    print(f"  - Total de registros: {total_registros_geral}")
    print("="*80)

def main():
    """
    Função principal
    """
    # Caminho do arquivo
    arquivo_xls = "produtividade/ClienteTempo Gasto.xls"
    
    # Verificar se arquivo existe
    if not os.path.exists(arquivo_xls):
        print(f"Arquivo não encontrado: {arquivo_xls}")
        return
    
    print("Iniciando extração de dados de produtividade...")
    
    # Extrair dados
    dados = extrair_dados_produtividade(arquivo_xls)
    
    if dados is None:
        print("Falha na extração dos dados")
        return
    
    # Gerar relatório resumo
    gerar_relatorio_resumo(dados)
    
    # Salvar dados em JSON
    arquivo_json = "dados_produtividade.json"
    salvar_dados_json(dados, arquivo_json)
    
    # Salvar dados em CSVs
    diretorio_csvs = "dados_produtividade_csvs"
    salvar_dados_csv(dados, diretorio_csvs)
    
    print("\nExtração concluída com sucesso!")
    print(f"Arquivos gerados:")
    print(f"  - {arquivo_json}")
    print(f"  - Diretório: {diretorio_csvs}/")

if __name__ == "__main__":
    main()
