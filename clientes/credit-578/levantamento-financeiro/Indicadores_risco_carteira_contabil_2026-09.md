# CSG — Limitação na conciliação individual da carteira de créditos (retificação)

**Data da retificação:** 08/11/2026  
**Data-base dos demonstrativos:** 30/09/2026  
**Status da análise:** DESCRITIVA, NÃO UTILIZÁVEL PARA CONCLUIR INADIMPLÊNCIA

> **Correção metodológica importante.** O escritório esclareceu que **não existe fechamento confiável do saldo individual de cada devedor/contrato**. Em alguns recebimentos, o pagamento é realizado por terceiro ou aparece na conta de outra pessoa, sem identificação que permita vincular com segurança a parcela quitada. Assim, a ausência de baixa em uma conta de devedor não demonstra que a dívida continue em aberto, esteja vencida ou seja irrecuperável. A versão inicial deste documento, que tratava a imobilidade das contas como forte indício de inadimplência, deve ser desconsiderada nessa interpretação.

## 1. O que a contabilidade efetivamente demonstra

- Conta **1.1.2 — carteira de créditos**: **R$ 6.801.908,85**, em 30/09/2026.
- Contas nominativas de devedores (1.1.2.01.001): **R$ 5.107.111,11**.
- Direitos creditórios em conta sem detalhamento individual suficiente (1.1.2.02.001, conta 1435): **R$ 1.694.797,74**.
- A soma dos saldos analíticos concilia com o balancete contábil. **Isso não é conciliação de contratos, parcelas, liquidações ou pagamentos de terceiros**.
- O passivo contábil é tratado provisoriamente como referência de trabalho, conforme avaliação do escritório; a verificação contratual pontual dos credores permanece possível.

A pergunta **“quanto do ativo é efetivamente devido pelos clientes?”** continua **SEM RESPOSTA CONFIÁVEL** com os dados disponíveis. A taxa de inadimplência, os dias de atraso e a estimativa de perda **não podem ser inferidos dos saldos por conta contábil**, sem um vínculo verificável entre títulos emitidos e recebimentos/baixas.

## 2. Estatísticas contábeis — somente diagnóstico da qualidade da escrituração

No razão de 2026, as contas nominativas com saldo inicial e final positivo mas sem débitos nem créditos de janeiro a setembro são **195**, somando **R$ 1.611.642,59**. Entre elas, considerando somente a última data de movimento da mesma conta no razão de 2025:

- **107 contas**, R$ **1.206.682,34**, com último movimento até setembro de 2025;
- **62 contas**, R$ **569.014,93**, com último movimento até junho de 2025; essas 62 são subconjunto das 107.

Em **317 contas nominativas** com saldo positivo, totalizando **R$ 2.280.113,38**, não houve lançamentos de crédito em 2026.

**Esses números são indicadores de contas sem baixa contábil identificável; NÃO são valores de créditos vencidos, inadimplentes, de difícil recuperação ou ainda efetivamente devidos.** Os recortes se sobrepõem e não devem ser somados. Pagamentos podem ter ingressado em banco ou sido registrados em outras contas, e nem crédito em conta devedor é prova suficiente de recebimento bancário efetivo.

**Não apresentar R$ 1,61 milhão, R$ 1,21 milhão, R$ 569 mil ou R$ 2,28 milhões como inadimplência, exposição com risco de crédito ou provável perda.** Também não transformar esses indicadores automaticamente em ajustes do ativo.

## 3. Conclusão comprovada: os recebimentos bancários são creditados diretamente na conta 1435

O cruzamento integral dos razões `Razão2025.xls` e `Razão2026.xls` comprovou que a conta `1435 — DIREITOS CREDITORIOS` (`1.1.2.02.001`) é usada como contrapartida de recebimentos registrados em bancos. Os pares foram conferidos por **data, lote, valor e código de contrapartida**, com referência às linhas originais de ambos os lados. A trilha gerada está em `auditoria_quitacoes_1435.md` e `auditoria_quitacoes_1435.json`.

**2025:**
- Créditos contábeis na 1435: **R$ 1.933.943,09**, em **3.073 linhas positivas**.
- Correspondências a débito de contas bancárias, por mesmo dia/lote/valor: **R$ 1.879.572,77**, em **3.015 pares**.
- Desses pares, ao menos **2.996 débitos bancários**, totalizando **R$ 1.827.389,34**, apresentam a conta **1435 como contrapartida explícita** no lado do banco.
- **3 linhas / R$ 12.109,16** têm conta bancária explícita como contrapartida na 1435, mas não foram pareadas pelo valor exato; **55 linhas / R$ 42.261,16** não obtiveram vínculo bancário direto pelo critério estrito. Isso **não prova ausência de recebimento**: pode haver lançamento composto, reclassificação, compensação ou diferença temporal.
- Em 2025 também aparece a conta `2012 — BANCO DO BRASIL CONTA TRANSITÓRIA`, R$ 48.952,63 de entrada e saída, sem saldo final; não confundir sua movimentação com a origem principal das baixas da 1435.

