#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para importar arquivos no layout da Domínio Sistemas e gerar CSV
Layout: Lançamentos Contábeis em Lote
"""

import sys
import csv
import argparse
from datetime import datetime
from typing import List, Dict, Any
import os
from collections import defaultdict
import re


class DominioLayoutParser:
    """Parser para arquivos no layout da Domínio Sistemas"""
    
    def __init__(self):
        self.registros = []
        self.empresa_info = {}
        
    def parse_line(self, line: str) -> Dict[str, Any]:
        """Parse uma linha do arquivo baseado no identificador do registro"""
        if len(line) < 2:
            return None
            
        identificador = line[0:2]
        
        if identificador == "01":
            return self._parse_cabecalho(line)
        elif identificador == "02":
            return self._parse_dados_lote(line)
        elif identificador == "03":
            return self._parse_partidas_lancamentos(line)
        elif identificador == "04":
            return self._parse_rateios_gerenciais(line)
        elif identificador == "05":
            return self._parse_rateios_centro_custos(line)
        elif identificador == "99":
            return self._parse_finalizador(line)
        else:
            return {"tipo": "desconhecido", "linha": line.strip()}
    
    def _parse_cabecalho(self, line: str) -> Dict[str, Any]:
        """Parse registro 01 - Cabeçalho do Arquivo"""
        return {
            "tipo": "cabecalho",
            "identificador": line[0:2],
            "codigo_empresa": line[2:9],
            "cnpj_empresa": line[9:23],
            "data_inicial": line[23:33],
            "data_final": line[33:43],
            "valor_fixo_n": line[43:44],
            "tipo_nota": line[44:46],
            "constante": line[46:51],
            "sistema": line[51:52],
            "valor_fixo": line[52:54],
            "brancos": line[54:150]
        }
    
    def _parse_dados_lote(self, line: str) -> Dict[str, Any]:
        """Parse registro 02 - Dados do Lote"""
        return {
            "tipo": "dados_lote",
            "identificador": line[0:2],
            "codigo_sequencial": line[2:9],
            "tipo_lancamento": line[9:10],
            "data_lancamento": line[10:20],
            "usuario": line[20:50].strip(),
            "brancos": line[50:150]
        }
    
    def _parse_partidas_lancamentos(self, line: str) -> Dict[str, Any]:
        """Parse registro 03 - Partidas dos Lançamentos Contábeis"""
        return {
            "tipo": "partidas_lancamentos",
            "identificador": line[0:2],
            "codigo_sequencial": line[2:9],
            "conta_debito": line[9:16],
            "conta_credito": line[16:23],
            "valor_lancamento": line[23:38],
            "codigo_historico": line[38:45],
            "historico_complemento": line[45:557].strip(),
            "codigo_filial_matriz": line[557:564],
            "brancos": line[564:664]
        }
    
    def _parse_rateios_gerenciais(self, line: str) -> Dict[str, Any]:
        """Parse registro 04 - Rateios Gerenciais"""
        return {
            "tipo": "rateios_gerenciais",
            "identificador": line[0:2],
            "sequencial": line[2:9],
            "conta_debito": line[9:16],
            "conta_credito": line[16:23],
            "valor_lancamento": line[23:38],
            "brancos": line[38:100]
        }
    
    def _parse_rateios_centro_custos(self, line: str) -> Dict[str, Any]:
        """Parse registro 05 - Rateios por Centro de Custos"""
        return {
            "tipo": "rateios_centro_custos",
            "identificador": line[0:2],
            "sequencial": line[2:9],
            "centro_custo_debito": line[9:16],
            "centro_custo_credito": line[16:23],
            "valor_lancamento": line[23:38],
            "brancos": line[38:100]
        }
    
    def _parse_finalizador(self, line: str) -> Dict[str, Any]:
        """Parse registro 99 - Finalizador do Arquivo"""
        return {
            "tipo": "finalizador",
            "identificador": line[0:2],
            "finalizador": line[2:100]
        }
    
    def parse_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Parse arquivo completo e retorna lista de registros"""
        registros = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                conteudo = file.read()
                # Remove quebras de linha e espaços extras
                linhas = [linha.strip() for linha in conteudo.split('\n') if linha.strip()]
                
                for line_num, line in enumerate(linhas, 1):
                    if line.strip():  # Ignora linhas vazias
                        registro = self.parse_line(line)
                        if registro:
                            registro['linha_arquivo'] = line_num
                            registros.append(registro)
                            
        except UnicodeDecodeError:
            # Tenta com encoding diferente se UTF-8 falhar
            with open(file_path, 'r', encoding='latin-1') as file:
                conteudo = file.read()
                linhas = [linha.strip() for linha in conteudo.split('\n') if linha.strip()]
                
                for line_num, line in enumerate(linhas, 1):
                    if line.strip():
                        registro = self.parse_line(line)
                        if registro:
                            registro['linha_arquivo'] = line_num
                            registros.append(registro)
        
        return registros


