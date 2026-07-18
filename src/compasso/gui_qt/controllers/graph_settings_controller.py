"""Controller da janela "Configurações do Gráfico" (equivale a GraphSettingsWindow).

Ajusta os parâmetros de exibição do gráfico com **preview ao vivo** (via ``ctx.signal_plot``)
e **persistência** no ``prefs.json`` (``config_manager.set_graph_prefs``). Cada propriedade
reativa aplica o preview ao mudar; ``cancelar`` reverte ao snapshot de abertura. A escala Y é
travada durante uma sessão em andamento (fica fixa no experimento).
"""

from PySide6.QtCore import QObject, Property, Signal, Slot

from .. import gui_logger
from ..context import Context
from compasso.core import config_manager
from compasso.core.constants import SENSOR_DEFAULT, SENSOR_GRAPH_PARAMS

_MAPA_VALUE_MODE = {"Valor bruto": "raw", "Média": "mean"}
_MAPA_VALUE_MODE_INV = {"raw": "Valor bruto", "mean": "Média"}


class GraphSettingsController(QObject):
    """Estado reativo das configurações do gráfico + preview/persistência."""

    mudou = Signal()            # notify comum de todas as propriedades de settings
    sensorChanged = Signal()

    def __init__(self, ctx: Context):
        super().__init__()
        self._ctx = ctx
        self._snapshot = {}
        self._s = dict(config_manager.DEFAULT_GRAPH_SETTINGS)

    # ---------------------------------------------------------------- sensor
    def _params(self):
        return SENSOR_GRAPH_PARAMS.get(getattr(self._ctx, "sensor_type", SENSOR_DEFAULT),
                                       SENSOR_GRAPH_PARAMS[SENSOR_DEFAULT])

    def _get_unidade(self):
        return self._params()["unidade"]

    unidade = Property(str, _get_unidade, notify=sensorChanged)

    def _get_y_min(self):
        return float(self._params()["minimo"])

    yMin = Property(float, _get_y_min, notify=sensorChanged)

    def _get_y_max(self):
        return float(self._params()["maximo"])

    yMax = Property(float, _get_y_max, notify=sensorChanged)

    def _get_y_step(self):
        return float(self._params()["passo"])

    yStep = Property(float, _get_y_step, notify=sensorChanged)

    def _get_sessao_ativa(self):
        r = getattr(self._ctx, "runner", None)
        return bool(r is not None and r.is_running())

    sessaoAtiva = Property(bool, _get_sessao_ativa, notify=sensorChanged)

    # -------------------------------------------------- propriedades de settings
    def _mk(chave, tipo):
        def getter(self):
            return tipo(self._s.get(chave, config_manager.DEFAULT_GRAPH_SETTINGS[chave]))

        def setter(self, valor):
            valor = tipo(valor)
            if self._s.get(chave) != valor:
                self._s[chave] = valor
                self.mudou.emit()
                self._preview()

        return getter, setter

    _g, _s = _mk("y_scale", float)
    yScale = Property(float, _g, _s, notify=mudou)
    _g, _s = _mk("smoothing_enabled", bool)
    smoothingEnabled = Property(bool, _g, _s, notify=mudou)
    _g, _s = _mk("smoothing_window", int)
    smoothingWindow = Property(int, _g, _s, notify=mudou)
    _g, _s = _mk("fps", int)
    fps = Property(int, _g, _s, notify=mudou)
    _g, _s = _mk("line_width", float)
    lineWidth = Property(float, _g, _s, notify=mudou)
    _g, _s = _mk("grid_visible", bool)
    gridVisible = Property(bool, _g, _s, notify=mudou)
    _g, _s = _mk("axis_labels_visible", bool)
    labelsVisible = Property(bool, _g, _s, notify=mudou)
    del _mk, _g, _s

    def _get_value_mode(self):
        return self._s.get("value_mode", "raw")

    def _set_value_mode(self, modo):
        # aceita rótulo do menu ("Valor bruto"/"Média") ou a própria chave.
        chave = _MAPA_VALUE_MODE.get(modo, modo)
        if chave not in ("raw", "mean"):
            chave = "raw"
        if self._s.get("value_mode") != chave:
            self._s["value_mode"] = chave
            self.mudou.emit()
            self._preview()

    valueMode = Property(str, _get_value_mode, _set_value_mode, notify=mudou)

    def _get_value_mode_label(self):
        return _MAPA_VALUE_MODE_INV.get(self._s.get("value_mode", "raw"), "Valor bruto")

    valueModeLabel = Property(str, _get_value_mode_label, notify=mudou)

    # ------------------------------------------------------------------ ações
    @Slot()
    def abrir(self) -> None:
        """Carrega os valores ativos e guarda o snapshot para um eventual cancelar."""
        atual = dict(config_manager.DEFAULT_GRAPH_SETTINGS)
        salvo = getattr(self._ctx, "graph_settings", None)
        if isinstance(salvo, dict):
            atual.update({k: salvo[k] for k in config_manager.DEFAULT_GRAPH_SETTINGS if k in salvo})
        self._s = atual
        self._snapshot = dict(atual)
        self.sensorChanged.emit()
        self.mudou.emit()

    @Slot()
    def salvar(self) -> None:
        config_manager.set_graph_prefs(self._s)
        self._ctx.graph_settings = dict(self._s)
        self._preview()
        gui_logger.logger.info(f"Configurações do gráfico salvas: {self._s}")

    @Slot()
    def restaurar(self) -> None:
        """Volta os controles aos defaults (escala Y = padrão do sensor)."""
        padrao = dict(config_manager.DEFAULT_GRAPH_SETTINGS)
        padrao["y_scale"] = self._params()["padrao"]
        self._s = padrao
        self.mudou.emit()
        self._preview()

    @Slot()
    def cancelar(self) -> None:
        """Reverte o preview ao estado de abertura (sem salvar)."""
        self._aplicar(self._snapshot)

    def _preview(self) -> None:
        self._aplicar(self._s)

    def _aplicar(self, settings: dict) -> None:
        plot = getattr(self._ctx, "signal_plot", None)
        if plot is not None:
            try:
                plot.apply_settings(dict(settings))
            except Exception as e:
                gui_logger.logger.warning(f"Falha ao aplicar preview do gráfico: {e}")
