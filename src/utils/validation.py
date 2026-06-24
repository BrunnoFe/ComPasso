"""Validações puras dos dados do participante (sem dependência de GUI)."""


def validar_nome_genero(nome: str, genero: str) -> bool:
    """Valida nome e gênero do participante: ambos devem conter apenas letras e espaços."""
    if not all(c.isalpha() or c.isspace() for c in nome):
        return False
    if not all(c.isalpha() or c.isspace() for c in genero):
        return False
    return True


def validar_idade(idade: str) -> bool:
    """Valida a idade do participante: deve ser um inteiro entre 0 e 100."""
    if not idade.isdigit():
        return False
    valor = int(idade)
    return 0 <= valor <= 100