def formatar_valor(valor_str: str) -> str:
    """Converte string de valor para formato brasileiro (formato 15,2)"""
    try:
        # Remove espaços e converte vírgula para ponto
        valor_limpo = valor_str.strip().replace(',', '.')
        valor_float = float(valor_limpo) / 100.0  # Divide por 100 pois o formato é 15,2
        
        # Formata no padrão brasileiro sem separador de milhares
        return f"{valor_float:.2f}".replace('.', ',')
    except (ValueError, AttributeError):
        return "0,00"


def formatar_data(data_str: str) -> str:
    """Formata data do formato dd/mm/aaaa"""
    try:
        if data_str.strip() and len(data_str.strip()) == 10:
            return data_str.strip()
        return data_str.strip()
    except:
        return data_str.strip()


def extrair_nome_empresa(historico: str) -> str:
    """Extrai o nome da empresa do histórico após o número da NF ou SERVIÇO TOMADO NESTA DATA"""
    try:
        # Primeiro, verifica se há números no início do histórico (novo padrão)
        historico_limpo = historico.strip()
        
        # Se o histórico começa com números, extrai o nome após os números
        if historico_limpo and historico_limpo[0].isdigit():
            nome_empresa = ""
            for i, char in enumerate(historico_limpo):
                if char.isdigit():
                    continue
                else:
                    nome_empresa = historico_limpo[i:].strip()
                    break
            return nome_empresa.upper()
        
        # Procura por "VLR REF NFE Nº" seguido de números e depois o nome (novo padrão)
        if "VLR REF NFE Nº" in historico:
            # Encontra a posição após "VLR REF NFE Nº"
            pos_vlr = historico.find("VLR REF NFE Nº")
            if pos_vlr != -1:
                # Pega o texto após "VLR REF NFE Nº"
                texto_apos_vlr = historico[pos_vlr + len("VLR REF NFE Nº"):].strip()
                
                # Remove os números do início (número da NF)
                nome_empresa = ""
                for i, char in enumerate(texto_apos_vlr):
                    if char.isdigit() or char in "°":
                        continue
                    else:
                        nome_empresa = texto_apos_vlr[i:].strip()
                        break
                
                # Remove "Nº" se ainda estiver no início do nome
                if nome_empresa.startswith("Nº"):
                    nome_empresa = nome_empresa[2:].strip()
                
                # Remove números no início se ainda houver
                while nome_empresa and (nome_empresa[0].isdigit() or nome_empresa[0] in "°"):
                    nome_empresa = nome_empresa[1:].strip()
                
                return nome_empresa.upper()
        
        # Procura por "PAGO SIMPLES NACIONAL REF" seguido de números e depois o nome (novo padrão)
        if "PAGO SIMPLES NACIONAL REF" in historico:
            # Encontra a posição após "PAGO SIMPLES NACIONAL REF"
            pos_pago = historico.find("PAGO SIMPLES NACIONAL REF")
            if pos_pago != -1:
                # Pega o texto após "PAGO SIMPLES NACIONAL REF"
                texto_apos_pago = historico[pos_pago + len("PAGO SIMPLES NACIONAL REF"):].strip()
                
                # Remove os números do início (número da referência)
                nome_empresa = ""
                for i, char in enumerate(texto_apos_pago):
                    if char.isdigit() or char in "°":
                        continue
                    else:
                        nome_empresa = texto_apos_pago[i:].strip()
                        break
                
                # Remove "Nº" se ainda estiver no início do nome
                if nome_empresa.startswith("Nº"):
                    nome_empresa = nome_empresa[2:].strip()
                
                # Remove números no início se ainda houver
                while nome_empresa and (nome_empresa[0].isdigit() or nome_empresa[0] in "°"):
                    nome_empresa = nome_empresa[1:].strip()
                
                return nome_empresa.upper()
        
        # Procura por "VENDAS DE MERCADORIAS NESTA DATA" seguido de números e depois o nome
        if "VENDAS DE MERCADORIAS NESTA DATA" in historico:
            # Encontra a posição após "VENDAS DE MERCADORIAS NESTA DATA"
            pos_vendas = historico.find("VENDAS DE MERCADORIAS NESTA DATA")
            if pos_vendas != -1:
                # Pega o texto após "VENDAS DE MERCADORIAS NESTA DATA"
                texto_apos_vendas = historico[pos_vendas + len("VENDAS DE MERCADORIAS NESTA DATA"):].strip()
                
                # Remove os números do início (número do documento)
                nome_empresa = ""
                for i, char in enumerate(texto_apos_vendas):
                    if char.isdigit() or char in "°":
                        continue
                    else:
                        nome_empresa = texto_apos_vendas[i:].strip()
                        break
                
                # Remove "Nº" se ainda estiver no início do nome
                if nome_empresa.startswith("Nº"):
                    nome_empresa = nome_empresa[2:].strip()
                
                # Remove números no início se ainda houver
                while nome_empresa and (nome_empresa[0].isdigit() or nome_empresa[0] in "°"):
                    nome_empresa = nome_empresa[1:].strip()
                
                return nome_empresa.upper()
        
        # Procura por "SERVIÇO TOMADO NESTA DATA" seguido de números e depois o nome
        if "SERVIÇO TOMADO NESTA DATA" in historico:
            # Encontra a posição após "SERVIÇO TOMADO NESTA DATA"
            pos_servico = historico.find("SERVIÇO TOMADO NESTA DATA")
            if pos_servico != -1:
                # Pega o texto após "SERVIÇO TOMADO NESTA DATA"
                texto_apos_servico = historico[pos_servico + len("SERVIÇO TOMADO NESTA DATA"):].strip()
                
                # Remove "N°" se existir
                if texto_apos_servico.startswith("N°"):
                    texto_apos_servico = texto_apos_servico[2:].strip()
                
                # Remove os números do início (número do documento)
                nome_empresa = ""
                for i, char in enumerate(texto_apos_servico):
                    if char.isdigit() or char in "°":
                        continue
                    else:
                        nome_empresa = texto_apos_servico[i:].strip()
                        break
                
                # Remove "Nº" se ainda estiver no início do nome
                if nome_empresa.startswith("Nº"):
                    nome_empresa = nome_empresa[2:].strip()
                
                # Remove números no início se ainda houver
                while nome_empresa and (nome_empresa[0].isdigit() or nome_empresa[0] in "°"):
                    nome_empresa = nome_empresa[1:].strip()
                
                return nome_empresa.upper()
        
        # Procura por "NF Nº" seguido de números e depois o nome (padrão mais específico)
        if "NF Nº" in historico:
            # Encontra a posição após "NF Nº"
            pos_nf = historico.find("NF Nº")
            if pos_nf != -1:
                # Pega o texto após "NF Nº"
                texto_apos_nf = historico[pos_nf + len("NF Nº"):].strip()
                
                # Remove os números do início (número da NF)
                nome_empresa = ""
                for i, char in enumerate(texto_apos_nf):
                    if char.isdigit() or char in "°":
                        continue
                    else:
                        nome_empresa = texto_apos_nf[i:].strip()
                        break
                
                # Remove "Nº" se ainda estiver no início do nome
                if nome_empresa.startswith("Nº"):
                    nome_empresa = nome_empresa[2:].strip()
                
                # Remove números no início se ainda houver
                while nome_empresa and (nome_empresa[0].isdigit() or nome_empresa[0] in "°"):
                    nome_empresa = nome_empresa[1:].strip()
                
                return nome_empresa.upper()
        
        # Procura por "NF" seguido de números e depois o nome (padrão original)
        if "NF" in historico:
            # Encontra a posição após "NF"
            pos_nf = historico.find("NF")
            if pos_nf != -1:
                # Pega o texto após "NF"
                texto_apos_nf = historico[pos_nf + 2:].strip()
                
                # Remove "N°" se existir
                if texto_apos_nf.startswith("N°"):
                    texto_apos_nf = texto_apos_nf[2:].strip()
                
                # Remove os números do início (número da NF)
                nome_empresa = ""
                for i, char in enumerate(texto_apos_nf):
                    if char.isdigit() or char in "°":
                        continue
                    else:
                        nome_empresa = texto_apos_nf[i:].strip()
                        break
                
                # Remove "Nº" se ainda estiver no início do nome
                if nome_empresa.startswith("Nº"):
                    nome_empresa = nome_empresa[2:].strip()
                
                # Remove números no início se ainda houver
                while nome_empresa and (nome_empresa[0].isdigit() or nome_empresa[0] in "°"):
                    nome_empresa = nome_empresa[1:].strip()
                
                return nome_empresa.upper()
    except:
        pass
    return ""


