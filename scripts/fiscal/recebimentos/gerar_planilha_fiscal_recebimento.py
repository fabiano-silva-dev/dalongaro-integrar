#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import re
import os
import PyPDF2
import argparse
from glob import glob
from datetime import datetime
from collections import Counter

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

def converter_data_por_extenso(data_texto):
    """
    Converte data por extenso para formato dd/mm/aaaa
    """
    meses = {
        'janeiro': '01', 'fevereiro': '02', 'março': '03', 'abril': '04',
        'maio': '05', 'junho': '06', 'julho': '07', 'agosto': '08',
        'setembro': '09', 'outubro': '10', 'novembro': '11', 'dezembro': '12'
    }
    
    # Padrão para extrair dia, mês e ano
    padrao = r'(\d+)\s+de\s+(\w+)\s+de\s+(\d{4})'
    match = re.search(padrao, data_texto, re.IGNORECASE)
    
    if match:
        dia = match.group(1).zfill(2)
        mes_nome = match.group(2).lower()
        ano = match.group(3)
        
        if mes_nome in meses:
            mes = meses[mes_nome]
            return f"{dia}/{mes}/{ano}"
    
    return data_texto

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
            valor_limpo = match.group(1).strip().replace('.', '').replace(',', '.')
            return float(valor_limpo)
        return default

    try:
        # Extrair dados da originadora
        dados['Razão Social'] = get_value(r'ORIGINADORA:\s*(.*?)(?:\n|$)')
        dados['CPF/CNPJ'] = re.sub(r'[^\d]', '', get_value(r'CNPJ/CPF:\s*([\d./-]+)'))
        
        # Extrair dados do representante (nome, CPF, endereço)
        # Novo padrão flexível para capturar endereço mesmo com quebras de linha
        padrao_flexivel = r'residente à\s+([^,\n]+(?:\n[^,\n]+)?),\s*([^,]+),\s*([^,]+),\s*[\d-]+,\s*([^,]+),\s*([A-Z]{2})'
        match_representante = re.search(padrao_flexivel, texto)
        if match_representante:
            rua = match_representante.group(1).strip().upper().replace('\n', ' ').replace('\r', ' ')
            numero = match_representante.group(2).strip()
            bairro = match_representante.group(3).strip().upper()
            cidade = match_representante.group(4).strip().upper()
            uf = match_representante.group(5).strip().upper()
            dados['UF'] = uf
            dados['Município'] = cidade
            dados['Endereço'] = f"{rua}, {numero}".replace('\n', ' ').replace('\r', ' ')
        else:
            dados['UF'] = ''
            dados['Município'] = ''
            dados['Endereço'] = ''

        # Número do documento - padrão corrigido com múltiplas variações
        numero_match = re.search(r'Declaração de Recebimento\s+N\s*\.\s*(\d+)', texto)
        if not numero_match:
            numero_match = re.search(r'Declaração de Recebimento N\.?\s*(\d+)', texto)
        if not numero_match:
            numero_match = re.search(r'Declaração de Recebimento\s+N\s*(\d+)', texto)
        
        dados['Número Documento'] = numero_match.group(1).strip() if numero_match else ''
        
        # Data de recebimento - buscar padrão 'Cidade - UF, dd de <mês> de aaaa'
        data_match = re.search(r',\s*(\d{1,2}) de ([a-zç]+) de (\d{4})', texto, re.IGNORECASE)
        meses = {
            'janeiro': '01', 'fevereiro': '02', 'março': '03', 'marco': '03', 'abril': '04',
            'maio': '05', 'junho': '06', 'julho': '07', 'agosto': '08', 'setembro': '09',
            'outubro': '10', 'novembro': '11', 'dezembro': '12'
        }
        if data_match:
            dia = data_match.group(1).zfill(2)
            mes_nome = data_match.group(2).lower()
            ano = data_match.group(3)
            mes = meses.get(mes_nome, '01')
            dados['Data'] = f"{dia}/{mes}/{ano}"
        else:
            # Fallback para data atual
            agora = datetime.now()
            dados['Data'] = f"{agora.day:02d}/{agora.month:02d}/{agora.year}"
        
        # Valor líquido - padrão corrigido baseado no PDF real
        valor_liquido = get_float_value(r'Valor líquido\s*R\$\s*([\d.,]+)')
        if valor_liquido == 0.0:
            # Tentar outros padrões possíveis
            valor_liquido = get_float_value(r'Valor Líquido\s*R\$\s*([\d.,]+)')
        if valor_liquido == 0.0:
            valor_liquido = get_float_value(r'VALOR LÍQUIDO\s*R\$\s*([\d.,]+)')
        if valor_liquido == 0.0:
            valor_liquido = get_float_value(r'Valor:\s*R\$\s*([\d.,]+)')
        
        dados['Valor Contábil'] = valor_liquido
        
        # Valores padrão e fixos para campos não existentes no PDF
        dados['Série'] = ''  # Vazio conforme solicitado
        dados['Situação (0- Regular / 2- Cancelada)'] = 0
        dados['Acumulador'] = 57  # Novo valor conforme solicitado
        dados['CFOP'] = '1949'  # Novo CFOP conforme solicitado
        
        # Valores de produtos e descontos
        dados['Valor Produtos'] = valor_liquido
        dados['Valor Descontos'] = 0.00
        
        # Campos de impostos zerados
        for imposto in ['ICMS', 'IPI']:
            dados[f'Base de Calculo {imposto}'] = 0.00
            dados[f'Aliquota {imposto}'] = 0.00
            dados[f'Valor {imposto}'] = 0.00
            dados[f'Isentas {imposto}'] = 0.00

        # Outras ICMS igual ao valor contábil
        dados['Outras ICMS'] = valor_liquido
        dados['Outras IPI'] = 0.00

        # Campos de PIS/COFINS zerados
        dados['Base de Calculo PIS/COFINS'] = 0.00
        dados['Aliquota PIS'] = 0.00
        dados['Valor PIS'] = 0.00
        dados['Aliquota COFINS'] = 0.00
        dados['Valor COFINS'] = 0.00

        # Código do item vazio e demais campos sem informações
        dados['Código do Item'] = ''
        dados['Quantidade'] = 0
        dados['Valor Unitário'] = 0.00
        dados['CST PIS/COFINS'] = 0.00
        
        return dados

    except Exception as e:
        print(f"Erro ao processar o arquivo '{nome_arquivo}': {e}")
        return None

