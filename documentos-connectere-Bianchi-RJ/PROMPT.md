# Prompt — documentos de compras no +Gestão (Connectere), grupo Bianchi

Copie o bloco abaixo para um agente com navegador. O objetivo é repetir, mês a mês, o que já foi feito uma vez para o período 01/01/2026 a 13/10/2026.

---

Baixe os documentos de compras e despesas do +Gestão (Connectere) das três fazendas PJ do grupo Bianchi, só PDF e imagem, separados por mês. Não baixe XML. Não misture fazenda PF com PJ. Não use o PDF de impressão do sistema (`notas_fiscais/{id}.pdf?l=1`): esse arquivo não é o documento fiscal.

## Acesso

- Login: https://maisgestao.connectere.agr.br/usuarios/sign_in
- E-mail: dalongarointegrar@gmail.com
- Senha: Integrar@2025
- O host `g3.connectere.agr.br` é o mesmo sistema. O que filtra os dados é a sessão do cabeçalho (Produtor e Fazenda), não o domínio. Página 500 tem título “+G3”.
- Se o HTML contiver “Acesse a sua conta”, a sessão caiu: entre de novo e retome do lançamento em que parou.
- A safra do cabeçalho não filtra esta lista de notas.

## Fazendas — usar só estas

Confirme no cabeçalho o produtor e a fazenda antes de listar ou baixar. Em cada página da nota, o HTML precisa conter o nome do produtor e o nome da fazenda. Se aparecer “Registro não encontrado. Verifique a fazenda/produtor da sessão atual.”, anote o lançamento e siga; não troque de fazenda no meio do lote.

| Produtor | Como selecionar | Fazenda certa | Empresa | Não usar |
|---|---|---|---|---|
| Luciano Bianchi | `/contexto?pid=547` | PJ - Faz Luciano- MT | `/empresas/1857` | PF - Luciano- MT (eid 1018) e as outras fazendas do Luciano |
| Carlos Bianchi | `/contexto?pid=833` (o link some quando ele já está selecionado) | PJ - Carlos | `/empresas/1860` | PF - Carlos (eid 1859) |
| Claudio Bianchi | `/contexto?pid=516` | PJ - Faz Bianchi | `/empresas/1854` | PF - Faz Bianchi (eid 949) |

Uma fazenda por vez. Troque o destino do receptor antes de mudar de fazenda, para os arquivos não caírem na pasta errada.

Ao trocar de produtor pelo `/contexto?pid=`, o sistema pode abrir a fazenda PF. Confira o cabeçalho e, se precisar, volte para a PJ (`/contexto?eid=1854` no Claudio, `/contexto?eid=1860` no Carlos).

## Separar por endereço da fazenda remetente

Na base do Claudio e na do Carlos há notas de outra pessoa, no mesmo período e no mesmo filtro de compras. Elas se separam pelo campo **Endereço da fazenda remetente** (`q[endereco_remetente_id_eq]`). O que não entra nesse endereço fica com o produtor da sessão.

| Sessão | Endereço | CNPJ | id do endereço | Pasta dos documentos |
|---|---|---|---|---|
| Claudio Bianchi, PJ - Faz Bianchi | Matriz: VL Pau Fincado, São Gabriel - RS | 55.526.785/0001-22 | 304343 | Fabiane |
| Carlos Bianchi, PJ - Carlos | Fazenda: VL Pau Fincado, São Gabriel - RS | 55.524.705/0001-08 | 304372 | Elenise |

No `fluxo-navegador.js`, preencha `enderecoRemetenteId` com `304343` ou `304372` e grave na pasta correspondente. Sem esse id, a lista é a do produtor inteiro; aí separe depois, tirando da pasta dele os ids que aparecerem no filtro do endereço. Não misture de volta.

Exemplo, Fabiane dentro do Claudio, novembro de 2026:

```
https://maisgestao.connectere.agr.br/notas_fiscais?q[data_gteq]=01/11/2026&q[data_lteq]=30/11/2026&q[operacao_compras]=1&q[operacao_vendas]=0&q[endereco_remetente_id_eq]=304343&q[com_valor]=0
```

Para a Elenise, o mesmo endereço com `304372`, sessão do Carlos em PJ - Carlos. O lançamento dessa fazenda usa a conta CEF - Elenise.

## Período

Na primeira extração o período foi 01/01/2026 a 13/10/2026 e esses arquivos já existem. Não baixe de novo esse intervalo, salvo lançamento que tenha ficado sem arquivo por erro (404 ou página indisponível).

Daqui pra frente, rode um mês por vez. Ajuste só as datas, no formato `DD/MM/YYYY`:

- `q[data_gteq]` = primeiro dia do mês
- `q[data_lteq]` = último dia do mês

Exemplo, novembro de 2026:

```
https://maisgestao.connectere.agr.br/notas_fiscais?q[com_valor]=0&q[data_gteq]=01/11/2026&q[data_lteq]=30/11/2026&q[operacao_compras]=1&q[operacao_vendas]=0&q[pedido_id_eq]=
```

Compras, não vendas: `q[operacao_compras]=1` e `q[operacao_vendas]=0`. O link “Compras” do menu (`/notas_fiscais?q[operacao_compras]=1`) sem as datas mistura outros períodos.

## O que baixar de cada nota

Lista: 50 linhas por página. Linha `tr#nota_fiscal_{id}`. Colunas, a partir do `td` 1: Data, Número, Fornecedor/Cliente, Operação, Total. Deduplique pelo id. Não use `per_page` (responde 500). Não use a exportação CSV/XLSX da tela (sem `campos[]` volta HTML ou 500). A coluna Total da lista é o valor da operação.

