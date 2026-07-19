"""Constantes de domínio do experimento (sem dependência de GUI nem de outros módulos).

Centraliza literais que antes apareciam duplicados entre `recorder.py` e `experiment.py`
(marcadores de evento, palavras-chave de condição) e os formatos de nome de sessão/faixa.
Módulo de literais puros — não importa nada do projeto, então pode ser importado por
qualquer módulo de `compasso.core` sem risco de ciclo.
"""

# ---------------------------------------------------------------------------
# Marcadores de evento gravados na coluna 'markers' do CSV/XLSX.
# ---------------------------------------------------------------------------
MARKER_COUNTDOWN_START = "INICIO_CONTAGEM"
MARKER_BEEP = "BEEP"
MARKER_MUSIC_START = "INICIO_MUSICA"
MARKER_MUSIC_END = "FIM_MUSICA"
MARKER_STOP = "PARADA_FORCADA"

# ---------------------------------------------------------------------------
# Classificação da condição (fator) de uma faixa — ver `_classify_condition`.
# ---------------------------------------------------------------------------
CONDITION_MUSICA = "musica"
CONDITION_RUIDO = "ruido"
# Palavras-chave que classificam o fator como ruído (case-insensitive, por substring).
RUIDO_KEYWORDS = ("ruido", "ruído", "Ruído", "Ruido", "noise", "barulho", "white noise", "pink noise")

# ---------------------------------------------------------------------------
# Tipos de sensor do BITalino e parâmetros de exibição do gráfico por sensor.
# ---------------------------------------------------------------------------
# Cada sensor define a unidade do eixo Y e a escala Y simétrica do gráfico: valor
# padrão, mínimo, máximo e passo do slider/grade — todos na unidade do sensor.
# "Só exibição": o dado gravado continua BRUTO; o sensor muda apenas o rótulo e a
# janela de exibição do gráfico (não há conversão do sinal). Ver graph_frame.py.
#
# `padrao` == `maximo` de propósito: o padrão é a escala MAIS AMPLA de cada sensor, para que
# nenhum sinal saia da tela sem que ninguém tenha pedido isso. Um padrão apertado corta picos
# legítimos (um artefato de piscada no EOG, uma resposta grande de EDA) e o usuário vê um traço
# ceifado sem saber por quê. Apertar a escala é fácil e reversível pelos botões +/- de zoom do
# eixo Y, que funcionam ao vivo — já sair da tela por padrão, não.
SENSOR_DEFAULT = "ECG"
SENSOR_TYPES = ("EDA", "ECG", "EMG", "EOG", "EEG", "EGG")
SENSOR_GRAPH_PARAMS = {
    "EDA": {"unidade": "µS", "padrao": 20.0, "minimo": 2.0, "maximo": 20.0, "passo": 1.0},
    "ECG": {"unidade": "mV", "padrao": 3.0, "minimo": 0.4, "maximo": 3.0, "passo": 0.2},
    "EMG": {"unidade": "mV", "padrao": 3.0, "minimo": 0.4, "maximo": 3.0, "passo": 0.2},
    "EOG": {"unidade": "mV", "padrao": 2.0, "minimo": 0.1, "maximo": 2.0, "passo": 0.1},
    "EEG": {"unidade": "µV", "padrao": 50.0, "minimo": 10.0, "maximo": 50.0, "passo": 10.0},
    "EGG": {"unidade": "mV", "padrao": 2.0, "minimo": 0.1, "maximo": 2.0, "passo": 0.1},
}

# ---------------------------------------------------------------------------
# Formatação dos nomes de pasta da sessão e de arquivo de faixa (ver recorder.py).
# ---------------------------------------------------------------------------
# Sufixo de data/hora da pasta da sessão: `nome_idade_genero_<SESSION_TIMESTAMP_FORMAT>`.
SESSION_TIMESTAMP_FORMAT = "%d-%m-%Y_%H-%M-%S"
# Largura mínima (com zero à esquerda) da ordem 1-based no nome do arquivo da faixa.
TRACK_ORDER_MIN_WIDTH = 2
