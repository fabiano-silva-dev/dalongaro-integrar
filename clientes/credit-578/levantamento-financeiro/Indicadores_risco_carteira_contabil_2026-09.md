# CSG — triagem contábil de possível inadimplência

**Data da análise:** 08/11/2026. **Data-base dos saldos:** 30/09/2026.  
**Objetivo:** identificar sinais de carteira parada sem confundir ausência de movimento contábil com atraso contratual.

## Síntese para a administração

A conta **1.1.2 — carteira de créditos** do balancete em 30/09/2026 soma **R$ 6.801.908,85**. Desse valor:

- **R$ 5.107.111,11** aparecem em contas nominativas (classificação `1.1.2.01.001`).
- **R$ 1.694.797,74** estão na conta de controle `1435 — DIREITOS CREDITÓRIOS` (`1.1.2.02.001`), sem abertura nominal suficiente para analisar inadimplência por devedor.

Nos **1.118 registros de contas nominativas** do comparativo do razão 2026, há **944 contas com saldo devedor positivo**, somando **R$ 5.107.111,11**. Outras 174 contas terminam com saldo zero. A leitura refere-se a registros de contas, não a contratos/CPF únicos.

**Sinal principal de risco:** **195 contas nominativas, totalizando R$ 1.611.642,59, tinham saldo inicial positivo em 2026 e não registraram nem débitos nem créditos entre 01/01/2026 e 30/09/2026.** O valor corresponde a **23,69% da carteira total** e **31,56% da carteira nominativa**. São saldos contábeis persistentes — não valores confirmados em atraso.

Cruzamento dessas 195 contas com a data da última movimentação no índice do razão 2025:

- **107 contas / R$ 1.206.682,34** tiveram sua última movimentação em setembro/2025 ou antes, sem qualquer lançamento em 2026.
- **62 contas / R$ 569.014,93** tiveram sua última movimentação em junho/2025 ou antes, sem qualquer lançamento em 2026. **São subconjunto das 107, não somar novamente.**
- **71 contas / R$ 438.456,79** não tiveram lançamentos de crédito em 2025 e continuaram sem movimentação em 2026. Esse é outro recorte sobreposto, não somar aos anteriores.
- Entre os saldos parados, as contas contábeis **1343** (R$ 383.908,73; última movimentação registrada em 31/07/2025) e **1589** (R$ 179.065,67; última movimentação em 05/06/2025) merecem reconciliação específica. A identificação contábil não é uma afirmação de inadimplência do respectivo devedor.

Outro indicador, **menos seletivo**, é a ausência de **crédito contábil em 2026** em **317 contas nominativas com saldo**, totalizando **R$ 2.280.113,38**. Esse conjunto inclui os 195 casos parados e também créditos originados/registrados em 2026, para os quais a ausência de baixa pode ser normal. Não deve ser classificado como inadimplência sem o cronograma.

## Método, fontes e cautelas

- Fontes indexadas: `balancetes/Razão2025.xls` e `balancetes/Razão2026.xls`; arquivos de conciliação `razoes-anuais/conciliacao.json` e `razoes-anuais/catalogo.json`.
- Seleção: ano 2026; classificação exata `1.1.2.01.001`; saldo inicial maior que zero; saldo final maior que zero; ausência de débitos e créditos em 2026. O somatório é sobre as contas do razão/balancete reconciliadas, não sobre o total de partidas contábeis.
- Comparação histórica: por **código contábil** e último evento de 2025. Validar se os códigos e a titularidade foram preservados; as fontes analisadas não demonstram individualmente o vencimento de cada parcela.
- Movimentos da conta de devedor podem incluir aquisição, amortização, renegociação, estorno ou ajuste. **Crédito contábil não prova recebimento bancário**, e ausência de crédito não prova mora ou incobrabilidade.
- Não se calculou perda esperada nem provisão, e nenhum valor foi baixado ou ajustado. Em créditos com vencimento único posterior a setembro/2026, uma conta parada pode estar regular.
- O grupo `1.1.2.02.001` exige memória de composição; **R$ 1.694.797,74 não são automaticamente créditos problemáticos**.

## Conclusão

**Há sinais contábeis objetivos de carteira potencialmente atrasada ou sem evolução**, especialmente R$ 1.206.682,34 sem lançamentos por aproximadamente 12 meses ou mais. **Ainda não há prova de inadimplência contratual nem taxa de recuperação quantificável.** O saldo total do ativo pode estar superavaliado caso parte dos créditos não seja recuperável; não seria tecnicamente correto afirmar a perda sem evidências.

## Próximo cruzamento obrigatório

Pedir à gestora/originadora/controladora da carteira a **posição de todas as parcelas em 30/09/2026**, com: contrato, devedor, data de aquisição, valor de face, valor de aquisição, vencimento original e renegociado, principal/juros, pagamentos e baixas, saldo aberto, dias de atraso, motivo da baixa, garantia, cobrança e recuperação. Conciliar os créditos às contas nominativas e a composição da conta 1435, destacando as 195 contas sem movimentação. A partir disso, classificar a vencer, vencido até 30/90 dias, inadimplente, renegociado e perda esperada, de acordo com critérios e documentação sustentados.

**Não somar os recortes de risco entre si. Não reapurar o passivo por essa triagem.** A reconciliação bancária foi informada como concluída pelo escritório.

## Reprodutibilidade

Fonte principal de saldos: `razoes-anuais/conciliacao.json` (detalhes filtrados por 2026 e classificação `1.1.2.01.001`). Data da última movimentação: `razoes-anuais/catalogo.json` (campo `por_conta[].data_final` em ano 2025). Para linha nominativa não movimentada em 2026, os totais `opening`, `debit`, `credit`, `balance` estão em centavos. Para risco forte, exigir `opening>0`, `balance>0`, `debit=0`, `credit=0`. A diferença de 2026 na conta patrimonial 267 **não integra** as contas da carteira analisada.
