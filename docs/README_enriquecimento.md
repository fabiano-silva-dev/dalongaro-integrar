# Gerador de Planilha Domínio com Enriquecimento

Este script foi modificado para incluir funcionalidade de enriquecimento de dados através de um arquivo CSV adicional.

## Funcionalidades

- Processa arquivos no layout da Domínio Sistemas
- Extrai nome da empresa de históricos contendo "NF" ou "SERVIÇO TOMADO NESTA DATA"
- Enriquece dados com informações de um arquivo CSV adicional
- Gera CSV com dados combinados

## Uso

### Uso Básico (sem enriquecimento)
```bash
python gerar_planilha_dominio.py arquivo_dominio.txt
```

### Uso com Enriquecimento
```bash
python gerar_planilha_dominio.py arquivo_dominio.txt arquivo_enriquecimento.csv
```

### Uso Completo
```bash
python gerar_planilha_dominio.py arquivo_dominio.txt arquivo_enriquecimento.csv -o saida.csv -v
```

## Parâmetros

- `arquivo_entrada`: Arquivo no layout Domínio Sistemas (obrigatório)
- `arquivo_enriquecimento`: Arquivo CSV de enriquecimento (opcional, segundo parâmetro)
- `-o, --output`: Arquivo CSV de saída (opcional, padrão: nome_entrada-fiscal.csv)
- `-v, --verbose`: Modo verboso (opcional)

## Arquivo de Enriquecimento

O arquivo CSV de enriquecimento deve ter as seguintes colunas:

- `dados_principais_número`: Número da nota/documento
- `dados_principais_fornecedor/comprador`: Nome do fornecedor/comprador
- `financeiro_conta_financeira`: Conta financeira
- `itens_conta`: Conta de itens
- `item_descricao`: Descrição do item
- `itens_centro_resultado`: Centro de resultado

### Exemplo de arquivo de enriquecimento:
```csv
dados_principais_número;dados_principais_fornecedor/comprador;financeiro_conta_financeira;itens_conta;item_descricao;itens_centro_resultado
12345;EMPRESA ABC LTDA;1.1.01.001;2.1.01.001;SERVIÇOS DE CONSULTORIA;CR001
67890;FORNECEDOR XYZ S/A;1.1.01.002;2.1.01.002;MATERIAIS DE ESCRITÓRIO;CR002
```

## Lógica de Matching

O enriquecimento é feito através de duas condições:

1. **Número da nota**: Deve ser exatamente igual entre os arquivos
2. **Nome da empresa**: Comparação por similaridade de strings

### Comparação de Strings

A comparação de strings remove:
- Palavras comuns (LTDA, S/A, CIA, etc.)
- Caracteres especiais
- Números
- Palavras com menos de 3 caracteres

Exemplo:
- "EMPRESA ABC LTDA" vs "ABC EMPRESA" → Match ✓
- "FORNECEDOR XYZ S/A" vs "XYZ FORNECEDOR" → Match ✓
- "EMPRESA ABC LTDA" vs "FORNECEDOR DIFERENTE" → No Match ✗

## Arquivos Gerados

1. **arquivo-fiscal.csv**: CSV principal com dados do Domínio + enriquecimento
2. **arquivo-agrupado.csv**: CSV apenas com pares únicos Banco/Fornecedor

## Colunas do CSV de Saída

### Colunas Originais:
- codigo_sequencial
- tipo_lancamento
- data_lancamento
- usuario
- Banco (nome extraído do histórico)
- Fornecedor/Cliente
- valor_lancamento
- codigo_historico
- Histórico
- codigo_filial_matriz
- numero_nota

### Colunas de Enriquecimento (se aplicável):
- financeiro_conta_financeira
- itens_conta
- item_descricao
- itens_centro_resultado

## Testes

Execute os testes para verificar o funcionamento:

```bash
python teste_enriquecimento.py
```

Este teste demonstra:
- Limpeza de strings
- Comparação de similaridade
- Enriquecimento de dados 