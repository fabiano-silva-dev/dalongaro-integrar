#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para filtrar registros do layout Domínio Sistemas por conta de crédito e débito
Baseado no layout: Lançamentos Contábeis em Lote

Uso:
    python filtrar_contas_dominio.py arquivo.txt -d 0000602 -c 0000726
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
        
        # Remove BOM se presente
        line = line.replace('\ufeff', '')
            
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
        cabecalho_forcado = None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                conteudo = file.read()
                # Remove quebras de linha e espaços extras
                linhas = [linha.strip() for linha in conteudo.split('\n') if linha.strip()]
                
                for line_num, line in enumerate(linhas, 1):
                    if line.strip():  # Ignora linhas vazias
                        registro = self.parse_line(line)
                        if line_num == 1:
                            print(f"DEBUG: Primeira linha parseada: {registro}")
                        if registro:
                            registro['linha_arquivo'] = line_num
                            registro['linha_original'] = line  # Guarda a linha original
                            registros.append(registro)
                            # Debug para verificar o cabeçalho
                            if registro.get('tipo') == 'cabecalho':
                                print(f"DEBUG: Cabeçalho encontrado na linha {line_num}: {line[:50]}...")
                        # Se não reconheceu como cabeçalho, força inclusão
                        if line_num == 1 and (not registro or registro.get('tipo') != 'cabecalho'):
                            cabecalho_forcado = {
                                'tipo': 'cabecalho',
                                'linha_arquivo': 1,
                                'linha_original': line
                            }
        except UnicodeDecodeError:
            # Tenta com encoding diferente se UTF-8 falhar
            with open(file_path, 'r', encoding='latin-1') as file:
                conteudo = file.read()
                linhas = [linha.strip() for linha in conteudo.split('\n') if linha.strip()]
                
                for line_num, line in enumerate(linhas, 1):
                    if line.strip():
                        registro = self.parse_line(line)
                        if line_num == 1:
                            print(f"DEBUG: Primeira linha parseada: {registro}")
                        if registro:
                            registro['linha_arquivo'] = line_num
                            registro['linha_original'] = line  # Guarda a linha original
                            registros.append(registro)
                            # Debug para verificar o cabeçalho
                            if registro.get('tipo') == 'cabecalho':
                                print(f"DEBUG: Cabeçalho encontrado na linha {line_num}: {line[:50]}...")
                        # Se não reconheceu como cabeçalho, força inclusão
                        if line_num == 1 and (not registro or registro.get('tipo') != 'cabecalho'):
                            cabecalho_forcado = {
                                'tipo': 'cabecalho',
                                'linha_arquivo': 1,
                                'linha_original': line
                            }
        # Garante que o cabeçalho esteja presente
        if cabecalho_forcado:
            print("AVISO: Cabeçalho não reconhecido pelo parser, forçando inclusão!")
            registros = [cabecalho_forcado] + registros
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
    cabecalho_incluido = False
    
    for registro in registros:
        if registro.get('tipo') == 'cabecalho':
            # Sempre inclui o cabeçalho
            registros_completos.append(registro)
            cabecalho_incluido = True
            print(f"DEBUG: Cabeçalho incluído - linha {registro.get('linha_arquivo')}")
        elif registro.get('tipo') == 'dados_lote':
            # Inclui apenas os lotes que têm partidas filtradas
            if registro.get('codigo_sequencial') in lotes_incluidos:
                registros_completos.append(registro)
                print(f"DEBUG: Lote incluído - sequencial {registro.get('codigo_sequencial')}")
        elif registro.get('tipo') == 'partidas_lancamentos':
            # Inclui apenas as partidas filtradas
            if registro in registros_filtrados:
                registros_completos.append(registro)
                print(f"DEBUG: Partida incluída - sequencial {registro.get('codigo_sequencial')}")
        elif registro.get('tipo') == 'finalizador':
            # Sempre inclui o finalizador
            registros_completos.append(registro)
            print(f"DEBUG: Finalizador incluído")
    
    if not cabecalho_incluido:
        print("AVISO: Nenhum cabeçalho foi encontrado no arquivo original!")
    
    return registros_completos


