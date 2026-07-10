"""musics: varredura de áudios e casamento música→fator a partir do .xlsx."""

import os

import pytest

from compasso.core import musics
from compasso.core.musics import (scan_music_files, match_conditions,
                             MissingConditionError, AUDIO_EXTENSIONS)


@pytest.fixture(autouse=True)
def _silence_logger(mocker):
    """Evita ruído de log durante os testes deste módulo."""
    mocker.patch.object(musics.musics_logger.logger, "info")


# ----------------------------- scan_music_files ---------------------------- #
def test_scan_returns_only_audio_files(tmp_path):
    (tmp_path / "a.mp3").write_text("x")
    (tmp_path / "b.WAV").write_text("x")       # extensão maiúscula também conta
    (tmp_path / "c.ogg").write_text("x")
    (tmp_path / "leiame.txt").write_text("x")  # ignorado
    (tmp_path / "capa.png").write_text("x")    # ignorado

    found = scan_music_files(str(tmp_path))
    names = sorted(os.path.basename(p) for p in found)
    assert names == ["a.mp3", "b.WAV", "c.ogg"]
    assert all(p.lower().endswith(AUDIO_EXTENSIONS) for p in found)


def test_scan_returns_absolute_paths(tmp_path):
    (tmp_path / "a.mp3").write_text("x")
    found = scan_music_files(str(tmp_path))
    assert os.path.isabs(found[0])


def test_scan_missing_folder_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        scan_music_files(str(tmp_path / "nao_existe"))


def test_scan_empty_folder_returns_empty(tmp_path):
    assert scan_music_files(str(tmp_path)) == []


# ----------------------------- match_conditions ---------------------------- #
def test_match_maps_each_music_to_factor(tmp_path, make_factors_xlsx):
    (tmp_path / "a.mp3").write_text("x")
    (tmp_path / "b.mp3").write_text("x")
    music_files = [str(tmp_path / "a.mp3"), str(tmp_path / "b.mp3")]
    xlsx = make_factors_xlsx([("a.mp3", "musica"), ("b.mp3", "ruido")])

    mapping = match_conditions(music_files, xlsx)
    assert mapping[str(tmp_path / "a.mp3")] == "musica"
    assert mapping[str(tmp_path / "b.mp3")] == "ruido"


def test_match_missing_condition_raises(tmp_path, make_factors_xlsx):
    music_files = [str(tmp_path / "semfator.mp3")]
    xlsx = make_factors_xlsx([("outra.mp3", "musica")])
    with pytest.raises(MissingConditionError) as exc:
        match_conditions(music_files, xlsx)
    assert exc.value.music_name == "semfator.mp3"


def test_match_returns_none_when_columns_missing(tmp_path, make_factors_xlsx):
    xlsx = make_factors_xlsx([("a.mp3", "x")], columns=("arquivo", "tipo"))
    assert match_conditions([str(tmp_path / "a.mp3")], xlsx) is None


def test_match_with_custom_column_names(tmp_path, make_factors_xlsx):
    (tmp_path / "a.mp3").write_text("x")
    (tmp_path / "b.mp3").write_text("x")
    music_files = [str(tmp_path / "a.mp3"), str(tmp_path / "b.mp3")]
    # colunas com nomes arbitrários — só funcionam quando informadas explicitamente.
    xlsx = make_factors_xlsx([("a.mp3", "calmo"), ("b.mp3", "ruido")],
                             columns=("arquivo", "condicao"))

    assert match_conditions(music_files, xlsx) is None  # defaults 'musica'/'fator' não existem
    mapping = match_conditions(music_files, xlsx,
                               music_column="arquivo", factor_column="condicao")
    assert mapping[str(tmp_path / "a.mp3")] == "calmo"
    assert mapping[str(tmp_path / "b.mp3")] == "ruido"


def test_match_returns_none_when_empty_sheet(tmp_path, make_factors_xlsx):
    xlsx = make_factors_xlsx([], columns=("musica", "fator"))
    assert match_conditions([str(tmp_path / "a.mp3")], xlsx) is None


def test_match_missing_xlsx_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        match_conditions([], str(tmp_path / "nao_existe.xlsx"))
