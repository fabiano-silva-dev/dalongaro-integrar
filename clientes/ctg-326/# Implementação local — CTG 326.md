# Implementação local — CTG 326

Estou trabalhando em um projeto diferente do **FT/Integrar**.

A implementação desta demanda deve ser criada integralmente no projeto atual, dentro da pasta:

```text
CTG-326
```

O projeto **FT/Integrar** deve ser utilizado somente como referência técnica para localizar e compreender:

* rotinas de leitura de planilhas;
* normalização de datas e valores;
* identificação de colunas;
* tratamento de arquivos XLS, XLSX e CSV;
* estrutura interna dos lançamentos;
* validações;
* geração de arquivos para importação contábil;
* leiaute de exportação utilizado pelo sistema Domínio.

## Regra fundamental

Não alterar absolutamente nenhum arquivo do projeto **FT/Integrar**.

O acesso ao FT/Integrar deve ser exclusivamente de leitura.

Toda a implementação, configuração, documentação, arquivos intermediários e resultados devem permanecer dentro da pasta `CTG-326` do projeto atual.

Não criar commits, branches, arquivos temporários ou alterações dentro do FT/Integrar.

---

# Objetivo

Criar scripts locais que:

1. leiam as planilhas financeiras fornecidas pelo CTG 326;
2. analisem os lançamentos existentes;
3. utilizem o histórico, descrição, favorecido e demais informações para sugerir a classificação contábil;
4. utilizem o plano de contas disponível no arquivo `contas.pdf`;
5. gerem uma planilha intermediária de conferência;
6. permitam que essa planilha seja ajustada manualmente;
7. leiam novamente a planilha ajustada;
8. gerem o arquivo final no leiaute aceito pelo sistema Domínio;
9. permitam repetir a exportação sempre que a planilha intermediária for alterada.

---

# Estrutura geral do processo

A solução deverá possuir dois fluxos principais.

## Fluxo 1 — Importação e classificação

```text
Planilhas originais do CTG
        ↓
Leitura e normalização
        ↓
Análise do histórico e favorecido
        ↓
Classificação contábil sugerida
        ↓
Planilha de conferência editável
```

## Fluxo 2 — Exportação definitiva

```text
Planilha de conferência revisada
        ↓
Validações
        ↓
Geração do arquivo do Domínio
        ↓
Relatório de erros e pendências
```

A exportação para o Domínio não deve depender da releitura das planilhas originais.

Depois que a planilha de conferência for gerada, ela passa a ser a fonte da exportação definitiva.

---

# Etapa 1 — Analisar o FT/Integrar como referência

Antes de desenvolver, localize o projeto FT/Integrar disponível no ambiente.

Pesquise somente em modo de leitura por implementações relacionadas a:

```text
Dominio
Domínio
exportacao
exportação
contabil
contábil
lancamento
lançamento
planilha
spreadsheet
xlsx
xls
csv
historico
histórico
debito
débito
credito
crédito
```

Identifique:

* bibliotecas utilizadas para leitura de planilhas;
* funções de normalização de datas;
* funções de normalização de valores monetários;
* identificação dinâmica de cabeçalhos;
* tratamento de células vazias e fórmulas;
* estrutura interna de lançamentos;
* regras de validação;
* formato utilizado na exportação para o Domínio;
* encoding do arquivo;
* separadores;
* formato das datas;
* formato dos valores;
* ordem dos campos;
* histórico contábil;
* regras para débito e crédito;
* exemplos de arquivos já gerados.

Apresente inicialmente um resumo objetivo do que foi encontrado.

Depois, copie ou adapte apenas as ideias e lógicas necessárias para dentro do projeto atual.

Não criar dependência em tempo de execução com o FT/Integrar, salvo se isso for explicitamente indispensável.

A preferência é que o código necessário seja implementado de forma autônoma dentro da pasta `CTG-326`.

---

# Etapa 2 — Estrutura local

