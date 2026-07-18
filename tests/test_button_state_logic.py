"""Lógica de pré-requisitos do botão 'começar', sem renderizar a GUI.

``validar_prerequisitos`` é uma função pura que só lê o ``ctx`` — testamos a lógica, não a
renderização (a UI QML não é testada em unidade). Foi extraída do antigo DownFrame para o
``experiment_controller`` durante a migração para PySide6/QML.
"""

import types

from compasso.gui_qt.controllers.experiment_controller import validar_prerequisitos


def _ctx(**kwargs):
    base = dict(config_loaded=True, bitalino=object(), infos_saved=True,
                music_files=["a.mp3"], save_dir="/saida", runner=None)
    base.update(kwargs)
    return types.SimpleNamespace(**base)


def _call(ctx):
    return validar_prerequisitos(ctx)


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
