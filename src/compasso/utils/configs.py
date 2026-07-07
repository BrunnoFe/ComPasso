ENCODING_FORMAT = 'utf-8'

# Nome da aplicação — usado para montar as pastas em Documentos e em app-data.
APP_NAME = 'ComPasso'

# Página do projeto (menu "Ajuda" -> "Página do projeto").
PROJECT_URL = 'https://github.com/BrunnoFe/Compasso'

PROJECT_GITSITE = 'https://brunnofe.github.io/ComPasso/'

# Formato único dos registros de log (reutilizado pelos loggers e pelo errors.log).
LOG_FORMAT = '%(asctime)s:%(filename)s: %(name)s: %(levelname)s: %(funcName)s -> %(message)s'

# ---------------------------------------------------------------------------
# Nomes de pastas e arquivos da aplicação (resolvidos em src/utils/paths.py e
# src/core/config_manager.py). Centralizados aqui para que renomear uma pasta ou
# arquivo de saída seja uma alteração de uma única linha.
# ---------------------------------------------------------------------------
DATA_DIRNAME = 'Dados'                          # <Documentos>/ComPasso/<DATA_DIRNAME>
LOGS_DIRNAME = 'logs'                          # <app-data>/ComPasso/<LOGS_DIRNAME>
EXPERIMENT_FILES_DIRNAME = 'Configurações do Experimento'  # <Documentos>/ComPasso/<...>
ERRORS_LOG_FILENAME = 'errors.log'             # <app-data>/ComPasso/<ERRORS_LOG_FILENAME>
PREFS_FILENAME = 'prefs.json'                  # <app-data>/ComPasso/<PREFS_FILENAME>
ICON_FILENAME = 'icon.ico'                     # assets/<ICON_FILENAME> (ícone da janela)

# Formato de data/hora no nome dos arquivos de log (um por execução).
LOG_TIMESTAMP_FORMAT = '%d_%m_%Y_%H_%M_%S'
