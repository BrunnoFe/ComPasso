# -*- coding: utf-8 -*-
"""
compasso_splash.py
------------------
Tela de carregamento (3p) do ComPasso, pronta para incorporar no projeto.

Características pedidas:
  * Traço "Signal Line" desenhado de forma SUAVE, totalmente arredondado,
    sem cantos quebrados (usa spline + polilinha contínua + pontas redondas).
  * Blend teal->iris (compatível com os temas; troque via `blend`/`color`).
  * Frame arredondado sem barra de título (customtkinter + overrideredirect).
  * Tamanho 600x400 (reconfigurável via `size`).
  * "Carregando" com reticências dinâmicas: ".", "..", "...", repetindo.
  * Aparece por 3 segundos (reconfigurável via `duration_ms`) e então
    fecha, chamando `on_done` (ideal para abrir a janela principal).

Uso no projeto:
    from compasso_splash import show_splash
    show_splash(palette=C, display_family=DISPLAY_FAMILY,
                mono_family=MONO_FAMILY, on_done=abrir_app)

Demo:
    python compasso_splash.py
"""

import tkinter as tk

import customtkinter as ctk

from . import gui_logger

# ---------------------------------------------------------------------------
# Cores
# ---------------------------------------------------------------------------
# Par do blend por acento (esquerda -> direita). Encaixa com os PALETTE_* de theme.py.
THEME_BLENDS = {
    "#2DD4BF": ("#2DD4BF", "#7C74FF"),   # teal
    "#7C74FF": ("#7C74FF", "#2DD4BF"),   # iris
    "#F5A524": ("#F5A524", "#FB7185"),   # amber
}

# Cor-chave usada como `-transparentcolor` (Windows): pixels dessa cor viram transparentes,
# revelando os cantos arredondados do card. Precisa ser um hex VÁLIDO de 6 dígitos e escuro
# (minimiza a franja nos cantos quando a transparência não se aplica — macOS/Linux).
_SPLASH_CHROMA = "#010203"

_DEFAULT_PALETTE = {
    "accent": "#2DD4BF",
    "text": "#E6EDF3",
    "faint": "#6E7681",
    "win_bg": "#0E1116",
    "bar_bg": "#161B22",
    "win_bg_transparent": _SPLASH_CHROMA,
}


def _hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _rgb_to_hex(c):
    return "#%02X%02X%02X" % tuple(max(0, min(255, int(round(v)))) for v in c)


def _lerp_hex(a, b, t):
    ca, cb = _hex_to_rgb(a), _hex_to_rgb(b)
    return _rgb_to_hex([ca[i] + (cb[i] - ca[i]) * t for i in range(3)])


def _blend_for(palette):
    return THEME_BLENDS.get(palette.get("accent", "#2DD4BF").upper(),
                            THEME_BLENDS.get(palette.get("accent", "#2DD4BF"),
                                             ("#2DD4BF", "#7C74FF")))


# ---------------------------------------------------------------------------
# Forma do traço (idêntica ao 3p / SVG): 2 ondas suaves -> espículas de EEG.
# Espaço 0..64; amostrada densamente para o spline ficar limpo.
# ---------------------------------------------------------------------------
def _cubic(p0, p1, p2, p3, t):
    u = 1 - t
    return (u*u*u*p0[0] + 3*u*u*t*p1[0] + 3*u*t*t*p2[0] + t*t*t*p3[0],
            u*u*u*p0[1] + 3*u*u*t*p1[1] + 3*u*t*t*p2[1] + t*t*t*p3[1])


def _sample_shape(steps_bezier=40, steps_line=14):
    pts = []
    beziers = [
        [(6, 34), (11, 22), (16, 22), (21, 34)],
        [(21, 34), (26, 46), (30, 46), (34, 34)],
    ]
    for b in beziers:
        for i in range(steps_bezier + 1):
            pts.append(_cubic(*b, i / steps_bezier))
    line = [(34, 34), (38, 10), (42, 54), (46, 16),
            (50, 44), (54, 26), (58, 34)]
    for s in range(len(line) - 1):
        a, c = line[s], line[s + 1]
        for i in range(1, steps_line + 1):
            t = i / steps_line
            pts.append((a[0] + (c[0]-a[0])*t, a[1] + (c[1]-a[1])*t))
    return pts


