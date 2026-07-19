"""Testes da infraestrutura de logging: contexto de sessão, fábrica de LogRecord e handlers
centrais (errors.log / full.log).

Tudo em memória — nenhum teste emite para os handlers de arquivo (não escreve em app-data). O
``full.log`` usa ``delay=True``, então enquanto não se loga na raiz nenhum arquivo é criado; estes
testes inspecionam a configuração (níveis, presença, formato) sem gerar linhas.
"""

import logging

import pytest

from compasso.utils import (LOG_FORMAT, SEM_SESSAO, definir_sessao, limpar_sessao,
                            sessao_atual, get_full_log_path, get_errors_log_path)


@pytest.fixture(autouse=True)
def _sessao_limpa():
    """Garante que o contexto de sessão não vaze entre testes."""
    limpar_sessao()
    yield
    limpar_sessao()


# --------------------------------------------------------------------------- contexto de sessão
def test_sessao_padrao_eh_sem_sessao():
    assert sessao_atual() == SEM_SESSAO


def test_definir_e_limpar_sessao():
    definir_sessao("fulano_25_M_19_07_2026")
    assert sessao_atual() == "fulano_25_M_19_07_2026"
    limpar_sessao()
    assert sessao_atual() == SEM_SESSAO


def test_definir_sessao_vazia_equivale_a_limpar():
    definir_sessao("qualquer")
    definir_sessao("   ")
    assert sessao_atual() == SEM_SESSAO


# --------------------------------------------------------------------- fábrica de LogRecord
def test_fabrica_carimba_a_sessao_no_record():
    """Todo LogRecord criado carrega o atributo ``session`` com a coleta em curso."""
    factory = logging.getLogRecordFactory()
    definir_sessao("coleta_abc")
    record = factory("m", logging.INFO, "f.py", 1, "msg", None, None)
    assert record.session == "coleta_abc"


def test_fabrica_usa_sem_sessao_fora_de_coleta():
    factory = logging.getLogRecordFactory()
    record = factory("m", logging.INFO, "f.py", 1, "msg", None, None)
    assert record.session == SEM_SESSAO


def test_format_com_sessao_renderiza_o_campo():
    """O LOG_FORMAT expõe a sessão; um record formatado a inclui entre colchetes."""
    assert "%(session)s" in LOG_FORMAT
    factory = logging.getLogRecordFactory()
    definir_sessao("coleta_xyz")
    record = factory("m", logging.WARNING, "f.py", 1, "atenção", None, None)
    saida = logging.Formatter(LOG_FORMAT).format(record)
    assert "[coleta_xyz]" in saida


# ------------------------------------------------------------------- handlers centrais
def _handler(marca):
    return next((h for h in logging.getLogger().handlers if getattr(h, marca, False)), None)


def test_handler_full_registrado_em_debug():
    """O consolidado captura TODOS os níveis: handler DEBUG na raiz apontando p/ full.log."""
    h = _handler("_compasso_full")
    assert h is not None, "handler do full.log não registrado na raiz"
    assert h.level == logging.DEBUG
    assert str(get_full_log_path()) == h.baseFilename


def test_handler_errors_registrado_em_warning():
    """O errors.log (pré-existente) continua em WARNING e intacto ao lado do full."""
    h = _handler("_compasso_errors")
    assert h is not None, "handler do errors.log não registrado na raiz"
    assert h.level == logging.WARNING
    assert str(get_errors_log_path()) == h.baseFilename
