#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para identificar as 10 empresas (por código) que mais gastaram tempo
"""

import pandas as pd
import re
from datetime import datetime
import os

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

def minutos_para_hora_minuto(minutos):
    """
    Converte minutos para formato HH:MM
    """
    try:
        minutos = int(minutos)
        horas = minutos // 60
        mins = minutos % 60
        return f"{horas:02d}:{mins:02d}"
    except:
        return "00:00"

def analisar_top_10_empresas():
    """
    Analisa as 10 empresas que mais gastaram tempo
    """
    print("🏢 ANÁLISE TOP 10 EMPRESAS POR TEMPO GASTO")
    print("="*80)
    print(f"Data da análise: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("="*80)
    
    try:
        # 1. VERIFICAR DADOS ESTRUTURADOS
        print("\n📊 1. VERIFICANDO DADOS DISPONÍVEIS")
        print("-" * 60)
        
        if os.path.exists("dados_atividades_estruturados.csv"):
            print("✅ Usando dados já estruturados")
            df_atividades = pd.read_csv("dados_atividades_estruturados.csv")
            
            # Converter tempo para minutos
            df_atividades['tempo_minutos'] = df_atividades['tempo_gasto'].apply(converter_tempo_para_minutos)
            
            # Agrupar por empresa
            tempo_por_empresa = df_atividades.groupby(['codigo_cliente', 'nome_cliente'])['tempo_minutos'].sum().reset_index()
            tempo_por_empresa = tempo_por_empresa.sort_values('tempo_minutos', ascending=False)
            
        else:
            print("📁 Dados estruturados não encontrados, processando arquivo original...")
            
            # Processar arquivo original
            tempo_por_empresa = processar_arquivo_original()
        
        # 2. MOSTRAR TOP 10
        print("\n🏆 2. TOP 10 EMPRESAS POR TEMPO GASTO")
        print("-" * 60)
        
        if not tempo_por_empresa.empty:
            # Adicionar coluna hora:minuto
            tempo_por_empresa['tempo_hora_minuto'] = tempo_por_empresa['tempo_minutos'].apply(minutos_para_hora_minuto)
            
            top_10 = tempo_por_empresa.head(10)
            
            print("Rank | Código | Empresa | Tempo Total | Hora:Min | Horas | % do Total")
            print("-" * 90)
            
            tempo_total_sistema = tempo_por_empresa['tempo_minutos'].sum()
            
            for idx, row in top_10.iterrows():
                rank = idx + 1
                codigo = row['codigo_cliente']
                nome = row['nome_cliente']
                tempo_min = row['tempo_minutos']
                hora_min = row['tempo_hora_minuto']
                horas = tempo_min / 60
                percentual = (tempo_min / tempo_total_sistema) * 100
                
                # Truncar nome se for muito longo
                nome_display = nome[:35] + "..." if len(nome) > 35 else nome
                
                print(f"{rank:>4} | {codigo:>6} | {nome_display:<35} | {tempo_min:>8.1f}min | {hora_min:>8s} | {horas:>5.1f}h | {percentual:>5.1f}%")
            
            # 3. ESTATÍSTICAS GERAIS
            print("\n📈 3. ESTATÍSTICAS GERAIS")
            print("-" * 60)
            
            print(f"📊 Total de empresas analisadas: {len(tempo_por_empresa)}")
            print(f"⏰ Tempo total do sistema: {tempo_total_sistema/60:.1f} horas ({tempo_total_sistema:.1f} minutos)")
            print(f"📊 Tempo médio por empresa: {tempo_total_sistema/len(tempo_por_empresa):.1f} minutos")
            
            # Top 10 representa quanto do total?
            tempo_top_10 = top_10['tempo_minutos'].sum()
            percentual_top_10 = (tempo_top_10 / tempo_total_sistema) * 100
            print(f"🎯 Top 10 representa: {percentual_top_10:.1f}% do tempo total")
            
            # 4. ANÁLISE DETALHADA DO TOP 1
            print("\n🥇 4. ANÁLISE DETALHADA - EMPRESA #1")
            print("-" * 60)
            
            if not top_10.empty:
                top_1 = top_10.iloc[0]
                codigo_top1 = top_1['codigo_cliente']
                nome_top1 = top_1['nome_cliente']
                tempo_top1 = top_1['tempo_minutos']
                
                print(f"🏆 Empresa: {nome_top1}")
                print(f"🔢 Código: {codigo_top1}")
                print(f"⏰ Tempo total: {tempo_top1/60:.1f} horas ({tempo_top1:.1f} minutos)")
                
                # Analisar atividades desta empresa
                if 'df_atividades' in locals():
                    atividades_empresa = df_atividades[df_atividades['codigo_cliente'] == codigo_top1]
                    
                    if not atividades_empresa.empty:
                        print(f"📋 Total de atividades: {len(atividades_empresa)}")
                        
                        # Sistemas utilizados
                        sistemas_empresa = atividades_empresa.groupby('sistema')['tempo_minutos'].sum().sort_values(ascending=False)
                        print(f"\n🖥️  Sistemas utilizados:")
                        for sistema, tempo in sistemas_empresa.items():
                            horas_sis = tempo / 60
                            print(f"  • {sistema}: {horas_sis:.1f}h ({tempo:.1f}min)")
                        
                        # Usuários que trabalharam
                        usuarios_empresa = atividades_empresa.groupby('usuario')['tempo_minutos'].sum().sort_values(ascending=False)
                        print(f"\n👥 Usuários que trabalharam:")
                        for usuario, tempo in usuarios_empresa.items():
                            horas_usr = tempo / 60
                            print(f"  • {usuario}: {horas_usr:.1f}h ({tempo:.1f}min)")
            
            # 5. SALVAR RESULTADOS
            print("\n💾 5. SALVANDO RESULTADOS")
            print("-" * 60)
            
            # Salvar top 10 completo
            arquivo_top10 = "top_10_empresas_tempo.csv"
            top_10.to_csv(arquivo_top10, index=False)
            print(f"✅ Top 10 salvo em: {arquivo_top10}")
            
            # Salvar ranking completo
            arquivo_completo = "ranking_completo_empresas_tempo.csv"
            tempo_por_empresa.to_csv(arquivo_completo, index=False)
            print(f"✅ Ranking completo salvo em: {arquivo_completo}")
            
            # 6. RECOMENDAÇÕES
            print("\n💡 6. RECOMENDAÇÕES BASEADAS NA ANÁLISE")
            print("-" * 60)
            
            if not top_10.empty:
                top_1_tempo = top_10.iloc[0]['tempo_minutos']
                top_1_percentual = (top_1_tempo / tempo_total_sistema) * 100
                
                if top_1_percentual > 20:
                    print("🚨 ATENÇÃO: A empresa #1 representa mais de 20% do tempo total")
                    print("   Recomenda-se investigar se há sobrecarga ou se é normal")
                
                if top_1_percentual > 10:
                    print("📊 A empresa #1 é um cliente de alto volume")
                    print("   Considere estratégias de otimização e priorização")
                
                print(f"🎯 Foco principal: Empresa {top_10.iloc[0]['codigo_cliente']} ({top_10.iloc[0]['nome_cliente']})")
                print(f"   Representa {top_1_percentual:.1f}% do tempo total")
            
        else:
            print("❌ Nenhum dado encontrado para análise")
            
    except Exception as e:
        print(f"❌ Erro na análise: {e}")

def processar_arquivo_original():
    """
    Processa o arquivo original para extrair dados de empresas
    """
    print("📁 Processando arquivo original...")
    
    try:
        # Tentar diferentes codificações
        codificacoes = ['utf-8', 'latin1', 'iso-8859-1', 'cp1252']
        df = None
        
        arquivo_csv = "produtividade/ClienteTempo Gasto.csv"
        
        for codificacao in codificacoes:
            try:
                df = pd.read_csv(arquivo_csv, header=None, encoding=codificacao)
                print(f"✅ Arquivo lido com encoding: {codificacao}")
                break
            except Exception as e:
                continue
        
        if df is None:
            print("❌ Não foi possível ler o arquivo com nenhuma codificação")
            return pd.DataFrame()
        
        empresas_tempo = {}
        cliente_atual = None
        
        for idx, row in df.iterrows():
            # Converter linha para lista de células
            linha_cells = [str(cell).strip() if pd.notna(cell) else '' for cell in row]
            linha_str = ' '.join([c for c in linha_cells if c])
            
            if not linha_str.strip():
                continue
            
            # Detectar cliente (primeira célula deve conter "Cliente:")
            primeira_celula = linha_cells[0] if len(linha_cells) > 0 else ''
            if primeira_celula and 'Cliente:' in primeira_celula:
                # O código está geralmente na coluna 2 (índice 2)
                # O nome está geralmente na coluna 4 (índice 4)
                codigo = ''
                nome = ''
                
                # Procurar código (número após "Cliente:")
                for i, cell in enumerate(linha_cells):
                    if i > 0 and cell.strip() and cell.strip().isdigit():
                        codigo = cell.strip()
                        # Nome geralmente vem algumas colunas depois
                        if i + 2 < len(linha_cells) and linha_cells[i + 2].strip():
                            nome = linha_cells[i + 2].strip()
                        elif i + 1 < len(linha_cells) and linha_cells[i + 1].strip():
                            nome = linha_cells[i + 1].strip()
                        break
                
                # Se não encontrou código nas colunas, tentar regex
                if not codigo:
                    match = re.search(r'Cliente:\s*,?\s*(\d+)', linha_str)
                    if match:
                        codigo = match.group(1).strip()
                        # Tentar extrair nome após o código
                        partes = linha_str.split(codigo, 1)
                        if len(partes) > 1:
                            nome_raw = partes[1].strip()
                            # Limpar nome
                            nome = re.sub(r'^\s*,\s*', '', nome_raw)
                            nome = re.sub(r'\s+', ' ', nome)
                            nome = re.sub(r'\.0\s*$', '', nome)
                            nome = nome.strip(',').strip()
                
                if codigo and len(codigo) > 0:
                    # Validar que é um código de cliente real (não parte de tempo)
                    if codigo.isdigit() and int(codigo) > 0 and len(codigo) <= 4:
                        if not nome:
                            nome = "Sem nome"
                        # Limpar nome de caracteres especiais
                        nome = re.sub(r'^\.0\s*', '', nome)
                        nome = nome.strip()
                        
                        cliente_atual = {
                            'codigo': codigo,
                            'nome': nome
                        }
                        # Não printar todos os clientes para não poluir o output
                continue
            
            # Ignorar linhas com "Total do Cliente"
            if 'Total do Cliente:' in linha_str:
                continue
            
            # Detectar atividade (linha com data e tempo)
            if cliente_atual:
                data_pattern = r'\d{2}/\d{2}/\d{4}'
                tempo_pattern = r'\d{2}:\d{2}:\d{2}'
                
                data_match = re.search(data_pattern, linha_str)
                tempo_match = re.search(tempo_pattern, linha_str)
                
                if data_match and tempo_match:
                    # Usar group(0) para pegar toda a correspondência
                    tempo = tempo_match.group(0)
                    minutos = converter_tempo_para_minutos(tempo)
                    
                    if minutos > 0:  # Validar que o tempo foi convertido corretamente
                        chave = (cliente_atual['codigo'], cliente_atual['nome'])
                        if chave not in empresas_tempo:
                            empresas_tempo[chave] = 0
                        empresas_tempo[chave] += minutos
        
        # Converter para DataFrame
        dados = []
        for (codigo, nome), tempo_total in empresas_tempo.items():
            dados.append({
                'codigo_cliente': codigo,
                'nome_cliente': nome,
                'tempo_minutos': tempo_total
            })
        
        df_resultado = pd.DataFrame(dados)
        print(f"✅ Total de empresas encontradas: {len(df_resultado)}")
        return df_resultado.sort_values('tempo_minutos', ascending=False)
        
    except Exception as e:
        import traceback
        print(f"❌ Erro ao processar arquivo original: {e}")
        traceback.print_exc()
        return pd.DataFrame()

def main():
    """
    Função principal
    """
    print("🚀 INICIANDO ANÁLISE TOP 10 EMPRESAS")
    
    # Executar análise
    analisar_top_10_empresas()
    
    print("\n" + "="*80)
    print("ANÁLISE TOP 10 EMPRESAS CONCLUÍDA")
    print("="*80)

if __name__ == "__main__":
    main()





