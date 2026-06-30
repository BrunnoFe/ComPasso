"""Resolução de caminhos da aplicação e criação idempotente das pastas.

As bases (Documentos / app-data) são redirecionadas para ``tmp_path`` via mock, de
modo que nenhum diretório real do usuário é tocado. O caminho Windows com ctypes
(``_windows_documents``) não é exercitado aqui (depende de API do SO).
"""

from pathlib import Path

from src.utils import paths
from src.utils.configs import APP_NAME


def test_get_data_dir_structure(mocker, tmp_path):
    docs = tmp_path / "Documents"
    mocker.patch("src.utils.paths.get_documents_dir", return_value=docs)
    assert paths.get_data_dir() == docs / APP_NAME / "data"


def test_get_logs_dir_structure(mocker, tmp_path):
    appdata = tmp_path / "AppData"
    mocker.patch("src.utils.paths.get_app_data_dir", return_value=appdata)
    assert paths.get_logs_dir() == appdata / APP_NAME / "logs"


def test_get_errors_log_path_structure(mocker, tmp_path):
    appdata = tmp_path / "AppData"
    mocker.patch("src.utils.paths.get_app_data_dir", return_value=appdata)
    assert paths.get_errors_log_path() == appdata / APP_NAME / "errors.log"


def test_ensure_app_dirs_creates_data_and_logs(mocker, tmp_path):
    docs = tmp_path / "Documents"
    appdata = tmp_path / "AppData"
    mocker.patch("src.utils.paths.get_documents_dir", return_value=docs)
    mocker.patch("src.utils.paths.get_app_data_dir", return_value=appdata)

    result = paths.ensure_app_dirs()

    assert result["data"].is_dir()
    assert result["logs"].is_dir()
    assert result["data"] == docs / APP_NAME / "data"
    assert result["logs"] == appdata / APP_NAME / "logs"
    assert result["errors"] == appdata / APP_NAME / "errors.log"


def test_ensure_app_dirs_is_idempotent(mocker, tmp_path):
    mocker.patch("src.utils.paths.get_documents_dir", return_value=tmp_path / "D")
    mocker.patch("src.utils.paths.get_app_data_dir", return_value=tmp_path / "A")
    paths.ensure_app_dirs()
    # segunda chamada não deve levantar (exist_ok=True)
    paths.ensure_app_dirs()
    assert (tmp_path / "D" / APP_NAME / "data").is_dir()


def test_app_data_dir_returns_path():
    # smoke: o tipo de retorno é Path em qualquer plataforma
    assert isinstance(paths.get_app_data_dir(), Path)
