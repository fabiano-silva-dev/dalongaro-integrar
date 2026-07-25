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

    def get_value(pattern, default='', source_text=None):
        if source_text is None:
            source_text = texto
        match = re.search(pattern, source_text, re.IGNORECASE | re.DOTALL)
        # Converte todos os valores de texto para caixa alta
        return match.group(1).strip().upper() if match else default.upper()
        
    def get_float_value(pattern, default=0.0, source_text=None):
        if source_text is None:
            source_text = texto
        match = re.search(pattern, source_text, re.IGNORECASE | re.DOTALL)
        if match:
            # Limpa e converte o valor para float
            return float(match.group(1).strip().replace('.', '').replace(',', '.'))
        return default

    try:
        padrao_secao_emitente = re.search(r'QUADRO\s+I\s*[\u2013-]\s*QUALIFICAÇÃO\s+DO\s+EMITENTE(.*?)(?:QUADRO\s+I\.I|QUADRO\s+II|QUADRO\s+III|$)', texto, re.IGNORECASE | re.DOTALL)
        secao_emitente = padrao_secao_emitente.group(1) if padrao_secao_emitente else texto

        # Mapeamento dos campos do PDF para o leiaute fiscal (TUDO EM CAIXA ALTA)
        # Priorizar captura até a quebra de linha após o rótulo dentro do quadro do emitente
        razao_social = get_value(r'Nome:\s*([^\n\r]+)', source_text=secao_emitente)
        if not razao_social:
            razao_social = get_value(r'Raz[ãa]o\s+social:\s*([^\n\r]+)', source_text=secao_emitente)
        if not razao_social:
            razao_social = get_value(r'Raz[ãa]o\s+social:\s*(.*?)\s+\("EMITENTE"\)', source_text=secao_emitente)

        if razao_social:
            razao_social_limpo = re.sub(r'\("EMITENTE"\).*', '', razao_social, flags=re.IGNORECASE).strip()
            razao_social_limpo = re.sub(r'^\s*', '', razao_social_limpo)
            dados['Razão Social'] = razao_social_limpo.upper()
        else:
            dados['Razão Social'] = ''
        
        # Extrair CPF/CNPJ - tentar primeiro CPF, depois CNPJ/ME dentro do quadro
        cpf_cnpj = get_value(r'CPF:\s*([\d.-]+)', source_text=secao_emitente)
        if not cpf_cnpj:
            cpf_cnpj = get_value(r'CNPJ/ME:\s*([\d./-]+)', source_text=secao_emitente)
        
        dados['CPF/CNPJ'] = re.sub(r'[^\d]', '', cpf_cnpj)

        cidade_uf_match = re.search(r'Cidade:\s*([^\n\r]*?)\s*UF:\s*([A-Z]{2})', secao_emitente, re.IGNORECASE)
        if cidade_uf_match:
            dados['Município'] = cidade_uf_match.group(1).strip().upper()
            dados['UF'] = cidade_uf_match.group(2).strip().upper()
        else:
            dados['Município'] = get_value(r'Cidade:\s*([^\n\r]+)', source_text=secao_emitente)
            dados['UF'] = get_value(r'UF:\s*([A-Z]{2})', source_text=secao_emitente)
        
        endereco_completo = get_value(r'(?:Endereço|Logradouro):\s*([^\n\r]+)', source_text=secao_emitente)
        match_endereco = re.search(r'(.*?),\s*([\d\w]+),', endereco_completo)
        dados['Endereço'] = match_endereco.group(1).strip() if match_endereco else endereco_completo

        dados['Número Documento'] = get_value(r'CÉDULA DE CRÉDITO BANCÁRIO Nº (\d+)')
        
        # 1. Data da planilha = Data de liberação do recurso
        dados['Data'] = get_value(r'Data de liberação do recurso: ([\d/]+)')
        
        # 3 e 4. Coleta de valores para os novos cálculos
        valor_total_parcelas = get_float_value(r'Valor Total das Parcelas: R\$\s*([\d.,]+)')
        preco_aquisicao = get_float_value(r'Preço de Aquisição:\s*R\$\s*([\d.,]+)')
        
        # Extrair quantidade de parcelas
        quantidade_parcelas = get_value(r'Quantidade de Parcelas:\s*(\d+)')
        if quantidade_parcelas == '':
            quantidade_parcelas = '1'  # Valor padrão se não encontrar
        
        dados['Valor Produtos'] = valor_total_parcelas
        dados['Preco Aquisicao'] = preco_aquisicao
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

        # 4. Base de Calculo PIS/COFINS = Valor Total das Parcelas - Preco Aquisicao
        base_calculo_pis_cofins = valor_total_parcelas - preco_aquisicao
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

