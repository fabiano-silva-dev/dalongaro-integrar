#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gera CSV a partir da listagem analítica de terceiros (Cadastro+Endereço).
Funciona mesmo quando openpyxl falha por erro no stylesheet do Excel.
"""

import zipfile
import xml.etree.ElementTree as ET
import re
import os
import argparse
import csv


def col_ref_to_index(ref):
    """Converte referência de coluna (A, B, ..., Z, AA, ...) para índice."""
    result = 0
    for char in ref.upper():
        result = result * 26 + (ord(char) - ord('A') + 1)
    return result - 1


def parse_cell_ref(ref):
    """Extrai (row, col) de referência como 'C2', 'AA10'."""
    match = re.match(r'^([A-Z]+)(\d+)$', ref.upper())
    if not match:
        return None, None
    col_str, row_str = match.groups()
    col = col_ref_to_index(col_str)
    row = int(row_str)
    return row, col


def _elem_text(elem):
    """Extrai todo o texto de um elemento XML."""
    t = elem.text or ''
    for c in elem:
        t += _elem_text(c)
    t += elem.tail or ''
    return t


def read_shared_strings(zip_file):
    """Lê shared strings do arquivo xlsx."""
    try:
        with zip_file.open('xl/sharedStrings.xml') as f:
            tree = ET.parse(f)
            root = tree.getroot()
            ns = {'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
            return [_elem_text(si) for si in root.findall('.//main:si', ns)]
    except KeyError:
        return []


def read_sheet_data(zip_file, sheet_path='xl/worksheets/Sheet1.xml'):
    """Lê dados da planilha como matriz (row, col) -> valor."""
    with zip_file.open(sheet_path) as f:
        tree = ET.parse(f)
        root = tree.getroot()
        ns = {'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        sheet_data = root.find('main:sheetData', ns)
        if sheet_data is None:
            return {}, 0, 0

        cells = {}
        max_row = 0
        max_col = 0
        for row_elem in sheet_data.findall('main:row', ns):
            row_num = int(row_elem.get('r', 0))
            max_row = max(max_row, row_num)
            for c in row_elem.findall('main:c', ns):
                ref = c.get('r')
                if not ref:
                    continue
                r, col = parse_cell_ref(ref)
                if r is None:
                    continue
                max_col = max(max_col, col)
                v_elem = c.find('main:v', ns)
                cell_type = c.get('t')
                value = None
                if v_elem is not None and v_elem.text is not None:
                    if cell_type == 's':
                        # Shared string - índice
                        idx = int(v_elem.text)
                        cells[(r, col)] = ('s', idx)
                    else:
                        cells[(r, col)] = ('n', v_elem.text)
        return cells, max_row, max_col


def get_workbook_sheets(zip_file):
    """Retorna mapeamento sheet_id -> path do arquivo XML."""
    with zip_file.open('xl/workbook.xml') as f:
        tree = ET.parse(f)
        root = tree.getroot()
        ns = {'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        sheets = root.find('main:sheets', ns)
        if sheets is None:
            return {}

    with zip_file.open('xl/_rels/workbook.xml.rels') as f:
        tree = ET.parse(f)
        root = tree.getroot()
        rels = {}
        for rel in root:
            r_id = rel.get('{http://www.w3.org/1999/xlink}id') or rel.get('Id')
            target = rel.get('{http://www.w3.org/1999/xlink}href') or rel.get('Target')
            if r_id and target:
                rels[r_id] = 'xl/' + target.replace('../', '')
        return rels


# Labels das colunas do CSV de saída (layout Domínio/ERP)
LABELS_CSV = [
    'Codigo', 'Nome', 'Razão Social', 'CNPJ', 'CPF', 'Tipo', 'ID Estrangeiro',
    'Data Criacao', 'Observações', 'Status', 'Inscrição Estadual', 'eMail principal',
    'Telefone principal', 'Celular', 'Aniversário', 'CEP', 'Estado', 'Cidade',
    'Endereço', 'Número', 'Bairro', 'Complemento', 'Nome Contato', 'eMail Contato',
    'Exporta mSac', 'Vendedor', 'Limite Credito'
]

# Mapeamento: Excel (linha_cadastro, col) e (linha_endereco, col) -> label
# Cadastro: B=1 Código, D=3 Nome/Razão, E=4 ST, F=5 Tipo, G=6 Contato, H=7 Tel1, J=9 Tel2,
#           L=11 CPF/CNPJ, N=13 Insc.Estadual, Q=16 Email
# Endereço: D=3 Endereço, E=4 Número, G=6 Complemento, J=9 Bairro, N=13 Cidade, R=17 UF, T=19 CEP
MAP_CADASTRO = {
    1: 'Codigo', 3: 'Razão Social', 4: 'Status', 5: 'Tipo', 6: 'Nome Contato',
    7: 'Telefone principal', 9: 'Celular', 11: '_cpf_cnpj', 13: 'Inscrição Estadual', 16: 'eMail principal'
}
MAP_ENDERECO = {
    3: 'Endereço', 4: 'Número', 6: 'Complemento', 9: 'Bairro', 13: 'Cidade', 17: 'Estado', 19: 'CEP'
}


def _digitos(s):
    """Retorna apenas dígitos."""
    return re.sub(r'[^\d]', '', str(s)) if s else ''


def xlsx_to_dataframe(xlsx_path, sheet_name=None):
    """
    Lê arquivo xlsx via XML (sem openpyxl).
    Agrupa cadastro + endereço em um registro por cliente.
    Retorna lista de dicts com os labels LABELS_CSV.
    """
    all_data = []

    with zipfile.ZipFile(xlsx_path, 'r') as zf:
        shared_strings = read_shared_strings(zf)
        cells, max_row, max_col = read_sheet_data(zf)

        def get_value(r, c):
            key = (r, c)
            if key not in cells:
                return ''
            t, v = cells[key]
            if t == 's':
                idx = int(v)
                return shared_strings[idx] if idx < len(shared_strings) else ''
            return str(v) if v else ''

        # Encontrar início dos dados (após cabeçalhos)
        header_row = None
        for r in range(1, min(15, max_row + 1)):
            filled = sum(1 for c in range(max_col + 1) if get_value(r, c))
            if filled >= 3:
                header_row = r
                break
        header_row = header_row or 1
        data_start = header_row + 2

        # Processar pares cadastro+endereço (cadastro não tem Código na linha seguinte)
        r = data_start
        while r <= max_row:
            cadastro = {}
            for col, label in MAP_CADASTRO.items():
                val = get_value(r, col).strip()
                if label == '_cpf_cnpj':
                    digits = _digitos(val)
                    if len(digits) == 11:
                        cadastro['CPF'] = val
                        cadastro['CNPJ'] = ''
                    elif len(digits) == 14:
                        cadastro['CPF'] = ''
                        cadastro['CNPJ'] = val
                    else:
                        cadastro['CPF'] = val if digits else ''
                        cadastro['CNPJ'] = ''
                elif val:
                    cadastro[label] = val

            # Linha seguinte é endereço somente se NÃO for outro cadastro (sem Código em B)
            endereco = {}
            tem_endereco = False
            if r + 1 <= max_row and not get_value(r + 1, 1).strip():
                for col, label in MAP_ENDERECO.items():
                    val = get_value(r + 1, col).strip()
                    if val:
                        endereco[label] = val
                        tem_endereco = True

            # Se linha atual tem Código ou Nome/Razão, é um cadastro válido
            if cadastro.get('Codigo') or cadastro.get('Razão Social'):
                row_out = {label: '' for label in LABELS_CSV}
                row_out.update(cadastro)
                row_out.update(endereco)
                # Nome = Razão Social quando for PF (tem CPF)
                if row_out.get('Razão Social') and row_out.get('CPF'):
                    row_out['Nome'] = row_out['Razão Social']
                all_data.append(row_out)
                r += 2 if tem_endereco else 1
            else:
                r += 1

    return LABELS_CSV, all_data


def main():
    parser = argparse.ArgumentParser(
        description='Gera CSV da listagem de terceiros (Cadastro+Endereço)'
    )
    parser.add_argument(
        'arquivo',
        nargs='?',
        default='/home/fabiano/Downloads/4. Listagem Analítica III Terceiros (Cadastro+Endereço).xlsx',
        help='Caminho do arquivo Excel .xlsx'
    )
    parser.add_argument(
        '-o', '--output',
        help='Arquivo CSV de saída (padrão: mesmo nome do arquivo com extensão .csv)'
    )
    parser.add_argument(
        '--sep',
        default=';',
        help='Separador do CSV (padrão: ;)'
    )
    parser.add_argument(
        '-e', '--encoding',
        default='iso-8859-1',
        help='Encoding do CSV (padrão: iso-8859-1)'
    )
    args = parser.parse_args()

    xlsx_path = os.path.abspath(args.arquivo)
    if not os.path.exists(xlsx_path):
        print(f"Erro: Arquivo não encontrado: {xlsx_path}")
        return 1

    if args.output:
        csv_path = os.path.abspath(args.output)
    else:
        # Salva no diretório atual para evitar problemas de permissão
        base = os.path.splitext(os.path.basename(xlsx_path))[0]
        csv_path = os.path.join(os.getcwd(), base + '.csv')

    print(f"Lendo: {xlsx_path}")
    headers, rows = xlsx_to_dataframe(xlsx_path)

    if not rows:
        print("Nenhum dado encontrado na planilha.")
        return 1

    print(f"Colunas: {len(headers)}")
    print(f"Registros: {len(rows)}")

    with open(csv_path, 'w', newline='', encoding=args.encoding, errors='replace') as f:
        writer = csv.DictWriter(f, fieldnames=headers, delimiter=args.sep)
        writer.writeheader()
        writer.writerows(rows)

    print(f"CSV salvo: {csv_path}")
    return 0


if __name__ == '__main__':
    exit(main())
