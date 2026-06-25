import customtkinter as ctk

from .. import gui_logger
from ..guiconfigs import set_grids
from ..theme import (AZUL, AZUL_CLARO, BASE_FONT_MED, ROSA, CINZA, TRANSPARENTE,
                     BASE_FONT, BORDER_WIDTH, CORNER)
from ..widgets import show_message, bind_hover_images, styled_label, styled_button, styled_combobox, styled_entry
from src.core import connectar_bitalino


class UpFrame(ctk.CTkFrame):
    """Painel superior: logo, seleção de MAC/canal, escaneamento e conexão do Bitalino."""

    def __init__(self, master, ctx):
        super().__init__(master, corner_radius=CORNER, border_width=BORDER_WIDTH, border_color=AZUL, bg_color=AZUL, fg_color=ROSA, background_corner_colors=(AZUL, AZUL, AZUL, AZUL))
        set_grids(self, rows_conf={1: [0]}, column_conf={2: [0], 1: [1, 2]})

        self.ctx = ctx
        imgs = ctx.images

        self.logo = ctk.CTkLabel(self, image=imgs.logo, corner_radius=CORNER, anchor=ctk.W, bg_color=ROSA, fg_color=TRANSPARENTE, text="")
        self.logo.grid(row=0, column=0, pady=15, padx=15, sticky=ctk.NSEW)

        self.mac_addr_var = ctk.StringVar(value="Escolha o dispositivo...")

        self.mac_adress_label = styled_label(self, text="Insira o endereço MAC do Bitalino:", font=BASE_FONT_MED)
        self.mac_adress_label.grid(row=0, column=1, pady=15, padx=10, sticky=ctk.N)

        self.up_select_macaddr = styled_entry(self, placeholder_text="Endereço MAC", textvariable=self.mac_addr_var, bg_color=ROSA, justify=ctk.CENTER, font=BASE_FONT_MED)
        self.up_select_macaddr.grid(row=0, column=1, pady=10, padx=10, sticky=ctk.EW)

        self.scan_controls = ctk.CTkFrame(self, fg_color=TRANSPARENTE, bg_color=ROSA)
        self.scan_controls.grid(row=0, column=1, pady=15, padx=10, sticky=ctk.S)

        self.canal_label = styled_label(self.scan_controls, text="Canal:", bg_color=TRANSPARENTE)
        self.canal_label.grid(row=0, column=0, padx=(0, 8), sticky=ctk.S)

        self.canal_var = ctk.StringVar(value="A1")
        self.canal_combobox = styled_combobox(self.scan_controls, state="readonly", variable=self.canal_var, width=90,
                                               values=["A1", "A2", "A3", "A4", "A5", "A6"], justify=ctk.LEFT, 
                                               command=self._on_channel_change)
        self.canal_combobox.grid(row=0, column=1, sticky=ctk.S)

        self.disconnect_button = styled_button(self.scan_controls, text="Desconectar",
                                               bg_color=TRANSPARENTE, fg_color=ROSA,
                                               command=self.disconnect_bitalino)
        self.disconnect_button.grid(row=0, column=2, padx=(8, 0), sticky=ctk.S)

        self.button_conectbt_img = imgs.conect_bitalino
        self.button_conectbt_img_dim = imgs.conect_bitalino_dim
        self.button_conectbt_img_conectado = imgs.conectado

        self.button_conect_bitalino = ctk.CTkButton(self, image=self.button_conectbt_img, bg_color=ROSA, fg_color=TRANSPARENTE,
                                                    text="", border_color=AZUL, border_spacing=0, hover=False, hover_color=AZUL_CLARO,
                                                    command=lambda: self.conect_bitalino(self.mac_addr_var.get()))
        self.button_conect_bitalino.grid(row=0, column=2, pady=20, padx=10, sticky=ctk.NSEW)
        bind_hover_images(self.button_conect_bitalino, self.button_conectbt_img, self.button_conectbt_img_dim)

    def _on_channel_change(self, canal_escolhido: str):
        """Atualiza o canal LSL usado na coluna 'signal' (padrão 0 se inválido)."""
        try:
            self.ctx.signal_channel = int(canal_escolhido[1])
        except (TypeError, ValueError):
            self.ctx.signal_channel = 0
        gui_logger.logger.info(f"Canal de sinal selecionado: {self.ctx.signal_channel}")

    def conect_bitalino(self, mac_addr: str):
        """Conecta ao Bitalino fora da thread da GUI; trata o resultado na thread principal."""
        gui_logger.logger.info(f"Solicitada conexão ao Bitalino com MAC: {mac_addr}, type: {type(mac_addr)}")
        self.mac_addr: str = mac_addr.split(" - ")[-1]  # extrai o MAC do formato "Nome - MAC"
        gui_logger.logger.info(f"Endereço MAC extraído para conexão: {self.mac_addr}")
        self.button_conect_bitalino.configure(state="disabled")
        self.ctx.run_async(lambda: self._connect_bitalino_worker(self.mac_addr),
                           on_done=self._handle_connection_result)

    def _connect_bitalino_worker(self, mac_addr: str):
        """Executa a conexão LSL (bloqueante) fora da thread da GUI. Retorna o inlet ou erro (str)."""
        gui_logger.logger.info(f"Conectando ao Bitalino com MAC: {mac_addr}")
        return connectar_bitalino(mac_addr=mac_addr)

    def _handle_connection_result(self, bitalino):
        """Trata o resultado da conexão: `str`/`Exception` é erro; caso contrário é o inlet."""
        if isinstance(bitalino, (str, Exception)):
            self.button_conect_bitalino.configure(state="normal")
            msg = bitalino if isinstance(bitalino, str) else f"Erro inesperado ao conectar: {bitalino}"
            show_message("Erro na conexão", msg, icon="warning")
        else:
            self.ctx.bitalino = bitalino
            self.ctx.mac_addr = self.mac_addr
            self.ctx.status_text.set("Bitalino conectado")
            self.button_conect_bitalino.unbind('<Enter>')
            self.button_conect_bitalino.unbind('<Leave>')
            self.button_conect_bitalino.configure(state="disabled", image=self.button_conectbt_img_conectado)
            self.up_select_macaddr.configure(state="disabled")

    def disconnect_bitalino(self):
        """Encerra manualmente a conexão LSL com o Bitalino e restaura a UI de conexão.

        Bloqueia (com aviso) se houver um experimento em andamento — o usuário deve parar
        o experimento antes de desconectar."""
        runner = self.ctx.runner
        if runner is not None and runner.is_running():
            show_message("Atenção", "Pare o experimento antes de desconectar o Bitalino.", icon="warning")
            return

        inlet = self.ctx.bitalino
        if inlet is not None:
            try:
                inlet.close_stream()
            except Exception as e:
                gui_logger.logger.warning(f"Falha ao encerrar o stream do Bitalino: {e}")
        self.ctx.bitalino = None
        self.ctx.mac_addr = None
        gui_logger.logger.info("Bitalino desconectado manualmente pelo usuário.")
        self.ctx.status_text.set("Bitalino desconectado")

        # restaura o botão de conexão e o campo de MAC
        self.button_conect_bitalino.configure(state="normal", image=self.button_conectbt_img)
        bind_hover_images(self.button_conect_bitalino, self.button_conectbt_img, self.button_conectbt_img_dim)
        self.up_select_macaddr.configure(state="normal")
