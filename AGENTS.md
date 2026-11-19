# Dalongaro Integrar

Workspace da consultoria do escritório de contabilidade Dalongaro. O trabalho é achar o documento, conferir o número e entregar só o que foi pedido. Responder em português, direto, começando pelo resultado.

Quem opera é o Fabiano. Ele trabalha no código: script, planilha, PDF e pasta do cliente. Não explicar o óbvio nem abrir com o plano.

## Como responder

- Confirme o cliente, o código do Domínio e o período antes de calcular ou baixar.
- Não invente nota, saldo, chave ou valor. Se a conta não fecha, diga a diferença.
- Escreva o número que a multiplicação fecha. Não copie erro de centavos de um docx do cliente.
- Na resposta, não repita senha, token nem conteúdo de certificado.
- Commit e push só quando o pedido for explícito. Não versionar `.pfx`, `.ofx`, certificado, XML de nota nem CSV de lançamento baixado.
- Peça jurídica: minuta, não protocolada, com `[Local]`, `[data]` e `[Advogado(a) responsável – OAB]`. Juntar o documento pedido, nada além dele. Não anexar resumo interno com saldo bancário, recado de pessoa ou estratégia de cobrança.
- Documento interno sensível pode ficar no Git. Não vai para o Drive compartilhado nem para a peça.

## Onde olhar

| Precisa de | Vá em |
|---|---|
| Cliente | `clientes/nome-codigo/`. Índice: `clientes/_indice/clientes.csv` e `mapa_pastas.txt` |
| Grupo Bianchi | `clientes/_indice/grupo_bianchi.md` |
| Produtividade do escritório | `python run_pipeline.py` e `docs/README_PRODUTIVIDADE.md` |
| Script | `scripts/{produtividade,cadastro,contabil,fiscal,bancario,utilitarios}/` |
| Layout e cadastro | `referencia/` |
| Download Connectere do Bianchi | `documentos-connectere-Bianchi-RJ/PROMPT.md` e `receptor.py` |
| Compras já baixadas, 01/01/2026 a 13/10/2026 | `/ico/fabiano/ft/integrar/backups/`, não copiar de novo |

Pastas de cliente: `nome-codigo` em minúsculas (`luciano-664`). Período: `YYYY-MM`. Rodar comando na raiz do repositório.

## Atividades

1. **Connectere (+Gestão).** Baixar DANFE e anexo de compra ou venda, por fazenda PJ e por mês. Conferir produtor e fazenda no cabeçalho. DANFE é `a[href*="danfe.pdf"]`. Romaneio de classificação: `/notas_fiscais/romaneio_carregamento/{id}.pdf?l=1`. Não usar `notas_fiscais/{id}.pdf?l=1`. Não baixar XML. Receptor em `127.0.0.1:8765`, um destino por fazenda. O procedimento completo está no `PROMPT.md`.
2. **Domínio e SPED.** Balancete, DRE, razão e filtro de contas a partir do arquivo exportado. Script em `scripts/contabil/`. O arquivo de importação não se soma de novo à ECD do mesmo período.
3. **Fiscal.** Credit (código 578): CCB, entradas, recebimentos e boletos em `scripts/fiscal/credit/`. Extratos Grafeno e Sicoob em `scripts/fiscal/extratos/`.
4. **Bancário.** Conciliação Sicredi do Posto Pilecco: `scripts/bancario/comparar_sicredi_razao.py`. OFX não entra no Git.
5. **Produtividade.** `ClienteTempo Gasto.xls` vira relatório por cliente, usuário e sistema. `python run_pipeline.py`.
6. **Peça e Drive.** Montar a memória, subir só o conjunto da juntada e colocar o link da pasta em cada item. Remote rclone `relatorios`. Caminho por nome falha: usar `--drive-root-folder-id`.

## Acessos

Não colar estes dados em peça, e-mail ou resposta de chat.

### Connectere (+Gestão)

Sistema de gestão de fazendas. O host `g3.connectere.agr.br` é o mesmo sistema. O filtro é a sessão do cabeçalho, não o domínio.

- Login: https://maisgestao.connectere.agr.br/usuarios/sign_in
- Usuário: dalongarointegrar@gmail.com
- Senha: mantida fora do repositório
- Se a página disser “Acesse a sua conta”, a sessão caiu.

| Produtor | Sessão | Fazenda | Empresa | Não usar |
|---|---|---|---|---|
| Luciano Bianchi | `/contexto?pid=547` | PJ - Faz Luciano- MT | `/empresas/1857` | PF - Luciano- MT (eid 1018) |
| Carlos Bianchi | `/contexto?pid=833` | PJ - Carlos | `/empresas/1860` | PF - Carlos (eid 1859) |
| Claudio Bianchi | `/contexto?pid=516` | PJ - Faz Bianchi | `/empresas/1854` | PF - Faz Bianchi (eid 949) |

Ao trocar de produtor, o sistema pode abrir a fazenda PF. Voltar para a PJ antes de listar. Fabiane sai do Claudio pelo endereço remetente `304343`. Elenise sai do Carlos pelo endereço `304372`.

### ContaGo

Ainda sem endereço, usuário e senha neste repositório. Quando houver, gravar aqui neste formato:

- Login:
- Usuário:
- Senha:

### Drive da consultoria

Remote rclone `relatorios`, pasta Consultoria-Dalongaro. Não há login de usuário neste arquivo. Operar com `--drive-root-folder-id`. O remote `backup03` é outro Drive, de backup de servidor, e não serve para a juntada.

### Domínio, Sicredi, Sicoob e Grafeno

Não há login web guardado. O trabalho parte do arquivo exportado (TXT, XLS, PDF, OFX) já colocado na pasta do cliente.
