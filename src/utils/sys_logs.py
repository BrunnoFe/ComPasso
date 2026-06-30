import time
import logging

from src.utils.configs import ENCODING_FORMAT, LOG_FORMAT
from src.utils.paths import get_logs_dir


class SetLogger():
    """Cria um logger nomeado que grava em uma subpasta própria dentro de ``logs/``.

    O arquivo fica em ``<app-data>/Compasso/logs/<category>/<category>_<timestamp>.log``.
    A subpasta é criada sob demanda, de modo que o logger funciona independentemente da
    ordem de importação.
    """

    def __init__(self, namelogger: str, category: str, level: str = 'DEBUG') -> None:
        """
        Args:
            namelogger (str): nome do logger (único por módulo).
            category (str): categoria/subpasta dos logs (ex.: 'gui', 'connections').
            level (str, optional): nível mínimo. Default 'DEBUG'.
        """
        if level.upper() not in logging._nameToLevel:
            level = 'DEBUG'

        self.logger: logging.Logger = logging.getLogger(namelogger)
        self.logger.setLevel(logging._nameToLevel[level.upper()])

        folder = get_logs_dir() / category
        folder.mkdir(parents=True, exist_ok=True)
        timestamp = time.strftime(r"%d_%m_%Y_%H_%M_%S", time.localtime())
        self.logfilepath: str = str(folder / f"{category}_{timestamp}.log")

        self.logFormat = logging.Formatter(fmt=LOG_FORMAT)

        # evita anexar handlers duplicados caso o mesmo logger seja reinstanciado
        if not self.logger.handlers:
            self.logFileHandler = logging.FileHandler(self.logfilepath, encoding=ENCODING_FORMAT)
            self.logFileHandler.setFormatter(self.logFormat)

            self.logStremHandler = logging.StreamHandler()
            self.logStremHandler.setFormatter(self.logFormat)

            self.logger.addHandler(self.logFileHandler)
            self.logger.addHandler(self.logStremHandler)

        self.logger.info(f'Logger "{namelogger}" iniciado')
