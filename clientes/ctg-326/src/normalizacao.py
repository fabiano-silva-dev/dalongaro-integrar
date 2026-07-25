"""Normalização de textos, datas e valores monetários."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Optional

CENTAVO = Decimal("0.01")


def normalizar_texto(valor: Any) -> str:
    if valor is None:
        return ""
    texto = str(valor).strip()
    texto = re.sub(r"\s+", " ", texto)
    return texto


def normalizar_chave(valor: Any) -> str:
    texto = normalizar_texto(valor).upper()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"[^A-Z0-9 ]+", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def parse_valor(valor: Any) -> Optional[Decimal]:
    if valor is None or valor == "":
        return None
    if isinstance(valor, Decimal):
        return valor.quantize(CENTAVO, rounding=ROUND_HALF_UP)
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        return Decimal(str(valor)).quantize(CENTAVO, rounding=ROUND_HALF_UP)

    texto = str(valor).strip()
    if not texto:
        return None

    negativo = False
    if texto.startswith("(") and texto.endswith(")"):
        negativo = True
        texto = texto[1:-1]
    texto = texto.replace("R$", "").replace(" ", "").strip()
    if texto.startswith("-"):
        negativo = True
        texto = texto[1:]

    if "," in texto and "." in texto:
        if texto.rfind(",") > texto.rfind("."):
            texto = texto.replace(".", "").replace(",", ".")
        else:
            texto = texto.replace(",", "")
    elif "," in texto:
        texto = texto.replace(".", "").replace(",", ".")

    try:
        num = Decimal(texto)
    except InvalidOperation:
        return None
    if negativo:
        num = -num
    return num.quantize(CENTAVO, rounding=ROUND_HALF_UP)


def parse_data(valor: Any) -> Optional[date]:
    if valor is None or valor == "":
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if isinstance(valor, (int, float)):
        # serial Excel (aproximação openpyxl já costuma converter)
        try:
            from datetime import timedelta

            base = datetime(1899, 12, 30)
            return (base + timedelta(days=float(valor))).date()
        except Exception:
            return None

    texto = normalizar_texto(valor)
    texto = texto.replace("//", "/")
    # corrige formatos quebrados: 24/072025, 03/082025, 05/092025
    m = re.match(r"^(\d{1,2})/(\d{2})(\d{4})$", texto)
    if m:
        texto = f"{m.group(1)}/{m.group(2)}/{m.group(3)}"
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", texto)
    if m:
        try:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            return None

    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d.%m.%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(texto, fmt).date()
        except ValueError:
            continue
    return None


def formatar_data_br(d: Optional[date]) -> str:
    if not d:
        return ""
    return d.strftime("%d/%m/%Y")


def formatar_valor_br(v: Optional[Decimal]) -> str:
    if v is None:
        return ""
    q = v.quantize(CENTAVO, rounding=ROUND_HALF_UP)
    sinal = "-" if q < 0 else ""
    q = abs(q)
    inteiro, frac = f"{q:.2f}".split(".")
    inteiro = f"{int(inteiro):,}".replace(",", ".")
    return f"{sinal}{inteiro},{frac}"


def valor_para_centavos(v: Decimal) -> str:
    centavos = int((abs(v).quantize(CENTAVO) * 100).to_integral_value(rounding=ROUND_HALF_UP))
    return str(centavos).zfill(15)


def id_lancamento(
    arquivo: str,
    aba: str,
    linha: int,
    data: Optional[date],
    documento: str,
    historico: str,
    favorecido: str,
    valor: Optional[Decimal],
) -> str:
    base = "|".join(
        [
            normalizar_chave(arquivo),
            normalizar_chave(aba),
            str(linha),
            formatar_data_br(data),
            normalizar_chave(documento),
            normalizar_chave(historico),
            normalizar_chave(favorecido),
            formatar_valor_br(valor) if valor is not None else "",
        ]
    )
    return hashlib.sha1(base.encode("utf-8")).hexdigest()[:16].upper()
