# Sistema de Análise de Produtividade - ClienteTempo Gasto

## 📋 Descrição

Este sistema foi desenvolvido para extrair, processar e analisar dados de produtividade a partir do arquivo `ClienteTempo Gasto.xls`, gerando relatórios estruturados e análises detalhadas para tomada de decisão.

## 🎯 Objetivos

- Converter arquivo Excel (.xls) para formato CSV estruturado
- Extrair dados de tempo gasto por cliente, sistema e usuário
- Gerar múltiplos tipos de relatórios para análise
- Fornecer insights sobre produtividade e eficiência operacional
- Criar base de dados estruturada para futuras análises

## 📁 Estrutura de Arquivos

```
dalongaro-integrar/
├── produtividade/
│   ├── ClienteTempo Gasto.xls          # Arquivo original
│   ├── ClienteTempo Gasto.csv          # Arquivo convertido
│   ├── processados/                    # CSVs por aba (conversão multi-aba)
│   └── relatorios/
│       ├── basicos/                    # Relatórios padrão do pipeline
│       │   ├── relatorio_por_cliente.csv
│       │   ├── relatorio_por_sistema.csv
│       │   ├── relatorio_por_usuario.csv
│       │   └── relatorio_por_data.csv
│       ├── avancados/                  # Análises de eficiência
│       │   ├── eficiencia_por_usuario.csv
│       │   ├── eficiencia_por_sistema.csv
│       │   ├── produtividade_por_cliente.csv
│       │   └── analise_temporal.csv
│       ├── por_periodo/                # Relatórios por mês/fonte
│       │   ├── 2025-08/
│       │   └── cliente-tempo-gasto/
│       └── exemplos/                   # Modelos de referência
├── dados_atividades_estruturados.csv   # Dados principais estruturados
├── relatorio_executivo_produtividade.txt
├── saida/_ultimo/                      # Saídas temporárias
├── _arquivo/old/                       # Histórico e versões antigas
└── scripts/ (na raiz, reorganização na Fase 2)
    ├── converter_xls_para_csv.py
    ├── processar_dados_produtividade.py
    ├── gerar_relatorios_avancados.py
    └── relatorio_executivo_produtividade.py
```

## 🚀 Como Usar

### 1. Conversão do Arquivo Excel

```bash
python converter_xls_para_csv.py
```

**O que faz:**
- Converte o arquivo `.xls` para `.csv` usando LibreOffice
- Tenta diferentes métodos de leitura para compatibilidade
- Gera arquivo CSV limpo e estruturado

### 2. Processamento dos Dados

```bash
python processar_dados_produtividade.py
```

**O que faz:**
- Extrai e estrutura os dados do CSV
- Identifica clientes, sistemas, usuários e atividades
- Gera relatórios básicos por categoria
- Cria arquivo de dados estruturados

### 3. Relatórios Avançados

```bash
python gerar_relatorios_avancados.py
```

**O que faz:**
- Analisa eficiência por usuário e sistema
- Calcula métricas de produtividade
- Gera análises temporais detalhadas
- Cria relatórios de performance

### 4. Relatório Executivo

```bash
python relatorio_executivo_produtividade.py
```

**O que faz:**
- Consolida todos os relatórios
- Gera visão executiva da produtividade
- Fornece recomendações estratégicas
- Salva relatório em arquivo de texto

## 📊 Tipos de Relatórios Gerados

### Relatórios Básicos
- **Por Cliente**: Atividades e sistemas utilizados por cliente
- **Por Sistema**: Uso e distribuição por sistema
- **Por Usuário**: Produtividade e escopo por usuário
- **Por Data**: Análise temporal das atividades

### Relatórios Avançados
- **Eficiência por Usuário**: Tempo médio por atividade
- **Eficiência por Sistema**: Performance por sistema
- **Produtividade por Cliente**: Ranking de clientes
- **Análise Temporal**: Tendências e padrões temporais

