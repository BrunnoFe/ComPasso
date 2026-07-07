"""Validação/normalização de endereço MAC nos dois módulos que a fazem.

- ``compasso.core.bitalino_connect.MAC_RE``: aceita separadores ``:``, espaço e ``-`` e é
  usada por ``connectar_bitalino`` para NORMALIZAR para a forma ``AA:BB:..`` maiúscula.
- ``compasso.core.config_manager.MAC_REGEX``: validação do campo no .config (``:`` ou espaço).

Os caminhos de hardware de ``connectar_bitalino`` são exercitados só o suficiente para
provar a normalização e a rejeição — ``resolve_byprop``/``StreamInlet`` são mockados.
"""

import pytest

from compasso.core.bitalino_connect import MAC_RE, connectar_bitalino
from compasso.core.config_manager import MAC_REGEX


# ----------------------- MAC_RE (bitalino_connect) ------------------------- #
@pytest.mark.parametrize("mac", [
    "20:17:09:18:60:29",
    "20 17 09 18 60 29",
    "20-17-09-18-60-29",
    "aa:bb:cc:dd:ee:ff",
    "AA:BB:CC:DD:EE:FF",
])
def test_mac_re_accepts_valid_separators(mac):
    assert MAC_RE.match(mac) is not None


@pytest.mark.parametrize("mac", [
    "20:17:09:18:60",        # poucos grupos
    "20:17:09:18:60:29:30",  # grupos demais
    "201:17:09:18:60:29",    # grupo com 3 dígitos
    "2G:17:09:18:60:29",     # caractere não-hex
    "",                       # vazio
    "20:17:09:18:60:2",      # último grupo com 1 dígito
])
def test_mac_re_rejects_invalid(mac):
    assert MAC_RE.match(mac) is None


def test_connectar_normalizes_mac_to_upper_colon(mocker):
    """MAC com espaços e minúsculas deve ser normalizado para 'AA:BB:..' antes de resolver."""
    fake_inlet = mocker.MagicMock()
    fake_inlet.info.return_value.nominal_srate.return_value = 100.0
    fake_inlet.info.return_value.channel_count.return_value = 6
    fake_inlet.pull_sample.return_value = ([1.0], 123.0)

    resolve = mocker.patch("compasso.core.bitalino_connect.resolve_byprop",
                           return_value=[object()])
    mocker.patch("compasso.core.bitalino_connect.StreamInlet", return_value=fake_inlet)

    result = connectar_bitalino("aa bb cc dd ee ff")

    assert result is fake_inlet
    # o valor passado a resolve_byprop deve ser a forma normalizada maiúscula com ':'
    assert resolve.call_args.kwargs["value"] == "AA:BB:CC:DD:EE:FF"


def test_connectar_invalid_mac_returns_error_string(mocker):
    # MAC inválido não deve nem tentar resolver
    resolve = mocker.patch("compasso.core.bitalino_connect.resolve_byprop")
    result = connectar_bitalino("not-a-mac")
    assert isinstance(result, str)
    assert "inválido" in result.lower()
    resolve.assert_not_called()


def test_connectar_returns_error_when_pull_fails(mocker):
    fake_inlet = mocker.MagicMock()
    fake_inlet.info.return_value.nominal_srate.return_value = 100.0
    fake_inlet.info.return_value.channel_count.return_value = 6
    fake_inlet.pull_sample.side_effect = Exception("sem amostras")
    mocker.patch("compasso.core.bitalino_connect.resolve_byprop", return_value=[object()])
    mocker.patch("compasso.core.bitalino_connect.StreamInlet", return_value=fake_inlet)

    result = connectar_bitalino("20:17:09:18:60:29")
    assert isinstance(result, str)
    assert "Lab Streaming Layer" in result


# ----------------------- MAC_REGEX (config_manager) ------------------------ #
@pytest.mark.parametrize("mac", [
    "20:17:09:18:60:29",
    "20 17 09 18 60 29",
    "AA:BB:CC:DD:EE:FF",
])
def test_config_mac_regex_accepts(mac):
    assert MAC_REGEX.match(mac) is not None


@pytest.mark.parametrize("mac", [
    "20-17-09-18-60-29",   # config_manager NÃO aceita hífen (só ':' e espaço)
    "20:17:09:18:60",
    "2G:17:09:18:60:29",
    "",
])
def test_config_mac_regex_rejects(mac):
    assert MAC_REGEX.match(mac) is None
