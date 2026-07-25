#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script configurável para processar dados de produtividade de diferentes meses
"""

import pandas as pd
import re
import os
import shutil
from datetime import datetime
import argparse

def converter_xls_para_csv(arquivo_xls, arquivo_csv_saida):
    """
    Converte arquivo XLS para CSV usando LibreOffice
    """
    print(f"🔄 Convertendo {arquivo_xls} para CSV...")
    
    comando = f"libreoffice --headless --convert-to csv '{arquivo_xls}' --outdir ."
    
    try:
        resultado = os.system(comando)
        if resultado == 0:
            # Renomear arquivo gerado
            if os.path.exists(arquivo_csv_saida):
                os.remove(arquivo_csv_saida)
            
            # Encontrar arquivo CSV gerado
            arquivos_csv = [f for f in os.listdir('.') if f.endswith('.csv') and 'ClienteTempo' in f]
            if arquivos_csv:
                arquivo_gerado = arquivos_csv[0]
                shutil.move(arquivo_gerado, arquivo_csv_saida)
                print(f"✅ Conversão concluída: {arquivo_csv_saida}")
                return True
            else:
                print("❌ Arquivo CSV não encontrado após conversão")
                return False
        else:
            print(f"❌ Erro na conversão: código {resultado}")
            return False
    except Exception as e:
        print(f"❌ Erro na conversão: {e}")
        return False

def limpar_e_estruturar_dados(arquivo_csv):
    """
    Limpa e estrutura os dados do CSV de produtividade
    """
    print(f"📊 Processando arquivo: {arquivo_csv}")
    
    # Tentar diferentes codificações
    codificacoes = ['utf-8', 'latin1', 'iso-8859-1', 'cp1252']
    df = None
    
    for codificacao in codificacoes:
        try:
            print(f"🔍 Tentando codificação: {codificacao}")
            df = pd.read_csv(arquivo_csv, header=None, encoding=codificacao)
            print(f"✅ Sucesso com codificação: {codificacao}")
            break
        except Exception as e:
            print(f"❌ Falha com codificação {codificacao}: {e}")
            continue
    
    if df is None:
        raise Exception("Não foi possível ler o arquivo com nenhuma codificação")
    
    print(f"📊 Forma original: {df.shape}")
    
    dados_estruturados = []
    atividades = []
    clientes = []
    cliente_atual = None
    
    for idx, row in df.iterrows():
        # Juntar todas as células não vazias da linha
        linha = ' '.join([str(cell) for cell in row if pd.notna(cell) and str(cell).strip()])
        
        # Pular linhas vazias ou cabeçalhos
        if not linha.strip():
            continue
            
        # Pular cabeçalhos específicos
        if any(termo in linha for termo in ['Relação de Clientes', 'Período:', 'Hora:', 'Página:']):
            continue
            
        # Pular cabeçalho de colunas
        if 'Sistema' in linha and 'Usuário' in linha and 'Data' in linha and 'Tempo Gasto' in linha:
            continue
            
        # Detectar cliente
        if 'Cliente:' in linha:
            # Extrair código e nome do cliente
            match = re.search(r'Cliente:\s*(\d+)', linha)
            if match:
                codigo = match.group(1).strip()
                # Extrair nome do cliente (tudo após o código)
                nome_parte = linha.split(codigo, 1)[1].strip()
                # Limpar o nome
                nome = re.sub(r'\.0\s*', '', nome_parte).strip()
                
                cliente_atual = {
                    'codigo': codigo,
                    'nome': nome,
                    'atividades': []
                }
            continue
            
        # Detectar total do cliente
        if 'Total do Cliente:' in linha:
            match = re.search(r'Total do Cliente:\s*(\d{2}:\d{2}:\d{2})', linha)
            if match and cliente_atual:
                cliente_atual['tempo_total'] = match.group(1)
                clientes.append(cliente_atual.copy())
                cliente_atual = None
            continue
            
        # Detectar linha de atividade
        if cliente_atual and not 'Cliente:' in linha and not 'Total do Cliente:' in linha:
            # Procurar por padrões de data e tempo
            data_pattern = r'\d{2}/\d{2}/\d{4}'
            tempo_pattern = r'\d{2}:\d{2}:\d{2}'
            
            data_match = re.search(data_pattern, linha)
            tempo_match = re.search(tempo_pattern, linha)
            
            if data_match and tempo_match:
                # Identificar sistema
                sistema = None
                sistemas_conhecidos = ['Folha', 'Contabilidade', 'Escrita', 'Patrimonio', 'Atualizar', 'Registro', 'Honorários', 'Lalur']
                for sis in sistemas_conhecidos:
                    if sis in linha:
                        sistema = sis
                        break
                
                # Identificar usuário
                usuario = None
                usuarios_conhecidos = ['PAMELA', 'GERENTE', 'VIVIANE', 'RAYANE', 'VANEZA', 'MARIA', 'DUDA', 'CRISTINA', 'MATIAS', 'ANDERSON', 'FABIANO', 'GABRIEL', 'LUCAS.MT', 'SUELEN', 'VINICIUS', 'MASTER2', 'MASTER3']
                for usr in usuarios_conhecidos:
                    if usr in linha:
                        usuario = usr
                        break
                
                if sistema and usuario:
                    atividade = {
                        'codigo_cliente': cliente_atual['codigo'],
                        'nome_cliente': cliente_atual['nome'],
                        'sistema': sistema,
                        'usuario': usuario,
                        'data': data_match.group(),
                        'tempo_gasto': tempo_match.group()
                    }
                    atividades.append(atividade)
                    cliente_atual['atividades'].append(atividade)
    
    return dados_estruturados, atividades, clientes

def criar_dataframe_estruturado(dados_estruturados):
    """
    Cria um DataFrame pandas estruturado a partir dos dados processados
    """
    if not dados_estruturados:
        return pd.DataFrame(), pd.DataFrame()
    
    # Criar DataFrame de atividades
    df_atividades = pd.DataFrame(dados_estruturados)
    
    # Criar DataFrame de clientes
    df_clientes = pd.DataFrame()
    
    return df_atividades, df_clientes

def gerar_relatorios(df_atividades, df_clientes):
    """
    Gera relatórios básicos de produtividade
    """
    relatorios = {}
    
    # 1. Relatório por Cliente
    if not df_atividades.empty:
        relatorio_cliente = df_atividades.groupby(['codigo_cliente', 'nome_cliente']).agg({
            'sistema': 'nunique',
            'usuario': 'nunique',
            'tempo_gasto': 'count'
        }).reset_index()
        relatorio_cliente.columns = ['Código Cliente', 'Nome Cliente', 'Sistemas Únicos', 'Usuários Únicos', 'Total Atividades']
        relatorios['por_cliente'] = relatorio_cliente
    
    # 2. Relatório por Sistema
    if not df_atividades.empty:
        relatorio_sistema = df_atividades.groupby('sistema').agg({
            'codigo_cliente': 'nunique',
            'usuario': 'nunique',
            'tempo_gasto': 'count'
        }).reset_index()
        relatorio_sistema.columns = ['Sistema', 'Clientes Únicos', 'Usuários Únicos', 'Total Atividades']
        relatorios['por_sistema'] = relatorio_sistema
    
    # 3. Relatório por Usuário
    if not df_atividades.empty:
        relatorio_usuario = df_atividades.groupby('usuario').agg({
            'codigo_cliente': 'nunique',
            'sistema': 'nunique',
            'tempo_gasto': 'count'
        }).reset_index()
        relatorio_usuario.columns = ['Usuário', 'Clientes Únicos', 'Sistemas Únicos', 'Total Atividades']
        relatorios['por_usuario'] = relatorio_usuario
    
    # 4. Relatório por Data
    if not df_atividades.empty:
        relatorio_data = df_atividades.groupby('data').agg({
            'codigo_cliente': 'nunique',
            'sistema': 'nunique',
            'usuario': 'nunique',
            'tempo_gasto': 'count'
        }).reset_index()
        relatorio_data.columns = ['Data', 'Clientes Únicos', 'Sistemas Únicos', 'Usuários Únicos', 'Total Atividades']
        relatorios['por_data'] = relatorio_data
    
    return relatorios

def salvar_relatorios(relatorios, diretorio_saida):
    """
    Salva todos os relatórios em arquivos CSV
    """
    os.makedirs(diretorio_saida, exist_ok=True)
    
    for nome_relatorio, df_relatorio in relatorios.items():
        nome_arquivo = f"relatorio_{nome_relatorio}.csv"
        caminho_completo = os.path.join(diretorio_saida, nome_arquivo)
        
        df_relatorio.to_csv(caminho_completo, index=False, encoding='utf-8-sig')
        print(f"📄 Relatório salvo: {caminho_completo}")
        
        # Mostrar resumo do relatório
        print(f"  - {nome_relatorio}: {len(df_relatorio)} registros")

def processar_mes_especifico(mes, ano, diretorio_produtividade="produtividade"):
    """
    Processa dados de produtividade para um mês específico
    """
    print(f"🚀 PROCESSANDO MÊS: {mes}/{ano}")
    print("="*80)
    
    # 1. DEFINIR NOMES DE ARQUIVOS
    nome_arquivo_xls = f"ClienteTempo Gasto {mes}{ano}.xls"
    nome_arquivo_csv = f"ClienteTempo Gasto {mes}{ano}.csv"
    
    caminho_xls = os.path.join(diretorio_produtividade, nome_arquivo_xls)
    caminho_csv = os.path.join(diretorio_produtividade, nome_arquivo_csv)
    
    # 2. VERIFICAR SE ARQUIVO XLS EXISTE
    if not os.path.exists(caminho_xls):
        print(f"❌ Arquivo não encontrado: {caminho_xls}")
        print("📁 Arquivos disponíveis na pasta produtividade:")
        
        if os.path.exists(diretorio_produtividade):
            arquivos = os.listdir(diretorio_produtividade)
            arquivos_xls = [f for f in arquivos if f.endswith('.xls') and 'ClienteTempo' in f]
            for arquivo in arquivos_xls:
                print(f"  • {arquivo}")
        
        return False
    
    # 3. CONVERTER XLS PARA CSV
    if not converter_xls_para_csv(caminho_xls, caminho_csv):
        return False
    
    # 4. PROCESSAR DADOS
    try:
        dados_estruturados, atividades, clientes = limpar_e_estruturar_dados(caminho_csv)
        
        if not atividades:
            print("❌ Nenhuma atividade foi extraída")
            return False
        
        print(f"\n📊 Total de atividades extraídas: {len(atividades)}")
        
        # 5. CRIAR DATAFRAMES
        df_atividades, df_clientes = criar_dataframe_estruturado(atividades)
        
        print(f"📊 DataFrame de Atividades: {df_atividades.shape}")
        
        # 6. GERAR RELATÓRIOS
        print("\n📈 Gerando relatórios...")
        relatorios = gerar_relatorios(df_atividades, df_clientes)
        
        # 7. SALVAR RELATÓRIOS
        diretorio_relatorios = f"produtividade/relatorios/por_periodo/{ano}-{mes}"
        salvar_relatorios(relatorios, diretorio_relatorios)
        
        # 8. SALVAR DADOS ESTRUTURADOS
        nome_arquivo_atividades = f"dados_atividades_estruturados_{mes}{ano}.csv"
        nome_arquivo_clientes = f"dados_clientes_estruturados_{mes}{ano}.csv"
        
        df_atividades.to_csv(nome_arquivo_atividades, index=False, encoding='utf-8-sig')
        print(f"💾 Dados de atividades salvos: {nome_arquivo_atividades}")
        
        if not df_clientes.empty:
            df_clientes.to_csv(nome_arquivo_clientes, index=False, encoding='utf-8-sig')
            print(f"💾 Dados de clientes salvos: {nome_arquivo_clientes}")
        
        # 9. LIMPEZA
        if os.path.exists(caminho_csv):
            os.remove(caminho_csv)
            print(f"🧹 Arquivo temporário removido: {caminho_csv}")
        
        print(f"\n✅ Processamento concluído com sucesso para {mes}/{ano}!")
        print(f"📁 Relatórios salvos em: {diretorio_relatorios}/")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no processamento: {e}")
        return False

def main():
    """
    Função principal
    """
    parser = argparse.ArgumentParser(description='Processar dados de produtividade para um mês específico')
    parser.add_argument('--mes', type=str, required=True, help='Mês (ex: agosto, 08, 8)')
    parser.add_argument('--ano', type=str, required=True, help='Ano (ex: 2025)')
    parser.add_argument('--diretorio', type=str, default='produtividade', help='Diretório onde estão os arquivos XLS')
    
    args = parser.parse_args()
    
    # Normalizar mês
    mes = args.mes.lower().strip()
    ano = args.ano.strip()
    
    # Mapear nomes de meses para números
    meses_map = {
        'janeiro': '01', 'jan': '01', '1': '01', '01': '01',
        'fevereiro': '02', 'fev': '02', '2': '02', '02': '02',
        'marco': '03', 'mar': '03', '3': '03', '03': '03',
        'abril': '04', 'abr': '04', '4': '04', '04': '04',
        'maio': '05', 'mai': '05', '5': '05', '05': '05',
        'junho': '06', 'jun': '06', '6': '06', '06': '06',
        'julho': '07', 'jul': '07', '7': '07', '07': '07',
        'agosto': '08', 'ago': '08', '8': '08', '08': '08',
        'setembro': '09', 'set': '09', '9': '09', '09': '09',
        'outubro': '10', 'out': '10', '10': '10',
        'novembro': '11', 'nov': '11', '11': '11',
        'dezembro': '12', 'dez': '12', '12': '12'
    }
    
    if mes in meses_map:
        mes_numero = meses_map[mes]
        mes_nome = mes.capitalize()
    else:
        print(f"❌ Mês inválido: {mes}")
        print("Meses válidos:", list(set([k for k in meses_map.keys() if len(k) > 2])))
        return
    
    print(f"📅 Processando: {mes_nome} de {ano}")
    print(f"🔢 Código do mês: {mes_numero}")
    
    # Processar mês específico
    sucesso = processar_mes_especifico(mes_numero, ano, args.diretorio)
    
    if sucesso:
        print(f"\n🎉 {mes_nome} de {ano} processado com sucesso!")
    else:
        print(f"\n❌ Falha no processamento de {mes_nome} de {ano}")

if __name__ == "__main__":
    main()





