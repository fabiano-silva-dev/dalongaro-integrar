"""Gera o ofício DOCX de resposta aos esclarecimentos da Administração Judicial."""

from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

PASTA = Path(__file__).resolve().parent
SAIDAS = [
    PASTA / "Resposta_Esclarecimentos_Grupo_Bianchi_08-09-2026.docx",
    PASTA / "Resposta_Esclarecimentos_Grupo_Bianchi_setembro_2026.docx",
]


def set_run_font(run, name="Arial", size=11, bold=False, italic=False):
    run.font.name = name
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    run.font.color.rgb = RGBColor(0, 0, 0)


def add_paragraph(
    doc,
    text="",
    *,
    size=11,
    bold=False,
    italic=False,
    align=WD_ALIGN_PARAGRAPH.JUSTIFY,
    space_before=0,
    space_after=8,
    first_line=None,
    runs=None,
):
    p = doc.add_paragraph()
    p.alignment = align
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
    if first_line is not None:
        p.paragraph_format.first_line_indent = Cm(first_line)
    if runs:
        for piece, kw in runs:
            r = p.add_run(piece)
            set_run_font(r, size=size, **kw)
    elif text:
        r = p.add_run(text)
        set_run_font(r, size=size, bold=bold, italic=italic)
    return p


def add_bottom_border(paragraph, color="808080", sz="8"):
    pPr = paragraph._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), sz)
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), color)
    pBdr.append(bottom)
    pPr.append(pBdr)