Crie uma estrutura organizada dentro da pasta `CTG-326`.

Estrutura sugerida:

```text
CTG-326/
├── entrada/
│   ├── planilhas/
│   └── plano-contas/
│       └── contas.pdf
├── trabalho/
│   ├── extraido/
│   ├── conferencias/
│   └── temporarios/
├── saida/
│   ├── dominio/
│   ├── relatorios/
│   └── pendencias/
├── configuracoes/
│   ├── regras-classificacao.json
│   ├── favorecidos.json
│   └── configuracao.json
├── scripts/
├── src/
├── tests/
├── logs/
└── README.md
```

Adapte essa estrutura ao padrão do projeto atual, caso ele já possua uma organização definida.

Não espalhar scripts e arquivos gerados na raiz do projeto.

---

# Etapa 3 — Leitura das planilhas originais

Os scripts devem localizar e processar os arquivos existentes em:

```text
CTG-326/entrada/planilhas
```

Suportar, conforme as bibliotecas já existentes no ambiente:

* XLS;
* XLSX;
* CSV.

Analisar todas as abas relevantes.

A leitura deve considerar:

* cabeçalhos em posições diferentes;
* títulos antes do cabeçalho;
* células mescladas;
* linhas vazias;
* subtotais;
* totais;
* saldos anteriores;
* saldos finais;
* fórmulas;
* valores armazenados como texto;
* datas em diferentes formatos;
* lançamentos negativos;
* colunas diferentes entre arquivos;
* registros duplicados;
* estornos;
* entradas;
* saídas;
* transferências;
* lançamentos incompletos.

A identificação das colunas deve ser feita preferencialmente pelos nomes dos cabeçalhos, e não por posições fixas.

Reconhecer variações como:

```text
Data
Data do movimento
Pagamento
Recebimento
Vencimento
Histórico
Historico
Descrição
Descricao
Complemento
Observação
Observacao
Favorecido
Fornecedor
Cliente
Associado
Documento
Número
Numero
Entrada
Receita
Crédito
Credito
Saída
Saida
Despesa
Débito
Debito
Valor
Conta
Banco
Caixa
Forma de pagamento
```

---

# Etapa 4 — Normalização dos dados

Todos os lançamentos devem ser convertidos para uma estrutura interna padronizada.

Exemplo conceitual:

```json
{
    "id_lancamento": "",
    "arquivo_origem": "",
    "aba_origem": "",
    "linha_origem": 0,
    "data": "",
    "documento": "",
    "historico_original": "",
    "historico_normalizado": "",
    "favorecido_original": "",
    "favorecido_normalizado": "",
    "tipo_movimento": "",
    "valor": 0.00,
    "conta_financeira": "",
    "codigo_conta_debito": "",
    "descricao_conta_debito": "",
    "codigo_conta_credito": "",
    "descricao_conta_credito": "",
    "historico_contabil": "",
    "regra_aplicada": "",
    "confianca": 0,
    "status": "",
    "exportar": "SIM",
    "observacoes": ""
}
```

A estrutura definitiva deve respeitar a linguagem e o padrão adotados pelo projeto atual.

## Tratamento de valores

Tratar corretamente valores como:

```text
1.234,56
R$ 1.234,56
-1.234,56
(1.234,56)
1234.56
```

Internamente, trabalhar com tipo numérico apropriado.

Evitar cálculos com valores monetários usando ponto flutuante sem controle de precisão.

## Tratamento de datas

Reconhecer formatos como:

```text
01/07/2026
1/7/2026
2026-07-01
01-07-2026
```

Também tratar datas numéricas do Excel.

---

# Etapa 5 — Plano de contas

Utilizar o arquivo:

```text
CTG-326/entrada/plano-contas/contas.pdf
```

O PDF contém o plano de contas contábil do CTG.

Extrair e organizar:

