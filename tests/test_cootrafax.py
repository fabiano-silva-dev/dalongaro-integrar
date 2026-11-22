"""Testes unitários do motor COOTRAFAX."""
import importlib.util
import unittest
from decimal import Decimal
from pathlib import Path

CAMINHO = Path(__file__).resolve().parents[1] / "scripts/contabil/cootrafax/gerar_lancamentos.py"
SPEC = importlib.util.spec_from_file_location("cootrafax", CAMINHO)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


class TestCootrafax(unittest.TestCase):
    def test_valores(self):
        self.assertEqual(MOD.numero("1.234,56"), Decimal("1234.56"))
        self.assertEqual(MOD.formato(Decimal("1234.56")), "1234,56")
        with self.assertRaises(ValueError):
            MOD.numero("1,234.56")

    def test_contas_debito(self):
        self.assertEqual(MOD.DEBITO, {"PF": "213", "PJ": "214"})


if __name__ == "__main__":
    unittest.main()
