#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import re
import os
import PyPDF2
from glob import glob
import traceback

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

def extrair_informacoes_operacao(texto, nome_arquivo):
    """
    Extrai informações da operação financeira do texto de um PDF.
    """
    dados = {'Arquivo': nome_arquivo}

    def clean_value(value):
        return float(value.replace('.', '').replace(',', '.')) if value else 0.0

    try:
        # Dados de identificação
        dados['Cliente'] = re.search(r'Nome: (.*?)\s+\("EMITENTE"\)', texto).group(1).strip()
        cpf_raw = re.search(r'CPF: ([\d.-]+)', texto).group(1).strip()
        dados['CPF'] = re.sub(r'[^\d]', '', cpf_raw)

        # Dados da Operação (Quadro II)
        dados['Valor do Crédito'] = clean_value(re.search(r'Valor do Crédito: R\$\s*([\d.,]+)', texto).group(1))
        dados['Valor Entregue'] = clean_value(re.search(r'Valor Entregue ao Emitente: R\$\s*([\d.,]+)', texto).group(1))
        dados['Valor da Parcela'] = clean_value(re.search(r'Valor da Parcela: R\$\s*([\d.,]+)', texto).group(1))
        dados['Número de Parcelas'] = int(re.search(r'Número de Parcelas: (\d+)', texto).group(1))
        dados['Vencimento da Primeira Parcela'] = re.search(r'Vencimento da Primeira Parcela: ([\d/]+)', texto).group(1)
        dados['Vencimento da Última Parcela'] = re.search(r'Vencimento da Última Parcela: ([\d/]+)', texto).group(1)
        dados['Taxa de Juros a.m.'] = clean_value(re.search(r'Taxa de Juros % a\.m\.:\s*([\d.,]+)', texto).group(1))
        dados['Taxa de Juros a.a.'] = clean_value(re.search(r'Taxa de Juros % a\.a\.:\s*([\d.,]+)', texto).group(1))
        dados['CET a.a.'] = clean_value(re.search(r'Custo Efetivo Total \(CET\) % a\.a\.:\s*([\d.,]+)', texto).group(1))
        dados['IOF'] = clean_value(re.search(r'IOF: R\$\s*([\d.,]+)', texto).group(1))
        dados['Data de Liberação'] = re.search(r'Data de liberação do recurso: ([\d/]+)', texto).group(1)
        dados['Valor Total das Parcelas'] = clean_value(re.search(r'Valor Total das Parcelas: R\$\s*([\d.,]+)', texto).group(1))
        
        return dados

    except AttributeError as e:
        print(f"Erro ao extrair dados do arquivo '{nome_arquivo}': uma informação esperada não foi encontrada. Detalhes: {e}")
        # traceback.print_exc() # Descomente para depuração detalhada
        return None
    except Exception as e:
        print(f"Ocorreu um erro inesperado ao processar '{nome_arquivo}': {e}")
        return None


def main():
    diretorio_pdfs = "credita/CCB CLIENTES 04.2025/"
    padrao_busca = os.path.join(diretorio_pdfs, 'CCB*.pdf')
    lista_arquivos_pdf = glob(padrao_busca)

    if not lista_arquivos_pdf:
        print(f"Nenhum arquivo com o padrão 'CCB*.pdf' encontrado em '{diretorio_pdfs}'")
        return

    print(f"Encontrados {len(lista_arquivos_pdf)} arquivos. Processando...")

    todos_os_dados = []
    for pdf_path in lista_arquivos_pdf:
        nome_arquivo = os.path.basename(pdf_path)
        print(f"  - Processando: {nome_arquivo}")
        
        texto_pdf = extrair_texto_do_pdf(pdf_path)
        if not texto_pdf:
            continue

        dados_operacao = extrair_informacoes_operacao(texto_pdf, nome_arquivo)
        if dados_operacao:
            todos_os_dados.append(dados_operacao)

    if not todos_os_dados:
        print("Nenhum dado foi extraído com sucesso. A planilha não será gerada.")
        return

    df = pd.DataFrame(todos_os_dados)
    
    colunas_ordenadas = [
        'Cliente', 'CPF', 'Valor do Crédito', 'Valor Entregue', 'Valor da Parcela', 
        'Número de Parcelas', 'Vencimento da Primeira Parcela', 'Vencimento da Última Parcela',
        'Taxa de Juros a.m.', 'Taxa de Juros a.a.', 'CET a.a.', 'IOF', 'Data de Liberação',
        'Valor Total das Parcelas', 'Arquivo'
    ]
    df = df[colunas_ordenadas]

    output_path = "relatorio_operacoes.xlsx"
    print(f"\nSalvando dados das operações na planilha: '{output_path}'...")
    df.to_excel(output_path, index=False)

    print("Planilha de operações criada com sucesso!")


if __name__ == "__main__":
    main() 