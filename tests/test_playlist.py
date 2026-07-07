"""Construção da playlist: distribuição do ruído, totais e ordenação pseudoaleatória.

Testes puros — montam o `mapping` {caminho: fator} diretamente, sem tocar em xlsx/GUI.
"""

import random
from collections import Counter

import pytest

from compasso.core.experiment import (_distribute, expand_playlist, count_totals,
                                 session_totals, pseudo_random_order, _classify_condition)
from compasso.core.constants import CONDITION_MUSICA, CONDITION_RUIDO


@pytest.fixture(autouse=True)
def _seed():
    """Semente fixa para tornar as verificações probabilísticas determinísticas."""
    random.seed(1234)


def _is_noise(mapping, path):
    return _classify_condition(mapping.get(path, "")) == CONDITION_RUIDO


# --------------------------------- _distribute -------------------------------- #
def test_distribute_round_robin_two_files():
    counts = Counter(_distribute(["n1", "n2"], 5))
    assert sum(counts.values()) == 5
    assert sorted(counts.values()) == [2, 3]      # 5 entre 2 -> 3 + 2


def test_distribute_round_robin_three_files():
    counts = Counter(_distribute(["n1", "n2", "n3"], 5))
    assert sum(counts.values()) == 5
    assert sorted(counts.values()) == [1, 2, 2]   # 5 entre 3 -> 2/2/1


def test_distribute_empty_or_zero():
    assert _distribute([], 5) == []
    assert _distribute(["n1"], 0) == []
    assert _distribute(["n1"], -3) == []


# ------------------------------ expand / totals ------------------------------- #
def _mapping(musicas, ruidos):
    m = {f"/mus/{n}.mp3": "musica" for n in musicas}
    m.update({f"/rui/{n}.wav": "ruido" for n in ruidos})
    return m


def test_expand_music_once_noise_by_quantity():
    mapping = _mapping(["a", "b", "c"], ["w1"])
    playlist = expand_playlist(mapping, noise_quantity=5)
    counts = Counter(playlist)
    # cada música 1x
    assert counts["/mus/a.mp3"] == 1 and counts["/mus/b.mp3"] == 1 and counts["/mus/c.mp3"] == 1
    # ruído (único arquivo) tocado noise_quantity vezes
    assert counts["/rui/w1.wav"] == 5


def test_session_totals_counts():
    mapping = _mapping(["a", "b", "c", "d"], ["w1", "w2"])
    mt, nt = session_totals(mapping, noise_quantity=5)
    assert mt == 4
    assert nt == 5


def test_session_totals_no_noise_files_gives_zero():
    mapping = _mapping(["a", "b"], [])
    mt, nt = session_totals(mapping, noise_quantity=5)
    assert (mt, nt) == (2, 0)


def test_count_totals_matches_playlist():
    mapping = _mapping(["a", "b", "c"], ["w1", "w2"])
    playlist = expand_playlist(mapping, 4)
    totals = count_totals(playlist, mapping)
    assert totals[CONDITION_MUSICA] == 3
    assert totals[CONDITION_RUIDO] == 4


# ---------------------------- pseudo_random_order ----------------------------- #
def _assert_constraints(order, mapping):
    """Ruído nunca em primeiro; >=2 músicas entre ruídos consecutivos."""
    assert not _is_noise(mapping, order[0]), "ruído não pode ser a primeira faixa"
    last_noise = None
    for i, path in enumerate(order):
        if _is_noise(mapping, path):
            if last_noise is not None:
                musicas_entre = sum(1 for p in order[last_noise + 1:i]
                                    if not _is_noise(mapping, p))
                assert musicas_entre >= 2, f"apenas {musicas_entre} música(s) entre ruídos"
            last_noise = i


def test_order_respects_constraints_many_runs():
    mapping = _mapping([f"m{i}" for i in range(20)], ["w1"])
    for _ in range(200):
        order = pseudo_random_order(expand_playlist(mapping, 5), mapping)
        assert Counter(order) == Counter(expand_playlist(mapping, 5))  # mesmo multiconjunto de contagens
        _assert_constraints(order, mapping)


def test_order_preserves_multiset():
    mapping = _mapping([f"m{i}" for i in range(10)], ["w1", "w2"])
    playlist = expand_playlist(mapping, 4)
    order = pseudo_random_order(playlist, mapping)
    assert Counter(order) == Counter(playlist)


def test_order_no_noise_returns_all_musics():
    mapping = _mapping(["a", "b", "c"], [])
    order = pseudo_random_order(expand_playlist(mapping, 0), mapping)
    assert Counter(order) == Counter(["/mus/a.mp3", "/mus/b.mp3", "/mus/c.mp3"])


def test_order_infeasible_does_not_crash_and_noise_not_first():
    # muitos ruídos para poucas músicas -> melhor-esforço, mas ruído nunca primeiro
    mapping = _mapping(["a", "b"], ["w1"])
    order = pseudo_random_order(expand_playlist(mapping, 10), mapping)
    assert not _is_noise(mapping, order[0])
    assert len(order) == 12  # 2 músicas + 10 ruídos
