"""Guarda de conexão com o BITalino simulado (modo de teste).

Conectar com o simulador ligado grava dados que **não são do participante** — é um engano
fácil (o modo fica ligado de uma sessão para a outra) e caro, porque só se descobre com a
coleta inteira já gravada. Estes testes travam o comportamento do aviso.
"""

import pytest

from PySide6.QtCore import QObject

from compasso.core import fake_bitalino


@pytest.fixture
def controller(monkeypatch):
    """ConnectionController com um contexto mínimo e sem tocar em LSL."""
    from compasso.gui_qt.controllers.connection_controller import ConnectionController

    ctx = QObject()
    ctx.handle_connection_lost = None
    ctx.bitalino = None
    ctx.runner = None
    ctrl = ConnectionController(ctx)

    # `conectar` faria uma conexão real em thread; aqui só registramos a chamada.
    chamadas = []
    monkeypatch.setattr(ctrl, "conectar", lambda mac: chamadas.append(mac))
    ctrl.chamadas_conectar = chamadas
    return ctrl


def test_sem_simulacao_conecta_direto(controller, monkeypatch):
    monkeypatch.setattr(fake_bitalino, "esta_ativo", lambda: False)
    pedidos = []
    controller.pedirConfirmarConectarTeste.connect(pedidos.append)

    controller.solicitar_conectar("AA:BB:CC:DD:EE:FF")

    assert controller.chamadas_conectar == ["AA:BB:CC:DD:EE:FF"]
    assert pedidos == [], "não deveria pedir confirmação sem modo de teste"


def test_com_simulacao_pede_confirmacao_em_vez_de_conectar(controller, monkeypatch):
    """O clique não pode conectar direto: o usuário precisa ver o aviso primeiro."""
    monkeypatch.setattr(fake_bitalino, "esta_ativo", lambda: True)
    pedidos = []
    controller.pedirConfirmarConectarTeste.connect(pedidos.append)

    controller.solicitar_conectar("20:17:09:18:60:29")

    assert controller.chamadas_conectar == [], "conectou sem confirmação com o teste ligado"
    assert pedidos == ["20:17:09:18:60:29"], "o MAC precisa viajar até a resposta do diálogo"


def test_mac_sobrevive_ao_pedido_de_confirmacao(controller, monkeypatch):
    """O diálogo responde depois; o MAC tem de chegar intacto para o 'Sim' funcionar."""
    monkeypatch.setattr(fake_bitalino, "esta_ativo", lambda: True)
    recebidos = []
    controller.pedirConfirmarConectarTeste.connect(recebidos.append)

    controller.solicitar_conectar("aa:bb:cc:dd:ee:ff")
    # o QML devolve o mesmo valor ao confirmar:
    controller.conectar(recebidos[0])

    assert controller.chamadas_conectar == ["aa:bb:cc:dd:ee:ff"]
