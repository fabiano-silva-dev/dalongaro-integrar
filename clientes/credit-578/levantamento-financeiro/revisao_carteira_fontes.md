# Revisão da carteira CSG - integração de fontes existentes

## Correção da cobertura

Foram localizadas e processadas quatro pastas extraídas dentro do próprio cliente, em `_arquivo/zips/CCB CLIENTES MM.2026-.../CCB CLIENTES MM.2026/`. As fontes já estavam disponíveis; não eram documentos ausentes.

- Junho/2026: 35 PDFs; 34 CCBs; preço nas planilhas R$ 150.581,81; face R$ 261.002,35. Uma linha vazia do resumo corresponde à declaração direta nº 660592, Darciano Dalla Lana, com face R$ 25.500,00 e líquido R$ 22.923,28, recuperada do PDF denominado CCB.
- Julho/2026: 73 CCBs; preço R$ 224.521,99; face R$ 374.395,24.
- Agosto/2026: 59 CCBs; preço R$ 186.481,76; face R$ 293.503,43.
- Setembro/2026: 72 CCBs; preço R$ 249.723,89; face R$ 385.860,17.

Fontes monetárias: relatórios resumidos/fiscais/entradas e termos de endosso de cada mês nas pastas acima; conta de controle 1.1.2. Cada contrato e arquivo está identificado nas abas geradas.

## Validação e deduplicação

Os 239 PDFs novos foram integralmente lidos e todos contêm CSG/CNPJ 46.788.467/0001-49. As 238 CCBs novas identificam VIA CAPITAL CNPJ 48.632.754/0001-90; preço e face do termo de endosso conferem com as respectivas planilhas. O recebível direto identifica a CSG e a originadora Edson Ricardo de Moraes. Nenhum arquivo de outro cliente foi integrado.

A rotina elimina cópias binárias por SHA256 e repetições por documento; pacotes posteriores prevalecem com trilha de auditoria se houver versões. Nos conjuntos atuais não surgiram cópias de contrato que aumentassem o total.

A CCB 3887053, antes classificada como aquisição pendente por não ter linha no resumo, possui preço e data explícitos no termo de endosso. Foi recuperada desse documento original.

## Resultado da extração

- 1.116 CCBs com aquisição documental, sendo 621 em 2025 e 495 em 2026.
- 49 declarações de recebíveis diretos.
- 15.106 parcelas contratuais documentadas.
- Cobertura de aquisições: abril/2025 a setembro/2026.
- Saldo contábil atual R$ 6.801.908,85, integralmente conciliado às contas analíticas do balancete atualizado `balancetes/Balancete-ja-set-2026.pdf`, grupo 1.1.2.

## Achado documental adicional

Em 470 CCBs de 2025, o preço expresso no termo de endosso excede o valor financiado usado nas planilhas geradas. Diferença total de R$ 8.407,28. Ambos os valores agora aparecem lado a lado por contrato e em totais anuais separados. Em 2026 não há essa diferença. Os preços nos endossos totalizam R$ 2.223.561,08 em 2025 e R$ 1.710.427,85 em 2026; os valores da base de planilhas são R$ 2.215.153,80 e R$ 1.710.427,85, respectivamente. Fonte: PDFs, TERMO DE ENDOSSO/Quadro I; planilhas resumidas/fiscais individualizadas na aba Divergências carteira; conta 1.1.2.

Essa diferença não foi presumida como comissão, pagamento, perda nem ajuste automático dos custos/DRE. Deve ser confrontada com os lançamentos correspondentes, sem solicitar novamente documento contratual já localizado.

## Inspeção de possíveis posições abertas ou baixas

Foram inspecionados os nomes dos arquivos dos ZIPs de `_arquivo` e os cabeçalhos das planilhas extraídas. Foram encontrados contratos, resumos de aquisição, arquivos fiscais e relatórios de divergência de extração. Não foi identificado nesse conjunto relatório de posição aberta/paga por parcela nem nova base de baixas com contrato. A relação está na aba Revisão arquivo carteira.

`ConjuntoDeDados.zip` contém leiaute Domínio de Clientes/Fornecedores. Os dois ZIPs de planilhas contêm modelos de importação fiscal. Existe pacote de outubro/2026 com 64 PDFs, fora da data-base; contratos de outubro não comprovam fechamento contábil e não foram somados a setembro.

Os bancos foram informados como conciliados pelo cliente. Foram retirados pedidos genéricos de reconfirmação bancária. A pendência específica restante é ligar os registros de recebimento aos contratos/parcelas e obter a posição aberta no corte; calendário contratual não foi transformado em aging ou inadimplência presumida.

## Verificações

Extração integral executada duas vezes, esquema consistente em todas as abas, nomes com até 31 caracteres, 239 novos PDFs validados, 238 novas CCBs sem divergência de preço/face entre endosso e planilhas, documentos CCB sem dupla contagem, zero aquisições pendentes por ausência de resumo quando o endosso fornece os dados, soma analítica conciliada, e nenhuma célula de texto acima do limite do Excel.

Arquivo alterado: somente `mod_carteira.py`. Apoios de revisão: `revisao_carteira_resultado.json` e este registro. Outros módulos e relatórios finais serão regenerados pelo agente principal.