def obter_ano_mes(dados_fiscais):
    """
    Determina o ano e mês baseado no mês com mais registros nos dados.
    """
    if not dados_fiscais:
        # Fallback para data atual se não houver dados
        agora = datetime.now()
        return f"{agora.year}-{agora.month:02d}"
    
    # Contar registros por mês
    contagem_meses = {}
    
    for dados in dados_fiscais:
        try:
            # Extrair data do formato DD/MM/AAAA
            data_str = dados.get('Data', '')
            if data_str and '/' in data_str:
                partes = data_str.split('/')
                if len(partes) == 3:
                    dia, mes, ano = partes
                    chave_mes = f"{ano}-{int(mes):02d}"
                    contagem_meses[chave_mes] = contagem_meses.get(chave_mes, 0) + 1
        except (ValueError, IndexError):
            continue
    
    if contagem_meses:
        # Encontrar o mês com mais registros
        mes_mais_registros = max(contagem_meses.items(), key=lambda x: x[1])[0]
        return mes_mais_registros
    else:
        # Fallback para data atual
        agora = datetime.now()
        return f"{agora.year}-{agora.month:02d}"

def main():
    # Configurar parser de argumentos
    parser = argparse.ArgumentParser(description='Gerar planilhas fiscais a partir de arquivos CCB PDF')
    parser.add_argument('diretorio_ou_zip', help='Diretório com PDFs de CCB ou arquivo .zip (será extraído)')
    parser.add_argument('--padrao', default='CCB*.pdf', help='Padrão de busca para os arquivos PDF (padrão: CCB*.pdf)')
    
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
    dados_resumidos = []
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
            print(f"    ✓ Preco Aquisicao: R$ {dados_fiscais['Preco Aquisicao']:,.2f}")
            print(f"    ✓ Parcelas: {dados_fiscais['Quantidade de Parcelas']}")
            
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
            
            # Dados para o arquivo resumido
            dados_resumidos.append({
                'Número Documento': dados_fiscais['Número Documento'],
                'Nome': dados_fiscais['Razão Social'],
                'Data': dados_fiscais['Data'],
                'Preco Aquisicao': dados_fiscais['Preco Aquisicao'],
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

    # Gerar ano-mês baseado nos dados
    ano_mes = obter_ano_mes(todos_os_dados)
    print(f"Ano-mês determinado: {ano_mes}")
    
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

    # Salvar no diretório informado
    output_path = os.path.join(diretorio_pdfs, f"relatorio_fiscal{ano_mes}.xlsx")
    print(f"\nSalvando dados fiscais na planilha: '{output_path}'...")
    df.to_excel(output_path, index=False)

    # Segunda planilha - Dados resumidos
    df_resumido = pd.DataFrame(dados_resumidos)
    output_resumido_path = os.path.join(diretorio_pdfs, f"relatorio_resumido{ano_mes}.xlsx")
    print(f"Salvando dados resumidos na planilha: '{output_resumido_path}'...")
    df_resumido.to_excel(output_resumido_path, index=False)

    print("Planilhas criadas com sucesso!")
    
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
            output_divergencias_path = os.path.join(diretorio_pdfs, f"relatorio_divergencias{ano_mes}.xlsx")
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