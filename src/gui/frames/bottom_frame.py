import customtkinter as ctk

from ..guiconfigs import set_grids
from ..theme import AZUL, ROSA, TRANSPARENTE, BORDER_WIDTH, CORNER, NSE
from ..widgets import show_message, bind_hover_images, styled_label
from src.core import ExperimentRunner


class DownFrame(ctk.CTkFrame):
    """Painel inferior: contadores do experimento, status e o botão principal (começar)."""

    def __init__(self, master, ctx):
        super().__init__(master, corner_radius=CORNER, border_width=BORDER_WIDTH, bg_color=AZUL, fg_color=ROSA, border_color=AZUL)
        set_grids(self, rows_conf={1: [0, 1]}, column_conf={1: [0, 1, 2]}, grid_row=2)

        self.ctx = ctx

        self.exp_progress_music_label = styled_label(self, textvariable=self.ctx.music_counter)
        self.exp_progress_music_label.grid(row=0, column=0, padx=15, pady=10, sticky=ctk.W)

        self.exp_progress_ruido_label = styled_label(self, textvariable=self.ctx.ruido_counter)
        self.exp_progress_ruido_label.grid(row=1, column=0, padx=15, pady=10, sticky=ctk.W)

        self.down_infos_label = styled_label(self, textvariable=self.ctx.status_text)
        self.down_infos_label.grid(row=1, column=1, padx=15, pady=10, sticky=NSE)

        # imagens dos três estados do botão principal (comecar -> rodando -> continuar),
        # já carregadas e cacheadas em ctx.images (com fallback para "comecar").
        imgs = ctx.images
        self._button_images = {
            "comecar": (imgs.comecar, imgs.comecar_dim),
            "rodando": (imgs.rodando, imgs.rodando_dim),
            "continuar": (imgs.continuar, imgs.continuar_dim),
        }
        self._button_state = "comecar"
        self._comecar_enabled = None   # cache do último estado aplicado (evita flicker)

        self.comecar_bt = ctk.CTkButton(self, image=imgs.comecar, bg_color=TRANSPARENTE, fg_color=TRANSPARENTE, text="", hover=False, command=self.comecar_experimento)
        self.comecar_bt.grid(row=0, rowspan=3, column=2, pady=20, padx=20, sticky=NSE)

        # expõe a troca de estado do botão para o runner (chamada via ctx.run_after)
        self.ctx.set_button_state = self._set_button_state
        self._set_button_state("comecar")
        self._refresh_comecar_enabled()

    def _set_button_state(self, state: str):
        """Alterna o estado do botão principal: 'comecar' | 'rodando' | 'continuar'."""
        self._button_state = state
        normal, dim = self._button_images.get(state, self._button_images["comecar"])
        self.comecar_bt.unbind('<Enter>')
        self.comecar_bt.unbind('<Leave>')

        if state == "rodando":
            self.comecar_bt.configure(image=normal, state="disabled", command=lambda: None)
        elif state == "continuar":
            self.comecar_bt.configure(image=normal, state="normal", command=self._on_continuar)
            bind_hover_images(self.comecar_bt, normal, dim)
        else:  # comecar
            self.comecar_bt.configure(image=normal, command=self.comecar_experimento)
            bind_hover_images(self.comecar_bt, normal, dim, only_when_enabled=True)

    def _refresh_comecar_enabled(self):
        """Habilita 'começar' somente quando os cinco pré-requisitos estão satisfeitos.

        Só reconfigura o botão quando o estado habilitado/desabilitado realmente muda —
        reconfigurar a cada ciclo redesenha o botão e causa "flickering"."""
        try:
            if self._button_state == "comecar":
                running = self.ctx.runner is not None and self.ctx.runner.is_running()
                ready = (self.ctx.bitalino is not None and self.ctx.infos_saved
                         and bool(self.ctx.music_files) and bool(self.ctx.music_condition_mapping)
                         and bool(self.ctx.save_dir) and not running)
                if ready != self._comecar_enabled:
                    self._comecar_enabled = ready
                    self.comecar_bt.configure(state="normal" if ready else "disabled")
            else:
                self._comecar_enabled = None
        except Exception:
            pass
        self.after(200, self._refresh_comecar_enabled)

    def _on_continuar(self):
        """Avança para a próxima faixa (botão no estado 'continuar')."""
        if self.ctx.runner is not None:
            self.ctx.status_text.set("Continuando...")
            self.ctx.runner.continuar()

    def comecar_experimento(self):
        """Valida os pré-requisitos no contexto e inicia o experimento em thread separada."""
        problema = self._validar_prerequisitos()
        if problema:
            show_message("Atenção", problema, icon="warning")
            return

        if self.ctx.runner is None:
            self.ctx.runner = ExperimentRunner(self.ctx)
        self.ctx.status_text.set("Iniciando experimento...")
        self.ctx.runner.start()

    def _validar_prerequisitos(self) -> str:
        """Retorna uma mensagem de erro se algum pré-requisito faltar, ou '' se tudo certo."""
        if self.ctx.bitalino is None:
            return "Conecte o Bitalino antes de iniciar o experimento."
        if not self.ctx.infos_saved:
            return "Salve as informações do participante antes de iniciar."
        if not self.ctx.music_files:
            return "Carregue os arquivos de música antes de iniciar."
        if not self.ctx.save_dir:
            return "Escolha o diretório para salvar os dados antes de iniciar."
        if self.ctx.runner is not None and self.ctx.runner.is_running():
            return "O experimento já está em andamento."
        return ""
