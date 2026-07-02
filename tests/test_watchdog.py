"""ConnectionWatchdog: dispara perda de conexão após TIMEOUT sem amostras.

Sem hardware e sem dependência de tempo real: ``time.monotonic`` do módulo é
substituído por um ``FakeClock`` que avança um passo fixo a cada chamada, de modo
que o limiar de TIMEOUT é alcançado de forma determinística em poucos ticks. O
``POLL`` é reduzido só para manter o tempo de parede desprezível.
"""

import time as _t
import types

from src.core.bitalino_connect import ConnectionWatchdog


def _make_ctx(fired, **kwargs):
    """ctx falso: run_after executa de imediato; handle_connection_lost registra o disparo."""
    ctx = types.SimpleNamespace(
        bitalino=kwargs.get("bitalino"),
        runner=kwargs.get("runner"),
        run_after=lambda fn: fn(),
        handle_connection_lost=None,
    )
    return ctx


def _patch_clock(mocker, step):
    """Substitui ``bitalino_connect.time`` por um fake cujo monotonic avança ``step``/chamada."""
    state = {"v": 0.0}

    def monotonic():
        v = state["v"]
        state["v"] += step
        return v

    mocker.patch("src.core.bitalino_connect.time",
                 types.SimpleNamespace(monotonic=monotonic))
    return state


def _wait_until(predicate, timeout=2.0):
    deadline = _t.time() + timeout
    while not predicate() and _t.time() < deadline:
        _t.sleep(0.005)


# --------------------------------------------------------------------------- #
def test_fires_after_timeout_without_samples(mocker, make_inlet):
    _patch_clock(mocker, step=5.0)          # 5s "virtuais" por chamada de monotonic
    inlet = make_inlet(stream=[])           # idle: pull_sample sempre sem amostra
    fired = []

    ctx = _make_ctx(fired, bitalino=inlet, runner=None)
    wd = ConnectionWatchdog(ctx)
    wd.POLL = 0.005
    wd.TIMEOUT = 15.0

    def on_lost():
        fired.append(True)
        wd._stop_event.set()               # encerra o loop após o 1º disparo
    ctx.handle_connection_lost = on_lost

    wd.start()
    _wait_until(lambda: fired)
    wd.stop()

    assert fired == [True], "watchdog deveria disparar exatamente uma vez"


def test_no_fire_when_samples_keep_arriving(mocker, make_inlet):
    _patch_clock(mocker, step=1.0)          # gaps de 1s << TIMEOUT
    inlet = make_inlet(stream=[])
    inlet.pull_sample = lambda timeout=0.0: ([1.0], 123.0)  # sempre há amostra
    fired = []

    ctx = _make_ctx(fired, bitalino=inlet, runner=None)
    ctx.handle_connection_lost = lambda: fired.append(True)
    wd = ConnectionWatchdog(ctx)
    wd.POLL = 0.005
    wd.TIMEOUT = 15.0

    wd.start()
    _wait_until(lambda: False, timeout=0.1)  # deixa rodar vários ticks
    wd.stop()

    assert fired == [], "gaps curtos nunca devem disparar"


def test_idle_when_bitalino_is_none(mocker):
    _patch_clock(mocker, step=100.0)        # saltos enormes; ainda assim não dispara
    fired = []
    ctx = _make_ctx(fired, bitalino=None, runner=None)
    ctx.handle_connection_lost = lambda: fired.append(True)
    wd = ConnectionWatchdog(ctx)
    wd.POLL = 0.005
    wd.TIMEOUT = 15.0

    wd.start()
    _wait_until(lambda: False, timeout=0.1)
    wd.stop()

    assert fired == [], "desconectado (bitalino=None) não deve disparar"


def test_recording_path_does_not_poll_inlet(mocker, make_inlet):
    # Durante a gravação, o watchdog LÊ o timestamp do runner e NÃO puxa amostras
    # (para não roubar dados que estão sendo gravados).
    _patch_clock(mocker, step=1.0)
    inlet = make_inlet(stream=[([1.0], 1.0)])
    fired = []

    runner = mocker.MagicMock()
    runner.is_acquiring.return_value = True
    runner.last_acquisition_monotonic.side_effect = lambda: _t.monotonic()  # sempre recente

    ctx = _make_ctx(fired, bitalino=inlet, runner=runner)
    ctx.handle_connection_lost = lambda: fired.append(True)
    wd = ConnectionWatchdog(ctx)
    wd.POLL = 0.005
    wd.TIMEOUT = 15.0

    wd.start()
    _wait_until(lambda: runner.last_acquisition_monotonic.call_count >= 3, timeout=1.0)
    wd.stop()

    assert inlet.pull_calls == 0, "não deve puxar amostras enquanto grava"
    assert fired == []
