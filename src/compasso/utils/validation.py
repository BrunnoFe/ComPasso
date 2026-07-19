"""Validações puras dos dados do participante (sem dependência de GUI)."""

# Faixa etária de fábrica. Continua aqui como *default* das funções, mas a faixa efetiva é uma
# preferência do app (``core.app_prefs``): a trava antiga de 18–100 impedia, sem aviso, qualquer
# coleta com crianças e adolescentes. Este módulo permanece puro de propósito — quem conhece as
# preferências é o chamador, que as passa como argumento (``utils`` não importa ``core``).
MIN_IDADE = 0
MAX_IDADE = 120


def validar_nome_genero(nome: str, genero: str) -> bool:
    """Valida nome e gênero do participante: ambos devem conter apenas letras e espaços."""
    if not all(c.isalpha() or c.isspace() for c in nome):
        return False
    if not all(c.isalpha() or c.isspace() for c in genero):
        return False
    return True


def validar_idade(idade: str, minimo: int = MIN_IDADE, maximo: int = MAX_IDADE) -> bool:
    """Valida a idade do participante: inteiro dentro da faixa aceita.

    :param minimo: idade mínima aceita (padrão: faixa de fábrica).
    :param maximo: idade máxima aceita (padrão: faixa de fábrica).
    """
    if not idade.isdigit():
        return False
    return minimo <= int(idade) <= maximo
