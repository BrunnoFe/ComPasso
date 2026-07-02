"""Resolução de caminhos cross-platform e criação das pastas da aplicação.

Decisões (ver discussão de projeto):
- Dados do experimento (CSV/XLSX) -> ``<Documentos>/ComPasso/data`` (fácil de achar
  pelo pesquisador).
- Logs e ``errors.log`` -> diretório de app-data do SO (``%LOCALAPPDATA%`` no Windows,
  ``~/Library/Application Support`` no macOS, ``$XDG_DATA_HOME``/``~/.local/share`` no
  Linux), seguindo a convenção do sistema.

Sem dependências externas: a pasta Documentos no Windows é resolvida pela API de
"known folders" (à prova de redirecionamento do OneDrive) via ``ctypes``.
"""

import os
import platform
from pathlib import Path

from .configs import APP_NAME


def _windows_documents() -> Path:
    """Retorna a pasta Documentos no Windows via SHGetKnownFolderPath (FOLDERID_Documents).

    Confiável mesmo quando o OneDrive redireciona a pasta Documentos.
    """
    import ctypes
    from ctypes import wintypes

    class GUID(ctypes.Structure):
        _fields_ = [("Data1", ctypes.c_uint32),
                    ("Data2", ctypes.c_uint16),
                    ("Data3", ctypes.c_uint16),
                    ("Data4", ctypes.c_ubyte * 8)]

    # {FDD39AD0-238F-46AF-ADB4-6C85480369C7}
    folderid_documents = GUID(0xFDD39AD0, 0x238F, 0x46AF,
                              (ctypes.c_ubyte * 8)(0xAD, 0xB4, 0x6C, 0x85, 0x48, 0x03, 0x69, 0xC7))

    path_ptr = ctypes.c_wchar_p()
    SHGetKnownFolderPath = ctypes.windll.shell32.SHGetKnownFolderPath
    SHGetKnownFolderPath.argtypes = [ctypes.POINTER(GUID), wintypes.DWORD, wintypes.HANDLE, ctypes.POINTER(ctypes.c_wchar_p)]
    result = SHGetKnownFolderPath(ctypes.byref(folderid_documents), 0, None, ctypes.byref(path_ptr))
    try:
        if result != 0 or not path_ptr.value:
            raise OSError(f"SHGetKnownFolderPath falhou (HRESULT={result})")
        return Path(path_ptr.value)
    finally:
        ctypes.windll.ole32.CoTaskMemFree(path_ptr)


def get_documents_dir() -> Path:
    """Pasta Documentos do usuário (cross-platform), com fallback para ``~/Documents``."""
    if platform.system() == "Windows":
        try:
            return _windows_documents()
        except Exception:
            return Path.home() / "Documents"
    return Path.home() / "Documents"


def get_app_data_dir() -> Path:
    """Diretório de app-data do SO (sem o nome da aplicação)."""
    system = platform.system()
    if system == "Windows":
        base = os.environ.get("LOCALAPPDATA")
        return Path(base) if base else (Path.home() / "AppData" / "Local")
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support"
    xdg = os.environ.get("XDG_DATA_HOME")
    return Path(xdg) if xdg else (Path.home() / ".local" / "share")


def get_data_dir() -> Path:
    """Pasta dos dados do experimento: ``<Documentos>/ComPasso/data``."""
    return get_documents_dir() / APP_NAME / "data"


def get_logs_dir() -> Path:
    """Pasta raiz dos logs: ``<app-data>/ComPasso/logs``."""
    return get_app_data_dir() / APP_NAME / "logs"


def get_errors_log_path() -> Path:
    """Arquivo central de erros, fora da pasta de logs: ``<app-data>/ComPasso/errors.log``."""
    return get_app_data_dir() / APP_NAME / "errors.log"


def ensure_app_dirs() -> dict:
    """Cria (idempotente) as pastas de dados e de logs na primeira execução.

    :return: dict com os caminhos ``data``, ``logs`` e ``errors``.
    """
    data_dir = get_data_dir()
    logs_dir = get_logs_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    return {"data": data_dir, "logs": logs_dir, "errors": get_errors_log_path()}
