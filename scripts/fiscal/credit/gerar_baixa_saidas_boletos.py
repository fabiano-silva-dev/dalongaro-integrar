#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gera arquivo baixa_sai.txt para importação no Domínio (Baixa de Parcelas de Saídas).

Lê a aba BOLETOS de planilhas como 06.2026.xlsx e produz o TXT conforme o leiaute
Importacao_Baixas_Saidas/Conjunto de Dados.xml (código 9043):

  separador ;, decimal vírgula, 12 colunas, sem linha de cabeçalho no TXT.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date, datetime
from pathlib import Path

import openpyxl

_SCRIPTS = Path(__file__).resolve().parents[2]
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from paths import cliente
from runtime import setup_workspace

COLUNAS_BOLETOS = {
    "nr": 0,
    "nome": 1,
    "cpf_cnpj": 2,
    "emissao": 3,
    "vencimento": 4,
    "nosso_numero": 5,
    "seu_numero": 6,
    "situacao": 7,
    "data_situacao": 8,
    "valor": 9,
    "valor_liquidacao": 10,
    "tipo_liquidacao": 11,
}

CABECALHO_TXT = [
    "Número da Nota",
    "CNPJ do Cliente",
    "Data de Vencimento",
    "Data de Baixa",
    "Valor Recebido",
    "Valor Juros",
    "Valor Multa",
    "Valor Desconto",
    "Valor PIS",
    "Valor COFINS",
    "Valor CSLL",
    "Valor IRRF",
]


def parse_valor_br(valor) -> float:
    if valor is None or valor == "":
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = str(valor).strip().replace("R$", "").replace(" ", "")
    texto = texto.replace(".", "").replace(",", ".")
    return float(texto) if texto else 0.0


def formatar_valor(valor: float) -> str:
    return f"{valor:.2f}".replace(".", ",")


def formatar_data(valor) -> str:
    if valor is None or valor == "":
        return ""
    if isinstance(valor, datetime):
        return valor.strftime("%d/%m/%Y")
    if isinstance(valor, date):
        return valor.strftime("%d/%m/%Y")
    texto = str(valor).strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(texto[:10], fmt).strftime("%d/%m/%Y")
        except ValueError:
            continue
    return texto


def somente_digitos(valor) -> str:
    return re.sub(r"\D", "", str(valor or ""))


def localizar_aba_boletos(nomes_abas: list[str]) -> str | None:
    for nome in nomes_abas:
        if nome.strip().lower() == "boletos":
            return nome
    return None


def linha_boletos_para_baixa(row: tuple) -> dict | None:
    situacao = str(row[COLUNAS_BOLETOS["situacao"]] or "").strip().lower()
    if situacao != "liquidado":
        return None

    cnpj_cliente = somente_digitos(row[COLUNAS_BOLETOS["cpf_cnpj"]])
    data_vencimento = formatar_data(row[COLUNAS_BOLETOS["vencimento"]])
    data_baixa = formatar_data(row[COLUNAS_BOLETOS["data_situacao"]])

    valor_titulo = parse_valor_br(row[COLUNAS_BOLETOS["valor"]])
    valor_liquidacao = parse_valor_br(row[COLUNAS_BOLETOS["valor_liquidacao"]])
    diferenca = round(valor_liquidacao - valor_titulo, 2)

    valor_juros = diferenca if diferenca > 0 else 0.0
    valor_desconto = abs(diferenca) if diferenca < 0 else 0.0

    if not cnpj_cliente or not data_vencimento or not data_baixa:
        return None

    return {
        "numero_nota": "",
        "cnpj_cliente": cnpj_cliente,
        "data_vencimento": data_vencimento,
        "data_baixa": data_baixa,
        "valor_recebido": valor_titulo,
        "valor_juros": valor_juros,
        "valor_multa": 0.0,
        "valor_desconto": valor_desconto,
        "valor_pis": 0.0,
        "valor_cofins": 0.0,
        "valor_csll": 0.0,
        "valor_irrf": 0.0,
        "seu_numero": str(row[COLUNAS_BOLETOS["seu_numero"]] or ""),
        "nome_pagador": str(row[COLUNAS_BOLETOS["nome"]] or ""),
    }