def remover_zeros_esquerda(valor: str) -> str:
    """Remove zeros à esquerda de uma string numérica"""
    try:
        return str(int(valor))
    except (ValueError, AttributeError):
        return valor


def extrair_numero_nota(historico: str) -> str:
    """Extrai o número da nota fiscal ou documento do histórico"""
    try:
        # Primeiro, verifica se há números no início do histórico (novo padrão)
        historico_limpo = historico.strip()
        
        # Se o histórico começa com números, extrai apenas os números do início
        if historico_limpo and historico_limpo[0].isdigit():
            numero_nota = ""
            for char in historico_limpo:
                if char.isdigit():
                    numero_nota += char
                else:
                    break
            return numero_nota
        
        # Procura por "VLR REF NFE Nº" seguido de números (novo padrão)
        if "VLR REF NFE Nº" in historico:
            # Encontra a posição após "VLR REF NFE Nº"
            pos_vlr = historico.find("VLR REF NFE Nº")
            if pos_vlr != -1:
                # Pega o texto após "VLR REF NFE Nº"
                texto_apos_vlr = historico[pos_vlr + len("VLR REF NFE Nº"):].strip()
                
                # Extrai apenas os números do início
                numero_nota = ""
                for char in texto_apos_vlr:
                    if char.isdigit():
                        numero_nota += char
                    else:
                        break
                return numero_nota
        
        # Procura por "PAGO SIMPLES NACIONAL REF" seguido de números (novo padrão)
        if "PAGO SIMPLES NACIONAL REF" in historico:
            # Encontra a posição após "PAGO SIMPLES NACIONAL REF"
            pos_pago = historico.find("PAGO SIMPLES NACIONAL REF")
            if pos_pago != -1:
                # Pega o texto após "PAGO SIMPLES NACIONAL REF"
                texto_apos_pago = historico[pos_pago + len("PAGO SIMPLES NACIONAL REF"):].strip()
                
                # Extrai apenas os números do início
                numero_nota = ""
                for char in texto_apos_pago:
                    if char.isdigit():
                        numero_nota += char
                    else:
                        break
                return numero_nota
        
        # Procura por "SERVIÇO TOMADO NESTA DATA" seguido de números
        if "SERVIÇO TOMADO NESTA DATA" in historico:
            # Encontra a posição após "SERVIÇO TOMADO NESTA DATA"
            pos_servico = historico.find("SERVIÇO TOMADO NESTA DATA")
            if pos_servico != -1:
                # Pega o texto após "SERVIÇO TOMADO NESTA DATA"
                texto_apos_servico = historico[pos_servico + len("SERVIÇO TOMADO NESTA DATA"):].strip()
                
                # Remove "N°" se existir
                if texto_apos_servico.startswith("N°"):
                    texto_apos_servico = texto_apos_servico[2:].strip()
                
                # Extrai apenas os números do início
                numero_nota = ""
                for char in texto_apos_servico:
                    if char.isdigit():
                        numero_nota += char
                    else:
                        break
                return numero_nota
        
        # Procura por "VENDAS DE MERCADORIAS NESTA DATA" seguido de números
        if "VENDAS DE MERCADORIAS NESTA DATA" in historico:
            # Encontra a posição após "VENDAS DE MERCADORIAS NESTA DATA"
            pos_vendas = historico.find("VENDAS DE MERCADORIAS NESTA DATA")
            if pos_vendas != -1:
                # Pega o texto após "VENDAS DE MERCADORIAS NESTA DATA"
                texto_apos_vendas = historico[pos_vendas + len("VENDAS DE MERCADORIAS NESTA DATA"):].strip()
                
                # Extrai apenas os números do início
                numero_nota = ""
                for char in texto_apos_vendas:
                    if char.isdigit():
                        numero_nota += char
                    else:
                        break
                return numero_nota
        
        # Procura por "NF Nº" seguido de números (padrão mais específico)
        if "NF Nº" in historico:
            # Encontra a posição após "NF Nº"
            pos_nf = historico.find("NF Nº")
            if pos_nf != -1:
                # Pega o texto após "NF Nº"
                texto_apos_nf = historico[pos_nf + len("NF Nº"):].strip()
                
                # Extrai apenas os números do início
                numero_nota = ""
                for char in texto_apos_nf:
                    if char.isdigit():
                        numero_nota += char
                    else:
                        break
                return numero_nota
        
        # Procura por "NF" seguido de números (padrão original como fallback)
        if "NF" in historico:
            # Encontra a posição após "NF"
            pos_nf = historico.find("NF")
            if pos_nf != -1:
                # Pega o texto após "NF"
                texto_apos_nf = historico[pos_nf + 2:].strip()
                
                # Remove "N°" se existir
                if texto_apos_nf.startswith("N°"):
                    texto_apos_nf = texto_apos_nf[2:].strip()
                
                # Extrai apenas os números do início
                numero_nota = ""
                for char in texto_apos_nf:
                    if char.isdigit():
                        numero_nota += char
                    else:
                        break
                return numero_nota
    except:
        pass
    return ""


