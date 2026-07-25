#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de teste para verificar a extração do novo padrão NFE
"""

import re

def extrair_nome_empresa_novo_padrao(historico: str) -> str:
    """Extrai o nome da empresa do histórico com o novo padrão VLR REF NFE Nº"""
    try:
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
    except:
        pass
    return ""

def extrair_numero_nota_novo_padrao(historico: str) -> str:
    """Extrai o número da nota fiscal com o novo padrão VLR REF NFE Nº"""
    try:
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
    except:
        pass
    return ""

def testar_novo_padrao():
    """Testa a extração do novo padrão NFE"""
    
    # Exemplo do novo padrão
    exemplo = "VLR REF NFE Nº 9512 Vidacard Segurança do Trabalho Ltda."
    
    print("=== TESTE DO NOVO PADRÃO NFE ===")
    print(f"Histórico: {exemplo}")
    
    numero = extrair_numero_nota_novo_padrao(exemplo)
    nome = extrair_nome_empresa_novo_padrao(exemplo)
    
    print(f"Número extraído: '{numero}'")
    print(f"Nome da empresa: '{nome}'")
    print()
    
    # Teste com outros exemplos do arquivo
    exemplos_adicionais = [
        "VLR REF NFE Nº 2025575 QUARTA COLÔNIA SOLUÇÕES DIGITAIS LTDA",
        "COMPRA DE MERCADORIA CFE NF Nº 25211 EXTRACAO E COMERCIO DE CALCARIO ALIANCA SPE LTDA",
        "SERVIÇO TOMADO NESTA DATA 4298 BIANCHI BIANCHI & CIA LTDA - MT"
    ]
    
    for i, exemplo in enumerate(exemplos_adicionais, 1):
        print(f"Exemplo {i}:")
        print(f"  Histórico: {exemplo}")
        
        numero = extrair_numero_nota_novo_padrao(exemplo)
        nome = extrair_nome_empresa_novo_padrao(exemplo)
        
        print(f"  Número extraído: '{numero}'")
        print(f"  Nome da empresa: '{nome}'")
        print()

if __name__ == "__main__":
    testar_novo_padrao() 