"""Extração e consulta do plano de contas a partir do PDF."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional

import pdfplumber

from .caminhos import PLANO_CONTAS_JSON, PLANO_CONTAS_PDF
from .normalizacao import normalizar_chave


@dataclass
class Conta:
    codigo: str
    classificacao: str
    nome: str
    grau: int
    sintetica: bool

    @property
    def analitica(self) -> bool:
        return not self.sintetica


class PlanoContas:
    def __init__(self, contas: List[Conta]):
        self.contas = contas
        self.por_codigo: Dict[str, Conta] = {c.codigo: c for c in contas}
        self.por_codigo_zfill: Dict[str, Conta] = {
            c.codigo.zfill(7): c for c in contas
        }

    def get(self, codigo: str) -> Optional[Conta]:
        if not codigo:
            return None
        codigo = str(codigo).strip()
        return self.por_codigo.get(codigo) or self.por_codigo_zfill.get(codigo.zfill(7))

    def existe(self, codigo: str) -> bool:
        return self.get(codigo) is not None

    def descricao(self, codigo: str) -> str:
        c = self.get(codigo)
        return c.nome if c else ""

    def eh_analitica(self, codigo: str) -> bool:
        c = self.get(codigo)
        return bool(c and c.analitica)

    def buscar_por_nome(self, trecho: str, apenas_analiticas: bool = True) -> List[Conta]:
        chave = normalizar_chave(trecho)
        hits = []
        for c in self.contas:
            if apenas_analiticas and not c.analitica:
                continue
            if chave and chave in normalizar_chave(c.nome):
                hits.append(c)
        return hits

    def to_list(self) -> List[dict]:
        return [asdict(c) for c in self.contas]


_RE_LINHA = re.compile(
    r"^(\d+)\s+(S\s+)?([\d.]+)\s+(.+?)\s+(\d+)\s*$"
)


def extrair_do_pdf(pdf_path: Path = PLANO_CONTAS_PDF) -> PlanoContas:
    contas: List[Conta] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            texto = page.extract_text() or ""
            for line in texto.splitlines():
                line = line.strip()
                m = _RE_LINHA.match(line)
                if not m:
                    continue
                contas.append(
                    Conta(
                        codigo=m.group(1),
                        sintetica=bool(m.group(2)),
                        classificacao=m.group(3),
                        nome=m.group(4).strip(),
                        grau=int(m.group(5)),
                    )
                )
    return PlanoContas(contas)


def salvar_json(plano: PlanoContas, destino: Path = PLANO_CONTAS_JSON) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps(plano.to_list(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return destino


def carregar_ou_extrair(
    pdf_path: Path = PLANO_CONTAS_PDF,
    json_path: Path = PLANO_CONTAS_JSON,
    forcar: bool = False,
) -> PlanoContas:
    if json_path.exists() and not forcar:
        dados = json.loads(json_path.read_text(encoding="utf-8"))
        return PlanoContas([Conta(**d) for d in dados])
    plano = extrair_do_pdf(pdf_path)
    salvar_json(plano, json_path)
    return plano
