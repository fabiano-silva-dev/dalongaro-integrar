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

def extrair_informacoes(texto, nome_arquivo):
    """
    Extrai informações específicas do texto de um PDF usando expressões regulares.
    """
    dados = {'Arquivo': nome_arquivo}

    try:
        # Extrair dados do cliente
        dados['Razão Social'] = re.search(r'Nome: (.*?)\s+\("EMITENTE"\)', texto).group(1).strip()
        
        cpf_raw = re.search(r'CPF: ([\d.-]+)', texto).group(1).strip()
        dados['CPF/CNPJ'] = re.sub(r'[^\d]', '', cpf_raw)
        
        endereco_completo = re.search(r'Endereço: (.*?)\n', texto).group(1).strip()
        # Tenta separar o endereço, número e bairro
        match_endereco = re.search(r'(.*?),\s*([\d\w]+),\s*-\s*(.*)', endereco_completo)
        if match_endereco:
            dados['Endereço'] = match_endereco.group(1).strip()
            dados['Número Endereço'] = match_endereco.group(2).strip()
            dados['Bairro'] = match_endereco.group(3).strip()
        else:
            # Fallback se o padrão não corresponder
            dados['Endereço'] = endereco_completo
            dados['Número Endereço'] = ''
            dados['Bairro'] = ''

        dados['Município'] = re.search(r'Cidade: (.*?)\s+UF:', texto).group(1).strip()
        dados['UF'] = re.search(r'UF: (\w+)', texto).group(1).strip()
        dados['CEP'] = re.search(r'CEP: (\d{5}-?\d{3})', texto).group(1).strip()
        
        # Extrair telefone da página 13
        match_telefone = re.search(r'Telefone: \+?\s*55(\d{2})(\d{9})', texto)
        if match_telefone:
            ddd = match_telefone.group(1)
            numero = match_telefone.group(2)
            dados['Telefone'] = f"({ddd}) {numero[:5]}-{numero[5:]}"
        else:
            dados['Telefone'] = ''
            
        # Campos fixos ou não encontrados no PDF
        dados['C: cliente / F: Fornecedor'] = 'C'
        dados['Inscrição Estadual'] = ''
        dados['Inscrição Municipal'] = ''
        dados['Complemento Endereço'] = ''

    except AttributeError as e:
        print(f"Erro ao extrair dados do arquivo '{nome_arquivo}': uma informação esperada não foi encontrada. Pulando este arquivo.")
        return None

    return dados

def main():
    # Diretório contendo os arquivos PDF
    diretorio_pdfs = "credita/CCB CLIENTES 04.2025/"
    
    # Padrão para encontrar todos os arquivos PDF no diretório
    padrao_busca = os.path.join(diretorio_pdfs, '*.pdf')
    lista_arquivos_pdf = glob(padrao_busca)

    if not lista_arquivos_pdf:
        print(f"Nenhum arquivo PDF encontrado em '{diretorio_pdfs}'")
        return

    print(f"Encontrados {len(lista_arquivos_pdf)} arquivos PDF. Processando...")

    todos_os_dados = []
    for pdf_path in lista_arquivos_pdf:
        nome_arquivo = os.path.basename(pdf_path)
        print(f"  - Processando: {nome_arquivo}")
        
        texto_pdf = extrair_texto_do_pdf(pdf_path)
        if not texto_pdf:
            continue

        dados_cliente = extrair_informacoes(texto_pdf, nome_arquivo)
        if dados_cliente:
            todos_os_dados.append(dados_cliente)

    if not todos_os_dados:
        print("Nenhum dado foi extraído com sucesso. A planilha não será gerada.")
        return

    # Criar DataFrame do Pandas com todos os dados
    df = pd.DataFrame(todos_os_dados)
    
    # Reordenar colunas
    colunas_ordenadas = [
        'C: cliente / F: Fornecedor', 'Razão Social', 'CPF/CNPJ', 
        'Inscrição Estadual', 'Inscrição Municipal', 'UF', 'Município', 
        'Bairro', 'Endereço', 'Número Endereço', 'Complemento Endereço', 
        'CEP', 'Telefone', 'Arquivo'
    ]
    df = df[colunas_ordenadas]

    # Salvar em um único arquivo Excel
    output_path = "relatorio_clientes.xlsx"
    print(f"\nSalvando dados consolidados na planilha: '{output_path}'...")
    df.to_excel(output_path, index=False)

    print("Planilha consolidada criada com sucesso!")


if __name__ == "__main__":
    main() 