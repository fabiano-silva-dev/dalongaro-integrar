#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import re
import os
import PyPDF2
from glob import glob
from collections import Counter
from datetime import datetime
import argparse
import sys

def extrair_texto_do_pdf(caminho_pdf):
    """
    Extrai todo o texto de um arquivo PDF.
    """
    texto_completo = ""
    try:
        with open(caminho_pdf, 'rb') as arquivo:
            leitor_pdf = PyPDF2.PdfReader(arquivo)
            for pagina in leitor_pdf.pages:
                texto_pagina = pagina.extract_text()
                if texto_pagina:
                    texto_completo += texto_pagina
    except Exception as e:
        print(f"Erro ao ler o PDF '{caminho_pdf}': {e}")
        return None
    return texto_completo

def extrair_informacoes_recebimento(texto, nome_arquivo):
    """
    Extrai informações de um PDF de recebimento e mapeia para um leiaute fiscal.
    """
    dados = {}
    divergencias = []

    def get_value(pattern, default='', group=1, campo_nome=''):
        match = re.search(pattern, texto, re.DOTALL)
        valor = match.group(group).strip().upper() if match else default.upper()
        if not valor and campo_nome:
            divergencias.append(f"  - {campo_nome}: Não encontrado")
        return valor
        
    def get_float_value(pattern, default=0.0, campo_nome=''):
        match = re.search(pattern, texto)
        if match:
            return float(match.group(1).strip().replace('.', '').replace(',', '.'))
        if campo_nome:
            divergencias.append(f"  - {campo_nome}: Não encontrado")
        return default

    def formatar_data(data_extenso):
        if not data_extenso:
            return ''
        
        meses = {
            'JANEIRO': '01', 'FEVEREIRO': '02', 'MARÇO': '03', 'ABRIL': '04',
            'MAIO': '05', 'JUNHO': '06', 'JULHO': '07', 'AGOSTO': '08',
            'SETEMBRO': '09', 'OUTUBRO': '10', 'NOVEMBRO': '11', 'DEZEMBRO': '12'
        }
        
        # A string já está em maiúsculas por causa da função get_value
        match = re.search(r'(\d{2})\s+DE\s+([A-ZÇ]+)\s+DE\s+(\d{4})', data_extenso)
        
        if match:
            dia, mes_nome, ano = match.groups()
            mes_num = meses.get(mes_nome, '00')
            return f"{dia}/{mes_num}/{ano}"
        
        return data_extenso

    try:
        # Usa os dados da ORIGINADORA para popular a planilha
        dados['Razão Social'] = get_value(r'ORIGINADORA:\s*(.*?)\s*CNPJ/CPF:', campo_nome='Razão Social')
        dados['CPF/CNPJ'] = get_value(r'CNPJ/CPF:\s*([\d./-]+)', campo_nome='CPF/CNPJ')
        
        # O endereço, UF e Município estão no bloco do REPRESENTANTE
        bloco_representante = get_value(r'REPRESENTANTE\(S\) LEGAL DA ORIGINADORA:\s*(.*?)(?=DEVEDOR SOLIDÁRIO:|FIEL DEPOSITÁRIO:)', default='')
        dados['UF'] = get_value(r', (\w{2}), telefone', default='', group=1, campo_nome='UF')
        dados['Município'] = get_value(r', ([\w\s]+), \w{2}, telefone', default='', group=1, campo_nome='Município')
        endereco = get_value(r'residente à\s*(.*?),\s*N/A', default='', campo_nome='Endereço')
        dados['Endereço'] = endereco.replace('\n', ' ').replace('\r', ' ').strip() if endereco else ''
        
        # Buscar número do documento da Declaração de Recebimento
        dados['Número Documento'] = get_value(r'Declaração de Recebimento N\.\s*(\d+)', campo_nome='Número Documento')
        
        # Ajuste para buscar e formatar a data
        data_extenso = get_value(r'LONDRINA\s*-\s*\w{2},\s*([\d\sde\w]+)', campo_nome='Data')
        dados['Data'] = formatar_data(data_extenso)
        if not dados['Data'] and data_extenso:
            divergencias.append(f"  - Data: Formato não reconhecido: '{data_extenso}'")
        
        # Valores
        valor_bordero = get_float_value(r'Total do Borderô\s*R\$\s*([\d.,]+)', campo_nome='Total do Borderô')
        valor_desagio = get_float_value(r'\(-\) Deságio\s*R\$\s*([\d.,]+)', campo_nome='Valor Deságio')

        # Mapeamento conforme novas regras
        dados['Valor Produtos'] = valor_bordero
        dados['Base de Calculo PIS/COFINS'] = valor_desagio
        
        # Valores padrão e fixos
        dados['Série'] = '1'
        dados['Situação (0- Regular / 2- Cancelada)'] = 0
        dados['Acumulador'] = 56
        dados['CFOP'] = '5949'
        dados['Valor Descontos'] = 0.00
        dados['Valor Contabil'] = valor_bordero
        
        # Impostos
        for imposto in ['ICMS', 'IPI']:
            dados[f'Base de Calculo {imposto}'] = 0.00
            dados[f'Aliquota {imposto}'] = 0.00
            dados[f'Valor {imposto}'] = 0.00
            dados[f'Outras {imposto}'] = 0.00
            dados[f'Isentas {imposto}'] = 0.00

        aliquota_pis = 0.65
        aliquota_cofins = 4.0
        base_calculo = dados['Base de Calculo PIS/COFINS']
        dados['Aliquota PIS'] = aliquota_pis
        dados['Valor PIS'] = round((base_calculo * aliquota_pis) / 100, 2)
        dados['Aliquota COFINS'] = aliquota_cofins
        dados['Valor COFINS'] = round((base_calculo * aliquota_cofins) / 100, 2)

        # Itens
        dados['Código do Item'] = '1'
        dados['Quantidade'] = 1
        dados['Valor Unitário'] = valor_bordero
        dados['CST PIS/COFINS'] = '02'
        
        return dados, divergencias

    except Exception as e:
        print(f"Erro ao processar o arquivo '{nome_arquivo}': {e}")
        return None, [f"Erro geral: {e}"]

