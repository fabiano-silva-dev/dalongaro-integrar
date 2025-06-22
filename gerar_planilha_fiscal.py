#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import re
import os
import PyPDF2
from glob import glob
from datetime import datetime

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

def extrair_informacoes_fiscais(texto, nome_arquivo):
    """
    Extrai informações do texto de um PDF e as mapeia para um leiaute fiscal.
    """
    dados = {}

    def get_value(pattern, default=''):
        match = re.search(pattern, texto)
        # Converte todos os valores de texto para caixa alta
        return match.group(1).strip().upper() if match else default.upper()
        
    def get_float_value(pattern, default=0.0):
        match = re.search(pattern, texto)
        if match:
            # Limpa e converte o valor para float
            return float(match.group(1).strip().replace('.', '').replace(',', '.'))
        return default

    try:
        # Mapeamento dos campos do PDF para o leiaute fiscal (TUDO EM CAIXA ALTA)
        dados['Razão Social'] = get_value(r'Nome: (.*?)\s+\("EMITENTE"\)')
        dados['CPF/CNPJ'] = re.sub(r'[^\d]', '', get_value(r'CPF: ([\d.-]+)'))
        dados['UF'] = get_value(r'UF: (\w+)')
        dados['Município'] = get_value(r'Cidade: (.*?)\s+UF:')
        
        endereco_completo = get_value(r'Endereço: (.*?)\n')
        match_endereco = re.search(r'(.*?),\s*([\d\w]+),', endereco_completo)
        dados['Endereço'] = match_endereco.group(1).strip() if match_endereco else endereco_completo

        dados['Número Documento'] = get_value(r'CÉDULA DE CRÉDITO BANCÁRIO Nº (\d+)')
        
        # 1. Data da planilha = Data de liberação do recurso
        dados['Data'] = get_value(r'Data de liberação do recurso: ([\d/]+)')
        
        # 3 e 4. Coleta de valores para os novos cálculos
        valor_total_parcelas = get_float_value(r'Valor Total das Parcelas: R\$\s*([\d.,]+)')
        valor_financiado = get_float_value(r'Valor Financiado:\s*([\d.,]+)')
        
        # Extrair quantidade de parcelas
        quantidade_parcelas = get_value(r'Quantidade de Parcelas:\s*(\d+)')
        if quantidade_parcelas == '':
            quantidade_parcelas = '1'  # Valor padrão se não encontrar
        
        dados['Valor Produtos'] = valor_total_parcelas
        dados['Valor Financiado'] = valor_financiado
        dados['Quantidade de Parcelas'] = quantidade_parcelas
        
        # Valores padrão e fixos para campos não existentes no PDF
        dados['Série'] = '1'
        dados['Situação (0- Regular / 2- Cancelada)'] = 0
        dados['Acumulador'] = 55
        # 2. CFOP fixo em 5949
        dados['CFOP'] = '5949'
        dados['Valor Descontos'] = 0.00
        dados['Valor Contabil'] = dados['Valor Produtos'] - dados['Valor Descontos']
        
        # Campos de impostos zerados
        for imposto in ['ICMS', 'IPI']:
            dados[f'Base de Calculo {imposto}'] = 0.00
            dados[f'Aliquota {imposto}'] = 0.00
            dados[f'Valor {imposto}'] = 0.00
            dados[f'Outras {imposto}'] = 0.00
            dados[f'Isentas {imposto}'] = 0.00

        # 4. Base de Calculo PIS/COFINS = Valor Total das Parcelas - Valor Financiado
        base_calculo_pis_cofins = valor_total_parcelas - valor_financiado
        dados['Base de Calculo PIS/COFINS'] = base_calculo_pis_cofins
        dados['Valor Deságio'] = base_calculo_pis_cofins
        
        # Alíquotas e Valores de PIS/COFINS
        aliquota_pis = 0.65
        aliquota_cofins = 4.0
        
        dados['Aliquota PIS'] = aliquota_pis
        dados['Valor PIS'] = round((base_calculo_pis_cofins * aliquota_pis) / 100, 2)
        
        dados['Aliquota COFINS'] = aliquota_cofins
        dados['Valor COFINS'] = round((base_calculo_pis_cofins * aliquota_cofins) / 100, 2)

        # Mapeamento de itens (simplificado)
        dados['Código do Item'] = '1'
        dados['Quantidade'] = 1
        dados['Valor Unitário'] = dados['Valor Produtos']
        dados['CST PIS/COFINS'] = '02'
        
        return dados

    except Exception as e:
        print(f"Erro ao processar o arquivo '{nome_arquivo}': {e}")
        return None