def build():
    doc = Document()
    section = doc.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(2.5)
    section.top_margin = Cm(2.0)
    section.bottom_margin = Cm(2.0)

    add_paragraph(doc, "GRUPO BIANCHI", size=18, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    sub = add_paragraph(
        doc,
        "Recuperação Judicial · Esclarecimentos à Administração Judicial",
        size=11,
        italic=True,
        align=WD_ALIGN_PARAGRAPH.CENTER,
        space_after=4,
    )
    add_bottom_border(sub)
    add_paragraph(doc, space_after=10)

    add_paragraph(
        doc,
        align=WD_ALIGN_PARAGRAPH.LEFT,
        space_after=4,
        runs=[
            ("Assunto: ", {"bold": True}),
            ("Resposta à solicitação de esclarecimentos de 04 de setembro de 2026", {"bold": False}),
        ],
    )
    add_paragraph(
        doc,
        align=WD_ALIGN_PARAGRAPH.LEFT,
        space_after=12,
        runs=[
            ("Referência: ", {"bold": True}),
            ("art. 22, inciso II, da Lei nº 11.101/2005", {"bold": False}),
        ],
    )

    add_paragraph(doc, "Prezados Senhores,", align=WD_ALIGN_PARAGRAPH.LEFT, space_after=8)
    add_paragraph(
        doc,
        "Em atenção à solicitação de esclarecimentos datada de 04 de setembro de 2026, "
        "o Grupo Bianchi apresenta as informações a seguir, na ordem dos quesitos formulados.",
    )

    add_paragraph(
        doc,
        "1. Destinação financeira dos resultados — Claudio Bortoluzzi Bianchi",
        bold=True,
        align=WD_ALIGN_PARAGRAPH.LEFT,
        space_before=10,
        space_after=8,
    )
    add_paragraph(
        doc,
        "Os esclarecimentos fundamentam-se no Balancete Consolidado de 01/06/2026 a 31/07/2026 "
        "(empresas 666, 707, 708 e 709, CNPJ 55.524.729/0001-59) e no Razão das contas de "
        "disponibilidade do mesmo período (Caixa Geral, Sicoob, Vortix Grafeno e Banco Kreditare/Money Plus).",
    )
    add_paragraph(
        doc,
        "O resultado positivo apurado no bimestre (R$ 2.111.776,65) decorre do regime de competência: "
        "vendas de soja faturadas a prazo à Cotrijuc no total de R$ 3.313.050,00, deduzidas as despesas "
        "do período de R$ 1.203.139,85. O resultado contábil não representou ingresso imediato e integral "
        "do mesmo valor no caixa.",
    )

    add_paragraph(
        doc,
        "A) Origem dos recursos no caixa (Razão de disponibilidades)",
        bold=True,
        align=WD_ALIGN_PARAGRAPH.LEFT,
        space_before=6,
        space_after=6,
    )
    add_paragraph(
        doc,
        "Liquidação de duplicatas da Cotrijuc: R$ 5.673.050,00, creditados sobretudo na Kreditare/Money Plus "
        "e na Vortix Grafeno (NFs 312/313, 321, 325, 327, 330, 334, 337, 340, 344, 346, 351 e 356). "
        "O maior ingresso isolado foi R$ 2.360.000,00 em 02/06/2026.",
        first_line=0.5,
    )
    add_paragraph(
        doc,
        "Aportes e empréstimos tomados de partes relacionadas: R$ 220.760,38.",
        first_line=0.5,
    )
    add_paragraph(
        doc,
        "Houve ainda transferências internas entre Grafeno, Kreditare e Sicoob, que não alteram o caixa consolidado.",
    )

    add_paragraph(
        doc,
        "B) Destinação financeira (saídas efetivas de caixa, conforme o Razão)",
        bold=True,
        align=WD_ALIGN_PARAGRAPH.LEFT,
        space_before=6,
        space_after=6,
    )
    add_paragraph(
        doc,
        "Os recursos liquidados no bimestre foram aplicados nas seguintes frentes. Os valores abaixo "
        "saíram das contas de disponibilidade e conferem com o Balancete:",
    )
    add_paragraph(
        doc,
        "1. Mútuos / empréstimos intercompany — R$ 4.309.453,58, liquidados pelas contas Grafeno e Kreditare, "
        "com destaque para Luciano Bianchi PJ (R$ 3.540.188,01), Fabiane Maria Noal Bianchi PJ (R$ 304.515,45) "
        "e Agrobianchi Transportes (R$ 210.500,00). Em 02/06/2026, no mesmo dia do recebimento de R$ 2.360.000,00 "
        "da Cotrijuc, a Kreditare destinou R$ 2.300.000,00 a Luciano Bianchi PJ.",
        first_line=0.5,
    )
    add_paragraph(
        doc,
        "2. Arrendamentos agrícolas — R$ 715.123,20, pagos em caixa pela Kreditare em 05/06/2026 "
        "(R$ 240.235,89) e 08/06/2026 (R$ 185.764,20 e R$ 289.123,11).",
        first_line=0.5,
    )
    add_paragraph(
        doc,
        "3. Adiantamentos a fornecedores — R$ 584.962,10, saídas de caixa para manutenção de suprimentos "
        "e serviços (Maestria, Andreatta & Giongo, Bagualmaq e demais).",
        first_line=0.5,
    )
    add_paragraph(
        doc,
        "4. Pagamento direto a fornecedores — R$ 225.499,01 (Itaimbe, Mineração Monego, Super Tratores, "
        "Dal Ongaro, Base Assessoria e outros).",
        first_line=0.5,
    )
    add_paragraph(
        doc,
        "5. Custeio operacional pago no caixa — folha, adicionais, rescisões, INSS, FGTS, diaristas, "
        "seguros, energia e tarifas bancárias (R$ 2.678,80), lançados nas contas Grafeno, Kreditare, Sicoob e Caixa.",
        first_line=0.5,
    )

    add_paragraph(
        doc,
        "C) Verbas do Balancete que não representaram desembolso no bimestre",
        bold=True,
        align=WD_ALIGN_PARAGRAPH.LEFT,
        space_before=6,
        space_after=6,
    )
    add_paragraph(
        doc,
        "Estoque de insumos de R$ 3.856.690,00: aquisição a prazo, em especial junto à Cotrijuc, cujo passivo "
        "de fornecedores aumentou R$ 3.828.140,00 no bimestre, sem correspondente saída das contas de disponibilidade.",
        first_line=0.5,
    )
    add_paragraph(
        doc,
        "Imobilizado de R$ 78.000,00: máquinas e equipamentos adquiridos a prazo (WG Soluções Elétricas), "
        "ainda em aberto no passivo de fornecedores.",
        first_line=0.5,
    )

    add_paragraph(
        doc,
        "D) Disponibilidades ao final do bimestre",
        bold=True,
        align=WD_ALIGN_PARAGRAPH.LEFT,
        space_before=6,
        space_after=6,
    )
    add_paragraph(
        doc,
        "Diante das destinações acima, o saldo de caixa e bancos caiu de R$ 222.200,13 para R$ 58.101,52, "
        "assim distribuído no Razão: Vortix Grafeno R$ 44.929,31; Caixa Geral R$ 8.573,50; "
        "Sicoob R$ 4.193,98; Kreditare/Money Plus R$ 404,73.",
    )

    add_paragraph(
        doc,
        "2. Destinação financeira dos resultados — Luciano Bianchi",
        bold=True,
        align=WD_ALIGN_PARAGRAPH.LEFT,
        space_before=12,
        space_after=8,
    )
    add_paragraph(
        doc,
        "O resultado positivo de R$ 6.930.256,13 apurado no período de junho e julho de 2026 decorre, "
        "essencialmente, da comercialização da safra de gergelim por regime de competência (notas fiscais "
        "emitidas no bimestre).",
    )
    add_paragraph(
        doc,
        "A liquidação financeira dessas vendas ocorreu em momento posterior ao encerramento do bimestre. "
        "Dessa forma, no período analisado, o montante correspondente integrava o saldo de contas a receber, "
        "não figurando na disponibilidade imediata de caixa do bimestre.",
    )

    add_paragraph(
        doc,
        "3. Produção e comercialização do gergelim — Luciano Bianchi",
        bold=True,
        align=WD_ALIGN_PARAGRAPH.LEFT,
        space_before=12,
        space_after=8,
    )
    add_paragraph(
        doc,
        "Seguem os dados consolidados da safra de gergelim 2026:",
    )
    add_paragraph(doc, "Área cultivada: 3.400 ha", first_line=0.5, space_after=4)
    add_paragraph(doc, "Produção apurada: 2.936.462,59 kg", first_line=0.5, space_after=4)
    add_paragraph(doc, "Produtividade média: 863,67 kg/ha", first_line=0.5, space_after=4)
    add_paragraph(doc, "Desempenho da safra: 100% da produção apurada colhida e comercializada.", first_line=0.5, space_after=4)
    add_paragraph(
        doc,
        "Destinação e recebimento: venda integral à Arbaza Alimentos Ltda., cujo saldo líquido de "
        "R$ 6.665.030,93 ingressou na conta bancária em 20/08/2026.",
        first_line=0.5,
    )

    add_paragraph(
        doc,
        "Permanecemos à disposição para eventuais esclarecimentos complementares.",
        space_before=8,
    )
    add_paragraph(doc, "Atenciosamente,", align=WD_ALIGN_PARAGRAPH.LEFT, space_before=8, space_after=12)
    add_paragraph(
        doc,
        "Rio Grande do Sul, 08 de setembro de 2026.",
        align=WD_ALIGN_PARAGRAPH.LEFT,
    )

    for saida in SAIDAS:
        doc.save(saida)
        print(f"Gerado: {saida}")


if __name__ == "__main__":
    build()
