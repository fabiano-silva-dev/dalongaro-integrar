#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar consistência entre relatórios gerados e arquivo de resumo
"""

import pandas as pd
import re
from datetime import datetime

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

def extrair_dados_resumo(arquivo_csv):
    """
    Extrai dados do arquivo de resumo UsuárioTempo Gasto
    """
    print(f"Processando arquivo de resumo: {arquivo_csv}")
    
    # Tentar diferentes codificações
    codificacoes = ['utf-8', 'latin1', 'iso-8859-1', 'cp1252']
    df = None
    
    for codificacao in codificacoes:
        try:
            df = pd.read_csv(arquivo_csv, header=None, encoding=codificacao)
            print(f"Sucesso com codificação: {codificacao}")
            break
        except Exception as e:
            continue
    
    if df is None:
        print("Erro: Não foi possível ler o arquivo de resumo")
        return None
    
    dados_resumo = []
    usuario_atual = None
    
    for idx, row in df.iterrows():
        linha = ' '.join([str(cell) for cell in row if pd.notna(cell) and str(cell).strip()])
        
        if not linha.strip():
            continue
            
        # Pular cabeçalhos
        if any(termo in linha for termo in ['Relação de Usuários', 'Período:', 'Hora:', 'Página:']):
            continue
            
        # Pular cabeçalho de colunas
        if 'Sistema' in linha and 'Tempo Gasto' in linha:
            continue
            
        # Detectar usuário
        if 'Usuário:' in linha:
            match = re.search(r'Usuário:\s*([A-Z\s\.]+)', linha)
            if match:
                usuario_atual = match.group(1).strip()
            continue
            
        # Detectar total do usuário
        if 'Total do Usuário:' in linha:
            match = re.search(r'Total do Usuário:\s*(\d{2}:\d{2}:\d{2})', linha)
            if match and usuario_atual:
                tempo_total = match.group(1)
                dados_resumo.append({
                    'usuario': usuario_atual,
                    'tempo_total': tempo_total,
                    'tempo_minutos': converter_tempo_para_minutos(tempo_total)
                })
            continue
            
        # Detectar linha de sistema e tempo
        if usuario_atual and not 'Usuário:' in linha and not 'Total do Usuário:' in linha:
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
                    dados_resumo.append({
                        'usuario': usuario_atual,
                        'sistema': sistema,
                        'tempo': tempo,
                        'tempo_minutos': converter_tempo_para_minutos(tempo)
                    })
    
    return dados_resumo

def carregar_dados_relatorios():
    """
    Carrega dados dos relatórios gerados
    """
    try:
        # Dados de atividades
        df_atividades = pd.read_csv("dados_atividades_estruturados.csv")
        
        # Relatório de eficiência por usuário
        df_eficiencia = pd.read_csv("produtividade/relatorios/avancados/eficiencia_por_usuario.csv")
        
        return df_atividades, df_eficiencia
        
    except Exception as e:
        print(f"Erro ao carregar relatórios: {e}")
        return None, None

def comparar_dados(dados_resumo, df_atividades, df_eficiencia):
    """
    Compara dados do resumo com relatórios gerados
    """
    print("\n" + "="*80)
    print("VERIFICAÇÃO DE CONSISTÊNCIA DOS DADOS")
    print("="*80)
    
    if dados_resumo is None or df_atividades is None or df_eficiencia is None:
        print("❌ Dados insuficientes para comparação")
        return
    
    # 1. Comparar totais por usuário
    print("\n📊 COMPARAÇÃO DE TOTAIS POR USUÁRIO:")
    print("-" * 60)
    print(f"{'Usuário':<15} {'Resumo':<12} {'Relatório':<12} {'Diferença':<12} {'Status':<10}")
    print("-" * 60)
    
    # Agrupar dados de resumo por usuário
    resumo_por_usuario = {}
    for item in dados_resumo:
        if 'tempo_total' in item:
            usuario = item['usuario']
            if usuario not in resumo_por_usuario:
                resumo_por_usuario[usuario] = item['tempo_minutos']
    
    # Comparar com relatório
    for _, row in df_eficiencia.iterrows():
        usuario = row['usuario']
        tempo_relatorio = row['Tempo_Total_min']
        
        if usuario in resumo_por_usuario:
            tempo_resumo = resumo_por_usuario[usuario]
            diferenca = abs(tempo_relatorio - tempo_resumo)
            
            if diferenca < 1:  # Diferença menor que 1 minuto
                status = "✅ OK"
            elif diferenca < 5:  # Diferença menor que 5 minutos
                status = "⚠️  PEQ"
            else:
                status = "❌ DIF"
            
            print(f"{usuario:<15} {tempo_resumo:>8.1f}min {tempo_relatorio:>8.1f}min {diferenca:>8.1f}min {status:<10}")
        else:
            print(f"{usuario:<15} {'N/A':<12} {tempo_relatorio:>8.1f}min {'N/A':<12} {'❓'}")
    
    # 2. Comparar sistemas por usuário
    print(f"\n🖥️  COMPARAÇÃO DE SISTEMAS POR USUÁRIO:")
    print("-" * 60)
    
    # Agrupar dados de resumo por usuário e sistema
    resumo_sistema_usuario = {}
    for item in dados_resumo:
        if 'sistema' in item:
            usuario = item['usuario']
            sistema = item['sistema']
            tempo = item['tempo_minutos']
            
            if usuario not in resumo_sistema_usuario:
                resumo_sistema_usuario[usuario] = {}
            
            if sistema not in resumo_sistema_usuario[usuario]:
                resumo_sistema_usuario[usuario][sistema] = 0
            
            resumo_sistema_usuario[usuario][sistema] += tempo
    
    # Comparar com dados de atividades
    for usuario in resumo_sistema_usuario:
        print(f"\nUsuário: {usuario}")
        for sistema, tempo_resumo in resumo_sistema_usuario[usuario].items():
            # Buscar tempo no relatório de atividades
            tempo_atividades = df_atividades[
                (df_atividades['usuario'] == usuario) & 
                (df_atividades['sistema'] == sistema)
            ]['tempo_gasto'].apply(converter_tempo_para_minutos).sum()
            
            diferenca = abs(tempo_resumo - tempo_atividades)
            
            if diferenca < 1:
                status = "✅"
            elif diferenca < 5:
                status = "⚠️"
            else:
                status = "❌"
            
            print(f"  {sistema:<15}: {tempo_resumo:>6.1f}min vs {tempo_atividades:>6.1f}min (dif: {diferenca:>5.1f}min) {status}")
    
    # 3. Resumo de consistência
    print(f"\n📋 RESUMO DE CONSISTÊNCIA:")
    print("-" * 60)
    
    total_usuarios = len(resumo_por_usuario)
    usuarios_consistentes = 0
    usuarios_pequena_diferenca = 0
    usuarios_diferenca_significativa = 0
    
    for usuario, tempo_resumo in resumo_por_usuario.items():
        if usuario in df_eficiencia['usuario'].values:
            tempo_relatorio = df_eficiencia[df_eficiencia['usuario'] == usuario]['Tempo_Total_min'].iloc[0]
            diferenca = abs(tempo_resumo - tempo_relatorio)
            
            if diferenca < 1:
                usuarios_consistentes += 1
            elif diferenca < 5:
                usuarios_pequena_diferenca += 1
            else:
                usuarios_diferenca_significativa += 1
    
    print(f"✅ Usuários com dados consistentes: {usuarios_consistentes}/{total_usuarios}")
    print(f"⚠️  Usuários com pequena diferença: {usuarios_pequena_diferenca}/{total_usuarios}")
    print(f"❌ Usuários com diferença significativa: {usuarios_diferenca_significativa}/{total_usuarios}")
    
    # 4. Análise de sistemas
    print(f"\n🔍 ANÁLISE DE SISTEMAS:")
    print("-" * 60)
    
    sistemas_resumo = set()
    sistemas_relatorio = set()
    
    for item in dados_resumo:
        if 'sistema' in item:
            sistemas_resumo.add(item['sistema'])
    
    sistemas_relatorio = set(df_atividades['sistema'].unique())
    
    print(f"Sistemas no resumo: {sorted(sistemas_resumo)}")
    print(f"Sistemas no relatório: {sorted(sistemas_relatorio)}")
    
    sistemas_faltando = sistemas_resumo - sistemas_relatorio
    sistemas_novos = sistemas_relatorio - sistemas_resumo
    
    if sistemas_faltando:
        print(f"⚠️  Sistemas no resumo mas não no relatório: {sorted(sistemas_faltando)}")
    
    if sistemas_novos:
        print(f"ℹ️  Sistemas no relatório mas não no resumo: {sorted(sistemas_novos)}")

def main():
    """
    Função principal
    """
    print("🔍 VERIFICANDO CONSISTÊNCIA ENTRE RELATÓRIOS E ARQUIVO DE RESUMO")
    
    # 1. Extrair dados do arquivo de resumo
    dados_resumo = extrair_dados_resumo("UsuárioTempo Gasto.csv")
    
    if dados_resumo is None:
        print("❌ Falha na extração dos dados de resumo")
        return
    
    print(f"✅ Dados de resumo extraídos: {len(dados_resumo)} registros")
    
    # 2. Carregar dados dos relatórios
    df_atividades, df_eficiencia = carregar_dados_relatorios()
    
    if df_atividades is None or df_eficiencia is None:
        print("❌ Falha no carregamento dos relatórios")
        return
    
    print(f"✅ Relatórios carregados: {len(df_atividades)} atividades, {len(df_eficiencia)} usuários")
    
    # 3. Comparar dados
    comparar_dados(dados_resumo, df_atividades, df_eficiencia)
    
    print(f"\n✅ Verificação de consistência concluída!")

if __name__ == "__main__":
    main()











