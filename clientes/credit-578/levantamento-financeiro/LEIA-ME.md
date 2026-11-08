# Levantamento financeiro da CSG

Empresa: CREDIT SAINT GERMAIN SECURITIZADORA DE CRÉDITO S/A, CNPJ 46.788.467/0001-49. Consolidação contábil das empresas 578 e 592 do Domínio.

Período histórico: 14/06/2022 a 30/09/2026. Não foi identificado fechamento de outubro de 2026. Uma exportação feita em outubro pode conter somente lançamentos até setembro.

Atualização da fonte de 2026: o cliente indicou `balancetes/Balancete-ja-set-2026.pdf` como versão atualizada. Ela substitui o arquivo `Balancete 2026- posicao em 30-09.pdf` nos saldos e no resultado. A versão anterior permanece somente como referência nas abas `Atualização 2026` e `Diferenças contas 2026`; são revisões do mesmo período e não são somadas. O módulo `mod_atualizacao.py` reproduz essa comparação.

O NIRE correto da securitizadora é 43.300.068.854. O número divergente no cabeçalho dos balancetes não identifica esta sociedade e não foi adotado.

## Entregas

- `Relatorio_Executivo_CSG.pdf` e `Relatorio_Executivo_CSG.docx`: versão de leitura para a administração, com resumo, os seis relatórios em linguagem simples, cruzamento final, análise dos recursos de Jane e Lair, documentos solicitados e fontes. O fluxo acumulado usa os balancetes; a análise complementar dos recursos dos sócios identifica os lançamentos bancários de 2025. O Word é editável e o PDF tem o mesmo conteúdo. A emissão desta versão é 08/11/2026; a data-base permanece 30/09/2026.
- `levantamento_financeiro_CSG_2022-06_a_2026-09.xlsx`: seis relatórios e suas bases, síntese, conciliações, pendências e inventário de fontes.
- `Relatorio_Situacao_Financeira_CSG.pdf`: relatório executivo, quadros anuais, análise e ressalvas.
- `Inventario_fontes.md`: cobertura das fontes por período e principais lacunas.
- `gerar_levantamento_csg.py`: comando principal para reproduzir o levantamento. Os módulos `mod_contabilidade.py`, `mod_debentures.py`, `mod_carteira.py`, `mod_fluxo.py`, `mod_atualizacao.py` e `mod_revisao_documental.py` devem permanecer na mesma pasta, assim como `gerar_planilha.mjs` e `Premissas_confirmadas.json`.

Os arquivos JSON intermediários podem ser gerados novamente e não precisam ser versionados. A pasta `qa/` contém material de conferência visual, quando produzido.

## Como executar

A partir da raiz do projeto:

```bash
python3 clientes/credit-578/levantamento-financeiro/gerar_levantamento_csg.py --inventario
python3 clientes/credit-578/levantamento-financeiro/gerar_levantamento_csg.py
```

O primeiro comando produz apenas o inventário. O segundo relê as fontes, processa as bases, gera o PDF e chama `gerar_planilha.mjs` para gerar o Excel. Os documentos originais são somente lidos. Os arquivos de saída deste levantamento são substituídos na nova execução.

Ao final, o comando completo também executa `gerar_relatorio_cliente_csg.py`, que gera a versão para a administração. Para refazer somente a apresentação com os últimos dados já conciliados:

```bash
python3 clientes/credit-578/levantamento-financeiro/gerar_relatorio_cliente_csg.py
```

Esse comando lê `dados_levantamento.json`, produzido pelo levantamento principal. Não atualiza os dados contábeis. A opção `--emissao DD/MM/AAAA` altera a data de emissão e `--somente-docx` permite gerar apenas o arquivo editável.

Para conferir as bases e conciliações sem produzir Excel e PDF:

```bash
python3 clientes/credit-578/levantamento-financeiro/gerar_levantamento_csg.py --somente-dados
```

Esse modo gera `dados_levantamento.json` e as bases intermediárias dos módulos. Não altera documentos de origem.

## Dependências

- Python 3, com `openpyxl` para **leitura** de arquivos Excel e `reportlab` para o PDF.
- `python-docx` para a versão editável da administração. A apresentação usa o renderizador `render_docx.py` do runtime e LibreOffice para gerar PDF e imagens de conferência em `qa/cliente/`.
- Poppler, com o comando `pdftotext` disponível no ambiente. A conferência visual também pode usar `pdftoppm`.
- Fonte DejaVu Sans, usada pelo PDF em `/usr/share/fonts/truetype/dejavu/`.
- Node.js e `@oai/artifact-tool` fornecidos pelo runtime do Codex. A planilha é escrita por `gerar_planilha.mjs`; `openpyxl` não é usado para sua autoria.

