# Intencionalmente sem re-exports: importar `src.gui.main` aqui forçaria toda a stack
# de GUI (customtkinter, pywinstyles, CTkMenuBar) a carregar mesmo para quem só precisa
# de `src.core`/`src.utils` (ex.: testes de lógica pura). Importe direto do submódulo
# desejado, ex.: `from src.gui import ComPasso`, `from src.core import connectar_bitalino`.
