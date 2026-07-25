# Dalongaro Integrar

Workspace de automação e dados do escritório de contabilidade **Dalongaro**.

## Início rápido

```bash
pip install -r requirements.txt
python run_pipeline.py                    # pipeline de produtividade
python scripts/cadastro/extrair_empresas.py referencia/cadastro/Empresas.pdf
```

Execute os comandos a partir da **raiz** deste repositório.

## Estrutura do workspace

```
dalongaro-integrar/
├── clientes/           # Dados por cliente (nome-codigo/YYYY-MM/)
├── produtividade/      # Relatórios Domínio (tempo por cliente/usuário)
├── scripts/            # Automações Python por domínio
├── tests/              # Scripts de teste
├── docs/               # Documentação e relatórios em Markdown
├── referencia/         # Layouts, leiautes e cadastros de referência
├── saida/              # Saídas temporárias
├── _arquivo/           # Histórico (cold storage)
└── run_pipeline.py     # Atalho para o pipeline de produtividade
```

## Clientes

| Pasta | Código Domínio | Observação |
|-------|----------------|------------|
| `clientes/credit-578/` | 578 | CCB, fiscal, balancetes |
| `clientes/carlos-668/` | 668 | Mensal por `YYYY-MM/` |
| `clientes/claudio-666/` | 666 | |
| `clientes/fabiane-667/` | 667 | |
| `clientes/luciano-664/` | 664 | |
| `clientes/grupo-bianchi/` | — | Família Bianchi (membros sem código próprio) |
| `clientes/posto-pilecco/` | — | Conciliação Sicredi |
| `clientes/limarin-208/` | 208 | |
| `clientes/_indice/clientes.csv` | — | Cadastro mestre |

Mapa completo de renomeações: `clientes/_indice/mapa_pastas.txt`  
Grupo Bianchi: `clientes/_indice/grupo_bianchi.md`

## Scripts principais

| Domínio | Pasta | Exemplo |
|---------|-------|---------|
| Produtividade | `scripts/produtividade/` | `python run_pipeline.py` |
| Cadastro | `scripts/cadastro/` | `extrair_empresas.py`, `gerar_csv_listagem_terceiros.py` |
| Contábil | `scripts/contabil/` | balancete, Domínio, SPED |
| Fiscal | `scripts/fiscal/` | Credit CCB, extratos, recebimentos |
| Bancário | `scripts/bancario/` | Sicredi, conciliação |
| Utilitários | `scripts/utilitarios/` | scripts de reorganização |

## Comandos frequentes

```bash
# Produtividade mensal
python run_pipeline.py

# CCB Credit — período específico
python scripts/fiscal/credit/gerar_planilha_credit_CCB_layout_saidas.py \
  clientes/credit-578/ccb/2026-04/

# Conciliação Sicredi (Posto Pilecco)
python scripts/bancario/comparar_sicredi_razao.py

# Balancete/DRE a partir de SPED
python scripts/contabil/balancete/gerar_balancete_dre.py \
  clientes/carlos-668/sped_diario00668.txt \
  --saida clientes/carlos-668/relatorios_contabeis/

# Testes
python tests/teste_extracao.py
```

## Documentação

| Arquivo | Conteúdo |
|---------|----------|
| [docs/README_PRODUTIVIDADE.md](docs/README_PRODUTIVIDADE.md) | Sistema de análise de produtividade |
| [docs/README_EXCEL.md](docs/README_EXCEL.md) | Extração de contas analíticas |
| [docs/README_enriquecimento.md](docs/README_enriquecimento.md) | Enriquecimento de dados Domínio |
| [docs/mapa_fase4.txt](docs/mapa_fase4.txt) | Mapa da reorganização Fase 4 |

## Referência

- `referencia/layout_balancete_exemplo.xlsx` — modelo de balancete
- `referencia/Leiaute - Registros.pdf` — leiaute de registros
- `referencia/cadastro/Empresas.pdf` — cadastro para extração
- `referencia/cadastro/listagem_terceiros.csv` — listagem de terceiros

## Convenções

- **Clientes:** `nome-codigo` em minúsculas com hífen (`carlos-668`)
- **Períodos:** `YYYY-MM` nas pastas mensais
- **Saídas geradas:** `clientes/{nome}/saida/` ou `produtividade/relatorios/`
- **Execução:** sempre da raiz do workspace

---

Fabiano — 2025/2026