_SHAPE = _sample_shape()
_SX0, _SX1 = 6.0, 58.0
_SY0, _SY1 = 10.0, 54.0


# ---------------------------------------------------------------------------
# Canvas do traço — desenho SUAVE (spline) e contínuo (sem cantos quebrados)
# ---------------------------------------------------------------------------
class _SignalLine(tk.Canvas):
    def __init__(self, master, width, height, bg, color, blend,
                 width_stroke, pad, draw_ms=1600, hold_ms=600, **kw):
        super().__init__(master, width=width, height=height, bg=bg,
                         highlightthickness=0, bd=0, **kw)
        self._width_w, self._h_height = width, height
        self.color, self.blend = color, blend
        self.width_stroke, self.pad = width_stroke, pad
        self.draw_ms, self.hold_ms = draw_ms, hold_ms
        self._pts = self._scaled()
        self._items = []
        self._after = None
        self._animate()

    def _scaled(self):
        sx = (self._width_w - 2*self.pad) / (_SX1 - _SX0)
        sy = (self._h_height - 2*self.pad) / (_SY1 - _SY0)
        return [(self.pad + (x-_SX0)*sx, self.pad + (y-_SY0)*sy)
                for (x, y) in _SHAPE]

    def _draw_upto(self, k):
        for it in self._items:
            self.delete(it)
        self._items = []
        k = min(k, len(self._pts))
        if k < 2:
            return
        pts = self._pts[:k]

        # UMA polilinha contínua, spline (smooth) + pontas/juntas redondas.
        # Nada de segmentos soltos -> sem "contas" nem cantos quebrados.
        def line(points, col):
            flat = [c for p in points for c in p]
            self._items.append(self.create_line(
                *flat, fill=col, width=self.width_stroke,
                capstyle=tk.ROUND, joinstyle=tk.ROUND,
                smooth=True, splinesteps=36))

        if not self.blend:
            line(pts, self.color)
            return

        # Blend contínuo: caudas empilhadas (esq->dir), cada uma spline.
        full = len(self._pts) - 1
        step = 4
        for i in range(0, k - 1, step):
            t = i / max(1, full - 1)
            line(pts[i:], _lerp_hex(self.blend[0], self.blend[1], t))

    def _animate(self):
        total = len(self._pts)
        step_ms = max(8, int(self.draw_ms / total))

        def grow(k):
            self._draw_upto(k)
            if k < total:
                self._after = self.after(step_ms, grow, k + 2)
            else:
                self._after = self.after(self.hold_ms, grow, 2)
        grow(2)

    def stop(self):
        if self._after:
            self.after_cancel(self._after)
            self._after = None

    def destroy(self):
        self.stop()
        super().destroy()


