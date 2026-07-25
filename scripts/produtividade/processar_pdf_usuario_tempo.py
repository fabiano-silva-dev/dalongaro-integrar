#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extrai dados dos PDFs UsuárioTempo Gasto e Custo Benefício,
gerando planilha Excel para conferência.
"""

import argparse
import os
import re
from collections import defaultdict
from datetime import datetime

import fitz
import pandas as pd
from openpyxl.utils import get_column_letter

SISTEMAS = {
    'Contabilidade', 'Escrita', 'Folha', 'Patrimonio', 'Lalur',
    'Atualizar', 'Honorários', 'Registro', 'Gerente',
}

MAPEAMENTO_NOMES = {
    'MASTER2': 'JOYCE',
    'MASTER3': 'DOUGLAS',
}


def aplicar_mapeamento_nome(nome):
    nome_upper = nome.upper().strip()
    return MAPEAMENTO_NOMES.get(nome_upper, nome)


def converter_tempo_para_minutos(tempo_str):
    try:
        partes = str(tempo_str).split(':')
        if len(partes) == 3:
            return int(partes[0]) * 60 + int(partes[1]) + int(partes[2]) / 60
        if len(partes) == 2:
            return int(partes[0]) + int(partes[1]) / 60
    except (ValueError, TypeError):
        pass
    return 0


def minutos_para_hora_minuto_segundo(minutos):
    total_segundos = int(round(minutos * 60))
    horas = total_segundos // 3600
    mins = (total_segundos % 3600) // 60
    segs = total_segundos % 60
    return f"{horas:02d}:{mins:02d}:{segs:02d}"


def extrair_linhas_pdf(caminho_pdf):
    doc = fitz.open(caminho_pdf)
    try:
        return [linha.strip() for linha in "\n".join(page.get_text() for page in doc).split('\n') if linha.strip()]
    finally:
        doc.close()


def parsear_atividades(linhas):
    date_re = re.compile(r'^\d{2}/\d{2}/\d{4}$')
    time_re = re.compile(r'^\d{2}:\d{2}:\d{2}$')

    usuario_atual = None
    atividades = []

    i = 0
    while i < len(linhas):
        linha = linhas[i]

        if linha == 'Usuário:':
            usuario_atual = linhas[i + 1]
            i += 2
            continue

        if linha == 'Total do Usuário:':
            i += 2
            continue

        if (
            date_re.match(linha)
            and i + 3 < len(linhas)
            and linhas[i + 1] in SISTEMAS
            and time_re.match(linhas[i + 3])
        ):
            atividades.append({
                'usuario': aplicar_mapeamento_nome(usuario_atual or ''),
                'data': linha,
                'sistema': linhas[i + 1],
                'cliente': linhas[i + 2],
                'tempo_gasto': linhas[i + 3],
                'tempo_minutos': round(converter_tempo_para_minutos(linhas[i + 3]), 2),
            })
            i += 4
            continue

        i += 1

    return atividades


def gerar_resumos(df):
    resumos = {}

    resumos['Usuario'] = (
        df.groupby('usuario', as_index=False)
        .agg(
            Clientes_Unicos=('cliente', 'nunique'),
            Sistemas_Unicos=('sistema', 'nunique'),
            Total_Atividades=('tempo_gasto', 'count'),
            Tempo_Minutos=('tempo_minutos', 'sum'),
        )
        .sort_values('Tempo_Minutos', ascending=False)
    )
    resumos['Usuario']['Tempo_Total'] = resumos['Usuario']['Tempo_Minutos'].apply(minutos_para_hora_minuto_segundo)
    resumos['Usuario'] = resumos['Usuario'].drop(columns=['Tempo_Minutos'])

    resumos['Cliente'] = (
        df.groupby('cliente', as_index=False)
        .agg(
            Usuarios_Unicos=('usuario', 'nunique'),
            Sistemas_Unicos=('sistema', 'nunique'),
            Total_Atividades=('tempo_gasto', 'count'),
            Tempo_Minutos=('tempo_minutos', 'sum'),
        )
        .sort_values('Tempo_Minutos', ascending=False)
    )
    resumos['Cliente']['Tempo_Total'] = resumos['Cliente']['Tempo_Minutos'].apply(minutos_para_hora_minuto_segundo)
    resumos['Cliente'] = resumos['Cliente'].drop(columns=['Tempo_Minutos'])

    resumos['Sistema'] = (
        df.groupby('sistema', as_index=False)
        .agg(
            Usuarios_Unicos=('usuario', 'nunique'),
            Clientes_Unicos=('cliente', 'nunique'),
            Total_Atividades=('tempo_gasto', 'count'),
            Tempo_Minutos=('tempo_minutos', 'sum'),
        )
        .sort_values('Tempo_Minutos', ascending=False)
    )
    resumos['Sistema']['Tempo_Total'] = resumos['Sistema']['Tempo_Minutos'].apply(minutos_para_hora_minuto_segundo)
    resumos['Sistema'] = resumos['Sistema'].drop(columns=['Tempo_Minutos'])

    resumos['Data'] = (
        df.groupby('data', as_index=False)
        .agg(
            Usuarios_Unicos=('usuario', 'nunique'),
            Clientes_Unicos=('cliente', 'nunique'),
            Total_Atividades=('tempo_gasto', 'count'),
            Tempo_Minutos=('tempo_minutos', 'sum'),
        )
        .sort_values('data')
    )
    resumos['Data']['Tempo_Total'] = resumos['Data']['Tempo_Minutos'].apply(minutos_para_hora_minuto_segundo)
    resumos['Data'] = resumos['Data'].drop(columns=['Tempo_Minutos'])

    return resumos


def gerar_aba_detalhamento_funcionario(df):
    dados_funcionarios = defaultdict(lambda: defaultdict(float))
    for _, row in df.iterrows():
        dados_funcionarios[row['usuario']][row['cliente']] += row['tempo_minutos']

    funcionarios_ordenados = sorted(
        ((func, sum(empresas.values()), empresas) for func, empresas in dados_funcionarios.items()),
        key=lambda x: x[1],
        reverse=True,
    )
    tempo_total_geral = sum(t for _, t, _ in funcionarios_ordenados)

    detalhamento = []
    for funcionario, tempo_total, empresas in funcionarios_ordenados:
        detalhamento.append({
            'Funcionário': funcionario,
            'Empresa': '',
            'Tempo (HH:MM:SS)': minutos_para_hora_minuto_segundo(tempo_total),
        })
        for empresa, tempo in sorted(empresas.items(), key=lambda x: x[1], reverse=True):
            detalhamento.append({
                'Funcionário': '',
                'Empresa': empresa,
                'Tempo (HH:MM:SS)': minutos_para_hora_minuto_segundo(tempo),
            })
        detalhamento.append({'Funcionário': '', 'Empresa': '', 'Tempo (HH:MM:SS)': ''})

    resumo_func = []
    for funcionario, tempo_total, empresas in funcionarios_ordenados:
        percentual = (tempo_total / tempo_total_geral * 100) if tempo_total_geral > 0 else 0
        resumo_func.append({
            'Funcionário': funcionario,
            'Tempo (HH:MM:SS)': minutos_para_hora_minuto_segundo(tempo_total),
            'Percentual (%)': round(percentual, 2),
            'Quantidade de Empresas': len(empresas),
        })
    resumo_func.append({
        'Funcionário': 'TOTAL GERAL',
        'Tempo (HH:MM:SS)': minutos_para_hora_minuto_segundo(tempo_total_geral),
        'Percentual (%)': 100.0,
        'Quantidade de Empresas': '',
    })

    dados_empresas = defaultdict(float)
    for _, tempo_total, empresas in funcionarios_ordenados:
        for empresa, tempo in empresas.items():
            dados_empresas[empresa] += tempo

    resumo_emp = []
    for empresa, tempo_total in sorted(dados_empresas.items(), key=lambda x: x[1], reverse=True):
        percentual = (tempo_total / tempo_total_geral * 100) if tempo_total_geral > 0 else 0
        resumo_emp.append({
            'Empresa': empresa,
            'Tempo (HH:MM:SS)': minutos_para_hora_minuto_segundo(tempo_total),
            'Percentual (%)': round(percentual, 2),
        })
    resumo_emp.append({
        'Empresa': 'TOTAL GERAL',
        'Tempo (HH:MM:SS)': minutos_para_hora_minuto_segundo(tempo_total_geral),
        'Percentual (%)': 100.0,
    })

    return (
        pd.DataFrame(detalhamento),
        pd.DataFrame(resumo_func),
        pd.DataFrame(resumo_emp),
    )


def parsear_valor_monetario(valor_str):
    try:
        return float(str(valor_str).replace('.', '').replace(',', '.'))
    except (ValueError, TypeError):
        return 0.0


def parsear_percentual(valor_str):
    try:
        return float(str(valor_str).replace(',', '.'))
    except (ValueError, TypeError):
        return 0.0


def normalizar_nome_cliente(nome):
    nome = str(nome).upper().strip()
    nome = re.sub(r'[^\w\s&]', ' ', nome)
    return re.sub(r'\s+', ' ', nome).strip()


def parsear_faturamento(linhas):
    time_re = re.compile(r'^\d{2}:\d{2}:\d{2}$')
    pct_re = re.compile(r'^\d+,\d{2}$')
    money_re = re.compile(r'^[\d.]+,\d{2}$')

    skip_starts = (
        'Periodo:', 'Relatorio', 'Tempo Total', 'Faturamento:', 'Cliente',
        'Tempo Gasto', 'Pagina:', 'Emissao:', 'Hora:', '01/06/2026',
        '30/06/2026', 'a', '01/07/2026', '09:21:38',
    )
    skip_exact = {'%', '1/5', '2/5', '3/5', '4/5', '5/5'}

    registros = []
    i = 0
    while i < len(linhas):
        linha = linhas[i]
        if (
            linha in skip_exact
            or any(linha.startswith(prefixo) for prefixo in skip_starts)
            or re.match(r'^\d/\d$', linha)
            or (money_re.match(linha) and i < 15)
        ):
            i += 1
            continue

        if (
            i + 4 < len(linhas)
            and time_re.match(linhas[i + 1])
            and pct_re.match(linhas[i + 2])
            and money_re.match(linhas[i + 3])
            and pct_re.match(linhas[i + 4])
        ):
            registros.append({
                'cliente': linha,
                'tempo_gasto': linhas[i + 1],
                'tempo_minutos': round(converter_tempo_para_minutos(linhas[i + 1]), 2),
                'pct_tempo': parsear_percentual(linhas[i + 2]),
                'faturamento': parsear_valor_monetario(linhas[i + 3]),
                'pct_faturamento': parsear_percentual(linhas[i + 4]),
            })
            i += 5
            continue

        i += 1

    return registros


def extrair_faturamento_pdf(caminho_pdf):
    print(f"💰 Extraindo faturamento: {caminho_pdf}")
    linhas = extrair_linhas_pdf(caminho_pdf)
    registros = parsear_faturamento(linhas)
    if not registros:
        raise ValueError("Nenhum registro de faturamento extraído do PDF")
    return pd.DataFrame(registros)


def buscar_cliente_faturamento(nome_produtividade, df_faturamento):
    nome_norm = normalizar_nome_cliente(nome_produtividade)
    prefixo = nome_norm[:18]

    for _, row in df_faturamento.iterrows():
        cliente_norm = normalizar_nome_cliente(row['cliente'])
        if (
            cliente_norm.startswith(prefixo)
            or prefixo.startswith(cliente_norm[:18])
            or nome_norm in cliente_norm
            or cliente_norm in nome_norm
        ):
            return row

    return None


def gerar_aba_faturamento(df_faturamento):
    df = df_faturamento.copy()
    df['Tempo (HH:MM:SS)'] = df['tempo_minutos'].apply(minutos_para_hora_minuto_segundo)
    df = df.sort_values(['faturamento', 'tempo_minutos'], ascending=[False, False])

    df_saida = df.rename(columns={
        'cliente': 'Cliente',
        'pct_tempo': '% Tempo',
        'faturamento': 'Faturamento (R$)',
        'pct_faturamento': '% Faturamento',
    })
    df_saida = df_saida[[
        'Cliente', 'Tempo (HH:MM:SS)', '% Tempo',
        'Faturamento (R$)', '% Faturamento',
    ]]

    total_faturamento = df['faturamento'].sum()
    total_tempo = df['tempo_minutos'].sum()
    df_saida = pd.concat([
        df_saida,
        pd.DataFrame([{
            'Cliente': 'TOTAL GERAL',
            'Tempo (HH:MM:SS)': minutos_para_hora_minuto_segundo(total_tempo),
            '% Tempo': round(df['pct_tempo'].sum(), 2),
            'Faturamento (R$)': round(total_faturamento, 2),
            '% Faturamento': round(df['pct_faturamento'].sum(), 2),
        }]),
    ], ignore_index=True)

    return df_saida


def gerar_aba_tempo_faturamento(df_produtividade, df_faturamento):
    tempo_por_cliente = (
        df_produtividade.groupby('cliente', as_index=False)
        .agg(
            Tempo_Produtividade_Min=('tempo_minutos', 'sum'),
            Funcionarios=('usuario', 'nunique'),
            Atividades=('tempo_gasto', 'count'),
        )
        .sort_values('Tempo_Produtividade_Min', ascending=False)
    )

    linhas = []
    for _, row in tempo_por_cliente.iterrows():
        fat = buscar_cliente_faturamento(row['cliente'], df_faturamento)
        linhas.append({
            'Cliente (Produtividade)': row['cliente'],
            'Cliente (Faturamento)': fat['cliente'] if fat is not None else '',
            'Tempo Produtividade': minutos_para_hora_minuto_segundo(row['Tempo_Produtividade_Min']),
            'Tempo Custo Benefício': fat['tempo_gasto'] if fat is not None else '',
            '% Tempo': fat['pct_tempo'] if fat is not None else '',
            'Faturamento (R$)': round(fat['faturamento'], 2) if fat is not None else 0.0,
            '% Faturamento': fat['pct_faturamento'] if fat is not None else '',
            'Funcionários': row['Funcionarios'],
            'Atividades': row['Atividades'],
        })

    return pd.DataFrame(linhas)


def gerar_aba_detalhes_funcionario_top10_clientes(df, top_clientes=10):
    dados_funcionarios = defaultdict(lambda: defaultdict(float))
    for _, row in df.iterrows():
        dados_funcionarios[row['usuario']][row['cliente']] += row['tempo_minutos']

    funcionarios_ordenados = sorted(
        ((func, sum(clientes.values()), clientes) for func, clientes in dados_funcionarios.items()),
        key=lambda x: x[1],
        reverse=True,
    )

    detalhamento = []
    for funcionario, tempo_total, clientes in funcionarios_ordenados:
        detalhamento.append({
            'Funcionário': funcionario,
            'Cliente': '',
            'Tempo (HH:MM:SS)': minutos_para_hora_minuto_segundo(tempo_total),
        })
        for cliente, tempo in sorted(clientes.items(), key=lambda x: x[1], reverse=True)[:top_clientes]:
            detalhamento.append({
                'Funcionário': '',
                'Cliente': cliente,
                'Tempo (HH:MM:SS)': minutos_para_hora_minuto_segundo(tempo),
            })
        detalhamento.append({'Funcionário': '', 'Cliente': '', 'Tempo (HH:MM:SS)': ''})

    return pd.DataFrame(detalhamento)


def ajustar_colunas(worksheet, dataframe):
    for idx, col in enumerate(dataframe.columns, start=1):
        max_len = max((len(str(val)) for val in dataframe[col].astype(str)), default=0)
        max_len = max(max_len, len(str(col)))
        worksheet.column_dimensions[get_column_letter(idx)].width = min(max_len + 2, 50)


def gerar_planilha_excel(df, resumos, caminho_saida, df_faturamento=None):
    df_export = df.drop(columns=['tempo_minutos'])
    df_det, df_res_func, df_res_emp = gerar_aba_detalhamento_funcionario(df)
    df_detalhes = gerar_aba_detalhes_funcionario_top10_clientes(df)

    abas_extras = {}
    if df_faturamento is not None and not df_faturamento.empty:
        abas_extras['Faturamento Clientes'] = gerar_aba_faturamento(df_faturamento)
        abas_extras['Tempo x Faturamento'] = gerar_aba_tempo_faturamento(df, df_faturamento)

    with pd.ExcelWriter(caminho_saida, engine='openpyxl') as writer:
        df_export.to_excel(writer, sheet_name='Atividades Detalhadas', index=False)
        for nome, resumo in resumos.items():
            resumo.to_excel(writer, sheet_name=nome, index=False)
        df_det.to_excel(writer, sheet_name='Detalhamento Funcionário', index=False)
        df_detalhes.to_excel(writer, sheet_name='Detalhes Func - Top 10 Clientes', index=False)
        for nome, aba in abas_extras.items():
            aba.to_excel(writer, sheet_name=nome, index=False)
        df_res_func.to_excel(writer, sheet_name='Resumo Funcionários', index=False)
        df_res_emp.to_excel(writer, sheet_name='Resumo Empresas', index=False)

        planilhas = {
            'Atividades Detalhadas': df_export,
            **{nome: resumo for nome, resumo in resumos.items()},
            'Detalhamento Funcionário': df_det,
            'Detalhes Func - Top 10 Clientes': df_detalhes,
            **abas_extras,
            'Resumo Funcionários': df_res_func,
            'Resumo Empresas': df_res_emp,
        }
        for sheet_name, dataframe in planilhas.items():
            ajustar_colunas(writer.sheets[sheet_name], dataframe)


def processar_pdf(caminho_pdf, caminho_saida, caminho_pdf_faturamento=None):
    print(f"📄 Extraindo: {caminho_pdf}")
    linhas = extrair_linhas_pdf(caminho_pdf)
    atividades = parsear_atividades(linhas)

    if not atividades:
        raise ValueError("Nenhuma atividade extraída do PDF")

    df = pd.DataFrame(atividades)
    resumos = gerar_resumos(df)

    df_faturamento = None
    if caminho_pdf_faturamento:
        if os.path.exists(caminho_pdf_faturamento):
            df_faturamento = extrair_faturamento_pdf(caminho_pdf_faturamento)
            print(f"💰 Clientes com faturamento: {len(df_faturamento)}")
            print(f"💰 Total faturado: R$ {df_faturamento['faturamento'].sum():,.2f}")
        else:
            print(f"⚠️  PDF de faturamento não encontrado: {caminho_pdf_faturamento}")

    gerar_planilha_excel(df, resumos, caminho_saida, df_faturamento)

    tempo_total = df['tempo_minutos'].sum()
    print(f"✅ Planilha gerada: {caminho_saida}")
    print(f"📊 Atividades: {len(df)}")
    print(f"👥 Usuários: {df['usuario'].nunique()}")
    print(f"🏢 Clientes: {df['cliente'].nunique()}")
    print(f"📅 Dias: {df['data'].nunique()}")
    print(f"⏰ Tempo total: {minutos_para_hora_minuto_segundo(tempo_total)}")

    csv_saida = caminho_saida.replace('.xlsx', '.csv')
    df.to_csv(csv_saida, index=False, encoding='utf-8-sig')
    print(f"💾 CSV salvo: {csv_saida}")


def main():
    parser = argparse.ArgumentParser(description='Processar PDFs de produtividade e faturamento')
    parser.add_argument(
        '--pdf',
        default='produtividade/UsuárioTempo Gasto-junho-2026.pdf',
        help='Caminho do PDF de tempo por usuário',
    )
    parser.add_argument(
        '--pdf-faturamento',
        default='produtividade/ctudo-beneficio-junho-2026.pdf',
        help='Caminho do PDF de custo benefício / faturamento',
    )
    parser.add_argument(
        '--saida',
        default='produtividade/conferencia_produtividade_junho_2026.xlsx',
        help='Caminho da planilha Excel de saída',
    )
    parser.add_argument(
        '--sem-faturamento',
        action='store_true',
        help='Não incluir dados de faturamento',
    )
    args = parser.parse_args()

    print("🚀 PROCESSAMENTO PDF PRODUTIVIDADE + FATURAMENTO")
    print("=" * 60)
    print(f"Data de geração: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    processar_pdf(
        args.pdf,
        args.saida,
        None if args.sem_faturamento else args.pdf_faturamento,
    )


if __name__ == '__main__':
    main()