**Janeiro-setembro de 2026:**
- Créditos contábeis na 1435: **R$ 632.382,09**, em **973 linhas**.
- Pares banco / conta 1435 conferidos: **972 linhas / R$ 625.166,24**. Dessas, **971 / R$ 624.446,24** têm como contrapartida a conta 15 (Banco do Brasil Filial) e **1 / R$ 720,00** a conta 11 (Banco do Brasil Matriz).
- **Uma linha de R$ 7.215,85** corresponde a reclassificação interna para a conta `1502 — SAULO DA SILVA PINHEIRO`, no lote 32130 de 02/01/2026, com histórico de ajuste de saldos anteriores, **não é recebimento bancário**.
- Exemplo de par: **02/01/2026, lote 24711, R$ 198,76**, com histórico de recebimento via PIX; débito em banco 15 na linha 66 e crédito em direitos creditórios 1435 na linha 28123 do razão anual de 2026.

**Total dos pares bancários identificados de 2025 a setembro de 2026: R$ 2.504.739,01.** Este é volume histórico de recebimentos com correspondência contábil nos dois lados, **não saldo atual a receber**.

**Consequência gerencial decisiva:** o dinheiro pode ser registrado diretamente no banco com contrapartida na carteira genérica 1435, sem que a própria partida contábil contenha baixa em conta nominal do devedor. A falta de baixa em conta individual, portanto, **não comprova inadimplência**. Contudo, a existência dessa contabilização não prova, por si só, que um pagamento deveria ter sido baixado de conta nominativa; é preciso conhecer a origem do contrato e o tratamento contábil dos direitos creditórios. **Não descontar novamente os R$ 2,50 milhões do saldo atual de R$ 6,80 milhões**, pois os créditos à 1435 já afetaram a posição contábil.

A grande pendência deixou de ser descobrir **se** existem recebimentos diretos na conta genérica — **isso está confirmado** — e passou a ser vincular os recebimentos a títulos, contratos e devedores para determinar o saldo aberto real, os vencimentos e a inadimplência. O método de reconciliação deve aceitar pagamentos por terceiros e nomes diferentes do devedor contratual, usando identificadores bancários/contratuais.

## 4. Como obter um saldo de carteira defensável sem exigir fechamento perfeito por conta

O controle precisa partir de **eventos e documentos**, não da suposição de que o nome na entrada bancária identifica o devedor:

1. **Base de contratos/parcelas:** contrato, cedente/originadora, devedor, valor de aquisição, valor de face, vencimentos, renegociações, cessões, cancelamentos e baixas formais, com identificadores estáveis.
2. **Base de liquidações efetivas:** extratos já conciliados, relatórios bancários de cobrança, CNAB ou retorno de liquidação, identificador do boleto/pagamento (nosso número, linha digitável, ID transação, referência), data e valor.
3. **Vínculo documental:** conciliar por identificadores de título/contrato, lote, data e valor, inclusive quando pagador é terceiro. Nome do pagador sozinho não pode determinar automaticamente o devedor. Evidências ambíguas devem permanecer como **recebimento não identificado**.
4. **Conciliação global:** classificar (a) títulos sem quitação comprovada, (b) títulos liquidados e corretamente baixados, (c) créditos pagos mas não baixados ou de baixa duvidosa, (d) dinheiro recebido ainda não alocado, (e) créditos renegociados/estornados/cedidos; evitar dupla contagem.
5. **Conclusão de aging e recuperação:** somente sobre o **estoque aberto comprovado e reconciliado**, com vencimentos efetivos e histórico de cobrança. Classificar `a vencer`, `vencidos`, `disputados`, `renegociados` e `recuperabilidade não estimável` sem fingir precisão.

**Não somar automaticamente valores recebidos sem vínculo a um devedor específico nem descontá-los diretamente de um contrato.** É possível elaborar uma reconciliação global com partidas pendentes e faixas de incerteza, sem inventar fechamento individual.

## 5. Consequência para o relatório executivo

Apresentar como fato: **“Carteira contabilizada em R$ 6.801.908,85, conciliada ao balancete; posição efetivamente aberta por contrato, inadimplência e realização econômica não apuráveis de forma confiável por inexistência de conciliação individual das baixas e pela ocorrência de pagamentos por terceiros sem vínculo inequívoco.”**

Se o passivo exigível de **R$ 8.562.066,98** for adotado provisoriamente como referência, a diferença contábil de **R$ 731.945,65** é apenas a posição do balanço. O patrimônio econômico pode ser diferente, e não é possível quantificá-lo sem a reconciliação dos ativos. Não afirmar que o ativo está superavaliado, apenas que **há risco de incorreção não mensurado**.

## 6. Rastreabilidade

- `balancetes/Razão2025.xls` e `balancetes/Razão2026.xls`.
- `levantamento-financeiro/razoes-anuais/catalogo.json` e `razoes-anuais/conciliacao.json`.
- `balancetes/Balancete-ja-set-2026.pdf`.
- `levantamento-financeiro/LEIA-ME.md` e `Premissas_confirmadas.json`.

**Esta retificação substitui a interpretação de inadimplência da versão inicial deste documento.** Ela não altera lançamentos, balancetes ou contratos, tampouco afirma que pagamentos de terceiros específicos já foram encontrados ou conciliados.