def gerar_csv_02_03(registros: List[Dict[str, Any]], output_file: str, dados_enriquecimento: List[Dict[str, Any]] = None):
    """Gera CSV unindo registro 02 (lote) e 03 (partida) em uma linha, pelo código sequencial"""
    # Filtra registros 02 e 03
    lotes = [r for r in registros if r.get('tipo') == 'dados_lote']
    partidas = [r for r in registros if r.get('tipo') == 'partidas_lancamentos']

        # Indexa lotes por código sequencial
    lotes_dict = {l['codigo_sequencial']: l for l in lotes}

    # Define campos do CSV mantendo as descrições do layout original
    campos_02 = ['codigo_sequencial', 'tipo_lancamento', 'data_lancamento', 'usuario']
    campos_03 = ['conta_debito', 'conta_credito', 'valor_lancamento', 'codigo_historico', 'historico_complemento', 'codigo_filial_matriz']
    
    # Define campos finais mantendo as descrições do layout original
    campos = ['Código Sequencial', 'Tipo', 'Data do Lançamento', 'Usuário', 
              'Conta Débito', 'Conta Crédito', 'Valor do Lançamento', 'Código do Histórico', 
              'Histórico (Complemento)', 'Código da Filial/Matriz']
    
    # Adiciona campos de auditoria
    campos.extend(['Nome da Empresa', 'Número da Nota'])
    
    # Adiciona campos de enriquecimento se houver dados
    if dados_enriquecimento:
        campos.extend(['financeiro_conta_financeira', 'itens_conta', 'item_descricao', 'itens_centro_resultado'])

    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=campos, delimiter=';')
        writer.writeheader()
        
        for partida in partidas:
            cod_seq_partida = partida['codigo_sequencial']
            # O código do lote correspondente é o código da partida - 1
            cod_seq_lote = str(int(cod_seq_partida) - 1).zfill(7)
            lote = lotes_dict.get(cod_seq_lote, {})
            
            # Cria linha combinando dados do lote e da partida
            linha = {}
            
            # Adiciona campos do lote (registro 02) com nomes do layout original
            linha['Código Sequencial'] = lote.get('codigo_sequencial', '')
            linha['Tipo'] = lote.get('tipo_lancamento', '')
            linha['Data do Lançamento'] = lote.get('data_lancamento', '')
            linha['Usuário'] = lote.get('usuario', '')
            
            # Adiciona campos da partida (registro 03) com nomes do layout original
            linha['Conta Débito'] = partida.get('conta_debito', '')
            linha['Conta Crédito'] = partida.get('conta_credito', '')
            linha['Valor do Lançamento'] = partida.get('valor_lancamento', '')
            linha['Código do Histórico'] = partida.get('codigo_historico', '')
            linha['Histórico (Complemento)'] = partida.get('historico_complemento', '').upper()
            linha['Código da Filial/Matriz'] = partida.get('codigo_filial_matriz', '')
            
            # Extrai nome da empresa do histórico para auditoria
            historico = partida.get('historico_complemento', '')
            nome_empresa = extrair_nome_empresa(historico)
            linha['Nome da Empresa'] = nome_empresa
            
            # Extrai número da nota fiscal para auditoria
            numero_nota = extrair_numero_nota(historico)
            linha['Número da Nota'] = numero_nota
            
            # Remove zeros à esquerda da conta crédito
            if linha['Conta Crédito']:
                linha['Conta Crédito'] = remover_zeros_esquerda(linha['Conta Crédito'])
            
            # Formata valor e data
            if linha['Valor do Lançamento']:
                linha['Valor do Lançamento'] = formatar_valor(linha['Valor do Lançamento'])
            if linha['Data do Lançamento']:
                linha['Data do Lançamento'] = formatar_data(linha['Data do Lançamento'])
            
            # Adiciona dados de enriquecimento se disponível
            if dados_enriquecimento and numero_nota and nome_empresa:
                dados_enriquecidos = encontrar_dados_enriquecimento(numero_nota, nome_empresa, dados_enriquecimento)
                linha.update(dados_enriquecidos)
            
            writer.writerow(linha)


