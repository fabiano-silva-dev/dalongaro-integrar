#!/usr/bin/env python3
"""COOTRAFAX: extrai relatórios de CF, valida subtotais e prepara CSV contábil.

O CSV é de CONFERÊNCIA; não constitui leiaute de importação Domínio homologado.
"""
import argparse
import csv
import re
import sys
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import fitz

DEBITO = {"PF": "213", "PJ": "214"}
MOEDA = re.compile(r"^-?\d+(?:\.\d{3})*,\d{2}$")
CAB = re.compile(r"^(\d+) / ([^/]+) / ")
DATA = re.compile(r"^\d{2}/\d{2}/\d{2}$")
CAMPOS = ["periodo", "tipo", "codigo_cooperado", "cooperado", "data_emissao",
          "contrato", "veiculo", "valor_frete", "valor_documento", "valor_pedido",
          "valor_desconto", "valor_total", "data_quitacao", "fonte", "pagina"]


def numero(valor):
    if not MOEDA.fullmatch(valor):
        raise ValueError("Moeda inválida: " + repr(valor))
    return Decimal(valor.replace(".", "").replace(",", "."))


def formato(valor):
    return f"{valor:.2f}".replace(".", ",")


def exportar(arquivo, campos, registros):
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    with arquivo.open("w", encoding="utf-8-sig", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=campos, delimiter=";", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(registros)


def extrair(pdf, tipo):
    """Lê PDF em ordem natural; itens são blocos COOTR/MATRIZ, seguidos de subtotal."""
    periodo = pdf.stem
    if not re.fullmatch(r"\d{6}", periodo) or not 1 <= int(periodo[:2]) <= 12:
        raise ValueError("Nome esperado: MMAAAA.pdf")
    mm, aa = int(periodo[:2]), int(periodo[2:])
    linhas = []
    with fitz.open(pdf) as documento:
        for pagina, page in enumerate(documento, 1):
            linhas += [(s.strip(), pagina) for s in page.get_text(sort=False).splitlines() if s.strip()]
    movimentos, erros, grupo = [], [], []
    cooperado, codigo = "", ""
    i = 0
    while i < len(linhas):
        texto, pagina = linhas[i]
        cab = CAB.match(texto)
        if cab:
            novo_codigo, novo_nome = cab.group(1), cab.group(2).strip()
            if grupo and codigo != novo_codigo:
                erros.append(f"{pdf.name}: subtotal ausente para {codigo}")
                grupo = []
            codigo, cooperado = novo_codigo, novo_nome
            i += 1
            continue
        if texto == "COOTR" and i + 1 < len(linhas) and linhas[i + 1][0] == "MATRIZ":
            bloco = [x[0] for x in linhas[i:i + 24]]
            try:
                assert DATA.fullmatch(bloco[2]) and bloco[3] in {"CT", "CE"}
                assert bloco[4].isdigit() and re.fullmatch(r"[A-Z0-9]{7}", bloco[5])
                assert bloco[6].isdigit() and MOEDA.fullmatch(bloco[7])
                assert bloco[9].isdigit() and all(MOEDA.fullmatch(x) for x in bloco[10:14])
                dt = datetime.strptime(bloco[2], "%d/%m/%y")
                if (dt.month, dt.year) != (mm, aa) or not codigo:
                    raise ValueError("data fora do período ou cooperado ausente")
                reg = dict(periodo=f"{aa:04d}-{mm:02d}", tipo=tipo,
                    codigo_cooperado=codigo, cooperado=cooperado,
                    data_emissao=dt.strftime("%d/%m/%Y"), contrato=bloco[4],
                    veiculo=bloco[5], valor_frete=numero(bloco[7]),
                    valor_documento=numero(bloco[10]), valor_pedido=numero(bloco[11]),
                    valor_desconto=numero(bloco[12]), valor_total=numero(bloco[13]),
                    data_quitacao="", fonte=pdf.name, pagina=pagina)
                # Datas após valor total: a última antes do próximo COOTR é quitação.
                for j in range(i + 14, min(i + 25, len(linhas))):
                    item = linhas[j][0]
                    if item == "COOTR" or CAB.match(item):
                        break
                    if DATA.fullmatch(item):
                        reg["data_quitacao"] = datetime.strptime(item, "%d/%m/%y").strftime("%d/%m/%Y")
                movimentos.append(reg)
                grupo.append(reg)
            except (AssertionError, IndexError, ValueError) as exc:
                erros.append(f"{pdf.name}, pág. {pagina}: CF não reconhecido: {exc}")
            i += 1
            continue
        if (grupo and texto.isdigit() and i + 5 < len(linhas)
                and all(MOEDA.fullmatch(linhas[i + j][0]) for j in range(1, 6))):
            valores = [numero(linhas[i + j][0]) for j in range(1, 6)]
            chaves = ["valor_frete", "valor_documento", "valor_pedido", "valor_desconto", "valor_total"]
            totais = [sum((item[c] for item in grupo), Decimal(0)) for c in chaves]
            if int(texto) != len(grupo) or valores != totais:
                erros.append(f"{pdf.name}: subtotal divergente cooperado {codigo}")
            grupo = []
        i += 1
    if grupo:
        erros.append(f"{pdf.name}: último subtotal não conferido ({codigo})")
    if not movimentos:
        erros.append(f"{pdf.name}: nenhum contrato identificado")
    return movimentos, erros


def contas_csv(caminho):
    contas = {}
    with caminho.open(encoding="utf-8-sig", newline="") as fp:
        reader = csv.DictReader(fp, delimiter=";")
        if not {"tipo", "codigo_cooperado", "conta_credito"}.issubset(reader.fieldnames or []):
            raise ValueError("Cadastro exige tipo;codigo_cooperado;conta_credito")
        for row in reader:
            key = (row["tipo"].strip().upper(), row["codigo_cooperado"].strip())
            conta = row["conta_credito"].strip()
            if key in contas or key[0] not in DEBITO or (conta and not conta.isdigit()):
                raise ValueError("Cadastro inválido/duplicado: " + repr(key))
            contas[key] = conta
    return contas


def executar(entrada, saida, cadastro, base=None, data=None):
    arquivos = sorted(p for p in entrada.rglob("*.pdf")
                     if p.parent.name.upper() in DEBITO and re.fullmatch(r"\d{6}", p.stem))
    if not arquivos:
        raise ValueError("Nenhum PDF encontrado em PF/MMAAAA.pdf ou PJ/MMAAAA.pdf")
    registros, erros = [], []
    for pdf in arquivos:
        novos, falhas = extrair(pdf, pdf.parent.name.upper())
        registros.extend(novos)
        erros.extend(falhas)
    exportar(saida / "movimentos_extraidos.csv", CAMPOS,
             [{k: formato(v) if isinstance(v, Decimal) else v for k, v in r.items()} for r in registros])
    repetidos = defaultdict(int)
    for r in registros:
        repetidos[(r["tipo"], r["periodo"], r["codigo_cooperado"], r["contrato"])] += 1
    erros += ["Contrato repetido, revisar parcelas: " + repr(k)
              for k, qtd in repetidos.items() if qtd > 1]
    contas, pendencias, lancamentos = contas_csv(cadastro), [], []
    for r in registros:
        key = (r["tipo"], r["codigo_cooperado"])
        credito = contas.get(key)
        if not credito:
            pendencias.append(dict(tipo=key[0], codigo_cooperado=key[1],
                                   cooperado=r["cooperado"], problema="Conta de crédito não cadastrada"))
            continue
        if not base or not data:
            continue
        valor = r[{"frete": "valor_frete", "documento": "valor_documento", "total": "valor_total"}[base]]
        dt = r[{"emissao": "data_emissao", "quitacao": "data_quitacao"}[data]]
        if valor <= 0 or not dt:
            pendencias.append(dict(tipo=key[0], codigo_cooperado=key[1],
                                   cooperado=r["cooperado"], problema="Data ausente/valor não positivo"))
            continue
        lancamentos.append(dict(data=dt, debito=DEBITO[r["tipo"]], credito=credito,
            valor=formato(valor), historico="190",
            complemento=f"PRESTAÇÃO DE SERVIÇOS DE FRETES COOPERADO CFE CF Nº {r['contrato']} {r['cooperado']}",
            tipo=r["tipo"], contrato=r["contrato"], cooperado=r["cooperado"], fonte=r["fonte"]))
    pendencias = list({(p["tipo"], p["codigo_cooperado"], p["problema"]): p
                       for p in pendencias}.values())
    exportar(saida / "pendencias.csv",
             ["tipo", "codigo_cooperado", "cooperado", "problema"], pendencias)
    (saida / "validacao.txt").write_text(
        "\n".join([f"PDFs: {len(arquivos)}", f"Contratos: {len(registros)}",
                   f"Erros: {len(erros)}", f"Pendências: {len(pendencias)}",
                   f"Base: {base or 'NÃO DEFINIDA'}", f"Data: {data or 'NÃO DEFINIDA'}", *erros]) + "\n",
        encoding="utf-8")
    final = saida / "lancamentos_conferencia.csv"
    if erros or pendencias or not base or not data or len(lancamentos) != len(registros):
        final.unlink(missing_ok=True)
        print(f"BLOQUEADO: {len(registros)} contratos, {len(erros)} erros, {len(pendencias)} pendências")
        return 1
    exportar(final, ["data", "debito", "credito", "valor", "historico", "complemento",
                    "tipo", "contrato", "cooperado", "fonte"], lancamentos)
    print(f"Conferência liberada: {len(lancamentos)} lançamentos. CSV não homologado para importação.")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("entrada", type=Path)
    parser.add_argument("--saida", type=Path, required=True)
    parser.add_argument("--contas", type=Path, required=True)
    parser.add_argument("--base-valor", choices=["frete", "documento", "total"])
    parser.add_argument("--data-contabil", choices=["emissao", "quitacao"])
    args = parser.parse_args()
    return executar(args.entrada, args.saida, args.contas, args.base_valor, args.data_contabil)


if __name__ == "__main__":
    sys.exit(main())
