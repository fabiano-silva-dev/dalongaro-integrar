# Razões anuais CSG — índice e controles

Fontes preservadas: `balancetes/Razão2022.xls` a `Razão2026.xls`; conversões em `qa/razoes_anuais/RazãoYYYY.xlsx`. São 62,051 eventos de conta, divididos em 15 fragmentos JSONL de até 5.000 eventos. Valores em centavos inteiros, histórico integral e origem por arquivo/SHA-256, aba/linha/folha. O ano da fonte é sempre explícito; classificação pertence à época do arquivo.

Os cinco arquivos têm totais finais de todas as contas, assinaturas ao final e menos de 65.536 linhas por aba, sem indício do corte observado no razão geral anterior. **Em 2024 há 479 linhas de implantação, envolvendo 477 contas, no lote23308 de31/12/2024, histórico SALDO FINAL EM31/12/2024.** Débitos e créditos desse lote são R$4.381.414,59 cada. Esses registros são preservados e marcados em `tipo_evento_cobertura`; não equivalem a fluxo econômico identificado nem demonstram as operações anteriores à implantação. Detalhes e contas afetadas constam de `qualidade.2024.implantacoes_saldos` no catálogo.

`catalogo.json` apresenta cobertura, presença da conta 642 e grupos, contagens/totais por ano/grupo/conta, metadados e QA. `conciliacao.json` compara abertura, débitos, créditos e final por código de conta aos balancetes oficiais de cada ano; preserva mudanças de classificação, contas sem correspondência e continuidade divergente. Contas com seções repetidas são sinalizadas sem soma automática. A comparação identifica diferenças; encerramentos, filiais e reimplantação não são ajustados por suposição.

`razoes_anuais.sqlite` tem tabelas `eventos`, `contas`, `secoes`, `secao_origem`, `fonte` e busca FTS5 `busca`. `eventos.secao_id` é local ao ano; `secao_global` liga à tabela `secoes`, cujo JSON inclui `ano_fonte` e `secao_id_local`. Cada evento tem `source`, `ano_fonte`, `id_local`, identificador global, conta/classificação/nome, data/lote, histórico completo/partes, contrapartida bruta/código, débitos/créditos/saldos em centavos, formato e sinal de saldo, e origem. Arrays ficam serializados em colunas `_json` no SQLite.

**Não somar esta base à ECD, aos razões de disponível/ativo/passivo ou ao razão geral parcial**, que são sobrepostos. Cada evento pertence a uma conta e não equivale a uma partida completa. Transferências internas e contrapartidas recíprocas continuam nos valores brutos. Campo Cta.C.Part. ausente fica nulo; não é preenchido por inferência. Não se somam saldos de datas distintas. A DRE anual e acumulada já está apurada.

Regerar, após converter os XLS em XLSX preservando as fontes:

```sh
cd clientes/credit-578/levantamento-financeiro
python mod_razoes.py
```

Requer Python 3, openpyxl e Poppler (`pdftotext`, para balancetes). `load(base,out)` usa cache por SHA-256 original+convertido+parser em `qa/razoes_anuais/cache` e memoização no processo; não é necessário repetir a extração para cada módulo. `build(base,out)` gera controles e este índice. Os argumentos opcionais são `--base` e `--out`. SQLite/JSONL são ignorados no Git; script, README, catálogo, conciliação e manifesto são versionáveis. Nenhum serviço remoto é acessado, nem são modificadas fontes/relatórios.

QA de gravação: origem = memória = SQLite = JSONL; totais D/C iguais; integridade SQLite `ok`; resultado **OK**. Verificações de saldo e totais de conta constam no catálogo por fonte. Datas globais não garantem cobertura de toda conta: consulte a linha correspondente no catálogo.
