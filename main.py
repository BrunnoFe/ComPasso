import sys

import customtkinter as ctk

from src.gui import ComPasso
from src.utils import SetLogger

main_logger = SetLogger(category='main', namelogger='mainLogger')

# Tempo (ms) que a tela de carregamento fica visível antes da janela principal ser montada.
SPLASH_DURATION_MS = 3000


def _show_splash():
    """Mostra a tela de carregamento numa raiz Tk descartável, própria da splash.

    A janela principal (`ComPasso`) só é construída DEPOIS que a splash fecha — assim ela
    nunca chega a aparecer/piscar na tela antes da hora. Usa uma raiz oculta separada (em
    vez da própria `ComPasso`) porque construir o `ComPasso` já monta toda a UI (menu,
    frames...), o que é lento e ficaria visível antes de um `withdraw()` surtir efeito.
    """
    from src.gui.loading_screen import run_splash

    splash_root = ctk.CTk()
    splash_root.withdraw()
    try:
        # `quit()` apenas encerra o mainloop desta raiz; a splash chama `win.destroy()`
        # (seu próprio Toplevel) logo em seguida — destruir a raiz aqui causaria erro.
        run_splash(master=splash_root, duration_ms=SPLASH_DURATION_MS, on_done=splash_root.quit)
        splash_root.mainloop()
    finally:
        splash_root.destroy()


def main():
    main_logger.logger.info("=========================================")
    main_logger.logger.info("Iniciando o software ComPasso...")

    try:
        # Tela de carregamento: puramente decorativa — se falhar, segue para o app normalmente.
        try:
            _show_splash()
        except Exception as e:
            main_logger.logger.warning(f"Falha ao exibir a tela de carregamento: {e}")

        app = ComPasso(
            nome="ComPasso",
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