def gerar_csv_agrupado(registros: List[Dict[str, Any]], output_file: str, dados_enriquecimento: List[Dict[str, Any]] = None):
    """Gera CSV agrupado por nome da empresa com dados de enriquecimento"""
    # Agrupa por nome da empresa
    empresas_unicas = {}
    
    for registro in registros:
        nome_empresa = registro.get('Nome da Empresa', '').strip()
        if nome_empresa:
            # Se a empresa ainda não foi processada, busca dados de enriquecimento
            if nome_empresa not in empresas_unicas:
                dados_enriquecidos = {
                    'financeiro_conta_financeira': '',
                    'itens_conta': '',
                    'item_descricao': '',
                    'itens_centro_resultado': ''
                }
                
                # Se há dados de enriquecimento, procura por correspondência
                if dados_enriquecimento:
                    # Procura por qualquer registro que tenha essa empresa
                    for dado in dados_enriquecimento:
                        fornecedor_enriquecimento = dado.get('dados_principais_fornecedor/comprador', '').strip()
                        if comparar_strings_similaridade(nome_empresa, fornecedor_enriquecimento):
                            dados_enriquecidos['financeiro_conta_financeira'] = dado.get('financeiro_conta_financeira', '')
                            dados_enriquecidos['itens_conta'] = dado.get('itens_conta', '')
                            dados_enriquecidos['item_descricao'] = dado.get('item_descricao', '')
                            dados_enriquecidos['itens_centro_resultado'] = dado.get('itens_centro_resultado', '')
                            break
                
                empresas_unicas[nome_empresa] = dados_enriquecidos
    
    # Define campos do CSV
    campos = ['nome_empresa']
    if dados_enriquecimento:
        campos.extend(['financeiro_conta_financeira', 'itens_conta', 'item_descricao', 'itens_centro_resultado'])
    
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=campos, delimiter=';')
        writer.writeheader()
        
        for nome_empresa, dados in sorted(empresas_unicas.items()):
            linha = {'nome_empresa': nome_empresa}
            linha.update(dados)
            # Filtra apenas os campos presentes no cabeçalho
            linha_filtrada = {campo: linha.get(campo, '') for campo in campos}
            writer.writerow(linha_filtrada)


