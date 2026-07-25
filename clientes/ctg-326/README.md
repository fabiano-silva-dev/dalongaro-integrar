# CTG-326 — Classificação contábil e exportação Domínio

Solução **local e autônoma** para ler as planilhas financeiras do CTG, sugerir classificação contábil com base no plano de contas (`contas.pdf`), gerar planilha de conferência editável e exportar o arquivo no leiaute Domínio.

O projeto **FT/Integrar** foi usado apenas como referência de leitura (leiaute Domínio). Nenhum arquivo dele é alterado em tempo de execução.

## Estrutura

```text
ctg-326/
├── entrada/
│   ├── planilhas/          # planilhas originais (não alterar)
│   └── plano-contas/
│       └── contas.pdf
├── trabalho/
│   ├── extraido/           # plano-contas.json
│   ├── conferencias/       # CTG-326-classificacao.xlsx
│   └── temporarios/        # backups
├── saida/
│   ├── dominio/            # TXT Domínio
│   ├── relatorios/
│   └── pendencias/
├── configuracoes/
│   ├── configuracao.json
│   ├── regras-classificacao.json
│   └── favorecidos.json
├── scripts/
├── src/
└── tests/
```

## Dependências

Python 3.10+ com:

- `openpyxl`
- `pdfplumber`
- `pandas` / `xlrd` (opcional, para `.xls`)

Já previstas em `/ico/fabiano/ft/dalongaro-integrar/requirements.txt`.

## Fluxo

### 1) Analisar planilhas e gerar conferência

```bash
cd /ico/fabiano/ft/dalongaro-integrar/clientes/ctg-326
python scripts/analisar_planilhas.py
```

Gera:

- `trabalho/conferencias/CTG-326-classificacao.xlsx`
- `saida/pendencias/pendencias-analise-*.json`
- `saida/relatorios/analise-*.json`
- `trabalho/extraido/plano-contas.json`

### 2) Revisar a planilha

Abra `CTG-326-classificacao.xlsx` e ajuste:

- débito / crédito
- histórico contábil
- coluna `Exportar` (`SIM` / `NÃO`)
- observações

Linhas amarelas = baixa confiança. Linhas laranja = pendentes.

### 3) Validar sem exportar

```bash
python scripts/exportar_dominio.py \
  --arquivo trabalho/conferencias/CTG-326-classificacao.xlsx \
  --validar
```

### 4) Exportar Domínio

```bash
python scripts/exportar_dominio.py \
  --arquivo trabalho/conferencias/CTG-326-classificacao.xlsx
```

Arquivo gerado em `saida/dominio/CTG-326-dominio-AAAA-MM-DD-HHMMSS.txt` (ISO-8859-1 / latin-1).

Se houver linhas `Exportar=SIM` com confiança baixa, a exportação é bloqueada. Use `--forcar` somente após revisão consciente.

### 5) Reprocessar originais preservando manuais

```bash
python scripts/analisar_planilhas.py --reprocessar
```

Cria backup em `trabalho/temporarios/` e mescla pelo `ID do lançamento`.

### 6) Sugerir regras a partir de correções

```bash
python scripts/atualizar_regras.py \
  --arquivo trabalho/conferencias/CTG-326-classificacao.xlsx
```

## Leiaute Domínio (referência FT/Integrar)

TXT positional, encoding **ISO-8859-1**:

| Registro | Tamanho | Conteúdo |
|----------|---------|----------|
| 01 | 100 | cabeçalho (empresa `0000326`, CNPJ, período, tipo nota `05`) |
| 02 | 100 | lote (sequencial, data, usuário) |
| 03 | 664 | débito(7) + crédito(7) + valor centavos(15) + histórico(512) + filial(7) |
| 99 | 100 | finalizador |

Código **326** = código da empresa no Domínio (`0000326`), também usado como filial/matriz.

## Contas financeiras mapeadas

| Planilha | Conta |
|----------|-------|
| Caixa Copa / Caixa PF/PJ Campeira | `5` CAIXA |
| Sicredi Principal / Eventos | `7` SICREDI |
| Cresol Principal | `7` SICREDI *(provisório — não há conta Cresol no plano)* |

## Observações importantes

- Não inventar contas: só códigos do `contas.pdf`.
- Não exportar a partir das planilhas originais — só da conferência.
- Não sobrescrever conferência sem backup.
- Cresol e contas PF/PJ Campeira exigem revisão manual (plano sem contas dedicadas).
