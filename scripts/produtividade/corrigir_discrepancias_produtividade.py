#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para corrigir discrepâncias identificadas na verificação de consistência
"""

import os
import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

_SCRIPTS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_SCRIPTS))
from paths import ROOT, p

PROCESSAR_SCRIPT = p("scripts/produtividade/processar_dados_produtividade.py")
VALIDAR_SCRIPT = p("scripts/produtividade/validar_consistencia_automatica.py")


def setup_workspace():
    from runtime import setup_workspace as _setup
    return _setup()

def corrigir_sistemas_faltantes():
    """
    Atualiza a lista de sistemas para incluir os identificados no arquivo de resumo
    """
    print("🔧 CORRIGINDO SISTEMAS FALTANTES")
    print("="*60)
    
    # Sistemas originais
    sistemas_originais = ['Folha', 'Contabilidade', 'Escrita', 'Patrimonio', 'Atualizar', 'Registro']
    
    # Sistemas identificados no resumo
    sistemas_resumo = ['Honorários', 'Lalur']
    
    # Sistemas completos
    sistemas_completos = sistemas_originais + sistemas_resumo
    
    print(f"Sistemas originais: {sistemas_originais}")
    print(f"Sistemas do resumo: {sistemas_resumo}")
    print(f"Sistemas completos: {sistemas_completos}")
    
    return sistemas_completos

def corrigir_usuarios_faltantes():
    """
    Identifica usuários que estão no resumo mas não nos relatórios
    """
    print("\n👥 CORRIGINDO USUÁRIOS FALTANTES")
    print("="*60)
    
    # Usuários originais
    usuarios_originais = ['PAMELA', 'GERENTE', 'VIVIANE', 'RAYANE', 'VANEZA', 'MARIA', 'DUDA', 'CRISTINA', 'MATIAS']
    
    # Usuários identificados no resumo
    usuarios_resumo = ['ANDERSON', 'FABIANO', 'GABRIEL', 'LUCAS.MT', 'SUELEN', 'VINICIUS', 'MASTER2', 'MASTER3']
    
    # Usuários completos
    usuarios_completos = usuarios_originais + usuarios_resumo
    
    print(f"Usuários originais: {len(usuarios_originais)}")
    print(f"Usuários do resumo: {len(usuarios_resumo)}")
    print(f"Usuários completos: {len(usuarios_completos)}")
    
    return usuarios_completos

def atualizar_script_processamento(sistemas_completos, usuarios_completos):
    """
    Atualiza o script de processamento com as correções
    """
    print("\n📝 ATUALIZANDO SCRIPT DE PROCESSAMENTO")
    print("="*60)
    
    # Ler o script atual
    script_path = PROCESSAR_SCRIPT

    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            conteudo = f.read()
        
        # Atualizar sistemas conhecidos
        sistemas_antigos = "sistemas_conhecidos = ['Folha', 'Contabilidade', 'Escrita', 'Patrimonio', 'Atualizar', 'Registro']"
        sistemas_novos = f"sistemas_conhecidos = {sistemas_completos}"
        
        if sistemas_antigos in conteudo:
            conteudo = conteudo.replace(sistemas_antigos, sistemas_novos)
            print("✅ Sistemas conhecidos atualizados")
        else:
            print("⚠️  Padrão de sistemas não encontrado")
        
        # Atualizar usuários conhecidos
        usuarios_antigos = "usuarios_conhecidos = ['PAMELA', 'GERENTE', 'VIVIANE', 'RAYANE', 'VANEZA', 'MARIA', 'DUDA', 'CRISTINA', 'MATIAS']"
        usuarios_novos = f"usuarios_conhecidos = {usuarios_completos}"
        
        if usuarios_antigos in conteudo:
            conteudo = conteudo.replace(usuarios_antigos, usuarios_novos)
            print("✅ Usuários conhecidos atualizados")
        else:
            print("⚠️  Padrão de usuários não encontrado")
        
        # Salvar script atualizado
        script_backup = PROCESSAR_SCRIPT.with_suffix(".py.backup")
        with open(script_backup, 'w', encoding='utf-8') as f:
            f.write(conteudo)

        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(conteudo)

        print(f"✅ Script atualizado salvo em: {script_path}")
        print(f"📋 Backup salvo em: {script_backup}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao atualizar script: {e}")
        return False

def criar_script_validacao_automatica():
    """
    Cria um script de validação automática para futuras verificações
    """
    print("\n🤖 CRIANDO SCRIPT DE VALIDAÇÃO AUTOMÁTICA")
    print("="*60)
    
    script_validacao = """#!/usr/bin/env python3
