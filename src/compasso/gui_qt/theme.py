"""Singleton de tema exposto ao QML.

Substitui o esquema antigo (``compasso.gui.theme``), em que trocar de tema reescrevia
globais de módulo e exigia reconstruir toda a UI. Aqui o tema é um ``QObject`` com
propriedades reativas: ``colors``, ``metrics`` e ``fonts`` são lidas pelo QML via *binding*
(``Theme.colors.accent``); ao chamar ``setTheme(nome)`` um único sinal ``changed`` dispara e
todos os *bindings* se reavaliam — **troca instantânea, sem reconstruir a interface**.

Como não há mais reconstrução da UI, a antiga regra "só trocar tema com a app ociosa" deixa
de ser necessária (não há estado de conexão/experimento a resetar).
"""

from PySide6.QtCore import QObject, Property, Signal, Slot

from . import gui_logger
from . import palettes
from compasso.core import config_manager


class Theme(QObject):
    """Fornece cores/dimensões/fontes reativas ao QML e persiste a paleta escolhida.

    As três propriedades expostas (``colors``/``metrics``/``fonts``) retornam dicionários
    lidos no QML como objetos JS. Todas usam o mesmo sinal ``changed`` como *notify*, então
    qualquer *binding* que dependa delas se atualiza quando a paleta muda.
    """

    changed = Signal()

    def __init__(self, nome_inicial: str | None = None):
        super().__init__()
        # Preferência salva > argumento > padrão. Valida contra as paletas conhecidas.
        salvo = config_manager.get_theme_pref()
        escolhido = salvo or nome_inicial or palettes.PALETTE_PADRAO
        if escolhido not in palettes.PALETTES:
            escolhido = palettes.PALETTE_PADRAO
        self._nome = escolhido
        gui_logger.logger.info(f"Tema inicial: {self._nome}")

    # ------------------------------------------------------------------ nome
    def _get_nome(self) -> str:
        return self._nome

    nome = Property(str, _get_nome, notify=changed)

    def _get_nomes(self):
        return palettes.THEME_NAMES

    nomes = Property("QVariantList", _get_nomes, constant=True)

    def _get_eh_claro(self) -> bool:
        return self._nome in palettes.PALETAS_CLARAS

    ehClaro = Property(bool, _get_eh_claro, notify=changed)

    # -------------------------------------------------------------- dicts QML
    def _get_colors(self):
        return palettes.PALETTES[self._nome]

    colors = Property("QVariant", _get_colors, notify=changed)

    def _get_metrics(self):
        return palettes.METRICS

    metrics = Property("QVariant", _get_metrics, constant=True)

    def _get_fonts(self):
        return palettes.FONTS

    fonts = Property("QVariant", _get_fonts, constant=True)

    # ---------------------------------------------------------------- troca
    @Slot(str, result=bool)
    def setTheme(self, nome: str) -> bool:
        """Troca a paleta ativa (e persiste). Retorna False se o nome for desconhecido."""
        if nome not in palettes.PALETTES:
            gui_logger.logger.warning(f"Tema desconhecido ignorado: {nome!r}")
            return False
        if nome == self._nome:
            return True
        self._nome = nome
        try:
            config_manager.set_theme_pref(nome)
        except Exception as e:
            gui_logger.logger.error(f"Falha ao salvar preferência de tema: {e}")
        self.changed.emit()
        gui_logger.logger.info(f"Tema alterado para: {nome}")
        return True
