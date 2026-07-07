from . import gui_logger

def set_window_configs(master, width:int=400, height:int=200, width_multip=None, height_multip=None):
        """
        Configura as dimensões e a posição da janela na tela do usuário, centralizando-a. As dimensões podem ser passadas diretamente ou como multiplicadores da resolução do usuário.

        :param master: A janela a ser configurada.
        :param width: Largura da janela em pixels (opcional se width_multip for fornecido).
        :param height: Altura da janela em pixels (opcional se height_multip for fornecido).
        :param width_multip: Multiplicador da largura da janela em relação à largura da tela.
        :param height_multip: Multiplicador da altura da janela em relação à altura da tela.

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