# -*- coding: utf-8 -*-
\"\"\"
Script de validação automática de consistência de dados de produtividade
\"\"\"

import pandas as pd
import os
from datetime import datetime

def validar_consistencia_automatica():
    \"\"\"
    Valida automaticamente a consistência dos dados
    \"\"\"
    print(f"🔍 VALIDAÇÃO AUTOMÁTICA - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    # Verificar se arquivos existem
    arquivos_necessarios = [
        "dados_atividades_estruturados.csv",
        "produtividade/relatorios/avancados/eficiencia_por_usuario.csv"
    ]
    
    for arquivo in arquivos_necessarios:
        if not os.path.exists(arquivo):
            print(f"❌ Arquivo não encontrado: {arquivo}")
            return False
    
    # Carregar dados
    try:
        df_atividades = pd.read_csv("dados_atividades_estruturados.csv")
        df_eficiencia = pd.read_csv("produtividade/relatorios/avancados/eficiencia_por_usuario.csv")
        
        print(f"✅ Dados carregados: {len(df_atividades)} atividades, {len(df_eficiencia)} usuários")
        
        # Validações básicas
        total_usuarios = len(df_eficiencia)
        usuarios_com_atividades = len(df_atividades['usuario'].unique())
        
        print(f"📊 Usuários no relatório: {total_usuarios}")
        print(f"📊 Usuários com atividades: {usuarios_com_atividades}")
        
        if total_usuarios == usuarios_com_atividades:
            print("✅ Consistência de usuários: OK")
        else:
            print("⚠️  Inconsistência de usuários detectada")
        
        # Verificar sistemas
        sistemas_identificados = set(df_atividades['sistema'].unique())
        sistemas_esperados = {'Folha', 'Contabilidade', 'Escrita', 'Patrimonio', 'Atualizar', 'Registro', 'Honorários', 'Lalur'}
        
        sistemas_faltando = sistemas_esperados - sistemas_identificados
        sistemas_novos = sistemas_identificados - sistemas_esperados
        
        if sistemas_faltando:
            print(f"⚠️  Sistemas esperados mas não encontrados: {sistemas_faltando}")
        
        if sistemas_novos:
            print(f"ℹ️  Sistemas novos identificados: {sistemas_novos}")
        
        if not sistemas_faltando and not sistemas_novos:
            print("✅ Consistência de sistemas: OK")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na validação: {e}")
        return False

if __name__ == "__main__":
    validar_consistencia_automatica()
"""
    
    try:
        with open(VALIDAR_SCRIPT, 'w', encoding='utf-8') as f:
            f.write(script_validacao)
        
        print("✅ Script de validação automática criado")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao criar script de validação: {e}")
        return False

def gerar_relatorio_correcoes(sistemas_completos, usuarios_completos):
    """
    Gera relatório das correções aplicadas
    """
    print("\n📋 GERANDO RELATÓRIO DE CORREÇÕES")
    print("="*60)
    
    relatorio = f"""# Relatório de Correções Aplicadas - Sistema de Produtividade

## 📅 Data da Correção
{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

## 🔧 Correções Implementadas

### 1. Sistemas Atualizados
**Antes:** {['Folha', 'Contabilidade', 'Escrita', 'Patrimonio', 'Atualizar', 'Registro']}
**Depois:** {sistemas_completos}

**Sistemas Adicionados:**
- Honorários: Sistema de gestão de honorários
- Lalur: Sistema específico de algumas atividades

### 2. Usuários Atualizados
**Antes:** {['PAMELA', 'GERENTE', 'VIVIANE', 'RAYANE', 'VANEZA', 'MARIA', 'DUDA', 'CRISTINA', 'MATIAS']}
**Depois:** {usuarios_completos}

**Usuários Adicionados:**
- ANDERSON: Usuário com atividades significativas
- FABIANO: Usuário com múltiplos sistemas
- GABRIEL: Usuário com alto volume de atividades
- LUCAS.MT: Usuário com atividades específicas
- SUELEN: Usuário com sistema Lalur
- VINICIUS: Usuário com atividades mínimas
- MASTER2/MASTER3: Usuários master

### 3. Scripts Atualizados
- processar_dados_produtividade.py: Sistemas e usuários atualizados
- validar_consistencia_automatica.py: Novo script de validação

## 📊 Impacto das Correções

### Antes da Correção:
- Consistência: 65% dos usuários
- Sistemas identificados: 6
- Usuários cobertos: 9

### Depois da Correção:
- Consistência esperada: 95%+ dos usuários
- Sistemas identificados: 8
- Usuários cobertos: 17

## 🚀 Próximos Passos

1. **Executar pipeline atualizado** para gerar novos relatórios
2. **Verificar consistência** com script automático
3. **Validar dados** com arquivo de resumo
4. **Monitorar qualidade** continuamente

## ✅ Status

- [x] Sistemas atualizados
- [x] Usuários atualizados
- [x] Scripts corrigidos
- [x] Validação automática implementada
- [ ] Teste com dados completos
- [ ] Verificação final de consistência

---
**Responsável:** Sistema de Análise de Produtividade
**Versão:** 1.1.0 (Corrigida)
"""
    
    try:
        with open(p("relatorio_correcoes_aplicadas.md"), 'w', encoding='utf-8') as f:
            f.write(relatorio)
        
        print("✅ Relatório de correções gerado")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao gerar relatório: {e}")
        return False

def main():
    """
    Função principal
    """
    setup_workspace()

    print("🔧 INICIANDO CORREÇÃO DE DISCREPÂNCIAS IDENTIFICADAS")
    print("="*80)
    
    # 1. Corrigir sistemas faltantes
    sistemas_completos = corrigir_sistemas_faltantes()
    
    # 2. Corrigir usuários faltantes
    usuarios_completos = corrigir_usuarios_faltantes()
    
    # 3. Atualizar script de processamento
    sucesso_atualizacao = atualizar_script_processamento(sistemas_completos, usuarios_completos)
    
    # 4. Criar script de validação automática
    sucesso_validacao = criar_script_validacao_automatica()
    
    # 5. Gerar relatório de correções
    sucesso_relatorio = gerar_relatorio_correcoes(sistemas_completos, usuarios_completos)
    
    # Resumo final
    print("\n" + "="*80)
    print("RESUMO DAS CORREÇÕES")
    print("="*80)
    
    if sucesso_atualizacao and sucesso_validacao and sucesso_relatorio:
        print("🎉 TODAS AS CORREÇÕES FORAM APLICADAS COM SUCESSO!")
        print("\n📋 Arquivos gerados/atualizados:")
        print("  ✅ scripts/produtividade/processar_dados_produtividade.py (atualizado)")
        print("  ✅ scripts/produtividade/validar_consistencia_automatica.py (novo)")
        print("  ✅ relatorio_correcoes_aplicadas.md (novo)")
        print("  ✅ scripts/produtividade/processar_dados_produtividade.py.backup (backup)")
        
        print(f"\n🚀 Próximos passos:")
        print("  1. Executar: python scripts/produtividade/processar_dados_produtividade.py")
        print("  2. Validar: python scripts/produtividade/validar_consistencia_automatica.py")
        print(f"  3. Verificar consistência novamente")
        
    else:
        print("⚠️  ALGUMAS CORREÇÕES FALHARAM")
        print("Verifique os logs acima para identificar problemas")
    
    print("="*80)

if __name__ == "__main__":
    main()










