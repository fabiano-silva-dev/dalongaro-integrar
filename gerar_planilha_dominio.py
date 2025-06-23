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
            "tipo_nota": line[43:45],
            "constante": line[45:50],
            "sistema": line[50:52],
            "valor_fixo": line[52:54]
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
            "brancos": line[82:182]
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
            "brancos": line[38:138]
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
            "brancos": line[38:138]
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
    """Extrai o nome da empresa do histórico após o número da NF"""
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
            return nome_empresa
        
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
                
                return nome_empresa
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
    """Extrai o número da nota fiscal do histórico"""
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
        
        # Procura por "NF" seguido de números (padrão original)
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


def gerar_csv_02_03(registros: List[Dict[str, Any]], output_file: str):
    """Gera CSV unindo registro 02 (lote) e 03 (partida) em uma linha, pelo código sequencial"""
    # Filtra registros 02 e 03
    lotes = [r for r in registros if r.get('tipo') == 'dados_lote']
    partidas = [r for r in registros if r.get('tipo') == 'partidas_lancamentos']

    print(f"Debug: {len(lotes)} lotes encontrados, {len(partidas)} partidas encontradas")

    # Indexa lotes por código sequencial
    lotes_dict = {l['codigo_sequencial']: l for l in lotes}
    
    print(f"Debug: Códigos sequenciais dos lotes: {list(lotes_dict.keys())}")
    print(f"Debug: Códigos sequenciais das partidas: {[p['codigo_sequencial'] for p in partidas]}")

    # Define campos do CSV com novos nomes de colunas
    campos_02 = ['codigo_sequencial', 'tipo_lancamento', 'data_lancamento', 'usuario']
    campos_03 = ['conta_debito', 'conta_credito', 'valor_lancamento', 'codigo_historico', 'historico_complemento', 'codigo_filial_matriz']
    
    # Mapeia os campos antigos para os novos nomes
    mapeamento_campos = {
        'codigo_sequencial': 'codigo_sequencial',
        'tipo_lancamento': 'tipo_lancamento',
        'data_lancamento': 'data_lancamento',
        'usuario': 'usuario',
        'conta_debito': 'Banco',
        'conta_credito': 'Fornecedor/Cliente',
        'valor_lancamento': 'valor_lancamento',
        'codigo_historico': 'codigo_historico',
        'historico_complemento': 'Histórico',
        'codigo_filial_matriz': 'codigo_filial_matriz',
        'numero_nota': 'numero_nota'
    }
    
    # Define campos finais com novos nomes
    campos = ['codigo_sequencial', 'tipo_lancamento', 'data_lancamento', 'usuario', 
              'Banco', 'Fornecedor/Cliente', 'valor_lancamento', 'codigo_historico', 
              'Histórico', 'codigo_filial_matriz', 'numero_nota']

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
            
            # Adiciona campos do lote (registro 02)
            for campo in campos_02:
                linha[campo] = lote.get(campo, '')
            
            # Adiciona campos da partida (registro 03) com novos nomes
            linha['Banco'] = partida.get('conta_debito', '')
            linha['Fornecedor/Cliente'] = partida.get('conta_credito', '')
            linha['valor_lancamento'] = partida.get('valor_lancamento', '')
            linha['codigo_historico'] = partida.get('codigo_historico', '')
            linha['Histórico'] = partida.get('historico_complemento', '')
            linha['codigo_filial_matriz'] = partida.get('codigo_filial_matriz', '')
            
            # Extrai nome da empresa do histórico e substitui Banco
            historico = partida.get('historico_complemento', '')
            nome_empresa = extrair_nome_empresa(historico)
            if nome_empresa:
                linha['Banco'] = nome_empresa
            
            # Extrai número da nota fiscal
            numero_nota = extrair_numero_nota(historico)
            linha['numero_nota'] = numero_nota
            
            # Remove zeros à esquerda da conta_credito
            if 'Fornecedor/Cliente' in linha and linha['Fornecedor/Cliente']:
                linha['Fornecedor/Cliente'] = remover_zeros_esquerda(linha['Fornecedor/Cliente'])
            
            # Formata valor e data
            if 'valor_lancamento' in linha and linha['valor_lancamento']:
                linha['valor_lancamento'] = formatar_valor(linha['valor_lancamento'])
            if 'data_lancamento' in linha and linha['data_lancamento']:
                linha['data_lancamento'] = formatar_data(linha['data_lancamento'])
            
            writer.writerow(linha)


def gerar_csv_agrupado(registros: List[Dict[str, Any]], output_file: str):
    """Gera CSV apenas com as colunas Banco (nome) e Fornecedor/Cliente, pares únicos"""
    pares_unicos = set()
    for registro in registros:
        banco = registro.get('Banco', '').strip()
        fornecedor_cliente = registro.get('Fornecedor/Cliente', '').strip()
        # Remove zeros à esquerda da fornecedor_cliente
        if fornecedor_cliente:
            try:
                fornecedor_cliente = str(int(fornecedor_cliente))
            except:
                pass
        if banco and fornecedor_cliente:
            pares_unicos.add((banco, fornecedor_cliente))
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile, delimiter=';')
        writer.writerow(['Banco', 'Fornecedor/Cliente'])
        for banco, fornecedor_cliente in sorted(pares_unicos):
            writer.writerow([banco, fornecedor_cliente])


def main():
    parser = argparse.ArgumentParser(description='Importa arquivo Domínio Sistemas e gera CSV')
    parser.add_argument('arquivo_entrada', help='Caminho do arquivo de entrada no layout Domínio')
    parser.add_argument('-o', '--output', help='Arquivo CSV de saída (padrão: nome_entrada-fiscal.csv)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Modo verboso')
    
    args = parser.parse_args()
    
    # Verifica se arquivo existe
    if not os.path.exists(args.arquivo_entrada):
        print(f"Erro: Arquivo '{args.arquivo_entrada}' não encontrado.")
        sys.exit(1)
    
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
    
    # Gera CSV
    gerar_csv_02_03(registros, output_file)
    
    # Gera CSV agrupado
    output_file_agrupado = output_file.replace('-fiscal.csv', '-agrupado.csv')
    gerar_csv_agrupado(registros, output_file_agrupado)
    print(f"CSV agrupado gerado com sucesso: {output_file_agrupado}")
    
    print(f"CSV gerado com sucesso: {output_file}")
    print(f"Total de linhas processadas: {len(registros)}")


if __name__ == "__main__":
    main() 