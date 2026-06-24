import threading
from typing import Optional, TYPE_CHECKING

import customtkinter as ctk

from . import gui_logger
from src.core.player import Player

if TYPE_CHECKING:
    from .assets import AppImages


class AppContext:
    """Estado compartilhado da aplicação Compasso.

    Um único objeto, criado pela janela raiz (`Compasso`) e repassado para todos os
    frames, que centraliza:

    - serviços/estado: o `Player`, o inlet do Bitalino, dados do participante,
      arquivos de música e mapeamento de condições, diretório de saída;
    - textos reativos dos rótulos como `ctk.StringVar` — qualquer frame pode chamar
      `.set()` e os widgets ligados via `textvariable=` atualizam sozinhos, sem que
      um frame precise alcançar o widget de outro (fim dos `master.master.x`);
    - utilitários de threading (`run_after`, `run_async`) que padronizam o padrão de
      thread daemon + `after()` já usado na GUI.

    Regra: nunca tocar widgets/Vars fora da thread da GUI — use `run_after()` para agendar
    a atualização na thread principal.
    """

    def __init__(self, root: ctk.CTk):
        self.root = root

        # serviços / estado
        self.player: Player = Player()
        self.bitalino = None          # StreamInlet | None
        self.mac_addr = None          # str | None
        self.signal_channel = 0       # índice do canal LSL usado na coluna 'signal'
        self.runner = None            # ExperimentRunner | None
        self.images: Optional["AppImages"] = None   # criado por Compasso após o root

        # callback registrado pelo DownFrame para alternar o estado do botão principal
        # ("comecar" | "rodando" | "continuar"); chamado pelo runner via post().
        self.set_button_state = None

        # dados do participante
        self.nome = None
        self.idade = None
        self.genero = None
        self.infos_saved = False

        # arquivos / condições / saída
        self.music_folder = None
        self.conditions_file = None
        self.save_dir = None
        self.music_files = []
        self.music_condition_mapping = {}

        # textos reativos dos rótulos (qualquer frame faz .set())
        self.status_text = ctk.StringVar(value="Conecte o Bitalino")
        self.current_music_text = ctk.StringVar(value="Música: —")
        self.volume_text = ctk.StringVar(value="Volume: 50%")
        self.time_begin_text = ctk.StringVar(value="00:00")
        self.time_end_text = ctk.StringVar(value="00:00")
        self.music_counter = ctk.StringVar(value="Música: 0 de 0")
        self.pausa_counter = ctk.StringVar(value="Pausa: 0 de 0")
        self.ruido_counter = ctk.StringVar(value="Ruído: 0 de 0")

        gui_logger.logger.info("AppContext inicializado.")

    def run_after(self, func) -> None:
        """Agenda `fn()` para rodar na thread da GUI (seguro a partir de qualquer thread)."""
        try:
            self.root.after(0, func)
        except Exception as e:
            gui_logger.logger.error(f"Falha ao agendar callback na GUI: {e}")

    def run_async(self, work, on_done=None) -> None:
        """Executa `work()` em uma thread daemon e agenda `on_done(result)` na GUI.

        Exceções em `work()` são registradas via `gui_logger` e repassadas como
        resultado (instância de `Exception`) para `on_done`, se fornecido.

        :param work: callable sem argumentos executado fora da thread da GUI.
        :param on_done: callable(result) executado na thread da GUI ao final (opcional).
        """
        def runner():
            try:
                result = work()
            except Exception as e:
                gui_logger.logger.error(f"Erro em run_async: {e}")
                result = e
            if on_done is not None:
                self.run_after(func=lambda: on_done(result))

        threading.Thread(target=runner, daemon=True).start()
