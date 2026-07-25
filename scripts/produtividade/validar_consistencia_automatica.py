#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de validação automática de consistência de dados de produtividade
"""

import pandas as pd
import os
from datetime import datetime

def validar_consistencia_automatica():
    """
    Valida automaticamente a consistência dos dados
    """
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
