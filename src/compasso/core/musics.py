"""Lógica de negócio de músicas e condições (sem dependência de GUI).

Faz a varredura da pasta de áudios e o casamento de cada música com seu fator a
partir do arquivo Excel de condições. A camada de GUI apenas chama estas funções e
decide como exibir os resultados/erros.
"""

import os

from . import musics_logger

# `pandas` é importado sob demanda dentro de `match_conditions` (e não no topo) porque é o
# import mais caro da stack (~centenas de ms) e este módulo é alcançado por `compasso.core`
# no arranque — pagá-lo aqui atrasava a janela a aparecer. Agora o custo cai dentro da
# varredura, que já roda em thread de trabalho e sob a tela de carregamento.

AUDIO_EXTENSIONS = ('.mp3', '.wav', '.ogg')


def scan_music_files(folder: str) -> list:
    """Retorna os caminhos absolutos dos arquivos de áudio na pasta.

    :raises FileNotFoundError: se a pasta não existir.
    """
    if not os.path.exists(folder):
        raise FileNotFoundError(folder)

    # as extensões aceitas são preferência do app; AUDIO_EXTENSIONS é o padrão de fábrica.
    from . import app_prefs   # import local: evita ciclo na montagem de `compasso.core`.

    extensoes = tuple(str(e).lower() for e in
                      (app_prefs.obter().get("extensoes_audio") or AUDIO_EXTENSIONS))
    musics_logger.logger.debug(
        f"Varrendo '{folder}' por áudios (extensões aceitas: {extensoes}).")
    music_files = [os.path.join(folder, f) for f in os.listdir(folder)
                   if f.lower().endswith(extensoes)]
    for music in music_files:
        musics_logger.logger.info(f"Arquivo de música encontrado: {music}")
    if not music_files:
        # pasta vazia ou com extensões fora das aceitas é um erro de configuração comum e
        # silencioso: sem áudios, a playlist fica vazia e o experimento não inicia.
        musics_logger.logger.warning(
            f"Nenhum áudio encontrado em '{folder}' (extensões aceitas: {extensoes}).")
    else:
        musics_logger.logger.info(f"Varredura concluída: {len(music_files)} áudio(s) em '{folder}'.")
    return music_files


def match_conditions(music_files: list, conditions_path: str,
                     music_column: str = "musica", factor_column: str = "fator"):
    """Mapeia cada música para o seu fator a partir do Excel de condições.

    Os nomes das colunas são configuráveis (definidos pelo usuário na janela de configuração
    do experimento e persistidos no `.config`); os defaults reproduzem o comportamento antigo.

    Músicas sem condição correspondente na planilha são ignoradas (não entram no mapeamento) em
    vez de interromper o casamento das demais — o chamador decide como avisar o usuário.

    :param music_column: nome da coluna que contém os nomes dos arquivos de áudio.
    :param factor_column: nome da coluna que contém os fatores/condições.
    :return: tupla `(mapping, ignoradas)`, onde `mapping` é um dict
        {caminho_da_musica: fator} com as músicas casadas e `ignoradas` é a lista dos nomes de
        arquivo sem condição correspondente; ou `(None, [])` se o Excel não tiver as colunas
        informadas ou estiver vazio.
    :raises FileNotFoundError: se o arquivo de condições não existir.
    """
    if not os.path.exists(conditions_path):
        raise FileNotFoundError(conditions_path)

    import pandas as pd   # import tardio: ver nota no topo do módulo.

    musics_logger.logger.debug(
        f"Casando {len(music_files)} áudio(s) com '{conditions_path}' "
        f"(coluna música='{music_column}', coluna fator='{factor_column}').")
    conditions = pd.read_excel(conditions_path)
    if conditions.empty or music_column not in conditions.columns or factor_column not in conditions.columns:
        # falha silenciosa antes deste log: a planilha certa com nomes de coluna errados devolvia
        # (None, []) sem pista alguma — o casamento música↔condição simplesmente não acontecia.
        musics_logger.logger.warning(
            f"Planilha de condições inutilizável ({'vazia' if conditions.empty else 'sem as colunas esperadas'}): "
            f"colunas presentes={list(conditions.columns)}, esperadas música='{music_column}' e fator='{factor_column}'.")
        return None, []

    mapping = {}
    ignoradas = []
    for music in music_files:
        music_name = os.path.basename(music)
        fatores = conditions.loc[conditions[music_column] == music_name, factor_column].values #type: ignore
        if len(fatores) == 0:
            musics_logger.logger.warning(f"Nenhuma condição encontrada para {music_name}; música ignorada.")
            ignoradas.append(music_name)
            continue
        mapping[music] = fatores[0]
        musics_logger.logger.info(f"Condição encontrada para {music_name}: {fatores[0]}")
    musics_logger.logger.info(
        f"Casamento concluído: {len(mapping)} música(s) casada(s), {len(ignoradas)} ignorada(s).")
    return mapping, ignoradas