def determinar_ano_mes_maior_registros(todos_os_dados):
    """
    Determina o ano/mês com maior número de registros.
    """
    if not todos_os_dados:
        return None
    
    # Contar registros por ano/mês
    contador_meses = Counter()
    
    for dados in todos_os_dados:
        if dados.get('Data'):
            try:
                # Converter data para datetime
                data = datetime.strptime(dados['Data'], '%d/%m/%Y')
                ano_mes = data.strftime('%Y-%m')
                contador_meses[ano_mes] += 1
            except ValueError:
                continue
    
    if not contador_meses:
        return None
    
    # Retornar o ano/mês com mais registros
    ano_mes_maior = contador_meses.most_common(1)[0][0]
    print(f"Ano/mês com maior número de registros: {ano_mes_maior} ({contador_meses[ano_mes_maior]} registros)")
    
    return ano_mes_maior

def main():
    # Configurar parser de argumentos
    parser = argparse.ArgumentParser(
        description='Gera planilha fiscal de recebimentos a partir de PDFs de CCB'
    )
    
    parser.add_argument(
        'diretorio',
        type=str,
        help='Diretório onde estão os arquivos PDF de recebimento'
    )
    
    # Parsear argumentos
    args = parser.parse_args()
    
    # Verificar se o diretório existe
    if not os.path.exists(args.diretorio):
        print(f"Erro: O diretório '{args.diretorio}' não existe.")
        sys.exit(1)
    
    if not os.path.isdir(args.diretorio):
        print(f"Erro: '{args.diretorio}' não é um diretório válido.")
        sys.exit(1)
    
    diretorio_pdfs = args.diretorio
    padrao_busca = os.path.join(diretorio_pdfs, 'RECEBIMENTO*.pdf')
    lista_arquivos_pdf = glob(padrao_busca)
    
    colunas_leiaute = [
        'CPF/CNPJ', 'Razão Social', 'UF', 'Município', 'Endereço', 'Número Documento', 
        'Série', 'Data', 'Situação (0- Regular / 2- Cancelada)', 'Acumulador', 'CFOP',
        'Valor Produtos', 'Valor Descontos', 'Valor Contabil', 'Base de Calculo ICMS', 
        'Aliquota ICMS', 'Valor ICMS', 'Outras ICMS', 'Isentas ICMS', 'Base de Calculo IPI',
        'Aliquota IPI', 'Valor IPI', 'Outras IPI', 'Isentas IPI', 'Código do Item', 
        'Quantidade', 'Valor Unitário', 'CST PIS/COFINS', 'Base de Calculo PIS/COFINS', 
        'Aliquota PIS', 'Valor PIS', 'Aliquota COFINS', 'Valor COFINS'
    ]

    if not lista_arquivos_pdf:
        print(f"Nenhum arquivo com o padrão 'RECEBIMENTO*.pdf' encontrado em '{diretorio_pdfs}'")
        return

    print(f"Encontrados {len(lista_arquivos_pdf)} arquivos. Processando...")

    todos_os_dados = []
    todas_divergencias = {}
    
    for pdf_path in lista_arquivos_pdf:
        nome_arquivo = os.path.basename(pdf_path)
        print(f"  - Processando: {nome_arquivo}")
        
        texto_pdf = extrair_texto_do_pdf(pdf_path)
        if not texto_pdf:
            todas_divergencias[nome_arquivo] = ["Erro: Não foi possível extrair texto do PDF"]
            continue

        dados_fiscais, divergencias = extrair_informacoes_recebimento(texto_pdf, nome_arquivo)
        if dados_fiscais:
            todos_os_dados.append(dados_fiscais)
            if divergencias:
                todas_divergencias[nome_arquivo] = divergencias
        else:
            todas_divergencias[nome_arquivo] = divergencias

    if todos_os_dados:
        # Determinar ano/mês com maior número de registros
        ano_mes = determinar_ano_mes_maior_registros(todos_os_dados)
        
        if not ano_mes:
            print("Não foi possível determinar o ano/mês. Usando data atual.")
            ano_mes = datetime.now().strftime('%Y-%m')
        
        nome_planilha = f"relatorio_recebimentos_fiscal_{ano_mes}.xlsx"
        caminho_completo = os.path.join(diretorio_pdfs, nome_planilha)
        
        print(f"\nSalvando dados dos recebimentos na planilha: '{caminho_completo}'...")
        df = pd.DataFrame(todos_os_dados)
        
        # Converter a coluna 'Data' para o formato de data para ordenação
        df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y')
        df = df.sort_values(by='Data')
        
        # Formatar a coluna 'Data' de volta para string no formato dd/mm/aaaa para exibição
        df['Data'] = df['Data'].dt.strftime('%d/%m/%Y')
        
        # Garantir que todas as colunas do leiaute existam
        for col in colunas_leiaute:
            if col not in df.columns:
                df[col] = ''
        
        # Reordenar colunas para o leiaute fiscal
        df = df[colunas_leiaute]

        df.to_excel(caminho_completo, index=False)
        print(f"Planilha com leiaute fiscal para recebimentos criada com sucesso em: {caminho_completo}")
    else:
        print("Nenhum dado foi extraído com sucesso. A planilha não será gerada.")

    # Relatório de divergências
    if todas_divergencias:
        print(f"\n{'='*60}")
        print("RELATÓRIO DE DIVERGÊNCIAS")
        print(f"{'='*60}")
        
        arquivos_com_divergencias = 0
        total_divergencias = 0
        
        for arquivo, divergencias in todas_divergencias.items():
            if divergencias:
                arquivos_com_divergencias += 1
                total_divergencias += len(divergencias)
                print(f"\n📄 {arquivo}:")
                for divergencia in divergencias:
                    print(divergencia)
        
        print(f"\n{'='*60}")
        print(f"RESUMO:")
        print(f"  - Arquivos processados: {len(lista_arquivos_pdf)}")
        print(f"  - Arquivos com divergências: {arquivos_com_divergencias}")
        print(f"  - Total de divergências encontradas: {total_divergencias}")
        print(f"  - Arquivos processados com sucesso: {len(todos_os_dados)}")
        print(f"{'='*60}")
    else:
        print(f"\n✅ Todos os {len(lista_arquivos_pdf)} arquivos foram processados sem divergências!")


if __name__ == "__main__":
    main() 