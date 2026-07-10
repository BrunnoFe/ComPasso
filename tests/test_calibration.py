"""core/calibration: validação de parâmetros e cálculo da rampa de volume (lógica pura)."""

import pytest

from compasso.core import calibration as cal


# --------------------------- validar_parametros ---------------------------- #
def test_validar_parametros_defaults_ok():
    # os defaults da sessão devem ser sempre válidos.
    assert cal.validar_parametros(
        cal.CALIB_VOL_MIN_DEFAULT, cal.CALIB_VOL_MAX_DEFAULT,
        cal.CALIB_STEP_PCT_DEFAULT, cal.CALIB_STEP_SEG_DEFAULT) == []


def test_validar_parametros_aceita_strings_de_digitos():
    assert cal.validar_parametros("30", "50", 1, 1) == []


@pytest.mark.parametrize("valor", ["", " ", "abc", "1.5", "-3", None])
def test_validar_parametros_volume_nao_inteiro(valor):
    erros = cal.validar_parametros(valor, 50, 1, 1)
    assert any("Volume minimo" in e for e in erros)


def test_validar_parametros_volume_fora_do_intervalo():
    erros = cal.validar_parametros(30, 150, 1, 1)
    assert any("Volume maximo" in e for e in erros)


def test_validar_parametros_minimo_maior_que_maximo():
    erros = cal.validar_parametros(60, 40, 1, 1)
    assert any("nao pode ser maior" in e for e in erros)


def test_validar_parametros_diferenca_acima_do_maximo():
    # 10 -> 90 = diferença de 80 (> CALIB_DIFF_MAX = 40)
    erros = cal.validar_parametros(10, 90, 1, 1)
    assert any("diferenca" in e for e in erros)


def test_validar_parametros_diferenca_no_limite_ok():
    # 30 -> 70 = exatamente 40, aceito.
    assert cal.validar_parametros(30, 70, 1, 1) == []


@pytest.mark.parametrize("passo", [0, 6, "x"])
def test_validar_parametros_passo_fora_da_faixa(passo):
    erros = cal.validar_parametros(30, 50, passo, 1)
    assert any("Passo de volume" in e for e in erros)


@pytest.mark.parametrize("intervalo", [0, 6, "x"])
def test_validar_parametros_intervalo_fora_da_faixa(intervalo):
    erros = cal.validar_parametros(30, 50, 1, intervalo)
    assert any("Intervalo de aumento" in e for e in erros)


# --------------------------- numero_de_incrementos ------------------------- #
@pytest.mark.parametrize("vmin, vmax, passo, esperado", [
    (30, 50, 1, 20),
    (30, 50, 5, 4),
    (30, 50, 3, 7),    # 20/3 -> arredonda para cima
    (30, 30, 1, 0),    # sem intervalo
    (50, 30, 1, 0),    # máximo <= mínimo
])
def test_numero_de_incrementos(vmin, vmax, passo, esperado):
    assert cal.numero_de_incrementos(vmin, vmax, passo) == esperado


# --------------------------- duracao_estimada ------------------------------ #
def test_duracao_estimada_inclui_hold():
    # 30->50 com passo 1 a cada 2 s: 20 degraus * 2 s + 2 s de hold = 42 s.
    d = cal.duracao_estimada_segundos(30, 50, 1, 2)
    assert d == pytest.approx(20 * 2 + cal.CALIB_HOLD_SEGUNDOS)


def test_duracao_estimada_hold_customizavel():
    d = cal.duracao_estimada_segundos(30, 50, 5, 1, hold_seg=0)
    assert d == pytest.approx(4 * 1)


# --------------------------- volume_no_incremento -------------------------- #
def test_volume_no_incremento_progride_e_limita_no_maximo():
    assert cal.volume_no_incremento(0, 30, 50, 5) == 30
    assert cal.volume_no_incremento(2, 30, 50, 5) == 40
    assert cal.volume_no_incremento(4, 30, 50, 5) == 50
    # além do necessário: nunca ultrapassa o máximo.
    assert cal.volume_no_incremento(10, 30, 50, 5) == 50


def test_volume_no_incremento_resto_ainda_limita():
    # passo 3: 30,33,...,48,50(limitado) — o último degrau não passa de 50.
    assert cal.volume_no_incremento(6, 30, 50, 3) == 48
    assert cal.volume_no_incremento(7, 30, 50, 3) == 50
