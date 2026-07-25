#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para gerar relatórios avançados e análises dos dados de produtividade
"""

import pandas as pd
import numpy as np
from datetime import datetime
import os

def carregar_dados():
    """
    Carrega os dados estruturados
    """
    try:
        df_atividades = pd.read_csv("dados_atividades_estruturados.csv")
        print(f"Dados carregados: {df_atividades.shape}")
        return df_atividades
    except Exception as e:
        print(f"Erro ao carregar dados: {e}")
        return None

def converter_tempo_para_minutos(tempo_str):
    """
    Converte tempo no formato HH:MM:SS para minutos
    """
    try:
        partes = tempo_str.split(':')
        horas = int(partes[0])
        minutos = int(partes[1])
        segundos = int(partes[2])
        return horas * 60 + minutos + segundos / 60
    except:
        return 0

def gerar_relatorio_produtividade_detalhado(df):
    """
    Gera relatório detalhado de produtividade
    """
    print("\n" + "="*80)
    print("RELATÓRIO DETALHADO DE PRODUTIVIDADE")
    print("="*80)
    
    # Converter tempo para minutos
    df['tempo_minutos'] = df['tempo_gasto'].apply(converter_tempo_para_minutos)
    
    # 1. Resumo geral
    print(f"\nRESUMO GERAL:")
    print(f"  - Total de atividades: {len(df)}")
    print(f"  - Total de clientes únicos: {df['codigo_cliente'].nunique()}")
    print(f"  - Total de usuários únicos: {df['usuario'].nunique()}")
    print(f"  - Total de sistemas únicos: {df['sistema'].nunique()}")
    print(f"  - Período: {df['data'].min()} a {df['data'].max()}")
    
    # 2. Análise por sistema
    print(f"\nANÁLISE POR SISTEMA:")
    analise_sistema = df.groupby('sistema').agg({
        'tempo_minutos': ['sum', 'mean', 'count'],
        'codigo_cliente': 'nunique',
        'usuario': 'nunique'
    }).round(2)
    
    analise_sistema.columns = ['Tempo Total (min)', 'Tempo Médio (min)', 'Total Atividades', 'Clientes Únicos', 'Usuários Únicos']
    print(analise_sistema)
    
    # 3. Análise por usuário
    print(f"\nANÁLISE POR USUÁRIO:")
    analise_usuario = df.groupby('usuario').agg({
        'tempo_minutos': ['sum', 'mean', 'count'],
        'codigo_cliente': 'nunique',
        'sistema': 'nunique'
    }).round(2)
    
    analise_usuario.columns = ['Tempo Total (min)', 'Tempo Médio (min)', 'Total Atividades', 'Clientes Únicos', 'Sistemas Únicos']
    print(analise_usuario)
    
    # 4. Top 10 clientes por tempo total
    print(f"\nTOP 10 CLIENTES POR TEMPO TOTAL:")
    top_clientes = df.groupby(['codigo_cliente', 'nome_cliente'])['tempo_minutos'].sum().sort_values(ascending=False).head(10)
    for (codigo, nome), tempo in top_clientes.items():
        horas = int(tempo // 60)
        minutos = int(tempo % 60)
        print(f"  {codigo:>3} - {nome:<50} {horas:>2}h {minutos:>2}min")
    
    # 5. Análise temporal
    print(f"\nANÁLISE TEMPORAL:")
    df['data'] = pd.to_datetime(df['data'], format='%d/%m/%Y')
    analise_temporal = df.groupby('data').agg({
        'tempo_minutos': 'sum',
        'codigo_cliente': 'nunique',
        'usuario': 'nunique'
    }).round(2)
    
    analise_temporal.columns = ['Tempo Total (min)', 'Clientes Únicos', 'Usuários Únicos']
    print(analise_temporal)
    
    return df

def gerar_relatorio_efficiency(df):
    """
    Gera relatório de eficiência
    """
    print("\n" + "="*80)
    print("RELATÓRIO DE EFICIÊNCIA")
    print("="*80)
    
    # Eficiência por usuário (tempo médio por atividade)
    print(f"\nEFICIÊNCIA POR USUÁRIO (tempo médio por atividade):")
    eficiencia_usuario = df.groupby('usuario').agg({
        'tempo_minutos': 'mean',
        'tempo_gasto': 'count'
    }).round(2)
    
    eficiencia_usuario.columns = ['Tempo Médio (min)', 'Total Atividades']
    eficiencia_usuario = eficiencia_usuario.sort_values('Tempo Médio (min)')
    print(eficiencia_usuario)
    
    # Eficiência por sistema
    print(f"\nEFICIÊNCIA POR SISTEMA (tempo médio por atividade):")
    eficiencia_sistema = df.groupby('sistema').agg({
        'tempo_minutos': 'mean',
        'tempo_gasto': 'count'
    }).round(2)
    
    eficiencia_sistema.columns = ['Tempo Médio (min)', 'Total Atividades']
    eficiencia_sistema = eficiencia_sistema.sort_values('Tempo Médio (min)')
    print(eficiencia_sistema)
    
    # Usuários mais produtivos (mais atividades em menos tempo)
    print(f"\nUSUÁRIOS MAIS PRODUTIVOS (atividades por hora):")
    df['atividades_por_hora'] = df.groupby('usuario')['tempo_gasto'].transform('count') / (df.groupby('usuario')['tempo_minutos'].transform('sum') / 60)
    produtividade_usuario = df.groupby('usuario').agg({
        'atividades_por_hora': 'first',
        'tempo_minutos': 'sum',
        'tempo_gasto': 'count'
    }).round(2)
    
    produtividade_usuario.columns = ['Atividades/Hora', 'Tempo Total (min)', 'Total Atividades']
    produtividade_usuario = produtividade_usuario.sort_values('Atividades/Hora', ascending=False)
    print(produtividade_usuario)

def salvar_relatorios_avancados(df):
    """
    Salva relatórios avançados em CSV
    """
    diretorio = "produtividade/relatorios/avancados"
    os.makedirs(diretorio, exist_ok=True)
    
    # Converter tempo para minutos
    df['tempo_minutos'] = df['tempo_gasto'].apply(converter_tempo_para_minutos)
    
    # 1. Relatório de eficiência por usuário
    eficiencia_usuario = df.groupby('usuario').agg({
        'tempo_minutos': ['sum', 'mean', 'count'],
        'codigo_cliente': 'nunique',
        'sistema': 'nunique'
    }).round(2)
    
    eficiencia_usuario.columns = ['Tempo_Total_min', 'Tempo_Medio_min', 'Total_Atividades', 'Clientes_Unicos', 'Sistemas_Unicos']
    eficiencia_usuario.to_csv(f"{diretorio}/eficiencia_por_usuario.csv", encoding='utf-8-sig')
    
    # 2. Relatório de eficiência por sistema
    eficiencia_sistema = df.groupby('sistema').agg({
        'tempo_minutos': ['sum', 'mean', 'count'],
        'codigo_cliente': 'nunique',
        'usuario': 'nunique'
    }).round(2)
    
    eficiencia_sistema.columns = ['Tempo_Total_min', 'Tempo_Medio_min', 'Total_Atividades', 'Clientes_Unicos', 'Usuarios_Unicos']
    eficiencia_sistema.to_csv(f"{diretorio}/eficiencia_por_sistema.csv", encoding='utf-8-sig')
    
    # 3. Relatório de produtividade por cliente
    produtividade_cliente = df.groupby(['codigo_cliente', 'nome_cliente']).agg({
        'tempo_minutos': ['sum', 'mean', 'count'],
        'sistema': 'nunique',
        'usuario': 'nunique'
    }).round(2)
    
    produtividade_cliente.columns = ['Tempo_Total_min', 'Tempo_Medio_min', 'Total_Atividades', 'Sistemas_Unicos', 'Usuarios_Unicos']
    produtividade_cliente.to_csv(f"{diretorio}/produtividade_por_cliente.csv", encoding='utf-8-sig')
    
    # 4. Relatório temporal detalhado
    df['data'] = pd.to_datetime(df['data'], format='%d/%m/%Y')
    analise_temporal = df.groupby('data').agg({
        'tempo_minutos': ['sum', 'mean', 'count'],
        'codigo_cliente': 'nunique',
        'usuario': 'nunique',
        'sistema': 'nunique'
    }).round(2)
    
    analise_temporal.columns = ['Tempo_Total_min', 'Tempo_Medio_min', 'Total_Atividades', 'Clientes_Unicos', 'Usuarios_Unicos', 'Sistemas_Unicos']
    analise_temporal.to_csv(f"{diretorio}/analise_temporal.csv", encoding='utf-8-sig')
    
    print(f"\nRelatórios avançados salvos em: {diretorio}/")

def main():
    """
    Função principal
    """
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from runtime import setup_workspace
    setup_workspace()

    print("Gerando relatórios avançados de produtividade...")
    
    # Carregar dados
    df = carregar_dados()
    if df is None:
        return
    
    # Gerar relatório detalhado
    df = gerar_relatorio_produtividade_detalhado(df)
    
    # Gerar relatório de eficiência
    gerar_relatorio_efficiency(df)
    
    # Salvar relatórios avançados
    salvar_relatorios_avancados(df)
    
    print(f"\nProcessamento concluído!")

if __name__ == "__main__":
    main()
