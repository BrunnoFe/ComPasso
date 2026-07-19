"""Controller da janela "Configurações → App".

Cobre a lógica própria do controller — o que não é mera passagem para ``app_prefs``: parsing
das listas digitadas como texto, detecção do que exige reinício e o ciclo abrir/cancelar.
A renderização do QML não é testada aqui (ver tests/README.md).
"""

import pytest

from PySide6.QtCore import QObject

from compasso.core import app_prefs


@pytest.fixture
def controller(monkeypatch):
    """Controller ligado a um contexto mínimo, sem tocar o prefs.json real."""
    from compasso.gui_qt.controllers.app_settings_controller import AppSettingsController

    app_prefs._cache = app_prefs.padroes()
    # `definir` gravaria em disco: substituído por uma escrita no cache em memória.
    def definir_falso(novas):
        limpo, erros = app_prefs.validar(novas)
        app_prefs._cache = limpo
        return erros

    monkeypatch.setattr(app_prefs, "definir", definir_falso)

    ctrl = AppSettingsController(QObject())
    ctrl.abrir()
    return ctrl


# --------------------------------------------------------------------------- #
# Parsing das listas digitadas como texto
# --------------------------------------------------------------------------- #
def test_extensoes_recebem_ponto_automaticamente(controller):
    """O usuário digitar "wav" em vez de ".wav" é erro óbvio e correção óbvia."""
    controller.extensoesAudio = "wav, mp3"
    assert controller.extensoesAudio == ".wav, .mp3"


def test_extensoes_preservam_ponto_existente(controller):
    controller.extensoesAudio = ".wav, .flac"
    assert controller.extensoesAudio == ".wav, .flac"


def test_extensoes_ignoram_espacos_e_itens_vazios(controller):
    controller.extensoesAudio = "  .wav ,, .ogg  ,  "
    assert controller.extensoesAudio == ".wav, .ogg"


def test_extensoes_normalizam_maiusculas(controller):
    controller.extensoesAudio = ".WAV, .Mp3"
    assert controller.extensoesAudio == ".wav, .mp3"


def test_palavras_ruido_preservam_caixa_e_acento(controller):
    """A comparação é feita sem caixa no core; aqui o texto do usuário é preservado."""
    controller.palavrasRuido = "Ruído, Silêncio"
    assert controller.palavrasRuido == "Ruído, Silêncio"


# --------------------------------------------------------------------------- #
# Formato de timestamp (rótulo legível <-> formato strftime)
# --------------------------------------------------------------------------- #
def test_definir_timestamp_por_rotulo(controller):
    rotulo_iso = [r for r in controller.rotulosTimestamp if "ISO" in r][0]
    controller.definir_timestamp_por_rotulo(rotulo_iso)
    assert controller.formatoTimestamp == "%Y-%m-%d_%H-%M-%S"
    assert controller.rotuloTimestampAtual == rotulo_iso


def test_rotulo_desconhecido_nao_altera_nada(controller):
    antes = controller.formatoTimestamp
    controller.definir_timestamp_por_rotulo("Formato inventado")
    assert controller.formatoTimestamp == antes


# --------------------------------------------------------------------------- #
# Reinício e ciclo de edição
# --------------------------------------------------------------------------- #
def test_mudanca_comum_nao_pede_reinicio(controller):
    controller.gerarXlsx = False
    controller.salvar()
    assert controller.pendenteReinicio is False


@pytest.mark.parametrize("propriedade, valor", [
    ("escalaUi", 125),
    ("nivelLog", "DEBUG"),
    ("retencaoLogs", 60),
])
def test_preferencias_de_arranque_pedem_reinicio(controller, propriedade, valor):
    setattr(controller, propriedade, valor)
    controller.salvar()
    assert controller.pendenteReinicio is True


def test_ha_alteracoes_detecta_edicao(controller):
    assert controller.ha_alteracoes() is False
    controller.lslTimeout = 9
    assert controller.ha_alteracoes() is True


def test_cancelar_reverte_ao_snapshot(controller):
    original = controller.lslTimeout
    controller.lslTimeout = 12
    controller.cancelar()
    assert controller.lslTimeout == original
    assert controller.ha_alteracoes() is False


def test_salvar_adota_novo_snapshot(controller):
    """Depois de salvar, o estado salvo vira a linha de base (senão o cancelar reverteria)."""
    controller.lslTimeout = 9
    controller.salvar()
    assert controller.ha_alteracoes() is False
    controller.cancelar()
    assert controller.lslTimeout == 9


def test_restaurar_padroes_afeta_os_campos_sem_salvar(controller):
    controller.idadeMinima = 30
    controller.restaurar_padroes()
    assert controller.idadeMinima == app_prefs.padroes()["idade_minima"]


def test_avancado_nasce_bloqueado_a_cada_abertura(controller):
    """O consentimento vale por abertura da janela, não para sempre."""
    controller.avancadoLiberado = True
    controller.abrir()
    assert controller.avancadoLiberado is False


def test_salvar_valor_invalido_corrige_e_avisa(controller):
    """Valor fora de faixa cai no padrão e a UI passa a refletir o que ficou salvo."""
    avisos = []
    controller.mensagem.connect(lambda t, x, tipo: avisos.append((t, x, tipo)))
    controller.idadeMinima = 90
    controller.idadeMaxima = 10          # faixa invertida
    controller.salvar()
    assert controller.idadeMinima <= controller.idadeMaxima
    assert avisos and avisos[0][2] == "warning"
