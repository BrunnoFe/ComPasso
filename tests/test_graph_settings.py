"""Janela "Configurações do Gráfico": preview ao vivo e persistência.

Regressão do bug em que as alterações eram gravadas em disco mas o gráfico voltava ao estado
anterior: o botão Salvar fecha a janela, e o ``onClosing`` da janela chama ``cancelar()`` —
que revertia o preview para o snapshot de abertura logo depois de salvar. As alterações só
"reapareciam" ao reabrir a janela, que relê as preferências já gravadas.

Não instancia QML nem o item do gráfico: o ``signal_plot`` é um espião que registra o último
``apply_settings`` recebido, que é exatamente o que o usuário vê na tela.
"""

import types

import pytest

pytest.importorskip("PySide6.QtCore")

from compasso.core import config_manager                                    # noqa: E402
from compasso.gui_qt.controllers.graph_settings_controller import (         # noqa: E402
    GraphSettingsController)


class PlotEspiao:
    """Substituto do ``GraficoSinal``: guarda o que foi aplicado na tela."""

    def __init__(self):
        self.aplicado = {}

    def apply_settings(self, settings):
        self.aplicado.update(settings)


@pytest.fixture
def controller(tmp_path, mocker):
    """Controller com prefs isoladas em tmp_path e um gráfico espião."""
    mocker.patch("compasso.core.config_manager.get_prefs_path",
                 return_value=tmp_path / "prefs.json")
    ctx = types.SimpleNamespace(
        sensor_type="EDA",
        runner=None,
        graph_settings=dict(config_manager.DEFAULT_GRAPH_SETTINGS),
        signal_plot=PlotEspiao(),
    )
    c = GraphSettingsController(ctx)
    c.abrir()
    return c


def _fechar_janela(controller):
    """Simula o ``onClosing`` da janela, que dispara ``cancelar()`` em qualquer fechamento."""
    controller.cancelar()


def test_salvar_sobrevive_ao_fechamento_da_janela(controller):
    """Após Salvar, fechar a janela NÃO pode reverter o gráfico (o bug relatado)."""
    controller.lineWidth = 3.5
    controller.smoothingWindow = 11
    controller.salvar()
    _fechar_janela(controller)

    aplicado = controller._ctx.signal_plot.aplicado
    assert aplicado["line_width"] == 3.5
    assert aplicado["smoothing_window"] == 11


def test_salvar_persiste_nas_preferencias(controller):
    """O que foi salvo é o que a próxima execução do app vai carregar."""
    controller.lineWidth = 3.5
    controller.valueMode = "Média"
    controller.salvar()

    salvo = config_manager.get_graph_prefs()
    assert salvo["line_width"] == 3.5
    assert salvo["value_mode"] == "mean"
    assert controller._ctx.graph_settings["line_width"] == 3.5


def test_cancelar_sem_salvar_reverte_o_preview(controller):
    """Fechar sem salvar continua desfazendo o preview — o outro lado do contrato."""
    original = controller.lineWidth
    controller.lineWidth = 3.5
    assert controller._ctx.signal_plot.aplicado["line_width"] == 3.5

    _fechar_janela(controller)
    assert controller._ctx.signal_plot.aplicado["line_width"] == original


def test_alteracao_tem_efeito_imediato_no_grafico(controller):
    """Cada mudança de propriedade chega ao gráfico na hora, sem esperar o Salvar."""
    controller.gridVisible = False
    assert controller._ctx.signal_plot.aplicado["grid_visible"] is False
    controller.smoothingEnabled = False
    assert controller._ctx.signal_plot.aplicado["smoothing_enabled"] is False


def test_restaurar_padroes_aplica_e_pode_ser_salvo(controller):
    controller.lineWidth = 3.5
    controller.restaurar()
    padrao = config_manager.DEFAULT_GRAPH_SETTINGS["line_width"]
    assert controller._ctx.signal_plot.aplicado["line_width"] == padrao
    controller.salvar()
    _fechar_janela(controller)
    assert controller._ctx.signal_plot.aplicado["line_width"] == padrao
