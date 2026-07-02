"""Constantes de domínio do experimento (sem dependência de GUI nem de outros módulos).

Centraliza literais que antes apareciam duplicados entre `recorder.py` e `experiment.py`
(marcadores de evento, palavras-chave de condição) e os formatos de nome de sessão/faixa.
Módulo de literais puros — não importa nada do projeto, então pode ser importado por
qualquer módulo de `src.core` sem risco de ciclo.
"""

# ---------------------------------------------------------------------------
# Marcadores de evento gravados na coluna 'markers' do CSV/XLSX.
# ---------------------------------------------------------------------------
MARKER_COUNTDOWN_START = "countdown_start"
MARKER_MUSIC_START = "music_start"
MARKER_MUSIC_END = "music_end"
MARKER_STOP = "stop"

# ---------------------------------------------------------------------------
# Classificação da condição (fator) de uma faixa — ver `_classify_condition`.
# ---------------------------------------------------------------------------
CONDITION_MUSICA = "musica"
CONDITION_RUIDO = "ruido"
# Palavras-chave que classificam o fator como ruído (case-insensitive, por substring).
RUIDO_KEYWORDS = ("ruido", "ruído")

# ---------------------------------------------------------------------------
# Formatação dos nomes de pasta da sessão e de arquivo de faixa (ver recorder.py).
# ---------------------------------------------------------------------------
# Sufixo de data/hora da pasta da sessão: `nome_idade_genero_<SESSION_TIMESTAMP_FORMAT>`.
SESSION_TIMESTAMP_FORMAT = "%d-%m-%Y_%H-%M-%S"
# Largura mínima (com zero à esquerda) da ordem 1-based no nome do arquivo da faixa.
TRACK_ORDER_MIN_WIDTH = 2
