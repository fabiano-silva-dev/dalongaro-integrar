"""Gera o ofício DOCX de resposta aos esclarecimentos da Administração Judicial."""

from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

SAIDA = Path(__file__).resolve().parent / "Resposta_Esclarecimentos_Grupo_Bianchi_setembro_2026.docx"


def set_run_font(run, name="Times New Roman", size=12, bold=False, italic=False, color=None):
    run.font.name = name
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    if color is not None:
        run.font.color.rgb = color


def add_paragraph(
    doc,
    text="",
    *,
    size=12,
    bold=False,
    italic=False,
    align=WD_ALIGN_PARAGRAPH.JUSTIFY,
    space_before=0,
    space_after=8,
    first_line=None,
):
    p = doc.add_paragraph()
    p.alignment = align
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
    if first_line is not None:
        p.paragraph_format.first_line_indent = Cm(first_line)
    if text:
        run = p.add_run(text)
        set_run_font(run, size=size, bold=bold, italic=italic)
    return p


def shade_cell(cell, fill="1F4E79"):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    shd.set(qn("w:val"), "clear")
    tcPr.append(shd)


def set_cell_border(cell):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcBorders = OxmlElement("w:tcBorders")
    for edge in ("top", "left", "bottom", "right"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "4")
        el.set(qn("w:color"), "1F4E79")
        tcBorders.append(el)
    tcPr.append(tcBorders)


def write_cell(cell, text, *, bold=False, white=False, center=False, size=10):
    cell.text = ""
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER if center else WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after = Pt(3)
    run = p.add_run(text)
    set_run_font(run, size=size, bold=bold, color=RGBColor(255, 255, 255) if white else RGBColor(0, 0, 0))
    set_cell_border(cell)


