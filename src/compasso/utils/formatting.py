"""Funções utilitárias de formatação (sem dependência de GUI)."""


def format_time(secs: float) -> str:
    """Formata um número de segundos como 'MM:SS'. Retorna '00:00' em caso de erro."""
    try:
        secs = int(secs)
        return f"{secs // 60:02d}:{secs % 60:02d}"
    except Exception:
        return "00:00"
