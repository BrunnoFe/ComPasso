"""Versionamento centralizado em `pyproject.toml` (ver src/compasso/utils/version.py).

Cobre dois pontos que dependiam de disciplina manual antes desta suíte existir:
- `get_app_version()` (runtime) precisa bater com `[project].version` de `pyproject.toml`.
- `version_info.txt` (recurso do executável Windows) precisa ser exatamente o que
  `scripts/generate_version_info.py` geraria a partir da versão atual — se alguém bumpar a
  versão em `pyproject.toml` e esquecer de rodar o script (ou editar o arquivo à mão), este
  teste falha em vez de deixar os dois arquivos divergirem silenciosamente.
"""

import importlib.util
import re
from pathlib import Path

import pytest

from compasso.utils import get_app_version

RAIZ = Path(__file__).resolve().parent.parent
PYPROJECT = RAIZ / "pyproject.toml"
VERSION_INFO = RAIZ / "version_info.txt"


def _carregar_script_geracao():
    """Importa scripts/generate_version_info.py por caminho (a pasta não é um pacote)."""
    caminho = RAIZ / "scripts" / "generate_version_info.py"
    spec = importlib.util.spec_from_file_location("generate_version_info", caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


gerador = _carregar_script_geracao()


def test_versao_pyproject_esta_no_formato_esperado():
    versao = gerador.ler_versao_pyproject()
    assert re.fullmatch(r"\d+\.\d+\.\d+", versao), (
        f"Versão '{versao}' em pyproject.toml não está no formato AAAA.M.P."
    )


def test_get_app_version_bate_com_pyproject():
    """Falha se `uv sync` não tiver rodado após um bump de versão (metadados desatualizados)."""
    assert get_app_version() == gerador.ler_versao_pyproject()


def test_version_info_txt_sincronizado_com_pyproject():
    """Detecta version_info.txt não regenerado (ou editado à mão) após mudar a versão."""
    versao_atual = gerador.ler_versao_pyproject()
    esperado = gerador.montar_conteudo(versao_atual)
    atual = VERSION_INFO.read_text(encoding="utf-8")
    assert atual == esperado, (
        "version_info.txt está desatualizado em relação a pyproject.toml — rode "
        "`uv run python scripts/generate_version_info.py` e commite o resultado."
    )


def test_montar_conteudo_inclui_versao_nos_campos_esperados():
    conteudo = gerador.montar_conteudo("2027.1.2")
    assert "filevers=(2027, 1, 2, 0)" in conteudo
    assert "prodvers=(2027, 1, 2, 0)" in conteudo
    assert "StringStruct('FileVersion', '2027.1.2')" in conteudo
    assert "StringStruct('ProductVersion', '2027.1.2')" in conteudo
    assert "© 2027 ComPasso" in conteudo


@pytest.mark.parametrize("versao_invalida", ["2026.4", "2026.4.0.1", "v2026.4.0", "abc"])
def test_montar_conteudo_rejeita_formato_invalido(versao_invalida):
    with pytest.raises(SystemExit):
        gerador.montar_conteudo(versao_invalida)
