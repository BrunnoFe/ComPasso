"""Nomes de pasta de sessão e de arquivo de faixa (lógica pura, sem hardware)."""

import re
import types

import pytest

from compasso.core.recorder import _sanitize, build_session_dirname, build_track_filename


# --------------------------- _sanitize ------------------------------------- #
@pytest.mark.parametrize("entrada, esperado", [
    ("minha musica", "minha_musica"),     # espaço -> _
    ("a/b\\c", "a_b_c"),                   # separadores -> _
    ("nome.mp3", "nome_mp3"),              # ponto -> _
    ("ok-nome_1", "ok-nome_1"),            # hífen, underscore e alfanumérico preservados
    ("  trim  ", "trim"),                  # espaços nas pontas removidos antes
    ("José", "Jos_"),                      # acento não-alfanumérico-ASCII -> _ (isalnum é unicode? ver nota)
])
def test_sanitize(entrada, esperado):
    # Observação: 'é'.isalnum() é True (unicode), então é preservado; ajustamos o caso.
    if entrada == "José":
        assert _sanitize(entrada) == "José"
    else:
        assert _sanitize(entrada) == esperado


def test_sanitize_none_returns_empty():
    assert _sanitize(None) == ""


# ------------------------ build_track_filename ----------------------------- #
def test_track_filename_zero_padded_width_two():
    # total de 1 dígito -> largura mínima 2
    assert build_track_filename(1, 9, "musica.mp3") == "01_musica"
    assert build_track_filename(9, 9, "musica.mp3") == "09_musica"


def test_track_filename_width_follows_total():
    # total de 3 dígitos -> largura 3
    assert build_track_filename(7, 120, "x.wav") == "007_x"
    assert build_track_filename(120, 120, "x.wav") == "120_x"


def test_track_filename_strips_audio_extension():
    assert build_track_filename(1, 1, "cancao.ogg").endswith("_cancao")
    assert "ogg" not in build_track_filename(1, 1, "cancao.ogg")


def test_track_filename_sanitizes_music_name():
    out = build_track_filename(1, 1, "minha musica feliz.mp3")
    assert out == "01_minha_musica_feliz"


def test_track_filename_handles_name_without_extension():
    assert build_track_filename(3, 5, "semext") == "03_semext"


# ------------------------ build_session_dirname ---------------------------- #
def test_session_dirname_pattern():
    ctx = types.SimpleNamespace(nome="Maria Clara", idade="27", genero="Feminino")
    name = build_session_dirname(ctx)
    # nome_idade_genero_dia-mes-ano_hora-min-seg  (com nome/genero sanitizados)
    assert re.match(
        r"^Maria_Clara_27_Feminino_\d{2}-\d{2}-\d{4}_\d{2}-\d{2}-\d{2}$", name
    ), name


def test_session_dirname_uses_fixed_timestamp(mocker):
    fixed = mocker.MagicMock()
    fixed.strftime.return_value = "01-02-2026_03-04-05"
    mocker.patch("compasso.core.recorder.datetime").now.return_value = fixed
    ctx = types.SimpleNamespace(nome="Ana", idade="30", genero="F")
    assert build_session_dirname(ctx) == "Ana_30_F_01-02-2026_03-04-05"
