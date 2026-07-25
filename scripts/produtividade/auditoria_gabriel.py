#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para auditar especificamente o usuário GABRIEL e seus clientes
"""

import pandas as pd
import re
from datetime import datetime
import os

def auditar_gabriel_detalhadamente():
    """
    Audita especificamente o usuário GABRIEL e seus clientes
    """
    print("🔍 AUDITORIA ESPECÍFICA - USUÁRIO GABRIEL")
    print("="*80)
    print(f"Data da auditoria: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("="*80)
    
    # 1. VERIFICAR DADOS NO ARQUIVO DE RESUMO
    print("\n📋 1. DADOS DE GABRIEL NO ARQUIVO DE RESUMO")
    print("-" * 60)
    
    dados_resumo_gabriel = extrair_dados_gabriel_resumo("UsuárioTempo Gasto.csv")
    
    if dados_resumo_gabriel:
        print("✅ Dados de GABRIEL encontrados no arquivo de resumo:")
        for sistema, tempo in dados_resumo_gabriel.items():
            print(f"  • {sistema}: {tempo}")
        
        tempo_total_resumo = sum(dados_resumo_gabriel.values())
        print(f"\n📊 Total no resumo: {tempo_total_resumo} minutos ({tempo_total_resumo/60:.1f} horas)")
    else:
        print("❌ Nenhum dado de GABRIEL encontrado no arquivo de resumo")
    
    # 2. VERIFICAR DADOS NOS RELATÓRIOS GERADOS
    print("\n📊 2. DADOS DE GABRIEL NOS RELATÓRIOS GERADOS")
    print("-" * 60)
    
    dados_relatorios_gabriel = verificar_gabriel_relatorios()
    
    if dados_relatorios_gabriel:
        print("✅ Dados de GABRIEL encontrados nos relatórios:")
        for sistema, tempo in dados_relatorios_gabriel.items():
            print(f"  • {sistema}: {tempo}")
        
        tempo_total_relatorios = sum(dados_relatorios_gabriel.values())
        print(f"\n📊 Total nos relatórios: {tempo_total_relatorios} minutos ({tempo_total_relatorios/60:.1f} horas)")
    else:
        print("❌ Nenhum dado de GABRIEL encontrado nos relatórios")
    
    # 3. COMPARAR DADOS
    print("\n⚖️ 3. COMPARAÇÃO DOS DADOS")
    print("-" * 60)
    
    if dados_resumo_gabriel and dados_relatorios_gabriel:
        comparar_dados_gabriel(dados_resumo_gabriel, dados_relatorios_gabriel)
    elif dados_resumo_gabriel and not dados_relatorios_gabriel:
        print("🚨 PROBLEMA CRÍTICO: GABRIEL está no resumo mas NÃO nos relatórios!")
        print("   Isso explica a discrepância encontrada.")
    else:
        print("⚠️  GABRIEL não encontrado em nenhum dos arquivos")
    
    # 4. VERIFICAR CLIENTES DE GABRIEL
    print("\n👥 4. CLIENTES DE GABRIEL")
    print("-" * 60)
    
    clientes_gabriel = buscar_clientes_gabriel()
    
    if clientes_gabriel:
        print("✅ Clientes encontrados para GABRIEL:")
        for cliente in clientes_gabriel:
            print(f"  • {cliente}")
    else:
        print("❌ Nenhum cliente encontrado para GABRIEL")
    
    # 5. ANÁLISE DE CAUSA RAIZ
    print("\n🔍 5. ANÁLISE DE CAUSA RAIZ")
    print("-" * 60)
    
    analisar_causa_raiz_gabriel(dados_resumo_gabriel, dados_relatorios_gabriel)
    
    # 6. RECOMENDAÇÕES ESPECÍFICAS
    print("\n💡 6. RECOMENDAÇÕES ESPECÍFICAS PARA GABRIEL")
    print("-" * 60)
    
    gerar_recomendacoes_gabriel(dados_resumo_gabriel, dados_relatorios_gabriel)

def extrair_dados_gabriel_resumo(arquivo_csv):
    """
    Extrai dados específicos de GABRIEL do arquivo de resumo
    """
    try:
        # Tentar diferentes codificações
        codificacoes = ['utf-8', 'latin1', 'iso-8859-1', 'cp1252']
        df = None
        
        for codificacao in codificacoes:
            try:
                df = pd.read_csv(arquivo_csv, header=None, encoding=codificacao)
                break
            except:
                continue
        
        if df is None:
            return None
        
        dados_gabriel = {}
        usuario_atual = None
        
        for idx, row in df.iterrows():
            linha = ' '.join([str(cell) for cell in row if pd.notna(cell) and str(cell).strip()])
            
            if not linha.strip():
                continue
            
            # Detectar usuário
            if 'Usuário:' in linha:
                match = re.search(r'Usuário:\s*([A-Z\s\.]+)', linha)
                if match:
                    usuario_atual = match.group(1).strip()
                continue
            
            # Se for GABRIEL, capturar sistemas e tempos
            if usuario_atual == 'GABRIEL':
                # Procurar por sistemas conhecidos
                sistemas_conhecidos = ['Contabilidade', 'Escrita', 'Folha', 'Patrimonio', 'Lalur', 'Atualizar', 'Honorários']
                sistema = None
                
                for sis in sistemas_conhecidos:
                    if sis in linha:
                        sistema = sis
                        break
                
                if sistema:
                    # Procurar por tempo
                    tempo_match = re.search(r'(\d{2}:\d{2}:\d{2})', linha)
                    if tempo_match:
                        tempo = tempo_match.group(1)
                        # Converter para minutos
                        minutos = converter_tempo_para_minutos(tempo)
                        dados_gabriel[sistema] = minutos
        
        return dados_gabriel
        
    except Exception as e:
        print(f"Erro ao extrair dados de GABRIEL: {e}")
        return None

def verificar_gabriel_relatorios():
    """
    Verifica se GABRIEL aparece nos relatórios gerados
    """
    try:
        # Verificar dados de atividades
        if os.path.exists("dados_atividades_estruturados.csv"):
            df_atividades = pd.read_csv("dados_atividades_estruturados.csv")
            
            # Filtrar atividades de GABRIEL
            gabriel_atividades = df_atividades[df_atividades['usuario'] == 'GABRIEL']
            
            if not gabriel_atividades.empty:
                dados_gabriel = {}
                for sistema in gabriel_atividades['sistema'].unique():
                    tempo_total = gabriel_atividades[gabriel_atividades['sistema'] == sistema]['tempo_gasto'].apply(converter_tempo_para_minutos).sum()
                    dados_gabriel[sistema] = tempo_total
                
                return dados_gabriel
        
        return None
        
    except Exception as e:
        print(f"Erro ao verificar relatórios: {e}")
        return None

def buscar_clientes_gabriel():
    """
    Busca clientes específicos de GABRIEL
    """
    try:
        if os.path.exists("dados_atividades_estruturados.csv"):
            df_atividades = pd.read_csv("dados_atividades_estruturados.csv")
            
            # Filtrar atividades de GABRIEL
            gabriel_atividades = df_atividades[df_atividades['usuario'] == 'GABRIEL']
            
            if not gabriel_atividades.empty:
                clientes = gabriel_atividades[['codigo_cliente', 'nome_cliente']].drop_duplicates()
                return [f"{row['codigo_cliente']} - {row['nome_cliente']}" for _, row in clientes.iterrows()]
        
        return []
        
    except Exception as e:
        print(f"Erro ao buscar clientes: {e}")
        return []

def comparar_dados_gabriel(dados_resumo, dados_relatorios):
    """
    Compara dados de GABRIEL entre resumo e relatórios
    """
    print("📊 COMPARAÇÃO DETALHADA:")
    
    sistemas_todos = set(dados_resumo.keys()) | set(dados_relatorios.keys())
    
    for sistema in sorted(sistemas_todos):
        tempo_resumo = dados_resumo.get(sistema, 0)
        tempo_relatorios = dados_relatorios.get(sistema, 0)
        
        if tempo_resumo > 0 and tempo_relatorios > 0:
            if abs(tempo_resumo - tempo_relatorios) < 1:
                status = "✅ OK"
            else:
                status = "⚠️  DIFERENÇA"
            print(f"  • {sistema}: {tempo_resumo:>6.1f}min vs {tempo_relatorios:>6.1f}min {status}")
        elif tempo_resumo > 0:
            print(f"  • {sistema}: {tempo_resumo:>6.1f}min vs {'N/A':>6} ❌ FALTANDO NOS RELATÓRIOS")
        else:
            print(f"  • {sistema}: {'N/A':>6} vs {tempo_relatorios:>6.1f}min ❌ FALTANDO NO RESUMO")

def analisar_causa_raiz_gabriel(dados_resumo, dados_relatorios):
    """
    Analisa a causa raiz da discrepância de GABRIEL
    """
    print("🔍 ANÁLISE DE CAUSA RAIZ:")
    
    if dados_resumo and not dados_relatorios:
        print("  • GABRIEL está no arquivo de resumo mas NÃO nos relatórios")
        print("  • Possíveis causas:")
        print("    1. Atividades apenas nos dias 30 e 31 de agosto")
        print("    2. Dados em arquivo diferente do ClienteTempo Gasto.xls")
        print("    3. Problema na extração dos dados")
        print("    4. Usuário não identificado pelo sistema de extração")
    
    elif dados_resumo and dados_relatorios:
        print("  • GABRIEL aparece em ambos os arquivos")
        print("  • Verificar diferenças específicas por sistema")
    
    else:
        print("  • GABRIEL não encontrado em nenhum arquivo")
        print("  • Verificar se o nome está correto")

def gerar_recomendacoes_gabriel(dados_resumo, dados_relatorios):
    """
    Gera recomendações específicas para resolver problemas de GABRIEL
    """
    print("💡 RECOMENDAÇÕES:")
    
    if dados_resumo and not dados_relatorios:
        print("  1. 🔍 Verificar se GABRIEL trabalhou nos dias 30 e 31 de agosto")
        print("  2. 📁 Procurar dados de GABRIEL em outros arquivos")
        print("  3. 🔧 Atualizar sistema de extração para incluir GABRIEL")
        print("  4. 📊 Verificar se há padrão específico nas atividades de GABRIEL")
        print("  5. 🧪 Testar extração com dados completos")
    
    elif dados_resumo and dados_relatorios:
        print("  1. ✅ Dados de GABRIEL estão sendo capturados")
        print("  2. 📊 Verificar diferenças específicas por sistema")
        print("  3. 🔧 Ajustar sistema se necessário")
    
    else:
        print("  1. ❓ Investigar por que GABRIEL não aparece em nenhum arquivo")
        print("  2. 🔍 Verificar se o nome está correto")
        print("  3. 📁 Procurar em outros arquivos de produtividade")

def converter_tempo_para_minutos(tempo_str):
    """
    Converte tempo no formato HH:MM:SS para minutos
    """
    try:
        if pd.isna(tempo_str) or tempo_str == '':
            return 0
        
        partes = str(tempo_str).split(':')
        if len(partes) == 3:
            horas = int(partes[0])
            minutos = int(partes[1])
            segundos = int(partes[2])
            return horas * 60 + minutos + segundos / 60
        elif len(partes) == 2:
            minutos = int(partes[0])
            segundos = int(partes[1])
            return minutos + segundos / 60
        else:
            return 0
    except:
        return 0

def main():
    """
    Função principal
    """
    print("🚀 INICIANDO AUDITORIA ESPECÍFICA DO USUÁRIO GABRIEL")
    
    # Executar auditoria
    auditar_gabriel_detalhadamente()
    
    print("\n" + "="*80)
    print("AUDITORIA DE GABRIEL CONCLUÍDA")
    print("="*80)

if __name__ == "__main__":
    main()










