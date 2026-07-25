#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para comparar arquivo OFX do Sicredi com Razão contábil
Compara dia a dia e identifica diferenças
"""

import pandas as pd
import numpy as np
from datetime import datetime
import os
import sys
import re
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SCRIPTS))
from paths import cliente  # noqa: E402

POSTO_ENTRADA = cliente("posto-pilecco", "entrada")
POSTO_SAIDA = cliente("posto-pilecco", "saida")

def ler_arquivo_ods(arquivo_ods):
    """Lê arquivo ODS (extrato bancário)"""
    try:
        print(f"Lendo arquivo ODS: {arquivo_ods}")
        # Tentar com pandas (requer odfpy)
        try:
            df = pd.read_excel(arquivo_ods, engine='odf')
            print(f"Sucesso! Forma: {df.shape}, Colunas: {list(df.columns)}")
            return df
        except Exception as e1:
            print(f"Erro com pandas/odf: {e1}")
            # Tentar com pyexcel-ods3
            try:
                import pyexcel_ods3
                data = pyexcel_ods3.get_data(arquivo_ods)
                # Pegar primeira aba
                sheet_name = list(data.keys())[0]
                df = pd.DataFrame(data[sheet_name])
                print(f"Sucesso com pyexcel-ods3! Forma: {df.shape}")
                return df
            except Exception as e2:
                print(f"Erro com pyexcel-ods3: {e2}")
                raise Exception("Não foi possível ler arquivo ODS")
    except Exception as e:
        print(f"Erro ao ler ODS: {e}")
        return None

def converter_xls_com_libreoffice(arquivo_xls, arquivo_saida_csv):
    """Tenta converter XLS para CSV usando LibreOffice"""
    try:
        import subprocess
        print(f"Tentando converter com LibreOffice: {arquivo_xls}")
        # Converter para CSV usando LibreOffice
        cmd = [
            'libreoffice',
            '--headless',
            '--convert-to', 'csv',
            '--outdir', os.path.dirname(arquivo_saida_csv) or '.',
            arquivo_xls
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            # LibreOffice cria arquivo com mesmo nome mas extensão .csv
            arquivo_csv_gerado = arquivo_xls.rsplit('.', 1)[0] + '.csv'
            if os.path.exists(arquivo_csv_gerado):
                print(f"Conversão bem-sucedida: {arquivo_csv_gerado}")
                return arquivo_csv_gerado
        print(f"Falha na conversão: {result.stderr}")
        return None
    except Exception as e:
        print(f"Erro ao converter com LibreOffice: {e}")
        return None

def ler_arquivo_xls(arquivo_xls):
    """Lê arquivo XLS (Razão contábil)"""
    try:
        print(f"Lendo arquivo XLS: {arquivo_xls}")
        
        # Primeiro, verificar se já existe CSV convertido
        arquivo_csv = arquivo_xls.rsplit('.', 1)[0] + '.csv'
        if os.path.exists(arquivo_csv):
            print(f"Arquivo CSV encontrado: {arquivo_csv}, tentando ler...")
            try:
                codificacoes = ['utf-8', 'latin1', 'iso-8859-1', 'cp1252']
                for cod in codificacoes:
                    try:
                        df = pd.read_csv(arquivo_csv, encoding=cod, sep=',', on_bad_lines='skip')
                        print(f"Sucesso lendo CSV (encoding={cod})! Forma: {df.shape}, Colunas: {list(df.columns)}")
                        return df
                    except:
                        continue
            except Exception as e:
                print(f"Falha ao ler CSV existente: {e}")
        
        # Método 1: Tentar com xlrd diretamente (versão 1.2.0 para formatos BIFF antigos)
        try:
            import xlrd
            # Tentar com xlrd diretamente
            print("Tentando com xlrd diretamente...")
            workbook = xlrd.open_workbook(arquivo_xls, formatting_info=False)
            sheet = workbook.sheet_by_index(0)
            
            # Converter para DataFrame
            data = []
            for row_idx in range(sheet.nrows):
                row = []
                for col_idx in range(sheet.ncols):
                    cell = sheet.cell(row_idx, col_idx)
                    # Converter tipos de data
                    if cell.ctype == xlrd.XL_CELL_DATE:
                        try:
                            date_tuple = xlrd.xldate_as_tuple(cell.value, workbook.datemode)
                            if date_tuple[0] > 1900:  # Data válida
                                from datetime import datetime
                                date_value = datetime(*date_tuple[:6]).date()
                                row.append(date_value)
                            else:
                                row.append(cell.value)
                        except:
                            row.append(cell.value)
                    else:
                        row.append(cell.value)
                data.append(row)
            
            if len(data) > 0:
                # Primeira linha como cabeçalho
                if len(data) > 1:
                    df = pd.DataFrame(data[1:], columns=data[0])
                else:
                    df = pd.DataFrame(data)
                print(f"Sucesso com xlrd direto! Forma: {df.shape}, Colunas: {list(df.columns)}")
                return df
        except Exception as e1:
            print(f"Falha com xlrd direto: {e1}")
        
        # Método 2: Tentar com pandas e xlrd (pode não funcionar com xlrd 1.2.0)
        try:
            print("Tentando com pandas/xlrd...")
            # Temporariamente desabilitar verificação de versão do pandas
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                df = pd.read_excel(arquivo_xls, engine='xlrd')
            print(f"Sucesso com pandas/xlrd! Forma: {df.shape}, Colunas: {list(df.columns)}")
            return df
        except Exception as e2:
            print(f"Falha com pandas/xlrd: {e2}")
        
        # Método 3: Tentar com pyexcel-xls
        try:
            import pyexcel_xls
            print("Tentando com pyexcel-xls...")
            data = pyexcel_xls.get_data(arquivo_xls)
            sheet_name = list(data.keys())[0]
            df = pd.DataFrame(data[sheet_name])
            # Primeira linha como cabeçalho
            if len(df) > 0:
                df.columns = df.iloc[0]
                df = df[1:].reset_index(drop=True)
            print(f"Sucesso com pyexcel-xls! Forma: {df.shape}, Colunas: {list(df.columns)}")
            return df
        except Exception as e3:
            print(f"Falha com pyexcel-xls: {e3}")
        
        # Método 4: Tentar com openpyxl
        try:
            print("Tentando com openpyxl...")
            df = pd.read_excel(arquivo_xls, engine='openpyxl')
            print(f"Sucesso com openpyxl! Forma: {df.shape}, Colunas: {list(df.columns)}")
            return df
        except Exception as e4:
            print(f"Falha com openpyxl: {e4}")
        
        # Método 5: Tentar sem especificar engine
        try:
            print("Tentando sem especificar engine...")
            df = pd.read_excel(arquivo_xls)
            print(f"Sucesso sem engine! Forma: {df.shape}, Colunas: {list(df.columns)}")
            return df
        except Exception as e5:
            print(f"Falha sem engine: {e5}")
        
        # Método 6: Tentar converter com LibreOffice e ler CSV
        try:
            print("Tentando converter com LibreOffice...")
            arquivo_csv_temp = arquivo_xls.rsplit('.', 1)[0] + '_temp.csv'
            arquivo_csv_convertido = converter_xls_com_libreoffice(arquivo_xls, arquivo_csv_temp)
            if arquivo_csv_convertido and os.path.exists(arquivo_csv_convertido):
                # Tentar diferentes codificações
                codificacoes = ['utf-8', 'latin1', 'iso-8859-1', 'cp1252']
                for cod in codificacoes:
                    try:
                        df = pd.read_csv(arquivo_csv_convertido, encoding=cod, sep=',')
                        print(f"Sucesso com CSV convertido (encoding={cod})! Forma: {df.shape}, Colunas: {list(df.columns)}")
                        # Limpar arquivo temporário
                        try:
                            os.remove(arquivo_csv_convertido)
                        except:
                            pass
                        return df
                    except:
                        continue
        except Exception as e6:
            print(f"Falha com conversão LibreOffice: {e6}")
        
        raise Exception("Não foi possível ler arquivo XLS com nenhum método")
    except Exception as e:
        print(f"Erro ao ler XLS: {e}")
        return None

def identificar_colunas_data_valor(df, nome_arquivo):
    """Identifica automaticamente colunas de data e valor"""
    print(f"\nAnalisando colunas de {nome_arquivo}:")
    print(df.head(10).to_string())
    
    # Procurar coluna de data
    coluna_data = None
    for col in df.columns:
        # Verificar se contém datas
        try:
            amostra = df[col].dropna().head(100)
            if len(amostra) > 0:
                # Tentar converter para data
                pd.to_datetime(amostra, errors='coerce', dayfirst=True)
                datas_validas = pd.to_datetime(amostra, errors='coerce', dayfirst=True).notna().sum()
                if datas_validas > len(amostra) * 0.5:  # Mais de 50% são datas
                    coluna_data = col
                    print(f"  Coluna de data encontrada: {col}")
                    break
        except:
            continue
    
    # Procurar colunas de valor
    colunas_valor = []
    for col in df.columns:
        try:
            amostra = df[col].dropna().head(100)
            if len(amostra) > 0:
                # Tentar converter para numérico
                valores = pd.to_numeric(amostra, errors='coerce')
                valores_validos = valores.notna().sum()
                if valores_validos > len(amostra) * 0.5:
                    # Verificar se tem valores monetários
                    valores_abs = valores.abs()
                    if valores_abs.max() > 0.01:  # Valores significativos
                        colunas_valor.append(col)
                        print(f"  Coluna de valor encontrada: {col}")
        except:
            continue
    
    # Procurar coluna de histórico/descrição
    coluna_historico = None
    for col in df.columns:
        amostra = df[col].dropna().head(100)
        if len(amostra) > 0:
            # Verificar se são strings
            if amostra.dtype == 'object':
                # Verificar se tem texto descritivo
                texto_medio = amostra.astype(str).str.len().mean()
                if texto_medio > 5:  # Texto médio maior que 5 caracteres
                    coluna_historico = col
                    print(f"  Coluna de histórico encontrada: {col}")
                    break
    
    return coluna_data, colunas_valor, coluna_historico

def processar_extrato_sicredi(df):
    """Processa extrato bancário do Sicredi"""
    print("\n=== Processando Extrato Sicredi ===")
    
    # Identificar colunas manualmente para o Sicredi (já conhecemos a estrutura)
    col_data = None
    col_valor = None
    col_historico = None
    
    for col in df.columns:
        col_upper = str(col).upper()
        if 'DATA' in col_upper and col_data is None:
            col_data = col
        elif 'VALOR' in col_upper and col_valor is None:
            col_valor = col
        elif 'DESCRIÇÃO' in col_upper or 'DESCRICAO' in col_upper or 'HISTÓRICO' in col_upper or 'HISTORICO' in col_upper:
            col_historico = col
    
    # Se não encontrou, usar identificação automática
    if not col_data or not col_historico:
        col_data, colunas_valor, col_historico = identificar_colunas_data_valor(df, "Sicredi")
        if colunas_valor:
            col_valor = colunas_valor[0]
    
    if not col_data:
        print("AVISO: Coluna de data não encontrada automaticamente")
        print("Por favor, verifique as colunas manualmente")
        return None
    
    if not col_valor:
        print("AVISO: Coluna de valor não encontrada automaticamente")
        return None
    
    if not col_historico:
        print("AVISO: Coluna de histórico não encontrada, usando coluna DESCRIÇÃO")
        # Tentar encontrar coluna DESCRIÇÃO
        for col in df.columns:
            if 'DESCRIÇÃO' in str(col).upper() or 'DESCRICAO' in str(col).upper():
                col_historico = col
                break
    
    # Criar DataFrame processado
    dados = []
    
    for idx, row in df.iterrows():
        try:
            # Data
            data = pd.to_datetime(row[col_data], errors='coerce', dayfirst=True)
            if pd.isna(data):
                continue
            
            # Valores - usar coluna VALOR e TIPO para determinar entrada/saída
            valor = 0
            tipo = None
            
            # Verificar coluna TIPO se existir
            tipo_str = None
            if 'TIPO' in df.columns:
                tipo_str = str(row['TIPO']).upper() if pd.notna(row['TIPO']) else ""
            
            val = pd.to_numeric(row[col_valor], errors='coerce')
            if pd.notna(val) and abs(val) > 0.001:
                if tipo_str:
                    if 'CREDIT' in tipo_str or 'CRÉDITO' in tipo_str or 'ENTRADA' in tipo_str:
                        valor = abs(val)
                        tipo = 'ENTRADA'
                    elif 'DEBIT' in tipo_str or 'DÉBITO' in tipo_str or 'SAIDA' in tipo_str or 'SAÍDA' in tipo_str:
                        valor = -abs(val)
                        tipo = 'SAIDA'
                    else:
                        # Se não identificou, usar sinal do valor
                        valor = val
                        tipo = 'ENTRADA' if val > 0 else 'SAIDA'
                else:
                    # Se não tem coluna TIPO, usar sinal do valor
                    valor = val
                    tipo = 'ENTRADA' if val > 0 else 'SAIDA'
            
            if abs(valor) < 0.001:
                continue
            
            # Histórico
            historico = str(row[col_historico]) if col_historico and pd.notna(row[col_historico]) else ""
            
            dados.append({
                'data': data.date(),
                'valor': valor,
                'tipo': tipo if tipo else ('ENTRADA' if valor > 0 else 'SAIDA'),
                'historico': historico,
                'origem': 'SICREDI'
            })
        except Exception as e:
            print(f"Erro ao processar linha {idx}: {e}")
            continue
    
    df_processado = pd.DataFrame(dados)
    print(f"Total de registros processados: {len(df_processado)}")
    return df_processado

def processar_razao(df):
    """Processa razão contábil"""
    print("\n=== Processando Razão Contábil ===")
    
    # Procurar linha de cabeçalho (geralmente contém "Data", "Débito", "Crédito")
    linha_cabecalho = None
    for idx, row in df.iterrows():
        row_str = ' '.join([str(x) for x in row.values if pd.notna(x)]).upper()
        if 'DATA' in row_str and ('DÉBITO' in row_str or 'DEBITO' in row_str) and ('CRÉDITO' in row_str or 'CREDITO' in row_str):
            linha_cabecalho = idx
            print(f"Linha de cabeçalho encontrada: {idx}")
            break
    
    if linha_cabecalho is None:
        print("AVISO: Cabeçalho não encontrado, tentando identificar colunas automaticamente")
        col_data, colunas_valor, col_historico = identificar_colunas_data_valor(df, "Razão")
    else:
        # Usar a linha de cabeçalho para identificar colunas
        cabecalho = df.iloc[linha_cabecalho]
        col_data = None
        col_debito = None
        col_credito = None
        col_historico = None
        
        for idx, col_name in enumerate(cabecalho):
            col_str = str(col_name).upper() if pd.notna(col_name) else ""
            if 'DATA' in col_str:
                col_data = idx
            elif 'DÉBITO' in col_str or 'DEBITO' in col_str:
                col_debito = idx
            elif 'CRÉDITO' in col_str or 'CREDITO' in col_str:
                col_credito = idx
            elif 'HISTÓRICO' in col_str or 'HISTORICO' in col_str:
                col_historico = idx
        
        print(f"Colunas identificadas - Data: {col_data}, Débito: {col_debito}, Crédito: {col_credito}, Histórico: {col_historico}")
        
        if col_data is None:
            print("AVISO: Coluna de data não encontrada")
            return None
    
    # Criar DataFrame processado
    dados = []
    inicio_dados = linha_cabecalho + 2 if linha_cabecalho is not None else 0  # Pular cabeçalho e linha de conta
    
    for idx in range(inicio_dados, len(df)):
        try:
            row = df.iloc[idx]
            
            # Data
            if col_data is not None:
                data_str = str(row.iloc[col_data]) if col_data < len(row) else None
            else:
                # Tentar primeira coluna
                data_str = str(row.iloc[0]) if len(row) > 0 else None
            
            if not data_str or data_str == 'nan' or data_str.strip() == '':
                continue
            
            data = pd.to_datetime(data_str, errors='coerce', dayfirst=True)
            if pd.isna(data):
                continue
            
            # Valores - Débito e Crédito
            valor = 0
            tipo = None
            
            # Tentar coluna de débito
            if col_debito is not None and col_debito < len(row):
                debito_str = str(row.iloc[col_debito]) if pd.notna(row.iloc[col_debito]) else ""
                if debito_str and debito_str != 'nan':
                    # Converter vírgula para ponto
                    debito_str = debito_str.replace(',', '.').replace('"', '').strip()
                    debito = pd.to_numeric(debito_str, errors='coerce')
                    if pd.notna(debito) and debito > 0.001:
                        valor = debito  # Débito é entrada (positivo) - aumenta saldo da conta
                        tipo = 'ENTRADA'
            
            # Tentar coluna de crédito
            if col_credito is not None and col_credito < len(row):
                credito_str = str(row.iloc[col_credito]) if pd.notna(row.iloc[col_credito]) else ""
                if credito_str and credito_str != 'nan':
                    # Converter vírgula para ponto
                    credito_str = credito_str.replace(',', '.').replace('"', '').strip()
                    credito = pd.to_numeric(credito_str, errors='coerce')
                    if pd.notna(credito) and credito > 0.001:
                        valor = -credito  # Crédito é saída (negativo) - diminui saldo da conta
                        tipo = 'SAIDA'
            
            if abs(valor) < 0.001:
                continue
            
            # Histórico
            if col_historico is not None and col_historico < len(row):
                historico = str(row.iloc[col_historico]) if pd.notna(row.iloc[col_historico]) else ""
            else:
                # Tentar coluna 2 (geralmente histórico)
                historico = str(row.iloc[2]) if len(row) > 2 and pd.notna(row.iloc[2]) else ""
            
            dados.append({
                'data': data.date(),
                'valor': valor,
                'tipo': tipo if tipo else ('ENTRADA' if valor > 0 else 'SAIDA'),
                'historico': historico,
                'origem': 'RAZAO'
            })
        except Exception as e:
            # Ignorar erros silenciosamente para não poluir o output
            continue
    
    df_processado = pd.DataFrame(dados)
    print(f"Total de registros processados: {len(df_processado)}")
    return df_processado

def comparar_por_dia(df_sicredi, df_razao):
    """Compara os dados dia a dia"""
    print("\n=== Comparação Dia a Dia ===")
    
    # Agrupar por dia
    sicredi_dia = df_sicredi.groupby('data').agg({
        'valor': ['sum', 'count'],
        'tipo': lambda x: {
            'ENTRADAS': (x == 'ENTRADA').sum(),
            'SAIDAS': (x == 'SAIDA').sum()
        }
    }).reset_index()
    
    sicredi_dia.columns = ['data', 'total_valor', 'qtd_transacoes', 'tipos']
    sicredi_dia['total_entradas'] = sicredi_dia['tipos'].apply(lambda x: x['ENTRADAS'])
    sicredi_dia['total_saidas'] = sicredi_dia['tipos'].apply(lambda x: x['SAIDAS'])
    sicredi_dia = sicredi_dia.drop('tipos', axis=1)
    
    # Calcular entradas e saídas separadamente
    sicredi_entradas = df_sicredi[df_sicredi['tipo'] == 'ENTRADA'].groupby('data')['valor'].sum().reset_index()
    sicredi_entradas.columns = ['data', 'entradas']
    sicredi_saidas = df_sicredi[df_sicredi['tipo'] == 'SAIDA'].groupby('data')['valor'].sum().reset_index()
    sicredi_saidas.columns = ['data', 'saidas']
    
    sicredi_dia = sicredi_dia.merge(sicredi_entradas, on='data', how='left')
    sicredi_dia = sicredi_dia.merge(sicredi_saidas, on='data', how='left')
    sicredi_dia['entradas'] = sicredi_dia['entradas'].fillna(0)
    sicredi_dia['saidas'] = sicredi_dia['saidas'].fillna(0)
    sicredi_dia['origem'] = 'SICREDI'
    
    # Razão
    razao_dia = df_razao.groupby('data').agg({
        'valor': ['sum', 'count'],
        'tipo': lambda x: {
            'ENTRADAS': (x == 'ENTRADA').sum(),
            'SAIDAS': (x == 'SAIDA').sum()
        }
    }).reset_index()
    
    razao_dia.columns = ['data', 'total_valor', 'qtd_transacoes', 'tipos']
    razao_dia['total_entradas'] = razao_dia['tipos'].apply(lambda x: x['ENTRADAS'])
    razao_dia['total_saidas'] = razao_dia['tipos'].apply(lambda x: x['SAIDAS'])
    razao_dia = razao_dia.drop('tipos', axis=1)
    
    razao_entradas = df_razao[df_razao['tipo'] == 'ENTRADA'].groupby('data')['valor'].sum().reset_index()
    razao_entradas.columns = ['data', 'entradas']
    razao_saidas = df_razao[df_razao['tipo'] == 'SAIDA'].groupby('data')['valor'].sum().reset_index()
    razao_saidas.columns = ['data', 'saidas']
    
    razao_dia = razao_dia.merge(razao_entradas, on='data', how='left')
    razao_dia = razao_dia.merge(razao_saidas, on='data', how='left')
    razao_dia['entradas'] = razao_dia['entradas'].fillna(0)
    razao_dia['saidas'] = razao_dia['saidas'].fillna(0)
    razao_dia['origem'] = 'RAZAO'
    
    # Juntar para comparação
    comparacao = sicredi_dia.merge(razao_dia, on='data', how='outer', suffixes=('_sicredi', '_razao'))
    comparacao = comparacao.fillna(0)
    
    # Calcular diferenças
    comparacao['diff_total'] = comparacao['total_valor_sicredi'] - comparacao['total_valor_razao']
    comparacao['diff_entradas'] = comparacao['entradas_sicredi'] - comparacao['entradas_razao']
    comparacao['diff_saidas'] = comparacao['saidas_sicredi'] - comparacao['saidas_razao']
    comparacao['diff_qtd'] = comparacao['qtd_transacoes_sicredi'] - comparacao['qtd_transacoes_razao']
    
    # Ordenar por data
    comparacao = comparacao.sort_values('data')
    
    return comparacao, sicredi_dia, razao_dia

def gerar_relatorio(comparacao, df_sicredi, df_razao):
    """Gera relatório completo"""
    print("\n" + "="*80)
    print("RELATÓRIO DE COMPARAÇÃO - SICREDI vs RAZÃO")
    print("="*80)
    
    # Totais gerais
    print("\n--- TOTAIS GERAIS ---")
    total_entradas_sicredi = df_sicredi[df_sicredi['tipo'] == 'ENTRADA']['valor'].sum()
    total_saidas_sicredi = abs(df_sicredi[df_sicredi['tipo'] == 'SAIDA']['valor'].sum())
    saldo_sicredi = df_sicredi['valor'].sum()
    
    total_entradas_razao = df_razao[df_razao['tipo'] == 'ENTRADA']['valor'].sum()
    total_saidas_razao = abs(df_razao[df_razao['tipo'] == 'SAIDA']['valor'].sum())
    saldo_razao = df_razao['valor'].sum()
    
    print(f"\nSICREDI:")
    print(f"  Total Entradas: R$ {total_entradas_sicredi:,.2f}")
    print(f"  Total Saídas:   R$ {total_saidas_sicredi:,.2f}")
    print(f"  Saldo:          R$ {saldo_sicredi:,.2f}")
    print(f"  Qtd Transações: {len(df_sicredi)}")
    
    print(f"\nRAZÃO:")
    print(f"  Total Entradas: R$ {total_entradas_razao:,.2f}")
    print(f"  Total Saídas:   R$ {total_saidas_razao:,.2f}")
    print(f"  Saldo:          R$ {saldo_razao:,.2f}")
    print(f"  Qtd Transações: {len(df_razao)}")
    
    print(f"\nDIFERENÇAS:")
    print(f"  Diferença Entradas: R$ {total_entradas_sicredi - total_entradas_razao:,.2f}")
    print(f"  Diferença Saídas:   R$ {total_saidas_sicredi - total_saidas_razao:,.2f}")
    print(f"  Diferença Saldo:    R$ {saldo_sicredi - saldo_razao:,.2f}")
    print(f"  Diferença Qtd:      {len(df_sicredi) - len(df_razao)} transações")
    
    # Comparação dia a dia
    print("\n--- COMPARAÇÃO DIA A DIA ---")
    print("\nDias com diferenças:")
    print("-"*80)
    
    diferencas = comparacao[
        (abs(comparacao['diff_total']) > 0.01) | 
        (abs(comparacao['diff_entradas']) > 0.01) | 
        (abs(comparacao['diff_saidas']) > 0.01)
    ]
    
    if len(diferencas) > 0:
        for _, row in diferencas.iterrows():
            print(f"\nData: {row['data']}")
            print(f"  SICREDI - Entradas: R$ {row['entradas_sicredi']:,.2f} | Saídas: R$ {row['saidas_sicredi']:,.2f} | Total: R$ {row['total_valor_sicredi']:,.2f} | Qtd: {row['qtd_transacoes_sicredi']:.0f}")
            print(f"  RAZÃO   - Entradas: R$ {row['entradas_razao']:,.2f} | Saídas: R$ {row['saidas_razao']:,.2f} | Total: R$ {row['total_valor_razao']:,.2f} | Qtd: {row['qtd_transacoes_razao']:.0f}")
            print(f"  DIFERENÇA - Entradas: R$ {row['diff_entradas']:,.2f} | Saídas: R$ {row['diff_saidas']:,.2f} | Total: R$ {row['diff_total']:,.2f} | Qtd: {row['diff_qtd']:.0f}")
    else:
        print("Nenhuma diferença encontrada!")
    
    # Salvar em CSV
    arquivo_saida = str(POSTO_SAIDA / "comparacao_sicredi_razao.csv")
    comparacao.to_csv(arquivo_saida, index=False, encoding='utf-8-sig')
    print(f"\n\nRelatório detalhado salvo em: {arquivo_saida}")
    
    # Salvar histórico por dia
    arquivo_historico = str(POSTO_SAIDA / "historico_por_dia.csv")
    historico_dia = []
    
    todas_datas = sorted(set(df_sicredi['data'].tolist() + df_razao['data'].tolist()))
    
    for data in todas_datas:
        sicredi_dia = df_sicredi[df_sicredi['data'] == data]
        razao_dia = df_razao[df_razao['data'] == data]
        
        for _, row in sicredi_dia.iterrows():
            historico_dia.append({
                'data': data,
                'origem': 'SICREDI',
                'tipo': row['tipo'],
                'valor': row['valor'],
                'historico': row['historico']
            })
        
        for _, row in razao_dia.iterrows():
            historico_dia.append({
                'data': data,
                'origem': 'RAZAO',
                'tipo': row['tipo'],
                'valor': row['valor'],
                'historico': row['historico']
            })
    
    df_historico = pd.DataFrame(historico_dia)
    df_historico = df_historico.sort_values(['data', 'origem', 'tipo'])
    
    # Formatar números no padrão brasileiro antes de salvar
    df_historico_formatado = df_historico.copy()
    
    # Função para formatar números no padrão brasileiro
    def formatar_br(valor):
        if pd.isna(valor) or valor == '':
            return ''
        try:
            valor_float = float(valor)
            valor_str = f"{valor_float:,.2f}"  # Formato: 1234.56
            # Trocar ponto por vírgula (decimal) e vírgula por ponto (milhar)
            valor_str = valor_str.replace(',', 'TEMP').replace('.', ',').replace('TEMP', '.')
            return valor_str
        except:
            return str(valor)
    
    # Formatar coluna de valor
    if 'valor' in df_historico_formatado.columns:
        df_historico_formatado['valor'] = df_historico_formatado['valor'].apply(formatar_br)
    
    # Salvar com separador ";" e números no padrão brasileiro
    df_historico_formatado.to_csv(arquivo_historico, index=False, encoding='utf-8-sig', sep=';')
    print(f"Histórico detalhado salvo em: {arquivo_historico}")

def resumir_historico(historico):
    """Resume o histórico removendo detalhes e mantendo palavras-chave"""
    if pd.isna(historico) or not historico:
        return "SEM HISTÓRICO"
    
    hist = str(historico).upper().strip()
    
    # Remover caracteres especiais e números longos
    # Remover números longos (como códigos de transação)
    hist = re.sub(r'\d{10,}', '', hist)
    # Remover datas no formato DD/MM/YYYY
    hist = re.sub(r'\d{2}/\d{2}/\d{4}', '', hist)
    # Remover referências N/DATA
    hist = hist.replace('N/DATA', '').replace('N/DATA.', '')
    # Remover múltiplos espaços
    hist = re.sub(r'\s+', ' ', hist).strip()
    
    # Identificar palavras-chave principais
    palavras_chave = []
    
    # Tipos de transação comuns
    if any(x in hist for x in ['PIX', 'PIX RECEBIDO', 'PIX ENVIADO', 'RECEBIMENTO PIX']):
        if 'RECEBIMENTO PIX' in hist or 'RECEBIDO' in hist or 'RECEB' in hist:
            return "PIX RECEBIDO"
        elif 'ENVIADO' in hist or 'ENVI' in hist:
            return "PIX ENVIADO"
        return "PIX"
    
    # Depósitos de dinheiro no ATM (normalizar variações)
    if any(x in hist for x in ['DEP DINHEIRO', 'DEPÓSITO DINHEIRO', 'DEPOSITO DINHEIRO', 'DEP DINHEIRO ATM']):
        # Normalizar: remover códigos de transação e manter apenas o essencial
        # Ex: "DEP DINHEIRO ATM-892f7b8d 01297741030 DOUGLAS SCHIO PILECCO" 
        # e "DEPÓSITO BANCÁRIO  OUTROS DEP DINHEIRO ATM 01297741030 DOUGLAS SCHIO PILECCO"
        # ambos devem ser "DEPÓSITO DINHEIRO ATM"
        return "DEPÓSITO DINHEIRO ATM"
    
    if any(x in hist for x in ['DEPOSITO', 'DEPÓSITO', 'DEP CHEQUE', 'DEPOSITO CHEQUE']):
        return "DEPÓSITO CHEQUE"
    
    if any(x in hist for x in ['TRANSFERENCIA', 'TRANSFERÊNCIA']):
        if 'RECEBIDA' in hist or 'RECEB' in hist:
            return "TRANSFERÊNCIA RECEBIDA"
        elif 'ENVIADA' in hist or 'ENVI' in hist:
            return "TRANSFERÊNCIA ENVIADA"
        return "TRANSFERÊNCIA"
    
    if any(x in hist for x in ['CARTAO', 'CARTÃO', 'CARTAO CREDITO', 'CARTAO DEBITO']):
        if 'CREDITO' in hist or 'CRÉDITO' in hist:
            return "CARTÃO CRÉDITO"
        elif 'DEBITO' in hist or 'DÉBITO' in hist:
            return "CARTÃO DÉBITO"
        return "CARTÃO"
    
    if any(x in hist for x in ['BOLETO', 'LIQUIDACAO BOLETO', 'LIQUIDAÇÃO']):
        return "BOLETO"
    
    if any(x in hist for x in ['TED', 'DOC']):
        return "TED/DOC"
    
    if any(x in hist for x in ['TARIFA', 'TAXA', 'IOF', 'JUROS']):
        return "TARIFAS E TAXAS"
    
    if any(x in hist for x in ['SALARIO', 'SALÁRIO', 'FOLHA']):
        return "PAGAMENTO SALÁRIO"
    
    if any(x in hist for x in ['FORNECEDOR', 'FORNEC']):
        return "PAGAMENTO FORNECEDOR"
    
    if any(x in hist for x in ['CLIENTE', 'RECEBIMENTO CLIENTE', 'VENDA']):
        return "RECEBIMENTO CLIENTE"
    
    # Se não encontrou palavra-chave, pegar primeiras palavras significativas
    palavras = [p for p in hist.split() if len(p) > 3 and p.isalpha()]
    if palavras:
        return ' '.join(palavras[:3]).upper()
    
    return hist[:50] if len(hist) > 50 else hist

def comparar_entradas_por_historico(df_sicredi, df_razao):
    """Compara entradas agrupadas por histórico resumido"""
    print("\n" + "="*80)
    print("COMPARAÇÃO DE ENTRADAS POR HISTÓRICO RESUMIDO")
    print("="*80)
    
    # Filtrar apenas entradas
    entradas_sicredi = df_sicredi[df_sicredi['tipo'] == 'ENTRADA'].copy()
    entradas_razao = df_razao[df_razao['tipo'] == 'ENTRADA'].copy()
    
    # Adicionar coluna de histórico resumido
    entradas_sicredi['historico_resumido'] = entradas_sicredi['historico'].apply(resumir_historico)
    entradas_razao['historico_resumido'] = entradas_razao['historico'].apply(resumir_historico)
    
    # Agrupar por histórico resumido
    sicredi_por_hist = entradas_sicredi.groupby('historico_resumido').agg({
        'valor': ['sum', 'count']
    }).reset_index()
    sicredi_por_hist.columns = ['historico_resumido', 'total_sicredi', 'qtd_sicredi']
    
    razao_por_hist = entradas_razao.groupby('historico_resumido').agg({
        'valor': ['sum', 'count']
    }).reset_index()
    razao_por_hist.columns = ['historico_resumido', 'total_razao', 'qtd_razao']
    
    # Juntar para comparação
    comparacao_hist = sicredi_por_hist.merge(razao_por_hist, on='historico_resumido', how='outer')
    comparacao_hist = comparacao_hist.fillna(0)
    
    # Calcular diferenças
    comparacao_hist['diff_total'] = comparacao_hist['total_sicredi'] - comparacao_hist['total_razao']
    comparacao_hist['diff_qtd'] = comparacao_hist['qtd_sicredi'] - comparacao_hist['qtd_razao']
    
    # Ordenar por diferença absoluta (maiores diferenças primeiro)
    comparacao_hist['diff_abs'] = comparacao_hist['diff_total'].abs()
    comparacao_hist = comparacao_hist.sort_values('diff_abs', ascending=False)
    
    print("\n--- RESUMO POR HISTÓRICO (ordenado por maior diferença) ---\n")
    print(f"{'Histórico Resumido':<40} {'Sicredi':>15} {'Razão':>15} {'Diferença':>15} {'Qtd Sicredi':>12} {'Qtd Razão':>12}")
    print("-" * 110)
    
    for _, row in comparacao_hist.iterrows():
        hist = row['historico_resumido'][:38] if len(row['historico_resumido']) > 38 else row['historico_resumido']
        print(f"{hist:<40} {row['total_sicredi']:>15,.2f} {row['total_razao']:>15,.2f} {row['diff_total']:>15,.2f} {row['qtd_sicredi']:>12.0f} {row['qtd_razao']:>12.0f}")
    
    # Mostrar apenas diferenças significativas
    print("\n--- DIFERENÇAS SIGNIFICATIVAS (diferença > R$ 10,00) ---\n")
    diferencas = comparacao_hist[comparacao_hist['diff_abs'] > 10]
    
    if len(diferencas) > 0:
        print(f"{'Histórico Resumido':<40} {'Sicredi':>15} {'Razão':>15} {'Diferença':>15}")
        print("-" * 85)
        for _, row in diferencas.iterrows():
            hist = row['historico_resumido'][:38] if len(row['historico_resumido']) > 38 else row['historico_resumido']
            print(f"{hist:<40} {row['total_sicredi']:>15,.2f} {row['total_razao']:>15,.2f} {row['diff_total']:>15,.2f}")
    else:
        print("Nenhuma diferença significativa encontrada!")
    
    # Salvar em CSV com separador ";" e números no padrão brasileiro
    arquivo_saida = str(POSTO_SAIDA / "comparacao_entradas_por_historico.csv")
    
    # Criar cópia para formatação
    comparacao_hist_formatado = comparacao_hist.copy()
    
    # Função para formatar números no padrão brasileiro
    def formatar_br(valor):
        if pd.isna(valor) or valor == '':
            return ''
        try:
            # Formatar com 2 casas decimais, vírgula como decimal, ponto como milhar
            valor_float = float(valor)
            # Usar locale ou formatação manual
            valor_str = f"{valor_float:,.2f}"  # Formato: 1234.56
            # Trocar ponto por vírgula (decimal) e vírgula por ponto (milhar)
            valor_str = valor_str.replace(',', 'TEMP').replace('.', ',').replace('TEMP', '.')
            return valor_str
        except:
            return str(valor)
    
    # Formatar números monetários no padrão brasileiro
    colunas_monetarias = ['total_sicredi', 'total_razao', 'diff_total', 'diff_abs']
    for col in colunas_monetarias:
        if col in comparacao_hist_formatado.columns:
            comparacao_hist_formatado[col] = comparacao_hist_formatado[col].apply(formatar_br)
    
    # Formatar quantidades como inteiros
    if 'qtd_sicredi' in comparacao_hist_formatado.columns:
        comparacao_hist_formatado['qtd_sicredi'] = comparacao_hist_formatado['qtd_sicredi'].apply(
            lambda x: f"{int(float(x))}" if pd.notna(x) and x != '' else '0'
        )
    if 'qtd_razao' in comparacao_hist_formatado.columns:
        comparacao_hist_formatado['qtd_razao'] = comparacao_hist_formatado['qtd_razao'].apply(
            lambda x: f"{int(float(x))}" if pd.notna(x) and x != '' else '0'
        )
    if 'diff_qtd' in comparacao_hist_formatado.columns:
        comparacao_hist_formatado['diff_qtd'] = comparacao_hist_formatado['diff_qtd'].apply(
            lambda x: f"{int(float(x))}" if pd.notna(x) and x != '' else '0'
        )
    
    # Salvar com separador ";"
    comparacao_hist_formatado.to_csv(arquivo_saida, index=False, encoding='utf-8-sig', sep=';')
    print(f"\n\nComparação por histórico salva em: {arquivo_saida}")
    
    # Detalhar transações que estão apenas em um dos arquivos
    print("\n--- HISTÓRICOS APENAS NO SICREDI ---\n")
    apenas_sicredi = comparacao_hist[comparacao_hist['total_razao'] == 0]
    if len(apenas_sicredi) > 0:
        for _, row in apenas_sicredi.head(20).iterrows():
            print(f"  {row['historico_resumido']:<50} R$ {row['total_sicredi']:>15,.2f} ({row['qtd_sicredi']:.0f} transações)")
    else:
        print("  Nenhum histórico encontrado apenas no Sicredi")
    
    print("\n--- HISTÓRICOS APENAS NO RAZÃO ---\n")
    apenas_razao = comparacao_hist[comparacao_hist['total_sicredi'] == 0]
    if len(apenas_razao) > 0:
        for _, row in apenas_razao.head(20).iterrows():
            print(f"  {row['historico_resumido']:<50} R$ {row['total_razao']:>15,.2f} ({row['qtd_razao']:.0f} transações)")
    else:
        print("  Nenhum histórico encontrado apenas no Razão")

def gerar_entradas_por_tipo_historico(df_sicredi, df_razao):
    """Gera um arquivo CSV separado para cada tipo de histórico com todos os registros"""
    print("\n" + "="*80)
    print("GERANDO ARQUIVOS POR TIPO DE HISTÓRICO")
    print("="*80)
    
    # Filtrar apenas entradas
    entradas_sicredi = df_sicredi[df_sicredi['tipo'] == 'ENTRADA'].copy()
    entradas_razao = df_razao[df_razao['tipo'] == 'ENTRADA'].copy()
    
    # Adicionar histórico resumido
    entradas_sicredi['historico_resumido'] = entradas_sicredi['historico'].apply(resumir_historico)
    entradas_razao['historico_resumido'] = entradas_razao['historico'].apply(resumir_historico)
    
    # Juntar todos os registros
    todos_registros = []
    
    # Adicionar entradas do Sicredi
    for _, row in entradas_sicredi.iterrows():
        todos_registros.append({
            'data': row['data'],
            'origem': 'SICREDI',
            'historico_original': row['historico'],
            'valor': row['valor']
        })
    
    # Adicionar entradas do Razão
    for _, row in entradas_razao.iterrows():
        todos_registros.append({
            'data': row['data'],
            'origem': 'RAZAO',
            'historico_original': row['historico'],
            'valor': row['valor']
        })
    
    # Criar DataFrame completo
    df_completo = pd.DataFrame(todos_registros)
    df_completo['historico_resumido'] = df_completo['historico_original'].apply(resumir_historico)
    
    # Função para formatar números no padrão brasileiro
    def formatar_br(valor):
        if pd.isna(valor) or valor == '':
            return ''
        try:
            valor_float = float(valor)
            valor_str = f"{valor_float:,.2f}"
            valor_str = valor_str.replace(',', 'TEMP').replace('.', ',').replace('TEMP', '.')
            return valor_str
        except:
            return str(valor)
    
    # Criar diretório para os arquivos
    POSTO_SAIDA.mkdir(parents=True, exist_ok=True)
    diretorio = str(POSTO_SAIDA / "entradas_por_historico")
    
    # Agrupar por histórico resumido e gerar um arquivo para cada
    historicos_unicos = df_completo['historico_resumido'].unique()
    arquivos_gerados = []
    
    for historico in historicos_unicos:
        # Filtrar registros deste histórico
        df_historico = df_completo[df_completo['historico_resumido'] == historico].copy()
        
        # Ordenar por data e origem
        df_historico = df_historico.sort_values(['data', 'origem'])
        
        # Formatar números
        df_historico_formatado = df_historico.copy()
        df_historico_formatado['valor'] = df_historico_formatado['valor'].apply(formatar_br)
        
        # Remover coluna historico_resumido (já está no nome do arquivo)
        df_historico_formatado = df_historico_formatado.drop('historico_resumido', axis=1)
        
        # Criar nome do arquivo (sanitizar para nome de arquivo válido)
        nome_arquivo = historico.replace('/', '_').replace('\\', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')
        nome_arquivo = nome_arquivo.strip()
        if not nome_arquivo:
            nome_arquivo = "SEM_HISTORICO"
        
        arquivo_saida = os.path.join(diretorio, f"{nome_arquivo}.csv")
        
        # Salvar em CSV com separador ";" e números no padrão brasileiro
        df_historico_formatado.to_csv(arquivo_saida, index=False, encoding='utf-8-sig', sep=';')
        
        arquivos_gerados.append({
            'historico': historico,
            'arquivo': arquivo_saida,
            'registros': len(df_historico_formatado),
            'total_sicredi': len(df_historico_formatado[df_historico_formatado['origem'] == 'SICREDI']),
            'total_razao': len(df_historico_formatado[df_historico_formatado['origem'] == 'RAZAO'])
        })
    
    # Mostrar resumo
    print(f"\nArquivos gerados no diretório: {diretorio}/")
    print(f"Total de tipos de histórico: {len(arquivos_gerados)}")
    print("\nArquivos criados:")
    for info in sorted(arquivos_gerados, key=lambda x: x['historico']):
        print(f"  {info['historico']:<50} -> {info['arquivo']}")
        print(f"    Registros: {info['registros']} (Sicredi: {info['total_sicredi']}, Razão: {info['total_razao']})")
    
    return arquivos_gerados

def main():
    from runtime import setup_workspace

    setup_workspace()
    POSTO_SAIDA.mkdir(parents=True, exist_ok=True)

    arquivo_ods = POSTO_ENTRADA / "sicredi-pilecco-ofx.ods"
    arquivo_xls = POSTO_ENTRADA / "Razão.xls"
    
    if not arquivo_ods.exists():
        print(f"Erro: Arquivo não encontrado: {arquivo_ods}")
        return

    if not arquivo_xls.exists():
        print(f"Erro: Arquivo não encontrado: {arquivo_xls}")
        return
    
    # Ler arquivos
    df_ods = ler_arquivo_ods(arquivo_ods)
    if df_ods is None:
        return
    
    df_xls = ler_arquivo_xls(arquivo_xls)
    if df_xls is None:
        return
    
    # Processar dados
    df_sicredi = processar_extrato_sicredi(df_ods)
    if df_sicredi is None or len(df_sicredi) == 0:
        print("Erro: Não foi possível processar extrato Sicredi")
        return
    
    df_razao = processar_razao(df_xls)
    if df_razao is None or len(df_razao) == 0:
        print("Erro: Não foi possível processar Razão")
        return
    
    # Comparar
    comparacao, sicredi_dia, razao_dia = comparar_por_dia(df_sicredi, df_razao)
    
    # Gerar relatório
    gerar_relatorio(comparacao, df_sicredi, df_razao)
    
    # Comparar entradas por histórico resumido
    comparar_entradas_por_historico(df_sicredi, df_razao)
    
    # Gerar arquivos separados por tipo de histórico
    gerar_entradas_por_tipo_historico(df_sicredi, df_razao)

if __name__ == "__main__":
    main()

