"""Aquisição/sincronização do LSLRecorder (a lógica mais crítica e mais difícil de depurar).

Cobre, com um inlet falso e relógio determinístico (sem hardware, sem esperas reais):
- captura de ``t0`` em ``start()``;
- descarte de amostras com timestamp < t0 (a 1ª linha gravada tem timestamp >= 0);
- conversão ``timestamp = ts - t0``;
- casamento de marcador com a amostra mais próxima (primeira com ``ts >= lsl_time``);
- extração do canal selecionado em ``signal``;
- cabeçalho/colunas exatos do CSV e geração do XLSX em ``finalize()``.
"""

import csv

import pytest

from src.core.recorder import LSLRecorder, CSV_HEADER

T0 = 1000.0  # valor fixo de local_clock() para o início da captura


@pytest.fixture
def patch_clock(mocker):
    """Fixa ``recorder.local_clock`` em T0 (usado por ``start()`` para definir t0)."""
    mocker.patch("src.core.recorder.local_clock", return_value=T0)


def _drive(recorder, inlet):
    """Roda o recorder até o stream esgotar, sem stop prematuro nem espera real.

    O ``on_exhausted`` do inlet sinaliza a parada quando as amostras acabam; assim
    todas as amostras do ``stream`` são consumidas antes do loop encerrar.
    """
    inlet.on_exhausted = recorder._stop_event.set
    t0 = recorder.start()
    recorder._thread.join(timeout=5.0)
    assert not recorder._thread.is_alive(), "thread de aquisição não encerrou"
    return t0


def _read_rows(csv_path):
    with open(csv_path, newline="", encoding="utf-8") as f:
        return list(csv.reader(f))


# --------------------------------------------------------------------------- #
def test_start_returns_t0(patch_clock, make_inlet, tmp_path):
    inlet = make_inlet(stream=[([1.0], T0)])
    rec = LSLRecorder(inlet, channel=0, csv_path=str(tmp_path / "f.csv"))
    t0 = _drive(rec, inlet)
    assert t0 == T0
    assert rec.t0 == T0


def test_header_is_exact(patch_clock, make_inlet, tmp_path):
    inlet = make_inlet(stream=[([1.0], T0)])
    rec = LSLRecorder(inlet, channel=0, csv_path=str(tmp_path / "f.csv"))
    _drive(rec, inlet)
    rows = _read_rows(rec.csv_path)
    assert rows[0] == CSV_HEADER


def test_negative_timestamps_are_dropped(patch_clock, make_inlet, tmp_path):
    # amostras antes (ts<t0), em (==t0) e depois (ts>t0) de t0
    inlet = make_inlet(stream=[
        ([10.0], T0 - 0.2),   # descartada
        ([11.0], T0 - 0.1),   # descartada
        ([12.0], T0),         # mantida -> timestamp 0.0
        ([13.0], T0 + 0.1),   # mantida -> timestamp 0.1
    ])
    rec = LSLRecorder(inlet, channel=0, csv_path=str(tmp_path / "f.csv"))
    _drive(rec, inlet)
    rows = _read_rows(rec.csv_path)[1:]  # sem o cabeçalho
    timestamps = [float(r[0]) for r in rows]
    signals = [float(r[1]) for r in rows]
    assert timestamps == pytest.approx([0.0, 0.1])
    assert all(t >= 0 for t in timestamps)
    assert signals == pytest.approx([12.0, 13.0])  # só as amostras >= t0


def test_signal_uses_selected_channel(patch_clock, make_inlet, tmp_path):
    inlet = make_inlet(stream=[([10.0, 11.0, 12.0, 13.0], T0)])
    rec = LSLRecorder(inlet, channel=2, csv_path=str(tmp_path / "f.csv"))
    _drive(rec, inlet)
    row = _read_rows(rec.csv_path)[1]
    assert float(row[1]) == 12.0  # sample[2]