def obter_ano_mes():
    """
    Obtém o ano e mês atual para usar no nome do arquivo.
    """
    agora = datetime.now()
    return f"{agora.year}-{agora.month:02d}"

def main():
    diretorio_pdfs = "credita/CCB CLIENTES 05.2025/"
    padrao_busca = os.path.join(diretorio_pdfs, 'CCB*.pdf')
    lista_arquivos_pdf = glob(padrao_busca)

    if not lista_arquivos_pdf:
        print(f"Nenhum arquivo com o padrão 'CCB*.pdf' encontrado em '{diretorio_pdfs}'")
        return

    print(f"Encontrados {len(lista_arquivos_pdf)} arquivos CCB:")
    print("=" * 60)
    
    # Listar todos os arquivos encontrados
    for i, pdf_path in enumerate(lista_arquivos_pdf, 1):
        nome_arquivo = os.path.basename(pdf_path)
        print(f"{i:2d}. {nome_arquivo}")
    
    print("=" * 60)
    print("Processando documentos para extrair informações...")
    print()

    todos_os_dados = []
    dados_resumidos = []
    
    for pdf_path in lista_arquivos_pdf:
        nome_arquivo = os.path.basename(pdf_path)
        print(f"  - Processando: {nome_arquivo}")
        
        texto_pdf = extrair_texto_do_pdf(pdf_path)
        if not texto_pdf:
            continue

        dados_fiscais = extrair_informacoes_fiscais(texto_pdf, nome_arquivo)
        if dados_fiscais:
            todos_os_dados.append(dados_fiscais)
            
            # Mostrar informações básicas do documento
            print(f"    ✓ Número CCB: {dados_fiscais['Número Documento']}")
            print(f"    ✓ Cliente: {dados_fiscais['Razão Social']}")
            print(f"    ✓ Data: {dados_fiscais['Data']}")
            print(f"    ✓ Valor Financiado: R$ {dados_fiscais['Valor Financiado']:,.2f}")
            print(f"    ✓ Parcelas: {dados_fiscais['Quantidade de Parcelas']}")
            print()
            
            # Dados para o arquivo resumido
            dados_resumidos.append({
                'Número Documento': dados_fiscais['Número Documento'],
                'Nome': dados_fiscais['Razão Social'],
                'Data': dados_fiscais['Data'],
                'Valor Financiado': dados_fiscais['Valor Financiado'],
                'Valor Deságio': dados_fiscais['Valor Deságio'],
                'Quantidade de Parcelas': dados_fiscais['Quantidade de Parcelas']
            })
        else:
            print(f"    ✗ Erro ao extrair dados do arquivo")

    if not todos_os_dados:
        print("Nenhum dado foi extraído com sucesso. As planilhas não serão geradas.")
        return

    print(f"\nResumo: {len(todos_os_dados)} documentos processados com sucesso")
    print("=" * 60)

    # Gerar ano-mês para o nome do arquivo
    ano_mes = obter_ano_mes()
    
    # Primeira planilha - Leiaute fiscal completo
    df = pd.DataFrame(todos_os_dados)
    
    colunas_finais = [
        'CPF/CNPJ', 'Razão Social', 'UF', 'Município', 'Endereço', 'Número Documento', 
        'Série', 'Data', 'Situação (0- Regular / 2- Cancelada)', 'Acumulador', 'CFOP',
        'Valor Produtos', 'Valor Descontos', 'Valor Contabil', 'Base de Calculo ICMS', 
        'Aliquota ICMS', 'Valor ICMS', 'Outras ICMS', 'Isentas ICMS', 'Base de Calculo IPI',
        'Aliquota IPI', 'Valor IPI', 'Outras IPI', 'Isentas IPI', 'Código do Item', 
        'Quantidade', 'Valor Unitário', 'CST PIS/COFINS', 'Base de Calculo PIS/COFINS', 
        'Aliquota PIS', 'Valor PIS', 'Aliquota COFINS', 'Valor COFINS'
    ]
    df = df.reindex(columns=colunas_finais)

    output_path = f"relatorio_fiscal{ano_mes}.xlsx"
    print(f"\nSalvando dados fiscais na planilha: '{output_path}'...")
    df.to_excel(output_path, index=False)

    # Segunda planilha - Dados resumidos
    df_resumido = pd.DataFrame(dados_resumidos)
    output_resumido_path = f"relatorio_resumido{ano_mes}.xlsx"
    print(f"Salvando dados resumidos na planilha: '{output_resumido_path}'...")
    df_resumido.to_excel(output_resumido_path, index=False)

    print("Planilhas criadas com sucesso!")


if __name__ == "__main__":
    main() 