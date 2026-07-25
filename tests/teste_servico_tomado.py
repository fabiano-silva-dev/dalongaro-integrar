#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de teste para demonstrar o tratamento da string "SERVIÇO TOMADO NESTA DATA"
"""

# Importa as funções do script principal
from gerar_planilha_dominio import extrair_nome_empresa, extrair_numero_nota

def testar_servico_tomado():
    """Testa o tratamento da string 'SERVIÇO TOMADO NESTA DATA'"""
    
    # Exemplos de históricos com "SERVIÇO TOMADO NESTA DATA"
    exemplos = [
        "SERVIÇO TOMADO NESTA DATA N° 12345 EMPRESA ABC LTDA",
        "SERVIÇO TOMADO NESTA DATA 67890 FORNECEDOR XYZ S/A",
        "SERVIÇO TOMADO NESTA DATA Nº 11111 CONTRATADA 123 LTDA",
        "NF N° 99999 NOTA FISCAL PADRÃO",
        "12345 EMPRESA QUE COMEÇA COM NÚMEROS"
    ]
    
    print("=== TESTE DE EXTRAÇÃO DE NOME DA EMPRESA ===")
    for i, historico in enumerate(exemplos, 1):
        nome_empresa = extrair_nome_empresa(historico)
        print(f"Exemplo {i}:")
        print(f"  Histórico: {historico}")
        print(f"  Nome extraído: '{nome_empresa}'")
        print()
    
    print("=== TESTE DE EXTRAÇÃO DE NÚMERO DO DOCUMENTO ===")
    for i, historico in enumerate(exemplos, 1):
        numero_doc = extrair_numero_nota(historico)
        print(f"Exemplo {i}:")
        print(f"  Histórico: {historico}")
        print(f"  Número extraído: '{numero_doc}'")
        print()

if __name__ == "__main__":
    testar_servico_tomado() 