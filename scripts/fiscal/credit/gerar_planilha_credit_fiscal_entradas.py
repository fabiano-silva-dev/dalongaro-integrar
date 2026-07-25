#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import re
import os
import zipfile
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
        # Extrair dados do emitente do contrato
        # Padrão para encontrar os dados do emitente
        padrao_emitente = r'Pela presente CÉDULA DE CRÉDITO BANCÁRIO.*?o EMITENTE promete pagar a\s+(.*?),\s+inscrita no CNPJ nº\.\s*([\d./-]+).*?com sede na\s+(.*?),\s+nº\s*([\d\w]+).*?Bairro\s+(\w+).*?CEP\s*([\d-]+),\s+(.*?)\s+-\s+(\w+)'
        
        match_emitente = re.search(padrao_emitente, texto, re.DOTALL)
        
        if match_emitente:
            dados['Razão Social'] = match_emitente.group(1).strip().upper()
            dados['CPF/CNPJ'] = re.sub(r'[^\d]', '', match_emitente.group(2))
            endereco_completo = match_emitente.group(3).strip().upper()
            numero = match_emitente.group(4).strip()
            bairro = match_emitente.group(5).strip().upper()
            cidade = match_emitente.group(7).strip().upper()
            uf = match_emitente.group(8).strip().upper()
            
            dados['UF'] = uf
            dados['Município'] = cidade
            # Endereço sem CEP e sem quebras de linha
            dados['Endereço'] = f"{endereco_completo}, {numero}, {bairro}".replace('\n', ' ').replace('\r', ' ')
        else:
            # Fallback para o padrão anterior se não encontrar o novo formato
            # Tentar primeiro o formato "Razão social: NOME CPF ("EMITENTE")"
            razao_social = get_value(r'Razão social: (.*?)\s+\d+\s+\("EMITENTE"\)')
            if not razao_social:
                # Fallback para o formato "Nome: NOME ("EMITENTE")"
                razao_social = get_value(r'Nome: (.*?)\s+\("EMITENTE"\)')
            
            dados['Razão Social'] = razao_social
            
            # Extrair CPF/CNPJ - tentar primeiro CPF, depois CNPJ/ME
            cpf_cnpj = get_value(r'CPF: ([\d.-]+)')
            if not cpf_cnpj:
                cpf_cnpj = get_value(r'CNPJ/ME: ([\d./-]+)')
            
            dados['CPF/CNPJ'] = re.sub(r'[^\d]', '', cpf_cnpj)
            dados['UF'] = get_value(r'UF: (\w+)')
            dados['Município'] = get_value(r'Cidade: (.*?)\s+UF:')
            
            endereco_completo = get_value(r'Endereço: (.*?)\n')
            match_endereco = re.search(r'(.*?),\s*([\d\w]+),', endereco_completo)
            dados['Endereço'] = match_endereco.group(1).strip() if match_endereco else endereco_completo

        # Número do documento
        dados['Número Documento'] = get_value(r'CÉDULA DE CRÉDITO BANCÁRIO Nº (\d+)')
        
        # Data de liberação do recurso
        dados['Data'] = get_value(r'Data de liberação do recurso: ([\d/]+)')
        
        # Valor do crédito (Valor Contábil)
        preco_aquisicao = get_float_value(r'Preço de Aquisição:\s*R\$\s*([\d.,]+)')
        dados['Valor Contábil'] = preco_aquisicao
        
        # Valores padrão e fixos para campos não existentes no PDF
        dados['Série'] = ''  # Vazio conforme solicitado
        dados['Situação (0- Regular / 2- Cancelada)'] = 0
        dados['Acumulador'] = 58  # Novo valor conforme solicitado
        dados['CFOP'] = '2933'  # Novo CFOP conforme solicitado
        
        # Valores de produtos e descontos
        dados['Valor Produtos'] = preco_aquisicao
        dados['Valor Descontos'] = 0.00
        
        # Campos de impostos zerados
        for imposto in ['ICMS', 'IPI']:
            dados[f'Base de Calculo {imposto}'] = 0.00
            dados[f'Aliquota {imposto}'] = 0.00
            dados[f'Valor {imposto}'] = 0.00
            dados[f'Isentas {imposto}'] = 0.00

        # Outras ICMS igual ao valor contábil
        dados['Outras ICMS'] = preco_aquisicao
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
    parser = argparse.ArgumentParser(description='Gera planilha fiscal a partir de PDFs de CCB')
    parser.add_argument('diretorio_ou_zip', help='Diretório com PDFs de CCB ou arquivo .zip (será extraído)')
    parser.add_argument('--padrao', default='CCB*.pdf', help='Padrão para buscar arquivos PDF (padrão: CCB*.pdf)')
    
    args = parser.parse_args()
    
    diretorio_pdfs = args.diretorio_ou_zip

    # Se for um arquivo .zip, extrair para um diretório e usar esse diretório
    if os.path.isfile(diretorio_pdfs) and diretorio_pdfs.lower().endswith('.zip'):
        base_zip = os.path.abspath(diretorio_pdfs)
        nome_sem_ext = os.path.splitext(os.path.basename(base_zip))[0]
        dir_pai = os.path.dirname(base_zip)
        dir_extract = os.path.join(dir_pai, nome_sem_ext)
        if not os.path.isdir(dir_extract):
            os.makedirs(dir_extract, exist_ok=True)
            print(f"Extraindo '{os.path.basename(base_zip)}' para '{dir_extract}'...")
            with zipfile.ZipFile(base_zip, 'r') as z:
                z.extractall(dir_extract)
        diretorio_pdfs = dir_extract
        # Se dentro do extraído houver só uma pasta (ex.: zip com "CCB CLIENTES 01.2026/"), usar essa pasta
        itens = [x for x in os.listdir(diretorio_pdfs) if not x.startswith('.')]
        if len(itens) == 1:
            unico = os.path.join(diretorio_pdfs, itens[0])
            if os.path.isdir(unico):
                diretorio_pdfs = unico

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
    datas_coletadas = []
    divergencias = []
    clientes_nao_identificados = []
    
    for pdf_path in lista_arquivos_pdf:
        nome_arquivo = os.path.basename(pdf_path)
        print(f"  - Processando: {nome_arquivo}")
        
        texto_pdf = extrair_texto_do_pdf(pdf_path)
        if not texto_pdf:
            continue

        dados_fiscais = extrair_informacoes_fiscais(texto_pdf, nome_arquivo)
        if dados_fiscais:
            todos_os_dados.append(dados_fiscais)
            datas_coletadas.append(dados_fiscais['Data'])
            
            # Verificar campos obrigatórios
            campos_obrigatorios = ['Razão Social', 'CPF/CNPJ', 'Município', 'UF', 'Endereço']
            campos_faltando = []
            
            for campo in campos_obrigatorios:
                valor = dados_fiscais.get(campo, '')
                if not valor or valor.strip() == '':
                    campos_faltando.append(campo)
                    if campo == 'Razão Social':
                        clientes_nao_identificados.append({
                            'Arquivo': nome_arquivo,
                            'Número CCB': dados_fiscais.get('Número Documento', ''),
                        })

            # Mostrar informações básicas do documento
            print(f"    ✓ Número CCB: {dados_fiscais['Número Documento']}")
            print(f"    ✓ Cliente: {dados_fiscais['Razão Social']}")
            print(f"    ✓ Data: {dados_fiscais['Data']}")
            print(f"    ✓ Valor Contábil: R$ {dados_fiscais['Valor Contábil']:,.2f}")
            print(f"    ✓ CFOP: {dados_fiscais['CFOP']}")
            
            # Registrar divergências se houver
            if campos_faltando:
                divergencias.append({
                    'Arquivo': nome_arquivo,
                    'Número CCB': dados_fiscais['Número Documento'],
                    'Cliente': dados_fiscais['Razão Social'],
                    'Campos Faltando': ', '.join(campos_faltando)
                })
                print(f"    ⚠ Campos não encontrados: {', '.join(campos_faltando)}")
            
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
    output_path = os.path.join(diretorio_pdfs, f"relatorio_fiscal_entradas_{ano_mes}.xlsx")
    print(f"\nSalvando dados fiscais na planilha: '{output_path}'...")
    df.to_excel(output_path, index=False)

    print("Planilha criada com sucesso!")
    
    # Relatório de divergências
    if divergencias:
        print("\n" + "=" * 80)
        print("RELATÓRIO DE DIVERGÊNCIAS - CAMPOS NÃO ENCONTRADOS")
        print("=" * 80)
        
        for i, div in enumerate(divergencias, 1):
            print(f"\n{i}. Arquivo: {div['Arquivo']}")
            print(f"   Número CCB: {div['Número CCB']}")
            print(f"   Cliente: {div['Cliente']}")
            print(f"   Campos faltando: {div['Campos Faltando']}")
        
        print(f"\nTotal de documentos com divergências: {len(divergencias)}")
        
        # Salvar relatório de divergências
        if divergencias:
            df_divergencias = pd.DataFrame(divergencias)
            output_divergencias_path = os.path.join(diretorio_pdfs, f"relatorio_divergencias_entradas_{ano_mes}.xlsx")
            print(f"\nSalvando relatório de divergências: '{output_divergencias_path}'...")
            df_divergencias.to_excel(output_divergencias_path, index=False)
    else:
        print("\n✓ Nenhuma divergência encontrada - todos os campos obrigatórios foram extraídos com sucesso!")

    if clientes_nao_identificados:
        print("\n" + "=" * 80)
        print("CLIENTES NÃO IDENTIFICADOS")
        print("=" * 80)

        for i, cliente in enumerate(clientes_nao_identificados, 1):
            print(f"\n{i}. Arquivo: {cliente['Arquivo']}")
            print(f"   Número CCB: {cliente['Número CCB']}")

        print(f"\nTotal de registros sem cliente identificado: {len(clientes_nao_identificados)}")
    else:
        print("\n✓ Todos os clientes foram identificados com sucesso!")


if __name__ == "__main__":
    main() 