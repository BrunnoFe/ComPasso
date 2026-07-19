"""Resolução de diretórios de recursos empacotados, **agnóstica de empacotador**.

O ComPasso é distribuído de duas formas que localizam os arquivos de dados (``assets/`` e os
``.qml``) de maneiras diferentes — e roda também direto do código-fonte em desenvolvimento. Este
módulo concentra a detecção do ambiente para que o resto do código peça só "onde estão os
recursos" sem saber qual empacotador está em uso:

* **PyInstaller** — extrai os dados para ``sys._MEIPASS`` (atributo que só existe no bundle).
* **Nuitka** — define ``__compiled__`` no namespace de todo módulo compilado; no modo onefile os
  dados incluídos via ``--include-data-dir`` ficam ao lado dos módulos, na pasta temporária de
  extração (a raiz é reconstruída a partir de ``__file__``).
* **Desenvolvimento** — nenhum dos dois; os dados estão na árvore do repositório.

Regra de layout que os dois empacotadores respeitam (ver ``compasso.spec`` e
``scripts/build_nuitka.py``): ``assets/`` na raiz do bundle e a árvore ``compasso/gui_qt/qml``
preservada. Assim, ``base_recursos()`` devolve a mesma raiz nos dois casos e quem chama só
concatena o subcaminho.
"""

import sys
from pathlib import Path

# Nuitka injeta ``__compiled__`` no namespace de cada módulo que compila; em CPython puro
# (dev / PyInstaller, que NÃO recompila) a variável não existe. É a forma recomendada de
# detectar execução sob Nuitka e é fixa por build (por isso constante de módulo).
EH_NUITKA = "__compiled__" in globals()


def eh_pyinstaller() -> bool:
    """True se rodando sob PyInstaller (``sys._MEIPASS`` só existe no bundle).

    Checado em tempo de chamada (não no import) para ser testável via monkeypatch.
    """
    return hasattr(sys, "_MEIPASS")


def eh_empacotado() -> bool:
    """True em qualquer empacotamento congelado (PyInstaller ou Nuitka)."""
    return EH_NUITKA or eh_pyinstaller()


def base_recursos() -> Path | None:
    """Raiz onde os data-files empacotados vivem, ou ``None`` em desenvolvimento.

    - PyInstaller: ``sys._MEIPASS``.
    - Nuitka: reconstruída de ``__file__`` (``<raiz>/compasso/utils/resources.py`` → sobe 2
      níveis até ``<raiz>``, onde ``assets/`` e ``compasso/`` foram colocados no build).
    """
    if eh_pyinstaller():
        return Path(sys._MEIPASS)
    if EH_NUITKA:
        return Path(__file__).resolve().parents[2]
    return None