def add_bottom_border(paragraph, color="1F4E79", sz="18"):
    pPr = paragraph._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), sz)
    bottom.set(qn("w:space"), "4")
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

    header = add_paragraph(doc, "GRUPO BIANCHI", size=18, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    add_bottom_border(header)
    add_paragraph(
        doc,
        "Recuperação Judicial  ·  Esclarecimentos à Administração Judicial",
        size=10,
        italic=True,
        align=WD_ALIGN_PARAGRAPH.CENTER,
        space_before=4,
        space_after=16,
    )

    add_paragraph(doc, "À Administração Judicial", size=12, bold=True, align=WD_ALIGN_PARAGRAPH.LEFT, space_after=2)
    add_paragraph(
        doc,
        "Andreatta & Giongo Consultores Associados S/S",
        size=12,
        align=WD_ALIGN_PARAGRAPH.LEFT,
        space_after=2,
    )
    add_paragraph(
        doc,
        "Aos cuidados de Genil Andreatta e Luciano José Giongo",
        size=11,
        align=WD_ALIGN_PARAGRAPH.LEFT,
        space_after=2,
    )
    add_paragraph(
        doc,
        "E-mails: genil@recuperacaojudicial.net.br  ·  edinaprohde@gmail.com",
        size=11,
        align=WD_ALIGN_PARAGRAPH.LEFT,
        space_after=12,
    )

    p = add_paragraph(doc, align=WD_ALIGN_PARAGRAPH.LEFT, space_after=2)
    r = p.add_run("Assunto: ")
    set_run_font(r, bold=True)
    r = p.add_run("Resposta à solicitação de esclarecimentos de 04 de setembro de 2026")
    set_run_font(r)

    p = add_paragraph(doc, align=WD_ALIGN_PARAGRAPH.LEFT, space_after=12)
    r = p.add_run("Referência: ")
    set_run_font(r, bold=True)
    r = p.add_run("art. 22, inciso II, da Lei nº 11.101/2005")
    set_run_font(r)

    add_paragraph(doc, "Prezados Senhores,", align=WD_ALIGN_PARAGRAPH.LEFT, space_after=10)

    add_paragraph(
        doc,
        "Em atendimento à solicitação de esclarecimentos datada de 04 de setembro de 2026, "
        "o Grupo Bianchi apresenta as informações abaixo, na ordem dos quesitos formulados.",
        first_line=1.25,
    )

    # --- Item 1 ---
    add_paragraph(
        doc,
        "1. Destinação financeira dos resultados — Claudio Bortoluzzi Bianchi",
        size=12,
        bold=True,
        align=WD_ALIGN_PARAGRAPH.LEFT,
        space_before=10,
        space_after=8,
    )
    add_paragraph(
        doc,
        "O montante de R$ 2.826.820,43, apontado como resultado positivo acumulado no período "
        "de junho a julho de 2026, corresponde à apuração pelo regime de competência (receitas "
        "reconhecidas no período), e não ao ingresso efetivo de caixa no mesmo intervalo.",
        first_line=1.25,
    )
    add_paragraph(
        doc,
        "Desse modo, o resultado positivo do período não se confunde com disponibilidade financeira "
        "imediata. Parte relevante das receitas reconhecidas em junho e julho permanece, no próprio "
        "período, na forma de contas a receber, sendo liquidada em data posterior à competência das notas.",
        first_line=1.25,
    )
    add_paragraph(
        doc,
        "A destinação financeira (regime de caixa) dos recursos efetivamente recebidos por "
        "Claudio Bortoluzzi Bianchi está sendo consolidada a partir dos pagamentos lançados no "
        "controle financeiro — fornecedores, obrigações, insumos, empréstimos e disponibilidades. "
        "O detalhamento analítico dos desembolsos será encaminhado em complemento a este ofício, "
        "tão logo concluída a filtragem no sistema.",
        first_line=1.25,
    )

    # --- Item 2 ---
    add_paragraph(
        doc,
        "2. Destinação financeira dos resultados — Luciano Bianchi",
        size=12,
        bold=True,
        align=WD_ALIGN_PARAGRAPH.LEFT,
        space_before=10,
        space_after=8,
    )
    add_paragraph(
        doc,
        "O montante de R$ 6.930.256,13, apontado como resultado positivo acumulado no período "
        "de junho a julho de 2026, decorre, em essência, da comercialização da safra de gergelim, "
        "com notas fiscais emitidas em junho e julho de 2026.",
        first_line=1.25,
    )
    add_paragraph(
        doc,
        "A liquidação financeira dessas vendas não ocorreu no período de competência. O pagamento "
        "pelo comprador foi creditado em 20/08/2026, no valor líquido de R$ 6.665.030,93, depositado "
        "em conta. A diferença entre o resultado apurado na competência e o valor líquido creditado "
        "corresponde a glosas, encargos e retenções próprias da liquidação comercial (frete, qualidade, "
        "tributos incidentes na comercialização e demais abatimentos de acerto).",
        first_line=1.25,
    )
    add_paragraph(
        doc,
        "Portanto, no bimestre junho–julho de 2026 os recursos equivalentes a essas vendas estavam "
        "em contas a receber, e não em disponibilidades. Somente a partir de 20/08/2026 o caixa "
        "passou a ser aplicado, de forma resumida, nas destinações abaixo.",
        first_line=1.25,
    )

    table = doc.add_table(rows=5, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True
    headers = ("Destinação", "Esclarecimento")
    rows = [
        (
            "Disponibilidades",
            "Ingresso líquido de R$ 6.665.030,93 em 20/08/2026, mantido em conta até as liquidações subsequentes.",
        ),
        (
            "Arrendamentos",
            "Pagamento de arrendamentos em atraso do arrendador Peter, após o crédito do gergelim.",
        ),
        (
            "Custeio da atividade rural e fornecedores",
            "Demais obrigações da lavoura e do giro operacional, em liquidação pela equipe financeira após o ingresso do recurso.",
        ),
        (
            "Empréstimos",
            "Eventuais amortizações com o recurso do gergelim, se houver, constarão do complemento analítico após a filtragem no controle financeiro.",
        ),
    ]
    write_cell(table.rows[0].cells[0], headers[0], bold=True, white=True, center=True, size=10)
    write_cell(table.rows[0].cells[1], headers[1], bold=True, white=True, center=True, size=10)
    shade_cell(table.rows[0].cells[0], "1F4E79")
    shade_cell(table.rows[0].cells[1], "1F4E79")
    for i, (a, b) in enumerate(rows, start=1):
        fill = "F2F2F2" if i % 2 == 0 else "FFFFFF"
        write_cell(table.rows[i].cells[0], a, bold=True, size=10)
        write_cell(table.rows[i].cells[1], b, size=10)
        shade_cell(table.rows[i].cells[0], fill)
        shade_cell(table.rows[i].cells[1], fill)

    add_paragraph(
        doc,
        "Em síntese: o resultado positivo de junho–julho é efeito da competência das notas de "
        "gergelim; o caixa correspondente ingressou em 20/08/2026 e vem sendo destinado ao "
        "pagamento de arrendamentos em atraso e ao custeio da atividade rural, com o saldo "
        "remanescente em disponibilidades.",
        first_line=1.25,
        space_before=10,
    )

    # --- Item 3 ---
    add_paragraph(
        doc,
        "3. Produção e comercialização do gergelim — Luciano Bianchi",
        size=12,
        bold=True,
        align=WD_ALIGN_PARAGRAPH.LEFT,
        space_before=10,
        space_after=8,
    )
    add_paragraph(
        doc,
        "Seguem os dados finais da safra de gergelim 2026, conforme os indicadores solicitados:",
        first_line=1.25,
    )

    table3 = doc.add_table(rows=7, cols=2)
    table3.alignment = WD_TABLE_ALIGNMENT.CENTER
    t3 = [
        ("Indicador", "Informação"),
        ("Área cultivada (ha)", "3.400 ha"),
        ("Produção apurada (kg)", "2.936.462,59 kg"),
        ("Produtividade média (kg/ha)", "863,67 kg/ha"),
        ("Desempenho informado", "Safra integralmente colhida e comercializada (100% da produção apurada)."),
        ("Quantidade comercializada (kg)", "2.936.462,59 kg"),
        (
            "Destinação da produção",
            "Comercialização integral com a Arbaza Alimentos Ltda. Saldo líquido depositado em conta em 20/08/2026, no valor de R$ 6.665.030,93.",
        ),
    ]
    for i, (a, b) in enumerate(t3):
        if i == 0:
            write_cell(table3.rows[i].cells[0], a, bold=True, white=True, center=True, size=10)
            write_cell(table3.rows[i].cells[1], b, bold=True, white=True, center=True, size=10)
            shade_cell(table3.rows[i].cells[0], "1F4E79")
            shade_cell(table3.rows[i].cells[1], "1F4E79")
        else:
            fill = "F2F2F2" if i % 2 == 0 else "FFFFFF"
            write_cell(table3.rows[i].cells[0], a, bold=True, size=10)
            write_cell(table3.rows[i].cells[1], b, size=10)
            shade_cell(table3.rows[i].cells[0], fill)
            shade_cell(table3.rows[i].cells[1], fill)

    add_paragraph(
        doc,
        "A produtividade média (863,67 kg/ha) resulta da divisão da produção apurada pela área "
        "cultivada (2.936.462,59 kg ÷ 3.400 ha).",
        first_line=1.25,
        space_before=10,
    )

    add_paragraph(
        doc,
        "Permanecemos à disposição para os esclarecimentos complementares que se fizerem "
        "necessários, inclusive o detalhamento analítico de caixa do item 1.",
        first_line=1.25,
        space_before=6,
    )
    add_paragraph(doc, "Atenciosamente,", align=WD_ALIGN_PARAGRAPH.LEFT, space_before=8, space_after=16)
    add_paragraph(
        doc,
        "Rio Grande do Sul, 08 de setembro de 2026.",
        align=WD_ALIGN_PARAGRAPH.LEFT,
        space_after=20,
    )

    add_paragraph(doc, "________________________________", align=WD_ALIGN_PARAGRAPH.CENTER, space_after=0)
    add_paragraph(doc, "Claudio Bortoluzzi Bianchi", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    add_paragraph(doc, "Recuperando", size=10, italic=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=16)

    add_paragraph(doc, "________________________________", align=WD_ALIGN_PARAGRAPH.CENTER, space_after=0)
    add_paragraph(doc, "Luciano Bianchi", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    add_paragraph(doc, "Recuperando", size=10, italic=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=0)

    doc.save(SAIDA)
    print(f"Gerado: {SAIDA}")


if __name__ == "__main__":
    build()
