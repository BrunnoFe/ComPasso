"""Versão do app, lida em runtime a partir de uma única fonte: `pyproject.toml` (`[project].version`).

Antes disso a versão era um literal hardcoded (`VERSION = "..."`) repetido em `main.py`,
`version_info.txt` e outros lugares — cada release exigia lembrar de atualizar todos eles à mão.
`get_app_version()` substitui o hardcode em `main.py`; `version_info.txt` (recurso do executável
Windows) continua sendo um arquivo estático à parte, mas passa a ser **gerado** a partir do
`pyproject.toml` por `scripts/generate_version_info.py` em vez de editado à mão — ver BUILD.md.

No executável PyInstaller, os metadados do pacote (`compasso-X.Y.Z.dist-info/`) precisam ser
empacotados explicitamente (`copy_metadata("compasso")` em `compasso.spec`); sem isso,
`importlib.metadata.version` não encontraria o pacote no app congelado.
"""

from importlib.metadata import PackageNotFoundError, version

# Usado quando o pacote não está instalado com metadados (ex.: rodando main.py sem `uv sync`
# nem instalação editável) — nunca deve aparecer num app rodando via `uv run` ou no executável.
VERSAO_DESCONHECIDA = "0.0.0-dev"


def get_app_version() -> str:
    """Retorna a versão do app declarada em `pyproject.toml`, ou um fallback se indisponível."""
    try:
        return version("compasso")
    except PackageNotFoundError:
        return VERSAO_DESCONHECIDA
