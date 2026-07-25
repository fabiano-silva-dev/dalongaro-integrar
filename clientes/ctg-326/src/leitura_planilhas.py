"""Leitura e normalização de planilhas financeiras (XLS/XLSX/CSV)."""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from openpyxl import load_workbook

from .normalizacao import (
    formatar_data_br,
    id_lancamento,
    normalizar_chave,
    normalizar_texto,
    parse_data,
    parse_valor,
)

IGNORAR_LINHAS = {
    "SALDO ANTERIOR",
    "TOTAL",
    "SALDO ATUAL",
    "SALDO FINAL",
    "SUBTOTAL",
}

ALIASES = {
    "data": {"DATA", "DATA DO MOVIMENTO", "PAGAMENTO", "RECEBIMENTO", "VENCIMENTO"},
    "historico": {
        "HISTORICO",
        "HISTÓRICO",
        "DESCRICAO",
        "DESCRIÇÃO",
        "COMPLEMENTO",
        "OBSERVACAO",
        "OBSERVAÇÃO",
    },
    "favorecido": {"FAVORECIDO", "FORNECEDOR", "CLIENTE", "ASSOCIADO"},
    "documento": {"DOCUMENTO", "NUMERO", "NÚMERO", "NRO", "NF"},
    "entrada": {"ENTRADA", "RECEITA", "CREDITO", "CRÉDITO"},
    "saida": {"SAIDA", "SAÍDA", "DESPESA", "DEBITO", "DÉBITO"},
    "valor": {"VALOR"},
    "conta": {"CONTA", "BANCO", "CAIXA"},
    "forma": {"FORMA DE PAGAMENTO", "FORMA PAGAMENTO"},
}


@dataclass
class Lancamento:
    id_lancamento: str
    arquivo_origem: str
    aba_origem: str
    linha_origem: int
    data: Optional[str]
    documento: str = ""
    historico_original: str = ""
    historico_normalizado: str = ""
    favorecido_original: str = ""
    favorecido_normalizado: str = ""
    tipo_movimento: str = ""
    valor: Decimal = Decimal("0.00")
    conta_financeira: str = ""
    codigo_conta_debito: str = ""
    descricao_conta_debito: str = ""
    codigo_conta_credito: str = ""
    descricao_conta_credito: str = ""
    historico_contabil: str = ""
    regra_aplicada: str = ""
    confianca: int = 0
    status: str = "PENDENTE"
    exportar: str = "NÃO"
    observacoes: str = ""
    origem_classificacao: str = "AUTOMÁTICA"
    extras: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["valor"] = str(self.valor)
        return d


def _mapear_colunas(headers: Iterable[Any]) -> Dict[str, int]:
    mapa: Dict[str, int] = {}
    for idx, h in enumerate(headers):
        chave = normalizar_chave(h)
        if not chave:
            continue
        for campo, aliases in ALIASES.items():
            if chave in aliases and campo not in mapa:
                mapa[campo] = idx
    return mapa


def _eh_linha_ignorar(historico: str, data_ok: bool) -> bool:
    chave = normalizar_chave(historico)
    if not chave and not data_ok:
        return True
    if chave in IGNORAR_LINHAS:
        return True
    if chave.startswith("SALDO "):
        return True
    return False


def _celula(row: Tuple[Any, ...], idx: Optional[int]) -> Any:
    if idx is None or idx >= len(row):
        return None
    return row[idx]


def _tipo_e_valor(
    row: Tuple[Any, ...], mapa: Dict[str, int]
) -> Tuple[str, Optional[Decimal]]:
    entrada = parse_valor(_celula(row, mapa.get("entrada")))
    saida = parse_valor(_celula(row, mapa.get("saida")))
    valor_unico = parse_valor(_celula(row, mapa.get("valor")))

    if entrada is not None and entrada != 0 and (saida is None or saida == 0):
        return "ENTRADA", abs(entrada)
    if saida is not None and saida != 0 and (entrada is None or entrada == 0):
        return "SAIDA", abs(saida)
    if entrada is not None and saida is not None and entrada != 0 and saida != 0:
        # linha anômala — prioriza a maior
        if abs(entrada) >= abs(saida):
            return "ENTRADA", abs(entrada)
        return "SAIDA", abs(saida)
    if valor_unico is not None and valor_unico != 0:
        if valor_unico < 0:
            return "SAIDA", abs(valor_unico)
        return "ENTRADA", abs(valor_unico)
    return "", None


