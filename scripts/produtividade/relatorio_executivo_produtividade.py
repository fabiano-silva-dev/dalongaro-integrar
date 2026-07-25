#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para gerar relatório executivo consolidado de produtividade
"""

import pandas as pd
import os
from datetime import datetime

def gerar_relatorio_executivo():
    """
    Gera relatório executivo consolidado
    """
    print("="*100)
    print("RELATÓRIO EXECUTIVO DE PRODUTIVIDADE")
    print("="*100)
    print(f"Data de geração: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("="*100)
    
    # Carregar dados principais
    try:
        df_atividades = pd.read_csv("dados_atividades_estruturados.csv")
        print(f"\n📊 DADOS GERAIS:")
        print(f"  • Total de atividades registradas: {len(df_atividades):,}")
        print(f"  • Período analisado: {df_atividades['data'].min()} a {df_atividades['data'].max()}")
        print(f"  • Total de clientes atendidos: {df_atividades['codigo_cliente'].nunique():,}")
        print(f"  • Total de usuários ativos: {df_atividades['usuario'].nunique():,}")
        print(f"  • Total de sistemas utilizados: {df_atividades['sistema'].nunique():,}")
    except Exception as e:
        print(f"Erro ao carregar dados principais: {e}")
        return
    
    # Carregar relatórios específicos
    try:
        # Relatório por sistema
        df_sistema = pd.read_csv("produtividade/relatorios/basicos/relatorio_por_sistema.csv")
        print(f"\n🖥️  ANÁLISE POR SISTEMA:")
        for _, row in df_sistema.iterrows():
            sistema = row['Sistema']
            clientes = row['Clientes Únicos']
            usuarios = row['Usuários Únicos']
            atividades = row['Total Atividades']
            print(f"  • {sistema:<15}: {atividades:>3} atividades, {clientes:>3} clientes, {usuarios:>2} usuários")
        
        # Relatório por usuário
        df_usuario = pd.read_csv("produtividade/relatorios/basicos/relatorio_por_usuario.csv")
        print(f"\n👥 ANÁLISE POR USUÁRIO:")
        for _, row in df_usuario.iterrows():
            usuario = row['Usuário']
            clientes = row['Clientes Únicos']
            sistemas = row['Sistemas Únicos']
            atividades = row['Total Atividades']
            print(f"  • {usuario:<10}: {atividades:>3} atividades, {clientes:>3} clientes, {sistemas:>2} sistemas")
        
        # Relatório de eficiência
        df_eficiencia = pd.read_csv("produtividade/relatorios/avancados/eficiencia_por_usuario.csv")
        print(f"\n⚡ EFICIÊNCIA OPERACIONAL:")
        print(f"  • Usuário mais eficiente: {df_eficiencia.loc[df_eficiencia['Tempo_Medio_min'].idxmin(), 'usuario']}")
        print(f"  • Usuário com mais atividades: {df_eficiencia.loc[df_eficiencia['Total_Atividades'].idxmax(), 'usuario']}")
        print(f"  • Usuário com maior tempo total: {df_eficiencia.loc[df_eficiencia['Tempo_Total_min'].idxmax(), 'usuario']}")
        
        # Top clientes
        df_produtividade = pd.read_csv("produtividade/relatorios/avancados/produtividade_por_cliente.csv")
        print(f"\n🏆 TOP 5 CLIENTES POR PRODUTIVIDADE:")
        top_clientes = df_produtividade.nlargest(5, 'Tempo_Total_min')
        for idx, row in top_clientes.iterrows():
            codigo = row['codigo_cliente']
            nome = row['nome_cliente'][:40] + "..." if len(row['nome_cliente']) > 40 else row['nome_cliente']
            tempo = row['Tempo_Total_min']
            horas = int(tempo // 60)
            minutos = int(tempo % 60)
            print(f"  • {codigo:>3} - {nome:<40} {horas:>2}h {minutos:>2}min")
            
    except Exception as e:
        print(f"Erro ao carregar relatórios específicos: {e}")
    
    # Análise de tendências
    try:
        df_temporal = pd.read_csv("produtividade/relatorios/avancados/analise_temporal.csv")
        print(f"\n📈 ANÁLISE TEMPORAL:")
        print(f"  • Dia com maior volume: {df_temporal.loc[df_temporal['Tempo_Total_min'].idxmax(), 'data']}")
        print(f"  • Dia com menor volume: {df_temporal.loc[df_temporal['Tempo_Total_min'].idxmin(), 'data']}")
        print(f"  • Média diária de tempo: {df_temporal['Tempo_Total_min'].mean():.1f} minutos")
        
    except Exception as e:
        print(f"Erro ao carregar análise temporal: {e}")
    
    # Recomendações
    print(f"\n💡 RECOMENDAÇÕES:")
    print(f"  • Focar em treinamento para usuários com menor eficiência")
    print(f"  • Analisar sistemas com maior tempo médio por atividade")
    print(f"  • Identificar padrões de produtividade por período do mês")
    print(f"  • Considerar redistribuição de carga de trabalho entre usuários")
    
    print(f"\n" + "="*100)
    print("RELATÓRIO CONCLUÍDO")
    print("="*100)

def salvar_relatorio_executivo():
    """
    Salva o relatório executivo em arquivo de texto
    """
    # Redirecionar saída para arquivo
    import sys
    from io import StringIO
    
    # Capturar saída
    old_stdout = sys.stdout
    sys.stdout = StringIO()
    
    # Gerar relatório
    gerar_relatorio_executivo()
    
    # Capturar conteúdo
    output = sys.stdout.getvalue()
    sys.stdout = old_stdout
    
    # Salvar em arquivo
    with open("relatorio_executivo_produtividade.txt", "w", encoding="utf-8") as f:
        f.write(output)
    
    print("Relatório executivo salvo em: relatorio_executivo_produtividade.txt")

def main():
    """
    Função principal
    """
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from runtime import setup_workspace
    setup_workspace()

    print("Gerando relatório executivo de produtividade...")
    
    # Gerar relatório no console
    gerar_relatorio_executivo()
    
    # Salvar relatório em arquivo
    salvar_relatorio_executivo()
    
    print(f"\nProcessamento concluído!")

if __name__ == "__main__":
    main()











