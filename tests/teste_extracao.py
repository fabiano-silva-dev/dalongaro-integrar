#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de teste para verificar a extração de dados
Ajustado para estrutura de duas colunas
"""

from extrair_empresas import extrair_dados_empresa

# Texto de exemplo fornecido pelo usuário (estrutura de duas colunas)
texto_exemplo = """Código: 1 Data da inscrição: 10/12/2004
Apelido: VERONTINO Insc. Suframa:
Nome: VERONTINO DA ROSA E SILVA Insc. Sub. Trib.:
Razão social: VERONTINO DA ROSA E SILVA Natureza Jurídica: Empresário (Individual)
Nome fantasia: PRESTADORA DE SERVICOS SILVA Contador: CLEBER ALVES DA SILVA
Tipo de endereço: Início atividades: 10/12/2004
Endereço: RUA VITORIO DE DAVID Cliente desde: 01/01/2005
Número: 1378 Situação: Inativa
Bairro: SANTO ANTONIO Data da situação:
Complemento: Motivo: Outras
Município: FAXINAL DO SOTURNO Duração do contrato: Indeterminado
UF: RS Data:
CEP: 97220000 Foro Comarca:
Caixa postal: CNAE 2.3: 4330-4/04
País: BRASIL CAE:
Telefone: (55) 02632548 Ramo de atividade: Serviços de pintura em edificações em geral.
Fax: Responsável Legal: VERONTINO DA ROSA E SILVA
E-mail: clrosso@yahoo.com.br Outro registro: Não
Página na internet: Registro:
CNPJ/CPF/CEI/CAEPF: 07.148.155/0001-19 Data de registro:
Insc. estadual: Capital social:
Insc. municipal: Data:
Insc. Junta Comercial: 43106714495
Sistema licenciado para VALDECIR DAL ONGARO"""

def testar_extracao():
    """
    Testa a extração dos dados da empresa de exemplo
    """
    print("Testando extração de dados da empresa (estrutura de duas colunas)...")
    print("=" * 70)
    
    dados = extrair_dados_empresa(texto_exemplo)
    
    print("Dados extraídos organizados por colunas:")
    print("\n" + "=" * 70)
    
    # Coluna Esquerda
    print("📋 COLUNA ESQUERDA:")
    print("-" * 40)
    campos_esquerda = [
        'codigo', 'apelido', 'nome', 'razao_social', 'nome_fantasia',
        'tipo_endereco', 'endereco', 'numero', 'bairro', 'complemento',
        'municipio', 'uf', 'cep', 'caixa_postal', 'pais',
        'telefone', 'fax', 'email', 'pagina_internet',
        'cnpj_cpf', 'inscricao_estadual', 'inscricao_municipal', 'inscricao_junta_comercial',
        'inscricao_suframa', 'inscricao_sub_trib'
    ]
    
    for campo in campos_esquerda:
        if dados.get(campo):
            print(f"✓ {campo}: {dados[campo]}")
    
    print("\n" + "=" * 70)
    
    # Coluna Direita
    print("📋 COLUNA DIREITA:")
    print("-" * 40)
    campos_direita = [
        'data_inscricao', 'natureza_juridica', 'contador', 'inicio_atividades',
        'cliente_desde', 'situacao', 'data_situacao', 'motivo',
        'duracao_contrato', 'data_contrato', 'foro_comarca',
        'cnae', 'cae', 'ramo_atividade', 'responsavel_legal',
        'outro_registro', 'registro', 'data_registro',
        'capital_social', 'data_capital', 'sistema_licenciado'
    ]
    
    for campo in campos_direita:
        if dados.get(campo):
            print(f"✓ {campo}: {dados[campo]}")
    
    print("\n" + "=" * 70)
    
    # Estatísticas
    total_campos = len([v for v in dados.values() if v])
    campos_esquerda_preenchidos = len([dados.get(c) for c in campos_esquerda if dados.get(c)])
    campos_direita_preenchidos = len([dados.get(c) for c in campos_direita if dados.get(c)])
    
    print(f"📊 ESTATÍSTICAS:")
    print(f"   Total de campos extraídos: {total_campos}")
    print(f"   Coluna esquerda: {campos_esquerda_preenchidos} campos")
    print(f"   Coluna direita: {campos_direita_preenchidos} campos")
    
    # Verificar campos importantes
    print("\n🔍 VERIFICAÇÃO DE CAMPOS IMPORTANTES:")
    campos_importantes = ['codigo', 'nome', 'cnpj_cpf', 'email', 'telefone', 'endereco', 'municipio', 'uf']
    for campo in campos_importantes:
        status = "✓" if dados.get(campo) else "✗"
        print(f"{status} {campo}: {dados.get(campo, 'N/A')}")

if __name__ == "__main__":
    testar_extracao()