* código da conta;
* descrição;
* nível;
* hierarquia;
* natureza;
* conta sintética ou analítica;
* grupo contábil;
* situação ativa, quando disponível.

Somente contas existentes nesse plano poderão ser utilizadas.

Não inventar códigos contábeis.

Evitar lançamentos em contas sintéticas quando existirem contas analíticas apropriadas.

Gerar também um arquivo estruturado derivado do PDF, por exemplo:

```text
CTG-326/trabalho/extraido/plano-contas.json
```

ou:

```text
CTG-326/trabalho/extraido/plano-contas.xlsx
```

Esse arquivo deverá poder ser regenerado sempre que o PDF for alterado.

---

# Etapa 6 — Classificação contábil

A classificação deve analisar conjuntamente:

* histórico;
* descrição;
* favorecido;
* fornecedor;
* associado;
* documento;
* tipo de movimento;
* entrada ou saída;
* conta bancária;
* caixa;
* forma de pagamento;
* lançamentos semelhantes;
* regras cadastradas;
* plano de contas.

Para cada lançamento, sugerir:

* conta de débito;
* conta de crédito;
* histórico contábil;
* regra utilizada;
* nível de confiança;
* observação ou justificativa.

## Cuidados contábeis

Não considerar automaticamente:

```text
Toda entrada = receita
Toda saída = despesa
```

Devem ser identificadas situações como:

* transferências entre bancos e caixa;
* adiantamentos;
* empréstimos;
* devoluções;
* estornos;
* pagamento de obrigações;
* recebimento de créditos;
* aquisição de bens;
* imobilizado;
* receitas;
* despesas;
* movimentações patrimoniais.

## Exemplos conceituais

Os códigos devem ser encontrados no `contas.pdf`.

Recebimento de mensalidade:

```text
Débito: Caixa ou Banco
Crédito: Receita de mensalidades
```

Pagamento de energia elétrica:

```text
Débito: Despesa com energia elétrica
Crédito: Caixa ou Banco
```

Pagamento de fornecedor já provisionado:

```text
Débito: Fornecedores
Crédito: Caixa ou Banco
```

Transferência bancária:

```text
Débito: Banco de destino
Crédito: Banco de origem
```

Compra de equipamento:

```text
Débito: Conta correspondente do imobilizado
Crédito: Caixa, Banco ou Fornecedores
```

---

# Etapa 7 — Regras configuráveis

As classificações não devem ficar espalhadas pelo código em grandes blocos de `if` e `else`.

Criar arquivos de configuração dentro de:

```text
CTG-326/configuracoes
```

Exemplo de regra:

```json
{
    "nome": "Pagamento de energia elétrica",
    "prioridade": 100,
    "tipo_movimento": "SAIDA",
    "palavras": [
        "energia",
        "conta de luz",
        "rge"
    ],
    "favorecidos": [
        "RGE"
    ],
    "codigo_conta_debito": "",
    "codigo_conta_credito": "CONTA_FINANCEIRA",
    "confianca": 100
}
```

Os códigos devem ser preenchidos somente com contas existentes no plano de contas.

Permitir adicionar ou corrigir regras sem precisar alterar o código-fonte.

---

# Etapa 8 — Cadastro de favorecidos

Criar uma base configurável de favorecidos e suas classificações recorrentes.

Exemplo:

```json
{
    "nome_normalizado": "RGE",
    "variacoes": [
        "RGE",
        "RGE SUL",
        "RGE SUL DISTRIBUIDORA DE ENERGIA"
    ],
    "tipo_movimento": "SAIDA",
    "codigo_conta_debito": "",
    "historico_padrao": "PGTO ENERGIA ELÉTRICA"
}
```

A classificação por favorecido deve ajudar o processo, mas não deve substituir uma informação mais específica do histórico.

---

# Etapa 9 — Planilha de conferência editável

Após ler e classificar as planilhas originais, gerar uma planilha intermediária editável.