No ambiente desta entrega, o comando principal procura o runtime em:

```text
~/.cache/codex-runtimes/codex-primary-runtime/dependencies/
```

O executável esperado é `node/bin/node` e os pacotes ficam em `node/node_modules`. O programa cria nesta pasta do levantamento um vínculo `node_modules` para os pacotes do runtime, quando necessário. Esse vínculo não deve ser versionado.

É possível indicar outro executável Node pela variável `CSG_NODE`. Essa variável muda somente o executável; os pacotes também precisam continuar acessíveis ao arquivo `gerar_planilha.mjs`. Em outro computador, ajuste o caminho do runtime ou providencie um vínculo para o diretório que contém `@oai/artifact-tool`. Não copie nem modifique os pacotes do runtime.

Se as dependências Python não estiverem disponíveis, instale-as no ambiente Python escolhido:

```bash
python3 -m pip install openpyxl reportlab python-docx pillow
```

Em sistemas Debian/Ubuntu, Poppler e a fonte são fornecidos pelos pacotes `poppler-utils` e `fonts-dejavu-core`. O ambiente precisa conseguir localizar `pdftotext` e a pasta da fonte citada acima.

Neste computador, o LibreOffice do runtime exige bibliotecas do sistema mais novas. O gerador da versão do cliente registra essa falha e usa explicitamente `/usr/bin/soffice` como alternativa, mantendo o renderizador canônico e o Python do runtime. Nenhuma dependência gerenciada é modificada. Os PNGs e o PDF renderizado são conferidos antes da entrega.

## Fontes e critérios

Todos os caminhos abaixo são relativos à pasta do cliente, um nível acima desta pasta:

- `publicacao-balancos/DOCUMENTOS CREDIT/`: BP, DRE e balancetes oficiais de 2022 a 2025. As contas analíticas da DRE determinam receitas e despesas anuais; os grupos de resultado dos balancetes anuais já estão encerrados.
- `balancetes/Balancete-ja-set-2026.pdf`: saldos patrimoniais e resultado acumulado de janeiro a setembro de 2026.
- `fiscal/dominio/sped_diario00578.txt`: ECD de 2025, com plano, saldos e partidas contábeis. Lançamentos de encerramento não são novamente tratados como despesas.
- `CONTABIL*.TXT`, inclusive cópias em `fiscal/dominio/`: arquivos de importação. Cópias idênticas são identificadas por conteúdo. Não são somadas novamente à ECD do mesmo período nem tratadas como diário completo.
- Escrituras, aditamentos, certificados e boletins em `entrada/` e `publicacao-balancos/outras informações/`: incluem certificados históricos de 2022 e 2023 e quatro boletins de 2024 com R$ 500.000,00 de integralização declarada. A vinculação aos lançamentos por série e titular está separada da conciliação bancária já confirmada. O nominal bruto de R$ 3.000.000,00 inclui duas cautelas distintas de Lair; R$ 2.300.000,00 depende da hipótese de substituição de uma delas, ainda a resolver.
- `ccb/`, `_arquivo/zips/CCB CLIENTES` de junho a setembro de 2026, `saida/relatorio_operacoes.xlsx` e `Importacao_Baixas_*`: aquisições documentadas de abril de 2025 a setembro de 2026, condições contratuais e baixas observadas. Não representam, por si, o estoque completo aberto na data-base. Documentos de outubro ficam fora dos totais desta data-base.
- `05.2026.xlsx` e `06.2026.xlsx`: extratos parciais e detalhes de cobranças. Saldos não são entradas de caixa; detalhes de boletos não devem ser somados novamente aos créditos bancários.
- `fiscal/planilhas/CONTROLE - CUSTOS 2025.xlsx`: conferência gerencial de janeiro a outubro de 2025, sem cobertura de novembro e dezembro. Segue controle de caixa e não substitui a despesa por competência.

As DFCs e DMPLs do Domínio não são usadas para forçar fechamento. O inventário contém hashes SHA-256 e identifica duplicatas. A planilha registra as fontes e contas junto às linhas e preserva diferenças e dados faltantes.

