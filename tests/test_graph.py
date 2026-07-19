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


def _alimentar(g, duracao, n, valor):
    """Empurra `n` amostras drenando a cada quadro, como o timer faz em execução real.

    Drenar importa: a fila entre a thread de aquisição e a da GUI tem `maxlen`, então despejar
    tudo de uma vez descartaria as amostras antigas — que é o comportamento desejado quando a
    GUI estagna, mas não o do funcionamento normal.
    """
    for i in range(n):
        t = duracao * i / n
        g.push(t, valor(t))
        if i % 500 == 0:
            g._drenar_pendentes()
    g._drenar_pendentes()


from PySide6.QtCore import QObject as _QObject


class _CtxFalso(_QObject):
    """Contexto mínimo com a superfície que o `GraficoSinal` lê ao receber o `contexto`.

    Precisa ser um QObject de verdade: a propriedade `contexto` do item é declarada como
    ``Property(QObject, ...)`` e recusa qualquer outra coisa.
    """

    def __init__(self, graph_settings=None, sensor_type="ECG"):
        super().__init__()
        self.graph_settings = graph_settings or {}
        self.sensor_type = sensor_type
        self.signal_channel = 1
        self.signal_plot = None


def test_configuracoes_salvas_valem_desde_a_criacao(_app):
    """O gráfico precisa nascer com as preferências do usuário, sem abrir a janela de config.

    Regressão: as preferências passaram a ser lidas DEPOIS do `engine.load()`, então o item
    era criado com `ctx.graph_settings` vazio e mantinha os defaults; só a abertura de
    "Configurações → Gráfico" (que reaplica tudo) corrigia a aparência — exatamente o que o
    usuário via ao começar uma coleta.
    """
    g = _grafico(_app)
    salvas = {"smoothing_enabled": True, "smoothing_window": 9, "line_width": 3.0,
              "grid_visible": False, "axis_labels_visible": False, "y_scale": 2.0}
    ctx = _CtxFalso(graph_settings=salvas)

    g.contexto = ctx      # é o que o QML faz ao criar o item

    assert g._suavizacao_ativa is True
    assert g._janela_suavizacao == 9
    assert g._largura_linha == 3.0
    assert g._grade_visivel is False
    assert g._rotulos_visiveis is False
    assert g._escala_y == 2.0
    assert ctx.signal_plot is g, "o gráfico deve se registrar como fachada no contexto"


def test_escala_pode_mudar_durante_a_gravacao(_app):
    """O slider da janela de configurações vale durante a sessão, como os botões +/-.

    Bloquear um e permitir o outro era inconsistente: os dois mexem no mesmo valor pelo mesmo
    caminho, e a escala é só exibição (a decimação guarda valores brutos).
    """
    g = _grafico(_app)
    g.contexto = _CtxFalso(graph_settings={"y_scale": 2.0})
    g.begin(30.0, 5.0)
    assert g._gravando is True

    g.apply_settings({"y_scale": 1.0})
    assert g._escala_y == 1.0, "a escala foi ignorada durante a gravação"


def test_escala_fora_da_faixa_do_sensor_e_limitada(_app):
    """Um valor salvo por outro sensor não pode jogar o traço para fora da tela."""
    g = _grafico(_app)
    g.contexto = _CtxFalso(graph_settings={})
    g.apply_settings({"y_scale": 999.0})
    assert g._escala_y == g._escala_max


def test_zoom_ao_vivo_e_slider_compartilham_o_mesmo_valor(_app):
    """Os botões +/- precisam publicar no ctx o valor que a janela de configurações lê."""
    g = _grafico(_app)
    ctx = _CtxFalso(graph_settings={"y_scale": 2.0})
    g.contexto = ctx
    antes = g._escala_y

    g.ampliar_zoom()

    assert g._escala_y < antes
    assert ctx.graph_settings["y_scale"] == g._escala_y


def test_contexto_sem_configuracoes_mantem_os_defaults(_app):
    """Sem preferências salvas (1ª execução), os defaults do sensor continuam valendo."""
    g = _grafico(_app)
    padrao_escala = g._escala_y
    g.contexto = _CtxFalso(graph_settings={})
    assert g._escala_y == padrao_escala


def test_decimacao_limita_pontos(_app):
    """120k amostras devem virar no máximo ~_COLUNAS_DECIMACAO pontos (custo constante)."""
    from compasso.gui_qt.signal_chart import _COLUNAS_DECIMACAO
    g = _grafico(_app)
    g.begin(60.0, 5.0)
    esc = g._escala_y
    _alimentar(g, 60.0, 120_000, lambda t: 0.6 * esc * math.sin(2 * math.pi * t))
    g.end()
    pontos = g._pontos_decimados()
    assert 1000 < len(pontos) <= _COLUNAS_DECIMACAO


def test_amostras_cruas_nao_sao_acumuladas(_app):
    """O custo de memória não cresce com o nº de amostras — só os baldes de decimação existem."""
    from compasso.gui_qt.signal_chart import _COLUNAS_DECIMACAO
    g = _grafico(_app)
    g.begin(60.0, 5.0)
    _alimentar(g, 60.0, 120_000, lambda t: 1.0)
    assert len(g._baldes) <= _COLUNAS_DECIMACAO
    assert not hasattr(g, "_tempos") and not hasattr(g, "_valores")


