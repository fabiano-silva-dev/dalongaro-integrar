#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para executar todo o pipeline de análise de produtividade
"""

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_SCRIPTS))
from paths import ROOT, ensure_root_cwd

def executar_comando(comando, descricao):
    """
    Executa um comando e registra o resultado
    """
    print(f"\n{'='*80}")
    print(f"EXECUTANDO: {descricao}")
    print(f"{'='*80}")
    print(f"Comando: {comando}")
    
    try:
        resultado = subprocess.run(
            comando,
            shell=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            cwd=ROOT,
        )
        
        if resultado.returncode == 0:
            print(f"✅ SUCESSO: {descricao}")
            if resultado.stdout:
                print("Saída:")
                print(resultado.stdout)
        else:
            print(f"❌ ERRO: {descricao}")
            if resultado.stderr:
                print("Erro:")
                print(resultado.stderr)
            return False
            
    except Exception as e:
        print(f"❌ EXCEÇÃO: {descricao} - {e}")
        return False
    
    return True

def verificar_arquivos_necessarios():
    """
    Verifica se os arquivos necessários existem
    """
    arquivos_necessarios = [
        "produtividade/ClienteTempo Gasto.xls"
    ]
    
    print("Verificando arquivos necessários...")
    
    for arquivo in arquivos_necessarios:
        if os.path.exists(arquivo):
            print(f"✅ {arquivo}")
        else:
            print(f"❌ {arquivo} - NÃO ENCONTRADO")
            return False
    
    return True

def verificar_dependencias():
    """
    Verifica se as dependências estão instaladas
    """
    dependencias = [
        ("python", "Python"),
        ("libreoffice", "LibreOffice"),
    ]
    
    print("Verificando dependências...")
    
    for comando, nome in dependencias:
        try:
            resultado = subprocess.run(f"which {comando}", shell=True, capture_output=True, text=True)
            if resultado.returncode == 0:
                print(f"✅ {nome}")
            else:
                print(f"❌ {nome} - NÃO ENCONTRADO")
                return False
        except:
            print(f"❌ {nome} - ERRO NA VERIFICAÇÃO")
            return False
    
    return True

def main():
    """
    Função principal que executa todo o pipeline
    """
    ensure_root_cwd()
    print("🚀 INICIANDO PIPELINE COMPLETO DE ANÁLISE DE PRODUTIVIDADE")
    print(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    # Verificar dependências
    if not verificar_dependencias():
        print("❌ Dependências não atendidas. Abortando execução.")
        sys.exit(1)
    
    # Verificar arquivos
    if not verificar_arquivos_necessarios():
        print("❌ Arquivos necessários não encontrados. Abortando execução.")
        sys.exit(1)
    
    # Pipeline de execução
    py = sys.executable
    etapas = [
        (f"{py} scripts/produtividade/converter_xls_para_csv.py", "Conversão Excel para CSV"),
        (f"{py} scripts/produtividade/processar_dados_produtividade.py", "Processamento dos dados"),
        (f"{py} scripts/produtividade/gerar_relatorios_avancados.py", "Geração de relatórios avançados"),
        (f"{py} scripts/produtividade/relatorio_executivo_produtividade.py", "Relatório executivo"),
    ]
    
    sucessos = 0
    total_etapas = len(etapas)
    
    for comando, descricao in etapas:
        if executar_comando(comando, descricao):
            sucessos += 1
        else:
            print(f"❌ Falha na etapa: {descricao}")
            print("Pipeline interrompido devido a erro.")
            break
    
    # Resumo final
    print(f"\n{'='*80}")
    print("RESUMO DO PIPELINE")
    print(f"{'='*80}")
    print(f"Etapas executadas com sucesso: {sucessos}/{total_etapas}")
    
    if sucessos == total_etapas:
        print("🎉 PIPELINE EXECUTADO COM SUCESSO TOTAL!")
        print("\nArquivos gerados:")
        
        arquivos_gerados = [
            "produtividade/ClienteTempo Gasto.csv",
            "dados_atividades_estruturados.csv",
            "produtividade/relatorios/basicos/",
            "produtividade/relatorios/avancados/",
            "relatorio_executivo_produtividade.txt"
        ]
        
        for arquivo in arquivos_gerados:
            if os.path.exists(arquivo):
                if os.path.isdir(arquivo):
                    print(f"  📁 {arquivo}/")
                else:
                    tamanho = os.path.getsize(arquivo)
                    print(f"  📄 {arquivo} ({tamanho:,} bytes)")
            else:
                print(f"  ❌ {arquivo} - NÃO GERADO")
        
        print(f"\n💡 Para visualizar o relatório executivo:")
        print(f"   cat relatorio_executivo_produtividade.txt")
        
    else:
        print("⚠️  PIPELINE EXECUTADO COM ERROS")
        print("Verifique os logs acima para identificar problemas.")
    
    print(f"\n{'='*80}")

if __name__ == "__main__":
    main()





