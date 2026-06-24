import sys

from src.gui import Compasso
from src.utils import SetLogger

main_logger = SetLogger(category='main', namelogger='mainLogger')

def main():
    main_logger.logger.info("=========================================")
    main_logger.logger.info("Iniciando o software Compasso...")
    
    try:
        app = Compasso(
            nome="Compasso - OpenSignals", 
        )
        main_logger.logger.info("Interface gráfica carregada com sucesso.")
        app.mainloop()

    except Exception as e:
        # Se QUALQUER erro crítico acontecer, salva no arquivo log antes de fechar o programa
        main_logger.logger.critical(f"Erro fatal na execução: {e}", exc_info=True)
        sys.exit(1)
        
    finally:
        # empre roda quando o programa fecha por conta do usuário
        main_logger.logger.info("Software encerrado pelo usuário.")
        main_logger.logger.info("=========================================\n")

if __name__ == "__main__":
    main()