def gerar_csv_agrupado_do_csv(csv_file: str, output_file: str, dados_enriquecimento: List[Dict[str, Any]] = None):
    """Gera CSV agrupado a partir do CSV fiscal gerado"""
    # Lê o CSV fiscal
    registros_csv = []
    try:
        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file, delimiter=';')
            for row in reader:
                registros_csv.append(row)
    except Exception as e:
        print(f"Erro ao ler CSV fiscal: {e}")
        return
    
    # Agrupa por nome da empresa
    empresas_unicas = {}
    
    for registro in registros_csv:
        nome_empresa = registro.get('Nome da Empresa', '').strip()
        if nome_empresa:
            # Se a empresa ainda não foi processada, busca dados de enriquecimento
            if nome_empresa not in empresas_unicas:
                dados_enriquecidos = {
                    'financeiro_conta_financeira': '',
                    'itens_conta': '',
                    'item_descricao': '',
                    'itens_centro_resultado': ''
                }
                
                # Se há dados de enriquecimento, procura por correspondência
                if dados_enriquecimento:
                    # Procura por qualquer registro que tenha essa empresa
                    for dado in dados_enriquecimento:
                        fornecedor_enriquecimento = dado.get('dados_principais_fornecedor/comprador', '').strip()
                        if comparar_strings_similaridade(nome_empresa, fornecedor_enriquecimento):
                            dados_enriquecidos['financeiro_conta_financeira'] = dado.get('financeiro_conta_financeira', '')
                            dados_enriquecidos['itens_conta'] = dado.get('itens_conta', '')
                            dados_enriquecidos['item_descricao'] = dado.get('item_descricao', '')
                            dados_enriquecidos['itens_centro_resultado'] = dado.get('itens_centro_resultado', '')
                            break
                
                empresas_unicas[nome_empresa] = dados_enriquecidos
    
    # Define campos do CSV
    campos = ['nome_empresa']
    if dados_enriquecimento:
        campos.extend(['financeiro_conta_financeira', 'itens_conta', 'item_descricao', 'itens_centro_resultado'])
    
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=campos, delimiter=';')
        writer.writeheader()
        
        for nome_empresa, dados in sorted(empresas_unicas.items()):
            linha = {'nome_empresa': nome_empresa}
            linha.update(dados)
            # Filtra apenas os campos presentes no cabeçalho
            linha_filtrada = {campo: linha.get(campo, '') for campo in campos}
            writer.writerow(linha_filtrada)


