#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para converter extrato PDF do Sicredi para formato OFX
"""

import sys
import os
import re
import argparse
from datetime import datetime
from pathlib import Path

try:
    import PyPDF2
except ImportError:
    print("PyPDF2 não encontrado. Instalando...")
    os.system("pip install PyPDF2")
    import PyPDF2


def extrair_texto_pdf(caminho_pdf):
    """
    Extrai texto de um arquivo PDF do Sicredi
    """
    try:
        with open(caminho_pdf, 'rb') as arquivo:
            leitor_pdf = PyPDF2.PdfReader(arquivo)
            texto_completo = ""
            
            for pagina in leitor_pdf.pages:
                texto_pagina = pagina.extract_text()
                if texto_pagina:
                    texto_completo += texto_pagina + "\n"
                    
            return texto_completo
            
    except FileNotFoundError:
        print(f"Erro: Arquivo '{caminho_pdf}' não encontrado.")
        return None
    except Exception as e:
        print(f"Erro ao processar o PDF: {e}")
        return None


def extrair_info_conta(texto):
    """
    Extrai informações da conta do extrato
    """
    info = {
        'banco': 'SICREDI',
        'banco_id': '748',
        'conta': '',
        'nome': '',
        'periodo_inicio': '',
        'periodo_fim': ''
    }
    
    # Extrair número da conta (formato: 000087685-2)
    match_conta = re.search(r'(\d{9}-\d)', texto)
    if match_conta:
        info['conta'] = match_conta.group(1).replace('-', '')
    
    # Extrair nome do cliente
    linhas = texto.split('\n')
    for i, linha in enumerate(linhas):
        if 'EXTRATO DE CONTA CORRENTE' in linha:
            # O nome geralmente está na próxima linha ou algumas linhas depois
            for j in range(i+1, min(i+5, len(linhas))):
                if linhas[j].strip() and not linhas[j].strip().startswith('R.'):
                    nome_match = re.match(r'^([A-ZÀ-Ú\s\.]+(?:LTDA|ME|CIA|S\.A\.)?)', linhas[j].strip())
                    if nome_match:
                        info['nome'] = nome_match.group(1).strip()
                        break
    
    # Extrair período
    match_periodo = re.search(r'PERIODO:\s*DE\s*(\d{2}/\d{4})\s*A\s*(\d{2}/\d{4})', texto)
    if match_periodo:
        mes_inicio, ano_inicio = match_periodo.group(1).split('/')
        mes_fim, ano_fim = match_periodo.group(2).split('/')
        info['periodo_inicio'] = f"{ano_inicio}{mes_inicio}01"
        # Último dia do mês fim
        ultimo_dia = 28 if mes_fim == '02' else 30 if mes_fim in ['04', '06', '09', '11'] else 31
        info['periodo_fim'] = f"{ano_fim}{mes_fim}{ultimo_dia}"
    
    return info


def parsear_valor(valor_str):
    """
    Converte valor no formato brasileiro (1.234,56) para float
    """
    if not valor_str or valor_str.strip() == '':
        return 0.0
    
    # Remove espaços e caracteres não numéricos exceto vírgula e ponto
    valor_str = valor_str.strip()
    valor_str = re.sub(r'[^\d,.]', '', valor_str)
    
    if not valor_str:
        return 0.0
    
    # Converte formato brasileiro para float
    valor_str = valor_str.replace('.', '').replace(',', '.')
    
    try:
        return float(valor_str)
    except ValueError:
        return 0.0


def extrair_transacoes(texto):
    """
    Extrai transações do texto do extrato
    """
    transacoes = []
    
    # Padrão para linhas de transação
    # DATA | DOCUMENTO | HISTORICO | DEBITO | CREDITO | SALDO
    # Exemplo: 02/01/2025 |  | LIQUIDACAO BOLETO 32048808000135 SULPARTS COMERC | 415,00 |  |
    
    linhas = texto.split('\n')
    
    # Padrão regex para capturar transações
    # Data no formato DD/MM/YYYY
    padrao_data = r'^(\d{2}/\d{2}/\d{4})'
    
    id_contador = 1
    
    for linha in linhas:
        linha = linha.strip()
        
        # Verificar se a linha começa com uma data
        match_data = re.match(padrao_data, linha)
        if not match_data:
            continue
        
        data_str = match_data.group(1)
        resto = linha[len(data_str):].strip()
        
        # Ignorar linhas de saldo anterior/atual
        if 'SALDO ANTERIOR' in resto or 'SALDO ATUAL' in resto:
            continue
        if 'DE TRANSPORTE' in resto:
            continue
        
        # Tentar extrair valores de débito e crédito
        # Os valores geralmente estão no final da linha no formato brasileiro
        
        # Padrão: procurar valores no formato 1.234,56 ou 123,45
        valores = re.findall(r'[\d.,]+,\d{2}(?:\s|$)', resto)
        
        debito = 0.0
        credito = 0.0
        historico = resto
        documento = ''
        
        # Extrair documento (código alfanumérico após a data)
        match_doc = re.match(r'^([A-Z0-9_-]+)\s+', resto)
        if match_doc:
            doc_candidato = match_doc.group(1)
            # Verificar se não é parte do histórico
            if len(doc_candidato) <= 15 and doc_candidato not in ['LIQUIDACAO', 'PAGAMENTO', 'RECEBIMENTO', 'DEBITO', 'CREDITO']:
                documento = doc_candidato
                historico = resto[len(doc_candidato):].strip()
        
        # Processar valores encontrados
        if valores:
            # Tentar identificar débito vs crédito baseado na posição ou contexto
            historico_upper = historico.upper()
            
            # Palavras que indicam crédito (entrada)
            palavras_credito = ['RECEBIMENTO', 'CREDITO', 'LIQ.COBRANCA', 'DEP CHEQUE', 'DEPOSITO', 'LIBERACAO']
            # Palavras que indicam débito (saída)
            palavras_debito = ['LIQUIDACAO BOLETO', 'PAGAMENTO', 'FAGAMENTO', 'DEB.', 'DEBITO', 'CESTA', 'ARRECADACAO', 'TED', 'FOLHA']
            
            eh_credito = any(palavra in historico_upper for palavra in palavras_credito)
            eh_debito = any(palavra in historico_upper for palavra in palavras_debito)
            
            # Pegar o primeiro valor significativo
            for valor_str in valores:
                valor = parsear_valor(valor_str)
                if valor > 0:
                    if eh_credito and not eh_debito:
                        credito = valor
                    else:
                        debito = valor
                    break
            
            # Remover valores do histórico
            for valor_str in valores:
                historico = historico.replace(valor_str, '').strip()
        
        # Limpar histórico
        historico = re.sub(r'\s+', ' ', historico).strip()
        historico = historico.rstrip('|').strip()
        
        # Só adicionar se tiver algum valor
        if debito > 0 or credito > 0:
            transacao = {
                'data': data_str,
                'documento': documento,
                'historico': historico[:80] if len(historico) > 80 else historico,  # Limitar tamanho
                'debito': debito,
                'credito': credito,
                'id': f"{id_contador:010d}"
            }
            transacoes.append(transacao)
            id_contador += 1
    
    return transacoes


def gerar_ofx(info_conta, transacoes, arquivo_saida):
    """
    Gera arquivo OFX a partir das transações extraídas
    """
    agora = datetime.now()
    timestamp = agora.strftime("%Y%m%d%H%M%S")
    
    # Header OFX
    ofx = """OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:NONE