### Relatório Executivo
- Resumo consolidado de todos os dados
- Principais métricas de produtividade
- Análise de eficiência operacional
- Recomendações estratégicas

## 🔍 Estrutura dos Dados

### Dados de Atividades
- `codigo_cliente`: Código identificador do cliente
- `nome_cliente`: Nome do cliente
- `sistema`: Sistema utilizado (Folha, Contabilidade, Escrita, etc.)
- `usuario`: Usuário responsável pela atividade
- `data`: Data da atividade
- `tempo_gasto`: Tempo gasto na atividade (HH:MM:SS)

### Sistemas Identificados
- **Folha**: Sistema de folha de pagamento
- **Contabilidade**: Sistema contábil
- **Escrita**: Sistema de escrituração
- **Patrimonio**: Sistema patrimonial
- **Atualizar**: Sistema de atualizações
- **Registro**: Sistema de registros

## 📈 Métricas Calculadas

### Eficiência
- Tempo médio por atividade
- Atividades por hora
- Distribuição de carga de trabalho

### Produtividade
- Total de atividades por usuário
- Clientes atendidos por usuário
- Sistemas utilizados por usuário

### Análise Temporal
- Volume de trabalho por dia
- Padrões de produtividade
- Tendências semanais/mensais

## 💡 Insights Principais

### Usuários Mais Eficientes
- **VIVIANE**: 5.54 min/atividade
- **GERENTE**: 7.07 min/atividade
- **PAMELA**: 8.66 min/atividade

### Sistemas Mais Utilizados
- **Folha**: 591 atividades (45.8%)
- **Escrita**: 364 atividades (28.2%)
- **Contabilidade**: 322 atividades (25.0%)

### Top Clientes
- **POSTO PILECCO LTDA**: 44h 26min
- **SPECIATTA CONGELADOS LTDA**: 34h 53min
- **G. MANFIO & CIA. LTDA**: 24h 24min

## 🛠️ Requisitos Técnicos

### Dependências Python
```bash
pip install pandas openpyxl xlrd numpy
```

### Software do Sistema
- **LibreOffice**: Para conversão de arquivos Excel
- **Python 3.7+**: Para execução dos scripts

### Compatibilidade
- Arquivos Excel (.xls, .xlsx)
- Codificações: UTF-8, Latin1, ISO-8859-1, CP1252
- Sistemas: Linux, Windows, macOS

## 🔄 Fluxo de Processamento

```
Arquivo .xls → Conversão CSV → Extração Dados → Estruturação → Análise → Relatórios
     ↓              ↓              ↓              ↓           ↓         ↓
  LibreOffice   Pandas CSV    Regex/Parse   DataFrame   GroupBy   CSV/Text
```

## 📝 Personalização

### Adicionar Novos Sistemas
Edite a lista `sistemas_conhecidos` no script `processar_dados_produtividade.py`

### Adicionar Novos Usuários
Edite a lista `usuarios_conhecidos` no script `processar_dados_produtividade.py`

### Modificar Relatórios
Edite as funções de geração de relatórios nos scripts correspondentes

## 🚨 Tratamento de Erros

- **Codificação**: Tenta múltiplas codificações automaticamente
- **Formato Excel**: Usa LibreOffice para conversão robusta
- **Dados Corrompidos**: Filtra e limpa dados inválidos
- **Logs**: Registra erros e sucessos durante o processamento

## 📞 Suporte

Para dúvidas ou problemas:
1. Verifique os logs de erro nos scripts
2. Confirme a estrutura do arquivo Excel original
3. Verifique as dependências Python instaladas
4. Confirme a presença do LibreOffice no sistema

## 🔮 Próximas Funcionalidades

- [ ] Gráficos e visualizações
- [ ] Dashboard web interativo
- [ ] Exportação para Excel formatado
- [ ] Análise de tendências sazonais
- [ ] Comparativo entre períodos
- [ ] Alertas de produtividade

---

**Desenvolvido para análise de produtividade empresarial**
**Versão**: 1.0.0
**Data**: Agosto 2025











