#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import csv

def is_num(val):
    try:
        float(val.replace(',', '.'))
        return True
    except:
        return False

def estruturar_plano_contas():
    # Ler o arquivo CSV original
    with open('Contas.csv', 'r', encoding='utf-8') as file:
        lines = file.readlines()
    
    # Encontrar onde começa a tabela de dados (linha 6)
    start_line = 5  # Linha 6 (índice 5)
    
    # Extrair apenas os dados da tabela
    data_lines = lines[start_line:]
    
    # Processar os dados
    dados_estruturados = []
    for line in data_lines:
        if line.strip():  # Ignorar linhas vazias
            reader = csv.reader([line])
            row = next(reader)
            if len(row) >= 20:
                numero = row[0].strip() if len(row) > 0 else ""
                codigo = row[1].strip() if len(row) > 1 else ""
                tipo = row[3].strip() if len(row) > 3 else ""
                classificacao = row[7].strip() if len(row) > 7 else ""
                grau = row[22].strip() if len(row) > 22 else ""
                nome = ""
                # Procurar o nome da direita para a esquerda, ignorando valores numéricos e iguais ao grau
                for idx in range(len(row)-1, -1, -1):
                    val = row[idx].strip()
                    if val and not is_num(val) and val != grau:
                        nome = val
                        break
                # Só incluir se tiver código ou nome
                if codigo or nome:
                    dados_estruturados.append({
                        'numero': numero,
                        'codigo': codigo,
                        'tipo': tipo,
                        'classificacao': classificacao,
                        'nome': nome,
                        'grau': grau
                    })
    df = pd.DataFrame(dados_estruturados)
    df.to_csv('Contas_estruturado.csv', index=False, encoding='utf-8')
    df.to_excel('Contas_estruturado.xlsx', index=False)
    print(f"Arquivo estruturado criado com {len(df)} registros")
    print("\nPrimeiras 10 linhas:")
    print(df.head(10))
    return df

if __name__ == "__main__":
    df = estruturar_plano_contas() 