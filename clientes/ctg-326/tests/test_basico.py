#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Testes essenciais CTG-326."""

from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.dominio import (  # noqa: E402
    limpar_historico,
    montar_registro_01,
    montar_registro_03,
    montar_registro_99,
)
from src.normalizacao import (  # noqa: E402
    id_lancamento,
    normalizar_chave,
    parse_data,
    parse_valor,
)
from src.plano_contas import Conta, PlanoContas  # noqa: E402
from src.validacao import validar_linha  # noqa: E402


class TestNormalizacao(unittest.TestCase):
    def test_valores_br(self):
        self.assertEqual(parse_valor("1.234,56"), Decimal("1234.56"))
        self.assertEqual(parse_valor("R$ 1.234,56"), Decimal("1234.56"))
        self.assertEqual(parse_valor("(1.234,56)"), Decimal("-1234.56"))
        self.assertEqual(parse_valor("-10,50"), Decimal("-10.50"))
        self.assertEqual(parse_valor(1234.56), Decimal("1234.56"))

    def test_datas(self):
        self.assertEqual(parse_data("01/07/2026"), date(2026, 7, 1))
        self.assertEqual(parse_data("1/7/2026"), date(2026, 7, 1))
        self.assertEqual(parse_data("2026-07-01"), date(2026, 7, 1))
        self.assertEqual(parse_data("24/072025"), date(2025, 7, 24))
        self.assertEqual(parse_data("11//12/2025"), date(2025, 12, 11))

    def test_chave_e_id(self):
        self.assertEqual(normalizar_chave("Ação  Café"), "ACAO CAFE")
        a = id_lancamento("a.xlsx", "mai", 5, date(2025, 5, 1), "", "x", "", Decimal("10"))
        b = id_lancamento("a.xlsx", "mai", 5, date(2025, 5, 1), "", "x", "", Decimal("10"))
        self.assertEqual(a, b)


class TestDominio(unittest.TestCase):
    def test_tamanhos(self):
        r01 = montar_registro_01("326", "87.445.102/0001-07", date(2025, 5, 1), date(2025, 12, 31))
        self.assertEqual(len(r01), 100)
        self.assertTrue(r01.startswith("010000326"))
        r03 = montar_registro_03(1, "5", "33", Decimal("1190.12"), "PGTO TESTE", "326")
        self.assertEqual(len(r03), 664)
        self.assertEqual(r03[9:16], "0000005")
        self.assertEqual(r03[16:23], "0000033")
        self.assertEqual(r03[23:38], "000000000119012")
        self.assertEqual(len(montar_registro_99()), 100)

    def test_historico_acentos(self):
        h = limpar_historico("Pagamento\nenergia\telétrica")
        self.assertNotIn("\n", h)
        self.assertIn("elétrica", h)


class TestValidacao(unittest.TestCase):
    def setUp(self):
        self.plano = PlanoContas(
            [
                Conta("5", "1.1.1.01.001", "CAIXA", 5, False),
                Conta("33", "4.1.1.01.001", "RECEITAS DA COPA", 5, False),
                Conta("3", "1.1.1", "DISPONIBILIDADES", 3, True),
            ]
        )

    def test_ok(self):
        erros = validar_linha(
            {
                "data": "01/05/2025",
                "valor": Decimal("10.00"),
                "codigo_conta_debito": "5",
                "codigo_conta_credito": "33",
                "historico_contabil": "TESTE",
            },
            self.plano,
        )
        self.assertEqual(erros, [])

    def test_debito_igual_credito(self):
        erros = validar_linha(
            {
                "data": "01/05/2025",
                "valor": Decimal("10.00"),
                "codigo_conta_debito": "5",
                "codigo_conta_credito": "5",
                "historico_contabil": "TESTE",
            },
            self.plano,
        )
        self.assertTrue(any("igual" in e for e in erros))

    def test_sintetica(self):
        erros = validar_linha(
            {
                "data": "01/05/2025",
                "valor": Decimal("10.00"),
                "codigo_conta_debito": "3",
                "codigo_conta_credito": "33",
                "historico_contabil": "TESTE",
            },
            self.plano,
        )
        self.assertTrue(any("sintética" in e for e in erros))


if __name__ == "__main__":
    unittest.main()