def obter_ano_mes_dominante(datas):
    """
    Obtém o ano e mês mais frequente nas datas dos registros.
    """
    if not datas:
        # Fallback para data atual se não houver datas
        agora = datetime.now()
        return f"{agora.year}-{agora.month:02d}"
    
    # Contar frequência de ano-mês
    ano_mes_contador = Counter()
    for data_str in datas:
        try:
            # Converter data DD/MM/YYYY para YYYY-MM
            data_obj = datetime.strptime(data_str, '%d/%m/%Y')
            ano_mes = f"{data_obj.year}-{data_obj.month:02d}"
            ano_mes_contador[ano_mes] += 1
        except:
            continue
    
    if ano_mes_contador:
        # Retornar o ano-mês mais frequente
        return ano_mes_contador.most_common(1)[0][0]
    else:
        # Fallback para data atual
        agora = datetime.now()
        return f"{agora.year}-{agora.month:02d}"

def main():
    # Configurar argumentos de linha de comando
    parser = argparse.ArgumentParser(description='Gera planilha fiscal a partir de PDFs de Recebimento')
    parser.add_argument('diretorio', help='Diretório onde estão os arquivos PDF de Recebimento')
    parser.add_argument('--padrao', default='RECEBIMENTO*.pdf', help='Padrão para buscar arquivos PDF (padrão: RECEBIMENTO*.pdf)')
    
    args = parser.parse_args()
    
    diretorio_pdfs = args.diretorio
    padrao_busca = os.path.join(diretorio_pdfs, args.padrao)
    
    # Verificar se o diretório existe
    if not os.path.exists(diretorio_pdfs):
        print(f"Erro: O diretório '{diretorio_pdfs}' não existe.")
        return
    
    if not os.path.isdir(diretorio_pdfs):
        print(f"Erro: '{diretorio_pdfs}' não é um diretório válido.")
        return
    
    lista_arquivos_pdf = glob(padrao_busca)

    if not lista_arquivos_pdf:
        print(f"Nenhum arquivo com o padrão '{args.padrao}' encontrado em '{diretorio_pdfs}'")
        return

    print(f"Encontrados {len(lista_arquivos_pdf)} arquivos de Recebimento:")
    print("=" * 60)
    
    # Listar todos os arquivos encontrados
    for i, pdf_path in enumerate(lista_arquivos_pdf, 1):
        nome_arquivo = os.path.basename(pdf_path)
        print(f"{i:2d}. {nome_arquivo}")
    
    print("=" * 60)
    print("Processando documentos para extrair informações...")
    print()

    todos_os_dados = []
    datas_coletadas = []
    
    for pdf_path in lista_arquivos_pdf:
        nome_arquivo = os.path.basename(pdf_path)
        print(f"  - Processando: {nome_arquivo}")
        
        texto_pdf = extrair_texto_do_pdf(pdf_path)
        if not texto_pdf:
            continue

        dados_fiscais = extrair_informacoes_fiscais(texto_pdf, nome_arquivo)
        if dados_fiscais:
            todos_os_dados.append(dados_fiscais)
            if dados_fiscais['Data']:
                datas_coletadas.append(dados_fiscais['Data'])
            
            # Mostrar informações básicas do documento
            print(f"    ✓ Número Recebimento: {dados_fiscais['Número Documento']}")
            print(f"    ✓ Cliente: {dados_fiscais['Razão Social']}")
            print(f"    ✓ Data: {dados_fiscais['Data']}")
            print(f"    ✓ Valor Contábil: R$ {dados_fiscais['Valor Contábil']:,.2f}")
            print(f"    ✓ CFOP: {dados_fiscais['CFOP']}")
            print()
        else:
            print(f"    ✗ Erro ao extrair dados do arquivo")

    if not todos_os_dados:
        print("Nenhum dado foi extraído com sucesso. A planilha não será gerada.")
        return

    print(f"\nResumo: {len(todos_os_dados)} documentos processados com sucesso")
    print("=" * 60)

    # Gerar ano-mês baseado na maioria das datas dos registros
    ano_mes = obter_ano_mes_dominante(datas_coletadas)
    print(f"Ano-mês dominante nas datas: {ano_mes}")
    
    # Criar DataFrame com as colunas especificadas
    df = pd.DataFrame(todos_os_dados)
    
    colunas_finais = [
        'CPF/CNPJ', 'Razão Social', 'UF', 'Município', 'Endereço', 'Número Documento', 
        'Série', 'Data', 'Situação (0- Regular / 2- Cancelada)', 'Acumulador', 'CFOP',
        'Valor Produtos', 'Valor Descontos', 'Valor Contábil', 'Base de Calculo ICMS', 
        'Aliquota ICMS', 'Valor ICMS', 'Outras ICMS', 'Isentas ICMS', 'Base de Calculo IPI',
        'Aliquota IPI', 'Valor IPI', 'Outras IPI', 'Isentas IPI', 'Código do Item', 
        'Quantidade', 'Valor Unitário', 'CST PIS/COFINS', 'Base de Calculo PIS/COFINS', 
        'Aliquota PIS', 'Valor PIS', 'Aliquota COFINS', 'Valor COFINS'
    ]
    df = df.reindex(columns=colunas_finais)

    # Gerar arquivo dentro do diretório especificado
    output_path = os.path.join(diretorio_pdfs, f"relatorio_fiscal_recebimento_{ano_mes}.xlsx")
    print(f"\nSalvando dados fiscais na planilha: '{output_path}'...")
    df.to_excel(output_path, index=False)

    print("Planilha criada com sucesso!")

    # Relatório de divergências: arquivos sem número de documento
    divergentes = [(d, f) for d, f in zip(todos_os_dados, lista_arquivos_pdf) if not d.get('Número Documento')]
    if divergentes:
        print("\nATENÇÃO: Os seguintes arquivos NÃO tiveram o número do documento extraído:")
        for d, f in divergentes:
            print(f" - {d.get('Razão Social', '')} | Arquivo: {os.path.basename(f)}")
        print(f"Total de divergências: {len(divergentes)}")
    else:
        print("\nTodos os arquivos tiveram o número do documento extraído corretamente.")

if __name__ == "__main__":
    main() 