def test_signal_out_of_range_falls_back_to_last(patch_clock, make_inlet, tmp_path):
    inlet = make_inlet(stream=[([10.0, 11.0], T0)])
    rec = LSLRecorder(inlet, channel=9, csv_path=str(tmp_path / "f.csv"))
    _drive(rec, inlet)
    row = _read_rows(rec.csv_path)[1]
    assert float(row[1]) == 11.0  # sample[-1]


def test_marker_attaches_to_nearest_sample(patch_clock, make_inlet, tmp_path):
    rec = LSLRecorder(make_inlet(), channel=0, csv_path=str(tmp_path / "f.csv"))
    # marcador em T0+0.5 deve cair na 1ª amostra com ts >= T0+0.5 (ou seja, T0+0.6)
    rec.add_marker("music_start", T0 + 0.5, music_file="x.mp3", fator="musica")
    inlet = make_inlet(stream=[
        ([1.0], T0 + 0.0),   # sem marcador
        ([2.0], T0 + 0.4),   # sem marcador (0.5 > 0.4)
        ([3.0], T0 + 0.6),   # recebe o marcador
        ([4.0], T0 + 0.8),   # sem marcador
    ])
    rec.inlet = inlet
    _drive(rec, inlet)
    rows = _read_rows(rec.csv_path)[1:]
    markers = [r[2] for r in rows]
    assert markers == ["", "", "music_start", ""]
    # music_file/fator presentes apenas na linha do marcador
    music_start_row = rows[2]
    assert music_start_row[3] == "x.mp3"
    assert music_start_row[4] == "musica"
    assert rows[0][3] == "" and rows[0][4] == ""


def test_markers_appended_in_time_order(patch_clock, make_inlet, tmp_path):
    rec = LSLRecorder(make_inlet(), channel=0, csv_path=str(tmp_path / "f.csv"))
    # adicionados fora de ordem; devem ser anexados em ordem temporal
    rec.add_marker("music_end", T0 + 0.9, music_file="x.mp3", fator="musica")
    rec.add_marker("countdown_start", T0 + 0.0, music_file="x.mp3", fator="musica")
    rec.add_marker("music_start", T0 + 0.5, music_file="x.mp3", fator="musica")
    inlet = make_inlet(stream=[
        ([1.0], T0 + 0.0),
        ([2.0], T0 + 0.5),
        ([3.0], T0 + 1.0),
    ])
    rec.inlet = inlet
    _drive(rec, inlet)
    markers = [r[2] for r in _read_rows(rec.csv_path)[1:]]
    assert markers == ["countdown_start", "music_start", "music_end"]


def test_finalize_creates_xlsx(patch_clock, make_inlet, tmp_path):
    import pandas as pd

    inlet = make_inlet(stream=[([1.0], T0), ([2.0], T0 + 0.1)])
    rec = LSLRecorder(inlet, channel=0, csv_path=str(tmp_path / "f.csv"))
    _drive(rec, inlet)
    csv_path, xlsx_path = rec.finalize()
    assert csv_path == rec.csv_path
    assert xlsx_path.endswith(".xlsx")
    df = pd.read_excel(xlsx_path)
    assert list(df.columns) == CSV_HEADER


def test_buffered_samples_are_drained_before_t0(patch_clock, make_inlet, tmp_path):
    # amostras "antigas" no buffer (timeout=0.0) devem ser descartadas no drain,
    # não aparecendo no CSV; só as do stream (timeout>0) são gravadas.
    inlet = make_inlet(
        buffered=[([99.0], T0 - 5.0), ([98.0], T0 - 4.0)],
        stream=[([1.0], T0)],
    )
    rec = LSLRecorder(inlet, channel=0, csv_path=str(tmp_path / "f.csv"))
    _drive(rec, inlet)
    signals = [float(r[1]) for r in _read_rows(rec.csv_path)[1:]]
    assert signals == [1.0]  # nenhuma amostra do buffer antigo
