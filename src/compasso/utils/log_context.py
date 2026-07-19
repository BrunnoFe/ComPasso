"""Contexto de correlação dos logs: o identificador da coleta em curso.

Carimba cada linha de log com o nome da sessão de coleta ativa (o campo ``%(session)s`` do
``LOG_FORMAT``), permitindo correlacionar mensagens de módulos diferentes — recorder, experiment,
player, connections — dentro de uma mesma coleta. Sem isso, o ``full.log`` intercala as linhas de
todos os módulos sem nenhum fio condutor entre elas.

Vive em ``utils`` (não em ``core``) de propósito: a fábrica de ``LogRecord`` que consome este
valor é instalada no ``bootstrap``, antes de qualquer logger existir, e ``utils`` não pode importar
``core`` (ciclo — ver CLAUDE.md). Quem sabe quando uma coleta começa é o ``core`` (o
``ExperimentRunner``), que chama ``definir_sessao(...)``/``limpar_sessao()`` — a direção de import
permitida (core -> utils).

Thread-safe: a coleta roda numa thread daemon separada da GUI, então o setter e o leitor (chamado
pela fábrica de ``LogRecord``, a partir de qualquer thread que logue) disputam o mesmo estado.
"""

import threading

# Sentinela para linhas fora de qualquer coleta (arranque, edição de config, ociosidade).
SEM_SESSAO = "-"

_lock = threading.Lock()
_sessao_atual = SEM_SESSAO


def definir_sessao(sessao_id: str) -> None:
    """Define o identificador da coleta em curso (carimbado em todo log a partir daqui).

    Args:
        sessao_id: nome da sessão de coleta (tipicamente a pasta da sessão). Um valor vazio
            equivale a limpar o contexto.
    """
    global _sessao_atual
    with _lock:
        _sessao_atual = str(sessao_id).strip() or SEM_SESSAO


def limpar_sessao() -> None:
    """Remove o identificador de coleta (volta ao estado 'fora de sessão')."""
    global _sessao_atual
    with _lock:
        _sessao_atual = SEM_SESSAO


def sessao_atual() -> str:
    """Retorna o identificador da coleta em curso, ou ``SEM_SESSAO`` se não houver."""
    with _lock:
        return _sessao_atual
