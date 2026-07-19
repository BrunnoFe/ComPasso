from .configs import (ENCODING_FORMAT, APP_NAME, PROJECT_URL, LOG_FORMAT, DATA_DIRNAME, PROJECT_GITSITE,
                     LOGS_DIRNAME, EXPERIMENT_FILES_DIRNAME, ERRORS_LOG_FILENAME,
                     PREFS_FILENAME, ICON_FILENAME, LOG_TIMESTAMP_FORMAT,
                     FULL_LOGS_DIRNAME, FULL_LOG_FILENAME)
from .paths import (get_documents_dir, get_app_data_dir, get_data_dir,
                    get_logs_dir, get_errors_log_path, get_full_logs_dir, get_full_log_path,
                    ensure_app_dirs, open_path)
from .bootstrap import bootstrap

# Garante as pastas (data/logs/full), os handlers centrais (errors.log/full.log) e a fábrica de
# LogRecord (campo `session`) ANTES de qualquer logger ser criado.
bootstrap()

from .sys_logs import SetLogger
from .log_context import definir_sessao, limpar_sessao, sessao_atual, SEM_SESSAO
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
    'FULL_LOGS_DIRNAME',
    'FULL_LOG_FILENAME',
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
    'get_full_logs_dir',
    'get_full_log_path',
    'ensure_app_dirs',
    'open_path',
    'bootstrap',
    'SetLogger',
    'definir_sessao',
    'limpar_sessao',
    'sessao_atual',
    'SEM_SESSAO',
    'validar_nome_genero',
    'validar_idade',
    'MIN_IDADE',
    'MAX_IDADE',
    'format_time',
    'PROJECT_GITSITE',
    'get_app_version',
    'VERSAO_DESCONHECIDA',
]