def carregar_arquivo_enriquecimento(arquivo_path: str) -> List[Dict[str, Any]]:
    """Carrega arquivo CSV de enriquecimento com dados adicionais"""
    dados = []
    try:
        with open(arquivo_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file, delimiter=',')
            for row in reader:
                dados.append(row)
        print(f"Arquivo de enriquecimento carregado: {len(dados)} registros")
    except UnicodeDecodeError:
        # Tenta com encoding diferente se UTF-8 falhar
        with open(arquivo_path, 'r', encoding='latin-1') as file:
            reader = csv.DictReader(file, delimiter=',')
            for row in reader:
                dados.append(row)
        print(f"Arquivo de enriquecimento carregado: {len(dados)} registros")
    except Exception as e:
        print(f"Erro ao carregar arquivo de enriquecimento: {e}")
        return []
    
    return dados


def limpar_string_para_comparacao(texto: str) -> str:
    """Remove palavras comuns e caracteres especiais para comparação"""
    if not texto:
        return ""
    
    # Converte para maiúsculas e remove espaços extras
    texto_limpo = texto.upper().strip()
    
    # Remove palavras comuns que não são relevantes para comparação
    palavras_remover = [
        'LTDA', 'LTD', 'CIA', 'COMPANHIA', 'S/A', 'SA', 'ME', 'EPP', 'EIRELI',
        'SOCIEDADE', 'LIMITADA', 'ANONIMA', 'ANÔNIMA', 'COMERCIO', 'COMÉRCIO',
        'INDUSTRIA', 'INDÚSTRIA', 'SERVICOS', 'SERVIÇOS', 'COMERCIAL',
        'DISTRIBUIDORA', 'REPRESENTACOES', 'REPRESENTAÇÕES', 'IMPORTADORA',
        'EXPORTADORA', 'PRODUTOS', 'SISTEMAS', 'TECNOLOGIA', 'INFORMATICA',
        'INFORMÁTICA', 'CONSTRUTORA', 'ENGENHARIA', 'ARQUITETURA'
    ]
    
    for palavra in palavras_remover:
        # Remove a palavra completa (com espaços antes e depois)
        texto_limpo = re.sub(r'\b' + re.escape(palavra) + r'\b', '', texto_limpo)
    
    # Remove caracteres especiais e números
    texto_limpo = re.sub(r'[^\w\s]', '', texto_limpo)
    texto_limpo = re.sub(r'\d+', '', texto_limpo)
    
    # Remove espaços múltiplos e trim
    texto_limpo = re.sub(r'\s+', ' ', texto_limpo).strip()
    
    return texto_limpo


def comparar_strings_similaridade(str1: str, str2: str) -> bool:
    """Compara duas strings e retorna True se houver similaridade significativa"""
    if not str1 or not str2:
        return False
    
    # Limpa as strings para comparação
    str1_limpa = limpar_string_para_comparacao(str1)
    str2_limpa = limpar_string_para_comparacao(str2)
    
    if not str1_limpa or not str2_limpa:
        return False
    
    # Divide em palavras
    palavras1 = set(str1_limpa.split())
    palavras2 = set(str2_limpa.split())
    
    # Filtra palavras com menos de 3 caracteres
    palavras1 = {p for p in palavras1 if len(p) > 3}
    palavras2 = {p for p in palavras2 if len(p) > 3}
    
    if not palavras1 or not palavras2:
        return False
    
    # Calcula interseção
    intersecao = palavras1.intersection(palavras2)
    
    # Retorna True se houver pelo menos uma palavra em comum
    return len(intersecao) > 0


