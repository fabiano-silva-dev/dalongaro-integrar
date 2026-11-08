# Índice pesquisável do razão geral CSG

**INCOMPLETO / CORTE NA EXPORTAÇÃO XLS**

O XLS original e o XLSX convertido terminam na linha 65.536, dentro da conta 1434 — VIA CAPITAL, em 10/02/2026, sem total dessa conta. A conta 642 (debêntures) não aparece. Há movimentos de 2022 a setembro de 2026 em outras contas; isso não torna a exportação completa. Dividir o arquivo não recupera o trecho ausente. Os razões separados já disponíveis continuam sendo fontes próprias.

## Conteúdo desta versão

- 41,348 eventos de razão, 1,728 contas; valores exatos em centavos inteiros.
- Intervalo global dos movimentos: 2022-06-23 a 2026-09-30.
- 11 fragmentos JSONL, por ano, com no máximo 5000 eventos cada.
- 14,581 eventos sem Cta.C.Part.; campo preservado nulo, sem inferência.
- 1,727 totais de conta comparados aos totais impressos, 0 divergências.
- 41,348 recorrências de saldo verificadas, 0 divergências.
- Contagem origem = SQLite = JSONL e totais de débito/crédito: OK; integridade SQLite: ok.

## Arquivos e origem

`catalogo.json` contém SHA-256 das fontes, metadados, contagens por ano/grupo/conta, intervalos por conta, avisos, classificação completa e QA. `checagens_contas.json` contém a comparação de cada total de conta à fonte. `manifesto.json` contém os hashes dos derivados. Esses arquivos e este README são versionáveis. O SQLite e os fragmentos JSONL são grandes e ficam ignorados pelo `.gitignore` local.

Fonte: `balancetes/Razão - geral.xls`. Conversão lida: `levantamento-financeiro/qa/razao_geral/Razão - geral.xlsx`. Nenhuma fonte foi modificada. A leitura usa `openpyxl`, todas as abas, mantendo contexto de conta e histórico entre abas. Linhas de continuação são concatenadas sem truncamento e guardadas também em partes originais. Cabeçalhos, saldos anteriores e totais são classificados separadamente; linhas não reconhecidas fazem o QA falhar.

O saldo numérico da célula mantém seu sinal, com D positivo e C negativo, verificado a cada movimento por saldo anterior + débito − crédito. O formato de Excel e a seção visual utilizada ficam preservados; parênteses visuais, que variam com a natureza da conta, não são usados para inverter o número. Saldo anterior só existe no índice quando consta na fonte.

## Pesquisa

O SQLite tem tabelas `eventos`, `contas`, `secoes` e `fonte`, índices por conta/classificação/grupo/data/ano/lote/contrapartida e busca textual `busca` (FTS5, quando disponível). `secoes.dados_json` preserva cabeçalho, saldo anterior e total da fonte. Exemplos com Python padrão:

```python
import sqlite3
con = sqlite3.connect('razao_geral.sqlite')
con.row_factory = sqlite3.Row
rows = con.execute("SELECT * FROM eventos WHERE codigo_conta=? AND ano=? ORDER BY data,id", ('1434', 2026)).fetchall()
rows = con.execute("SELECT e.* FROM busca b JOIN eventos e ON e.id=b.rowid WHERE busca MATCH ? ORDER BY e.data,e.id", ('EMPRESTIMO',)).fetchall()
```

Cada evento possui `id`, `secao_id`, `data`, `ano`, `lote`, `codigo_conta`, `classificacao`, `nome_conta`, `grupo_1/2/3`, `historico`, `historico_partes`, `contrapartida`, `contrapartida_codigo`, `debito_centavos`, `credito_centavos`, `saldo_centavos`, natureza/sinal/formato do saldo, `aba`, `linha`, `aba_final`, `linha_final`, `origens` (aba/linha/folha impressa), caminhos e SHA-256 original/convertido. No SQLite, as listas estruturadas ficam em `historico_partes_json` e `origens_json`. Contrapartida numérica é texto para preservar identificadores.

Um evento representa uma linha de uma conta, **não uma partida completa**. Lotes podem ser compostos. Não interpretar a soma de débitos/créditos de todas as contas como fluxo de caixa, nem somar posições de datas distintas. Cta.C.Part. ausente não prova ausência de contrapartida na escrituração.

## Regerar

Requer Python 3 e `openpyxl`. A conversão prévia requer LibreOffice; preservar o XLS original:

```sh
cd clientes/credit-578/levantamento-financeiro
mkdir -p qa/razao_geral
libreoffice -env:UserInstallation=file:///tmp/csg-razao-conversao --headless --convert-to xlsx --outdir qa/razao_geral '../balancetes/Razão - geral.xls'
python indexar_razao_geral.py --self-test
python indexar_razao_geral.py
```

O comando padrão assume esta fonte parcial. Uma futura exportação completa, em XLSX/CSV/TXT ou dividida na origem por ano/grupo, exige revisão de cobertura antes de substituir o índice; o script aceita `--original`, `--xlsx`, `--out` e `--fonte-completa`. Este último apenas retira a marca manual de fonte parcial; limite de 65.536 linhas com conta sem total continua detectado automaticamente. A ausência desse limite não certifica completude documental.

**Não somar nem concatenar este índice aos razões de disponível/ativo/passivo**, pois há sobreposição de contas/movimentos. Substituir a fonte após revisão de cobertura e deduplicação; não executar append automático. A execução regrava somente os derivados com nomes conhecidos na pasta de saída. O script não acessa serviços remotos nem modifica relatórios financeiros.
