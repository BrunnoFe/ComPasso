"""Gera `version_info.txt` (recurso de versão do executável Windows, lido pelo PyInstaller)
a partir da versão declarada em `pyproject.toml` — fonte única de verdade do versionamento.

`version_info.txt` é um arquivo estático que o PyInstaller não consegue gerar dinamicamente
durante o build; este script existe para não precisarmos editá-lo à mão a cada release
(histórico: era fácil esquecer de atualizá-lo em paralelo ao `pyproject.toml`).

Uso (antes de `pyinstaller compasso.spec`, ver BUILD.md):
    uv run python scripts/generate_version_info.py
"""

from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PYPROJECT = RAIZ / "pyproject.toml"
DESTINO = RAIZ / "version_info.txt"

_TEMPLATE = """# UTF-8
#
# Arquivo de versão do Windows usado pelo PyInstaller (EXE version=...).
# GERADO AUTOMATICAMENTE por scripts/generate_version_info.py a partir de `pyproject.toml`
# ([project].version) — não editar à mão. Para mudar a versão, edite pyproject.toml e rode o
# script de novo.
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({partes}, 0),
    prodvers=({partes}, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [StringStruct('CompanyName', 'ComPasso'),
         StringStruct('FileDescription', 'ComPasso'),
         StringStruct('FileVersion', '{versao}'),
         StringStruct('InternalName', 'ComPasso'),
         StringStruct('LegalCopyright', '© {ano} ComPasso'),
         StringStruct('OriginalFilename', 'ComPasso.exe'),
         StringStruct('ProductName', 'ComPasso'),
         StringStruct('ProductVersion', '{versao}')])
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""

_VERSION_RE = re.compile(r'(?m)^version\s*=\s*"([^"]+)"')


def ler_versao_pyproject() -> str:
    """Extrai `[project].version` de pyproject.toml sem depender de um parser TOML externo."""
    texto = PYPROJECT.read_text(encoding="utf-8")
    match = _VERSION_RE.search(texto)
    if not match:
        raise SystemExit(f"Não encontrei 'version = \"...\"' em {PYPROJECT}.")
    return match.group(1)


def montar_conteudo(versao: str) -> str:
    """Monta o conteúdo de `version_info.txt` para a versão informada (formato `AAAA.M.P`)."""
    partes = versao.split(".")
    if len(partes) != 3 or not all(p.isdigit() for p in partes):
        raise SystemExit(
            f"Versão '{versao}' não está no formato AAAA.M.P esperado (ex.: 2026.4.0)."
        )
    return _TEMPLATE.format(partes=", ".join(partes), versao=versao, ano=partes[0])


def main() -> None:
    versao = ler_versao_pyproject()
    DESTINO.write_text(montar_conteudo(versao), encoding="utf-8")
    print(f"version_info.txt gerado para a versão {versao} ({DESTINO}).")


if __name__ == "__main__":
    main()
