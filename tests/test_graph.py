import math
import tkinter as tk

# Intervalo (ms) entre quadros do redesenho (~25 fps por padrão).
_TICK_MS = 30

from src.gui.frames.signal_plot import SignalPlot

# ---------------------------------------------------------------------------
# Live demo
# ---------------------------------------------------------------------------
def _demo():
    palette = {
        "win_bg": "#0E1116", "bar_bg": "#161B22", "footer_bg": "#12161C",
        "border": "#21262d", "border_win": "#262c36", "input_bg": "#0E1116",
        "text": "#E6EDF3", "muted": "#8B949E", "faint": "#6E7681",
        "faint2": "#4B525C", "accent": "#2DD4BF", "accent_ink": "#04120F",
        "accent_tint": "#0C2B28", "accent_border": "#14463F",
        "success": "#34D399", "danger": "#F87171",
    }
    C = palette

    root = tk.Tk()
    root.title("ComPasso — gráfico do sinal (live demo)")
    root.configure(bg=C["win_bg"])
    root.geometry("1180x420")

    # painel do gráfico
    panel = tk.Frame(root, bg=C["bar_bg"], highlightthickness=1,
                     highlightbackground=C["border"])
    panel.pack(fill="both", expand=True, padx=18, pady=6)
    head = tk.Frame(panel, bg=C["bar_bg"])
    head.pack(fill="x", padx=14, pady=(10, 0))
    tk.Label(head, text="SINAL DO BITALINO · CANAL A1", bg=C["bar_bg"],
             fg=C["faint"], font=("Segoe UI", 9)).pack(side="left")
    val_lbl = tk.Label(head, text="—", bg=C["bar_bg"], fg=C["accent"],
                       font=("Consolas", 12, "bold"))
    val_lbl.pack(side="right")

    plot = SignalPlot(panel, palette=C, channel_label="A1",
                      display_family="Segoe UI", mono_family="Consolas")
    plot.pack(fill="both", expand=True, padx=10, pady=10)

    # rodapé (mock)
    foot = tk.Frame(root, bg=C["footer_bg"])
    foot.pack(fill="x")
    status = tk.Label(foot, text="● Conectado · pronto", bg=C["footer_bg"],
                      fg=C["success"], font=("Segoe UI", 10))
    status.pack(side="left", padx=18, pady=10)

    # --- simulação de uma gravação (tempo acelerado) ---
    state = {"t": 0.0, "running": False}
    DURATION = 60.0          # música de 60 s
    SPEED = 6.0              # 6x mais rápido que o real
    DT = 1.0 / 100.0         # 100 Hz

    def signal(t):
        r = (math.sin(t * 2.1) * 6 + math.sin(t * 5.7) * 3.5
             + math.sin(t * 11.3) * 2.0 + math.sin(t * 0.7) * 4
             + math.sin(t * 53.1) * 1.2)
        r += 6 + math.sin(t * 0.25) * 3     # deriva lenta -> Y cresce aos poucos
        return r

    def step():
        if not state["running"]:
            return
        # empurra ~ (SPEED/100 * refresh) amostras por quadro
        n = int(SPEED * DT * 100 * (_TICK_MS / 1000.0) / DT)
        n = max(1, int(SPEED * (_TICK_MS / 1000.0) / DT))
        for _ in range(n):
            if state["t"] >= DURATION:
                break
            state["t"] += DT
            plot.push(state["t"], signal(state["t"]))
        plot.set_playhead(state["t"])
        cv = plot.current_value
        if cv is not None:
            val_lbl.config(text="%+.1f µV" % cv)
        if state["t"] >= DURATION:
            state["running"] = False
            plot.end()
            status.config(text="● Registro concluído", fg=C["accent"])
            root.after(2500, start_cycle)   # reinicia o ciclo
            return
        root.after(_TICK_MS, step)

    def start_cycle():
        state["t"] = 0.0
        state["running"] = True
        plot.begin(DURATION)
        status.config(text="● Gravando…", fg=C["danger"])
        val_lbl.config(text="0.0 µV")
        step()

    # começa ocioso, depois grava
    plot.reset_idle()
    root.after(1200, start_cycle)
    root.mainloop()


if __name__ == "__main__":
    _demo()