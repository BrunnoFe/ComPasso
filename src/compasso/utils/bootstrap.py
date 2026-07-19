"""Inicialização da aplicação: cria as pastas na primeira execução e configura os handlers
centrais de log (``errors.log`` e o consolidado ``logs/full/full.log``), além da fábrica de
``LogRecord`` que carimba cada linha com o identificador da coleta em curso.

Idempotente — pode ser chamado várias vezes com segurança. É invocado automaticamente quando o
pacote ``compasso.utils`` é importado, garantindo que as pastas existam e que a fábrica esteja
instalada antes de qualquer ``SetLogger`` ser criado (senão o campo ``%(session)s`` do
``LOG_FORMAT`` não existiria no LogRecord e o formatador levantaria ``KeyError``).
"""

import logging
from logging.handlers import RotatingFileHandler

from .configs import ENCODING_FORMAT, LOG_FORMAT
from .paths import ensure_app_dirs, get_errors_log_path, get_full_log_path
from .log_context import sessao_atual, SEM_SESSAO

_configured = False


def bootstrap() -> None:
    """Garante as pastas da aplicação e instala os handlers e a fábrica de log (uma vez)."""
    global _configured
    if _configured:
        return
    ensure_app_dirs()
    _install_record_factory()
    _silenciar_terceiros_ruidosos()
    _configure_error_log()
    _configure_full_log()
    _configured = True


# Loggers de terceiros que despejam DEBUG em altíssimo volume e afogariam o full.log (que é
# DEBUG na raiz). `comtypes` loga cada "Release <POINTER...>" da camada COM do pycaw — dezenas de
# linhas por consulta de volume, sem valor para a rastreabilidade da coleta. Elevados a WARNING
# para que só o essencial deles chegue ao consolidado.
_TERCEIROS_RUIDOSOS = ("comtypes",)


def _silenciar_terceiros_ruidosos() -> None:
    """Eleva o nível de loggers de bibliotecas de terceiros excessivamente verbosos."""
    for nome in _TERCEIROS_RUIDOSOS:
        logging.getLogger(nome).setLevel(logging.WARNING)


def _install_record_factory() -> None:
    """Faz toda linha de log carregar o identificador da coleta (campo ``session``).

    A fábrica de ``LogRecord`` roda para **todos** os registros de **todos** os loggers, então
    injetar ``record.session`` aqui garante que qualquer handler (per-categoria, errors.log,
    full.log) possa usar ``%(session)s`` no formato sem risco de ``KeyError``. Preferido a um
    ``Filter`` por handler justamente por ser um ponto único, independente de quantos handlers
    existam. Ver ``log_context.py``.
    """
    default_factory = logging.getLogRecordFactory()
    if getattr(default_factory, "_compasso_session", False):
        return  # já instalada (bootstrap reentrante em processo de longa vida)

    def factory(*args, **kwargs):
        record = default_factory(*args, **kwargs)
        # a fábrica pode rodar antes de qualquer coleta; sessao_atual() devolve SEM_SESSAO.
        record.session = sessao_atual()
        return record

    factory._compasso_session = True  # type: ignore[attr-defined]  # marca p/ evitar reinstalação
    logging.setLogRecordFactory(factory)


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
    handler._compasso_errors = True  #type: ignore  # marca para evitar duplicação
    root.addHandler(handler)


def _configure_full_log() -> None:
    """Adiciona ao logger raiz um RotatingFileHandler DEBUG que consolida TUDO.

    Diferente do ``errors.log`` (só WARNING+) e dos arquivos por categoria (um por módulo), este
    reúne **todos os níveis de todos os módulos** num único arquivo. É possível porque todos os
    loggers nomeados propagam para o raiz e a propagação chama os handlers do raiz sem reavaliar o
    nível do próprio logger raiz — só o nível do handler (DEBUG) importa.

    Rotação por tamanho (5 MB × 5 backups) para não crescer sem limite; ``delay=True`` para só
    criar o arquivo quando a primeira linha for gravada.
    """
    root = logging.getLogger()
    if any(getattr(h, "_compasso_full", False) for h in root.handlers):
        return  # já configurado

    handler = RotatingFileHandler(get_full_log_path(), maxBytes=5_000_000, backupCount=5,
                                  encoding=ENCODING_FORMAT, delay=True)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    handler._compasso_full = True  # type: ignore  # marca para evitar duplicação
    root.addHandler(handler)