Sugestão de nome:

```text
CTG-326/trabalho/conferencias/CTG-326-classificacao.xlsx
```

Essa planilha será utilizada para:

* conferir os lançamentos;
* corrigir débito;
* corrigir crédito;
* alterar histórico;
* marcar lançamentos que não devem ser exportados;
* incluir observações;
* resolver pendências;
* realizar uma nova exportação sem reler os arquivos originais.

## Colunas mínimas

A planilha deve conter:

```text
ID do lançamento
Arquivo de origem
Aba de origem
Linha de origem
Data
Documento
Histórico original
Favorecido
Tipo de movimento
Valor
Conta financeira original
Código da conta de débito
Descrição da conta de débito
Código da conta de crédito
Descrição da conta de crédito
Histórico contábil
Regra aplicada
Nível de confiança
Status
Exportar
Observações
```

## Requisitos da planilha

* cabeçalhos claros;
* filtro automático;
* primeira linha congelada;
* formatação de datas;
* formatação monetária em padrão brasileiro;
* destaque para pendências;
* destaque para classificações de baixa confiança;
* validação da coluna `Exportar`, aceitando preferencialmente `SIM` ou `NÃO`;
* validação dos códigos contábeis;
* listas de seleção de contas, quando tecnicamente viável;
* preservação do ID do lançamento;
* nenhuma fórmula essencial escondida;
* possibilidade de edição pelo usuário.

A planilha deve ser o principal arquivo de trabalho e conferência.

---

# Etapa 10 — Exportação baseada na planilha revisada

Criar um script independente que leia exclusivamente a planilha de conferência.

Exemplo de execução conceitual:

```bash
python scripts/exportar_dominio.py \
    --arquivo trabalho/conferencias/CTG-326-classificacao.xlsx
```

Ou equivalente na linguagem já utilizada no projeto atual.

O script deverá:

1. abrir a planilha revisada;
2. validar todas as linhas marcadas para exportação;
3. confirmar a existência das contas no plano;
4. verificar datas;
5. verificar valores;
6. verificar débito e crédito;
7. verificar histórico;
8. impedir débito igual ao crédito;
9. impedir contas inexistentes;
10. gerar o arquivo do Domínio;
11. gerar um relatório de erros;
12. gerar um resumo da exportação.

Sempre que a planilha for alterada, o usuário deverá poder executar novamente o script e gerar um novo arquivo.

---

# Etapa 11 — Leiaute do Domínio

Não inventar o leiaute.

Localizar no FT/Integrar a lógica real já utilizada para exportação ao sistema Domínio e adaptá-la para dentro do projeto atual.

Confirmar:

* formato do arquivo;
* ordem dos campos;
* separador;
* data;
* valor;
* débito;
* crédito;
* código do histórico;
* complemento do histórico;
* código da empresa;
* lote;
* estabelecimento;
* encoding;
* quebra de linha;
* caracteres permitidos;
* tamanho máximo do histórico;
* nome do arquivo.

O código relacionado ao CTG é:

```text
326
```

Antes de posicionar esse código na exportação, verificar no modelo existente do FT/Integrar qual campo ele representa.

Pode ser:

* código da empresa;
* código interno;
* código do cliente;
* código do estabelecimento;
* outro identificador.

Não presumir.

---

# Etapa 12 — Arquivos de saída

O processo deverá gerar:

## Arquivo de conferência

```text
CTG-326/trabalho/conferencias/CTG-326-classificacao.xlsx
```

## Arquivo para o Domínio

```text
CTG-326/saida/dominio/
```

O nome deve conter data e hora ou número da versão para não sobrescrever exportações anteriores.

Exemplo:

```text
CTG-326-dominio-2026-07-25-01.txt
```

## Arquivo de pendências

```text
CTG-326/saida/pendencias/
```

Deve conter os lançamentos que não puderam ser exportados.

## Relatório da execução

