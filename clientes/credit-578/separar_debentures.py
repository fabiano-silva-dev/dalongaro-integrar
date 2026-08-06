#!/usr/bin/env python3
"""Separa e totaliza lançamentos de debêntures do arquivo Domínio 6100."""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent
SRC = BASE / "CONTABIL_DOMINIO_2_83_1_17072025_131325.TXT"
OUT_TXT = BASE / "CONTABIL_DEBENTURES_17072025.txt"
OUT_CSV = BASE / "debentures_total_junho_2025.csv"
OUT_RESUMO = BASE / "debentures_resumo_junho_2025.txt"


def brl(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def is_debentures(hist: str) -> bool:
    h = hist.upper()
    # encoding-safe: Ê/É podem vir corrompidos (DEB�NTURES)
    return "DEB" in h and "NTUR" in h


def main() -> None:
    text = SRC.read_bytes().decode("latin-1")
    lines = text.splitlines()

    # índices das partidas (6000 + 6100s)
    partida_idxs: list[list[int]] = []
    atual: list[int] = []
    for i, line in enumerate(lines):
        parts = line.split("|")
        if len(parts) < 2:
            continue
        tipo = parts[1]
        if tipo == "6000":
            if atual:
                partida_idxs.append(atual)
            atual = [i]
        elif tipo == "6100":
            atual.append(i)
    if atual:
        partida_idxs.append(atual)

    deb_idxs: list[list[int]] = []
    for idxs in partida_idxs:
        hists = []
        for i in idxs:
            parts = lines[i].split("|")
            if parts[1] == "6100" and len(parts) > 7:
                hists.append(parts[7])
        if any(is_debentures(h) for h in hists):
            deb_idxs.append(idxs)

    total_deb = total_cred = 0.0
    by_ref: dict[str, float] = defaultdict(float)
    by_date: dict[str, float] = defaultdict(float)
    contas: dict[str, float] = defaultdict(float)
    csv_rows: list[tuple[str, str, str, str, float, str]] = []

    for idxs in deb_idxs:
        for i in idxs:
            parts = lines[i].split("|")
            if parts[1] != "6100":
                continue
            data = parts[2]
            cdeb, ccred = parts[3], parts[4]
            valor = float(parts[5].replace(".", "").replace(",", "."))
            hist = parts[7] if len(parts) > 7 else ""
            m = re.search(r"INT-(\d+)", hist, re.I)
            ref = f"INT-{m.group(1)}" if m else "SEM-REF"
            csv_rows.append((data, ref, cdeb, ccred, valor, hist))
            if cdeb:
                total_deb += valor
                by_ref[ref] += valor
                by_date[data] += valor
                contas[f"D {cdeb}"] += valor
            if ccred:
                total_cred += valor
                contas[f"C {ccred}"] += valor

    def ref_key(r: str) -> int:
        m = re.search(r"\d+", r)
        return int(m.group()) if m else 0

    def date_key(d: str) -> tuple[str, str, str]:
        dd, mm, yy = d.split("/")
        return (yy, mm, dd)

    # Arquivo Domínio só com debêntures
    selected = [0]  # header |0000|CNPJ|
    for idxs in deb_idxs:
        selected.extend(idxs)
    with OUT_TXT.open("w", encoding="latin-1", newline="\n") as f:
        for i in selected:
            f.write(lines[i] + "\n")

    # CSV detalhado
    with OUT_CSV.open("w", encoding="utf-8-sig", newline="\n") as f:
        f.write("data;ref;conta_debito;conta_credito;valor;historico\n")
        for data, ref, cdeb, ccred, valor, hist in csv_rows:
            f.write(
                f"{data};{ref};{cdeb};{ccred};"
                f"{str(valor).replace('.', ',')};{hist}\n"
            )
        f.write(f"\nTOTAL_DEBITO;;;{str(total_deb).replace('.', ',')};\n")
        f.write(f"TOTAL_CREDITO;;;{str(total_cred).replace('.', ',')};\n")
        f.write(f"QTD_PARTIDAS;;;{len(deb_idxs)};\n")

    # Resumo
    with OUT_RESUMO.open("w", encoding="utf-8") as f:
        f.write(
            "CREDIT 578 — Rendimentos de Debêntures\n"
            f"Fonte: {SRC.name}\n"
        )
        f.write("=" * 72 + "\n")
        f.write(f"Partidas: {len(deb_idxs)}\n")
        f.write(f"Total débito:  {brl(total_deb)}\n")
        f.write(f"Total crédito: {brl(total_cred)}\n")
        f.write("Contas:\n")
        for k, v in sorted(contas.items()):
            f.write(f"  {k}: {brl(v)}\n")
        f.write("\nPor referência INT:\n")
        for ref, v in sorted(by_ref.items(), key=lambda x: ref_key(x[0])):
            f.write(f"  {ref}: {brl(v)}\n")
        f.write("\nPor data:\n")
        for d, v in sorted(by_date.items(), key=lambda x: date_key(x[0])):
            f.write(f"  {d}: {brl(v)}\n")

    print(f"Partidas: {len(deb_idxs)}")
    print(f"Total débito:  {brl(total_deb)}")
    print(f"Total crédito: {brl(total_cred)}")
    print("Contas:")
    for k, v in sorted(contas.items()):
        print(f"  {k}: {brl(v)}")
    print("\nPor INT:")
    for ref, v in sorted(by_ref.items(), key=lambda x: ref_key(x[0])):
        print(f"  {ref}: {brl(v)}")
    print("\nPor data:")
    for d, v in sorted(by_date.items(), key=lambda x: date_key(x[0])):
        print(f"  {d}: {brl(v)}")
    print("\nArquivos:")
    print(f"  {OUT_TXT.name} ({len(selected)} linhas)")
    print(f"  {OUT_CSV.name}")
    print(f"  {OUT_RESUMO.name}")


if __name__ == "__main__":
    main()
