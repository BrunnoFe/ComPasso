import customtkinter as ctk

from . import gui_logger
from . import set_window_grid, set_window_configs, set_grids
from .context import AppContext
from .assets import AppImages
from .theme import AZUL, TRANSPARENTE, WIN_MIN_WIDTH, WIN_MIN_HEIGHT, BORDER_WIDTH, CORNER
from .frames import UpFrame, MidFrame, DownFrame

ctk.set_appearance_mode("system")


class Compasso(ctk.CTk):
    """Janela raiz: cria o `AppContext` e monta o `MainFrame`."""

    def __init__(self, nome="Compasso"):
        super().__init__(fg_color=AZUL)
        self.title(nome)
        self.resizable(False, False)
        self.minsize(WIN_MIN_WIDTH, WIN_MIN_HEIGHT)
        set_window_configs(self, width_multip=0.5, height_multip=0.5)
        set_window_grid(self)

        self.ctx = AppContext(self)
        self.ctx.images = AppImages()   # carregado após o root existir
        self.main_frame = MainFrame(self, self.ctx)


class MainFrame(ctk.CTkFrame):
    """Contêiner dos três painéis principais (superior, central e inferior)."""

    def __init__(self, master, ctx):
        super().__init__(master, corner_radius=CORNER, border_width=BORDER_WIDTH, border_color=AZUL, bg_color=TRANSPARENTE, fg_color=TRANSPARENTE)
        set_grids(self, rows_conf={1: [0, 2], 4: [1]}, column_conf={1: [0]})
        gui_logger.logger.info("MainFrame iniciado.")

        self.ctx = ctx

        self.up_frame = UpFrame(self, ctx)
        self.mid_frame = MidFrame(self, ctx)
        self.down_frame = DownFrame(self, ctx)

        self.after(100, self.mid_frame.upright_mid_frame.check_music_file_infos)


if __name__ == "__main__":
    app = Compasso()
    app.mainloop()
