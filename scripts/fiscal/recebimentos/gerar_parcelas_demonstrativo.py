#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lê o demonstrativo de faturamento (HTML/XLS) e gera planilha Excel com 3 parcelas por nota:
- Vencimentos: 35, 42 e 49 dias a partir da emissão
- 5% de desconto em cada parcela
"""

import re
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd


def parse_valor_br(valor_str):
    """Converte string no formato brasileiro (ex: '3.135,00' ou '391,44') para float."""
    if pd.isna(valor_str) or valor_str == '' or str(valor_str).strip() == '':
        return None
    if isinstance(valor_str, (int, float)):
        return float(valor_str) if valor_str > 0 else None
    s = str(valor_str).strip().replace('.', '').replace(',', '.')
    try:
        return float(s)
    except ValueError:
        return None


def parse_data_br(data_str):
    """Converte data DD/MM/YYYY ou datetime para date."""
    if pd.isna(data_str) or data_str == '' or str(data_str).strip() == '':
        return None
    if hasattr(data_str, 'date'):
        return data_str.date()
    s = str(data_str).strip()
    try:
        return datetime.strptime(s[:10], '%d/%m/%Y').date()
    except ValueError:
        try:
            return datetime.strptime(s[:10], '%Y-%m-%d').date()
        except ValueError:
            return None


def _extrair_texto_td(td):
    """Extrai texto de um <td>...</td>."""
    import re
    m = re.search(r'<td[^>]*>(.*?)</td>', td, re.DOTALL | re.IGNORECASE)
    if not m:
        return ''
    texto = m.group(1).replace('&nbsp;', ' ').strip()
    return re.sub(r'\s+', ' ', texto).strip()


def ler_demonstrativo(caminho_arquivo):
    """Lê o arquivo HTML/.xls e retorna DataFrame com as linhas de notas."""
    import re
    caminho = Path(caminho_arquivo)
    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")

    texto = caminho.read_text(encoding='utf-8', errors='replace')
    # Cada linha de dados: <tr><td>Emissão</td><td>Venc</td><td>No.Título</td><td>Cliente</td><td>Nota Fisc.</td><td></td><td>  valor</td><td></td></tr>
    linhas = []
    # Partir por <tr> e pegar cada <td>
    for bloco in re.finditer(r'<tr>(.*?)</tr>', texto, re.DOTALL | re.IGNORECASE):
        conteudo = bloco.group(1)
        celdas = re.findall(r'<td[^>]*>.*?</td>', conteudo, re.DOTALL | re.IGNORECASE)
        celulas_texto = [_extrair_texto_td(c) for c in celdas]
        if len(celulas_texto) < 7:
            continue
        # Posições: 0=Emissão, 1=Venc, 2=No.Título, 3=Cliente, 4=Nota Fisc., 5=vazio, 6=Vlr.Tit.
        emissao = parse_data_br(celulas_texto[0])
        valor = parse_valor_br(celulas_texto[6])
        if emissao is not None and valor is not None and valor > 0:
            linhas.append({
                'Emissão': emissao,
                'Vencimento_original': celulas_texto[1],
                'No.Título': celulas_texto[2],
                'Cliente': celulas_texto[3],
                'Nota Fisc.': celulas_texto[4],
                'Vlr.Tit.': valor,
            })
    return pd.DataFrame(linhas)


def gerar_parcelas(df_notas, dias_parcelas=(35, 42, 49)):
    """
    Gera 3 linhas por nota. Entrada = Emissão + 2 dias; Vencimento = Entrada + dias.
    Valor das 3 parcelas soma exatamente o valor total da nota (ajuste de centavos na última).
    """
    registros = []
    for _, nota in df_notas.iterrows():
        emissao = nota['Emissão']
        entrada = emissao + timedelta(days=2)
        valor_total = round(nota['Vlr.Tit.'], 2)
        # Três parcelas que fecham exatamente com o total (evita erro de arredondamento)
        p1 = round(valor_total / 3, 2)
        p2 = round(valor_total / 3, 2)
        p3 = valor_total - p1 - p2  # terceira parcela absorve a diferença
        valores_parcelas = [p1, p2, p3]
        for num_parcela, (dias, valor_parcela) in enumerate(zip(dias_parcelas, valores_parcelas), start=1):
            vencimento = entrada + timedelta(days=dias)
            registros.append({
                'Emissão': emissao,
                'Entrada': entrada,
                'Nota Fisc.': nota['Nota Fisc.'],
                'Cliente': nota['Cliente'],
                'No.Título': nota['No.Título'],
                'Parcela': num_parcela,
                'Vencimento': vencimento,
                'Valor parcela': round(valor_parcela, 2),
                'Valor total nota': valor_total,
            })
    return pd.DataFrame(registros)


def formatar_data_br(d):
    """Formata date como dd/mm/aaaa."""
    if pd.isna(d) or d is None:
        return ''
    if hasattr(d, 'strftime'):
        return d.strftime('%d/%m/%Y')
    return str(d)


def main():
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from runtime import setup_workspace
    from paths import ROOT

    setup_workspace()
    entrada = sys.argv[1] if len(sys.argv) > 1 else '/home/fabiano/Downloads/demonstrativo_faturamento_entre_01-01-2025_e_31-12-2025.xls'
    saida = sys.argv[2] if len(sys.argv) > 2 else str(ROOT / 'parcelas_por_nota_35_42_49.xlsx')

    print(f"Lendo: {entrada}")
    df_notas = ler_demonstrativo(entrada)
    # Apenas OSMAR NICOLINI
    df_notas = df_notas[df_notas['Cliente'].str.contains('OSMAR NICOLINI', case=False, na=False)].copy()
    print(f"Notas encontradas (OSMAR NICOLINI): {len(df_notas)}")

    df_parcelas = gerar_parcelas(df_notas, dias_parcelas=(35, 42, 49))
    print(f"Linhas geradas (3 por nota): {len(df_parcelas)}")

    # Formatar datas como dd/mm/aaaa
    for col in ['Emissão', 'Entrada', 'Vencimento']:
        if col in df_parcelas.columns:
            df_parcelas[col] = df_parcelas[col].apply(formatar_data_br)

    df_parcelas.to_excel(saida, index=False, sheet_name='Parcelas')
    print(f"Planilha salva: {saida}")

    # Resumo (soma das parcelas deve fechar com total das notas)
    total_notas = df_parcelas.groupby(['Nota Fisc.', 'Emissão'])['Valor total nota'].first().sum()
    total_parcelas = df_parcelas['Valor parcela'].sum()
    print(f"Total notas: {total_notas:,.2f}")
    print(f"Soma das parcelas: {total_parcelas:,.2f} (deve fechar)")


if __name__ == '__main__':
    main()
