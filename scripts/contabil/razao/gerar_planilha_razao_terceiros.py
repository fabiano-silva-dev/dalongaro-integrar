#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gera planilha do razão de terceiros a partir de PDF Domínio."""

from __future__ import annotations

import argparse
import importlib.util
import re
import smtplib
import ssl
import sys
import tempfile
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import fitz
import pandas as pd

_SCRIPTS = Path(__file__).resolve().parents[2]
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from runtime import setup_workspace
from contabil.dominio.gerar_planilha_dominio import extrair_nome_empresa, extrair_numero_nota

SEND_EMAIL_PATH = Path('/ico/fabiano/ft/scripts-servidor-eficere/send_email.py')
EMAIL_DESTINO_PADRAO = 'fabiano@iconeweb.com.br'

SKIP_LINES = {
    'RAZÃO', 'CONSOLIDADO', 'Período:', 'C.N.P.J.:', 'Empresa:', 'Conta:',
    'Cta.C.Part.', 'Número Histórico', 'Data', 'Saldo-Exercício', 'Crédito',
    'Débito', 'Folha:', '-', '362', '3.2.2.04.009',
    'SERVIÇOS PRESTADOS POR TERCEIROS', 'SALDO ANTERIOR',
    'Total da conta:', 'Sistema licenciado para VALDECIR DAL ONGARO',
}

RE_DATA = re.compile(r'^\d{2}/\d{2}/\d{4}$')
RE_NUMERO = re.compile(r'^\d{1,5}$')
RE_CTA = re.compile(r'^\d{1,3}$')
RE_VALOR = re.compile(r'^-?\d{1,3}(?:\.\d{3})*,\d{2}$')
RE_PAGINA = re.compile(r'^-- \d+ of \d+ --$')
RE_PREFIXO_DOC = re.compile(r'^[\d.\s:/-]+')


def _load_send_email():
    spec = importlib.util.spec_from_file_location('send_email', SEND_EMAIL_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'Não foi possível carregar {SEND_EMAIL_PATH}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def limpar_nome_terceiro(nome: str) -> str:
    limpo = RE_PREFIXO_DOC.sub('', nome).strip()
    return limpo or nome


def parse_valor_br(texto: str) -> float:
    return float(texto.replace('.', '').replace(',', '.'))


def is_valor(line: str) -> bool:
    return bool(RE_VALOR.match(line.strip()))


def is_header_line(line: str) -> bool:
    line = line.strip()
    if not line or line in SKIP_LINES:
        return True
    if RE_PAGINA.match(line):
        return True
    if 'LUCIANO BIANCHI' in line or '55.531.817' in line:
        return True
    if line.startswith('01/01/2025') or line.startswith('000'):
        return True
    return False


def extrair_linhas_pdf(caminho_pdf: Path) -> list[str]:
    doc = fitz.open(caminho_pdf)
    linhas: list[str] = []
    for page in doc:
        for line in page.get_text('text').split('\n'):
            line = line.strip()
            if line:
                linhas.append(line)
    return linhas


def coletar_historico(linhas: list[str], anchor_idx: int) -> str:
    historico_partes: list[str] = []
    vistos: set[str] = set()

    for j in range(anchor_idx - 1, -1, -1):
        line = linhas[j]
        if is_header_line(line):
            break
        if RE_DATA.match(line) or (RE_NUMERO.match(line) and historico_partes):
            break
        if is_valor(line):
            if historico_partes:
                break
            continue
        if line in vistos:
            break
        vistos.add(line)
        historico_partes.insert(0, line)

    return ' '.join(historico_partes).strip()


def identificar_lancamento(linhas: list[str], data_idx: int) -> tuple[int, str, str, float] | None:
    """Retorna (anchor_idx, data, numero, valor) para padrões com ou sem Cta.C.Part."""
    if data_idx < 1 or data_idx + 1 >= len(linhas):
        return None
    if not RE_DATA.match(linhas[data_idx]) or not is_valor(linhas[data_idx + 1]):
        return None

    numero = linhas[data_idx - 1]
    if not RE_NUMERO.match(numero):
        return None

    valor = parse_valor_br(linhas[data_idx + 1])

    if data_idx >= 2 and RE_CTA.match(linhas[data_idx - 2]):
        return data_idx - 2, linhas[data_idx], numero, valor

    return data_idx - 1, linhas[data_idx], numero, valor


def deve_ignorar_lancamento(historico: str) -> bool:
    historico_upper = historico.upper()
    ignorar = (
        'SALDO ANTERIOR',
        'VLR TRANSF PARA RESULTADO DO EXERCICIO',
    )
    return any(m in historico_upper for m in ignorar)


def extrair_lancamentos(linhas: list[str]) -> list[dict]:
    lancamentos: list[dict] = []

    for i, line in enumerate(linhas):
        if not RE_DATA.match(line):
            continue

        identificado = identificar_lancamento(linhas, i)
        if identificado is None:
            continue

        anchor_idx, data, _numero_razao, valor = identificado
        historico = coletar_historico(linhas, anchor_idx)
        if not historico or deve_ignorar_lancamento(historico):
            continue

        nome_terceiro = limpar_nome_terceiro(extrair_nome_empresa(historico) or historico)

        lancamentos.append({
            'data': data,
            'nome_terceiro': nome_terceiro.strip(),
            'historico': historico,
            'numero_documento': extrair_numero_nota(historico),
            'valor': valor,
        })

    return lancamentos


def gerar_planilha(lancamentos: list[dict], caminho_saida: Path) -> None:
    df_detalhe = pd.DataFrame(lancamentos)
    df_detalhe = df_detalhe[['data', 'nome_terceiro', 'historico', 'numero_documento', 'valor']]

    df_resumo = (
        df_detalhe.groupby('nome_terceiro', as_index=False)['valor']
        .sum()
        .sort_values('nome_terceiro')
    )
    df_resumo.columns = ['nome_terceiro', 'valor']

    with pd.ExcelWriter(caminho_saida, engine='openpyxl') as writer:
        df_detalhe.to_excel(writer, sheet_name='Lançamentos', index=False)
        df_resumo.to_excel(writer, sheet_name='Resumo por Terceiro', index=False)

        for sheet_name in ('Lançamentos', 'Resumo por Terceiro'):
            ws = writer.sheets[sheet_name]
            for col in ws.columns:
                max_len = max(len(str(cell.value or '')) for cell in col)
                ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 60)


