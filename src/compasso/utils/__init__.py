from .configs import (ENCODING_FORMAT, APP_NAME, PROJECT_URL, LOG_FORMAT, DATA_DIRNAME, PROJECT_GITSITE,
                     LOGS_DIRNAME, EXPERIMENT_FILES_DIRNAME, ERRORS_LOG_FILENAME,
                     PREFS_FILENAME, ICON_FILENAME, LOG_TIMESTAMP_FORMAT)
from .paths import (get_documents_dir, get_app_data_dir, get_data_dir,
                    get_logs_dir, get_errors_log_path, ensure_app_dirs, open_path)
from .bootstrap import bootstrap

# Garante as pastas (data/logs) e o errors.log antes de qualquer logger ser criado.
bootstrap()

from .sys_logs import SetLogger
from .validation import validar_nome_genero, validar_idade, MIN_IDADE, MAX_IDADE
from .formatting import format_time
from .version import get_app_version, VERSAO_DESCONHECIDA

__all__ = [
    'ENCODING_FORMAT',
    'APP_NAME',
    'PROJECT_URL',
    'LOG_FORMAT',
    'DATA_DIRNAME',
    'LOGS_DIRNAME',
    'EXPERIMENT_FILES_DIRNAME',
    'ERRORS_LOG_FILENAME',
    'PREFS_FILENAME',
    'ICON_FILENAME',
    'LOG_TIMESTAMP_FORMAT',
    'get_documents_dir',
    'get_app_data_dir',
    'get_data_dir',
    'get_logs_dir',
    'get_errors_log_path',
    'ensure_app_dirs',
    'open_path',
    'bootstrap',
    'SetLogger',
    'validar_nome_genero',
    'validar_idade',
    'MIN_IDADE',
    'MAX_IDADE',
    'format_time',
    'PROJECT_GITSITE',
    'get_app_version',
    'VERSAO_DESCONHECIDA',
]