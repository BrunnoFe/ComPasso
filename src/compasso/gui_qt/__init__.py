"""Camada de interface gráfica do ComPasso em PySide6/QML.

Substitui a antiga GUI em CustomTkinter (pacote ``compasso.gui``). Enquanto a migração está
em andamento, os dois pacotes coexistem; ao final, este passa a ser a única camada de GUI.

Exporta:
- ``executar_app``: ponto de entrada que sobe o ``QApplication`` + engine QML.
- ``Context``: hub de estado compartilhado (QObject) exposto ao QML.
- ``Theme``: singleton de tema (QObject) que fornece cores/fontes/dimensões reativas ao QML.
"""

from compasso.utils import SetLogger

# Um logger por camada, no padrão dos demais pacotes (ver core/__init__.py).
# Definido ANTES de importar .app, pois os submódulos fazem `from . import gui_logger`.
gui_logger = SetLogger(category='gui', namelogger='guiQtLogger')

from .app import executar_app  # noqa: E402 (precisa de gui_logger já definido)

__all__ = ["gui_logger", "executar_app"]
