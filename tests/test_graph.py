"""Lógica de redução de dados do gráfico do sinal (``GraficoSinal``, QQuickPaintedItem).

A renderização QPainter não é testada em unidade (só a lógica, como no restante da suíte).
Aqui verificamos a decimação por coluna (contagem de pontos LIMITADA → custo por quadro
constante), o relógio de exibição e o ``reset_idle``, sem renderizar nada.
"""

import math

import pytest

# QGuiApplication headless para instanciar o item (a plataforma offscreen é fixada no conftest).
_qt = pytest.importorskip("PySide6.QtGui")


@pytest.fixture(scope="module")
def _app():
    app = _qt.QGuiApplication.instance() or _qt.QGuiApplication([])
    return app


def _grafico(_app):
    from compasso.gui_qt.signal_chart import GraficoSinal
    g = GraficoSinal()
    g._timer.stop()   # controlamos os quadros manualmente (determinístico)
    return g


def test_decimacao_limita_pontos(_app):
    """120k amostras devem virar no máximo ~_COLUNAS_DECIMACAO pontos (custo constante)."""
    from compasso.gui_qt.signal_chart import _COLUNAS_DECIMACAO
    g = _grafico(_app)
    g.begin(60.0, 5.0)
    esc = g._escala_y
    for i in range(120_000):
        t = 60.0 * i / 120_000
        g.push(t, 0.6 * esc * math.sin(2 * math.pi * t))
    g._quadro()
    g.end()
    g._quadro()
    pontos = g._pontos_decimados()
    assert 1000 < len(pontos) <= _COLUNAS_DECIMACAO


def test_eixo_x_relativo_ao_inicio_da_musica(_app):
    """O último ponto após o fim fica em ~ (duração - antecedência)."""
    g = _grafico(_app)
    g.begin(30.0, 5.0)
    for i in range(3000):
        t = 30.0 * i / 3000
        g.push(t, 1.0)
    g._quadro()
    g.end()
    g._quadro()
    ultimo_t = g._pontos_decimados()[-1][0]
    assert abs(ultimo_t - (30.0 - 5.0)) < 0.2


def test_reset_idle_limpa(_app):
    g = _grafico(_app)
    g.begin(10.0, 2.0)
    for i in range(500):
        g.push(10.0 * i / 500, 1.0)
    g._quadro()
    assert g._pontos_decimados()
    g.reset_idle()
    g._quadro()
    assert g._pontos_decimados() == []
    assert g.leitura == "—"


def test_media_movel_suaviza(_app):
    """A média móvel reduz a variação ponto-a-ponto em relação ao sinal bruto."""
    g = _grafico(_app)
    assert g._media_movel([0, 10, 0, 10, 0], 3) != [0, 10, 0, 10, 0]
    # janela 1 (ou desativada) não altera os valores.
    assert g._media_movel([0, 10, 0], 1) == [0, 10, 0]