def encontrar_dados_enriquecimento(numero_nota: str, nome_empresa: str, dados_enriquecimento: List[Dict[str, Any]]) -> Dict[str, str]:
    """Encontra dados de enriquecimento baseado no número da nota e nome da empresa"""
    resultado = {
        'financeiro_conta_financeira': '',
        'itens_conta': '',
        'item_descricao': '',
        'itens_centro_resultado': ''
    }
    
    if not numero_nota or not dados_enriquecimento:
        return resultado
    
    for dado in dados_enriquecimento:
        numero_enriquecimento = dado.get('dados_principais_número', '').strip()
        fornecedor_enriquecimento = dado.get('dados_principais_fornecedor/comprador', '').strip()
        
        # Verifica se o número da nota é igual
        if numero_nota == numero_enriquecimento:
            # Verifica se há similaridade no nome da empresa
            if comparar_strings_similaridade(nome_empresa, fornecedor_enriquecimento):
                resultado['financeiro_conta_financeira'] = dado.get('financeiro_conta_financeira', '')
                resultado['itens_conta'] = dado.get('itens_conta', '')
                resultado['item_descricao'] = dado.get('item_descricao', '')
                resultado['itens_centro_resultado'] = dado.get('itens_centro_resultado', '')
                break
    
    return resultado


def main():
    parser = argparse.ArgumentParser(description='Importa arquivo Domínio Sistemas e gera CSV')
    parser.add_argument('arquivo_entrada', help='Caminho do arquivo de entrada no layout Domínio')
    parser.add_argument('arquivo_enriquecimento', nargs='?', help='Arquivo CSV de enriquecimento com dados adicionais (opcional)')
    parser.add_argument('-o', '--output', help='Arquivo CSV de saída (padrão: nome_entrada-fiscal.csv)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Modo verboso')
    
    args = parser.parse_args()
    
    # Verifica se arquivo existe
    if not os.path.exists(args.arquivo_entrada):
        print(f"Erro: Arquivo '{args.arquivo_entrada}' não encontrado.")
        sys.exit(1)
    
    # Carrega arquivo de enriquecimento se fornecido
    dados_enriquecimento = None
    if args.arquivo_enriquecimento:
        if not os.path.exists(args.arquivo_enriquecimento):
            print(f"Erro: Arquivo de enriquecimento '{args.arquivo_enriquecimento}' não encontrado.")
            sys.exit(1)
        dados_enriquecimento = carregar_arquivo_enriquecimento(args.arquivo_enriquecimento)
    
    # Define arquivo de saída
    if args.output:
        output_file = args.output
    else:
        # Pega o nome base do arquivo de entrada (sem extensão)
        nome_base = os.path.splitext(os.path.basename(args.arquivo_entrada))[0]
        # Pega o diretório do arquivo de entrada
        diretorio = os.path.dirname(args.arquivo_entrada)
        # Cria o nome do arquivo de saída
        output_file = os.path.join(diretorio, f"{nome_base}-fiscal.csv")
    
    print(f"Processando arquivo: {args.arquivo_entrada}")
    if args.arquivo_enriquecimento:
        print(f"Arquivo de enriquecimento: {args.arquivo_enriquecimento}")
    
    # Parse do arquivo
    parser_dominio = DominioLayoutParser()
    registros = parser_dominio.parse_file(args.arquivo_entrada)
    
    if args.verbose:
        print(f"Total de registros processados: {len(registros)}")
        
        # Estatísticas por tipo
        tipos = {}
        for registro in registros:
            tipo = registro.get('tipo', 'desconhecido')
            tipos[tipo] = tipos.get(tipo, 0) + 1
        
        print("\nEstatísticas por tipo de registro:")
        for tipo, count in tipos.items():
            print(f"  {tipo}: {count}")
    
    # Gera CSV principal
    gerar_csv_02_03(registros, output_file, dados_enriquecimento)
    
    # Gera CSV agrupado a partir do CSV gerado
    output_file_agrupado = output_file.replace('-fiscal.csv', '-agrupado.csv')
    if output_file_agrupado == output_file:  # Se não conseguiu substituir, adiciona sufixo
        output_file_agrupado = output_file.replace('.csv', '-agrupado.csv')
    gerar_csv_agrupado_do_csv(output_file, output_file_agrupado, dados_enriquecimento)
    print(f"CSV agrupado gerado com sucesso: {output_file_agrupado}")
    
    print(f"CSV gerado com sucesso: {output_file}")
    print(f"Total de linhas processadas: {len(registros)}")


if __name__ == "__main__":
    main() 