"""Volume durante o experimento: o app não escreve, mas acompanha o que o SO fizer.

Regra de coleta, não só de UI: a partir do "Começar", o volume das faixas tem de ser o mesmo
do início ao fim, e qualquer alteração precisa ser deliberada do usuário pelo sistema
operacional — nunca um efeito colateral da interface. O slider fica travado e o backend não
chama ``set_system_volume``; em troca, um timer sincroniza o slider com o volume real do SO.
"""

import pytest

from PySide6.QtCore import QObject


class RunnerFalso:
    def __init__(self, rodando=False, adquirindo=False):
        self._rodando = rodando
        self._adquirindo = adquirindo

    def is_running(self):
        return self._rodando

    def is_acquiring(self):
        return self._adquirindo


class CtxFalso(QObject):
    """Superfície mínima do Context usada pelo PlayerController."""

    def __init__(self):
        super().__init__()
        self.runner = None
        self.player = None
        self.volume_calibrado = None
        self.volume_travado = False
        self.calibracao_habilitada = False
        self.calibracao_caminho = None
        self.atualizar_botao_calibrar = None
        self.aplicar_volume_calibrado = None
        self.calibrarVisible = False
        self._textos = {}

        class _Var:
            def __init__(self, dono, chave):
                self._dono, self._chave = dono, chave

            def set(self, v):
                self._dono._textos[self._chave] = v

            def get(self):
                return self._dono._textos.get(self._chave, "")

        self.volume_text = _Var(self, "volume")
        self.status_text = _Var(self, "status")
        self.time_begin_text = _Var(self, "ini")
        self.time_end_text = _Var(self, "fim")

    def notify_stepper(self):
        pass


@pytest.fixture(scope="module")
def _app():
    """QTimer só arma com uma aplicação Qt viva (a plataforma offscreen vem do conftest)."""
    from PySide6.QtGui import QGuiApplication

    return QGuiApplication.instance() or QGuiApplication([])


@pytest.fixture
def player(_app, monkeypatch):
    """PlayerController com o volume do sistema simulado por uma variável."""
    from compasso.gui_qt.controllers import player_controller as pc_mod

    estado = {"sistema": 20, "escritas": []}

    def set_falso(v):
        estado["sistema"] = int(v)
        estado["escritas"].append(int(v))
        return True

    def get_falso(padrao=50.0):
        return float(estado["sistema"])

    monkeypatch.setattr(pc_mod, "set_system_volume", set_falso)
    monkeypatch.setattr(pc_mod, "get_system_volume", get_falso)

    ctx = CtxFalso()
    ctrl = pc_mod.PlayerController(ctx)
    ctrl._timer_progresso.stop()          # os testes disparam os passos manualmente
    ctrl._timer_sinc_volume.stop()
    ctrl._estado = estado
    ctrl._ctx_falso = ctx
    return ctrl


def aplicar_debounce(player):
    """Simula o disparo do timer de debounce (single-shot: o Qt o desarma ao disparar)."""
    player._timer_volume.stop()
    player._aplicar_volume_pendente()


# --------------------------------------------------------------------------- #
# O app não escreve no volume depois que o experimento começa
# --------------------------------------------------------------------------- #
def test_fora_da_sessao_o_slider_aplica_normalmente(player):
    player.definir_volume(12)
    aplicar_debounce(player)
    assert player._estado["sistema"] == 12
    assert player.volume == 12


def test_durante_a_sessao_o_slider_e_ignorado(player):
    player.definir_volume(12)
    aplicar_debounce(player)
    player._ctx_falso.runner = RunnerFalso(rodando=True)

    player.definir_volume(90)

    assert player._estado["sistema"] == 12, "o app alterou o volume com o experimento rodando"
    assert player.volume == 12


def test_entre_faixas_tambem_e_ignorado(player):
    """Sessão rodando mas sem aquisição (esperando o 'Continuar') ainda é sessão."""
    player._ctx_falso.runner = RunnerFalso(rodando=True, adquirindo=False)
    player.definir_volume(90)
    assert player._estado["escritas"] == []


