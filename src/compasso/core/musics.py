"""Lógica de negócio de músicas e condições (sem dependência de GUI).

Faz a varredura da pasta de áudios e o casamento de cada música com seu fator a
partir do arquivo Excel de condições. A camada de GUI apenas chama estas funções e
decide como exibir os resultados/erros.
"""

import os

import pandas as pd

from . import musics_logger

AUDIO_EXTENSIONS = ('.mp3', '.wav', '.ogg')


class MissingConditionError(Exception):
    """Levantada quando uma música não tem condição correspondente no Excel."""
    def __init__(self, music_name: str):
        self.music_name = music_name
        super().__init__(f"Nenhuma condição encontrada para {music_name}")


def scan_music_files(folder: str) -> list:
    """Retorna os caminhos absolutos dos arquivos de áudio na pasta.

    :raises FileNotFoundError: se a pasta não existir.
    """
    if not os.path.exists(folder):
        raise FileNotFoundError(folder)

    music_files = [os.path.join(folder, f) for f in os.listdir(folder)
                   if f.lower().endswith(AUDIO_EXTENSIONS)]
    for music in music_files:
        musics_logger.logger.info(f"Arquivo de música encontrado: {music}")
    return music_files


def match_conditions(music_files: list, conditions_path: str,
                     music_column: str = "musica", factor_column: str = "fator"):
    """Mapeia cada música para o seu fator a partir do Excel de condições.

    Os nomes das colunas são configuráveis (definidos pelo usuário na janela de configuração
    do experimento e persistidos no `.config`); os defaults reproduzem o comportamento antigo.

    :param music_column: nome da coluna que contém os nomes dos arquivos de áudio.
    :param factor_column: nome da coluna que contém os fatores/condições.
    :return: dict {caminho_da_musica: fator} em caso de sucesso, ou `None` se o Excel
        não tiver as colunas informadas ou estiver vazio.
    :raises FileNotFoundError: se o arquivo de condições não existir.
    :raises MissingConditionError: se alguma música não tiver condição correspondente.
    """
    if not os.path.exists(conditions_path):
        raise FileNotFoundError(conditions_path)

    conditions: pd.DataFrame = pd.read_excel(conditions_path)
    if conditions.empty or music_column not in conditions.columns or factor_column not in conditions.columns:
        return None

    mapping = {}
    for music in music_files:
        music_name = os.path.basename(music)
        fatores = conditions.loc[conditions[music_column] == music_name, factor_column].values #type: ignore
        if len(fatores) == 0:
            raise MissingConditionError(music_name)
        mapping[music] = fatores[0]
        musics_logger.logger.info(f"Condição encontrada para {music_name}: {fatores[0]}")
    return mapping
