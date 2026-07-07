# Intencionalmente sem re-exports: importar `compasso.gui.app` aqui forçaria toda a stack
# de GUI (customtkinter, pywinstyles, CTkMenuBar) a carregar mesmo para quem só precisa
# de `compasso.core`/`compasso.utils` (ex.: testes de lógica pura). Importe direto do
# submódulo desejado, ex.: `from compasso.gui import ComPasso`,
# `from compasso.core import connectar_bitalino`.
