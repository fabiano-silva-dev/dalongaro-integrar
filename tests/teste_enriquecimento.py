#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de teste para demonstrar o enriquecimento de dados
"""

# Importa as funções do script principal
from gerar_planilha_dominio import (
    carregar_arquivo_enriquecimento, 
    comparar_strings_similaridade, 
    encontrar_dados_enriquecimento,
    limpar_string_para_comparacao
)

def testar_enriquecimento():
    """Testa as funções de enriquecimento"""
    
    # Carrega dados de exemplo
    dados_enriquecimento = [
        {
            'dados_principais_número': '12345',
            'dados_principais_fornecedor/comprador': 'EMPRESA ABC LTDA',
            'financeiro_conta_financeira': '1.1.01.001',
            'itens_conta': '2.1.01.001',
            'item_descricao': 'SERVIÇOS DE CONSULTORIA',
            'itens_centro_resultado': 'CR001'
        },
        {
            'dados_principais_número': '67890',
            'dados_principais_fornecedor/comprador': 'FORNECEDOR XYZ S/A',
            'financeiro_conta_financeira': '1.1.01.002',
            'itens_conta': '2.1.01.002',
            'item_descricao': 'MATERIAIS DE ESCRITÓRIO',
            'itens_centro_resultado': 'CR002'
        }
    ]
    
    print("=== TESTE DE LIMPEZA DE STRINGS ===")
    exemplos_strings = [
        "EMPRESA ABC LTDA",
        "FORNECEDOR XYZ S/A",
        "CONTRATADA 123 LTDA",
        "SERVIÇO TOMADO NESTA DATA N° 12345 EMPRESA ABC LTDA"
    ]
    
    for texto in exemplos_strings:
        texto_limpo = limpar_string_para_comparacao(texto)
        print(f"Original: '{texto}'")
        print(f"Limpo: '{texto_limpo}'")
        print()
    
    print("=== TESTE DE COMPARAÇÃO DE STRINGS ===")
    pares_teste = [
        ("EMPRESA ABC LTDA", "EMPRESA ABC LTDA"),
        ("EMPRESA ABC LTDA", "ABC EMPRESA"),
        ("FORNECEDOR XYZ S/A", "XYZ FORNECEDOR"),
        ("EMPRESA ABC LTDA", "FORNECEDOR DIFERENTE"),
        ("SERVIÇO TOMADO NESTA DATA N° 12345 EMPRESA ABC LTDA", "EMPRESA ABC LTDA")
    ]
    
    for str1, str2 in pares_teste:
        similar = comparar_strings_similaridade(str1, str2)
        print(f"'{str1}' vs '{str2}' -> Similar: {similar}")
    
    print("\n=== TESTE DE ENRIQUECIMENTO ===")
    casos_teste = [
        ("12345", "EMPRESA ABC LTDA"),
        ("67890", "FORNECEDOR XYZ S/A"),
        ("99999", "EMPRESA INEXISTENTE"),
        ("12345", "ABC EMPRESA"),
        ("", "EMPRESA ABC LTDA"),
        ("12345", "")
    ]
    
    for numero_nota, nome_empresa in casos_teste:
        dados = encontrar_dados_enriquecimento(numero_nota, nome_empresa, dados_enriquecimento)
        print(f"Número: '{numero_nota}', Empresa: '{nome_empresa}'")
        print(f"  Conta Financeira: {dados['financeiro_conta_financeira']}")
        print(f"  Itens Conta: {dados['itens_conta']}")
        print(f"  Item Descrição: {dados['item_descricao']}")
        print(f"  Centro Resultado: {dados['itens_centro_resultado']}")
        print()

if __name__ == "__main__":
    testar_enriquecimento() 