def test_eixo_x_relativo_ao_inicio_da_musica(_app):
    """O último ponto após o fim fica em ~ (duração - antecedência)."""
    g = _grafico(_app)
    g.begin(30.0, 5.0)
    _alimentar(g, 30.0, 3000, lambda t: 1.0)
    g.end()
    ultimo_t = g._pontos_decimados()[-1][0]
    assert abs(ultimo_t - (30.0 - 5.0)) < 0.2


def test_reset_idle_limpa(_app):
    g = _grafico(_app)
    g.begin(10.0, 2.0)
    _alimentar(g, 10.0, 500, lambda t: 1.0)
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


@pytest.mark.parametrize("dur, passo", [
    (20, 5), (60, 5), (120, 10), (300, 30), (900, 60),
])
def test_marcas_x_incluem_t0_e_sao_multiplas_do_passo(dur, passo):
    """As marcas ancoram em 0 (t0 sempre presente) e são múltiplos exatos do passo."""
    from compasso.gui_qt.signal_chart import _marcas_multiplas
    marcas = _marcas_multiplas(-5, dur, passo)
    assert 0 in marcas
    assert all(abs(m % passo) < 1e-6 for m in marcas)
    assert marcas == sorted(marcas)


@pytest.mark.parametrize("dur, largura_px", [
    (20, 400), (60, 400), (60, 900), (300, 400), (900, 500), (3600, 400),
])
def test_rotulos_do_eixo_x_nunca_se_sobrepoem(dur, largura_px):
    """O passo de rótulo escolhido garante o espaço mínimo entre textos vizinhos."""
    from compasso.gui_qt.signal_chart import (_passo_rotulo_x, _marcas_multiplas,
                                              _FOLGA_ROTULO_PX, _PASSOS_ROTULO_X)
    x_min, x_max = -5, dur
    largura_texto = 34
    passo = _passo_rotulo_x(x_min, x_max, largura_px, largura_texto)
    marcas = _marcas_multiplas(x_min, x_max, passo)
    escala = largura_px / (x_max - x_min)
    distancias = [(b - a) * escala for a, b in zip(marcas, marcas[1:])]
    # o passo mais esparso disponível pode não bastar para larguras absurdamente pequenas;
    # nesse caso exige-se apenas que ele tenha sido escolhido.
    if passo == _PASSOS_ROTULO_X[-1]:
        return
    assert all(d >= largura_texto + _FOLGA_ROTULO_PX for d in distancias)


@pytest.mark.parametrize("tema", ["Sereno", "Aurora"])
def test_grade_dos_temas_claros_e_discreta(_app, tema):
    """Nos temas claros a grade fica bem próxima do fundo, sem competir com o sinal.

    Regressão: a grade saía em ~#cdd0d4 sobre branco (a família de 1 s e a de 5 s eram ambas
    desenhadas nos múltiplos de 5, e as transparências se compunham), atrapalhando a leitura
    do traço.
    """
    from compasso.gui_qt.palettes import PALETTES
    g = _grafico(_app)
    g._paleta = dict(PALETTES[tema])
    assert g._eh_tema_claro()

    fundo = _qt.QColor(PALETTES[tema]["bar_bg"])
    base = g._cor_grade()
    menor = g._cor_grade_menor(base)

    def distancia(cor):
        """Diferença de luminância entre a grade composta sobre o fundo e o próprio fundo."""
        a = cor.alpha() / 255.0
        canais = [(cor.red(), fundo.red()), (cor.green(), fundo.green()), (cor.blue(), fundo.blue())]
        return max(abs((c * a + f * (1 - a)) - f) for c, f in canais)

    # a antiga grade dupla ficava a ~50 de distância do fundo; exige-se bem menos que isso.
    assert distancia(base) < 20, "grade de 5 s ainda escura demais para tema claro"
    assert distancia(menor) < distancia(base), "linha de 1 s deve ser mais apagada que a de 5 s"


def test_linhas_de_1s_nao_se_sobrepoem_as_de_5s(_app):
    """Cada instante recebe uma única linha, da família de maior destaque a que pertence."""
    from compasso.gui_qt.signal_chart import (_marcas_multiplas, _PASSO_MARCA_MENOR_S,
                                              _PASSO_MARCA_MEDIA_S)
    menores = [t for t in _marcas_multiplas(-5, 30, _PASSO_MARCA_MENOR_S)
               if abs(t) > 1e-6 and abs(t % _PASSO_MARCA_MEDIA_S) > 1e-6]
    medias = [t for t in _marcas_multiplas(-5, 30, _PASSO_MARCA_MEDIA_S) if abs(t) > 1e-6]
    assert not (set(menores) & set(medias))


@pytest.mark.parametrize("dur, largura_px", [
    (8, 1150), (18, 1150), (20, 1150), (30, 1150), (45, 1150),
])
def test_passo_de_rotulo_nunca_e_de_1_em_1(dur, largura_px):
    """O eixo tem a mesma aparência em qualquer faixa: rótulos sempre múltiplos de 5 s.

    Regressão do eixo "instável": com 1 s entre os candidatos, uma faixa de 18 s ganhava rótulo
    a cada segundo e uma de 30 s a cada 5 s, sem nada ter mudado no experimento.
    """
    from compasso.gui_qt.signal_chart import _passo_rotulo_x, _marcas_multiplas
    passo = _passo_rotulo_x(-5, dur, largura_px, 34)
    assert passo >= 5
    assert all(abs(m % 5) < 1e-6 for m in _marcas_multiplas(-5, dur, passo))
