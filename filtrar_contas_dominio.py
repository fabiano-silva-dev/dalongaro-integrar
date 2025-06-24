#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para filtrar registros do layout Domínio Sistemas por conta de crédito e débito
Baseado no layout: Lançamentos Contábeis em Lote
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
                            registro['linha_original'] = line  # Guarda a linha original
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
                            registro['linha_original'] = line  # Guarda a linha original
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


def filtrar_por_contas(registros: List[Dict[str, Any]], conta_debito: str = None, conta_credito: str = None) -> List[Dict[str, Any]]:
    """Filtra registros por conta de débito e/ou crédito específicas"""
    registros_filtrados = []
    lotes_incluidos = set()  # Para rastrear quais lotes devem ser incluídos
    
    # Primeiro, identifica quais partidas atendem aos critérios
    for registro in registros:
        if registro.get('tipo') == 'partidas_lancamentos':
            # Verifica se deve filtrar por conta de débito
            if conta_debito and registro.get('conta_debito', '').strip() != conta_debito.strip():
                continue
                
            # Verifica se deve filtrar por conta de crédito
            if conta_credito and registro.get('conta_credito', '').strip() != conta_credito.strip():
                continue
                
            registros_filtrados.append(registro)
            # Marca o lote correspondente para inclusão
            cod_seq_partida = registro['codigo_sequencial']
            cod_seq_lote = str(int(cod_seq_partida) - 1).zfill(7)
            lotes_incluidos.add(cod_seq_lote)
    
    # Agora inclui os lotes correspondentes e outros registros necessários
    registros_completos = []
    
    for registro in registros:
        if registro.get('tipo') == 'cabecalho':
            # Sempre inclui o cabeçalho
            registros_completos.append(registro)
        elif registro.get('tipo') == 'dados_lote':
            # Inclui apenas os lotes que têm partidas filtradas
            if registro.get('codigo_sequencial') in lotes_incluidos:
                registros_completos.append(registro)
        elif registro.get('tipo') == 'partidas_lancamentos':
            # Inclui apenas as partidas filtradas
            if registro in registros_filtrados:
                registros_completos.append(registro)
        elif registro.get('tipo') == 'finalizador':
            # Sempre inclui o finalizador
            registros_completos.append(registro)
    
    return registros_completos


def modificar_campos_empresa(linha: str, tipo_registro: str) -> str:
    """Modifica campos específicos da empresa na linha"""
    if tipo_registro == 'cabecalho':
        # Modifica código da empresa (posições 3-9) para 0000667
        linha = linha[:2] + '0000667' + linha[9:]
        # Modifica CNPJ da empresa (posições 10-23) para 55526785000122
        linha = linha[:9] + '55526785000122' + linha[23:]
    elif tipo_registro == 'partidas_lancamentos':
        # Garante que a linha tenha pelo menos 564 caracteres
        if len(linha) < 564:
            linha = linha.ljust(564)
        # Troca conta de débito 683 para 274 (posições 10-16)
        if linha[9:16] == '0000683':
            linha = linha[:9] + '0000274' + linha[16:]
        # Troca conta de crédito 8 para 660 (posições 16-23)
        if linha[15:22] == '0000008':
            linha = linha[:15] + '0000660' + linha[22:]
        # Modifica código da filial/matriz (posições 557-563) para 0000667
        linha = linha[:556] + '0000667' + linha[563:]
    
    return linha


def gerar_txt_filtrado(registros_filtrados: List[Dict[str, Any]], output_file: str):
    """Gera arquivo TXT no mesmo layout do original com os registros filtrados"""
    with open(output_file, 'w', encoding='utf-8') as file:
        for registro in registros_filtrados:
            # Modifica os campos da empresa conforme solicitado
            linha_modificada = modificar_campos_empresa(registro['linha_original'], registro['tipo'])
            # Escreve a linha modificada mantendo o layout exato
            file.write(linha_modificada + '\n')


def main():
    parser = argparse.ArgumentParser(description='Filtra registros Domínio Sistemas por conta de crédito e débito')
    parser.add_argument('arquivo_entrada', help='Caminho do arquivo de entrada no layout Domínio')
    parser.add_argument('-d', '--debito', help='Conta de débito para filtrar (ex: 0000602)')
    parser.add_argument('-c', '--credito', help='Conta de crédito para filtrar (ex: 0000726)')
    parser.add_argument('-o', '--output', help='Arquivo TXT de saída (padrão: nome_entrada-filtrado.txt)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Modo verboso')
    
    args = parser.parse_args()
    
    # Verifica se pelo menos um filtro foi especificado
    if not args.debito and not args.credito:
        print("Erro: É necessário especificar pelo menos uma conta de débito (-d) ou crédito (-c)")
        sys.exit(1)
    
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
        output_file = os.path.join(diretorio, f"{nome_base}-filtrado.txt")
    
    print(f"Processando arquivo: {args.arquivo_entrada}")
    if args.debito:
        print(f"Filtrando por conta de débito: {args.debito}")
    if args.credito:
        print(f"Filtrando por conta de crédito: {args.credito}")
    
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
    
    # Filtra registros por contas
    registros_filtrados = filtrar_por_contas(registros, args.debito, args.credito)
    
    # Conta quantas partidas foram encontradas
    partidas_filtradas = [r for r in registros_filtrados if r.get('tipo') == 'partidas_lancamentos']
    print(f"Partidas encontradas com os filtros aplicados: {len(partidas_filtradas)}")
    
    if len(partidas_filtradas) == 0:
        print("Nenhum registro encontrado com os filtros especificados.")
        return
    
    # Gera arquivo TXT filtrado
    gerar_txt_filtrado(registros_filtrados, output_file)
    
    print(f"Arquivo TXT filtrado gerado com sucesso: {output_file}")
    print(f"Total de registros no arquivo filtrado: {len(registros_filtrados)}")
    print("Campos modificados:")
    print("  - Código da Empresa: 0000667")
    print("  - CNPJ da Empresa: 55526785000122")
    print("  - Código da Filial/Matriz: 0000667")


if __name__ == "__main__":
    main() 