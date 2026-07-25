"""Geração e leitura da planilha de conferência editável."""

from __future__ import annotations

import shutil
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from .caminhos import CONFERENCIA_XLSX, TEMPORARIOS
from .leitura_planilhas import Lancamento
from .normalizacao import parse_valor
from .plano_contas import PlanoContas

COLUNAS = [
    ("id_lancamento", "ID do lançamento"),
    ("arquivo_origem", "Arquivo de origem"),
    ("aba_origem", "Aba de origem"),
    ("linha_origem", "Linha de origem"),
    ("data", "Data"),
    ("documento", "Documento"),
    ("historico_original", "Histórico original"),
    ("favorecido_original", "Favorecido"),
    ("tipo_movimento", "Tipo de movimento"),
    ("valor", "Valor"),
    ("conta_financeira", "Conta financeira original"),
    ("codigo_conta_debito", "Código da conta de débito"),
    ("descricao_conta_debito", "Descrição da conta de débito"),
    ("codigo_conta_credito", "Código da conta de crédito"),
    ("descricao_conta_credito", "Descrição da conta de crédito"),
    ("historico_contabil", "Histórico contábil"),
    ("regra_aplicada", "Regra aplicada"),
    ("confianca", "Nível de confiança"),
    ("status", "Status"),
    ("exportar", "Exportar"),
    ("origem_classificacao", "Origem da classificação"),
    ("observacoes", "Observações"),
]


def _backup_se_existir(caminho: Path) -> Optional[Path]:
    if not caminho.exists():
        return None
    TEMPORARIOS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = TEMPORARIOS / f"{caminho.stem}-backup-{stamp}{caminho.suffix}"
    shutil.copy2(caminho, dest)
    return dest