def test_escrita_pendente_nao_vaza_para_dentro_da_sessao(player):
    """Um debounce disparado depois do início do experimento não pode aplicar."""
    player.definir_volume(35)                      # agenda a escrita
    player._ctx_falso.runner = RunnerFalso(rodando=True)   # experimento começa antes do timer
    aplicar_debounce(player)
    assert player._estado["escritas"] == []


def test_volume_calibrado_nao_se_aplica_durante_a_sessao(player):
    player._ctx_falso.runner = RunnerFalso(rodando=True)
    player.aplicar_volume_calibrado(80)
    assert player._estado["escritas"] == []


def test_slider_trava_durante_toda_a_sessao(player):
    player._atualizar_progresso()
    assert player.volumeTravado is False

    player._ctx_falso.runner = RunnerFalso(rodando=True, adquirindo=False)
    player._atualizar_progresso()
    assert player.volumeTravado is True, "slider destravado entre faixas"


# --------------------------------------------------------------------------- #
# Sincronização com o volume real do SO
# --------------------------------------------------------------------------- #
def test_sincroniza_quando_o_usuario_muda_pelo_sistema(player):
    player.definir_volume(12)
    aplicar_debounce(player)

    player._estado["sistema"] = 70          # usuário mexeu na bandeja do Windows
    player._sincronizar_volume_do_sistema()

    assert player.volume == 70
    assert player._ctx_falso._textos["volume"] == "70%"


def test_sincroniza_tambem_durante_a_sessao(player):
    """Durante o experimento o SO é a única via — a UI precisa refletir a verdade."""
    player._ctx_falso.runner = RunnerFalso(rodando=True)
    player._estado["sistema"] = 33
    player._sincronizar_volume_do_sistema()
    assert player.volume == 33


def test_sincronizacao_nunca_escreve_no_sistema(player):
    player._estado["sistema"] = 44
    player._sincronizar_volume_do_sistema()
    assert player._estado["escritas"] == [], "a sincronização escreveu de volta no sistema"


def test_sincronizacao_nao_atropela_o_slider_em_movimento(player):
    """Com uma escrita nossa pendente (debounce ativo), a leitura não pode reverter o arrasto."""
    player.definir_volume(12)               # deixa o timer de debounce ativo
    assert player._timer_volume.isActive()
    player._estado["sistema"] = 20          # o SO ainda tem o valor antigo
    player._sincronizar_volume_do_sistema()
    assert player.volume == 12, "a sincronização desfez o que o usuário acabou de arrastar"


def test_falha_de_leitura_nao_puxa_o_volume_para_o_padrao(player, monkeypatch):
    """`get_system_volume` devolve 50 em erro; adotar esse 50 causaria o bug relatado."""
    from compasso.gui_qt.controllers import player_controller as pc_mod

    player.definir_volume(12)
    aplicar_debounce(player)
    monkeypatch.setattr(pc_mod, "get_system_volume", lambda padrao=50.0: padrao)

    player._sincronizar_volume_do_sistema()

    assert player.volume == 12, "a UI adotou o 50 de fallback como se fosse o volume real"
    assert player._estado["escritas"] == [12]


def test_get_system_volume_permite_distinguir_falha_de_valor():
    """Contrato do `padrao=None`: quem age sobre a leitura precisa saber que ela falhou."""
    import platform

    from compasso.core import audio

    if platform.system() not in ("Windows", "Darwin", "Linux"):
        pytest.skip("plataforma sem caminho de leitura")
    # força o ramo de indisponibilidade sem depender do SO real.
    original = audio.AudioUtilities
    try:
        audio.AudioUtilities = None
        if platform.system() == "Windows":
            assert audio.get_system_volume(padrao=None) is None
            assert audio.get_system_volume() == 50.0
    finally:
        audio.AudioUtilities = original
