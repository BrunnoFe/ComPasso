"""Fixtures compartilhadas da suíte de testes do Compasso.

Como rodar (a partir da raiz do repositório)::

    venv\\Scripts\\activate
    pip install -r requirements-dev.txt
    pytest

Princípios:
- Nenhum teste toca hardware real (BITalino/LSL), rede ou diálogos de arquivo.
- Nenhuma escrita de DADOS fora de ``tmp_path``. (Importar ``src.core``/``src.utils`` tem
  o efeito colateral pré-existente de criar arquivos de log em app-data — é a infraestrutura
  de logging do próprio app, não dado de teste; ver tests/README.md.)
- O hardware é substituído por fakes determinísticos (``FakeInlet``, ``FakeClock``).
"""

import types

import pytest


# --------------------------------------------------------------------------- #
# Fakes de hardware / relógio
# --------------------------------------------------------------------------- #
class FakeInlet:
    """Substituto determinístico de ``pylsl.StreamInlet``.

    Modela as duas fases que o ``LSLRecorder`` usa:
    - ``buffered``: amostras "antigas" retornadas a chamadas ``pull_sample(timeout=0.0)``
      (a fase de *drain* em ``start()``).
    - ``stream``: amostras "novas" retornadas a chamadas ``pull_sample(timeout>0)``
      (a fase de aquisição em ``_run``).

    Quando ``stream`` esgota, invoca ``on_exhausted`` (uma única vez) e passa a
    retornar ``(None, None)`` — permitindo encerrar o loop de aquisição de forma
    determinística, sem esperas reais.

    Cada item das listas é uma tupla ``(sample, ts)`` onde ``sample`` é uma lista de
    floats (um valor por canal) e ``ts`` é o timestamp LSL.
    """

    def __init__(self, stream=None, buffered=None, on_exhausted=None):
        self.stream = list(stream or [])
        self.buffered = list(buffered or [])
        self.on_exhausted = on_exhausted
        self._exhausted_fired = False
        self.pull_calls = 0
        self._info = _FakeStreamInfo()

    def pull_sample(self, timeout=0.0):
        self.pull_calls += 1
        if timeout == 0.0:
            # fase de drain: consome o buffer "antigo"
            if self.buffered:
                return self.buffered.pop(0)
            return (None, None)
        # fase de aquisição
        if self.stream:
            return self.stream.pop(0)
        if not self._exhausted_fired:
            self._exhausted_fired = True
            if self.on_exhausted is not None:
                self.on_exhausted()
        return (None, None)

    def info(self):
        return self._info


class _FakeStreamInfo:
    """Info mínima de stream (taxa nominal e nº de canais) para diagnósticos."""

    def __init__(self, srate=100.0, channels=6):
        self._srate = srate
        self._channels = channels

    def nominal_srate(self):
        return self._srate

    def channel_count(self):
        return self._channels


class FakeClock:
    """Relógio determinístico para substituir ``local_clock``/``time.monotonic``.

    - ``value`` é o instante atual.
    - chamar a instância (``clock()``) retorna ``value`` e, opcionalmente, o
      incrementa em ``step`` a cada chamada (útil para o watchdog, que avança o
      tempo sozinho a cada tick).
    """

    def __init__(self, value=0.0, step=0.0):
        self.value = float(value)
        self.step = float(step)

    def __call__(self):
        current = self.value
        self.value += self.step
        return current

    def advance(self, delta):
        self.value += delta

    def set(self, value):
        self.value = float(value)


@pytest.fixture
def make_inlet():
    """Fábrica de ``FakeInlet`` (ver docstring da classe)."""
    def _factory(stream=None, buffered=None, on_exhausted=None):
        return FakeInlet(stream=stream, buffered=buffered, on_exhausted=on_exhausted)
    return _factory


@pytest.fixture
def fake_clock():
    """Fábrica de ``FakeClock``."""
    def _factory(value=0.0, step=0.0):
        return FakeClock(value=value, step=step)
    return _factory


# --------------------------------------------------------------------------- #
# Dados de exemplo (configuração / participante / planilha de fatores)
# --------------------------------------------------------------------------- #
@pytest.fixture
def valid_config_values(tmp_path):
    """Dict de configuração VÁLIDA, com pastas/arquivo reais criados em ``tmp_path``."""
    music_folder = tmp_path / "musicas"
    music_folder.mkdir()
    save_dir = tmp_path / "saida"
    save_dir.mkdir()
    factors = tmp_path / "fatores.xlsx"
    factors.write_bytes(b"")  # existência basta para validate_values (mock de extensão)
    return {
        "config_version": 1,
        "music_folder": str(music_folder),
        "music_quantity": 3,
        "noise_quantity": 1,
        "factors_file": str(factors),
        "data_save_path": str(save_dir),
        "bitalino_channel": "A1",
        "bitalino_mac": "20:17:09:18:60:29",
    }


@pytest.fixture
def make_factors_xlsx(tmp_path):
    """Fábrica que grava um .xlsx de condições em ``tmp_path``.

    Uso::

        path = make_factors_xlsx([("a.mp3", "musica"), ("b.mp3", "ruido")])

    Passe ``columns=(...)`` para nomes de coluna alternativos (testar colunas faltando).
    """
    import pandas as pd

    counter = {"n": 0}

    def _factory(rows, columns=("musica", "fator"), filename=None):
        counter["n"] += 1
        name = filename or f"fatores_{counter['n']}.xlsx"
        path = tmp_path / name
        df = pd.DataFrame(rows, columns=list(columns))
        df.to_excel(path, index=False)
        return str(path)

    return _factory


@pytest.fixture
def participant():
    """Dados de participante de exemplo (objeto com .nome/.idade/.genero)."""
    return types.SimpleNamespace(nome="Maria Clara", idade="27", genero="Feminino")
