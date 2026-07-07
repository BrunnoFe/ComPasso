"""config_manager: validação de valores, round-trip salvar/carregar e preferências."""

import json

import pytest

from src.core import config_manager as cm


# ------------------------------ _is_int ------------------------------------ #
@pytest.mark.parametrize("value, minimum, esperado", [
    ("1", 1, True),
    (1, 1, True),
    ("0", 0, True),
    ("0", 1, False),     # abaixo do mínimo
    ("-1", 0, False),
    ("abc", 0, False),
    ("1.5", 0, False),
    ("", 0, False),
    (None, 0, False),
    ("  3  ", 1, True),  # espaços são tolerados
])
def test_is_int(value, minimum, esperado):
    assert cm._is_int(value, minimum) is esperado


# --------------------------- default_config -------------------------------- #
def test_default_config_has_all_required_keys():
    d = cm.default_config()
    assert d["config_version"] == cm.CONFIG_VERSION
    for key in cm.REQUIRED_KEYS:
        assert key in d


# --------------------------- validate_values ------------------------------- #
def test_validate_values_ok(valid_config_values, mocker):
    # factors_file da fixture é .xlsx e existe; pastas existem -> sem erros
    assert cm.validate_values(valid_config_values) == []


def test_validate_values_reports_each_missing_field():
    errors = cm.validate_values(cm.default_config())  # tudo vazio
    joined = " ".join(errors)
    assert "Pasta de músicas" in joined
    assert "Quantidade de músicas" in joined
    assert "Arquivo de fatores" in joined
    assert "Pasta de salvamento" in joined
    assert "Canal ativo do BITalino" in joined
    assert "Endereço MAC" in joined


def test_validate_values_bad_channel(valid_config_values):
    valid_config_values["bitalino_channel"] = "A9"
    errors = cm.validate_values(valid_config_values)
    assert any("Canal ativo" in e for e in errors)


def test_validate_values_bad_mac(valid_config_values):
    valid_config_values["bitalino_mac"] = "xx:yy"
    errors = cm.validate_values(valid_config_values)
    assert any("MAC" in e for e in errors)


def test_validate_values_factors_must_be_xlsx(tmp_path, valid_config_values):
    wrong = tmp_path / "fatores.txt"
    wrong.write_text("x")
    valid_config_values["factors_file"] = str(wrong)
    errors = cm.validate_values(valid_config_values)
    assert any(".xlsx" in e for e in errors)


def test_validate_values_music_quantity_min_one(valid_config_values):
    valid_config_values["music_quantity"] = 0
    errors = cm.validate_values(valid_config_values)
    assert any("Quantidade de músicas" in e for e in errors)


def test_validate_values_noise_quantity_allows_zero(valid_config_values):
    valid_config_values["noise_quantity"] = 0
    assert cm.validate_values(valid_config_values) == []


# --------------------------- save / load ----------------------------------- #
def test_save_then_load_round_trip(tmp_path, valid_config_values, mocker):
    mocker.patch.object(cm.config_logger.logger, "info")
    path = tmp_path / "exp.config"
    cm.save_config(str(path), valid_config_values)

    # gravou JSON com versão de schema e apenas as chaves obrigatórias
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["config_version"] == cm.CONFIG_VERSION
    assert set(raw) == set(["config_version"] + cm.REQUIRED_KEYS)

    data, errors = cm.load_config(str(path))
    assert errors == []
    assert data["bitalino_mac"] == valid_config_values["bitalino_mac"]


def test_save_creates_parent_dirs(tmp_path, valid_config_values, mocker):
    mocker.patch.object(cm.config_logger.logger, "info")
    nested = tmp_path / "a" / "b" / "exp.config"
    cm.save_config(str(nested), valid_config_values)
    assert nested.exists()


def test_load_invalid_json_returns_error(tmp_path, mocker):
    mocker.patch.object(cm.config_logger.logger, "error")
    bad = tmp_path / "bad.config"
    bad.write_text("{ not json ", encoding="utf-8")
    data, errors = cm.load_config(str(bad))
    assert data is None
    assert errors and "JSON" in errors[0]