def ler_xlsx(
    caminho: Path, conta_financeira: str = ""
) -> List[Lancamento]:
    wb = load_workbook(caminho, data_only=True, read_only=True)
    lancamentos: List[Lancamento] = []
    try:
        for aba in wb.sheetnames:
            ws = wb[aba]
            header_idx = None
            mapa: Dict[str, int] = {}
            for i, row in enumerate(ws.iter_rows(values_only=True), 1):
                if header_idx is None:
                    candidato = _mapear_colunas(row)
                    if "data" in candidato and (
                        "historico" in candidato
                        or "entrada" in candidato
                        or "saida" in candidato
                        or "valor" in candidato
                    ):
                        header_idx = i
                        mapa = candidato
                    continue

                historico = normalizar_texto(_celula(row, mapa.get("historico")))
                data = parse_data(_celula(row, mapa.get("data")))
                if _eh_linha_ignorar(historico, data is not None):
                    continue
                tipo, valor = _tipo_e_valor(row, mapa)
                if not tipo or valor is None or valor <= 0:
                    continue

                documento = normalizar_texto(_celula(row, mapa.get("documento")))
                favorecido = normalizar_texto(_celula(row, mapa.get("favorecido")))
                conta = normalizar_texto(_celula(row, mapa.get("conta"))) or conta_financeira
                lid = id_lancamento(
                    caminho.name,
                    aba,
                    i,
                    data,
                    documento,
                    historico,
                    favorecido,
                    valor,
                )
                lancamentos.append(
                    Lancamento(
                        id_lancamento=lid,
                        arquivo_origem=caminho.name,
                        aba_origem=aba,
                        linha_origem=i,
                        data=formatar_data_br(data),
                        documento=documento,
                        historico_original=historico,
                        historico_normalizado=normalizar_chave(historico),
                        favorecido_original=favorecido,
                        favorecido_normalizado=normalizar_chave(favorecido),
                        tipo_movimento=tipo,
                        valor=valor,
                        conta_financeira=conta,
                        historico_contabil=historico.upper() if historico else "",
                    )
                )
    finally:
        wb.close()
    return lancamentos


def ler_csv(caminho: Path, conta_financeira: str = "") -> List[Lancamento]:
    lancamentos: List[Lancamento] = []
    with caminho.open("r", encoding="utf-8-sig", newline="") as fh:
        sample = fh.read(4096)
        fh.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=";,\t")
        except csv.Error:
            dialect = csv.excel
            dialect.delimiter = ";"
        reader = csv.reader(fh, dialect)
        rows = list(reader)

    header_idx = None
    mapa: Dict[str, int] = {}
    for i, row in enumerate(rows, 1):
        if header_idx is None:
            candidato = _mapear_colunas(row)
            if "data" in candidato and (
                "historico" in candidato
                or "entrada" in candidato
                or "saida" in candidato
                or "valor" in candidato
            ):
                header_idx = i
                mapa = candidato
            continue
        historico = normalizar_texto(_celula(tuple(row), mapa.get("historico")))
        data = parse_data(_celula(tuple(row), mapa.get("data")))
        if _eh_linha_ignorar(historico, data is not None):
            continue
        tipo, valor = _tipo_e_valor(tuple(row), mapa)
        if not tipo or valor is None or valor <= 0:
            continue
        documento = normalizar_texto(_celula(tuple(row), mapa.get("documento")))
        favorecido = normalizar_texto(_celula(tuple(row), mapa.get("favorecido")))
        conta = normalizar_texto(_celula(tuple(row), mapa.get("conta"))) or conta_financeira
        lid = id_lancamento(
            caminho.name, "csv", i, data, documento, historico, favorecido, valor
        )
        lancamentos.append(
            Lancamento(
                id_lancamento=lid,
                arquivo_origem=caminho.name,
                aba_origem="csv",
                linha_origem=i,
                data=formatar_data_br(data),
                documento=documento,
                historico_original=historico,
                historico_normalizado=normalizar_chave(historico),
                favorecido_original=favorecido,
                favorecido_normalizado=normalizar_chave(favorecido),
                tipo_movimento=tipo,
                valor=valor,
                conta_financeira=conta,
                historico_contabil=historico.upper() if historico else "",
            )
        )
    return lancamentos


def ler_arquivo(caminho: Path, conta_financeira: str = "") -> List[Lancamento]:
    suf = caminho.suffix.lower()
    if suf in {".xlsx", ".xlsm"}:
        return ler_xlsx(caminho, conta_financeira)
    if suf == ".xls":
        # openpyxl não lê xls legado; tenta via pandas/xlrd se disponível
        try:
            import pandas as pd

            xls = pd.ExcelFile(caminho)
            # converte para xlsx temporário em memória via openpyxl-like path:
            # simplificação: usa pandas e reconstrói linhas
            from openpyxl import Workbook
            from tempfile import NamedTemporaryFile

            wb = Workbook()
            wb.remove(wb.active)
            for sheet in xls.sheet_names:
                df = pd.read_excel(caminho, sheet_name=sheet, header=None)
                ws = wb.create_sheet(sheet)
                for r_idx, row in enumerate(df.itertuples(index=False), 1):
                    for c_idx, val in enumerate(row, 1):
                        ws.cell(r_idx, c_idx, None if pd.isna(val) else val)
            with NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
                tmp_path = Path(tmp.name)
                wb.save(tmp_path)
            try:
                return ler_xlsx(tmp_path, conta_financeira)
            finally:
                tmp_path.unlink(missing_ok=True)
        except Exception as exc:
            raise RuntimeError(f"Falha ao ler XLS {caminho.name}: {exc}") from exc
    if suf == ".csv":
        return ler_csv(caminho, conta_financeira)
    raise ValueError(f"Formato não suportado: {caminho.suffix}")


def listar_planilhas(pasta: Path) -> List[Path]:
    arquivos: List[Path] = []
    for padrao in ("*.xlsx", "*.xlsm", "*.xls", "*.csv"):
        arquivos.extend(sorted(pasta.glob(padrao)))
    return [a for a in arquivos if not a.name.startswith("~$")]