Na página `/notas_fiscais/{id}`:

- DANFE: `a[href*="danfe.pdf"]`, em geral `/comercial/nfes/{nfeId}/danfe.pdf`. É PDF da mesma origem; `fetch` com credencial funciona.
- Anexo (desembolso diverso e qualquer outro com arquivo): tabela `#arquivos_modal`, linhas `tr[data-url]`. Células: nome do arquivo, mime, tamanho. Texto “Nenhum item encontrado.” significa sem anexo.
- Aceite só pdf, jpg, jpeg, png, gif e webp, pelo mime ou pela extensão.
- Ignore XML mesmo que esteja anexado.
- Ignore o PDF de impressão `notas_fiscais/{id}.pdf?l=1`.

Anexo do Active Storage: a URL vem como `/rails/active_storage/blobs/redirect/{assinatura}/arquivo`. Troque `redirect` por `proxy` antes do `fetch`, com `credentials: 'include'`. O `fetch` direto no `redirect` falha (o S3 não tem CORS). A rota `/rails/active_storage/disk/` responde 404. Alguns `proxy` e DANFE também respondem 404: o arquivo está quebrado no sistema; registre e siga.

Dois workers em paralelo. Até 4 tentativas na página da nota. Quatro workers geram muitos “Failed to fetch”. Descarte corpo com menos de 80 bytes ou content-type xml/html.

Nome do arquivo:

```
{AAAA-MM-DD}_{numero ou sn}_{slug do fornecedor}_{id da nota}_{danfe|anexo|anexoN}.{pdf|jpg|png|...}
```

Slug: tira acento, troca o que não for letra ou número por `-`, corta em 36 caracteres.

## Onde gravar

Suba o receptor desta pasta antes de baixar. Um destino por fazenda:

```bash
python3 receptor.py baixados/pj-faz-luciano-mt
python3 receptor.py baixados/pj-carlos
python3 receptor.py baixados/pj-faz-bianchi
python3 receptor.py baixados/fabiane
python3 receptor.py baixados/elenise
```

O receptor escuta em `127.0.0.1:8765`. A página HTTPS pode enviar POST para `http://127.0.0.1`. Nome começando com `_` é log e entra em modo append. Os demais vão para a subpasta `AAAA-MM` do prefixo do nome. Encerre o receptor da fazenda anterior (a porta 8765) antes de apontar para outra pasta. Encerrar o processo não apaga arquivo já gravado.

O navegador manda o binário com o cabeçalho `X-Filename`. O fluxo está em `fluxo-navegador.js`: preencha produtor, fazenda, datas e a frase que precisa aparecer no HTML, carregue a lista, rode em lotes de cerca de 150 a 300 notas e pare quando o índice chegar no total.

## CSV do que ficou sem PDF nem imagem

Arquivo `lancamentos-sem-pdf-nem-imagem.csv`, separador `;`, com a coluna do valor. Não entregue o CSV sem essa coluna.

```
id;data;numero;fornecedor;operacao;valor;situacao
```

`valor` é o texto da coluna Total, por exemplo `R$ 9,90`. Todo id precisa ter valor; se faltar, releia a lista em vez de deixar em branco. `situacao`: `sem_arquivo` quando não há DANFE nem anexo de PDF/imagem; `arquivo_indisponivel` quando o link existe e responde 404; `registro_nao_encontrado` quando a página da nota não abre na fazenda atual.

## O que já foi baixado (01/01/2026 a 13/10/2026)

Está no repositório IntegraExpert, pasta `backups/`, e não deve ser copiado para cá de novo:

| Fazenda | Pasta | Notas únicas | Arquivos | Sem PDF/imagem |
|---|---|---|---|---|
| PJ - Faz Luciano- MT | `integrar/backups/documentos-pj-faz-luciano-mt/` | 1.359 (a tela mostrava 1.360) | 1.104 (1.065 PDF, 39 JPG), 1.063 notas | 290, com coluna `total` |
| PJ - Carlos, sem o endereço da Elenise | `integrar/backups/documentos-pj-carlos/` | 452 | 341 arquivos, 324 notas | 126, com coluna `valor`. 404 nas notas 7820035 e 7821099 |
| Elenise, CNPJ 55.524.705/0001-08, tirada da base do Carlos | `integrar/backups/documentos-elenise/` | 19 | 5 arquivos, 4 notas | 15, com coluna `valor` |
| PJ - Faz Bianchi, sem o endereço da Fabiane | `integrar/backups/documentos-pj-faz-bianchi/` | 1.373 | 1.077 arquivos, 1.020 notas | 353, com coluna `valor`. Nota 8314374: registro não encontrado |
| Fabiane, CNPJ 55.526.785/0001-22, tirada da base do Claudio | `integrar/backups/documentos-fabiane/` | 383 | 368 arquivos, 357 notas | 26, com coluna `valor` |

Na lista do Luciano, Compra para Recebimento Futuro e Recebimento de Simples Remessa vêm em pares com o mesmo valor. Somar as duas conta duas vezes.

## Ao terminar um mês

- Confira o cabeçalho (produtor e fazenda) e as datas usadas.
- Conte arquivos por pasta `AAAA-MM`, separe PDF e imagem, e confira se o início do arquivo é PDF ou imagem de verdade.
- Gere o CSV sem arquivo, com valor em todas as linhas.
- Não versione PDF, imagem nem CSV de lançamento. Não commite sem pedido explícito.