def modificar_campos_empresa(linha: str, tipo_registro: str, 
                           nova_conta_debito: str = None, 
                           nova_conta_credito: str = None,
                           novo_codigo_empresa: str = "0000667",
                           novo_cnpj_empresa: str = "55526785000122",
                           novo_codigo_filial: str = "0000667") -> str:
    """
    Modifica campos específicos da empresa na linha
    
    Args:
        linha: Linha original do arquivo
        tipo_registro: Tipo do registro (cabecalho, partidas_lancamentos, etc.)
        nova_conta_debito: Nova conta de débito para substituir a original
        nova_conta_credito: Nova conta de crédito para substituir a original
        novo_codigo_empresa: Novo código da empresa
        novo_cnpj_empresa: Novo CNPJ da empresa
        novo_codigo_filial: Novo código da filial/matriz
    """
    if tipo_registro == 'cabecalho':
        # Garante que a linha tenha pelo menos 54 caracteres
        if len(linha) < 54:
            linha = linha.ljust(54)
        # Garante que a linha comece com '01'
        if not linha.startswith('01'):
            linha = '01' + linha[2:]
        # Garante que o CNPJ tenha exatamente 14 caracteres
        cnpj_ajustado = (novo_cnpj_empresa or '').strip()[:14].ljust(14)
        # Substitui campos nas posições corretas
        linha = (
            linha[:2] + (novo_codigo_empresa or '').strip().ljust(7)[:7] +
            cnpj_ajustado +
            linha[23:33] +  # data_inicial
            linha[33:43] +  # data_final
            linha[43:45] +  # tipo_nota
            linha[45:50] +  # constante
            linha[50:52] +  # sistema
            linha[52:54] +  # valor_fixo
            linha[54:]      # resto da linha
        )
        return linha
    elif tipo_registro == 'partidas_lancamentos':
        # Garante que a linha tenha pelo menos 564 caracteres
        if len(linha) < 564:
            linha = linha.ljust(564)
            
        # Troca conta de débito se especificada (posições 9-16)
        if nova_conta_debito and linha[9:16] != nova_conta_debito:
            linha = linha[:9] + nova_conta_debito + linha[16:]
            
        # Troca conta de crédito se especificada (posições 16-23)
        if nova_conta_credito and linha[16:23] != nova_conta_credito:
            linha = linha[:16] + nova_conta_credito + linha[23:]
            
        # Modifica código da filial/matriz (posições 557-563)
        linha = linha[:556] + novo_codigo_filial + linha[563:]
    
    return linha


def gerar_txt_filtrado(registros_filtrados: List[Dict[str, Any]], 
                      output_file: str,
                      nova_conta_debito: str = None,
                      nova_conta_credito: str = None,
                      novo_codigo_empresa: str = "0000667",
                      novo_cnpj_empresa: str = "55526785000122",
                      novo_codigo_filial: str = "0000667"):
    """
    Gera arquivo TXT no mesmo layout do original com os registros filtrados
    
    Args:
        registros_filtrados: Lista de registros filtrados
        output_file: Caminho do arquivo de saída
        nova_conta_debito: Nova conta de débito para substituir
        nova_conta_credito: Nova conta de crédito para substituir
        novo_codigo_empresa: Novo código da empresa
        novo_cnpj_empresa: Novo CNPJ da empresa
        novo_codigo_filial: Novo código da filial/matriz
    """
    with open(output_file, 'w', encoding='utf-8') as file:
        for registro in registros_filtrados:
            tipo = registro.get('tipo')
            # Se for um cabeçalho forçado, trata como cabeçalho
            if tipo == 'cabecalho' and 'identificador' not in registro:
                linha_modificada = modificar_campos_empresa(
                    registro['linha_original'],
                    'cabecalho',
                    nova_conta_debito,
                    nova_conta_credito,
                    novo_codigo_empresa,
                    novo_cnpj_empresa,
                    novo_codigo_filial
                )
                # Garante que o cabeçalho comece com '01'
                if not linha_modificada.startswith('01'):
                    linha_modificada = '01' + linha_modificada[2:]
            else:
                linha_modificada = modificar_campos_empresa(
                    registro['linha_original'],
                    tipo,
                    nova_conta_debito,
                    nova_conta_credito,
                    novo_codigo_empresa,
                    novo_cnpj_empresa,
                    novo_codigo_filial
                )
            file.write(linha_modificada + '\n')


