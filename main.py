import sys

from compasso.gui_qt import executar_app
from compasso.utils import SetLogger, get_app_version

main_logger = SetLogger(category='main', namelogger='mainLogger')

# Lida de pyproject.toml (`[project].version`) em runtime — fonte única, ver
# src/compasso/utils/version.py. Nunca hardcode a versão aqui de novo.
VERSION = get_app_version()


def main():
    main_logger.logger.info("=========================================")
    main_logger.logger.info("Iniciando o software ComPasso...")

    try:
        codigo = executar_app(versao=VERSION)
        main_logger.logger.info("Interface gráfica encerrada.")
        sys.exit(codigo)

    except SystemExit:
        raise
    except Exception as e:
        # Se QUALQUER erro crítico acontecer, salva no arquivo de log antes de fechar o programa.
        main_logger.logger.critical(f"Erro fatal na execução: {e}", exc_info=True)
        sys.exit(1)

    finally:
        # Sempre roda quando o programa fecha.
        main_logger.logger.info("Software encerrado.")
        main_logger.logger.info("=========================================\n")


if __name__ == "__main__":
    main()