# ---------------------------------------------------------------------------
# show_splash — a tela 3p
# ---------------------------------------------------------------------------
def show_splash(master=None, palette=None, display_family="Segoe UI",
                mono_family="Consolas", size=(600, 400), duration_ms=3000,
                on_done=None, use_blend=True, corner_radius=22):
    """
    Mostra a tela de carregamento 3p e fecha após `duration_ms`.

        master      : janela pai (ou None p/ criar a própria raiz).
        palette     : seu dict C (usa accent / text / faint / win_bg).
        size        : (largura, altura). Padrão 600x400 — reconfigurável.
        duration_ms : tempo visível antes de fechar (padrão 3000 = 3 s).
        on_done     : callback chamado ao fechar (ex.: abrir o app).
        use_blend   : True = degradê teal->iris; False = cor sólida (accent).
    """
    if ctk is None:
        raise RuntimeError("customtkinter é necessário para show_splash")

    C = palette or _DEFAULT_PALETTE
    ctk.set_appearance_mode("dark")
    w, h = size
    blend = _blend_for(C) if use_blend else None

    owns_root = master is None
    win = ctk.CTk() if owns_root else ctk.CTkToplevel(master)
    win.overrideredirect(True)                      # sem barra de título
    win.configure(fg_color=C["win_bg_transparent"])

    # centraliza
    win.update_idletasks()
    sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
    win.geometry("%dx%d+%d+%d" % (w, h, (sw - w)//2, (sh - h)//2))
    try:
        win.wm_attributes("-transparentcolor", C["win_bg_transparent"])
    except Exception as e:
        gui_logger.logger.warning(f"Splash: transparência indisponível neste SO: {e}")

    # frame arredondado
    card = ctk.CTkFrame(win, fg_color=C["win_bg"], corner_radius=corner_radius,
                        border_width=1, border_color=C["bar_bg"])
    card.pack(fill="both", expand=True, padx=2, pady=2)

    inner = ctk.CTkFrame(card, fg_color="transparent")
    inner.place(relx=0.5, rely=0.5, anchor="center")

    line_w = int(min(w, h) * 0.62)
    line_h = int(line_w * 0.6)
    signal = _SignalLine(inner, width=line_w, height=line_h,
                         bg=C["win_bg"], color=C["accent"], blend=blend,
                         width_stroke=max(4, line_w // 34), pad=10,
                         draw_ms=1700, hold_ms=500)
    signal.pack()

    ctk.CTkLabel(inner, text="ComPasso", text_color=C["text"],
                 font=ctk.CTkFont(display_family, max(22, w // 22),
                                  weight="bold")).pack(pady=(18, 2))

    loading = ctk.CTkLabel(inner, text="Carregando", text_color=C["faint"],
                           font=ctk.CTkFont(mono_family, max(12, w // 42)))
    loading.pack()

    # "..." dinâmico: ".", "..", "..." repetindo
    _dots = {"n": 0}

    def tick():
        _dots["n"] = (_dots["n"] % 3) + 1
        loading.configure(text="CARREGANDO " + "." * _dots["n"])
        loading._job = win.after(420, tick)
    tick()

    def close():
        # Cancela a animação da linha e o "Carregando..." pendentes ANTES de destruir a
        # janela, senão um `after` órfão dispararia sobre widgets já destruídos (TclError).
        try:
            signal.stop()
        except Exception:
            pass
        job = getattr(loading, "_job", None)
        if job is not None:
            try:
                win.after_cancel(job)
            except Exception:
                pass
        if on_done:
            on_done()
        win.destroy()

    win.after(duration_ms, close)

    if owns_root:
        win.mainloop()
    return win


# ---------------------------------------------------------------------------
# Integração com o app — usa a paleta/fontes do tema ativo (theme.py)
# ---------------------------------------------------------------------------
def run_splash(master, on_done=None, duration_ms=3000):
    """Exibe a splash com as cores e fontes do tema ATIVO do ComPasso.

    Monta o dict de paleta esperado por `show_splash` a partir das constantes de
    `theme.py` (única fonte de verdade das cores), garantindo que a tela de carregamento
    combine com a preferência de tema persistida (Teal/Iris/Amber).

    :param master: janela pai (a janela principal, tipicamente oculta com `withdraw`).
    :param on_done: callback chamado quando a splash fecha (ex.: revelar a janela principal).
    :param duration_ms: tempo visível antes de fechar (ms).
    :return: a `CTkToplevel` da splash.
    """
    from .theme import WIN_BG, BAR_BG, ACCENT, TEXT, FAINT, DISPLAY_FAMILY, MONO_FAMILY

    palette = {
        "accent": ACCENT,
        "text": TEXT,
        "faint": FAINT,
        "win_bg": WIN_BG,
        "bar_bg": BAR_BG,
        "win_bg_transparent": _SPLASH_CHROMA,
    }
    return show_splash(master=master, palette=palette,
                       display_family=DISPLAY_FAMILY, mono_family=MONO_FAMILY,
                       duration_ms=duration_ms, on_done=on_done)


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    C = {
        "accent": "#2DD4BF", "text": "#E6EDF3", "faint": "#6E7681",
        "win_bg": "#0E1116", "bar_bg": "#161B22", "win_bg_transparent": "#244058"
    }
    show_splash(palette=C, duration_ms=3500,
                on_done=lambda: print("splash fechada -> abrir app aqui"))
