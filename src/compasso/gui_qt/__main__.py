"""Permite executar a GUI Qt com ``python -m compasso.gui_qt`` (útil durante a migração)."""

import sys

from .app import executar_app

# Versão exibida na barra de título (o ponto de entrada oficial passará o valor real).
VERSION = "2026.3.0"

if __name__ == "__main__":
    sys.exit(executar_app(versao=VERSION))