def formatar_linha_txt(registro: dict) -> str:
    valores = [
        registro["numero_nota"],
        registro["cnpj_cliente"],
        registro["data_vencimento"],
        registro["data_baixa"],
        formatar_valor(registro["valor_recebido"]),
        formatar_valor(registro["valor_juros"]),
        formatar_valor(registro["valor_multa"]),
        formatar_valor(registro["valor_desconto"]),
        formatar_valor(registro["valor_pis"]),
        formatar_valor(registro["valor_cofins"]),
        formatar_valor(registro["valor_csll"]),
        formatar_valor(registro["valor_irrf"]),
    ]
    return ";".join(valores)


def ler_boletos(planilha: Path) -> tuple[list[dict], list[str]]:
    if not planilha.exists():
        raise FileNotFoundError(f"Planilha não encontrada: {planilha}")

    wb = openpyxl.load_workbook(planilha, read_only=True, data_only=True)
    aba = localizar_aba_boletos(wb.sheetnames)
    if not aba:
        wb.close()
        raise ValueError(f"Aba BOLETOS não encontrada em {planilha.name}")

    registros: list[dict] = []
    ignorados: list[str] = []

    ws = wb[aba]
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row or not row[COLUNAS_BOLETOS["nr"]]:
            continue

        registro = linha_boletos_para_baixa(row)
        if registro:
            registros.append(registro)
        else:
            situacao = str(row[COLUNAS_BOLETOS["situacao"]] or "").strip()
            if situacao.lower() == "liquidado":
                seu_numero = row[COLUNAS_BOLETOS["seu_numero"]]
                ignorados.append(f"Linha {row[COLUNAS_BOLETOS['nr']]} ({seu_numero}): dados incompletos")

    wb.close()
    return registros, ignorados


def gerar_baixa_saidas(
    planilha: Path,
    saida: Path | None = None,
) -> Path:
    registros, ignorados = ler_boletos(planilha)

    if saida is None:
        saida = cliente("credit-578", "Importacao_Baixas_Saidas", "baixa_sai.txt")

    saida.parent.mkdir(parents=True, exist_ok=True)
    linhas = [formatar_linha_txt(r) for r in registros]
    conteudo = "\n".join(linhas)
    if linhas:
        conteudo += "\n"

    saida.write_text(conteudo, encoding="cp1252")

    print(f"Planilha: {planilha}")
    print(f"Registros gerados: {len(registros)}")
    print(f"Arquivo: {saida}")

    if ignorados:
        print(f"\nAvisos ({len(ignorados)}):")
        for aviso in ignorados[:10]:
            print(f"  - {aviso}")
        if len(ignorados) > 10:
            print(f"  ... e mais {len(ignorados) - 10}")

    if registros:
        amostra = registros[0]
        print("\nColunas:")
        print(";".join(CABECALHO_TXT))
        print("\nExemplo da primeira linha:")
        print(formatar_linha_txt(amostra))
        print(
            f"  ({amostra['nome_pagador']} | Seu Número: {amostra['seu_numero']})"
        )

    return saida


def main(argv: list[str] | None = None) -> int:
    setup_workspace()

    parser = argparse.ArgumentParser(
        description="Gera baixa_sai.txt para importação de baixas de saídas no Domínio."
    )
    parser.add_argument(
        "planilha",
        nargs="?",
        default=str(cliente("credit-578", "06.2026.xlsx")),
        help="Caminho da planilha com aba BOLETOS (padrão: clientes/credit-578/06.2026.xlsx)",
    )
    parser.add_argument(
        "-o",
        "--saida",
        help="Caminho do arquivo TXT de saída (padrão: Importacao_Baixas_Saidas/baixa_sai.txt)",
    )
    args = parser.parse_args(argv)

    planilha = Path(args.planilha)
    saida = Path(args.saida) if args.saida else None

    try:
        gerar_baixa_saidas(planilha, saida)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
