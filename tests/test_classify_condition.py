"""Classificação do fator de uma faixa em 'musica' ou 'ruido'."""

import pytest

from src.core.experiment import _classify_condition


@pytest.mark.parametrize("fator, esperado", [
    ("ruido", "ruido"),
    ("ruído", "ruido"),          # com acento
    ("RUIDO branco", "ruido"),   # case-insensitive + substring
    ("ruido rosa", "ruido"),
    ("musica", "musica"),
    ("clássica", "musica"),
    ("", "musica"),              # vazio -> musica (padrão)
    (None, "musica"),            # None -> musica (padrão)
    ("  Ruído  ", "ruido"),      # espaços nas pontas
])
def test_classify_condition(fator, esperado):
    assert _classify_condition(fator) == esperado
