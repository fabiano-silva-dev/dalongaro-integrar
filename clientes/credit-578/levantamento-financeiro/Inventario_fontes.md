# Inventário das fontes - CSG



Data-base mantida em 30/09/2026. A fonte de 2026 é balancetes/Balancete-ja-set-2026.pdf, indicado pelo cliente como atualizado. O arquivo anterior é mantido somente para comparar revisões do mesmo período. A data da exportação não é a data dos lançamentos.



## 2022

BP, DRE, balancete anual, Razão2022.xls indexado e certificados de debêntures; conciliação bancária confirmada pelo escritório

PENDENTE: Classificar finalidade dos lançamentos e contrapartidas do razão já recebido; carteira UY3; escritura original e vínculo dos títulos aos lançamentos

Fonte: publicacao-balancos/DOCUMENTOS CREDIT/*2022.pdf; outras informações; Premissas_confirmadas.json



## 2023

BP, DRE, balancete anual, Razão2023.xls indexado e certificados históricos; conciliação bancária confirmada

PENDENTE: Classificar movimentações no razão já recebido, posição de carteira por parcela e primeiro aditamento

Fonte: publicacao-balancos/DOCUMENTOS CREDIT/*2023.pdf; outras informações



## 2024

BP, DRE, balancete anual, Razão2024.xls indexado, aditamentos e boletins com importância realizada; 479 registros de implantação em 31/12/2024 separados para revisão

PENDENTE: Vincular documentos aos lançamentos por titular e data; classificar contrapartidas e excluir implantação/transfers do fluxo; carteira por parcela

Fonte: publicacao-balancos/DOCUMENTOS CREDIT/*2024.pdf; outras informações



## 2025

BP, DRE, balancete, Razão2025.xls indexado, ECD completa, custos gerenciais; CCBs desde abril; bancos conciliados conforme escritório

PENDENTE: Posição de parcelas em aberto; histórico de aquisições jan-mar/2025; abertura pontual de lançamentos mistos

Fonte: fiscal/dominio/sped_diario00578.txt; ccb/; fiscal/planilhas/CONTROLE - CUSTOS 2025.xlsx



## 2026 jan-set

Balancete fechado, Razão2026.xls indexado; importações de todos os meses; CCBs jan-set inclusive pacotes arquivados; bancos conciliados

PENDENTE: Classificar fluxos pelos razões recebidos, esclarecer diferença de R$ 646.275,68 na conta 267 e vincular plano de importação ao plano final; posição aberta por parcela

Fonte: balancetes/Balancete-ja-set-2026.pdf; CONTABIL*; ccb/; _arquivo/zips/; Premissas_confirmadas.json



## 2026 outubro

Nenhum fechamento de outubro identificado nas fontes

PENDENTE: Balancete fechado e razão de outubro, se já concluídos

Fonte: CONTABIL de 20/10/2026 contém lançamentos até setembro; data de exportação não altera data-base



## Integridade e duplicatas

1375 arquivos inventariados; hashes SHA-256 e cópias idênticas na aba Fontes. Arquivos de importação não são somados a lançamentos da ECD no mesmo período.

DFC e DMPL do Domínio são referência; não controlam o levantamento.

Identificação: CNPJ 46.788.467/0001-49; NIRE correto 43.300.068.854. O NIRE divergente do cabeçalho não foi utilizado.
## Razões anuais incorporados ao levantamento em 08/11/2026

Fontes: `balancetes/Razão2022.xls` a `balancetes/Razão2026.xls`. Índice rastreável em `levantamento-financeiro/razoes-anuais/`: 62.051 eventos; totais/saldos internos verificados; cinco arquivos sem indício do corte do antigo `Razão - geral.xls`. O ano de 2024 contém lote 23308, com 479 lançamentos de implantação e R$ 4.381.414,59 em cada lado, excluídos de interpretações automáticas como caixa econômico. Em 2026, a conciliação dos razões ao balancete atualizado é sem diferença em 1.221 contas e divergente na conta 267 (R$ 646.275,68). A posição patrimonial publicada usa o balancete atualizado; a diferença permanece pendente de explicação. Os razões novos não são somados à ECD ou aos índices anteriores sobrepostos.

Síntese de interpretação e documentos prioritários: `Atualizacao_razoes_anuais_2026-11-08.md`.
