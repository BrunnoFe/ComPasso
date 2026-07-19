"""Contrato de superfície do ``Player`` (backend QtMultimedia).

O ``Player`` é consumido como um objeto estável (``ctx.player``) por três chamadores que NÃO
conhecem o backend: ``ExperimentRunner`` (thread worker) e os controllers de player/calibração
(thread da GUI). Este teste trava a superfície pública — os nomes e as assinaturas dos métodos —
para que uma troca de backend (ex.: pygame -> QtMultimedia) permaneça *drop-in*.

Não exercita reprodução real (headless não toca áudio de forma confiável) nem instancia o
``Player`` (exigiria uma ``QGuiApplication`` + event loop). Ver ``tests/README.md`` sobre o que
é deliberadamente não coberto. A reprodução ponta-a-ponta é validada manualmente no app.
"""

import inspect

from compasso.core.player import Player

# método -> parâmetros esperados (além de self), na ordem. É o contrato usado pelos chamadores.
API_ESPERADA = {
    "load": ["path"],
    "play": [],
    "stop": [],
    "is_busy": [],
    "aguardar_fim": ["timeout"],
    "get_pos": [],
    "get_length": [],
    # o beep é carregado uma vez no arranque; tocar não recebe caminho.
    "play_beep": [],
    "preload_beep": ["path"],
}


def test_player_expoe_a_api_publica():
    """Todos os métodos do contrato existem e são invocáveis."""
    for nome in API_ESPERADA:
        metodo = getattr(Player, nome, None)
        assert metodo is not None, f"Player não expõe '{nome}'"
        assert callable(metodo), f"Player.{nome} não é invocável"


def test_player_mantem_as_assinaturas():
    """As assinaturas batem com o que os chamadores usam (mantém o Player drop-in)."""
    for nome, params_esperados in API_ESPERADA.items():
        sig = inspect.signature(getattr(Player, nome))
        params = [p for p in sig.parameters if p != "self"]
        assert params == params_esperados, (
            f"Assinatura de Player.{nome} mudou: esperado {params_esperados}, obtido {params}")
