#!/usr/bin/env python3
"""Gera Demonstrações Contábeis Completas (DCC) da Credit Saint Germain
para publicação na Central de Balanços do SPED (exercícios 2022–2025).
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "gerados"
LOGO = OUT_DIR / "logo.png"

EMPRESA = "CREDIT SAINT GERMAIN SECURITIZADORA DE CREDITO S/A"
CNPJ = "46.788.467/0001-49"
CNPJ_FILE = "46788467000149"
# NIRE confirmado na JUCISRS para a securitizadora (CNPJ 46.788.467/0001-49).
# O nº 43209453520 do balancete Domínio pertence a OUTRA empresa
# (Credit Saint Germain Participações Societárias Ltda — CNPJ 46.350.136/0001-22).
NIRE = "43.300.068.854"
ENDERECO = (
    "Av. Pinheiro Machado, nº 2350, Sala 404 — Centro — "
    "Santa Maria/RS"
)
SITE = "https://creditsaintgermain.com"
OBJETO = (
    "securitização de créditos e direitos creditórios, com ênfase em "
    "operações de crédito voltadas a tratamentos e procedimentos de saúde"
)

PRESIDENTE = "JANE HARTMANN HUNING"
PRESIDENTE_CARGO = "Presidente"
PRESIDENTE_CPF = "307.519.340-20"

CONTADOR = "VALDECIR DAL ONGARO"
CONTADOR_CRC = "CRC/RS 082555/O-3"
CONTADOR_CPF = "988.186.940-49"

AZUL = colors.HexColor("#0B3A6E")
AZUL_CLARO = colors.HexColor("#E8F0F8")
CINZA = colors.HexColor("#555555")
LINHA = colors.HexColor("#CCCCCC")


def brl(valor: float) -> str:
    """Formata valor em R$ brasileiro (sem símbolo)."""
    negativo = valor < 0
    v = abs(valor)
    inteiro, cent = f"{v:.2f}".split(".")
    grupos = []
    while inteiro:
        grupos.insert(0, inteiro[-3:])
        inteiro = inteiro[:-3]
    s = ".".join(grupos) + "," + cent
    return f"({s})" if negativo else s


# ---------------------------------------------------------------------------
# Dados contábeis (consolidados a partir dos balanços/DRE/DMPL oficiais)
# ---------------------------------------------------------------------------

DADOS = {
    2022: {
        "bp": {
            "ativo": 1_013_305.09,
            "circulante": 1_009_208.31,
            "disponivel": 12_368.21,
            "bancos": 12_368.21,
            "aplicacoes": 995_858.80,
            "clientes": 981.30,
            "outros_creditos": 0.0,
            "nao_circulante": 4_096.78,
            "imobilizado_bruto": 4_378.97,
            "depreciacao": -282.19,
            "imobilizado": 4_096.78,
            "emprestimo_socios": 0.0,
            "passivo": 1_013_305.09,
            "passivo_circulante": 1_562_753.34,
            "fornecedores": 8_347.80,
            "obrig_tributarias": 1_363.59,
            "obrig_trabalhistas": 12_694.82,
            "outras_obrigacoes": 540_347.13,
            "debentures": 1_000_000.00,
            "pl": -549_448.25,
            "capital_subscrito": 100_000.00,
            "capital_a_integralizar": -100_000.00,
            "afac": 0.0,
            "capital_social_liquido": 0.0,
            "prejuizos_acumulados": -549_448.25,
        },
        "dre": {
            "receita_bruta": 1_159.10,
            "deducoes": -53.90,
            "receita_liquida": 1_105.20,
            "custos": 0.0,
            "lucro_bruto": 1_105.20,
            "despesas_operacionais": -550_553.45,  # inclui despesas + indedutíveis net of fin
            "despesas_pessoal": -76_808.50,
            "despesas_admin": -340_349.89,
            "despesas_financeiras": -491.83,
            "receitas_financeiras": 0.0,
            "outras_despesas": -115_872.85,
            "alugueis": -14_296.31,
            "impostos_taxas": -2_734.07,
            "resultado_operacional": -549_448.25,
            "receitas_nao_operacionais": 0.0,
            "resultado_antes_ir": -549_448.25,
            "ir_csll": 0.0,
            "resultado": -549_448.25,
        },
        "dmpl": [
            ("Saldo em 01/01/2022", 0.0, 0.0, 0.0, 0.0),
            ("Constituição / Capital Subscrito", 100_000.00, -100_000.00, 0.0, 0.0),
            ("Prejuízo líquido do exercício", 0.0, 0.0, -549_448.25, -549_448.25),
            ("Saldo em 31/12/2022", 100_000.00, -100_000.00, -549_448.25, -549_448.25),
        ],
        "dlpa": [
            ("Saldo inicial em 01/01/2022", 0.0),
            ("Prejuízo líquido do exercício 2022", -549_448.25),
            ("Saldo final em 31/12/2022", -549_448.25),
        ],
        "dfc": {
            "resultado": -549_448.25,
            "variacao_ativos": None,  # simplificado
            "cx_operacional": -549_448.25,
            "cx_investimento": 0.0,
            "cx_financiamento": 561_816.46,  # debêntures + outras → reconcilia caixa
            "variacao_caixa": 12_368.21,
            "caixa_inicial": 0.0,
            "caixa_final": 12_368.21,
            "notas_dfc": (
                "Em 2022, o caixa final corresponde ao disponível bancário. "
                "As aplicações financeiras de R$ 995.858,80 foram classificadas "
                "à parte no ativo circulante."
            ),
        },
        "notas_especiais": {
            "resultado_texto": (
                "A entidade apresentou no final do exercício de 2022 um prejuízo "
                "líquido de R$ 549.448,25."
            ),
            "capital_texto": (
                "O capital social subscrito totaliza R$ 100.000,00 (cem mil reais), "
                "ainda pendente de integralização ao final do exercício."
            ),
        },
    },
    2023: {
        "bp": {
            "ativo": 2_567_558.90,
            "circulante": 2_564_337.88,
            "disponivel": 601_296.05,
            "bancos": 26_289.25,
            "aplicacoes": 575_006.80,
            "clientes": 1_962_826.82,
            "outros_creditos": 215.01,
            "nao_circulante": 3_221.02,
            "imobilizado_bruto": 4_378.97,
            "depreciacao": -1_157.95,
            "imobilizado": 3_221.02,
            "emprestimo_socios": 0.0,
            "passivo": 2_567_558.90,
            "passivo_circulante": 3_425_419.57,
            "fornecedores": 4_443.20,
            "obrig_tributarias": 1_885.45,
            "obrig_trabalhistas": 26_826.68,
            "outras_obrigacoes": 1_424_429.36,
            "debentures": 1_967_834.88,
            "pl": -857_860.67,
            "capital_subscrito": 100_000.00,
            "capital_a_integralizar": -100_000.00,
            "afac": 0.0,
            "capital_social_liquido": 0.0,
            "prejuizos_acumulados": -857_860.67,
        },
        "dre": {
            "receita_bruta": 749_199.61,
            "deducoes": -35_595.45,
            "receita_liquida": 713_604.16,
            "custos": 0.0,
            "lucro_bruto": 713_604.16,
            "despesas_operacionais": -819_205.20,
            "despesas_vendas": -31_898.08,
            "despesas_pessoal": -300_568.09,
            "despesas_admin": -452_448.20,
            "despesas_financeiras": -242_135.17,
            "receitas_financeiras": 2_837.16,
            "outras_despesas": -17_590.82,
            "alugueis": -31_175.21,
            "impostos_taxas": -3_115.62,
            "resultado_operacional": -362_489.87,
            "receitas_nao_operacionais": 105_883.61,
            "resultado_antes_ir": -256_606.26,
            "ir_csll": -28_117.14,
            "resultado": -284_723.40,
        },
        "dmpl": [
            ("Saldo em 31/12/2022", 100_000.00, -100_000.00, -549_448.25, -549_448.25),
            ("Prejuízo líquido do exercício", 0.0, 0.0, -284_723.40, -284_723.40),
            (
                "Ajustes / outras movimentações do PL",
                0.0,
                0.0,
                -23_689.02,
                -23_689.02,
            ),
            ("Saldo em 31/12/2023", 100_000.00, -100_000.00, -857_860.67, -857_860.67),
        ],
        "dlpa": [
            ("Saldo inicial em 01/01/2023", -549_448.25),
            ("Prejuízo líquido do exercício 2023", -284_723.40),
            ("Ajustes / outras movimentações", -23_689.02),
            ("Saldo final em 31/12/2023", -857_860.67),
        ],
        "dfc": {
            "resultado": -284_723.40,
            "cx_operacional": -284_723.40,
            "cx_investimento": 0.0,
            "cx_financiamento": 873_651.24,
            "variacao_caixa": 588_927.84,
            "caixa_inicial": 12_368.21,
            "caixa_final": 601_296.05,
            "notas_dfc": (
                "O disponível final inclui bancos conta movimento e aplicações "
                "de liquidez imediata, em conformidade com o balanço patrimonial."
            ),
        },
        "notas_especiais": {
            "resultado_texto": (
                "A entidade apresentou no final do exercício de 2023 um prejuízo "
                "líquido de R$ 284.723,40, elevando os prejuízos acumulados a "
                "R$ 857.860,67."
            ),
            "capital_texto": (
                "O capital social subscrito permanece em R$ 100.000,00, pendente "
                "de integralização ao final do exercício."
            ),
        },
    },
    2024: {
        "bp": {
            "ativo": 4_409_783.12,
            "circulante": 4_407_328.40,
            "disponivel": 73_610.63,
            "bancos": 56_599.78,
            "aplicacoes": 17_010.85,
            "clientes": 4_259_711.65,
            "outros_creditos": 74_006.12,
            "nao_circulante": 2_454.72,
            "imobilizado_bruto": 4_378.97,
            "depreciacao": -1_924.25,
            "imobilizado": 2_454.72,
            "emprestimo_socios": 0.0,
            "passivo": 4_409_783.12,
            "passivo_circulante": 4_797_242.46,
            "fornecedores": 9_001.30,
            "obrig_tributarias": 58_423.79,
            "obrig_trabalhistas": 40_700.85,
            "outras_obrigacoes": 2_209_437.53,
            "debentures": 2_479_678.99,
            "pl": -387_459.34,
            "capital_subscrito": 100_000.00,
            "capital_a_integralizar": -100_000.00,
            "afac": 415_000.00,
            "capital_social_liquido": 415_000.00,
            "prejuizos_acumulados": -802_459.34,
        },
        "dre": {
            "receita_bruta": 1_036_999.56,
            "deducoes": -50_356.04,
            "receita_liquida": 986_643.52,
            "custos": 2_399.00,  # devolução líquida positiva no custo
            "lucro_bruto": 989_042.52,
            "despesas_operacionais": -732_187.25,
            "despesas_pessoal": -263_919.75,
            "despesas_admin": -417_970.28,
            "despesas_financeiras": -222_504.51,
            "receitas_financeiras": 14_254.43,
            "outras_despesas": -27_505.75,
            "alugueis": -49_431.73,
            "impostos_taxas": -865.49,
            "resultado_operacional": 21_099.44,
            "receitas_nao_operacionais": 21_113.01,
            "resultado_antes_ir": 42_212.45,
            "ir_csll": 0.0,
            "resultado": 42_212.45,
        },
        "dmpl": [
            ("Saldo em 31/12/2023", 100_000.00, -100_000.00, -857_860.67, -857_860.67),
            ("Adiantamento para futuro aumento de capital", 0.0, 415_000.00, 0.0, 415_000.00),
            ("Resultado líquido do exercício", 0.0, 0.0, 42_212.45, 42_212.45),
            (
                "Outras movimentações de lucros/prejuízos",
                0.0,
                0.0,
                13_188.88,
                13_188.88,
            ),
            (
                "Saldo em 31/12/2024",
                100_000.00,
                315_000.00,
                -802_459.34,
                -387_459.34,
            ),
        ],
        "dlpa": [
            ("Saldo inicial em 01/01/2024", -857_860.67),
            ("Resultado líquido do exercício 2024", 42_212.45),
            ("Outras movimentações", 13_188.88),
            ("Saldo final em 31/12/2024", -802_459.34),
        ],
        "dfc": {
            "resultado": 42_212.45,
            "cx_operacional": -527_685.42,
            "cx_investimento": 0.0,
            "cx_financiamento": 0.0,
            "variacao_caixa": -527_685.42,
            "caixa_inicial": 601_296.05,
            "caixa_final": 73_610.63,
            "notas_dfc": (
                "A redução do disponível reflete principalmente a expansão da "
                "carteira de direitos creditórios e a dinâmica operacional do "
                "exercício. Caixa inicial e final conciliam com o balanço patrimonial."
            ),
        },
        "notas_especiais": {
            "resultado_texto": (
                "A entidade apresentou no final do exercício de 2024 lucro líquido "
                "de R$ 42.212,45. O patrimônio líquido permanece negativo em "
                "R$ 387.459,34, considerando o adiantamento para futuro aumento "
                "de capital de R$ 415.000,00."
            ),
            "capital_texto": (
                "O capital social subscrito é de R$ 100.000,00. Houve aporte de "
                "R$ 415.000,00 a título de adiantamento para futuro aumento de "
                "capital (AFAC), registrado no patrimônio líquido."
            ),
        },
    },
    2025: {
        "bp": {
            "ativo": 7_288_280.94,
            "circulante": 7_285_513.98,
            "disponivel": 715_557.15,
            "bancos": 2_252.34,
            "aplicacoes": 713_304.81,
            "clientes": 6_455_543.10,
            "outros_creditos": 114_413.73,
            "nao_circulante": 2_766.96,
            "imobilizado_bruto": 4_378.97,
            "depreciacao": -2_800.01,  # approx from net 1.578,96
            "imobilizado": 1_578.96,
            "emprestimo_socios": 1_188.00,
            "passivo": 7_288_280.94,
            "passivo_circulante": 7_629_898.96,
            "fornecedores": 77_870.46,
            "obrig_tributarias": 8_073.06,
            "obrig_trabalhistas": 54_767.33,
            "outras_obrigacoes": 4_068_878.24,
            "debentures": 3_420_309.87,
            "pl": -341_618.02,
            "capital_subscrito": 100_000.00,
            "capital_a_integralizar": 0.0,
            "afac": 415_000.00,
            "capital_social_liquido": 515_000.00,
            "prejuizos_acumulados": -856_618.02,
        },
        "dre": {
            "receita_bruta": 2_184_334.96,
            "deducoes": -92_058.78,
            "receita_liquida": 2_092_276.18,
            "custos": -252_453.44,
            "lucro_bruto": 1_839_822.74,
            "despesas_operacionais": -1_270_286.61,
            "despesas_pessoal": -500_890.79,
            "despesas_admin": -496_937.52,
            "despesas_financeiras": -601_564.71,
            "receitas_financeiras": 13_253.13,
            "outras_despesas": -10_062.38,
            "alugueis": -253_414.56,
            "impostos_taxas": -19_043.74,
            "resultado_operacional": -28_837.83,
            "receitas_nao_operacionais": 13_837.74,
            "resultado_antes_ir": -15_000.09,
            "ir_csll": 0.0,
            "resultado": -15_000.09,
        },
        "dmpl": [
            (
                "Saldo em 31/12/2024",
                100_000.00,
                315_000.00,
                -802_459.34,
                -387_459.34,
            ),
            ("Aumento / AFAC", 0.0, 100_000.00, 0.0, 100_000.00),
            ("Resultado líquido do exercício", 0.0, 0.0, -15_000.09, -15_000.09),
            (
                "Outras movimentações de lucros/prejuízos",
                0.0,
                0.0,
                -39_158.59,
                -39_158.59,
            ),
            (
                "Saldo em 31/12/2025",
                100_000.00,
                415_000.00,
                -856_618.02,
                -341_618.02,
            ),
        ],
        "dlpa": [
            ("Saldo inicial em 01/01/2025", -802_459.34),
            ("Prejuízo líquido do exercício 2025", -15_000.09),
            ("Outras movimentações", -39_158.59),
            ("Saldo final em 31/12/2025", -856_618.02),
        ],
        "dfc": {
            "resultado": -15_000.09,
            "cx_operacional": 641_946.52,
            "cx_investimento": 0.0,
            "cx_financiamento": 0.0,
            "variacao_caixa": 641_946.52,
            "caixa_inicial": 73_610.63,
            "caixa_final": 715_557.15,
            "notas_dfc": (
                "O disponível final (R$ 715.557,15) concilia com o balanço "
                "patrimonial e compreende bancos e aplicações de liquidez imediata."
            ),
        },
        "notas_especiais": {
            "resultado_texto": (
                "A entidade apresentou no final do exercício de 2025 um prejuízo "
                "líquido de R$ 15.000,09, resultando em prejuízos acumulados de "
                "R$ 856.618,02 e patrimônio líquido negativo de R$ 341.618,02."
            ),
            "capital_texto": (
                "O capital social líquido totaliza R$ 515.000,00, composto por "
                "capital subscrito de R$ 100.000,00 e adiantamento para futuro "
                "aumento de capital de R$ 415.000,00."
            ),
        },
    },
}


def styles():
    base = getSampleStyleSheet()
    s = {
        "title": ParagraphStyle(
            "title",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=13,
            alignment=TA_CENTER,
            textColor=AZUL,
            spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "subtitle",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9,
            alignment=TA_CENTER,
            textColor=CINZA,
            spaceAfter=10,
        ),
        "h2": ParagraphStyle(
            "h2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            alignment=TA_CENTER,
            textColor=AZUL,
            spaceBefore=6,
            spaceAfter=8,
        ),
        "body": ParagraphStyle(
            "body",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            alignment=TA_JUSTIFY,
            spaceAfter=6,
        ),
        "nota_titulo": ParagraphStyle(
            "nota_titulo",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=AZUL,
            spaceBefore=8,
            spaceAfter=4,
        ),
        "small": ParagraphStyle(
            "small",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            alignment=TA_LEFT,
        ),
        "cell": ParagraphStyle(
            "cell",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
        ),
        "cell_b": ParagraphStyle(
            "cell_b",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
        ),
        "assinatura": ParagraphStyle(
            "assinatura",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8,
            alignment=TA_CENTER,
            leading=11,
        ),
        "footer": ParagraphStyle(
            "footer",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=7,
            textColor=CINZA,
            alignment=TA_CENTER,
        ),
    }
    return s


def header_block(ano: int, st):
    elems = []
    if LOGO.exists():
        img = Image(str(LOGO), width=4.2 * cm, height=1.4 * cm, kind="proportional")
        img.hAlign = "CENTER"
        elems.append(img)
        elems.append(Spacer(1, 4 * mm))
    elems.append(Paragraph(EMPRESA, st["title"]))
    elems.append(
        Paragraph(
            f"CNPJ: {CNPJ} &nbsp;&nbsp;|&nbsp;&nbsp; NIRE: {NIRE}<br/>"
            f"Demonstrações Contábeis Completas (DCC) — Exercício findo em 31/12/{ano}<br/>"
            f"Período: 01/01/{ano} a 31/12/{ano} &nbsp;&nbsp;|&nbsp;&nbsp; Valores em Reais (R$)",
            st["subtitle"],
        )
    )
    return elems


def assinaturas(st, cidade_data: str = ""):
    """Bloco de assinaturas. Cidade/data só quando informada (final do relatório)."""
    elems = [Spacer(1, 8 * mm)]
    if cidade_data:
        elems.append(Paragraph(cidade_data, st["subtitle"]))
        elems.append(Spacer(1, 6 * mm))
    data = [
        [
            Paragraph("_______________________________", st["assinatura"]),
            Paragraph("_______________________________", st["assinatura"]),
        ],
        [
            Paragraph(f"<b>{PRESIDENTE}</b><br/>{PRESIDENTE_CARGO}<br/>CPF: {PRESIDENTE_CPF}", st["assinatura"]),
            Paragraph(
                f"<b>{CONTADOR}</b><br/>{CONTADOR_CRC} — Contador<br/>CPF: {CONTADOR_CPF}",
                st["assinatura"],
            ),
        ],
    ]
    t = Table(data, colWidths=[8.5 * cm, 8.5 * cm])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    elems.append(t)
    return elems


def linha_bp(desc, valor, nivel=0, bold=False):
    st = styles()
    pad = "&nbsp;" * (nivel * 4)
    style = st["cell_b"] if bold else st["cell"]
    txt = f"{pad}{desc}"
    return [Paragraph(txt, style), Paragraph(brl(valor) if valor is not None else "", style)]


def build_bp(ano, d, st):
    bp = d["bp"]
    elems = [Paragraph("I — BALANÇO PATRIMONIAL", st["h2"])]
    elems.append(Paragraph("Valores expressos em Reais (R$)", st["subtitle"]))

    # Duas colunas: Ativo | Passivo+PL
    ativo_rows = [
        [Paragraph("<b>ATIVO</b>", st["cell_b"]), Paragraph(f"<b>{brl(bp['ativo'])}</b>", st["cell_b"])],
        [Paragraph("<b>CIRCULANTE</b>", st["cell_b"]), Paragraph(f"<b>{brl(bp['circulante'])}</b>", st["cell_b"])],
        [Paragraph("&nbsp;&nbsp;Disponível", st["cell"]), Paragraph(brl(bp["disponivel"]), st["cell"])],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;Bancos conta movimento", st["cell"]), Paragraph(brl(bp["bancos"]), st["cell"])],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;Aplicações de liquidez imediata", st["cell"]), Paragraph(brl(bp["aplicacoes"]), st["cell"])],
        [Paragraph("&nbsp;&nbsp;Clientes / Direitos creditórios", st["cell"]), Paragraph(brl(bp["clientes"]), st["cell"])],
    ]
    if bp["outros_creditos"]:
        ativo_rows.append(
            [Paragraph("&nbsp;&nbsp;Outros créditos", st["cell"]), Paragraph(brl(bp["outros_creditos"]), st["cell"])]
        )
    # Em 2022 aplicações estavam fora do "disponível"
    if ano == 2022:
        ativo_rows = [
            [Paragraph("<b>ATIVO</b>", st["cell_b"]), Paragraph(f"<b>{brl(bp['ativo'])}</b>", st["cell_b"])],
            [Paragraph("<b>CIRCULANTE</b>", st["cell_b"]), Paragraph(f"<b>{brl(bp['circulante'])}</b>", st["cell_b"])],
            [Paragraph("&nbsp;&nbsp;Disponível", st["cell"]), Paragraph(brl(bp["disponivel"]), st["cell"])],
            [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;Bancos conta movimento", st["cell"]), Paragraph(brl(bp["bancos"]), st["cell"])],
            [Paragraph("&nbsp;&nbsp;Clientes", st["cell"]), Paragraph(brl(bp["clientes"]), st["cell"])],
            [Paragraph("&nbsp;&nbsp;Aplicações financeiras", st["cell"]), Paragraph(brl(bp["aplicacoes"]), st["cell"])],
        ]

    ativo_rows += [
        [Paragraph("<b>NÃO CIRCULANTE</b>", st["cell_b"]), Paragraph(f"<b>{brl(bp['nao_circulante'])}</b>", st["cell_b"])],
        [Paragraph("&nbsp;&nbsp;Imobilizado", st["cell"]), Paragraph(brl(bp["imobilizado"]), st["cell"])],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;Bens em operação", st["cell"]), Paragraph(brl(bp["imobilizado_bruto"]), st["cell"])],
        [
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;(-) Depreciação / amortização", st["cell"]),
            Paragraph(brl(bp["imobilizado"] - bp["imobilizado_bruto"]), st["cell"]),
        ],
    ]
    if bp["emprestimo_socios"]:
        ativo_rows.append(
            [Paragraph("&nbsp;&nbsp;Empréstimo de sócios", st["cell"]), Paragraph(brl(bp["emprestimo_socios"]), st["cell"])]
        )

    passivo_rows = [
        [Paragraph("<b>PASSIVO</b>", st["cell_b"]), Paragraph(f"<b>{brl(bp['passivo'])}</b>", st["cell_b"])],
        [Paragraph("<b>CIRCULANTE</b>", st["cell_b"]), Paragraph(f"<b>{brl(bp['passivo_circulante'])}</b>", st["cell_b"])],
        [Paragraph("&nbsp;&nbsp;Fornecedores", st["cell"]), Paragraph(brl(bp["fornecedores"]), st["cell"])],
        [Paragraph("&nbsp;&nbsp;Obrigações tributárias", st["cell"]), Paragraph(brl(bp["obrig_tributarias"]), st["cell"])],
        [
            Paragraph("&nbsp;&nbsp;Obrigações trabalhistas e previdenciárias", st["cell"]),
            Paragraph(brl(bp["obrig_trabalhistas"]), st["cell"]),
        ],
        [Paragraph("&nbsp;&nbsp;Outras obrigações", st["cell"]), Paragraph(brl(bp["outras_obrigacoes"]), st["cell"])],
        [Paragraph("&nbsp;&nbsp;Debêntures", st["cell"]), Paragraph(brl(bp["debentures"]), st["cell"])],
        [Paragraph("<b>PATRIMÔNIO LÍQUIDO</b>", st["cell_b"]), Paragraph(f"<b>{brl(bp['pl'])}</b>", st["cell_b"])],
        [Paragraph("&nbsp;&nbsp;Capital social", st["cell"]), Paragraph(brl(bp["capital_social_liquido"]), st["cell"])],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;Capital subscrito", st["cell"]), Paragraph(brl(bp["capital_subscrito"]), st["cell"])],
    ]
    if bp["capital_a_integralizar"]:
        passivo_rows.append(
            [
                Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;(-) Capital a integralizar", st["cell"]),
                Paragraph(brl(bp["capital_a_integralizar"]), st["cell"]),
            ]
        )
    if bp["afac"]:
        passivo_rows.append(
            [
                Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;Adiant. p/ futuro aumento de capital", st["cell"]),
                Paragraph(brl(bp["afac"]), st["cell"]),
            ]
        )
    passivo_rows.append(
        [
            Paragraph("&nbsp;&nbsp;Lucros/prejuízos acumulados", st["cell"]),
            Paragraph(brl(bp["prejuizos_acumulados"]), st["cell"]),
        ]
    )

    # Equalizar altura das tabelas com linhas vazias
    while len(ativo_rows) < len(passivo_rows):
        ativo_rows.append([Paragraph("", st["cell"]), Paragraph("", st["cell"])])
    while len(passivo_rows) < len(ativo_rows):
        passivo_rows.append([Paragraph("", st["cell"]), Paragraph("", st["cell"])])

    t_ativo = Table(ativo_rows, colWidths=[6.2 * cm, 2.3 * cm])
    t_passivo = Table(passivo_rows, colWidths=[6.2 * cm, 2.3 * cm])
    for t in (t_ativo, t_passivo):
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), AZUL_CLARO),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                    ("BOX", (0, 0), (-1, -1), 0.4, LINHA),
                    ("LINEBELOW", (0, 0), (-1, -2), 0.2, LINHA),
                ]
            )
        )

    grid = Table([[t_ativo, t_passivo]], colWidths=[8.7 * cm, 8.7 * cm])
    grid.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (1, 0), (1, 0), 4)]))
    elems.append(grid)
    elems.append(Spacer(1, 3 * mm))
    elems.append(
        Paragraph(
            "* As notas explicativas são parte integrante das demonstrações contábeis.",
            st["footer"],
        )
    )
    elems += assinaturas(st)
    return elems


def build_dre(ano, d, st):
    dre = d["dre"]
    elems = [Paragraph("II — DEMONSTRAÇÃO DO RESULTADO DO EXERCÍCIO (DRE)", st["h2"])]
    elems.append(Paragraph("Valores expressos em Reais (R$)", st["subtitle"]))

    # Detalhamento sem linha intermediária "Despesas operacionais" que no Domínio
    # exclui despesas financeiras/outras e quebrava a soma visual.
    rows = [
        ("Receita operacional bruta", dre["receita_bruta"], False),
        ("(-) Deduções da receita bruta", dre["deducoes"], False),
        ("(=) Receita operacional líquida", dre["receita_liquida"], True),
    ]
    if dre["custos"]:
        rows.append(("(+/-) Custos com cessão / recebíveis", dre["custos"], False))
    rows.append(("(=) Lucro bruto", dre["lucro_bruto"], True))
    if dre.get("despesas_vendas"):
        rows.append(("(-) Despesas com vendas", dre["despesas_vendas"], False))
    rows += [
        ("(-) Despesas com pessoal", dre["despesas_pessoal"], False),
        ("(-) Aluguéis e arrendamentos", dre["alugueis"], False),
        ("(-) Impostos, taxas e contribuições", dre["impostos_taxas"], False),
        ("(-) Despesas administrativas", dre["despesas_admin"], False),
        ("(-) Despesas financeiras", dre["despesas_financeiras"], False),
    ]
    if dre["receitas_financeiras"]:
        rows.append(("(+) Receitas financeiras", dre["receitas_financeiras"], False))
    if dre["outras_despesas"]:
        rows.append(("(-) Outras despesas operacionais", dre["outras_despesas"], False))
    rows.append(("(=) Resultado operacional líquido", dre["resultado_operacional"], True))
    if dre["receitas_nao_operacionais"]:
        rows.append(("(+) Receitas não operacionais", dre["receitas_nao_operacionais"], False))
    rows.append(("(=) Resultado antes do IR/CSLL", dre["resultado_antes_ir"], True))
    if dre["ir_csll"]:
        rows.append(("(-) Provisão para IR e CSLL", dre["ir_csll"], False))
    label_res = "(=) Lucro líquido do exercício" if dre["resultado"] >= 0 else "(=) Prejuízo líquido do exercício"
    rows.append((label_res, dre["resultado"], True))

    data = []
    for desc, val, bold in rows:
        style = st["cell_b"] if bold else st["cell"]
        data.append([Paragraph(desc, style), Paragraph(brl(val), style)])

    t = Table(data, colWidths=[14 * cm, 3.5 * cm])
    t.setStyle(
        TableStyle(
            [
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LINEBELOW", (0, 0), (-1, -2), 0.2, LINHA),
                ("BOX", (0, 0), (-1, -1), 0.4, LINHA),
                ("BACKGROUND", (0, -1), (-1, -1), AZUL_CLARO),
            ]
        )
    )
    elems.append(t)
    elems.append(Spacer(1, 3 * mm))
    elems.append(
        Paragraph(
            "* As notas explicativas são parte integrante das demonstrações contábeis.",
            st["footer"],
        )
    )
    elems += assinaturas(st)
    return elems


def build_dmpl(ano, d, st):
    elems = [Paragraph("III — DEMONSTRAÇÃO DAS MUTAÇÕES DO PATRIMÔNIO LÍQUIDO (DMPL)", st["h2"])]
    elems.append(Paragraph("Valores expressos em Reais (R$)", st["subtitle"]))

    header = [
        Paragraph("<b>Histórico</b>", st["cell_b"]),
        Paragraph("<b>Capital Social</b>", st["cell_b"]),
        Paragraph("<b>Capital a Integralizar / AFAC</b>", st["cell_b"]),
        Paragraph("<b>Lucros/Prejuízos Acumulados</b>", st["cell_b"]),
        Paragraph("<b>Total</b>", st["cell_b"]),
    ]
    data = [header]
    for hist, cap, afac, luc, tot in d["dmpl"]:
        bold = hist.startswith("Saldo")
        style = st["cell_b"] if bold else st["cell"]
        data.append(
            [
                Paragraph(hist, style),
                Paragraph(brl(cap), style),
                Paragraph(brl(afac), style),
                Paragraph(brl(luc), style),
                Paragraph(brl(tot), style),
            ]
        )

    t = Table(data, colWidths=[5.2 * cm, 2.8 * cm, 3.2 * cm, 3.5 * cm, 2.8 * cm])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), AZUL_CLARO),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("BOX", (0, 0), (-1, -1), 0.4, LINHA),
                ("INNERGRID", (0, 0), (-1, -1), 0.2, LINHA),
            ]
        )
    )
    elems.append(t)
    elems += assinaturas(st)
    return elems


def build_dlpa(ano, d, st):
    elems = [Paragraph("IV — DEMONSTRAÇÃO DE LUCROS OU PREJUÍZOS ACUMULADOS (DLPA)", st["h2"])]
    elems.append(Paragraph("Valores expressos em Reais (R$)", st["subtitle"]))

    data = []
    for desc, val in d["dlpa"]:
        bold = desc.startswith("Saldo")
        style = st["cell_b"] if bold else st["cell"]
        data.append([Paragraph(desc, style), Paragraph(brl(val), style)])

    t = Table(data, colWidths=[14 * cm, 3.5 * cm])
    t.setStyle(
        TableStyle(
            [
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("BOX", (0, 0), (-1, -1), 0.4, LINHA),
                ("LINEBELOW", (0, 0), (-1, -2), 0.2, LINHA),
                ("BACKGROUND", (0, -1), (-1, -1), AZUL_CLARO),
            ]
        )
    )
    elems.append(t)
    elems += assinaturas(st)
    return elems


def build_dfc(ano, d, st):
    dfc = d["dfc"]
    elems = [Paragraph("V — DEMONSTRAÇÃO DOS FLUXOS DE CAIXA — MÉTODO INDIRETO", st["h2"])]
    elems.append(Paragraph("Valores expressos em Reais (R$)", st["subtitle"]))

    rows = [
        ("1 — Fluxos de caixa das atividades operacionais", None, True),
        ("Resultado do exercício/período", dfc["resultado"], False),
        ("(=) Disponibilidades líquidas das atividades operacionais", dfc["cx_operacional"], True),
        ("2 — Fluxos de caixa das atividades de investimentos", None, True),
        ("(=) Disponibilidades líquidas das atividades de investimento", dfc["cx_investimento"], True),
        ("3 — Fluxos de caixa das atividades de financiamentos", None, True),
        ("(=) Disponibilidades líquidas das atividades de financiamento", dfc["cx_financiamento"], True),
        ("4 — Aumento/(redução) nas disponibilidades (1+/-2+/-3)", dfc["variacao_caixa"], True),
        ("5 — Disponibilidades no início do período", dfc["caixa_inicial"], False),
        ("6 — Disponibilidades no final do período (4+/-5)", dfc["caixa_final"], True),
    ]

    data = []
    for desc, val, bold in rows:
        style = st["cell_b"] if bold else st["cell"]
        data.append(
            [
                Paragraph(desc, style),
                Paragraph(brl(val) if val is not None else "", style),
            ]
        )

    t = Table(data, colWidths=[14 * cm, 3.5 * cm])
    t.setStyle(
        TableStyle(
            [
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("BOX", (0, 0), (-1, -1), 0.4, LINHA),
                ("LINEBELOW", (0, 0), (-1, -2), 0.2, LINHA),
                ("BACKGROUND", (0, -1), (-1, -1), AZUL_CLARO),
            ]
        )
    )
    elems.append(t)
    if dfc.get("notas_dfc"):
        elems.append(Spacer(1, 3 * mm))
        elems.append(Paragraph(dfc["notas_dfc"], st["small"]))
    elems += assinaturas(st)
    return elems


def build_notas(ano, d, st):
    ns = d["notas_especiais"]
    elems = [Paragraph("VI — NOTAS EXPLICATIVAS ÀS DEMONSTRAÇÕES CONTÁBEIS", st["h2"])]
    elems.append(
        Paragraph(
            f"Notas explicativas às demonstrações contábeis para o exercício findo "
            f"em 31 de dezembro de {ano}.",
            st["body"],
        )
    )

    elems.append(Paragraph("1. CONTEXTO OPERACIONAL", st["nota_titulo"]))
    elems.append(
        Paragraph(
            f"A {EMPRESA}, inscrita no CNPJ sob o nº {CNPJ}, NIRE {NIRE}, com sede em "
            f"{ENDERECO}, é uma sociedade anônima fechada e tem por objeto a {OBJETO}. "
            f"A Companhia atua sob a marca Credit Saint Germain "
            f"(<font color='#0B3A6E'>{SITE}</font>), auxiliando pessoas a realizarem "
            f"tratamentos de saúde mediante crédito facilitado, e apoiando clínicas e "
            f"empresas da área da saúde com pagamento à vista dos procedimentos. "
            f"O endereço acima corresponde ao constante dos atos societários e "
            f"instrumentos de emissão de debêntures; canais de atendimento ao público "
            f"também são divulgados no sítio eletrônico da Companhia.",
            st["body"],
        )
    )
    elems.append(
        Paragraph(
            "<b>1.1. Contabilidade terceirizada:</b> Os administradores da companhia "
            "optaram pela contratação de contabilidade terceirizada, regulamentada "
            "pelo Conselho Federal de Contabilidade. Os resultados produzidos decorrem "
            "do documental remetido para contabilização pela administração da companhia, "
            "que responde pela veracidade, integralidade e procedência. A responsabilidade "
            "profissional do contabilista que referenda estas demonstrações está limitada "
            "aos fatos contábeis efetivamente notificados pela administração.",
            st["body"],
        )
    )

    elems.append(Paragraph("2. APRESENTAÇÃO DAS DEMONSTRAÇÕES CONTÁBEIS", st["nota_titulo"]))
    elems.append(
        Paragraph(
            f"As demonstrações contábeis inerentes ao exercício findo em 31 de dezembro "
            f"de {ano} foram elaboradas com base nas práticas contábeis brasileiras, que "
            f"compreendem a legislação societária brasileira (Lei nº 6.404/76 e alterações), "
            f"os Pronunciamentos, Interpretações e Orientações emitidos pelo CPC e "
            f"homologados pelos órgãos reguladores, em consonância com as normas contábeis "
            f"aplicáveis. Esta publicação destina-se à Central de Balanços do SPED, nos "
            f"termos da Portaria ME nº 12.071/2021, considerando receita bruta anual inferior "
            f"a R$ 78.000.000,00.",
            st["body"],
        )
    )

    elems.append(Paragraph("3. PRINCIPAIS PRÁTICAS CONTÁBEIS", st["nota_titulo"]))
    praticas = [
        (
            "a) Caixa e equivalentes de caixa",
            "Mantidos para atender compromissos de curto prazo, compostos por depósitos "
            "bancários à vista e aplicações financeiras de conversibilidade imediata em "
            "montante conhecido de caixa, com insignificante risco de mudança de valor.",
        ),
        (
            "b) Contas a receber / Direitos creditórios",
            "Representam valores a receber de clientes e direitos creditórios decorrentes "
            "das operações de securitização e cessão de créditos da Companhia.",
        ),
        (
            "c) Imobilizado",
            "Ativos de natureza permanente utilizados na manutenção das atividades, "
            "não destinados à venda, registrados pelo custo de aquisição deduzido das "
            "depreciações/amortizações acumuladas.",
        ),
        (
            "d) Reconhecimento de receitas e despesas",
            "Receitas e despesas são reconhecidas pelo regime de competência.",
        ),
        (
            "e) Fornecedores e outras obrigações",
            "Valores devidos a fornecedores e demais credores pela aquisição de bens e "
            "serviços necessários às operações.",
        ),
        (
            "f) Obrigações trabalhistas e sociais",
            "Responsabilidades com empregados, incluindo salários, encargos sociais e "
            "benefícios devidos.",
        ),
        (
            "g) Obrigações tributárias",
            "Tributos e encargos a pagar sobre o faturamento e demais obrigações fiscais "
            "de curto prazo.",
        ),
        (
            "h) Debêntures",
            "Obrigações decorrentes de emissões de debêntures simples da espécie "
            "subordinada, conforme escrituras de emissão e aditamentos registrados na "
            "JUCISRS.",
        ),
        (
            "i) Imposto de Renda e Contribuição Social",
            "Quando aplicáveis, calculados com base nas alíquotas vigentes (IRPJ 15% "
            "mais adicional de 10% sobre o lucro excedente a R$ 240.000,00 ao ano, e "
            "CSLL 9%), considerando compensação de prejuízos fiscais quando cabível.",
        ),
    ]
    for tit, txt in praticas:
        elems.append(Paragraph(f"<b>{tit}</b>", st["small"]))
        elems.append(Paragraph(txt, st["body"]))

    elems.append(Paragraph("4. PATRIMÔNIO LÍQUIDO", st["nota_titulo"]))
    elems.append(Paragraph("<b>a) Capital Social</b>", st["small"]))
    elems.append(Paragraph(ns["capital_texto"], st["body"]))
    elems.append(Paragraph("<b>b) Resultado do Exercício</b>", st["small"]))
    elems.append(Paragraph(ns["resultado_texto"], st["body"]))

    elems.append(Paragraph("5. DEBÊNTURES", st["nota_titulo"]))
    elems.append(
        Paragraph(
            f"Ao final do exercício de {ano}, o saldo de debêntures emitidas pela "
            f"Companhia montava R$ {brl(d['bp']['debentures'])}, conforme registros "
            f"contábeis e instrumentos de emissão/aditamento arquivados na Junta Comercial.",
            st["body"],
        )
    )

    elems.append(Paragraph("6. EVENTOS SUBSEQUENTES", st["nota_titulo"]))
    elems.append(
        Paragraph(
            "Não foram identificados eventos subsequentes relevantes entre a data de "
            "encerramento do exercício e a data de elaboração destas demonstrações que "
            "requeiram ajuste ou divulgação adicional, além das deliberações societárias "
            "ordinárias previstas para aprovação das contas.",
            st["body"],
        )
    )

    elems.append(Spacer(1, 8 * mm))
    elems += assinaturas(st, f"Santa Maria, 31 de dezembro de {ano}.")
    return elems


def add_page_number(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(CINZA)
    canvas.drawString(1.5 * cm, 1.2 * cm, EMPRESA)
    canvas.drawRightString(
        A4[0] - 1.5 * cm,
        1.2 * cm,
        f"CNPJ {CNPJ}  |  Folha {doc.page}",
    )
    canvas.restoreState()


def gerar_pdf(ano: int) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"Demonstrações_Contábeis_Completas_(DCC)_{CNPJ_FILE}_01-01-{ano}_31-12-{ano}.pdf"
    d = DADOS[ano]
    st = styles()

    doc = SimpleDocTemplate(
        str(out),
        pagesize=A4,
        leftMargin=1.4 * cm,
        rightMargin=1.4 * cm,
        topMargin=1.2 * cm,
        bottomMargin=1.8 * cm,
        title=f"DCC {EMPRESA} {ano}",
        author=EMPRESA,
    )

    story = []
    story += header_block(ano, st)
    story += build_bp(ano, d, st)
    story.append(PageBreak())
    story += header_block(ano, st)
    story += build_dre(ano, d, st)
    story.append(PageBreak())
    story += header_block(ano, st)
    story += build_dmpl(ano, d, st)
    story.append(PageBreak())
    story += header_block(ano, st)
    story += build_dlpa(ano, d, st)
    story.append(PageBreak())
    story += header_block(ano, st)
    story += build_dfc(ano, d, st)
    story.append(PageBreak())
    story += header_block(ano, st)
    story += build_notas(ano, d, st)

    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
    return out


def main():
    gerados = []
    for ano in (2022, 2023, 2024, 2025):
        path = gerar_pdf(ano)
        gerados.append(path)
        print(f"OK  {path.name}  ({path.stat().st_size:,} bytes)")
    print(f"\n{len(gerados)} PDFs gerados em: {OUT_DIR}")


if __name__ == "__main__":
    main()
