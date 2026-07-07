"""Lógica de pré-requisitos do botão 'começar' (DownFrame), sem renderizar a GUI.

``_validar_prerequisitos`` só lê ``self.ctx``; chamamos o método de forma desacoplada
(via ``__func__`` sobre um objeto falso com ``.ctx``), evitando construir o widget CTk
— coerente com a estratégia de testar a lógica, não a renderização.
"""

import types

from compasso.gui.frames.bottom_frame import DownFrame

_validar = DownFrame._validar_prerequisitos


def _ctx(**kwargs):
    base = dict(config_loaded=True, bitalino=object(), infos_saved=True,
                music_files=["a.mp3"], save_dir="/saida", runner=None)
    base.update(kwargs)
    return types.SimpleNamespace(**base)


def _call(ctx):
    return _validar(types.SimpleNamespace(ctx=ctx))


def test_all_prereqs_met_returns_empty():
    assert _call(_ctx()) == ""


def test_missing_config():
    assert "configuração" in _call(_ctx(config_loaded=False))


def test_missing_bitalino():
    assert "Bitalino" in _call(_ctx(bitalino=None))


def test_infos_not_saved():
    assert "informações do participante" in _call(_ctx(infos_saved=False))


def test_no_music_files():
    assert "música" in _call(_ctx(music_files=[]))


def test_no_save_dir():
    assert "diretório" in _call(_ctx(save_dir=None))


def test_already_running():
    runner = types.SimpleNamespace(is_running=lambda: True)
    assert "andamento" in _call(_ctx(runner=runner))


def test_runner_not_running_is_ok():
    runner = types.SimpleNamespace(is_running=lambda: False)
    assert _call(_ctx(runner=runner)) == ""


def test_prereqs_checked_in_priority_order():
    # faltando vários: a mensagem da configuração (1ª checagem) tem prioridade
    msg = _call(_ctx(config_loaded=False, bitalino=None, infos_saved=False,
                     music_files=[], save_dir=None))
    assert "configuração" in msg
