import CTkMessagebox

from . import gui_logger

def set_window_grid(master):
        """
        Configura o grid da janela principal, atribuindo peso 1 para a linha 0 e a coluna 0, permitindo que os widgets se expandam para preencher a janela.
        
        :param master: A janela principal a ser configurada.
        :param logger: Logger para registrar informações sobre a configuração do grid.
        
        """
        master.grid_columnconfigure(0, weight=1)
        master.grid_rowconfigure(0, weight=1)

        gui_logger.logger.info("Grid da janela principal configurado com sucesso: linha 0 e coluna 0 com peso 1.")

def set_window_configs(master, width:int=400, height:int=200, width_multip=None, height_multip=None):
        """
        Configura as dimensões e a posição da janela na tela do usuário, centralizando-a. As dimensões podem ser passadas diretamente ou como multiplicadores da resolução do usuário.

        :param master: A janela a ser configurada.
        :param width: Largura da janela em pixels (opcional se width_multip for fornecido).
        :param height: Altura da janela em pixels (opcional se height_multip for fornecido).
        :param width_multip: Multiplicador da largura da janela em relação à largura da tela.
        :param height_multip: Multiplicador da altura da janela em relação à altura da tela.
        :param logger: Logger para registrar informações sobre a configuração da janela.

        """
        master.user_screen_height = master.winfo_screenheight()
        master.user_screen_width = master.winfo_screenwidth()
        
        if master.user_screen_height < 1200:
            master.app_width = 1280
            master.app_heigth = 768
        else:
            master.app_width = int(master.user_screen_width*width_multip) if width_multip is not None else width
            master.app_heigth = int(master.user_screen_height*height_multip) if height_multip is not None else height
        
        master.geometry_str = f"{master.app_width}x{master.app_heigth}+{(master.user_screen_width//2)-(master.app_width//2)}+{(master.user_screen_height//2)-(master.app_heigth//2)}"             
        master.geometry(master.geometry_str)

        gui_logger.logger.info(msg=f"""Janela configurada com sucesso!
                                      User screen = {master.user_screen_width}x{master.user_screen_height}.
                                      App geometry = {master.app_width}x{master.app_heigth}.
                                      Geometry passed window = {master.geometry_str}""")

def set_grids(ctk_object, rows_conf: dict[int,list[int]], column_conf: dict[int,list[int]], grid_row=0, grid_column=0, columnspan=1, padx=10, pady=10, sticky="nsew"):
    """
    Configura o grid de um objeto do CustomTkinter, atribuindo pesos às linhas e colunas, além de posicionar o objeto no grid.

    :param ctk_object: O objeto do CustomTkinter a ser configurado.
    :param rows_conf: Dicionário onde as chaves são os pesos e os valores são listas de índices das linhas a receberem esse peso.
    :param column_conf: Dicionário onde as chaves são os pesos e os valores são listas de índices das colunas a receberem esse peso.
    :param grid_row: Índice da linha onde o objeto será posicionado.
    :param grid_column: Índice da coluna onde o objeto será posicionado.
    :param columnspan: Número de colunas que o objeto irá ocupar.
    :param padx: Espaçamento horizontal ao redor do objeto.
    :param pady: Espaçamento vertical ao redor do objeto.
    :param sticky: Direção para a qual o objeto se expandirá.

    """
    ctk_object.grid(row=grid_row, column=grid_column, columnspan=columnspan, padx=padx, pady=pady, sticky=sticky)
    gui_logger.logger.info(f"Objeto {ctk_object} posicionado no grid (row={grid_row}, column={grid_column}, columnspan={columnspan}, padx={padx}, pady={pady}, sticky={sticky}).")

    if rows_conf:
        for weight, row in rows_conf.items():
            for row in row:
                ctk_object.grid_rowconfigure(row, weight=weight)
    gui_logger.logger.info(f"Configurações de linhas aplicadas: {rows_conf}.")
    
    if column_conf:
        for weight, column in column_conf.items():
            for column in column:
                ctk_object.grid_columnconfigure(column, weight=weight)
    gui_logger.logger.info(f"Configurações de colunas aplicadas: {column_conf}.")

"""def _msgbox(self, title: str, message: str, icon: str = "cancel"):
    Exibe uma CTkMessagebox padronizada. Deve ser chamada na thread da GUI
    (use `self.ctx.post(...)` quando vier de uma thread de trabalho).
    CTkMessagebox(title=title, message=message, icon=icon, option_1="OK",
                    fg_color=ROSA, bg_color=AZUL, text_color=CINZA, button_color=AZUL_CLARO, button_hover_color=AMARELO,
                    font=BASE_FONT_MIN, border_color=AZUL, border_width=BORDER_WIDTH, title_color=CINZA,
                    button_text_color=CINZA, corner_radius=CORNER, sound=True,
                    width=500, height=300)"""