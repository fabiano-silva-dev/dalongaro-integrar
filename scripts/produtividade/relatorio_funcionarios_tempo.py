#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para gerar relatório de tempo gasto por funcionário e por empresa
"""

import pandas as pd
import re
import os
from datetime import datetime
from collections import defaultdict
from openpyxl.utils import get_column_letter

# ============================================================================
# CONFIGURAÇÃO - MAPEAMENTO DE NOMES DE USUÁRIOS CURINGAS
# ============================================================================
# 
# Use esta seção para mapear nomes do sistema para nomes padronizados no relatório.
# 
# Exemplo: Se no sistema aparece "MASTER2" mas você quer que apareça como
#          "JOYCE" no relatório, adicione: 'MASTER2': 'JOYCE'
#
# Para adicionar novos mapeamentos, siga o padrão:
#   'NOME_NO_SISTEMA': 'NOME_EXIBIDO_NO_RELATORIO'
#
# IMPORTANTE: Use sempre MAIÚSCULAS para as chaves e valores
# ============================================================================

MAPEAMENTO_NOMES = {
    'MASTER2': 'JOYCE',
    'MASTER3': 'DOUGLAS',
    # Adicione outros mapeamentos aqui:
    # 'NOME_NO_SISTEMA': 'NOME_PADRONIZADO',
    # 'OUTRO_NOME': 'NOME_EXIBIDO',
}

# ============================================================================
# FIM DA CONFIGURAÇÃO
# ============================================================================

def aplicar_mapeamento_nome(nome):
    """
    Aplica mapeamento de nomes alternativos
    """
    nome_upper = nome.upper().strip()
    return MAPEAMENTO_NOMES.get(nome_upper, nome)

def parece_nome_funcionario(texto):
    """
    Verifica se um texto parece ser um nome de funcionário
    Aceita letras, números, pontos, traços, mas deve conter pelo menos uma letra
    """
    if not texto or len(texto) < 2:
        return False
    
    # Não pode ser só números
    if texto.isdigit():
        return False
    
    # Não pode ser data ou tempo
    if re.match(r'\d{2}/\d{2}/\d{4}', texto) or re.match(r'\d{2}:\d{2}:\d{2}', texto):
        return False
    
    # Deve conter pelo menos uma letra
    if not any(c.isalpha() for c in texto):
        return False
    
    # Aceita letras, números, pontos, traços e underscores
    # Remove esses caracteres e verifica se sobram apenas letras e números
    texto_sem_especiais = re.sub(r'[._-]', '', texto)
    if texto_sem_especiais.isalnum():
        return True
    
    return False

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

def minutos_para_hora_minuto_segundo(minutos):
    """
    Converte minutos (decimais) para formato HH:MM:SS
    """
    try:
        minutos_totais = round(minutos * 60)  # Converter para segundos totais
        horas = minutos_totais // 3600
        minutos = (minutos_totais % 3600) // 60
        segundos = minutos_totais % 60
        return f"{horas:02d}:{minutos:02d}:{segundos:02d}"
    except:
        return "00:00:00"

def minutos_para_hora_minuto(minutos):
    """
    Converte minutos para formato HH:MM (mantido para compatibilidade)
    """
    try:
        minutos_int = int(round(minutos))
        horas = minutos_int // 60
        mins = minutos_int % 60
        return f"{horas:02d}:{mins:02d}"
    except:
        return "00:00"

def processar_dados():
    """
    Processa o arquivo CSV e extrai dados por funcionário e empresa
    """
    print("📁 Processando arquivo produtividade/ClienteTempo Gasto.csv...")
    
    # Estrutura: {funcionario: {empresa: tempo_total_minutos}}
    dados_funcionarios = defaultdict(lambda: defaultdict(float))
    
    # Tentar diferentes codificações
    codificacoes = ['latin1', 'iso-8859-1', 'cp1252', 'utf-8']
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
        print("❌ Não foi possível ler o arquivo")
        return {}
    
    cliente_atual = None
    cliente_codigo = None
    
    for idx, row in df.iterrows():
        # Converter linha para lista de células
        linha_cells = [str(cell).strip() if pd.notna(cell) else '' for cell in row]
        linha_str = ' '.join([c for c in linha_cells if c])
        
        if not linha_str.strip():
            continue
        
        # Detectar cliente
        primeira_celula = linha_cells[0] if len(linha_cells) > 0 else ''
        if primeira_celula and 'Cliente:' in primeira_celula:
            codigo = ''
            nome = ''
            
            # Procurar código e nome
            for i, cell in enumerate(linha_cells):
                if i > 0 and cell.strip() and cell.strip().isdigit():
                    codigo = cell.strip()
                    if len(codigo) <= 4 and int(codigo) > 0:
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
                    partes = linha_str.split(codigo, 1)
                    if len(partes) > 1:
                        nome_raw = partes[1].strip()
                        nome = re.sub(r'^\s*,\s*', '', nome_raw)
                        nome = re.sub(r'\s+', ' ', nome)
                        nome = re.sub(r'\.0\s*$', '', nome)
                        nome = nome.strip(',').strip()
            
            if codigo and len(codigo) > 0 and codigo.isdigit() and int(codigo) > 0 and len(codigo) <= 4:
                cliente_codigo = codigo
                if not nome:
                    nome = f"Cliente {codigo}"
                # Limpar nome de caracteres especiais
                nome = re.sub(r'^\.0\s*', '', nome)
                cliente_atual = nome.strip()
            continue
        
        # Ignorar linhas com "Total do Cliente"
        if 'Total do Cliente:' in linha_str:
            continue
        
        # Ignorar cabeçalhos e linhas de informação
        if 'Relação de Clientes' in linha_str or 'Período:' in linha_str or 'Sistema' in primeira_celula:
            continue
        
        # Detectar atividade (linha com data e tempo)
        if cliente_atual:
            data_pattern = r'\d{2}/\d{2}/\d{4}'
            tempo_pattern = r'\d{2}:\d{2}:\d{2}'
            
            data_match = re.search(data_pattern, linha_str)
            tempo_match = re.search(tempo_pattern, linha_str)
            
            if data_match and tempo_match:
                # Extrair usuário/funcionário
                # O usuário geralmente está na coluna correspondente a "Usuário"
                # Procurar por palavras que parecem nomes próprios
                funcionario = None
                
                # Tentar encontrar o funcionário nas células
                # Normalmente está próximo ao sistema (Folha, Contabilidade, Escrita, etc)
                for i, cell in enumerate(linha_cells):
                    cell_upper = cell.upper().strip()
                    # Nomes comuns de sistemas
                    if cell_upper in ['FOLHA', 'CONTABILIDADE', 'ESCRITA', 'PATRIMONIO', 'GERENTE', 'LALUR', 'REGISTRO', 'HONORÁRIOS', 'HONORARIOS']:
                        # O funcionário pode estar em algumas células à frente (geralmente i+4, mas pode variar)
                        # Procurar nas próximas 5 células
                        for offset in range(1, 6):
                            if i + offset < len(linha_cells):
                                func_candidate = linha_cells[i + offset].strip()
                                if func_candidate and parece_nome_funcionario(func_candidate):
                                    funcionario = func_candidate
                                    break
                        if funcionario:
                            break
                
                # Se não encontrou, tentar extrair da string
                if not funcionario:
                    # Procurar palavras que podem ser nomes (podem conter números, como MASTER2, MASTER3)
                    palavras = linha_str.split()
                    for palavra in palavras:
                        palavra_clean = palavra.strip(',')
                        # Verificar se parece ser um nome usando a função auxiliar
                        if (len(palavra_clean) >= 2 and 
                            parece_nome_funcionario(palavra_clean) and
                            palavra_clean.upper() not in ['FOLHA', 'CONTABILIDADE', 'ESCRITA', 'PATRIMONIO', 'LALUR', 'REGISTRO', 'HONORÁRIOS', 'HONORARIOS', 'SISTEMA', 'USUARIO', 'DATA', 'TEMPO', 'GASTO']):
                            funcionario = palavra_clean
                            break
                
                if funcionario:
                    tempo = tempo_match.group(0)
                    minutos = converter_tempo_para_minutos(tempo)
                    
                    if minutos > 0:
                        # Normalizar nome do funcionário (maiúsculas, sem espaços extras)
                        funcionario = funcionario.upper().strip()
                        funcionario = re.sub(r'\s+', ' ', funcionario)
                        
                        # Aplicar mapeamento de nomes (JOYCE -> MASTER2, DOUGLAS -> MASTER3)
                        funcionario = aplicar_mapeamento_nome(funcionario)
                        
                        dados_funcionarios[funcionario][cliente_atual] += minutos
    
    print(f"✅ Dados processados para {len(dados_funcionarios)} funcionários")
    return dados_funcionarios

def gerar_relatorio_txt(dados_funcionarios, arquivo_saida="produtividade/relatorio_funcionarios_tempo.txt"):
    """
    Gera relatório em formato TXT
    """
    # Criar diretório se não existir
    diretorio = os.path.dirname(arquivo_saida)
    if diretorio and not os.path.exists(diretorio):
        os.makedirs(diretorio, exist_ok=True)
    
    print(f"\n📝 Gerando relatório: {arquivo_saida}")
    
    # Ordenar funcionários por tempo total (decrescente)
    funcionarios_ordenados = []
    for funcionario, empresas in dados_funcionarios.items():
        tempo_total = sum(empresas.values())
        funcionarios_ordenados.append((funcionario, tempo_total, empresas))
    
    funcionarios_ordenados.sort(key=lambda x: x[1], reverse=True)
    
    with open(arquivo_saida, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("RELATÓRIO DE TEMPO GASTO POR FUNCIONÁRIO E EMPRESA\n")
        f.write(f"Data de geração: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        
        for funcionario, tempo_total, empresas in funcionarios_ordenados:
            # Nome do funcionário e tempo total (alinhados)
            tempo_total_formatado = minutos_para_hora_minuto_segundo(tempo_total)
            f.write(f"{funcionario:<25} {tempo_total_formatado:>11}\n")
            
            # Ordenar empresas por tempo (decrescente)
            empresas_ordenadas = sorted(empresas.items(), key=lambda x: x[1], reverse=True)
            
            for empresa, tempo in empresas_ordenadas:
                tempo_formatado = minutos_para_hora_minuto_segundo(tempo)
                # Empresa indentada com espaços
                f.write(f"          {empresa:<25} {tempo_formatado:>11}\n")
            
            f.write("\n")
        
        # Adicionar seção de resumo no final
        f.write("\n" + "=" * 80 + "\n")
        f.write("RESUMO - TOTAL POR FUNCIONÁRIO\n")
        f.write("=" * 80 + "\n\n")
        
        # Calcular tempo total geral
        tempo_total_geral = sum(tempo_total for _, tempo_total, _ in funcionarios_ordenados)
        
        for funcionario, tempo_total, empresas in funcionarios_ordenados:
            tempo_total_formatado = minutos_para_hora_minuto_segundo(tempo_total)
            percentual = (tempo_total / tempo_total_geral * 100) if tempo_total_geral > 0 else 0
            f.write(f"{funcionario:<25} {tempo_total_formatado:>11} ({percentual:>5.1f}%)\n")
        
        f.write("\n" + "-" * 80 + "\n")
        tempo_total_geral_formatado = minutos_para_hora_minuto_segundo(tempo_total_geral)
        f.write(f"{'TOTAL GERAL':<25} {tempo_total_geral_formatado:>11}\n")
        f.write("=" * 80 + "\n")
        
        # Adicionar resumo por empresa
        f.write("\n" + "=" * 80 + "\n")
        f.write("RESUMO - TOTAL POR EMPRESA\n")
        f.write("=" * 80 + "\n\n")
        
        # Agrupar dados por empresa
        dados_empresas = defaultdict(float)
        for funcionario, tempo_total, empresas in funcionarios_ordenados:
            for empresa, tempo in empresas.items():
                dados_empresas[empresa] += tempo
        
        # Ordenar empresas por tempo total (decrescente)
        empresas_ordenadas = sorted(dados_empresas.items(), key=lambda x: x[1], reverse=True)
        
        for empresa, tempo_total in empresas_ordenadas:
            tempo_total_formatado = minutos_para_hora_minuto_segundo(tempo_total)
            percentual = (tempo_total / tempo_total_geral * 100) if tempo_total_geral > 0 else 0
            f.write(f"{empresa:<50} {tempo_total_formatado:>11} ({percentual:>5.1f}%)\n")
        
        f.write("\n" + "-" * 80 + "\n")
        f.write(f"{'TOTAL GERAL':<50} {tempo_total_geral_formatado:>11}\n")
        f.write("=" * 80 + "\n")
    
    print(f"✅ Relatório salvo em: {arquivo_saida}")

def gerar_planilha_excel(dados_funcionarios, arquivo_saida="produtividade/relatorio_funcionarios_tempo.xlsx"):
    """
    Gera planilha Excel com três abas: Detalhamento, Resumo Funcionários, Resumo Empresas
    """
    # Criar diretório se não existir
    diretorio = os.path.dirname(arquivo_saida)
    if diretorio and not os.path.exists(diretorio):
        os.makedirs(diretorio, exist_ok=True)
    
    print(f"\n📊 Gerando planilha Excel: {arquivo_saida}")
    
    # Ordenar funcionários por tempo total (decrescente)
    funcionarios_ordenados = []
    for funcionario, empresas in dados_funcionarios.items():
        tempo_total = sum(empresas.values())
        funcionarios_ordenados.append((funcionario, tempo_total, empresas))
    
    funcionarios_ordenados.sort(key=lambda x: x[1], reverse=True)
    
    # Calcular tempo total geral
    tempo_total_geral = sum(tempo_total for _, tempo_total, _ in funcionarios_ordenados)
    
    # Criar ExcelWriter
    with pd.ExcelWriter(arquivo_saida, engine='openpyxl') as writer:
        
        # ========== ABA 1: DETALHAMENTO POR FUNCIONÁRIO ==========
        dados_detalhamento = []
        for funcionario, tempo_total, empresas in funcionarios_ordenados:
            empresas_ordenadas = sorted(empresas.items(), key=lambda x: x[1], reverse=True)
            
            # Primeira linha: Funcionário e total
            dados_detalhamento.append({
                'Funcionário': funcionario,
                'Empresa': '',
                'Tempo (HH:MM:SS)': minutos_para_hora_minuto_segundo(tempo_total),
                'Tempo (Minutos)': round(tempo_total, 2)
            })
            
            # Linhas seguintes: Empresas
            for empresa, tempo in empresas_ordenadas:
                dados_detalhamento.append({
                    'Funcionário': '',
                    'Empresa': empresa,
                    'Tempo (HH:MM:SS)': minutos_para_hora_minuto_segundo(tempo),
                    'Tempo (Minutos)': round(tempo, 2)
                })
            
            # Linha em branco entre funcionários
            dados_detalhamento.append({
                'Funcionário': '',
                'Empresa': '',
                'Tempo (HH:MM:SS)': '',
                'Tempo (Minutos)': ''
            })
        
        df_detalhamento = pd.DataFrame(dados_detalhamento)
        df_detalhamento.to_excel(writer, sheet_name='Detalhamento', index=False)
        
        # ========== ABA 2: RESUMO POR FUNCIONÁRIO ==========
        dados_resumo_funcionarios = []
        for funcionario, tempo_total, empresas in funcionarios_ordenados:
            percentual = (tempo_total / tempo_total_geral * 100) if tempo_total_geral > 0 else 0
            dados_resumo_funcionarios.append({
                'Funcionário': funcionario,
                'Tempo (HH:MM:SS)': minutos_para_hora_minuto_segundo(tempo_total),
                'Tempo (Minutos)': round(tempo_total, 2),
                'Percentual (%)': round(percentual, 2),
                'Quantidade de Empresas': len(empresas)
            })
        
        # Adicionar total geral
        dados_resumo_funcionarios.append({
            'Funcionário': 'TOTAL GERAL',
            'Tempo (HH:MM:SS)': minutos_para_hora_minuto_segundo(tempo_total_geral),
            'Tempo (Minutos)': round(tempo_total_geral, 2),
            'Percentual (%)': 100.0,
            'Quantidade de Empresas': ''
        })
        
        df_resumo_funcionarios = pd.DataFrame(dados_resumo_funcionarios)
        df_resumo_funcionarios.to_excel(writer, sheet_name='Resumo Funcionários', index=False)
        
        # ========== ABA 3: RESUMO POR EMPRESA ==========
        dados_empresas = defaultdict(float)
        for funcionario, tempo_total, empresas in funcionarios_ordenados:
            for empresa, tempo in empresas.items():
                dados_empresas[empresa] += tempo
        
        # Ordenar empresas por tempo total (decrescente)
        empresas_ordenadas = sorted(dados_empresas.items(), key=lambda x: x[1], reverse=True)
        
        dados_resumo_empresas = []
        for empresa, tempo_total in empresas_ordenadas:
            percentual = (tempo_total / tempo_total_geral * 100) if tempo_total_geral > 0 else 0
            dados_resumo_empresas.append({
                'Empresa': empresa,
                'Tempo (HH:MM:SS)': minutos_para_hora_minuto_segundo(tempo_total),
                'Tempo (Minutos)': round(tempo_total, 2),
                'Percentual (%)': round(percentual, 2)
            })
        
        # Adicionar total geral
        dados_resumo_empresas.append({
            'Empresa': 'TOTAL GERAL',
            'Tempo (HH:MM:SS)': minutos_para_hora_minuto_segundo(tempo_total_geral),
            'Tempo (Minutos)': round(tempo_total_geral, 2),
            'Percentual (%)': 100.0
        })
        
        df_resumo_empresas = pd.DataFrame(dados_resumo_empresas)
        df_resumo_empresas.to_excel(writer, sheet_name='Resumo Empresas', index=False)
        
        # Ajustar largura das colunas
        for sheet_name in writer.sheets:
            worksheet = writer.sheets[sheet_name]
            df = None
            if sheet_name == 'Detalhamento':
                df = df_detalhamento
            elif sheet_name == 'Resumo Funcionários':
                df = df_resumo_funcionarios
            elif sheet_name == 'Resumo Empresas':
                df = df_resumo_empresas
            
            if df is not None:
                for idx, col in enumerate(df.columns, 1):
                    max_length = max(df[col].astype(str).map(len).max(), 10)
                    col_letter = get_column_letter(idx)
                    worksheet.column_dimensions[col_letter].width = min(max_length + 2, 50)
    
    print(f"✅ Planilha Excel salva em: {arquivo_saida}")

def main():
    """
    Função principal
    """
    print("🚀 INICIANDO GERAÇÃO DE RELATÓRIO POR FUNCIONÁRIO")
    print("=" * 80)
    
    # Processar dados
    dados_funcionarios = processar_dados()
    
    if not dados_funcionarios:
        print("❌ Nenhum dado encontrado para gerar o relatório")
        return
    
    # Gerar relatório TXT
    gerar_relatorio_txt(dados_funcionarios)
    
    # Gerar planilha Excel
    gerar_planilha_excel(dados_funcionarios)
    
    # Estatísticas
    print("\n📊 ESTATÍSTICAS:")
    print("-" * 60)
    total_funcionarios = len(dados_funcionarios)
    total_empresas = len(set(empresa for empresas in dados_funcionarios.values() for empresa in empresas.keys()))
    tempo_total_geral = sum(sum(empresas.values()) for empresas in dados_funcionarios.values())
    
    print(f"👥 Total de funcionários: {total_funcionarios}")
    print(f"🏢 Total de empresas distintas: {total_empresas}")
    print(f"⏰ Tempo total registrado: {minutos_para_hora_minuto(tempo_total_geral)}")
    
    print("\n" + "=" * 80)
    print("RELATÓRIO GERADO COM SUCESSO")
    print("=" * 80)

if __name__ == "__main__":
    main()

