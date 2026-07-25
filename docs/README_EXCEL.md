# Extrator de Contas Analíticas para Excel

Este script Python extrai contas analíticas de um arquivo PDF de balancete e gera uma planilha Excel com código, descrição, débito e crédito em colunas separadas.

## Funcionalidades

- Extrai texto de arquivos PDF
- Identifica contas analíticas com valores financeiros
- Gera planilha Excel formatada
- Colunas: Código, Descrição, Débito, Crédito
- Formatação monetária brasileira (R$)

## Como usar

### Sintaxe básica:
```bash
python extrair_contas_analiticas_pdf_excel.py <arquivo_pdf> <arquivo_excel_saida>
```

### Exemplos:

1. **Extrair de PDF para Excel:**
```bash
python extrair_contas_analiticas_pdf_excel.py balancete.pdf contas_analiticas.xlsx
```

2. **Usar com arquivo específico:**
```bash
python extrair_contas_analiticas_pdf_excel.py seu_balancete.pdf resultado.xlsx
```

## Formato de entrada

O script espera um arquivo PDF de balancete com o formato:
```
PRODUTOR: NOME | FAZENDA: NOME
BALANCETE DE CONTAS
...
1.1.1.1.1 - Caixa Escritório 0,00 C 1.881,80 1.881,80 0,00 -
1.1.1.2.1 - Acerto 0,00 - 90.580,24 90.580,24 0,00 -
...
```

## Formato de saída

O script gera um arquivo Excel com as colunas:
- **Código**: Código da conta (ex: 1.1.1.1.1)
- **Descrição**: Nome da conta (ex: Caixa Escritório)
- **Débito**: Valor em débito formatado (ex: R$ 1.881,80)
- **Crédito**: Valor em crédito formatado (ex: R$ 1.881,80)

## Arquivos incluídos

- `extrair_contas_analiticas_pdf_excel.py` - Script principal para PDF
- `extrair_contas_analiticas_texto_excel.py` - Versão para arquivos de texto
- `requirements.txt` - Dependências necessárias

## Requisitos

- Python 3.x
- pandas
- PyPDF2
- openpyxl

## Instalação das dependências

```bash
pip install pandas PyPDF2 openpyxl
```

ou

```bash
pip install -r requirements.txt
```

## Comando para executar

```bash
python extrair_contas_analiticas_pdf_excel.py seu_arquivo_balancete.pdf contas_analiticas.xlsx
```

## Tratamento de erros

- Se o PDF não puder ser lido, o script informará o erro
- Se nenhuma conta analítica for encontrada, salvará o texto extraído em `texto_extraido.txt` para análise
- Valores inválidos são convertidos para 0,00

## Exemplo de saída

A planilha Excel gerada terá o formato:

| Código | Descrição | Débito | Crédito |
|--------|-----------|--------|---------|
| 1.1.1.1.1 | Caixa Escritório | R$ 0,00 | R$ 1.881,80 |
| 1.1.1.2.1 | Acerto | R$ 0,00 | R$ 90.580,24 |
| 1.1.1.3.1.2.1 | Sicredi - Luciano - 12813-9 - C/C | R$ 0,00 | R$ 0,00 | 