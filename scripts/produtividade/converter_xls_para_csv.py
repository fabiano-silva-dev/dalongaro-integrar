#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para converter o arquivo ClienteTempo Gasto.xls para CSV
"""

import pandas as pd
import os
import sys

def converter_xls_para_csv(arquivo_entrada, arquivo_saida):
    """
    Converte arquivo .xls para .csv
    """
    try:
        print(f"Tentando converter: {arquivo_entrada}")
        
        # Método 1: Tentar com xlrd (para arquivos .xls antigos)
        try:
            print("Tentando com engine='xlrd'...")
            df = pd.read_excel(arquivo_entrada, engine='xlrd')
            print("Sucesso com xlrd!")
            print(f"Forma dos dados: {df.shape}")
            print(f"Colunas: {list(df.columns)}")
            
        except Exception as e1:
            print(f"Falha com xlrd: {e1}")
            
            # Método 2: Tentar com openpyxl
            try:
                print("Tentando com engine='openpyxl'...")
                df = pd.read_excel(arquivo_entrada, engine='openpyxl')
                print("Sucesso com openpyxl!")
                print(f"Forma dos dados: {df.shape}")
                print(f"Colunas: {list(df.columns)}")
                
            except Exception as e2:
                print(f"Falha com openpyxl: {e2}")
                
                # Método 3: Tentar sem especificar engine
                try:
                    print("Tentando sem especificar engine...")
                    df = pd.read_excel(arquivo_entrada)
                    print("Sucesso sem especificar engine!")
                    print(f"Forma dos dados: {df.shape}")
                    print(f"Colunas: {list(df.columns)}")
                    
                except Exception as e3:
                    print(f"Falha sem especificar engine: {e3}")
                    raise Exception("Não foi possível ler o arquivo com nenhum método")
        
        # Mostrar primeiras linhas
        print("\nPrimeiras 5 linhas:")
        print(df.head().to_string())
        
        # Mostrar informações sobre os dados
        print(f"\nInformações do DataFrame:")
        print(f"Total de linhas: {len(df)}")
        print(f"Total de colunas: {len(df.columns)}")
        print(f"Tipos de dados:")
        print(df.dtypes)
        
        # Salvar como CSV
        df.to_csv(arquivo_saida, index=False, encoding='utf-8-sig')
        print(f"\nArquivo CSV salvo com sucesso: {arquivo_saida}")
        
        return df
        
    except Exception as e:
        print(f"Erro na conversão: {e}")
        return None

def converter_todas_as_abas(arquivo_entrada, diretorio_saida):
    """
    Converte todas as abas do arquivo Excel para CSVs separados
    """
    try:
        print(f"Tentando converter todas as abas de: {arquivo_entrada}")
        
        # Criar diretório de saída
        os.makedirs(diretorio_saida, exist_ok=True)
        
        # Método 1: Tentar com xlrd
        try:
            print("Tentando com engine='xlrd'...")
            todas_abas = pd.read_excel(arquivo_entrada, sheet_name=None, engine='xlrd')
            print("Sucesso com xlrd!")
            
        except Exception as e1:
            print(f"Falha com xlrd: {e1}")
            
            # Método 2: Tentar com openpyxl
            try:
                print("Tentando com engine='openpyxl'...")
                todas_abas = pd.read_excel(arquivo_entrada, sheet_name=None, engine='openpyxl')
                print("Sucesso com openpyxl!")
                
            except Exception as e2:
                print(f"Falha com openpyxl: {e2}")
                
                # Método 3: Tentar sem especificar engine
                try:
                    print("Tentando sem especificar engine...")
                    todas_abas = pd.read_excel(arquivo_entrada, sheet_name=None)
                    print("Sucesso sem especificar engine!")
                    
                except Exception as e3:
                    print(f"Falha sem especificar engine: {e3}")
                    raise Exception("Não foi possível ler o arquivo com nenhum método")
        
        print(f"Abas encontradas: {list(todas_abas.keys())}")
        
        # Converter cada aba para CSV
        for nome_aba, dados_aba in todas_abas.items():
            if dados_aba is not None and not dados_aba.empty:
                print(f"\nProcessando aba: {nome_aba}")
                print(f"Forma: {dados_aba.shape}")
                
                # Nome do arquivo CSV
                nome_arquivo = f"{nome_aba.replace(' ', '_').replace('/', '_')}.csv"
                caminho_completo = os.path.join(diretorio_saida, nome_arquivo)
                
                # Salvar CSV
                dados_aba.to_csv(caminho_completo, index=False, encoding='utf-8-sig')
                print(f"CSV salvo: {caminho_completo}")
                
                # Mostrar primeiras linhas
                print("Primeiras 3 linhas:")
                print(dados_aba.head(3).to_string())
                print("-" * 80)
        
        print(f"\nConversão concluída! Arquivos salvos em: {diretorio_saida}")
        return True
        
    except Exception as e:
        print(f"Erro na conversão de todas as abas: {e}")
        return False

def main():
    """
    Função principal
    """
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from runtime import setup_workspace
    setup_workspace()

    arquivo_entrada = "produtividade/ClienteTempo Gasto.xls"
    
    # Verificar se arquivo existe
    if not os.path.exists(arquivo_entrada):
        print(f"Arquivo não encontrado: {arquivo_entrada}")
        return
    
    print("Iniciando conversão do arquivo Excel para CSV...")
    
    # Criar diretório de saída se não existir
    diretorio_saida = "produtividade"
    if not os.path.exists(diretorio_saida):
        os.makedirs(diretorio_saida, exist_ok=True)
    
    # Tentar converter para um único CSV
    arquivo_csv_unico = os.path.join(diretorio_saida, "ClienteTempo Gasto.csv")
    print(f"\n{'='*60}")
    print("TENTANDO CONVERSÃO PARA CSV ÚNICO")
    print(f"{'='*60}")
    
    df_unico = converter_xls_para_csv(arquivo_entrada, arquivo_csv_unico)
    
    if df_unico is not None:
        print(f"\nConversão para CSV único bem-sucedida!")
    else:
        print(f"\nFalha na conversão para CSV único. Tentando converter todas as abas...")
        
        # Tentar converter todas as abas
        diretorio_csvs = os.path.join(diretorio_saida, "processados")
        print(f"\n{'='*60}")
        print("TENTANDO CONVERSÃO DE TODAS AS ABAS")
        print(f"{'='*60}")
        
        sucesso_abas = converter_todas_as_abas(arquivo_entrada, diretorio_csvs)
        
        if sucesso_abas:
            print(f"\nConversão de todas as abas bem-sucedida!")
        else:
            print(f"\nFalha em todos os métodos de conversão.")

if __name__ == "__main__":
    main()





