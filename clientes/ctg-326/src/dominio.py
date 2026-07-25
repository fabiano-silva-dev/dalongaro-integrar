"""Exportação no leiaute Domínio (registros 01/02/03/99) — espelho do FT/Integrar."""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .caminhos import DOMINIO, HISTORICO_EXPORTACOES, RELATORIOS
from .normalizacao import parse_data, valor_para_centavos


def _pad(texto: str, tamanho: int, fill: str = " ", left: bool = False) -> str:
    texto = texto or ""
    if left:
        return texto[:tamanho].rjust(tamanho, fill)
    return texto[:tamanho].ljust(tamanho, fill)


def _mb_pad(texto: str, tamanho: int) -> str:
    """Padding por caracteres Unicode (equivalente ao mb_str_pad do PHP)."""
    texto = texto or ""
    if len(texto) > tamanho:
        return texto[:tamanho]
    return texto + (" " * (tamanho - len(texto)))


def limpar_historico(texto: str) -> str:
    if not texto:
        return ""
    limpo = texto.replace("\r", " ").replace("\n", " ").replace("\t", " ")
    limpo = " ".join(limpo.split())
    return limpo[:512]


def montar_registro_01(
    codigo_empresa: str,
    cnpj: str,
    data_inicial: Optional[date],
    data_final: Optional[date],
    tipo_nota: str = "05",
    sistema: str = "1",
) -> str:
    linha = "01"
    linha += _pad(str(codigo_empresa).zfill(7), 7, "0", left=True)
    cnpj_limpo = "".join(ch for ch in str(cnpj) if ch.isdigit())
    linha += _pad(cnpj_limpo, 14)
    linha += data_inicial.strftime("%d/%m/%Y") if data_inicial else (" " * 10)
    linha += data_final.strftime("%d/%m/%Y") if data_final else (" " * 10)
    linha += "N"
    linha += _pad(tipo_nota, 2, "0", left=True)
    linha += "00000"
    linha += sistema
    linha += "17"
    return _pad(linha, 100)


def montar_registro_02(sequencial: int, data_lanc: date, usuario: str = "CTG326") -> str:
    linha = "02"
    linha += _pad(str(sequencial), 7, "0", left=True)
    linha += "X"
    linha += data_lanc.strftime("%d/%m/%Y")
    linha += _pad(usuario, 30)
    return _pad(linha, 100)


def montar_registro_03(
    sequencial: int,
    conta_debito: str,
    conta_credito: str,
    valor: Decimal,
    historico: str,
    codigo_filial: str,
) -> str:
    linha = "03"
    linha += _pad(str(sequencial), 7, "0", left=True)
    linha += _pad(str(conta_debito).zfill(7), 7, "0", left=True)
    linha += _pad(str(conta_credito).zfill(7), 7, "0", left=True)
    linha += valor_para_centavos(valor)
    linha += "0000000"
    linha += _mb_pad(limpar_historico(historico), 512)
    linha += _pad(str(codigo_filial).zfill(7), 7, "0", left=True)
    return _pad(linha, 664)


def montar_registro_99() -> str:
    return _pad("99", 100, "0")


def gerar_arquivo_dominio(
    lancamentos: List[Dict],
    codigo_empresa: str = "326",
    cnpj: str = "87445102000107",
    usuario: str = "CTG326",
    destino_dir: Path = DOMINIO,
) -> Tuple[Path, Dict]:
    datas = [parse_data(l.get("data")) for l in lancamentos]
    datas = [d for d in datas if d]
    data_ini = min(datas) if datas else None
    data_fim = max(datas) if datas else None

    linhas = [
        montar_registro_01(codigo_empresa, cnpj, data_ini, data_fim),
    ]
    seq = 1
    total = Decimal("0.00")
    ids = []
    for lanc in lancamentos:
        d = parse_data(lanc.get("data"))
        if not d:
            continue
        valor = lanc.get("valor")
        if not isinstance(valor, Decimal):
            from .normalizacao import parse_valor

            valor = parse_valor(valor) or Decimal("0")
        linhas.append(montar_registro_02(seq, d, usuario=usuario))
        linhas.append(
            montar_registro_03(
                seq,
                str(lanc.get("codigo_conta_debito") or ""),
                str(lanc.get("codigo_conta_credito") or ""),
                valor,
                str(lanc.get("historico_contabil") or ""),
                codigo_empresa,
            )
        )
        total += valor
        ids.append(lanc.get("id_lancamento"))
        seq += 1
    linhas.append(montar_registro_99())

    destino_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    nome = f"CTG-326-dominio-{stamp}.txt"
    caminho = destino_dir / nome
    conteudo = "\n".join(linhas)
    caminho.write_bytes(conteudo.encode("latin-1", errors="replace"))

    meta = {
        "arquivo": str(caminho),
        "quantidade": seq - 1,
        "valor_total": str(total),
        "data_inicial": data_ini.strftime("%d/%m/%Y") if data_ini else "",
        "data_final": data_fim.strftime("%d/%m/%Y") if data_fim else "",
        "ids": ids,
    }
    return caminho, meta


def registrar_historico(meta: Dict, conferencia: Path, pendencias: int) -> None:
    HISTORICO_EXPORTACOES.parent.mkdir(parents=True, exist_ok=True)
    hist = []
    if HISTORICO_EXPORTACOES.exists():
        hist = json.loads(HISTORICO_EXPORTACOES.read_text(encoding="utf-8"))
    import hashlib

    h = hashlib.sha1(conferencia.read_bytes()).hexdigest() if conferencia.exists() else ""
    hist.append(
        {
            "data_hora": datetime.now().isoformat(timespec="seconds"),
            "arquivo_conferencia": str(conferencia),
            "hash_conferencia": h,
            "quantidade_exportada": meta.get("quantidade"),
            "valor_total": meta.get("valor_total"),
            "arquivo_gerado": meta.get("arquivo"),
            "pendencias": pendencias,
            "ids": meta.get("ids", []),
        }
    )
    HISTORICO_EXPORTACOES.write_text(
        json.dumps(hist, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def salvar_relatorio(nome: str, dados: Dict) -> Path:
    RELATORIOS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    caminho = RELATORIOS / f"{nome}-{stamp}.json"
    caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return caminho
