"""Precisão temporal do agendamento de uma faixa (``ExperimentRunner._run_track``).

Regressão do bug que motivou a refatoração: a contagem regressiva era um laço de
``time.sleep(1.0)``, então cada volta custava ``1.0 s + ε`` e o beep tocava progressivamente
mais cedo em relação ao áudio, faixa após faixa. Aqui o desvio do relógio é **exagerado de
propósito** (cada espera dorme 8% a mais do que foi pedida, e às vezes muito mais) para que
qualquer volta ao agendamento por passos acumulados falhe de forma escandalosa.

Nada aqui toca hardware, áudio ou o relógio real: o `local_clock` do módulo é substituído por um
relógio controlado que só avança dentro das esperas.
"""

import types

import pytest

from compasso.core import experiment as exp
from compasso.core.constants import (MARKER_BEEP, MARKER_MUSIC_START, MARKER_COUNTDOWN_START,
                                     CONDITION_MUSICA, CONDITION_RUIDO)


class RelogioControlado:
    """Relógio de teste: só avança quando uma espera o faz avançar."""

    def __init__(self):
        self.valor = 1000.0   # base arbitrária, como o local_clock real

    def __call__(self):
        return self.valor

    def avancar(self, delta):
        self.valor += max(0.0, delta)


class EventoQueDorme:
    """Substituto de ``threading.Event`` que simula um SO que sempre dorme demais.

    ``wait(t)`` avança o relógio em ``t * excesso`` — o defeito real, amplificado. Se o
    agendamento contasse passos em vez de instantes, o erro se acumularia a cada espera.
    """

    def __init__(self, relogio, excesso=1.08):
        self._relogio = relogio
        self._excesso = excesso
        self._set = False

    def wait(self, timeout=None):
        self._relogio.avancar((timeout or 0.0) * self._excesso)
        return self._set

    def is_set(self):
        return self._set

    def set(self):
        self._set = True

    def clear(self):
        self._set = False


class RecorderFalso:
    """Captura os marcadores emitidos, com o instante de cada um."""

    def __init__(self, *a, **kw):
        self.marcadores = []

    def start(self):
        return RELOGIO.valor

    def add_marker(self, nome, ts, **kw):
        self.marcadores.append((nome, ts))

    def stop(self):
        pass

    def finalize(self):
        pass

    def instante(self, nome):
        for n, ts in self.marcadores:
            if n == nome:
                return ts
        raise AssertionError(f"marcador '{nome}' não foi emitido: {self.marcadores}")


class PlayerFalso:
    """Player sem áudio; a reprodução "dura" a duração informada."""

    def __init__(self, relogio, duracao=12.0):
        self._relogio = relogio
        self.duracao = duracao

    def load(self, path):
        return True

    def get_length(self):
        return self.duracao

    def play(self):
        pass

    def play_beep(self):
        return True

    def stop(self):
        pass

    def aguardar_fim(self, timeout):
        self._relogio.avancar(self.duracao)
        return True


RELOGIO = RelogioControlado()


@pytest.fixture
def runner(tmp_path, mocker):
    """``ExperimentRunner`` com relógio controlado, sem hardware, áudio ou GUI."""
    global RELOGIO
    RELOGIO = RelogioControlado()
    mocker.patch.object(exp, "local_clock", RELOGIO)
    mocker.patch.object(exp, "LSLRecorder", RecorderFalso)
    mocker.patch.object(exp, "get_system_volume", lambda: 50)
    mocker.patch.object(exp, "build_track_filename", lambda *a, **kw: "faixa")

    ctx = types.SimpleNamespace(
        player=PlayerFalso(RELOGIO),
        duracoes_audio={},
        bitalino=object(),
        signal_channel=1,
        music_condition_mapping={},
        save_dir=str(tmp_path),
        signal_plot=None,
        pre_stimulus_seconds=10,
        beep_habilitado=True,
        beep_antecedencia_segundos=5,
        run_after=lambda fn: None,
    )
    r = exp.ExperimentRunner(ctx)
    r._session_dir = str(tmp_path)
    r._stop_event = EventoQueDorme(RELOGIO)
    return r


# Erro máximo (s) aceito no posicionamento de um evento. Um agendador nunca acorda ANTES do
# prazo, só depois; o que se exige é que o atraso seja pequeno e — sobretudo — que não cresça.
_TOLERANCIA_S = 0.02


@pytest.mark.parametrize("lead", [1, 3, 5])
def test_beep_toca_no_lead_configurado_antes_do_audio(runner, lead):
    """O intervalo beep→áudio é o configurado, apesar de cada espera dormir 8% a mais."""
    runner.beep_antecedencia_segundos = lead
    rec = _capturar(runner)
    intervalo = rec.instante(MARKER_MUSIC_START) - rec.instante(MARKER_BEEP)
    assert intervalo == pytest.approx(lead, abs=_TOLERANCIA_S)


def test_audio_comeca_no_alvo_absoluto(runner):
    """O áudio começa em t0 + pré-estímulo, sem escorregar com o desvio das esperas."""
    rec = _capturar(runner)
    atraso = (rec.instante(MARKER_MUSIC_START) - rec.instante(MARKER_COUNTDOWN_START)
              - runner.countdown_seconds)
    assert 0 <= atraso < _TOLERANCIA_S


def test_intervalo_do_beep_nao_deriva_ao_longo_da_sessao(runner):
    """20 faixas seguidas mantêm o mesmo intervalo beep→áudio — o bug relatado.

    É esta a asserção que importa: não que o erro seja zero (o SO sempre acorda um pouco
    depois), mas que a 20ª faixa valha o mesmo que a 1ª. Com o laço de `sleep` antigo o desvio
    crescia com o número de esperas e a sessão terminava visivelmente dessincronizada.
    """
    intervalos = []
    for i in range(20):
        rec = _capturar(runner, nome=f"faixa{i}.mp3")
        intervalos.append(rec.instante(MARKER_MUSIC_START) - rec.instante(MARKER_BEEP))

    lead = runner.beep_antecedencia_segundos
    assert all(abs(v - lead) < _TOLERANCIA_S for v in intervalos)
    # nenhuma tendência: a última faixa não é mais tardia que a primeira.
    assert abs(intervalos[-1] - intervalos[0]) < 1e-3
    assert max(intervalos) - min(intervalos) < 1e-3


def test_sem_beep_nenhum_marcador_de_beep_e_emitido(runner):
    runner.beep_habilitado = False
    rec = _capturar(runner)
    assert all(nome != MARKER_BEEP for nome, _ in rec.marcadores)


def _capturar(runner, nome="faixa.mp3"):
    """Roda uma faixa e devolve o ``RecorderFalso`` usado nela."""
    criados = []
    original = exp.LSLRecorder

    def fabricar(*a, **kw):
        rec = original(*a, **kw)
        criados.append(rec)
        return rec

    exp.LSLRecorder = fabricar
    try:
        runner.ctx.music_condition_mapping = {nome: "alegre"}
        runner._run_track(1, nome, {CONDITION_MUSICA: 1, CONDITION_RUIDO: 0})
    finally:
        exp.LSLRecorder = original
    assert criados, "nenhum recorder foi criado"
    return criados[-1]
