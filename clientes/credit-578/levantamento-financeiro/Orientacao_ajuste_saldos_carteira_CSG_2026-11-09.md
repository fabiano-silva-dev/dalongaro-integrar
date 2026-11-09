# CSG — orientação técnica sobre ajuste de diferença entre créditos contábeis e controle gerencial

**Data:** 09/11/2026. **Base contábil:** 30/09/2026. **Parecer preliminar:** sem lançamento contábil efetuado.

## 1. Diferença levantada

- Direitos creditórios contábeis grupo 1.1.2 em 30/09/2026: **R$ 6.801.908,85**.
- Posição gerencial dos boletos não quitados em 07/10/2026, retirada a parte quitada: **R$ 6.083.101,78**.
- **Diferença indicativa R$ 718.807,07**, comparando datas diferentes e possivelmente critérios distintos (valor de face versus valor contábil).
- Para orientação de lançamento, analisar a hipótese pedida pela administração de que a diferença seja **real e integralmente referente a saldo a receber contabilizado a maior**; essa é **hipótese, não constatação de auditoria**, e não dispensa identificação da origem.

## 2. Precedentes encontrados nos razões — há conta específica

**Conta 657 — AJUSTES DE EXERCICIOS ANTERIORES, classificação 2.4.6.01.001**, existe no histórico do plano da CSG. Ela teve movimentação em 2023 e em 2025, com **saldo final zero nos dois exercícios** devido às respectivas contrapartidas/encerramento patrimonial. O histórico confirma uso para corrigir valores antigos sem transitar pelo resultado corrente, **mas a conta não é contrapartida universal de divergências**.

Precedentes com lançamento de ambos os lados conferido no mesmo lote:

1. **02/01/2023, lotes 1609, 1613 e 1611:** correção de créditos individuais (clientes 527, 529, 528). `D: clientes / C: 657`, respectivamente **R$ 2.143,27**, **R$ 1.241,20** e **R$ 597,94**. Histórico: ajustes das contas de clientes conforme relatório da empresa; **aumento do ativo** via ajuste patrimonial de exercícios anteriores.
2. **01/01/2025, lote 23306:** `D: 657 / C: 1434 — VIA CAPITAL`, **R$ 46.906,96**. Histórico expressamente identifica **erro no reconhecimento de passivo em 2024**, com **ausência de impacto no resultado corrente**. Aumento do passivo e redução do patrimônio líquido.
3. **31/12/2025, lote 24633:** `D: 657 R$ 1.252,93 / C: 31 — IRRF E CRF A RECUPERAR R$ 1.078,09 / C: 2013 — IRRF A RECUPERAR R$ 174,84`. Histórico: **ajuste de conta IRRF e CRF a recuperar**. **Redução do ativo contra conta patrimonial de ajuste de exercícios anteriores**, o precedente mais próximo da hipótese de correção de créditos contabilizados a maior.
4. **01/01/2026, lote 27941:** `D: cliente 1692 R$ 1.716,08 / C: cliente 1672 R$ 1.716,08`. Ajuste entre clientes, **sem redução do ativo agregado**.
5. **02/01/2026, lote 32130:** `D: cliente 1502 R$ 7.215,85 / C: conta 1435 — DIREITOS CREDITORIOS R$ 7.215,85`. Ajuste de saldo referente a exercícios anteriores **entre duas contas do ativo**, sem reduzir o total.

As fontes e pares completos (ano, data, lote, histórico, contas e linhas de origem) estão em `auditoria_ajustes_historicos_CSG.md` e `auditoria_ajustes_historicos_CSG.json`.

## 3. A conta que deve ser debitada depende da causa

**Hipótese A: recebimento já entrou no banco, mas foi creditado na conta 1435.** A partida `D: banco / C: 1435` **já reduziu o ativo**. Não repetir o débito em bancos nem lançar uma segunda baixa do mesmo crédito; primeiro identificar se a conta individual reproduziu indevidamente o mesmo direito ou se são carteiras diferentes. Se houver duplicidade de reconhecimento de créditos **de exercícios anteriores** comprovada, pode ser necessária `D: ajustes patrimoniais de exercícios anteriores (657, segundo norma e plano aprovado) / C: crédito contabilizado em duplicidade` — **somente pelo valor efetivamente duplicado**, com tratamento retrospectivo. A hipótese de reclassificar `D: 1435 / C: cliente` apenas desloca valores e não reduz o saldo total do ativo.

