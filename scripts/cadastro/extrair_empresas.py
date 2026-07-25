#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para extrair dados de empresas de PDF e gerar CSV
Autor: Fabiano
Data: 2025
"""

import re
import csv
import sys
from pathlib import Path
import PyPDF2
import pdfplumber

def extrair_dados_empresa(texto):
    """
    Extrai os dados da empresa do texto extraído do PDF
    Ajustado para estrutura de duas colunas
    """
    dados = {}
    
    # Padrões para extração dos dados - ajustados para duas colunas
    padroes = {
        'codigo': r'Código:\s*(\d+)',
        'apelido': r'Apelido:\s*([^\n]+?)(?=\s*[A-Z][a-z]+:|$)',
        'nome': r'Nome:\s*([^\n]+?)(?=\s*[A-Z][a-z]+:|$)',
        'razao_social': r'Razão social:\s*([^\n]+?)(?=\s*[A-Z][a-z]+:|$)',
        'nome_fantasia': r'Nome fantasia:\s*([^\n]+?)(?=\s*[A-Z][a-z]+:|$)',
        'tipo_endereco': r'Tipo de endereço:\s*([^\n]*?)(?=\s*[A-Z][a-z]+:|$)',
        'endereco': r'Endereço:\s*([^\n]+?)(?=\s*[A-Z][a-z]+:|$)',
        'numero': r'Número:\s*([^\n]+?)(?=\s*[A-Z][a-z]+:|$)',
        'bairro': r'Bairro:\s*([^\n]+?)(?=\s*[A-Z][a-z]+:|$)',
        'complemento': r'Complemento:\s*([^\n]*?)(?=\s*[A-Z][a-z]+:|$)',
        'municipio': r'Município:\s*([^\n]+?)(?=\s*[A-Z][a-z]+:|$)',
        'uf': r'UF:\s*([^\n]+?)(?=\s*[A-Z][a-z]+:|$)',
        'cep': r'CEP:\s*([^\n]+?)(?=\s*[A-Z][a-z]+:|$)',
        'caixa_postal': r'Caixa postal:\s*([^\n]*?)(?=\s*[A-Z][a-z]+:|$)',
        'pais': r'País:\s*([^\n]+?)(?=\s*[A-Z][a-z]+:|$)',
        'telefone': r'Telefone:\s*([^\n]+?)(?=\s*[A-Z][a-z]+:|$)',
        'fax': r'Fax:\s*([^\n]*?)(?=\s*[A-Z][a-z]+:|$)',
        'email': r'E-mail:\s*([^\n]+?)(?=\s*[A-Z][a-z]+:|$)',
        'pagina_internet': r'Página na internet:\s*([^\n]*?)(?=\s*[A-Z][a-z]+:|$)',
        'cnpj_cpf': r'CNPJ/CPF/CEI/CAEPF:\s*([^\n]+?)(?=\s*[A-Z][a-z]+:|$)',
        'inscricao_estadual': r'Insc\. estadual:\s*([^\n]*?)(?=\s*[A-Z][a-z]+:|$)',
        'inscricao_municipal': r'Insc\. municipal:\s*([^\n]*?)(?=\s*[A-Z][a-z]+:|$)',
        'inscricao_junta_comercial': r'Insc\. Junta Comercial:\s*([^\n]+?)(?=\s*[A-Z][a-z]+:|$)',
        'inscricao_suframa': r'Insc\. Suframa:\s*([^\n]*?)(?=\s*[A-Z][a-z]+:|$)',
        'inscricao_sub_trib': r'Insc\. Sub\. Trib\.:\s*([^\n]*?)(?=\s*[A-Z][a-z]+:|$)',
        'data_inscricao': r'Data da inscrição:\s*(\d{2}/\d{2}/\d{4})',
        'natureza_juridica': r'Natureza Jurídica:\s*([^\n]+?)(?=\s*[A-Z][a-z]+:|$)',
        'contador': r'Contador:\s*([^\n]+?)(?=\s*[A-Z][a-z]+:|$)',
        'inicio_atividades': r'Início atividades:\s*(\d{2}/\d{2}/\d{4})',
        'cliente_desde': r'Cliente desde:\s*(\d{2}/\d{2}/\d{4})',
        'situacao': r'Situação:\s*([^\n]+?)(?=\s*[A-Z][a-z]+:|$)',
        'data_situacao': r'Data da situação:\s*([^\n]*?)(?=\s*[A-Z][a-z]+:|$)',
        'motivo': r'Motivo:\s*([^\n]+?)(?=\s*[A-Z][a-z]+:|$)',
        'duracao_contrato': r'Duração do contrato:\s*([^\n]+?)(?=\s*[A-Z][a-z]+:|$)',
        'data_contrato': r'Data:\s*([^\n]*?)(?=\s*[A-Z][a-z]+:|$)',
        'foro_comarca': r'Foro Comarca:\s*([^\n]*?)(?=\s*[A-Z][a-z]+:|$)',
        'cnae': r'CNAE 2\.3:\s*([^\n]+?)(?=\s*[A-Z][a-z]+:|$)',
        'cae': r'CAE:\s*([^\n]*?)(?=\s*[A-Z][a-z]+:|$)',
        'ramo_atividade': r'Ramo de atividade:\s*([^\n]+?)(?=\s*[A-Z][a-z]+:|$)',
        'responsavel_legal': r'Responsável Legal:\s*([^\n]+?)(?=\s*[A-Z][a-z]+:|$)',
        'outro_registro': r'Outro registro:\s*([^\n]+?)(?=\s*[A-Z][a-z]+:|$)',
        'registro': r'Registro:\s*([^\n]*?)(?=\s*[A-Z][a-z]+:|$)',
        'data_registro': r'Data de registro:\s*([^\n]*?)(?=\s*[A-Z][a-z]+:|$)',
        'capital_social': r'Capital social:\s*([^\n]*?)(?=\s*[A-Z][a-z]+:|$)',
        'data_capital': r'Data:\s*([^\n]*?)(?=\s*[A-Z][a-z]+:|$)',
        'sistema_licenciado': r'Sistema licenciado para\s*([^\n]+?)(?=\s*[A-Z][a-z]+:|$)'
    }
    
    # Extrair dados usando os padrões
    for campo, padrao in padroes.items():
        match = re.search(padrao, texto)
        if match:
            dados[campo] = match.group(1).strip()
        else:
            dados[campo] = ''
    
    return dados

def extrair_pdf_com_pdfplumber(caminho_pdf):
    """
    Extrai texto do PDF usando pdfplumber (mais eficaz para PDFs com texto)
    """
    try:
        with pdfplumber.open(caminho_pdf) as pdf:
            texto_completo = ""
            for pagina in pdf.pages:
                texto = pagina.extract_text()
                if texto:
                    texto_completo += texto + "\n"
        return texto_completo
    except Exception as e:
        print(f"Erro ao extrair com pdfplumber: {e}")
        return None

def extrair_pdf_com_pypdf2(caminho_pdf):
    """
    Extrai texto do PDF usando PyPDF2 (fallback)
    """
    try:
        with open(caminho_pdf, 'rb') as arquivo:
            leitor = PyPDF2.PdfReader(arquivo)
            texto_completo = ""
            for pagina in leitor.pages:
                texto = pagina.extract_text()
                if texto:
                    texto_completo += texto + "\n"
        return texto_completo
    except Exception as e:
        print(f"Erro ao extrair com PyPDF2: {e}")
        return None

def gerar_csv(dados_empresas, arquivo_saida):
    """
    Gera arquivo CSV com os dados das empresas
    """
    if not dados_empresas:
        print("Nenhum dado para gerar CSV")
        return
    
    # Definir campos do CSV - organizados por colunas
    campos = [
        # Coluna Esquerda
        'codigo', 'apelido', 'nome', 'razao_social', 'nome_fantasia',
        'tipo_endereco', 'endereco', 'numero', 'bairro', 'complemento',
        'municipio', 'uf', 'cep', 'caixa_postal', 'pais',
        'telefone', 'fax', 'email', 'pagina_internet',
        'cnpj_cpf', 'inscricao_estadual', 'inscricao_municipal', 'inscricao_junta_comercial',
        'inscricao_suframa', 'inscricao_sub_trib',
        # Coluna Direita
        'data_inscricao', 'natureza_juridica', 'contador', 'inicio_atividades',
        'cliente_desde', 'situacao', 'data_situacao', 'motivo',
        'duracao_contrato', 'data_contrato', 'foro_comarca',
        'cnae', 'cae', 'ramo_atividade', 'responsavel_legal',
        'outro_registro', 'registro', 'data_registro',
        'capital_social', 'data_capital', 'sistema_licenciado'
    ]
    
    try:
        with open(arquivo_saida, 'w', newline='', encoding='utf-8') as arquivo_csv:
            writer = csv.DictWriter(arquivo_csv, fieldnames=campos)
            writer.writeheader()
            writer.writerows(dados_empresas)
        
        print(f"CSV gerado com sucesso: {arquivo_saida}")
        print(f"Total de empresas processadas: {len(dados_empresas)}")
        
    except Exception as e:
        print(f"Erro ao gerar CSV: {e}")

def processar_pdf(caminho_pdf):
    """
    Processa o PDF e extrai dados das empresas
    """
    print(f"Processando PDF: {caminho_pdf}")
    
    # Tentar extrair com pdfplumber primeiro
    texto = extrair_pdf_com_pdfplumber(caminho_pdf)
    
    # Se falhar, tentar com PyPDF2
    if not texto:
        texto = extrair_pdf_com_pypdf2(caminho_pdf)
    
    if not texto:
        print("Não foi possível extrair texto do PDF")
        return []
    
    # Dividir o texto em seções de empresas
    # Assumindo que cada empresa começa com "Código:"
    secoes_empresas = re.split(r'(?=Código:)', texto)
    
    dados_empresas = []
    for secao in secoes_empresas:
        if secao.strip() and 'Código:' in secao:
            dados = extrair_dados_empresa(secao)
            if dados['codigo']:  # Só adicionar se tem código
                dados_empresas.append(dados)
                print(f"Empresa extraída: {dados['nome']} (Código: {dados['codigo']})")
    
    return dados_empresas

def main():
    """
    Função principal
    """
    if len(sys.argv) != 2:
        print("Uso: python extrair_empresas.py <caminho_do_pdf>")
        print("Exemplo: python extrair_empresas.py Empresas.pdf")
        sys.exit(1)
    
    caminho_pdf = sys.argv[1]
    
    if not Path(caminho_pdf).exists():
        print(f"Arquivo não encontrado: {caminho_pdf}")
        sys.exit(1)
    
    # Processar PDF
    dados_empresas = processar_pdf(caminho_pdf)
    
    if dados_empresas:
        # Gerar CSV
        arquivo_saida = "empresas_extraidas.csv"
        gerar_csv(dados_empresas, arquivo_saida)
        
        # Mostrar resumo
        print("\nResumo da extração:")
        for empresa in dados_empresas:
            print(f"- {empresa['nome']} ({empresa['cnpj_cpf']})")
    else:
        print("Nenhuma empresa foi extraída do PDF")

if __name__ == "__main__":
    main()
