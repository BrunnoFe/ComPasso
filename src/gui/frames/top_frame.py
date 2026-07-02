import customtkinter as ctk

from .. import gui_logger
from ..theme import (BAR_BG, BORDER, INPUT_BG, TEXT, FAINT, ACCENT,
                     ACCENT_TINT, ACCENT_BORDER, SUCCESS, TRANSPARENTE,
                     DISPLAY_FAMILY, MONO_FAMILY, CORNER_SM, CORNER_PILL,
                     INPUT_H, BTN_H, FONT_2XS, FONT_XS, FONT_MD, FONT_3XL)
from ..widgets import show_message, caption, ghost_button, styled_button, Card
from ..canvas_widgets import Waveform, LiveEqualizer
from src.core import connectar_bitalino, ConnectionWatchdog

class ConnectionFrame(Card):
    """Barra de conexão: logo, endereço MAC, canal e o estado de conexão do Bitalino.

    Dois estados visuais mutuamente exclusivos, alternados por show/hide:
    - desconectado: botão de acento "Conectar" (MAC/canal habilitados);
    - conectado: pill "● Conectado" + equalizador animado + botão "Desconectar".

    Toda a lógica de conexão (worker LSL, watchdog, teardown, perda de conexão) é
    preservada da versão anterior.
    """

    def __init__(self, master, ctx):
        super().__init__(master)
        self.ctx = ctx

        main_connect_frame = ctk.CTkFrame(self, fg_color=TRANSPARENTE)
        main_connect_frame.pack(fill="x", padx=20, pady=16)

        # ----- logo (waveform + wordmark) -----
        logo_img_frame = ctk.CTkFrame(main_connect_frame, fg_color=TRANSPARENTE)
        logo_img_frame.pack(side="left")

        wave_box_img = ctk.CTkFrame(logo_img_frame, fg_color=ACCENT_TINT, corner_radius=11)
        wave_box_img.pack(side="left")
        Waveform(wave_box_img, [8, 16, 23, 12, 19], ACCENT, ACCENT_TINT,
                 bar_w=4, gap=3, height=24).pack(padx=10, pady=8)
        
        logo_txt_frame = ctk.CTkFrame(logo_img_frame, fg_color=TRANSPARENTE)
        logo_txt_frame.pack(side="left", padx=(12, 0))

        ctk.CTkLabel(logo_txt_frame, text="ComPasso", text_color=TEXT,
                     font=ctk.CTkFont(DISPLAY_FAMILY, FONT_3XL, weight="bold")).pack(anchor="w")

        ctk.CTkLabel(logo_txt_frame, text="MÚSICA & FISIOLOGIA", text_color=FAINT,
                     font=ctk.CTkFont(MONO_FAMILY, FONT_2XS)).pack(anchor="w")

        # divisor
        ctk.CTkFrame(main_connect_frame, fg_color=BORDER, width=5, height=42).pack(side="left", padx=22)

        # ----- MAC -----
        macaddr_frame = ctk.CTkFrame(main_connect_frame, fg_color=TRANSPARENTE)
        macaddr_frame.pack(side="left")

        caption(macaddr_frame, "ENDEREÇO MAC").pack(anchor="w", pady=(0, 5))

        self.mac_addr_var = ctk.StringVar(value="")
        self.mac_entry = ctk.CTkEntry(macaddr_frame, width=210, height=INPUT_H, corner_radius=CORNER_SM,
                                      fg_color=INPUT_BG, border_color=BORDER, text_color=TEXT,
                                      placeholder_text="XX:XX:XX:XX:XX:XX",
                                      textvariable=self.mac_addr_var,
                                      font=ctk.CTkFont(MONO_FAMILY, FONT_MD))
        self.mac_entry.pack()

        # ----- Canal -----
        channel_frame = ctk.CTkFrame(main_connect_frame, fg_color=TRANSPARENTE)
        channel_frame.pack(side="left", padx=(18, 0))

        caption(channel_frame, "CANAL").pack(anchor="w", pady=(0, 5))

        self.canal_var = ctk.StringVar(value="A1")

        self.canal_optionmenu = ctk.CTkOptionMenu(
            channel_frame, width=78, height=INPUT_H, corner_radius=CORNER_SM,
            values=[f"A{i}" for i in range(1, 7)], variable=self.canal_var,
            command=self._on_channel_change,
            fg_color=INPUT_BG, button_color=INPUT_BG, button_hover_color=BORDER,
            text_color=TEXT, dropdown_fg_color=BAR_BG, dropdown_text_color=TEXT,
            dropdown_hover_color=ACCENT_TINT, font=ctk.CTkFont(MONO_FAMILY, FONT_MD))
        
        self.canal_optionmenu.pack()

        # espaçador
        ctk.CTkFrame(main_connect_frame, fg_color=TRANSPARENTE, height=1).pack(side="left", expand=True, fill="x")

        # ----- slot direito: estados de conexão (Conectar | pill + Desconectar) -----
        self._right_conn_frame = ctk.CTkFrame(main_connect_frame, fg_color=TRANSPARENTE)
        self._right_conn_frame.pack(side="left")

        # estado desconectado
        self.connect_button = styled_button(self._right_conn_frame, text="Conectar", width=130, height=BTN_H,
                                             command=lambda: self.conect_bitalino(self.mac_addr_var.get()))

        # estado conectado (pill + equalizer + desconectar), montado sob demanda
        self.connected_box = ctk.CTkFrame(self._right_conn_frame, fg_color=TRANSPARENTE)
        self._equalizer = None

        self._show_disconnected()

    # ------------------------------------------------------------------ #
    def _show_disconnected(self):
        self.connected_box.pack_forget()
        if self._equalizer is not None:
            self._equalizer.destroy()
            self._equalizer = None
        for child in list(self.connected_box.winfo_children()):
            child.destroy()
        self.connect_button.configure(state="normal")
        self.connect_button.pack(side="left")

    def _show_connected(self):
        self.connect_button.pack_forget()

        pill = ctk.CTkFrame(self.connected_box, fg_color=ACCENT_TINT, corner_radius=CORNER_PILL,
                            border_width=1, border_color=ACCENT_BORDER)
        pill.pack(side="left", padx=(0, 10))
        inner = ctk.CTkFrame(pill, fg_color=TRANSPARENTE)
        inner.pack(padx=14, pady=7)
        ctk.CTkLabel(inner, text="●", text_color=SUCCESS,
                     font=ctk.CTkFont(DISPLAY_FAMILY, FONT_XS)).pack(side="left", padx=(0, 7))
        ctk.CTkLabel(inner, text="Conectado", text_color=ACCENT,
                     font=ctk.CTkFont(DISPLAY_FAMILY, FONT_MD, weight="bold")).pack(side="left")
        self._equalizer = LiveEqualizer(inner, ACCENT, ACCENT_TINT)
        self._equalizer.pack(side="left", padx=(8, 0))

        ghost = ghost_button(self.connected_box, "Desconectar", command=self.disconnect_bitalino)
        ghost.configure(width=110, height=BTN_H)
        ghost.pack(side="left")

        self.connected_box.pack(side="left")

    # ------------------------------------------------------------------ #
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
        self.connect_button.configure(state="disabled")
        self.ctx.run_async(lambda: self._connect_bitalino_worker(self.mac_addr),
                           on_done=self._handle_connection_result)

    def _connect_bitalino_worker(self, mac_addr: str):
        """Executa a conexão LSL (bloqueante) fora da thread da GUI. Retorna o inlet ou erro (str)."""
        gui_logger.logger.info(f"Conectando ao Bitalino com MAC: {mac_addr}")
        return connectar_bitalino(mac_addr=mac_addr)

    def _handle_connection_result(self, bitalino):
        """Trata o resultado da conexão: `str`/`Exception` é erro; caso contrário é o inlet."""
        if isinstance(bitalino, (str, Exception)):
            self.connect_button.configure(state="normal")
            msg = bitalino if isinstance(bitalino, str) else f"Erro inesperado ao conectar: {bitalino}"
            show_message("Erro na conexão", msg, icon="warning")
        else:
            self.ctx.bitalino = bitalino
            self.ctx.mac_addr = self.mac_addr
            self.ctx.status_text.set("Bitalino conectado")
            self.mac_entry.configure(state="disabled")
            self.canal_optionmenu.configure(state="disabled")
            self._show_connected()

            # inicia o watchdog de conexão (detecta perda de sinal por >= 15 s)
            self.ctx.handle_connection_lost = self._handle_connection_lost
            self.ctx.watchdog = ConnectionWatchdog(self.ctx)
            self.ctx.watchdog.start()

            self.ctx.notify_stepper()

    def disconnect_bitalino(self):
        """Encerra manualmente a conexão LSL com o Bitalino e restaura a UI de conexão.

        Bloqueia (com aviso) se houver um experimento em andamento — o usuário deve parar
        o experimento antes de desconectar."""
        runner = self.ctx.runner
        if runner is not None and runner.is_running():
            show_message("Atenção", "Pare o experimento antes de desconectar o Bitalino.", icon="warning")
            return

        self._teardown_connection()
        gui_logger.logger.info("Bitalino desconectado manualmente pelo usuário.")
        self.ctx.status_text.set("Bitalino desconectado")

    def _teardown_connection(self):
        """Encerra o watchdog e o stream, limpa o estado de conexão e restaura a UI.

        Reutilizado pela desconexão manual e pela perda de conexão detectada pelo watchdog."""
        watchdog = self.ctx.watchdog
        if watchdog is not None:
            try:
                watchdog.stop()
            except Exception as e:
                gui_logger.logger.warning(f"Falha ao encerrar o watchdog: {e}")
            self.ctx.watchdog = None

        inlet = self.ctx.bitalino
        if inlet is not None:
            try:
                inlet.close_stream()
            except Exception as e:
                gui_logger.logger.warning(f"Falha ao encerrar o stream do Bitalino: {e}")
        self.ctx.bitalino = None
        self.ctx.mac_addr = None

        # restaura o campo de MAC/canal e o botão de conexão
        self.mac_entry.configure(state="normal")
        self.canal_optionmenu.configure(state="normal")
        self._show_disconnected()

        self.ctx.notify_stepper()

    def _handle_connection_lost(self):
        """Tratamento da perda de conexão sinalizada pelo watchdog (na thread da GUI).

        Para o experimento em andamento (mesma rotina do botão "Parar", finalizando o
        arquivo com a marca 'stop'), reseta o estado de conexão e avisa o usuário."""
        runner = self.ctx.runner
        if runner is not None and runner.is_running():
            runner.stop()
        self._teardown_connection()
        self.ctx.status_text.set("Conexão com BITalino perdida")
        show_message("Atenção", "Conexão com BITalino perdida. Verifique o sensor.", icon="warning")