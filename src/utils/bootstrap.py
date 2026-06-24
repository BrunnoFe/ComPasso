"""Inicialização da aplicação: cria as pastas na primeira execução e configura o
arquivo central de erros (``errors.log``).

Idempotente — pode ser chamado várias vezes com segurança. É invocado automaticamente
quando o pacote ``src.utils`` é importado, garantindo que as pastas existam antes de
qualquer ``SetLogger`` ser criado.
"""

import logging
from logging.handlers import RotatingFileHandler

from .configs import ENCODING_FORMAT, LOG_FORMAT
from .paths import ensure_app_dirs, get_errors_log_path

_configured = False


def bootstrap() -> None:
    """Garante as pastas da aplicação e instala o handler central de erros (uma vez)."""
    global _configured
    if _configured:
        return
    ensure_app_dirs()
    _configure_error_log()
    _configured = True


def _configure_error_log() -> None:
    """Adiciona ao logger raiz um RotatingFileHandler de nível WARNING.

    Como todos os loggers nomeados propagam para o raiz, qualquer WARNING/ERROR/CRITICAL
    de qualquer módulo é gravado em ``errors.log`` automaticamente.
    """
    root = logging.getLogger()
    if any(getattr(h, "_compasso_errors", False) for h in root.handlers):
        return  # já configurado

    handler = RotatingFileHandler(get_errors_log_path(), maxBytes=1_000_000, backupCount=5,
                                  encoding=ENCODING_FORMAT, delay=True)
    handler.setLevel(logging.WARNING)
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    handler._compasso_errors = True  # marca para evitar duplicação
    root.addHandler(handler)
