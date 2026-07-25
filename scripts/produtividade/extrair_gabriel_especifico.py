#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script específico para extrair dados de GABRIEL e identificar o problema
"""

import pandas as pd
import re
from datetime import datetime

def extrair_gabriel_especifico():
    """
    Extrai especificamente os dados de GABRIEL para identificar o problema
    """
    print("🔍 EXTRAÇÃO ESPECÍFICA - USUÁRIO GABRIEL")
    print("="*80)
    
    # 1. VERIFICAR ARQUIVO ORIGINAL
    print("\n📁 1. VERIFICANDO ARQUIVO ORIGINAL")
    print("-" * 60)
    
    try:
        # Tentar diferentes codificações
        codificacoes = ['utf-8', 'latin1', 'iso-8859-1', 'cp1252']
        df = None
        
        arquivo_csv = "produtividade/ClienteTempo Gasto.csv"
        
        for codificacao in codificacoes:
            try:
                df = pd.read_csv(arquivo_csv, header=None, encoding=codificacao)
                print(f"✅ Arquivo lido com codificação: {codificacao}")
                break
            except:
                continue
        
        if df is None:
            print("❌ Não foi possível ler o arquivo")
            return
        
        print(f"📊 Forma do arquivo: {df.shape}")
        
        # 2. PROCURAR GABRIEL NO ARQUIVO ORIGINAL
        print("\n🔍 2. PROCURANDO GABRIEL NO ARQUIVO ORIGINAL")
        print("-" * 60)
        
        gabriel_encontrado = 0
        atividades_gabriel = []
        
        for idx, row in df.iterrows():
            linha = ' '.join([str(cell) for cell in row if pd.notna(cell) and str(cell).strip()])
            
            if 'GABRIEL' in linha.upper():
                gabriel_encontrado += 1
                
                # Extrair informações da linha
                data_match = re.search(r'\d{2}/\d{2}/\d{4}', linha)
                tempo_match = re.search(r'\d{2}:\d{2}:\d{2}', linha)
                
                # Identificar sistema
                sistemas = ['Contabilidade', 'Escrita', 'Folha', 'Patrimonio', 'Lalur', 'Atualizar', 'Honorários']
                sistema = None
                for sis in sistemas:
                    if sis in linha:
                        sistema = sis
                        break
                
                if data_match and tempo_match and sistema:
                    atividades_gabriel.append({
                        'linha': idx + 1,
                        'sistema': sistema,
                        'data': data_match.group(),
                        'tempo': tempo_match.group(),
                        'conteudo': linha[:100] + "..." if len(linha) > 100 else linha
                    })
        
        print(f"✅ GABRIEL encontrado {gabriel_encontrado} vezes no arquivo")
        
        # 3. ANALISAR ATIVIDADES DE GABRIEL
        print("\n📊 3. ANÁLISE DAS ATIVIDADES DE GABRIEL")
        print("-" * 60)
        
        if atividades_gabriel:
            print(f"📋 Total de atividades estruturadas: {len(atividades_gabriel)}")
            
            # Agrupar por sistema
            sistemas_gabriel = {}
            datas_gabriel = set()
            
            for atividade in atividades_gabriel:
                sistema = atividade['sistema']
                tempo = atividade['tempo']
                data = atividade['data']
                
                # Converter tempo para minutos
                minutos = converter_tempo_para_minutos(tempo)
                
                if sistema not in sistemas_gabriel:
                    sistemas_gabriel[sistema] = 0
                sistemas_gabriel[sistema] += minutos
                
                datas_gabriel.add(data)
            
            print(f"\n🖥️  Sistemas utilizados por GABRIEL:")
            for sistema, tempo_total in sistemas_gabriel.items():
                horas = int(tempo_total // 60)
                minutos = int(tempo_total % 60)
                print(f"  • {sistema}: {horas:>2}h {minutos:>2}min ({tempo_total:>6.1f}min)")
            
            print(f"\n📅 Datas de trabalho: {len(datas_gabriel)} dias")
            for data in sorted(datas_gabriel):
                print(f"  • {data}")
            
            tempo_total = sum(sistemas_gabriel.values())
            print(f"\n📊 Tempo total calculado: {tempo_total/60:.1f} horas ({tempo_total:.1f} minutos)")
        
        # 4. VERIFICAR PROBLEMA NA EXTRAÇÃO
        print("\n🔧 4. VERIFICANDO PROBLEMA NA EXTRAÇÃO")
        print("-" * 60)
        
        # Verificar se GABRIEL está na lista de usuários conhecidos
        usuarios_conhecidos = ['PAMELA', 'GERENTE', 'VIVIANE', 'RAYANE', 'VANEZA', 'MARIA', 'DUDA', 'CRISTINA', 'MATIAS']
        
        if 'GABRIEL' in usuarios_conhecidos:
            print("✅ GABRIEL está na lista de usuários conhecidos")
        else:
            print("❌ GABRIEL NÃO está na lista de usuários conhecidos!")
            print("   Esta é a causa do problema!")
            print(f"   Usuários conhecidos: {usuarios_conhecidos}")
        
        # 5. TESTAR EXTRAÇÃO MANUAL
        print("\n🧪 5. TESTANDO EXTRAÇÃO MANUAL")
        print("-" * 60)
        
        # Simular o processo de extração para GABRIEL
        atividades_extraidas = []
        cliente_atual = None
        
        for idx, row in df.iterrows():
            linha = ' '.join([str(cell) for cell in row if pd.notna(cell) and str(cell).strip()])
            
            if not linha.strip():
                continue
            
            # Detectar cliente
            if 'Cliente:' in linha:
                match = re.search(r'Cliente:\s*(\d+)', linha)
                if match:
                    codigo = match.group(1).strip()
                    nome_parte = linha.split(codigo, 1)[1].strip()
                    nome = re.sub(r'\.0\s*', '', nome_parte).strip()
                    
                    cliente_atual = {
                        'codigo': codigo,
                        'nome': nome
                    }
                continue
            
            # Detectar atividade de GABRIEL
            if cliente_atual and 'GABRIEL' in linha.upper():
                # Procurar por padrões de data e tempo
                data_pattern = r'\d{2}/\d{2}/\d{4}'
                tempo_pattern = r'\d{2}:\d{2}:\d{2}'
                
                data_match = re.search(data_pattern, linha)
                tempo_match = re.search(tempo_pattern, linha)
                
                if data_match and tempo_match:
                    # Extrair sistema
                    sistema = None
                    sistemas_conhecidos = ['Folha', 'Contabilidade', 'Escrita', 'Patrimonio', 'Atualizar', 'Registro']
                    for sis in sistemas_conhecidos:
                        if sis in linha:
                            sistema = sis
                            break
                    
                    if sistema:
                        atividade = {
                            'codigo_cliente': cliente_atual['codigo'],
                            'nome_cliente': cliente_atual['nome'],
                            'sistema': sistema,
                            'usuario': 'GABRIEL',
                            'data': data_match.group(),
                            'tempo_gasto': tempo_match.group()
                        }
                        atividades_extraidas.append(atividade)
        
        print(f"📊 Atividades extraídas manualmente: {len(atividades_extraidas)}")
        
        if atividades_extraidas:
            print("✅ Extração manual funcionou! O problema está no script principal")
            
            # Mostrar algumas atividades
            print("\n📋 Exemplos de atividades extraídas:")
            for i, atividade in enumerate(atividades_extraidas[:5]):
                print(f"  {i+1}. Cliente {atividade['codigo_cliente']} - {atividade['nome_cliente']}")
                print(f"     Sistema: {atividade['sistema']}, Data: {atividade['data']}, Tempo: {atividade['tempo_gasto']}")
        else:
            print("❌ Extração manual também falhou")
        
        # 6. RECOMENDAÇÕES
        print("\n💡 6. RECOMENDAÇÕES PARA RESOLVER")
        print("-" * 60)
        
        if len(atividades_extraidas) > 0:
            print("✅ SOLUÇÃO IDENTIFICADA:")
            print("  1. GABRIEL está no arquivo original com {len(atividades_extraidas)} atividades")
            print("  2. O problema é que GABRIEL não está na lista de usuários conhecidos")
            print("  3. Adicionar GABRIEL à lista de usuários conhecidos")
            print("  4. Reexecutar o script de processamento")
        else:
            print("⚠️  PROBLEMA MAIS COMPLEXO:")
            print("  1. Investigar por que a extração manual falhou")
            print("  2. Verificar formato específico das linhas de GABRIEL")
            print("  3. Ajustar lógica de extração")
        
    except Exception as e:
        print(f"❌ Erro na análise: {e}")

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
    print("🚀 INICIANDO ANÁLISE ESPECÍFICA DE GABRIEL")
    
    # Executar análise
    extrair_gabriel_especifico()
    
    print("\n" + "="*80)
    print("ANÁLISE DE GABRIEL CONCLUÍDA")
    print("="*80)

if __name__ == "__main__":
    main()