def test_load_missing_key_is_reported(tmp_path):
    incomplete = {"config_version": 1, "music_folder": "x"}  # faltam chaves
    path = tmp_path / "inc.config"
    path.write_text(json.dumps(incomplete), encoding="utf-8")
    data, errors = cm.load_config(str(path))
    assert any(e.startswith("Campo ausente") for e in errors)


def test_load_empty_value_is_reported(tmp_path):
    cfg = cm.default_config()  # chaves presentes, valores vazios
    path = tmp_path / "empty.config"
    path.write_text(json.dumps(cfg), encoding="utf-8")
    data, errors = cm.load_config(str(path))
    assert any(e.startswith("Campo vazio") for e in errors)


# --------------------------- preferências ---------------------------------- #
def test_prefs_round_trip(tmp_path, mocker):
    prefs_path = tmp_path / "prefs.json"
    mocker.patch("src.core.config_manager.get_prefs_path", return_value=prefs_path)
    assert cm.get_last_config_path() is None
    cm.set_last_config("/algum/caminho.config")
    assert cm.get_last_config_path() == "/algum/caminho.config"


def test_prefs_corrupt_file_returns_none(tmp_path, mocker):
    prefs_path = tmp_path / "prefs.json"
    prefs_path.write_text("{ broken", encoding="utf-8")
    mocker.patch("src.core.config_manager.get_prefs_path", return_value=prefs_path)
    assert cm.get_last_config_path() is None


# --------------------------- preferências do gráfico ----------------------- #
def test_graph_prefs_defaults_when_absent(tmp_path, mocker):
    prefs_path = tmp_path / "prefs.json"
    mocker.patch("src.core.config_manager.get_prefs_path", return_value=prefs_path)
    # sem arquivo -> todos os defaults
    assert cm.get_graph_prefs() == cm.DEFAULT_GRAPH_SETTINGS


def test_graph_prefs_round_trip(tmp_path, mocker):
    prefs_path = tmp_path / "prefs.json"
    mocker.patch("src.core.config_manager.get_prefs_path", return_value=prefs_path)
    settings = dict(cm.DEFAULT_GRAPH_SETTINGS)
    settings.update({"y_scale": 50, "smoothing_enabled": False, "fps": 30, "line_width": 2.5})
    cm.set_graph_prefs(settings)
    assert cm.get_graph_prefs() == settings


def test_graph_prefs_merges_missing_and_ignores_invalid(tmp_path, mocker):
    prefs_path = tmp_path / "prefs.json"
    # chave conhecida válida, uma ausente (cai no default) e uma com tipo errado (ignorada)
    prefs_path.write_text(json.dumps({"theme": "Teal", "graph": {
        "y_scale": 20, "grid_visible": "sim"}}), encoding="utf-8")
    mocker.patch("src.core.config_manager.get_prefs_path", return_value=prefs_path)
    result = cm.get_graph_prefs()
    assert result["y_scale"] == 20                                   # respeitada
    assert result["grid_visible"] == cm.DEFAULT_GRAPH_SETTINGS["grid_visible"]  # tipo errado -> default
    assert result["fps"] == cm.DEFAULT_GRAPH_SETTINGS["fps"]         # ausente -> default


def test_graph_prefs_preserves_theme_and_last_config(tmp_path, mocker):
    prefs_path = tmp_path / "prefs.json"
    mocker.patch("src.core.config_manager.get_prefs_path", return_value=prefs_path)
    cm.set_theme_pref("Iris")
    cm.set_last_config("/x/y.config")
    cm.set_graph_prefs(cm.DEFAULT_GRAPH_SETTINGS)
    # gravar o gráfico não apaga tema nem último config
    assert cm.get_theme_pref() == "Iris"
    assert cm.get_last_config_path() == "/x/y.config"
