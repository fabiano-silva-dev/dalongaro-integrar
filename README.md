# Importador Domínio Sistemas

Script Python para importar arquivos no layout da Domínio Sistemas (Lançamentos Contábeis em Lote) e gerar arquivos CSV.

## Funcionalidades

- Parse de arquivos no layout da Domínio Sistemas
- Suporte a todos os tipos de registro (01, 02, 03, 04, 05, 99)
- Geração de CSV com dados estruturados
- Formatação automática de valores e datas
- Modo verboso para estatísticas
- Suporte a diferentes encodings

## Tipos de Registro Suportados

- **01**: Cabeçalho do Arquivo
- **02**: Dados do Lote
- **03**: Partidas dos Lançamentos Contábeis
- **04**: Rateios Gerenciais
- **05**: Rateios por Centro de Custos
- **99**: Finalizador do Arquivo

## Uso

### Uso Básico
```bash
python importar_dominio.py arquivo_entrada.txt
```

### Uso com Arquivo de Saída Personalizado
```bash
python importar_dominio.py arquivo_entrada.txt -o saida.csv
```

### Modo Verboso (com estatísticas)
```bash
python importar_dominio.py arquivo_entrada.txt -v
```

### Uso Completo
```bash
python importar_dominio.py arquivo_entrada.txt -o saida.csv -v
```

## Parâmetros

- `arquivo_entrada`: Caminho do arquivo de entrada no layout Domínio (obrigatório)
- `-o, --output`: Arquivo CSV de saída (padrão: output.csv)
- `-v, --verbose`: Modo verboso com estatísticas

## Exemplo de Saída CSV

O arquivo CSV gerado terá as seguintes colunas:

- `linha_arquivo`: Número da linha no arquivo original
- `tipo`: Tipo do registro (cabecalho, dados_lote, partidas_lancamentos, etc.)
- `codigo_empresa`: Código da empresa (registro 01)
- `cnpj_empresa`: CNPJ da empresa (registro 01)
- `data_inicial`: Data inicial dos lançamentos (registro 01)
- `data_final`: Data final dos lançamentos (registro 01)
- `tipo_nota`: Tipo de nota (registro 01)
- `sistema`: Sistema (registro 01)
- `codigo_sequencial`: Código sequencial (registros 02, 03)
- `tipo_lancamento`: Tipo do lançamento (registro 02)
- `data_lancamento`: Data do lançamento (registro 02)
- `usuario`: Usuário (registro 02)
- `conta_debito`: Conta débito (registros 03, 04)
- `conta_credito`: Conta crédito (registros 03, 04)
- `valor_lancamento`: Valor do lançamento (registros 03, 04, 05)
- `codigo_historico`: Código do histórico (registro 03)
- `historico_complemento`: Histórico complemento (registro 03)
- `codigo_filial_matriz`: Código da filial/matriz (registro 03)
- `sequencial`: Sequencial (registros 04, 05)
- `centro_custo_debito`: Centro de custo débito (registro 05)
- `centro_custo_credito`: Centro de custo crédito (registro 05)

## Formatação Automática

- **Valores**: Convertidos de string para float (formato 15,2)
- **Datas**: Mantidas no formato dd/mm/aaaa
- **Campos vazios**: Preenchidos com valores vazios no CSV

## Requisitos

- Python 3.6+
- Bibliotecas padrão (não requer instalação de dependências externas)

## Exemplo de Execução

```bash
$ python importar_dominio.py lancamentos.txt -v
Processando arquivo: lancamentos.txt
Total de registros processados: 150

Estatísticas por tipo de registro:
  cabecalho: 1
  dados_lote: 25
  partidas_lancamentos: 120
  finalizador: 1

CSV gerado com sucesso: output.csv
Total de linhas processadas: 150
```

## Tratamento de Erros

- Verifica se o arquivo de entrada existe
- Suporte a diferentes encodings (UTF-8 e Latin-1)
- Ignora linhas vazias
- Registros desconhecidos são marcados como "desconhecido" 