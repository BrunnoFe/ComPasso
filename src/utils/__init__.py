from .configs import ENCODING_FORMAT, APP_NAME, LOG_FORMAT
from .paths import (get_documents_dir, get_app_data_dir, get_data_dir,
                    get_logs_dir, get_errors_log_path, ensure_app_dirs)
from .bootstrap import bootstrap

# Garante as pastas (data/logs) e o errors.log antes de qualquer logger ser criado.
bootstrap()

from .sys_logs import SetLogger
from .validation import validar_nome_genero, validar_idade
from .formatting import format_time

__all__ = [
    'ENCODING_FORMAT',
    'APP_NAME',
    'LOG_FORMAT',
    'get_documents_dir',
    'get_app_data_dir',
    'get_data_dir',
    'get_logs_dir',
    'get_errors_log_path',
    'ensure_app_dirs',
    'bootstrap',
    'SetLogger',
    'validar_nome_genero',
    'validar_idade',
    'format_time'
]