**Hipótese B: recebimento entrou no banco, mas foi registrado no passivo como recebimento pendente de identificação.** Corrigir a verdadeira contrapartida: `D: passivo de recebimentos a identificar / C: clientes ou direitos creditórios`, **se o passivo estiver efetivamente creditado e representar o mesmo título pago**. Reduz ativo e passivo, sem afetar o PL. A conta 1595 `ADIANTAMENTO DE CLIENTES` tinha somente **R$ 56.100,00 de saldo credor** em 30/09/2026: não serve para absorver arbitrariamente R$ 718.807,07. Investigar também outras contrapartidas, sem criar saldo devedor de passivo artificial.

**Hipótese C: recebimento foi creditado em receita indevida.** Se a receita indevida pertence a 2026, o estorno deve seguir os requisitos da rubrica de resultado efetivamente usada, com contrapartida na baixa do recebível. Se se trata de **erro material de exercício anterior**, examinar ajuste retrospectivo segundo CPC 23, não lançar como despesa operacional normal de 2026 só para equilibrar os números.

**Hipótese D: não houve recebimento; o crédito existe mas é de difícil recuperação.** Fazer análise específica de **perda esperada** pelo CPC 48, com evidências e critérios de avaliação, normalmente `D: perda estimada no resultado / C: provisão redutora do ativo`. Baixa definitiva só se inexistir expectativa razoável de recuperação. A diferença entre duas planilhas **não define automaticamente a perda**.

**Hipótese E: a planilha usa valor de face e a contabilidade usa custo/preço de aquisição ou custo amortizado.** Explicar e conciliar critérios; pode não haver necessidade de lançamento.

## 4. Simulação — somente se houver erro patrimonial de exercícios anteriores de R$ 718.807,07

**Lançamento ilustrativo, NÃO AUTORIZADO:**
- **D:** conta 657 — Ajustes de Exercícios Anteriores (ou rubrica patrimonial adequada, definida pelo responsável técnico) **R$ 718.807,07**.
- **C:** créditos a receber comprovadamente contabilizados a maior (conta(s) analítica(s) efetivamente afetadas) **R$ 718.807,07**.
- Resultado: ativo contábil passaria, **somente nesse cenário**, de R$ 7.830.121,33 para R$ 7.111.314,26; passivo exigível permanecendo R$ 8.562.066,98, patrimônio líquido passaria de **R$ (731.945,65)** para **R$ (1.450.752,72)**. **Não é o resultado econômico definitivo e não é ajuste efetivamente feito.** O CPC 23 exige considerar reapresentação comparativa e divulgação para erro material de período anterior; tratamento fiscal também deve ser avaliado.

Se a causa estiver no passivo de recebimentos sem identificação, o efeito **não é o mesmo**: ativo e passivo se reduzem e o PL não se altera. Portanto, não usar a conta 657 sem provar a natureza da diferença.

## 5. ALERTA de conciliação patrimonial preexistente

A conta **267 — (-) PREJUÍZOS ACUMULADOS** já apresenta diferença independente de **R$ 646.275,68** entre o razão encadeado e o balancete atualizado de 2026. O relatório executivo preserva o valor do balancete oficial para evitar inventar lançamento. **Antes de qualquer correção via PL, entender a origem desta diferença e não confundi-la com os R$ 718.807,07 do ativo.**

## 6. Providências para sustentação

- Obter saldo gerencial em **30/09/2026**, não somente 07/10; excluir boletos quitados e verificar se a planilha cobre tanto as contas individuais quanto a conta 1435.
- Conciliar **recebimento bancário → conta creditada → identificação do contrato/título**; usar pagamento por terceiro e lote/nosso número como referência, não apenas o nome.
- Demonstrar, em papel de trabalho, qual parte da diferença é duplicidade de ativo, pendência de passivo, erro de receita, perda esperada ou diferença de mensuração; fechar contra a escrituração.
- Somente então o contador responsável aprova o(s) lançamento(s), período, reflexos em demonstrações comparativas e notas explicativas. **Nenhum lançamento foi efetuado por esta auditoria.**

## 7. Normas consultadas

- CPC 23 — Políticas Contábeis, Mudança de Estimativa e Retificação de Erro (itens 41-49): https://conteudo.cvm.gov.br/export/sites/cvm/menu/regulados/normascontabeis/cpc/CPC_23_rev_14.pdf
- CPC 48 — Instrumentos Financeiros (itens 5.4.4 e 5.5): https://conteudo.cvm.gov.br/export/sites/cvm/menu/regulados/normascontabeis/cpc/CPC_48_rev_15.pdf
