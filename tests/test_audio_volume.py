"""Controle de volume do sistema (multiplataforma) — tudo mockado, sem tocar no SO real."""

import types

import pytest

from compasso.core import audio


@pytest.fixture(autouse=True)
def _reset_unavailable_flag():
    """Zera o flag de log-uma-vez entre testes (estado de módulo)."""
    audio._unavailable_logged = False
    yield
    audio._unavailable_logged = False


# ----------------------------- set_system_volume --------------------------- #
def test_set_volume_clamps_above_100(mocker):
    mocker.patch("compasso.core.audio.platform.system", return_value="Darwin")
    run = mocker.patch("compasso.core.audio.subprocess.run")
    audio.set_system_volume(150)
    # o comando enviado deve conter 100 (limitado)
    args = run.call_args.args[0]
    assert "set volume output volume 100" in " ".join(args)


def test_set_volume_clamps_below_0(mocker):
    mocker.patch("compasso.core.audio.platform.system", return_value="Darwin")
    run = mocker.patch("compasso.core.audio.subprocess.run")
    audio.set_system_volume(-20)
    args = run.call_args.args[0]
    assert "set volume output volume 0" in " ".join(args)


def test_set_volume_windows_uses_pycaw(mocker):
    mocker.patch("compasso.core.audio.platform.system", return_value="Windows")
    fake_device = mocker.MagicMock()
    mocker.patch("compasso.core.audio.AudioUtilities.GetSpeakers", return_value=fake_device)
    ok = audio.set_system_volume(50)
    assert ok is True
    fake_device.EndpointVolume.SetMasterVolumeLevelScalar.assert_called_once()
    scalar = fake_device.EndpointVolume.SetMasterVolumeLevelScalar.call_args.args[0]
    assert scalar == pytest.approx(0.5)


def test_set_volume_unsupported_os_returns_false(mocker):
    mocker.patch("compasso.core.audio.platform.system", return_value="Plan9")
    assert audio.set_system_volume(50) is False


def test_set_volume_returns_false_on_exception(mocker):
    mocker.patch("compasso.core.audio.platform.system", return_value="Linux")
    mocker.patch("compasso.core.audio.subprocess.run", side_effect=OSError("amixer ausente"))
    assert audio.set_system_volume(50) is False


# ----------------------------- get_system_volume --------------------------- #
def test_get_volume_windows_scales_to_100(mocker):
    mocker.patch("compasso.core.audio.platform.system", return_value="Windows")
    fake_device = mocker.MagicMock()
    fake_device.EndpointVolume.GetMasterVolumeLevelScalar.return_value = 0.75
    mocker.patch("compasso.core.audio.AudioUtilities.GetSpeakers", return_value=fake_device)
    assert audio.get_system_volume() == pytest.approx(75.0)


def test_get_volume_macos_parses_output(mocker):
    mocker.patch("compasso.core.audio.platform.system", return_value="Darwin")
    result = types.SimpleNamespace(stdout="42\n")
    mocker.patch("compasso.core.audio.subprocess.run", return_value=result)
    assert audio.get_system_volume() == pytest.approx(42.0)


def test_get_volume_falls_back_to_50_on_error(mocker):
    mocker.patch("compasso.core.audio.platform.system", return_value="Linux")
    mocker.patch("compasso.core.audio.subprocess.run", side_effect=OSError("erro"))
    assert audio.get_system_volume() == pytest.approx(50.0)


def test_get_volume_unsupported_os_returns_50(mocker):
    mocker.patch("compasso.core.audio.platform.system", return_value="Plan9")
    assert audio.get_system_volume() == pytest.approx(50.0)
