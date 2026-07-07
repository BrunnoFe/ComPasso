import threading

import customtkinter as ctk

from . import gui_logger
from src.core.player import Player

class AppContext:
    """Estado compartilhado da aplicação ComPasso.

    Um único objeto, criado pela janela raiz (`ComPasso`) e repassado para todos os
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
        self.mac_addr: str | None = None          # str | None
        self.signal_channel: int = 0       # índice do canal LSL usado na coluna 'signal'
        self.runner = None            # ExperimentRunner | None

        # fachada do gráfico do sinal (GraphFrame), registrada pelo próprio frame.
        # None quando não há UI do gráfico; o runner alimenta/controla via os métodos
        # thread-safe push/begin/end/reset_idle (ver src/gui/frames/graph_frame.py).
        self.signal_plot = None

        # configurações de exibição do gráfico (ver src/core/config_manager.py e a janela
        # "Configurações do Gráfico"). Populado no arranque a partir de get_graph_prefs();
        # o GraphFrame lê este dict ao construir o GraficoSinal (sobrevive à troca de tema).
        self.graph_settings: dict = {}

        # callback registrado pelo DownFrame para alternar o estado do botão principal
        # ("comecar" | "rodando" | "continuar"); chamado pelo runner via post().
        self.set_button_state = None

        # callback registrado pela ParticipantCard: salva infos do participante em silêncio
        # se o formulário estiver preenchido mas não salvo (usado pelo botão "começar").
        self.save_participant_infos_if_filled = None

        # callback registrado pela ParticipantCard: habilita/desabilita o botão "Editar"
        # (bloqueado pelo ExperimentRunner enquanto uma sessão está em andamento).
        self.set_participant_editable = None

        # callback registrado pelo MainFrame: ao iniciar o experimento (True) recolhe os
        # cards e trava o botão de recolher; ao finalizar/parar (False) expande e libera.
        self.set_experiment_ui_lock = None

        # watchdog de conexão do BITalino e callback de perda de conexão (top_frame).
        self.watchdog = None
        self.handle_connection_lost = None

        # callback registrado pelo StepperFrame: re-renderiza as etapas a partir do estado
        # (bitalino conectado, infos salvas, arquivos mapeados). Chamado por vários frames
        # sempre que uma dessas condições muda.
        self.refresh_stepper = None

        # dados do participante
        self.nome = None
        self.idade = None
        self.genero = None
        self.infos_saved = False

        # arquivos / condições / saída
        self.music_folder: str | None = None
        self.conditions_file: str | None = None
        self.save_dir: str | None = None
        self.music_files: list = []
        self.music_condition_mapping: dict = {}

        # configuração do experimento (.config): quantidade total de reproduções de ruído e
        # se há uma config carregada (pré-requisito para iniciar — ver bottom_frame).
        self.noise_quantity: int = 0
        # tempo pré-estímulo (s): contagem regressiva antes de cada faixa (padrão em config_manager)
        self.pre_stimulus_seconds: int = 5
        self.config_loaded: bool = False

        # textos reativos dos rótulos (qualquer frame faz .set())
        self.status_text = ctk.StringVar(value="Conecte o Bitalino")
        self.current_music_text = ctk.StringVar(value="—")
        self.current_condition_text = ctk.StringVar(value="")   # "música"/"ruído" (chip do player)
        self.volume_text = ctk.StringVar(value="Volume: 50%")
        self.time_begin_text = ctk.StringVar(value="00:00")
        self.time_end_text = ctk.StringVar(value="00:00")

        # contadores separados (número concluído + total) para o estilo do rodapé
        self.music_done_text = ctk.StringVar(value="0")
        self.music_total_text = ctk.StringVar(value="0")
        self.ruido_done_text = ctk.StringVar(value="0")
        self.ruido_total_text = ctk.StringVar(value="0")

        # progresso da sessão (barra + texto "N / total" no rodapé)
        self.session_progress = ctk.DoubleVar(value=0.0)
        self.session_status_text = ctk.StringVar(value="0 / 0")

        gui_logger.logger.info("AppContext inicializado.")

    def notify_stepper(self) -> None:
        """Agenda a re-renderização do stepper na thread da GUI, se registrado."""
        cb = self.refresh_stepper
        if cb is not None:
            self.run_after(cb)

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
                self.run_after(func=lambda: on_done(result)) #type: ignore

        threading.Thread(target=runner, daemon=True).start()
