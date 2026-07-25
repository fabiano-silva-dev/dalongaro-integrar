#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diagnóstico de matching entre lançamentos do Domínio e tabela de enriquecimento
"""
from gerar_planilha_dominio import (
    DominioLayoutParser,
    extrair_numero_nota,
    extrair_nome_empresa,
    carregar_arquivo_enriquecimento,
    comparar_strings_similaridade
)
import sys

# Arquivos de entrada
ARQ_DOMINIO = 'clientes/luciano-664/2025-03/dominio-fiscal-2025-03.txt'
ARQ_ENRIQUECIMENTO = 'clientes/luciano-664/2025-03/Exportação de Dados - Comercial.csv'

def main():
    parser = DominioLayoutParser()
    registros = parser.parse_file(ARQ_DOMINIO)
    dados_enriquecimento = carregar_arquivo_enriquecimento(ARQ_ENRIQUECIMENTO)

    print(f"Total lançamentos: {len(registros)}")
    print(f"Total enriquecimento: {len(dados_enriquecimento)}")
    print()
    print(f"{'Linha':<5} {'NumNota':<15} {'Empresa':<40} | {'Match?':<7} {'NumTabela':<15} {'FornecedorTabela'}")
    print('-'*120)

    for reg in registros:
        if reg.get('tipo') != 'partidas_lancamentos':
            continue
        historico = reg.get('historico_complemento', '')
        numero_nota = extrair_numero_nota(historico)
        nome_empresa = extrair_nome_empresa(historico)
        linha_arquivo = reg.get('linha_arquivo', '-')
        encontrou = False
        match_num = ''
        match_nome = ''
        for dado in dados_enriquecimento:
            num_tab = dado.get('dados_principais_número', '').strip()
            forn_tab = dado.get('dados_principais_fornecedor/comprador', '').strip()
            if numero_nota == num_tab:
                match_num = num_tab
                if comparar_strings_similaridade(nome_empresa, forn_tab):
                    encontrou = True
                    match_nome = forn_tab
                    break
        print(f"{linha_arquivo:<5} {numero_nota:<15} {nome_empresa:<40} | {'SIM' if encontrou else 'NÃO':<7} {match_num:<15} {match_nome}")

    print('\nNúmeros e nomes únicos do CSV de enriquecimento:')
    numeros_csv = set()
    nomes_csv = set()
    for dado in dados_enriquecimento:
        numeros_csv.add(dado.get('dados_principais_número', '').strip())
        nomes_csv.add(dado.get('dados_principais_fornecedor/comprador', '').strip())
    print('Números:')
    for n in sorted(n for n in numeros_csv if n):
        print(f'  - {n}')
    print('Nomes:')
    for n in sorted(n for n in nomes_csv if n):
        print(f'  - {n}')

if __name__ == "__main__":
    main() 