ENCODING:USASCII
CHARSET:1252
COMPRESSION:NONE
OLDFILEUID:NONE
NEWFILEUID:NONE

<OFX>
<SIGNONMSGSRSV1>
<SONRS>
<STATUS>
<CODE>0</CODE>
<SEVERITY>INFO</SEVERITY>
</STATUS>
<DTSERVER>{timestamp}[-3:GMT]</DTSERVER>
<LANGUAGE>POR</LANGUAGE>
<FI>
<ORG>{banco}</ORG>
<FID>{banco}</FID>
</FI>
</SONRS>
</SIGNONMSGSRSV1>
<BANKMSGSRSV1>
<STMTTRNRS>
<TRNUID>1</TRNUID>
<STATUS>
<CODE>0</CODE>
<SEVERITY>INFO</SEVERITY>
</STATUS>
<STMTRS>
<CURDEF>BRL</CURDEF>
<BANKACCTFROM>
<BANKID>{banco_id}</BANKID>
<ACCTID>{conta}</ACCTID>
<ACCTTYPE>CHECKING</ACCTTYPE>
</BANKACCTFROM>
<BANKTRANLIST>
<DTSTART>{periodo_inicio}000000[-3:GMT]</DTSTART>
<DTEND>{periodo_fim}000000[-3:GMT]</DTEND>
""".format(
        timestamp=timestamp,
        banco=info_conta['banco'],
        banco_id=info_conta['banco_id'],
        conta=info_conta['conta'],
        periodo_inicio=info_conta['periodo_inicio'],
        periodo_fim=info_conta['periodo_fim']
    )
    
    # Adicionar transações
    for trans in transacoes:
        # Converter data DD/MM/YYYY para YYYYMMDD
        data_parts = trans['data'].split('/')
        data_ofx = f"{data_parts[2]}{data_parts[1]}{data_parts[0]}"
        
        # Determinar tipo e valor
        if trans['credito'] > 0:
            tipo = 'CREDIT'
            valor = trans['credito']
        else:
            tipo = 'DEBIT'
            valor = -trans['debito']  # Débito é negativo no OFX
        
        # Limpar histórico para ASCII
        historico = trans['historico']
        historico = historico.replace('&', 'E')
        historico = re.sub(r'[<>]', '', historico)
        
        ofx += """<STMTTRN>
