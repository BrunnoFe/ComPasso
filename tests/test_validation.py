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
    ("0", False),      # abaixo do limite mínimo (MIN_IDADE = 18)
    ("18", True),      # limite mínimo
    ("27", True),
    ("100", True),     # limite máximo
    ("101", False),    # acima do limite
    ("-1", False),     # isdigit() é False para '-1'
    ("abc", False),
    ("", False),
    ("27.5", False),
])
def test_validar_idade(idade, esperado):
    assert validar_idade(idade) is esperado