```text
CTG-326/saida/relatorios/
```

Informar:

* arquivos originais lidos;
* quantidade de abas;
* linhas analisadas;
* lançamentos identificados;
* lançamentos válidos;
* lançamentos não classificados;
* lançamentos não exportados;
* duplicidades;
* valor total de entradas;
* valor total de saídas;
* valor total exportado;
* quantidade exportada;
* caminho do arquivo gerado.

---

# Etapa 13 — Atualização das regras a partir das correções

Quando uma classificação for corrigida manualmente na planilha, disponibilizar um processo opcional para transformar essa correção em regra reutilizável.

Por exemplo:

```bash
python scripts/atualizar_regras.py \
    --arquivo trabalho/conferencias/CTG-326-classificacao.xlsx
```

Esse processo poderá:

* identificar classificações alteradas;
* comparar classificação sugerida com classificação final;
* sugerir novas regras por histórico;
* sugerir regras por favorecido;
* atualizar os arquivos de configuração somente após validação;
* manter registro das regras adicionadas.

Não alterar automaticamente regras existentes sem rastreabilidade.

---

# Etapa 14 — Controle de duplicidade

Criar um identificador estável para cada lançamento.

A chave poderá considerar:

```text
arquivo
aba
linha
data
documento
histórico normalizado
favorecido
valor
```

Gerar um hash ou identificador equivalente.

A planilha de conferência deve preservar esse identificador.

Ao gerar uma nova exportação, alertar sobre:

* linhas duplicadas dentro da planilha;
* lançamentos já exportados;
* IDs repetidos;
* alterações em lançamentos anteriormente exportados.

Não bloquear uma nova exportação corrigida, mas exigir uma opção explícita de reprocessamento quando necessário.

---

# Etapa 15 — Histórico das exportações

Manter dentro da pasta `CTG-326` um registro das exportações realizadas.

Exemplo:

```text
CTG-326/saida/relatorios/historico-exportacoes.json
```

Registrar:

* data e hora;
* arquivo de conferência utilizado;
* hash do arquivo de conferência;
* quantidade exportada;
* valor total;
* arquivo gerado;
* lançamentos exportados;
* pendências;
* versão das regras utilizadas.

---

# Etapa 16 — Comandos esperados

Criar uma interface simples de execução.

Os nomes abaixo são apenas sugestões.

## Analisar as planilhas originais

```bash
python scripts/analisar_planilhas.py
```

Resultado:

* leitura das planilhas;
* classificação;
* geração da planilha editável;
* geração das pendências;
* nenhuma exportação definitiva.

## Gerar arquivo para o Domínio

```bash
python scripts/exportar_dominio.py \
    --arquivo trabalho/conferencias/CTG-326-classificacao.xlsx
```

Resultado:

* validação da planilha revisada;
* geração do arquivo do Domínio;
* geração do relatório.

## Validar sem exportar

```bash
python scripts/exportar_dominio.py \
    --arquivo trabalho/conferencias/CTG-326-classificacao.xlsx \
    --validar
```

Resultado:

* validações;
* relatório de erros;
* nenhum arquivo definitivo.

## Reprocessar planilhas originais

```bash
python scripts/analisar_planilhas.py --reprocessar
```

Antes de sobrescrever a planilha de conferência existente, criar uma cópia de segurança.

---

# Etapa 17 — Preservação das correções manuais

Ao reprocessar as planilhas originais, não perder automaticamente os ajustes já realizados na planilha de conferência.

Implementar um mecanismo de mesclagem baseado no `ID do lançamento`.

Quando o lançamento já existir na planilha anterior, preservar preferencialmente:

* código da conta de débito corrigido manualmente;
* código da conta de crédito corrigido manualmente;
* histórico contábil corrigido;
* campo `Exportar`;
* observações;
* status de revisão.

Adicionar uma coluna que identifique a origem da classificação:

