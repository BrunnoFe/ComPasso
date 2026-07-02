"""Widgets vetoriais em ``tkinter.Canvas`` usados pelo redesign.

- ``Waveform``: barras estáticas da logo (onda sonora).
- ``LiveEqualizer``: barrinhas animadas do indicador "Conectado".

São ``Canvas`` do tkinter puro (não CustomTkinter) porque desenham formas simples;
recebem as cores por parâmetro para casar com o fundo do widget-pai.
"""

import random
import tkinter as tk

# Intervalo (ms) entre quadros da animação do equalizador "Conectado".
_EQ_TICK_MS = 160


class Waveform(tk.Canvas):
    """Barras estáticas da logo (onda sonora)."""

    def __init__(self, master, heights, color, bg, bar_w=3, gap=2, height=30):
        w = len(heights) * (bar_w + gap)
        super().__init__(master, width=w, height=height, bg=bg,
                         highlightthickness=0, bd=0)
        base = height
        for i, h in enumerate(heights):
            x = i * (bar_w + gap)
            self.create_rectangle(x, base - h, x + bar_w, base,
                                  fill=color, outline="", width=0)


class LiveEqualizer(tk.Canvas):
    """Barrinhas animadas do indicador 'Conectado'.

    Anima sozinha via ``after`` enquanto o widget existir; ``destroy()`` (chamado quando
    a UI de conexão é desfeita) encerra o ciclo naturalmente.
    """

    def __init__(self, master, color, bg, bars=4, bar_w=3, gap=2, height=13):
        w = bars * (bar_w + gap)
        super().__init__(master, width=w, height=height, bg=bg,
                         highlightthickness=0, bd=0)
        self.color, self.bars = color, bars
        self.bar_w, self.gap, self.h = bar_w, gap, height
        self._rects = []
        for i in range(bars):
            x = i * (bar_w + gap)
            self._rects.append(self.create_rectangle(x, 0, x + bar_w, height,
                                                     fill=color, outline=""))
        self._tick()

    def _tick(self):
        # se o canvas foi destruído, interrompe o ciclo sem erro
        try:
            for i, r in enumerate(self._rects):
                hh = random.randint(int(self.h * 0.3), self.h)
                x = i * (self.bar_w + self.gap)
                self.coords(r, x, self.h - hh, x + self.bar_w, self.h)
            self.after(_EQ_TICK_MS, self._tick)
        except tk.TclError:
            return
