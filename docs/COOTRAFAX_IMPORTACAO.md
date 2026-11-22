# COOTRAFAX — preparação de lançamentos contábeis (Domínio)

## Origem dos dados

Arquivos mensais **Relatório de Contrato de Frete Emitido**, em subpastas PF e PJ, com nomes MMAAAA.pdf. Foram estudados os relatórios de janeiro a outubro de 2026 e as imagens de lançamentos manuais do Domínio.

Os prints indicam:
- PF: débito reduzido **213** (3.1.02.01.02.001), FRETE AUT. COOPERADO PF.
- PJ: débito reduzido **214** (3.1.02.01.02.002), FRETES COOP PJ.
- Histórico: **190**.
- Crédito: **conta individual de cada cooperado** no Domínio. Os exemplos dos prints (664 para Evandro Alberto e 1181 para Alechandre Belle Barbieri & Cia. Ltda.) não determinam automaticamente contas de outros cooperados.

O relatório distingue **Vl. Frete**, **Vl. Doc.**, **Vl. Total** e datas de emissão e quitação. É obrigatório definir com a contabilidade qual valor e qual data utilizar. Não presumir natureza tributária das diferenças.

## Preparação

Organize PDFs, por exemplo:

```
clientes/cootrafax/2026-01/origem/PF/012026.pdf
clientes/cootrafax/2026-01/origem/PJ/012026.pdf
```

Crie um CSV `clientes/cootrafax/contas_cooperados.csv`:

```csv
tipo;codigo_cooperado;conta_credito
PF;2323;
PJ;5004;
```

Preencha `conta_credito` com a **conta reduzida verificada no plano de contas Domínio**, nunca por similaridade de nome. Exemplos acima estão em branco intencionalmente.

## Executar na raiz do repositório

Primeira passagem: extração e relatório de pendências, sem liberar lançamentos:

```bash
python scripts/contabil/cootrafax/gerar_lancamentos.py clientes/cootrafax/2026-01/origem --contas clientes/cootrafax/contas_cooperados.csv --saida clientes/cootrafax/2026-01/saida
```

Depois de validar base e data, por exemplo, **somente se aprovado**:

```bash
python scripts/contabil/cootrafax/gerar_lancamentos.py clientes/cootrafax/2026-01/origem --contas clientes/cootrafax/contas_cooperados.csv --saida clientes/cootrafax/2026-01/saida --base-valor documento --data-contabil emissao
```

As opções `documento` e `emissao` são exemplos operacionais, **não regras já aprovadas**.

## Arquivos gerados

- `movimentos_extraidos.csv`: cada contrato com número, cooperado, data, valores distintos, arquivo de origem e página.
- `pendencias.csv`: cooperados sem conta; data/valor inválido.
- `validacao.txt`: totais extraídos, erros de leitura, subtotais divergentes e contratos repetidos.
- `lancamentos_conferencia.csv`: somente gerado **se todos os registros tiverem conta e todas as verificações passarem**. É um CSV de conferência, **não** um arquivo de importação homologado.

Falhas de subtotal ou duplicidades bloqueiam a liberação; não há lançamento parcial silencioso.

## Para homologar a importação definitiva

1. Exportar plano de contas do Domínio para preencher contas reduzidas por cooperado.
2. Validar escolha do valor (frete/documento/total) e a data contábil.
3. Avaliar contratos repetidos/parcelados, sem eliminar dados silenciosamente.
4. Obter arquivo-modelo do **leiaute oficial de importação dos lançamentos no Domínio**.
5. Testar importação em empresa de homologação, conferir débitos/créditos por mês e só então implementar o gerador TXT de produção.

**Nenhum arquivo deve ser importado na contabilidade sem as validações acima.**