def main():
    parser = argparse.ArgumentParser(
        description='Filtra registros Domínio Sistemas por conta de crédito e débito',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  python filtrar_contas_dominio.py arquivo.txt -d 0000602 -c 0000726
  python filtrar_contas_dominio.py arquivo.txt -d 0000602 -c 0000726 -nd 0000274 -nc 0000660
  python filtrar_contas_dominio.py arquivo.txt -d 0000683 -nd 0000274 -nc 0000660
        """
    )
    
    # Parâmetros obrigatórios para filtro
    parser.add_argument('arquivo_entrada', help='Caminho do arquivo de entrada no layout Domínio')
    parser.add_argument('-d', '--debito', help='Conta de débito para filtrar (ex: 0000602)')
    parser.add_argument('-c', '--credito', help='Conta de crédito para filtrar (ex: 0000726)')
    
    # Parâmetros para novas contas (opcionais)
    parser.add_argument('-nd', '--nova-debito', help='Nova conta de débito para substituir (ex: 0000274)')
    parser.add_argument('-nc', '--nova-credito', help='Nova conta de crédito para substituir (ex: 0000660)')
    
    # Parâmetros para dados da empresa (opcionais)
    parser.add_argument('--codigo-empresa', default='0000667', help='Novo código da empresa (padrão: 0000667)')
    parser.add_argument('--cnpj-empresa', default='55526785000122', help='Novo CNPJ da empresa (padrão: 55526785000122)')
    parser.add_argument('--codigo-filial', default='0000667', help='Novo código da filial/matriz (padrão: 0000667)')
    
    # Parâmetros gerais
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
        nome_arquivo = os.path.basename(args.arquivo_entrada)
        nome_base, ext = os.path.splitext(nome_arquivo)
        # Troca (666) por (667) e adiciona sufixo -filtrado
        nome_base = nome_base.replace('(666)', '(667)')
        nome_saida = f"{nome_base}-filtrado{ext}"
        diretorio = os.path.dirname(args.arquivo_entrada)
        output_file = os.path.join(diretorio, nome_saida)
    
    print(f"Processando arquivo: {args.arquivo_entrada}")
    if args.debito:
        print(f"Filtrando por conta de débito: {args.debito}")
    if args.credito:
        print(f"Filtrando por conta de crédito: {args.credito}")
    
    # Mostra informações sobre substituições
    if args.nova_debito:
        print(f"Nova conta de débito: {args.nova_debito}")
    if args.nova_credito:
        print(f"Nova conta de crédito: {args.nova_credito}")
    
    print(f"Novo código da empresa: {args.codigo_empresa}")
    print(f"Novo CNPJ da empresa: {args.cnpj_empresa}")
    print(f"Novo código da filial: {args.codigo_filial}")
    
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
    gerar_txt_filtrado(
        registros_filtrados, 
        output_file,
        args.nova_debito,
        args.nova_credito,
        args.codigo_empresa,
        args.cnpj_empresa,
        args.codigo_filial
    )
    
    print(f"\nArquivo TXT filtrado gerado com sucesso: {output_file}")
    print(f"Total de registros no arquivo filtrado: {len(registros_filtrados)}")
    
    # Mostra resumo das modificações
    print("\nModificações aplicadas:")
    print(f"  - Código da Empresa: {args.codigo_empresa}")
    print(f"  - CNPJ da Empresa: {args.cnpj_empresa}")
    print(f"  - Código da Filial/Matriz: {args.codigo_filial}")
    
    if args.nova_debito:
        print(f"  - Conta de débito alterada: {args.debito} → {args.nova_debito}")
    if args.nova_credito:
        print(f"  - Conta de crédito alterada: {args.credito} → {args.nova_credito}")


if __name__ == "__main__":
    main() 