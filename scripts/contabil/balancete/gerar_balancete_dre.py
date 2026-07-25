"""
Gera balancete e demonstração de resultados (DRE) a partir de um arquivo SPED ECF.

Para cada período (registro L030) são extraídos:
- Registros L100: estrutura de contas patrimoniais, formando o balancete.
- Registros L300: estrutura da DRE.

São produzidos quatro arquivos CSV (delimitador ";"):
1. balancete_detalhado.csv  → todas as contas do L100 com saldos e sinais.
2. balancete_resumo.csv     → consolidação por contas sintéticas (nível ≤ 2).
3. dre_detalhada.csv        → todas as contas do L300 com valores e sinais.
4. dre_resumo.csv           → consolidação da DRE por contas sintéticas (nível ≤ 3).

Uso:
    python gerar_balancete_dre.py caminho/para/SPED.txt --saida caminho/para/pasta_saida

Obs.: Os valores com sinal seguem a convenção contábil:
      - 'D' (débito) é tratado como positivo.
      - 'C' (crédito) é tratado como negativo.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Tuple


SIGNOTE = {"D": Decimal("1"), "C": Decimal("-1")}


@dataclass
class Periodo:
    codigo: str
    data_inicio: str
    data_fim: str


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extrai balancete e DRE de um arquivo SPED ECF (registros L100 e L300).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("arquivo", type=Path, help="Arquivo SPED ECF (.txt) a ser processado.")
    parser.add_argument(
        "--saida",
        type=Path,
        default=Path("relatorios_contabeis"),
        help="Pasta onde os CSVs gerados serão gravados.",
    )
    parser.add_argument(
        "--periodo",
        help="Limita a saída a um período específico (ex.: A00, A06...). Por padrão exporta todos.",
    )
    return parser.parse_args(argv)


def ler_registros(caminho: Path) -> Iterator[Tuple[str, List[str]]]:
    with caminho.open("r", encoding="utf-8", errors="ignore") as arquivo:
        for linha in arquivo:
            linha = linha.rstrip("\n")
            if not linha.strip():
                continue

            partes = linha.split("|")
            if len(partes) < 3:
                continue

            partes = partes[1:-1] if partes[-1] == "" else partes[1:]
            if not partes:
                continue

            yield partes[0], partes[1:]


def normalizar_decimal(valor: str) -> Decimal:
    texto = valor.strip()
    if not texto:
        return Decimal("0")
    texto = texto.replace(".", "").replace(",", ".")
    try:
        return Decimal(texto)
    except InvalidOperation:
        raise ValueError(f"Valor numérico inválido: {valor!r}")


def to_int(texto: str) -> Optional[int]:
    texto = texto.strip()
    if not texto:
        return None
    try:
        return int(texto)
    except ValueError:
        return None


def sinalizar(valor: Decimal, indicador: str) -> Decimal:
    return valor * SIGNOTE.get(indicador, Decimal("1"))


def escrever_csv(caminho: Path, cabecalho: List[str], linhas: List[Dict[str, object]]) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8", newline="") as arquivo:
        writer = csv.DictWriter(
            arquivo,
            fieldnames=cabecalho,
            delimiter=";",
            quoting=csv.QUOTE_MINIMAL,
        )
        writer.writeheader()
        for linha in linhas:
            writer.writerow(linha)


def processar_sped(
    caminho: Path,
    periodo_alvo: Optional[str] = None,
) -> Tuple[List[Dict[str, object]], List[Dict[str, object]], List[Dict[str, object]], List[Dict[str, object]]]:
    periodos: Dict[str, Periodo] = {}
    balancete_detalhado: List[Dict[str, object]] = []
    dre_detalhado: List[Dict[str, object]] = []

    periodo_atual: Optional[Periodo] = None

    for registro, valores in ler_registros(caminho):
        if registro == "L030":
            if len(valores) < 3:
                continue
            periodo_atual = Periodo(codigo=valores[2], data_inicio=valores[0], data_fim=valores[1])
            periodos[periodo_atual.codigo] = periodo_atual
            continue

        if periodo_atual is None:
            continue

        if periodo_alvo and periodo_atual.codigo != periodo_alvo:
            continue

        if registro == "L100" and len(valores) >= 12:
            saldo_inicial = normalizar_decimal(valores[8])
            saldo_final = normalizar_decimal(valores[9])
            saldo_resultado = normalizar_decimal(valores[10])

            ind_inicio = valores[7].strip()
            ind_resultado = valores[11].strip()

            saldo_inicial_sinal = sinalizar(saldo_inicial, ind_inicio)
            saldo_resultado_sinal = sinalizar(saldo_resultado, ind_resultado)
            saldo_final_sinal_estimado = saldo_inicial_sinal + saldo_resultado_sinal

            balancete_detalhado.append(
                {
                    "periodo": periodo_atual.codigo,
                    "data_inicio": periodo_atual.data_inicio,
                    "data_fim": periodo_atual.data_fim,
                    "codigo": valores[0],
                    "descricao": valores[1],
                    "tipo_conta": valores[2],
                    "nivel": to_int(valores[3]),
                    "cod_indicador": valores[4],
                    "conta_superior": valores[5],
                    "cod_aglutinador": valores[6],
                    "ind_saldo_inicial": ind_inicio,
                    "saldo_inicial": float(saldo_inicial),
                    "saldo_inicial_sinal": float(saldo_inicial_sinal),
                    "saldo_final": float(saldo_final),
                    "saldo_resultado": float(saldo_resultado),
                    "ind_resultado": ind_resultado,
                    "saldo_resultado_sinal": float(saldo_resultado_sinal),
                    "saldo_final_estimado_sinal": float(saldo_final_sinal_estimado),
                }
            )

        elif registro == "L300" and len(valores) >= 8:
            valor = normalizar_decimal(valores[6])
            ind_dc = valores[7].strip()
            valor_sinal = sinalizar(valor, ind_dc)

            dre_detalhado.append(
                {
                    "periodo": periodo_atual.codigo,
                    "data_inicio": periodo_atual.data_inicio,
                    "data_fim": periodo_atual.data_fim,
                    "codigo": valores[0],
                    "descricao": valores[1],
                    "tipo_conta": valores[2],
                    "nivel": to_int(valores[3]),
                    "cod_indicador": valores[4],
                    "conta_superior": valores[5],
                    "valor": float(valor),
                    "ind_dc": ind_dc,
                    "valor_sinal": float(valor_sinal),
                }
            )

    balancete_resumo = consolidar_balancete(balancete_detalhado)
    dre_resumo = consolidar_dre(dre_detalhado)

    return balancete_detalhado, balancete_resumo, dre_detalhado, dre_resumo


def consolidar_balancete(linhas: List[Dict[str, object]]) -> List[Dict[str, object]]:
    agregados: Dict[Tuple[str, str], Dict[str, object]] = {}
    for linha in linhas:
        if linha["tipo_conta"] != "S":
            continue

        nivel = linha["nivel"]
        if nivel is None or nivel > 2:
            continue

        chave = (linha["periodo"], linha["codigo"])
        acumulado = agregados.get(chave)
        if acumulado is None:
            acumulado = {
                "periodo": linha["periodo"],
                "data_inicio": linha["data_inicio"],
                "data_fim": linha["data_fim"],
                "codigo": linha["codigo"],
                "descricao": linha["descricao"],
                "nivel": nivel,
                "saldo_inicial_sinal": Decimal("0"),
                "saldo_resultado_sinal": Decimal("0"),
                "saldo_final_estimado_sinal": Decimal("0"),
            }
            agregados[chave] = acumulado

        acumulado["saldo_inicial_sinal"] += Decimal(str(linha["saldo_inicial_sinal"]))
        acumulado["saldo_resultado_sinal"] += Decimal(str(linha["saldo_resultado_sinal"]))
        acumulado["saldo_final_estimado_sinal"] += Decimal(str(linha["saldo_final_estimado_sinal"]))

    resultado: List[Dict[str, object]] = []
    for acumulado in agregados.values():
        resultado.append(
            {
                **{chave: acumulado[chave] for chave in ("periodo", "data_inicio", "data_fim", "codigo", "descricao", "nivel")},
                "saldo_inicial_sinal": float(acumulado["saldo_inicial_sinal"]),
                "saldo_resultado_sinal": float(acumulado["saldo_resultado_sinal"]),
                "saldo_final_estimado_sinal": float(acumulado["saldo_final_estimado_sinal"]),
            }
        )

    resultado.sort(key=lambda item: (item["periodo"], item["codigo"]))
    return resultado


def consolidar_dre(linhas: List[Dict[str, object]]) -> List[Dict[str, object]]:
    agregados: Dict[Tuple[str, str], Dict[str, object]] = {}
    for linha in linhas:
        if linha["tipo_conta"] != "S":
            continue

        nivel = linha["nivel"]
        if nivel is None or nivel > 3:
            continue

        chave = (linha["periodo"], linha["codigo"])
        acumulado = agregados.get(chave)
        if acumulado is None:
            acumulado = {
                "periodo": linha["periodo"],
                "data_inicio": linha["data_inicio"],
                "data_fim": linha["data_fim"],
                "codigo": linha["codigo"],
                "descricao": linha["descricao"],
                "nivel": nivel,
                "valor_sinal": Decimal("0"),
            }
            agregados[chave] = acumulado

        acumulado["valor_sinal"] += Decimal(str(linha["valor_sinal"]))

    resultado: List[Dict[str, object]] = []
    for acumulado in agregados.values():
        resultado.append(
            {
                **{chave: acumulado[chave] for chave in ("periodo", "data_inicio", "data_fim", "codigo", "descricao", "nivel")},
                "valor_sinal": float(acumulado["valor_sinal"]),
            }
        )

    resultado.sort(key=lambda item: (item["periodo"], item["codigo"]))
    return resultado


def main(argv: Iterable[str] | None = None) -> None:
    args = parse_args(argv)
    arquivo = args.arquivo.expanduser().resolve()
    if not arquivo.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {arquivo}")

    balancete_det, balancete_res, dre_det, dre_res = processar_sped(arquivo, periodo_alvo=args.periodo)

    destino = args.saida.expanduser().resolve()

    escrever_csv(
        destino / "balancete_detalhado.csv",
        [
            "periodo",
            "data_inicio",
            "data_fim",
            "codigo",
            "descricao",
            "tipo_conta",
            "nivel",
            "cod_indicador",
            "conta_superior",
            "cod_aglutinador",
            "ind_saldo_inicial",
            "saldo_inicial",
            "saldo_inicial_sinal",
            "saldo_final",
            "saldo_resultado",
            "ind_resultado",
            "saldo_resultado_sinal",
            "saldo_final_estimado_sinal",
        ],
        balancete_det,
    )

    escrever_csv(
        destino / "balancete_resumo.csv",
        [
            "periodo",
            "data_inicio",
            "data_fim",
            "codigo",
            "descricao",
            "nivel",
            "saldo_inicial_sinal",
            "saldo_resultado_sinal",
            "saldo_final_estimado_sinal",
        ],
        balancete_res,
    )

    escrever_csv(
        destino / "dre_detalhada.csv",
        [
            "periodo",
            "data_inicio",
            "data_fim",
            "codigo",
            "descricao",
            "tipo_conta",
            "nivel",
            "cod_indicador",
            "conta_superior",
            "valor",
            "ind_dc",
            "valor_sinal",
        ],
        dre_det,
    )

    escrever_csv(
        destino / "dre_resumo.csv",
        [
            "periodo",
            "data_inicio",
            "data_fim",
            "codigo",
            "descricao",
            "nivel",
            "valor_sinal",
        ],
        dre_res,
    )

    print(f"Arquivos gerados em: {destino}")


if __name__ == "__main__":
    main()


