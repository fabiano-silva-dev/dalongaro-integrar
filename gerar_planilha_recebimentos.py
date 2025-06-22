#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import re
import os
import PyPDF2
from glob import glob

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

    def get_value(pattern, default='', group=1):
        match = re.search(pattern, texto, re.DOTALL)
        return match.group(group).strip().upper() if match else default.upper()
        
    def get_float_value(pattern, default=0.0):
        match = re.search(pattern, texto)
        if match:
            return float(match.group(1).strip().replace('.', '').replace(',', '.'))
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
        dados['Razão Social'] = get_value(r'ORIGINADORA:\s*(.*?)\s*CNPJ/CPF:')
        dados['CPF/CNPJ'] = get_value(r'CNPJ/CPF:\s*([\d./-]+)')
        
        # O endereço, UF e Município estão no bloco do REPRESENTANTE
        bloco_representante = get_value(r'REPRESENTANTE\(S\) LEGAL DA ORIGINADORA:\s*(.*?)(?=DEVEDOR SOLIDÁRIO:|FIEL DEPOSITÁRIO:)', default='')
        dados['UF'] = get_value(r', (\w{2}), telefone', default='', group=1)
        dados['Município'] = get_value(r', ([\w\s]+), \w{2}, telefone', default='', group=1)
        dados['Endereço'] = get_value(r'residente à\s*(.*?),\s*N/A', default='')
        
        # Ajuste para buscar apenas o número do documento do aditivo
        dados['Número Documento'] = get_value(r'documento_aditivo_operacao_(\d+)\.doc')
        
        # Ajuste para buscar e formatar a data
        data_extenso = get_value(r'LONDRINA\s*-\s*\w{2},\s*([\d\sde\w]+)')
        dados['Data'] = formatar_data(data_extenso)
        
        # Valores
        valor_liquido = get_float_value(r'Valor líquido\s*R\$\s*([\d.,]+)')
        valor_desagio = get_float_value(r'\(-\) Deságio\s*R\$\s*([\d.,]+)')

        # Mapeamento conforme novas regras
        dados['Valor Produtos'] = valor_liquido
        dados['Base de Calculo PIS/COFINS'] = valor_desagio
        
        # Valores padrão e fixos
        dados['Série'] = '1'
        dados['Situação (0- Regular / 2- Cancelada)'] = 0
        dados['Acumulador'] = 56
        dados['CFOP'] = '5949'
        dados['Valor Descontos'] = 0.00
        dados['Valor Contabil'] = valor_liquido
        
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
        dados['Valor Unitário'] = valor_liquido
        dados['CST PIS/COFINS'] = '02'
        
        return dados

    except Exception as e:
        print(f"Erro ao processar o arquivo '{nome_arquivo}': {e}")
        return None

def main():
    diretorio_pdfs = "credita/CCB CLIENTES 05.2025/"
    padrao_busca = os.path.join(diretorio_pdfs, 'RECEBIMENTO*.pdf')
    lista_arquivos_pdf = glob(padrao_busca)
    
    # Extrair ano e mês do nome do diretório
    ano_mes = "2025-04"  # Baseado no diretório "CCB CLIENTES 04.2025"
    nome_planilha = f"relatorio_recebimentos_fiscal_{ano_mes}.xlsx"

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
    for pdf_path in lista_arquivos_pdf:
        nome_arquivo = os.path.basename(pdf_path)
        print(f"  - Processando: {nome_arquivo}")
        
        texto_pdf = extrair_texto_do_pdf(pdf_path)
        if not texto_pdf:
            continue

        dados_fiscais = extrair_informacoes_recebimento(texto_pdf, nome_arquivo)
        if dados_fiscais:
            todos_os_dados.append(dados_fiscais)

    if todos_os_dados:
        print(f"\nSalvando dados dos recebimentos na planilha: '{nome_planilha}'...")
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

        df.to_excel(nome_planilha, index=False)
        print("Planilha com leiaute fiscal para recebimentos criada com sucesso!")
    else:
        print("Nenhum dado foi extraído com sucesso. A planilha não será gerada.")


if __name__ == "__main__":
    main() 