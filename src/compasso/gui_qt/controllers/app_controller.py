"""Controller de nível de aplicação: ações do menu (Ajuda, Sair) e pedidos de janelas.

Concentra as ações que não pertencem a uma view específica: abrir a pasta de logs, abrir as
páginas do projeto, sair. Também emite *sinais de pedido* para as janelas de configuração/
gráfico/calibração — que a camada QML conecta às janelas reais (implementadas na Fase 6).
"""

import webbrowser

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtGui import QGuiApplication

from .. import gui_logger
from compasso.utils import PROJECT_URL, PROJECT_GITSITE, get_logs_dir, open_path


class AppController(QObject):
    """Ações do menu Ajuda/Sair e pedidos de abertura de janelas auxiliares."""

    # Pedidos de janela (conectados no QML; janelas reais chegam na Fase 6).
    pedirNovoConfig = Signal()
    pedirAbrirConfig = Signal()
    pedirEditarConfig = Signal()
    pedirGraphSettings = Signal()
    pedirAppSettings = Signal()

    @Slot(int, int, int, int)
    def salvar_geometria(self, x: int, y: int, largura: int, altura: int) -> None:
        """Guarda a geometria da janela ao fechar (preferência ``lembrar_geometria``)."""
        from compasso.core import app_prefs

        app_prefs.definir_geometria(x, y, largura, altura)

    @Slot()
    def abrir_pasta_logs(self) -> None:
        """Abre a pasta de logs no gerenciador de arquivos do SO."""
        try:
            open_path(str(get_logs_dir()))
        except Exception as e:
            gui_logger.logger.warning(f"Falha ao abrir a pasta de logs: {e}")

    @Slot()
    def abrir_pagina_projeto(self) -> None:
        """Abre a página do projeto (repositório) no navegador."""
        webbrowser.open(PROJECT_URL)

    @Slot()
    def abrir_site_projeto(self) -> None:
        """Abre o site do projeto (GitHub Pages) no navegador."""
        webbrowser.open(PROJECT_GITSITE)

    @Slot()
    def sair(self) -> None:
        """Encerra a aplicação."""
        gui_logger.logger.info("Encerramento solicitado pelo menu.")
        QGuiApplication.quit()
