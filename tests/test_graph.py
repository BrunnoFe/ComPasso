import math
import tkinter as tk

# Intervalo (ms) entre quadros do redesenho (~25 fps por padrão).
_INTERVALO_QUADRO_MS = 30

from src.gui.frames.signal_plot import GraficoSinal

# ---------------------------------------------------------------------------
# Demo ao vivo
# ---------------------------------------------------------------------------
def _demo():
    paleta = {
        "win_bg": "#0E1116", "bar_bg": "#161B22", "footer_bg": "#12161C",
        "border": "#21262d", "border_win": "#262c36", "input_bg": "#0E1116",
        "text": "#E6EDF3", "muted": "#8B949E", "faint": "#6E7681",
        "faint2": "#4B525C", "accent": "#2DD4BF", "accent_ink": "#04120F",
        "accent_tint": "#0C2B28", "accent_border": "#14463F",
        "success": "#34D399", "danger": "#F87171",
    }
    cores = paleta

    raiz = tk.Tk()
    raiz.title("ComPasso — gráfico do sinal (demo ao vivo)")
    raiz.configure(bg=cores["win_bg"])
    raiz.geometry("1180x420")

    # painel do gráfico
    painel = tk.Frame(raiz, bg=cores["bar_bg"], highlightthickness=1,
                      highlightbackground=cores["border"])
    painel.pack(fill="both", expand=True, padx=18, pady=6)
    cabecalho = tk.Frame(painel, bg=cores["bar_bg"])
    cabecalho.pack(fill="x", padx=14, pady=(10, 0))
    tk.Label(cabecalho, text="SINAL DO BITALINO · CANAL A1", bg=cores["bar_bg"],
             fg=cores["faint"], font=("Segoe UI", 9)).pack(side="left")
    rotulo_valor = tk.Label(cabecalho, text="—", bg=cores["bar_bg"], fg=cores["accent"],
                            font=("Consolas", 12, "bold"))
    rotulo_valor.pack(side="right")

    grafico = GraficoSinal(painel, paleta=cores,
                           familia_display="Segoe UI", familia_mono="Consolas")
    grafico.pack(fill="both", expand=True, padx=10, pady=10)

    # rodapé (mock)
    rodape = tk.Frame(raiz, bg=cores["footer_bg"])
    rodape.pack(fill="x")
    status = tk.Label(rodape, text="● Conectado · pronto", bg=cores["footer_bg"],
                      fg=cores["success"], font=("Segoe UI", 10))
    status.pack(side="left", padx=18, pady=10)

    # --- simulação de uma gravação (tempo acelerado) ---
    estado = {"t": 0.0, "rodando": False}
    DURACAO = 60.0           # música de 60 s
    ACELERACAO = 6.0         # 6x mais rápido que o real
    DT = 1.0 / 100.0         # 100 Hz

    def sinal(t):
        r = (math.sin(t * 2.1) * 6 + math.sin(t * 5.7) * 3.5
             + math.sin(t * 11.3) * 2.0 + math.sin(t * 0.7) * 4
             + math.sin(t * 53.1) * 1.2)
        r += 6 + math.sin(t * 0.25) * 3     # deriva lenta -> Y cresce aos poucos
        return r

    def avancar():
        if not estado["rodando"]:
            return
        n = max(1, int(ACELERACAO * (_INTERVALO_QUADRO_MS / 1000.0) / DT))
        for _ in range(n):
            if estado["t"] >= DURACAO:
                break
            estado["t"] += DT
            grafico.adicionar_amostra(estado["t"], sinal(estado["t"]))
        valor_atual = grafico.valor_atual
        if valor_atual is not None:
            rotulo_valor.config(text="%+.1f µV" % valor_atual)
        if estado["t"] >= DURACAO:
            estado["rodando"] = False
            grafico.finalizar()
            status.config(text="● Registro concluído", fg=cores["accent"])
            raiz.after(2500, iniciar_ciclo)   # reinicia o ciclo
            return
        raiz.after(_INTERVALO_QUADRO_MS, avancar)

    def iniciar_ciclo():
        estado["t"] = 0.0
        estado["rodando"] = True
        grafico.iniciar(DURACAO)
        status.config(text="● Gravando…", fg=cores["danger"])
        rotulo_valor.config(text="0.0 µV")
        avancar()

    # começa ocioso, depois grava
    grafico.voltar_ao_ocioso()
    raiz.after(1200, iniciar_ciclo)
    raiz.mainloop()


if __name__ == "__main__":
    _demo()
