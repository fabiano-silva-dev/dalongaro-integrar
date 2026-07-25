"""Classificação contábil por regras, favorecidos e heurísticas."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .caminhos import CONFIG
from .leitura_planilhas import Lancamento
from .normalizacao import normalizar_chave
from .plano_contas import PlanoContas


@dataclass
class ResultadoClassificacao:
    debito: str
    credito: str
    historico: str
    regra: str
    confianca: int
    origem: str
    observacoes: str = ""


def _carregar_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


class Classificador:
    def __init__(self, plano: PlanoContas, config_dir: Path = CONFIG):
        self.plano = plano
        self.config = _carregar_json(config_dir / "configuracao.json")
        self.regras = _carregar_json(config_dir / "regras-classificacao.json").get(
            "regras", []
        )
        self.favorecidos = _carregar_json(config_dir / "favorecidos.json").get(
            "favorecidos", []
        )
        self.contas_financeiras = self.config.get("contas_financeiras", {})
        self.confianca_minima_export = int(
            self.config.get("confianca_minima_exportacao", 80)
        )

    def conta_financeira_codigo(self, lanc: Lancamento) -> str:
        # prioriza mapeamento por arquivo
        mapa = self.contas_financeiras.get("por_arquivo", {})
        if lanc.arquivo_origem in mapa:
            return str(mapa[lanc.arquivo_origem])
        # fallback por palavras no nome do arquivo
        nome = normalizar_chave(lanc.arquivo_origem)
        por_palavra = self.contas_financeiras.get("por_palavra", {})
        for palavra, codigo in por_palavra.items():
            if normalizar_chave(palavra) in nome:
                return str(codigo)
        padrao = self.contas_financeiras.get("padrao", "5")
        return str(padrao)

    def _resolver_token(self, token: str, conta_fin: str) -> str:
        if not token:
            return ""
        if token == "CONTA_FINANCEIRA":
            return conta_fin
        return str(token)

    def _match_palavras(self, texto: str, palavras: List[str]) -> bool:
        if not palavras:
            return True
        return any(normalizar_chave(p) in texto for p in palavras)

    def _match_favorecido_regra(self, texto_fav: str, favorecidos: List[str]) -> bool:
        if not favorecidos:
            return True
        return any(normalizar_chave(f) in texto_fav or texto_fav in normalizar_chave(f) for f in favorecidos)

    def classificar_por_favorecido(
        self, lanc: Lancamento, conta_fin: str
    ) -> Optional[ResultadoClassificacao]:
        fav = lanc.favorecido_normalizado or lanc.historico_normalizado
        if not fav:
            return None
        for item in self.favorecidos:
            variacoes = [item.get("nome_normalizado", "")] + list(item.get("variacoes", []))
            if not any(normalizar_chave(v) and normalizar_chave(v) in fav for v in variacoes):
                # também aceita igualdade
                if not any(normalizar_chave(v) == fav for v in variacoes if v):
                    continue
            tipo = item.get("tipo_movimento")
            if tipo and tipo != lanc.tipo_movimento:
                continue
            deb = self._resolver_token(item.get("codigo_conta_debito", ""), conta_fin)
            cred = self._resolver_token(item.get("codigo_conta_credito", ""), conta_fin)
            if lanc.tipo_movimento == "ENTRADA":
                if not deb:
                    deb = conta_fin
                if not cred:
                    continue
            else:
                if not cred:
                    cred = conta_fin
                if not deb:
                    continue
            hist = item.get("historico_padrao") or lanc.historico_original.upper()
            return ResultadoClassificacao(
                debito=deb,
                credito=cred,
                historico=hist,
                regra=f"FAVORECIDO:{item.get('nome_normalizado', '')}",
                confianca=int(item.get("confianca", 90)),
                origem="FAVORECIDO",
            )
        return None

    def classificar_por_regra(
        self, lanc: Lancamento, conta_fin: str
    ) -> Optional[ResultadoClassificacao]:
        texto = f"{lanc.historico_normalizado} {lanc.favorecido_normalizado}".strip()
        regras = sorted(self.regras, key=lambda r: int(r.get("prioridade", 0)), reverse=True)
        for regra in regras:
            tipo = regra.get("tipo_movimento")
            if tipo and tipo != lanc.tipo_movimento:
                continue
            if not self._match_palavras(texto, regra.get("palavras", [])):
                continue
            if not self._match_favorecido_regra(
                lanc.favorecido_normalizado or texto, regra.get("favorecidos", [])
            ):
                continue
            deb = self._resolver_token(regra.get("codigo_conta_debito", ""), conta_fin)
            cred = self._resolver_token(regra.get("codigo_conta_credito", ""), conta_fin)
            if not deb or not cred:
                continue
            hist = regra.get("historico_padrao") or lanc.historico_original.upper()
            return ResultadoClassificacao(
                debito=deb,
                credito=cred,
                historico=hist,
                regra=regra.get("nome", "REGRA"),
                confianca=int(regra.get("confianca", 80)),
                origem="REGRA",
            )
        return None

    def classificar_heuristica(
        self, lanc: Lancamento, conta_fin: str
    ) -> ResultadoClassificacao:
        """Fallback conservador: marca pendência com confiança baixa."""
        texto = lanc.historico_normalizado
        # transferências entre contas financeiras
        if any(
            p in texto
            for p in [
                "TRANSFERENCIA ENTRE",
                "TRANSFERENCIA CONTA",
                "TRANSF ENTRE",
                "PIX ENVIADO PARA CONTA",
                "APLICACAO",
                "APLICAÇÃO",
                "RESGATE",
            ]
        ) or (
            "TRANSFERENCIA" in texto
            and any(x in texto for x in ["SICREDI", "CRESOL", "CAIXA", "BANCO", "CONSTAS", "CONTAS"])
        ):
            return ResultadoClassificacao(
                debito="",
                credito="",
                historico=lanc.historico_original.upper(),
                regra="HEURISTICA:TRANSFERENCIA",
                confianca=20,
                origem="AUTOMÁTICA",
                observacoes="Possível transferência — informar contas manualmente",
            )

        if lanc.tipo_movimento == "ENTRADA":
            return ResultadoClassificacao(
                debito=conta_fin,
                credito="",
                historico=lanc.historico_original.upper(),
                regra="HEURISTICA:ENTRADA_SEM_REGRA",
                confianca=30,
                origem="AUTOMÁTICA",
                observacoes="Entrada sem regra — informar conta de crédito",
            )
        return ResultadoClassificacao(
            debito="",
            credito=conta_fin,
            historico=lanc.historico_original.upper(),
            regra="HEURISTICA:SAIDA_SEM_REGRA",
            confianca=30,
            origem="AUTOMÁTICA",
            observacoes="Saída sem regra — informar conta de débito",
        )

    def aplicar(self, lanc: Lancamento) -> Lancamento:
        conta_fin = self.conta_financeira_codigo(lanc)
        lanc.conta_financeira = conta_fin

        resultado = self.classificar_por_favorecido(lanc, conta_fin)
        if resultado is None:
            resultado = self.classificar_por_regra(lanc, conta_fin)
        if resultado is None:
            resultado = self.classificar_heuristica(lanc, conta_fin)

        # valida contas no plano
        obs = resultado.observacoes
        for campo, codigo in (("débito", resultado.debito), ("crédito", resultado.credito)):
            if codigo and not self.plano.existe(codigo):
                obs = (obs + f"; conta {campo} {codigo} inexistente no plano").strip("; ")
                resultado.confianca = min(resultado.confianca, 10)
            elif codigo and not self.plano.eh_analitica(codigo):
                obs = (obs + f"; conta {campo} {codigo} é sintética").strip("; ")
                resultado.confianca = min(resultado.confianca, 40)

        lanc.codigo_conta_debito = resultado.debito
        lanc.descricao_conta_debito = self.plano.descricao(resultado.debito)
        lanc.codigo_conta_credito = resultado.credito
        lanc.descricao_conta_credito = self.plano.descricao(resultado.credito)
        lanc.historico_contabil = resultado.historico
        lanc.regra_aplicada = resultado.regra
        lanc.confianca = resultado.confianca
        lanc.origem_classificacao = resultado.origem
        lanc.observacoes = obs

        completo = bool(resultado.debito and resultado.credito and resultado.debito != resultado.credito)
        if completo and resultado.confianca >= self.confianca_minima_export:
            lanc.status = "CLASSIFICADO"
            lanc.exportar = "SIM"
        elif completo:
            lanc.status = "REVISAR"
            lanc.exportar = "NÃO"
        else:
            lanc.status = "PENDENTE"
            lanc.exportar = "NÃO"
        return lanc


def classificar_lista(lancamentos: List[Lancamento], plano: PlanoContas) -> List[Lancamento]:
    clf = Classificador(plano)
    return [clf.aplicar(l) for l in lancamentos]