<TRNTYPE>{tipo}</TRNTYPE>
<DTPOSTED>{data}000000[-3:GMT]</DTPOSTED>
<TRNAMT>{valor:.2f}</TRNAMT>
<FITID>{id}</FITID>
<REFNUM>{id}</REFNUM>
<MEMO>{historico}</MEMO>
</STMTTRN>
""".format(
            tipo=tipo,
            data=data_ofx,
            valor=valor,
            id=trans['id'],
            historico=historico
        )
    
    # Calcular saldo final
    saldo_final = sum(t['credito'] - t['debito'] for t in transacoes)
    
    # Footer OFX
    ofx += """</BANKTRANLIST>
<LEDGERBAL>
<BALAMT>{saldo:.2f}</BALAMT>
<DTASOF>{data_saldo}000000</DTASOF>
</LEDGERBAL>
</STMTRS>
</STMTTRNRS>
</BANKMSGSRSV1>
</OFX>
""".format(
        saldo=saldo_final,
        data_saldo=info_conta['periodo_fim']
    )
    
    # Salvar arquivo
    with open(arquivo_saida, 'w', encoding='utf-8') as f:
        f.write(ofx)
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description='Converte extrato PDF do Sicredi para formato OFX'
    )
    parser.add_argument(
        'pdf',
        help='Caminho do arquivo PDF do extrato Sicredi'
    )
    parser.add_argument(
        '-o', '--output',
        help='Caminho do arquivo OFX de saída (opcional, usa mesmo nome do PDF com .ofx)',
        default=None
    )
    parser.add_argument(
        '-d', '--debug',
        action='store_true',
        help='Mostra informações de debug'
    )
    
    args = parser.parse_args()
    
    # Verificar se arquivo existe
    if not os.path.exists(args.pdf):
        print(f"❌ Erro: Arquivo '{args.pdf}' não encontrado.")
        sys.exit(1)
    
    # Definir arquivo de saída
    if args.output:
        arquivo_saida = args.output
    else:
        arquivo_saida = Path(args.pdf).stem + '.ofx'
    
    print(f"📄 Processando: {args.pdf}")
    
    # Extrair texto do PDF
    texto = extrair_texto_pdf(args.pdf)
    if not texto:
        print("❌ Erro ao extrair texto do PDF.")
        sys.exit(1)
    
    if args.debug:
        print("\n=== TEXTO EXTRAÍDO (primeiros 2000 chars) ===")
        print(texto[:2000])
        print("\n" + "="*50)
    
    # Extrair informações da conta
    info_conta = extrair_info_conta(texto)
    print(f"🏦 Banco: {info_conta['banco']}")
    print(f"📋 Conta: {info_conta['conta']}")
    print(f"👤 Nome: {info_conta['nome']}")
    print(f"📅 Período: {info_conta['periodo_inicio']} a {info_conta['periodo_fim']}")
    
    # Extrair transações
    transacoes = extrair_transacoes(texto)
    print(f"💳 Transações encontradas: {len(transacoes)}")
    
    if args.debug and transacoes:
        print("\n=== PRIMEIRAS 5 TRANSAÇÕES ===")
        for t in transacoes[:5]:
            print(f"  {t['data']} | D:{t['debito']:.2f} | C:{t['credito']:.2f} | {t['historico'][:50]}")
        print("="*50)
    
    if not transacoes:
        print("⚠️  Nenhuma transação encontrada no PDF.")
        print("    Verifique se o PDF está no formato correto do Sicredi.")
        sys.exit(1)
    
    # Gerar OFX
    if gerar_ofx(info_conta, transacoes, arquivo_saida):
        print(f"✅ Arquivo OFX gerado: {arquivo_saida}")
        
        # Estatísticas
        total_debitos = sum(t['debito'] for t in transacoes)
        total_creditos = sum(t['credito'] for t in transacoes)
        print(f"\n📊 Resumo:")
        print(f"   Total de débitos:  R$ {total_debitos:,.2f}")
        print(f"   Total de créditos: R$ {total_creditos:,.2f}")
        print(f"   Saldo período:     R$ {total_creditos - total_debitos:,.2f}")
    else:
        print("❌ Erro ao gerar arquivo OFX.")
        sys.exit(1)


if __name__ == "__main__":
    main()