def enviar_email_com_anexo(
    destinatario: str,
    assunto: str,
    corpo: str,
    anexo: Path,
) -> None:
    send_email = _load_send_email()

    msg = MIMEMultipart()
    msg['From'] = send_email.EMAIL_FROM
    msg['To'] = destinatario
    msg['Subject'] = assunto
    msg.attach(MIMEText(corpo, 'plain'))

    with open(anexo, 'rb') as f:
        part = MIMEApplication(
            f.read(),
            Name=anexo.name,
        )
    part['Content-Disposition'] = f'attachment; filename="{anexo.name}"'
    msg.attach(part)

    access_token = send_email.get_access_token(send_email.EMAIL_FROM)
    context = ssl.create_default_context()

    with smtplib.SMTP_SSL(send_email.SMTP_HOST, send_email.SMTP_PORT, context=context) as server:
        server.ehlo()
        send_email._smtp_xoauth2_login(server, send_email.EMAIL_FROM, access_token)
        server.sendmail(send_email.EMAIL_FROM, destinatario, msg.as_string())


def main() -> int:
    setup_workspace()

    parser = argparse.ArgumentParser(
        description='Gera planilha do razão de terceiros a partir de PDF Domínio.'
    )
    parser.add_argument(
        'pdf',
        nargs='?',
        default='clientes/luciano-664/Razão-terceiros-2025.pdf',
        help='Caminho do PDF do razão de terceiros',
    )
    parser.add_argument(
        '-o', '--output',
        help='Arquivo Excel de saída (padrão: mesmo diretório do PDF)',
    )
    parser.add_argument(
        '--email',
        default=EMAIL_DESTINO_PADRAO,
        help=f'E-mail destino (padrão: {EMAIL_DESTINO_PADRAO})',
    )
    parser.add_argument(
        '--sem-email',
        action='store_true',
        help='Não envia e-mail ao finalizar',
    )
    args = parser.parse_args()

    caminho_pdf = Path(args.pdf)
    if not caminho_pdf.is_absolute():
        caminho_pdf = _SCRIPTS.parent / caminho_pdf

    if not caminho_pdf.exists():
        print(f'Erro: PDF não encontrado: {caminho_pdf}')
        return 1

    if args.output:
        caminho_saida = Path(args.output)
    else:
        caminho_saida = caminho_pdf.with_name('razao-terceiros.xlsx')

    print(f'Lendo PDF: {caminho_pdf}')
    linhas = extrair_linhas_pdf(caminho_pdf)
    lancamentos = extrair_lancamentos(linhas)

    if not lancamentos:
        print('Nenhum lançamento encontrado no PDF.')
        return 1

    print(f'Lançamentos extraídos: {len(lancamentos)}')
    print(f'Total: R$ {sum(l["valor"] for l in lancamentos):,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.'))

    gerar_planilha(lancamentos, caminho_saida)
    print(f'Planilha salva: {caminho_saida}')

    if not args.sem_email:
        assunto = f'Razão Terceiros - {caminho_pdf.stem}'
        corpo = (
            f'Segue em anexo a planilha gerada a partir do razão de terceiros.\n\n'
            f'Arquivo origem: {caminho_pdf.name}\n'
            f'Lançamentos: {len(lancamentos)}\n'
            f'Gerado em: {datetime.now().strftime("%d/%m/%Y %H:%M")}\n'
        )
        print(f'Enviando e-mail para {args.email}...')
        enviar_email_com_anexo(args.email, assunto, corpo, caminho_saida)
        print('E-mail enviado com sucesso.')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