def gerar_conferencia(
    lancamentos: List[Lancamento],
    plano: PlanoContas,
    destino: Path = CONFERENCIA_XLSX,
) -> Path:
    _backup_se_existir(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)

    wb = Workbook()
    ws = wb.active
    ws.title = "Conferência"

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="1F4E79")
    for col, (_campo, titulo) in enumerate(COLUNAS, 1):
        cell = ws.cell(1, col, titulo)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(wrap_text=True, vertical="center")

    for r_idx, lanc in enumerate(lancamentos, 2):
        dados = {
            "id_lancamento": lanc.id_lancamento,
            "arquivo_origem": lanc.arquivo_origem,
            "aba_origem": lanc.aba_origem,
            "linha_origem": lanc.linha_origem,
            "data": lanc.data,
            "documento": lanc.documento,
            "historico_original": lanc.historico_original,
            "favorecido_original": lanc.favorecido_original,
            "tipo_movimento": lanc.tipo_movimento,
            "valor": float(lanc.valor),
            "conta_financeira": lanc.conta_financeira,
            "codigo_conta_debito": lanc.codigo_conta_debito,
            "descricao_conta_debito": lanc.descricao_conta_debito,
            "codigo_conta_credito": lanc.codigo_conta_credito,
            "descricao_conta_credito": lanc.descricao_conta_credito,
            "historico_contabil": lanc.historico_contabil,
            "regra_aplicada": lanc.regra_aplicada,
            "confianca": lanc.confianca,
            "status": lanc.status,
            "exportar": lanc.exportar,
            "origem_classificacao": lanc.origem_classificacao,
            "observacoes": lanc.observacoes,
        }
        for c_idx, (campo, _) in enumerate(COLUNAS, 1):
            ws.cell(r_idx, c_idx, dados[campo])

        # formatação
        ws.cell(r_idx, 10).number_format = '#,##0.00'
        if lanc.status == "PENDENTE":
            fill = PatternFill("solid", fgColor="FCE4D6")
            for c in range(1, len(COLUNAS) + 1):
                ws.cell(r_idx, c).fill = fill
        elif lanc.confianca < 80:
            fill = PatternFill("solid", fgColor="FFF2CC")
            for c in range(1, len(COLUNAS) + 1):
                ws.cell(r_idx, c).fill = fill

    ws.auto_filter.ref = f"A1:{get_column_letter(len(COLUNAS))}{max(1, len(lancamentos)+1)}"
    ws.freeze_panes = "A2"

    larguras = [18, 36, 12, 10, 12, 14, 40, 22, 12, 12, 14, 14, 28, 14, 28, 36, 28, 10, 12, 10, 18, 40]
    for i, w in enumerate(larguras, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    # validação Exportar
    dv_exp = DataValidation(type="list", formula1='"SIM,NÃO"', allow_blank=True)
    ws.add_data_validation(dv_exp)
    dv_exp.add(f"T2:T{max(2, len(lancamentos)+1)}")

    # aba de contas para referência / lista
    ws_contas = wb.create_sheet("PlanoContas")
    ws_contas.append(["Código", "Classificação", "Nome", "Grau", "Sintética", "Analítica"])
    for c in plano.contas:
        if c.analitica:
            ws_contas.append([c.codigo, c.classificacao, c.nome, c.grau, "NÃO", "SIM"])
    ws_contas.auto_filter.ref = f"A1:F{ws_contas.max_row}"
    ws_contas.freeze_panes = "A2"

    # validação de códigos com lista (limitada pelo Excel; usa intervalo da aba)
    if ws_contas.max_row >= 2:
        dv_deb = DataValidation(
            type="list",
            formula1=f"PlanoContas!$A$2:$A${ws_contas.max_row}",
            allow_blank=True,
        )
        dv_cred = DataValidation(
            type="list",
            formula1=f"PlanoContas!$A$2:$A${ws_contas.max_row}",
            allow_blank=True,
        )
        ws.add_data_validation(dv_deb)
        ws.add_data_validation(dv_cred)
        dv_deb.add(f"L2:L{max(2, len(lancamentos)+1)}")
        dv_cred.add(f"N2:N{max(2, len(lancamentos)+1)}")

    wb.save(destino)
    return destino


def ler_conferencia(caminho: Path = CONFERENCIA_XLSX) -> List[Dict]:
    wb = load_workbook(caminho, data_only=True)
    ws = wb["Conferência"] if "Conferência" in wb.sheetnames else wb.active
    headers = [cell.value for cell in next(ws.iter_rows(min_row=1, max_row=1))]
    titulo_para_campo = {titulo: campo for campo, titulo in COLUNAS}
    campo_por_idx = {}
    for idx, h in enumerate(headers):
        if h in titulo_para_campo:
            campo_por_idx[idx] = titulo_para_campo[h]

    linhas = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not any(v is not None and str(v).strip() for v in row):
            continue
        item = {campo: None for campo, _ in COLUNAS}
        for idx, campo in campo_por_idx.items():
            item[campo] = row[idx] if idx < len(row) else None
        valor = parse_valor(item.get("valor"))
        item["valor"] = valor if valor is not None else Decimal("0")
        exp = str(item.get("exportar") or "").strip().upper()
        if exp in {"SIM", "S", "YES", "1", "TRUE"}:
            item["exportar"] = "SIM"
        else:
            item["exportar"] = "NÃO"
        item["codigo_conta_debito"] = str(item.get("codigo_conta_debito") or "").strip()
        item["codigo_conta_credito"] = str(item.get("codigo_conta_credito") or "").strip()
        item["historico_contabil"] = str(item.get("historico_contabil") or "").strip()
        item["id_lancamento"] = str(item.get("id_lancamento") or "").strip()
        item["data"] = str(item.get("data") or "").strip()
        linhas.append(item)
    wb.close()
    return linhas


def mesclar_com_revisao_anterior(
    novos: List[Lancamento], anteriores: List[Dict]
) -> List[Lancamento]:
    por_id = {str(a.get("id_lancamento")): a for a in anteriores if a.get("id_lancamento")}
    for lanc in novos:
        ant = por_id.get(lanc.id_lancamento)
        if not ant:
            continue
        origem_ant = str(ant.get("origem_classificacao") or "").strip().upper()
        status_ant = str(ant.get("status") or "").strip().upper()
        # Preserva apenas revisão humana explícita
        if origem_ant != "MANUAL" and status_ant not in {"REVISADO", "MANUAL"}:
            continue
        campos = [
            ("codigo_conta_debito", "codigo_conta_debito"),
            ("codigo_conta_credito", "codigo_conta_credito"),
            ("historico_contabil", "historico_contabil"),
            ("exportar", "exportar"),
            ("observacoes", "observacoes"),
            ("status", "status"),
            ("descricao_conta_debito", "descricao_conta_debito"),
            ("descricao_conta_credito", "descricao_conta_credito"),
        ]
        alterado = False
        for attr, key in campos:
            val = ant.get(key)
            if val is None or str(val).strip() == "":
                continue
            if str(getattr(lanc, attr)).strip() != str(val).strip():
                setattr(lanc, attr, str(val).strip())
                alterado = True
        if alterado:
            lanc.origem_classificacao = "IMPORTADA DA REVISÃO ANTERIOR"
            if lanc.codigo_conta_debito and lanc.codigo_conta_credito:
                if lanc.exportar == "SIM":
                    lanc.confianca = max(int(lanc.confianca or 0), 95)
                    if not lanc.status or lanc.status == "PENDENTE":
                        lanc.status = "REVISADO"
    return novos
