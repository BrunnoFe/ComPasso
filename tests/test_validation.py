"""Validações puras dos dados do participante."""

import pytest

from compasso.utils.validation import validar_nome_genero, validar_idade


@pytest.mark.parametrize("nome, genero, esperado", [
    ("Maria Clara", "Feminino", True),
    ("João", "Masculino", True),       # acentos são letras (isalpha unicode)
    ("Ana Maria", "Outro", True),
    ("Ana123", "Feminino", False),     # dígitos no nome
    ("Maria", "F3minino", False),      # dígitos no gênero
    ("Maria!", "Feminino", False),     # pontuação
    ("", "", True),                    # vazio: all() de sequência vazia é True
])
def test_validar_nome_genero(nome, genero, esperado):
    assert validar_nome_genero(nome, genero) is esperado


@pytest.mark.parametrize("idade, esperado", [
    ("0", True),       # faixa de fábrica agora é 0–120: coleta com crianças é caso legítimo
    ("18", True),
    ("27", True),
    ("120", True),     # limite máximo de fábrica
    ("121", False),    # acima do limite
    ("-1", False),     # isdigit() é False para '-1'
    ("abc", False),
    ("", False),
    ("27.5", False),
])
def test_validar_idade(idade, esperado):
    assert validar_idade(idade) is esperado


@pytest.mark.parametrize("idade, minimo, maximo, esperado", [
    ("17", 18, 100, False),   # faixa restrita explicitamente pelo chamador
    ("18", 18, 100, True),
    ("100", 18, 100, True),
    ("101", 18, 100, False),
    ("8", 6, 12, True),       # estudo com crianças: impossível antes de a faixa ser configurável
    ("5", 6, 12, False),
])
def test_validar_idade_faixa_personalizada(idade, minimo, maximo, esperado):
    """A faixa efetiva vem das preferências do app e é passada pelo chamador."""
    assert validar_idade(idade, minimo, maximo) is esperado