```text
AUTOMÁTICA
MANUAL
REGRA
FAVORECIDO
IMPORTADA DA REVISÃO ANTERIOR
```

Criar backup antes de atualizar qualquer planilha de conferência.

---

# Etapa 18 — Validações obrigatórias

Antes da exportação, verificar:

* data válida;
* valor maior que zero;
* código de débito preenchido;
* código de crédito preenchido;
* débito diferente do crédito;
* contas existentes no plano;
* utilização de contas analíticas quando exigido;
* histórico preenchido;
* linha marcada com `Exportar = SIM`;
* ausência de duplicidade;
* consistência dos totais;
* compatibilidade com o leiaute do Domínio;
* encoding;
* limite de caracteres;
* caracteres inválidos.

Uma linha inválida não deve impedir necessariamente a exportação das demais.

As linhas inválidas devem ser excluídas do arquivo final e relacionadas no arquivo de pendências.

---

# Etapa 19 — Testes

Criar testes para:

* leitura de XLS;
* leitura de XLSX;
* leitura de CSV;
* identificação dinâmica de cabeçalhos;
* datas do Excel;
* datas em texto;
* valores brasileiros;
* valores negativos;
* células vazias;
* fórmulas;
* totais e subtotais;
* classificação por histórico;
* classificação por favorecido;
* transferências;
* lançamentos patrimoniais;
* contas inexistentes;
* débito igual ao crédito;
* duplicidades;
* leitura da planilha revisada;
* preservação de ajustes manuais;
* geração do arquivo do Domínio;
* encoding;
* histórico com acentos;
* reexportação após ajuste.

---

# Etapa 20 — Documentação

Criar o arquivo:

```text
CTG-326/README.md
```

Documentar:

* objetivo;
* estrutura das pastas;
* dependências;
* instalação;
* localização das planilhas originais;
* localização do `contas.pdf`;
* comando para gerar a conferência;
* como revisar a planilha;
* comando para validar;
* comando para exportar;
* como corrigir classificações;
* como atualizar regras;
* como reprocessar;
* como preservar correções manuais;
* formato dos arquivos gerados;
* tratamento de erros;
* controle de duplicidade;
* histórico de exportações.

---

# Restrições obrigatórias

* Não modificar o FT/Integrar.
* Não gravar arquivos dentro do FT/Integrar.
* Não criar commits no FT/Integrar.
* Não importar diretamente classes do FT/Integrar sem avaliar a dependência.
* Não criar dependência permanente com o FT/Integrar.
* Não inventar o leiaute do Domínio.
* Não inventar contas contábeis.
* Não sobrescrever planilhas revisadas sem backup.
* Não perder correções manuais durante o reprocessamento.
* Não gerar o arquivo final diretamente das planilhas originais.
* Não exportar linhas pendentes ou inválidas.
* Não excluir registros silenciosamente.
* Não alterar arquivos originais.
* Não realizar commit ou push sem autorização.

---

# Resultado esperado nesta execução

Primeiro, realize a análise técnica e apresente:

1. onde foi localizado o FT/Integrar;
2. quais arquivos e rotinas serão utilizados apenas como referência;
3. qual é o leiaute do Domínio identificado;
4. quais planilhas do CTG 326 foram encontradas;
5. qual é a estrutura de cada planilha;
6. como o `contas.pdf` será convertido;
7. qual linguagem e bibliotecas serão utilizadas;
8. quais scripts serão criados dentro de `CTG-326`;
9. qual será o fluxo da planilha de conferência;
10. como os ajustes manuais serão preservados.

Depois dessa análise, implemente os scripts dentro do projeto atual.

Ao finalizar:

* execute a análise das planilhas;
* gere a planilha de conferência;
* gere o arquivo de pendências;
* valide os totais;
* não faça a exportação definitiva caso existam classificações duvidosas;
* informe todos os arquivos criados;
* apresente os comandos para revisar e reexportar;
* não faça commit ou push.
