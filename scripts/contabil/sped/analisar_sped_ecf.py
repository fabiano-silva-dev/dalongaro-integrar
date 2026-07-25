"""
Script utilitário para inspecionar arquivos SPED ECF em formato texto (campos delimitados por "|").

Ele gera um resumo estatístico por registro e destaca problemas comuns, como variação no número
de campos ou campos vazios. Ideal para explorar rapidamente o conteúdo antes de análises mais
aprofundadas.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Tuple


MAX_EXEMPLOS_POR_REGISTRO = 5


class RegistroResumo:
    def __init__(self) -> None:
        self.quantidade = 0
        self.tamanho_campos = Counter()
        self.campos_vazios = Counter()
        self.exemplos: List[List[str]] = []

    def adicionar_ocorrencia(self, valores: List[str]) -> None:
        self.quantidade += 1
        self.tamanho_campos[len(valores)] += 1

        for indice, valor in enumerate(valores, start=1):
            if not valor.strip():
                self.campos_vazios[indice] += 1

        if len(self.exemplos) < MAX_EXEMPLOS_POR_REGISTRO:
            self.exemplos.append(valores)

    def como_dict(self) -> dict:
        return {
            "quantidade": self.quantidade,
            "distribuicao_tamanho": dict(self.tamanho_campos),
            "campos_vazios": dict(self.campos_vazios),
            "exemplos": self.exemplos,
        }


def ler_registros(caminho: Path) -> Iterator[Tuple[str, List[str]]]:
    with caminho.open("r", encoding="utf-8", errors="ignore") as arquivo:
        for linha in arquivo:
            linha = linha.rstrip("\n")
            if not linha.strip():
                continue

            partes = linha.strip().split("|")

            if len(partes) < 3:
                continue

            partes = partes[1:-1] if partes[-1] == "" else partes[1:]

            if not partes:
                continue

            registro = partes[0]
            valores = partes[1:]
            yield registro, valores


def resumir_arquivo(caminho: Path) -> dict:
    resumos: dict[str, RegistroResumo] = defaultdict(RegistroResumo)
    total_linhas = 0

    for registro, valores in ler_registros(caminho):
        resumos[registro].adicionar_ocorrencia(valores)
        total_linhas += 1

    return {
        "arquivo": str(caminho),
        "total_registros": total_linhas,
        "registros": {chave: resumo.como_dict() for chave, resumo in sorted(resumos.items())},
    }


def imprimir_resumo(resumo: dict, mostrar_exemplos: bool) -> None:
    registros = resumo["registros"]

    print(f"Arquivo analisado: {resumo['arquivo']}")
    print(f"Total de registros lidos: {resumo['total_registros']}")
    print(f"Quantidade de tipos de registro: {len(registros)}\n")

    print("Resumo por registro (ordenado por quantidade):\n")
    ordenado = sorted(
        registros.items(),
        key=lambda item: item[1]["quantidade"],
        reverse=True,
    )

    for registro, dados in ordenado:
        print(f"Registro {registro}:")
        print(f"  - Ocorrências: {dados['quantidade']}")
        dist = ", ".join(f"{tam}:{freq}" for tam, freq in sorted(dados["distribuicao_tamanho"].items()))
        print(f"  - Distribuição de campos: {dist or 'não identificado'}")

        if dados["campos_vazios"]:
            vazios = ", ".join(f"campo_{idx}: {freq}" for idx, freq in sorted(dados["campos_vazios"].items()))
            print(f"  - Campos vazios detectados: {vazios}")
        else:
            print("  - Campos vazios detectados: nenhum")

        if mostrar_exemplos and dados["exemplos"]:
            print("  - Exemplos:")
            for exemplo in dados["exemplos"]:
                print("    ", json.dumps(exemplo, ensure_ascii=False))
        print()


def montar_argumentos(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gera um resumo estatístico do conteúdo de um arquivo SPED ECF.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("arquivo", type=Path, help="Caminho do arquivo de texto a ser analisado.")
    parser.add_argument(
        "--mostrar-exemplos",
        action="store_true",
        help=f"Exibe até {MAX_EXEMPLOS_POR_REGISTRO} exemplos de linhas por registro.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Exporta o resumo completo em formato JSON (stdout).",
    )
    parser.add_argument(
        "--registro",
        help="Exibe todas as ocorrências (ou as primeiras) de um registro específico.",
    )
    parser.add_argument(
        "--limite",
        type=int,
        default=20,
        help="Limite máximo de linhas ao exibir um registro específico (0 = sem limite).",
    )
    parser.add_argument(
        "--exportar-csv",
        type=Path,
        metavar="PASTA",
        help="Exporta cada registro para um arquivo CSV na pasta indicada.",
    )
    parser.add_argument(
        "--relatorio",
        type=Path,
        metavar="ARQUIVO",
        help="Gera um relatório detalhado em formato Markdown contendo análises do arquivo.",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        help="Quantidade de registros destacados nas tabelas do relatório detalhado.",
    )
    return parser.parse_args(argv)


def mostrar_registro_especifico(caminho: Path, codigo_registro: str, limite: int) -> None:
    print(f"\nOcorrências do registro {codigo_registro}:\n")
    encontrados = 0

    for registro, valores in ler_registros(caminho):
        if registro != codigo_registro:
            continue

        encontrados += 1
        print(f"[{encontrados}] {json.dumps(valores, ensure_ascii=False)}")

        if limite > 0 and encontrados >= limite:
            break

    if encontrados == 0:
        print("Nenhuma ocorrência encontrada.")
    elif limite > 0 and encontrados >= limite:
        print(f"... Limite de {limite} ocorrências atingido. Existem mais linhas no arquivo.")
    else:
        print("Fim das ocorrências.")


def exportar_registros_para_csv(caminho_arquivo: Path, pasta_destino: Path) -> None:
    pasta_destino = pasta_destino.expanduser().resolve()
    pasta_destino.mkdir(parents=True, exist_ok=True)

    arquivos_abertos: Dict[str, Tuple[Path, csv.writer]] = {}
    nome_sanitizado_cache: Dict[str, str] = {}

    try:
        for registro, valores in ler_registros(caminho_arquivo):
            if registro not in nome_sanitizado_cache:
                nome_limpo = re.sub(r"[^0-9A-Za-z_.-]", "_", registro)
                if not nome_limpo:
                    nome_limpo = f"registro_{hashlib.md5(registro.encode('utf-8', 'ignore')).hexdigest()[:8]}"
                nome_sanitizado_cache[registro] = nome_limpo

            nome_arquivo = nome_sanitizado_cache[registro]
            if registro not in arquivos_abertos:
                caminho_csv = pasta_destino / f"{nome_arquivo}.csv"
                arquivo = caminho_csv.open("w", encoding="utf-8", newline="")
                writer = csv.writer(
                    arquivo,
                    delimiter=";",
                    quoting=csv.QUOTE_MINIMAL,
                    escapechar="\\",
                )
                arquivos_abertos[registro] = (arquivo, writer)

            arquivo, writer = arquivos_abertos[registro]
            writer.writerow(valores)
    finally:
        for arquivo, _ in arquivos_abertos.values():
            arquivo.close()

    print(f"\nExportação concluída em: {pasta_destino}")
    print("Arquivos gerados: ", ", ".join(sorted(arquivos_abertos.keys())))


def gerar_relatorio_markdown(resumo: dict, caminho_relatorio: Path, top: int) -> None:
    registros = resumo["registros"]
    total = resumo["total_registros"]

    ordenado = sorted(registros.items(), key=lambda item: item[1]["quantidade"], reverse=True)

    variacoes = [
        (codigo, dados)
        for codigo, dados in registros.items()
        if len(dados["distribuicao_tamanho"]) > 1
    ]

    campos_vazios = []
    for codigo, dados in registros.items():
        if not dados["campos_vazios"]:
            continue
        total_reg = dados["quantidade"]
        for indice, freq in dados["campos_vazios"].items():
            proporcao = freq / total_reg if total_reg else 0
            campos_vazios.append((codigo, indice, freq, proporcao, total_reg))

    campos_vazios.sort(key=lambda item: item[3], reverse=True)

    regex_codigo = re.compile(r"^[0-9A-Z]+$")
    registros_incomuns = [
        (codigo, dados["quantidade"])
        for codigo, dados in registros.items()
        if not regex_codigo.match(codigo)
    ]

    linhas: List[str] = []
    linhas.append("# Relatório Analítico do Arquivo SPED ECF\n\n")
    linhas.append(f"- Arquivo analisado: `{resumo['arquivo']}`\n")
    linhas.append(f"- Total de registros: {total}\n")
    linhas.append(f"- Total de tipos distintos: {len(registros)}\n\n")

    linhas.append("## Top registros por quantidade\n\n")
    linhas.append("| Registro | Ocorrências | % do total | Distribuição de campos |\n")
    linhas.append("|---|---:|---:|---|\n")
    for codigo, dados in ordenado[:top]:
        proporcao = dados["quantidade"] / total if total else 0
        dist = ", ".join(f"{tam}:{freq}" for tam, freq in sorted(dados["distribuicao_tamanho"].items()))
        linhas.append(f"| {codigo} | {dados['quantidade']} | {proporcao:.2%} | {dist} |\n")

    if variacoes:
        linhas.append("\n## Registros com variação na contagem de campos\n\n")
        linhas.append("| Registro | Distribuições detectadas |\n")
        linhas.append("|---|---|\n")
        for codigo, dados in sorted(variacoes, key=lambda item: item[0]):
            dist = ", ".join(f"{tam}:{freq}" for tam, freq in sorted(dados["distribuicao_tamanho"].items()))
            linhas.append(f"| {codigo} | {dist} |\n")

    if campos_vazios:
        linhas.append("\n## Campos com maior incidência de valores vazios\n\n")
        linhas.append("| Registro | Campo | Ocorrências vazias | % dentro do registro | Total do registro |\n")
        linhas.append("|---|---|---:|---:|---:|\n")
        for codigo, indice, freq, proporcao, total_reg in campos_vazios[: top * 3]:
            linhas.append(f"| {codigo} | {indice} | {freq} | {proporcao:.2%} | {total_reg} |\n")

    if registros_incomuns:
        linhas.append("\n## Registros com códigos não usuais\n\n")
        linhas.append("| Registro | Ocorrências |\n")
        linhas.append("|---|---:|\n")
        for codigo, quantidade in sorted(registros_incomuns, key=lambda item: item[1], reverse=True):
            linhas.append(f"| `{codigo}` | {quantidade} |\n")

    linhas.append("\n## Exemplos coletados\n\n")
    for codigo, dados in ordenado[:top]:
        if not dados["exemplos"]:
            continue
        linhas.append(f"### Registro {codigo}\n\n")
        linhas.append("| # | Valores |\n")
        linhas.append("|---|---|\n")
        for idx, exemplo in enumerate(dados["exemplos"], start=1):
            linhas.append(f"| {idx} | `{json.dumps(exemplo, ensure_ascii=False)}` |\n")
        linhas.append("\n")

    caminho_relatorio = caminho_relatorio.expanduser().resolve()
    caminho_relatorio.parent.mkdir(parents=True, exist_ok=True)
    caminho_relatorio.write_text("".join(linhas), encoding="utf-8")
    print(f"\nRelatório detalhado salvo em: {caminho_relatorio}")


def main(argv: Iterable[str] | None = None) -> None:
    args = montar_argumentos(argv)
    caminho = args.arquivo.expanduser().resolve()

    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")

    resumo = resumir_arquivo(caminho)

    if args.json:
        print(json.dumps(resumo, ensure_ascii=False, indent=2))
    else:
        imprimir_resumo(resumo, mostrar_exemplos=args.mostrar_exemplos)

    if args.registro:
        mostrar_registro_especifico(caminho, args.registro, args.limite)

    if args.exportar_csv:
        exportar_registros_para_csv(caminho, args.exportar_csv)

    if args.relatorio:
        gerar_relatorio_markdown(resumo, args.relatorio, args.top)


if __name__ == "__main__":
    main()