O escritório confirmou neste atendimento que os balancetes e as DREs estão fechados com os extratos bancários. Essa conciliação é considerada concluída, conforme `Premissas_confirmadas.json`. O razão analítico será usado para detalhar os fluxos por finalidade e vincular operações a contratos.

## Ressalvas de leitura

1. **Custos e despesas estão apurados.** A movimentação líquida das contas de resultado, excluídos os encerramentos e conferida às DREs, permite entregar categorias, valores anuais e acumulado. O total inclui as deduções tributárias indicadas. A abertura do fluxo de caixa por finalidade também contempla operações que formam ativos ou liquidam principal de dívidas e deve evitar dupla contagem.
2. **Aplicações de 2022:** a conta `1.1.4` contém aplicações fora do disponível `1.1.1`. Sua classificação como equivalente de caixa depende de comprovar prazo, liquidez e risco. O levantamento mantém a classificação da fonte e não as acrescenta automaticamente ao disponível. Fonte: BP e balancete de 2022, contas `1.1.1` e `1.1.4`.
3. **PL de 2026:** o grupo `2.4` ainda não contém o resultado parcial dos grupos `3` e `4`. A conciliação patrimonial inclui esse resultado em aberto. Não há ajuste presumido para fazer o balanço fechar.
4. **Fluxo acumulado apurado nos balancetes:** a aba `Fluxo acumulado` apresenta saldo inicial, débitos, créditos, movimento líquido e saldo final do grupo `1.1.1` nos cinco períodos, com coluna acumulada. Somam-se movimentos; a abertura é a primeira e o saldo final é o da última data, sem somar posições anuais. `Caixa por conta` detalha as analíticas e mantém `1.1.4` separado. Os valores brutos incluem transferências internas e não são apresentados como fluxos exclusivos com terceiros. A abertura por finalidade e a eliminação das transferências são complementares. A ECD de 2025 fica como apoio opcional no Excel; não determina nem bloqueia os totais principais.
5. **Fluxo indireto:** a ponte patrimonial confere a variação do disponível por uma identidade entre ativos, passivos, PL e resultado. Ela não é uma DFC completa por atividades: faltam a eliminação detalhada de eventos sem caixa e a classificação em operação, investimento e financiamento.
6. **Carteira:** cronograma contratual não significa parcela aberta. Aging, inadimplência, perda esperada e valor recuperável dependem de posição completa por parcela. Não se presume que toda parcela esteja recebida, em aberto ou recuperável.
7. **Dívidas:** o prazo do Domínio não substitui o vencimento contratual. A ausência de contrato ou encargo contabilizado não prova que o mútuo não tenha juros. O saldo real por titular, a atualização contratual e a classificação de curto/longo prazo permanecem limitados pela documentação disponível.
8. **Situação real:** déficit contábil, necessidade imediata de caixa e déficit econômico ajustado são medidas distintas. Não foi adotada perda zero para calcular um PL real artificial.

`PENDENTE` significa que falta informação ou processamento suficiente para a conclusão indicada. `ESTIMADO` identifica premissa explícita. Um teste `OK` confirma a relação testada. A conciliação bancária está confirmada pelo escritório; a atualização contratual das dívidas e a avaliação de recuperação da carteira são análises específicas.

## Atualização com novas fontes

O processamento é reprodutível para **esta data-base**. A simples inclusão de arquivos novos não altera automaticamente o período do levantamento.

Antes de atualizar setembro para outro mês, revise manualmente os caminhos, filtros de período, colunas anuais, regras de precedência e deduplicação, condições contratuais, data-base e nomes das saídas nos módulos e no comando principal. Preserve a distinção entre data de exportação, data do lançamento, competência e vencimento. Verifique também se os novos documentos completam uma lacuna ou apenas repetem conteúdo existente.

Depois de regerar, confira as abas `Conciliação` e `Pendências`, abra o Excel e renderize o PDF para verificar legibilidade, tabelas e paginação. Confirme especialmente:

- Ativo = passivo exigível + PL, incluindo resultado em aberto quando aplicável.
- DRE reconstruída = DRE oficial/balancete da data-base.
- Despesas por categoria = contas analíticas, sem somar contas sintéticas.
- Variação das debêntures = movimentos comprovados, com diferenças identificadas.
- Fluxo identificado = disponível nas fontes correspondentes.
- Carteira gerencial aberta = conta `1.1.2`, ou diferença documentalmente explicada.

No Git, selecione apenas `clientes/credit-578/levantamento-financeiro/`. Não inclua arquivos de outros clientes nem fontes alteradas fora desta pasta.
