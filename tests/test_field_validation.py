"""Validação de entrada dos formulários (mensagens por campo expostas ao QML).

Cada propriedade `erroX` devolve a mensagem a exibir sob o campo, ou "" quando está tudo certo.
A view não repete nenhuma regra: a borda vermelha é apenas `erro !== ""`. Aqui testa-se a regra;
a aparência (borda/label) não é coberta, como o resto da suíte não cobre renderização QML.
"""

import types

import pytest

pytest.importorskip("PySide6.QtCore")

from compasso.core import calibration                                       # noqa: E402
from compasso.gui_qt.controllers.config_controller import ConfigController  # noqa: E402


@pytest.fixture
def cfg():
    ctx = types.SimpleNamespace()
    return ConfigController(ctx)


# --------------------------------------------------------------------- MAC
@pytest.mark.parametrize("mac", [
    "20:17:09:18:60:29",
    "20 17 09 18 60 29",
    "20-17-09-18-60-29",
    "AA:bb:CC:dd:EE:ff",     # hexadecimal em qualquer caixa
])
def test_mac_valido_nao_gera_erro(cfg, mac):
    cfg.bitalinoMac = mac
    assert cfg.erroMac == ""


@pytest.mark.parametrize("mac", [
    "20:17:09:18:60",           # 5 grupos
    "20:17:09:18:60:29:31",     # 7 grupos
    "20:17:09:18:60:2G",        # 'G' não é hexadecimal
    "201709186029",             # sem separador
    "meu bitalino",
])
def test_mac_invalido_gera_erro(cfg, mac):
    cfg.bitalinoMac = mac
    assert cfg.erroMac != ""


def test_mac_vazio_nao_e_tratado_como_invalido(cfg):
    """Campo ainda não preenchido não é erro — evita a janela abrir toda vermelha."""
    cfg.bitalinoMac = ""
    assert cfg.erroMac == ""


def test_regra_do_mac_e_a_mesma_da_conexao(cfg):
    """O campo aceita exatamente o que `connectar_bitalino` aceita (mesma MAC_RE)."""
    from compasso.core.bitalino_connect import MAC_RE
    for mac in ("20:17:09:18:60:29", "20 17 09 18 60 29", "AB-CD-EF-01-23-45", "xx:yy"):
        cfg.bitalinoMac = mac
        assert (cfg.erroMac == "") == bool(MAC_RE.match(mac))


# ----------------------------------------------------------------- colunas
def test_colunas_iguais_geram_erro(cfg):
    cfg.musicColumn = "musica"
    cfg.factorColumn = "musica"
    assert cfg.erroColunas != ""


def test_colunas_diferentes_nao_geram_erro(cfg):
    cfg.musicColumn = "musica"
    cfg.factorColumn = "fator"
    assert cfg.erroColunas == ""


def test_coluna_ainda_nao_escolhida_nao_gera_erro(cfg):
    """Com uma das colunas vazia não há o que comparar (planilha recém-carregada)."""
    cfg.musicColumn = ""
    cfg.factorColumn = ""
    assert cfg.erroColunas == ""


# --------------------------------------------------------------- quantidades
@pytest.mark.parametrize("valor", ["0", "3", "10"])
def test_quantidade_de_ruido_valida(cfg, valor):
    cfg.noiseQuantity = valor
    assert cfg.erroNoiseQuantity == ""


@pytest.mark.parametrize("valor", ["2.5", "abc", "-1", "3,5"])
def test_quantidade_de_ruido_invalida(cfg, valor):
    cfg.noiseQuantity = valor
    assert cfg.erroNoiseQuantity != ""


def test_quantidade_de_musicas_exige_pelo_menos_uma(cfg):
    cfg.musicQuantity = "0"
    assert cfg.erroMusicQuantity != ""
    cfg.musicQuantity = "1"
    assert cfg.erroMusicQuantity == ""


@pytest.mark.parametrize("campo, prop", [
    ("musicQuantity", "erroMusicQuantity"),
    ("noiseQuantity", "erroNoiseQuantity"),
])
def test_quantidade_vazia_nao_e_tratada_como_invalida(cfg, campo, prop):
    setattr(cfg, campo, "")
    assert getattr(cfg, prop) == ""


# --------------------------------------------------------------------- beep
def test_beep_depois_do_inicio_do_audio_gera_erro(cfg):
    cfg.beepEnabled = True
    cfg.preStimulus = 5
    cfg.beepLead = 5          # tocaria junto com o áudio, não antes
    assert cfg.erroBeep != ""
    assert cfg.beepInvalido


def test_beep_antes_do_audio_nao_gera_erro(cfg):
    cfg.beepEnabled = True
    cfg.preStimulus = 5
    cfg.beepLead = 2
    assert cfg.erroBeep == ""


def test_beep_desligado_nunca_gera_erro(cfg):
    cfg.beepEnabled = False
    cfg.preStimulus = 5
    cfg.beepLead = 10
    assert cfg.erroBeep == ""


# -------------------------------------------------------------- calibração
def test_diferenca_de_volume_acima_do_limite_gera_erro():
    """A regra continua no core; o controller só a traduz para a tela."""
    erros = calibration.validar_parametros(
        10, 10 + calibration.CALIB_DIFF_MAX + 1,
        calibration.CALIB_STEP_PCT_DEFAULT, calibration.CALIB_STEP_SEG_DEFAULT)
    assert any(str(calibration.CALIB_DIFF_MAX) in e for e in erros)


def test_diferenca_de_volume_no_limite_e_aceita():
    erros = calibration.validar_parametros(
        10, 10 + calibration.CALIB_DIFF_MAX,
        calibration.CALIB_STEP_PCT_DEFAULT, calibration.CALIB_STEP_SEG_DEFAULT)
    assert erros == []
