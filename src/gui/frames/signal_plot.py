# -*- coding: utf-8 -*-
"""
signal_plot.py
--------------
Gráfico do sinal do BITalino em tempo real (música inteira fixa no eixo X).

A linha se desenha progressivamente conforme os pontos são coletados; ao final
fica o registro inteiro da faixa. Segue o mesmo padrão do LiveEqualizer:
``tkinter.Canvas`` puro que recebe as cores do tema ativo por parâmetro e se
anima sozinho via ``after`` enquanto existir.

Eixos:
  * X (tempo): FIXO de 0s à duração total (janela = ``lead`` da contagem + duração
    da música, definida por quem chama ``begin``). Os RÓTULOS mostram ``t - lead``,
    então o eixo vai de ``-lead`` (ex.: -0:05) até a duração da música, com o
    ``0:00`` (início da música) DESTACADO por uma linha mais clara. Marcas com
    intervalo ADAPTATIVO ancoradas no 0. Cursor (playhead) vertical no tempo atual.
  * Y (sinal): plota o valor como chega (float, sem conversão). AUTO-ESCALA
    com limites "redondos" e ~10% de folga. Durante a gravação os limites só
    CRESCEM (nunca encolhem), então a linha nunca "pula" de escala. O zero
    aparece só se os dados cruzarem — o enquadramento segue a faixa dos dados.

Fluidez e formação contínua (linha + ponteiro sempre juntos):
  * Um único RELÓGIO DE EXIBIÇÃO (``_display_t``) rege ao mesmo tempo o ponteiro E
    o quanto da linha já foi revelado. Ele avança suave por quadro (~1 s/s) e fica
    ancorado à ponta dos dados (nunca a ultrapassa; nunca fica mais que ``_MAX_LAG``
    atrás). Como os dois usam o MESMO valor, o cursor cola na ponta da linha e ambos
    se formam continuamente, mesmo com as amostras LSL chegando em rajadas.
  * A linha é DECIMADA de forma INCREMENTAL (uma coluna de pixel por vez) e recebe
    uma MÉDIA MÓVEL leve + spline (``smooth=True``) só na exibição — o CSV/XLSX
    mantém o dado bruto. Custo por quadro ~O(largura), não O(total de pontos).
  * Os itens do canvas (grade, linha, playhead) são PERSISTENTES e atualizados
    via ``coords()``/``itemconfigure()`` a cada quadro; nada de ``delete('all')``
    por quadro (evita cintilação e o custo que crescia com a gravação). A grade só
    é reconstruída quando a escala/geometria muda.

Estados:
  * Ocioso: eixos discretos + "Aguardando gravação…".
  * Gravando: linha se formando + playhead + leitura do valor atual.
  * Concluído: registro inteiro visível (chame ``end()``).

Thread-safety:
  ``push()`` e ``set_playhead()`` são seguros para chamar da thread de
  aquisição (ex.: do LSLRecorder). Os pontos entram numa fila e são
  consumidos no próximo quadro, na thread da GUI.

Uso típico no app:
    plot = SignalPlot(parent, palette=C, channel_label="A1",
                      display_family=DISPLAY_FAMILY, mono_family=MONO_FAMILY)
    plot.pack(fill="both", expand=True)
    ...
    plot.begin(duration_s=lead + player.get_length())  # ao iniciar a faixa
    ...                                                 # a cada amostra:
    plot.push(t_segundos, valor_do_sinal)               #   (pode ser de outra thread)
    ...
    plot.end()                                           # fim da faixa
    plot.reset_idle()                                    # entre faixas / desconectar
"""

import math
import time
import bisect
import threading
from collections import deque

import tkinter as tk


# Intervalo (ms) entre quadros (~60 fps). Com atualização incremental + itens
# persistentes, este quadro é barato mesmo com muitos pontos acumulados.
_TICK_MS = 16

# Janela (em colunas de pixel) da média móvel leve aplicada só na EXIBIÇÃO da linha
# (o CSV/XLSX mantém o dado bruto). Suaviza o "serrilhado" sem achatar a forma.
_SMOOTH_WINDOW = 5

# Atraso máximo (s) do relógio de exibição em relação à ponta dos dados. Limita o
# tamanho do buffer que absorve as rajadas de amostras do LSL.
_MAX_LAG = 0.4

# Largura (px) de cada "tile" da linha do sinal. A linha é dividida em vários itens de
# canvas por faixa de x, de modo que mover o ponteiro só repinte o tile atual (custo por
# quadro constante, independente do tamanho da música). Ver _draw_tile/_update_tiles.
_TILE_PX = 200

# Eixo Y FIXO padrão (lo, hi, step) -> marcas -30, -15, 0, 15, 30 µV. Só reescala quando um
# pico ultrapassa a barreira em ~10% (ver _maybe_rescale_y); com Y fixo os tiles já
# percorridos ficam estáticos para sempre (o y de cada ponto não muda).
_Y_FIXED = (-30.0, 30.0, 15.0)

# Paleta de reserva (usada só se nenhuma for passada).
_DEFAULT_PALETTE = {
    "bar_bg": "#161B22", "border": "#21262d", "text": "#E6EDF3",
    "muted": "#8B949E", "faint": "#6E7681", "faint2": "#4B525C",
    "accent": "#2DD4BF", "success": "#34D399",
}


# ---------------------------------------------------------------------------
# Helpers de escala "redonda"
# ---------------------------------------------------------------------------
def _nice_step(rough):
    """Passo 'bonito' (1,2,5 x 10^k) >= rough."""
    if rough <= 0 or not math.isfinite(rough):
        return 1.0
    mag = 10 ** math.floor(math.log10(rough))
    for m in (1, 2, 5, 10):
        if m * mag >= rough:
            return m * mag
    return 10 * mag


def _nice_y_bounds(dmin, dmax, pad_frac=0.10, divisions=4):
    """Limites Y redondos com folga, a partir do min/max dos dados.

    :return: (lo, hi, step) já arredondados a múltiplos de um passo bonito.
    """
    if not math.isfinite(dmin) or not math.isfinite(dmax):
        return -1.0, 1.0, 0.5
    if dmax - dmin < 1e-9:
        dmin -= 1.0
        dmax += 1.0
    span = dmax - dmin
    pad = span * pad_frac
    lo, hi = dmin - pad, dmax + pad
    step = _nice_step((hi - lo) / divisions)
    lo = math.floor(lo / step) * step
    hi = math.ceil(hi / step) * step
    return lo, hi, step


# Intervalos permitidos para as marcas de tempo (segundos).
_TIME_STEPS = [1, 2, 5, 10, 15, 30, 60, 120, 300, 600]


def _nice_time_step(duration, target_ticks=7):
    """Escolhe um intervalo de marcas de tempo p/ ~target_ticks rótulos."""
    if duration <= 0:
        return 1
    rough = duration / target_ticks
    for s in _TIME_STEPS:
        if s >= rough:
            return s
    return _TIME_STEPS[-1]


def _fmt_signed_mmss(t):
    """mm:ss com sinal (ex.: -0:05 nos segundos finais da contagem; 0:00 no início da música)."""
    neg = t < -1e-9
    a = abs(int(round(t)))
    s = "%d:%02d" % (a // 60, a % 60)
    return ("-" + s) if neg else s


# ---------------------------------------------------------------------------
# Widget
# ---------------------------------------------------------------------------
class SignalPlot(tk.Canvas):
    """Gráfico do sinal em tempo real (playhead fluido, decimação incremental)."""

    # margens internas do desenho (px)
    PAD_L = 52     # espaço p/ rótulos do eixo Y
    PAD_R = 12
    PAD_T = 16
    PAD_B = 26     # espaço p/ rótulos do eixo X

    def __init__(self, master, palette=None, channel_label="A1",
                 display_family="Segoe UI", mono_family="Consolas",
                 unit="µV", idle_text="Aguardando gravação…", **kw):
        CORES = palette or _DEFAULT_PALETTE
        super().__init__(master, bg=CORES["bar_bg"], highlightthickness=0, bd=0, **kw)
        self.CORES = CORES
        self.channel_label = channel_label
        self.display_family = display_family
        self.mono_family = mono_family
        self.unit = unit
        self.idle_text = idle_text

        # estado dos dados
        self._buf = deque()             # fila (t, v) vinda de qualquer thread
        self._lock = threading.Lock()
        self._t = []                    # tempos acumulados (s)
        self._v = []                    # valores acumulados
        self._dmin = math.inf           # min/max monotônicos (só crescem)
        self._dmax = -math.inf
        self._duration = 0.0
        self._recording = False
        self._ended = False
        self._last_val = None

        # relógio de EXIBIÇÃO derivado dos próprios dados: avança suave por quadro e fica
        # ancorado à ponta dos dados (ver _advance_display_clock). O ponteiro e o corte da
        # linha usam o mesmo _display_t -> sempre sincronizados. _lead = segundos iniciais de
        # "lead" da contagem (rótulos do eixo = t - lead). Override manual opcional (demo).
        self._lead = 0.0
        self._display_t = 0.0
        self._last_frame_wall = None
        self._playhead_manual = None

        # estado de renderização incremental (buckets de decimação + ids dos itens)
        self._reset_render_state()

        self._after_id = None
        self.bind("<Configure>", lambda e: self._mark_full())
        self._tick()

    def _reset_render_state(self):
        """Zera a decimação incremental e os itens persistentes do canvas."""
        self._buckets = {}              # px_int -> [soma_v, contagem]
        self._bucket_order = []         # colunas na ordem de inserção (= ordenadas)
        self._ingest_from = 0           # nº de pontos de _t já decimados
        self._bucket_key = None         # (x0, x1, duração) — muda -> rebuild
        self._scale = None              # (lo, hi, step) desenhados
        self._geom = None               # (x0, y0, x1, y1) desenhados
        self._idle_drawn = None
        self._needs_full = True         # força um redesenho estrutural completo
        self._yscale = _Y_FIXED         # (lo, hi, step) do eixo Y (fixo; reescala é rara)
        self._tiles = {}                # índice do tile -> id do item de linha (persistente)
        self._active_tile = -1          # tile onde o corte (_display_t) está agora
        self._ph_ids = ()               # itens do playhead (linha, ponto, chip)
        self._last_line_px = -1         # última coluna de pixel em que a linha foi redesenhada
                                        # (os tiles só são reconstruídos quando o corte cruza um
                                        # pixel; o playhead atualiza todo quadro à parte)

    def _mark_full(self):
        self._needs_full = True

    # -- API pública (thread-safe) ---------------------------------------
    def begin(self, duration_s, lead_s=0):
        """Inicia uma gravação: fixa o eixo X em 0..duration_s e limpa os dados.

        :param duration_s: tamanho total da janela (lead da contagem + duração da música).
        :param lead_s: segundos iniciais que são o "lead" da contagem. Os rótulos do eixo
            mostram ``t - lead_s`` — o início da música (interno ``t=lead``) vira ``0:00`` e o
            começo da janela (interno ``t=0``) vira ``-lead``."""
        with self._lock:
            self._buf.clear()
        self._t, self._v = [], []
        self._dmin, self._dmax = math.inf, -math.inf
        self._duration = float(duration_s) if duration_s and duration_s > 0 else 1.0
        self._lead = float(lead_s) if lead_s and lead_s > 0 else 0.0
        self._last_val = None
        self._playhead_manual = None
        self._display_t = 0.0
        self._last_frame_wall = time.monotonic()
        self._recording = True
        self._ended = False
        self._reset_render_state()
        self._render()

    def push(self, t, value):
        """Adiciona uma amostra (t em segundos desde o início, valor float).

        Seguro para chamar de outra thread (ex.: a thread de aquisição)."""
        try:
            t = float(t)
            value = float(value)
        except (TypeError, ValueError):
            return
        if not (math.isfinite(t) and math.isfinite(value)):
            return
        with self._lock:
            self._buf.append((t, value))

    def set_playhead(self, t):
        """Define manualmente o instante do cursor (s), sobrepondo o relógio. Thread-safe.

        No app real não é usado (o playhead segue ``time.monotonic`` desde ``begin``);
        existe para cenários de tempo acelerado (demo)."""
        try:
            self._playhead_manual = float(t)
        except (TypeError, ValueError):
            pass

    def end(self):
        """Marca o fim da gravação; o registro inteiro permanece visível."""
        self._recording = False
        self._ended = True
        self._mark_full()

    def reset_idle(self):
        """Volta ao estado ocioso ('Aguardando gravação…')."""
        with self._lock:
            self._buf.clear()
        self._t, self._v = [], []
        self._dmin, self._dmax = math.inf, -math.inf
        self._recording = False
        self._ended = False
        self._last_val = None
        self._display_t = 0.0
        self._last_frame_wall = None
        self._playhead_manual = None
        self._reset_render_state()
        self._render()

    # -- consumo da fila --------------------------------------------------
    def _drain(self):
        with self._lock:
            if not self._buf:
                return False
            items = list(self._buf)
            self._buf.clear()
        for (t, v) in items:
            self._t.append(t)
            self._v.append(v)
            if v < self._dmin:
                self._dmin = v
            if v > self._dmax:
                self._dmax = v
            self._last_val = v
        return True

    # -- loop de animação -------------------------------------------------
    def _tick(self):
        try:
            self._drain()
            self._render()
            self._after_id = self.after(_TICK_MS, self._tick)
        except tk.TclError:
            return

    # -- geometria --------------------------------------------------------
    def _plot_rect(self):
        w = self.winfo_width() or int(self["width"] or 600)
        h = self.winfo_height() or int(self["height"] or 220)
        return (self.PAD_L, self.PAD_T, w - self.PAD_R, h - self.PAD_B)

    # -- decimação incremental por coluna de pixel ------------------------
    def _ingest(self, x0, x1):
        """Distribui os pontos ainda não processados em baldes por coluna de pixel.

        Só percorre os pontos novos (de ``_ingest_from`` em diante). Se a geometria
        X ou a duração mudou (ex.: redimensionamento), reconstrói do zero."""
        key = (x0, x1, self._duration)
        if key != self._bucket_key:
            self._bucket_key = key
            self._buckets = {}
            self._bucket_order = []
            self._ingest_from = 0
        dur = self._duration if self._duration > 0 else 1.0
        span = x1 - x0
        for i in range(self._ingest_from, len(self._t)):
            frac = self._t[i] / dur
            if frac < 0.0:
                frac = 0.0
            elif frac > 1.0:
                frac = 1.0
            px = int(x0 + frac * span)
            b = self._buckets.get(px)
            if b is None:
                self._buckets[px] = [self._v[i], 1]
                self._bucket_order.append(px)
            else:
                b[0] += self._v[i]
                b[1] += 1
        self._ingest_from = len(self._t)

    # -- relógio de exibição (playhead + revelação da linha) --------------
    def _advance_display_clock(self):
        """Avança ``_display_t`` suave por quadro, ancorado à ponta dos dados.

        Regras: avança ~1 s/s (fluido); nunca ultrapassa a última amostra disponível
        (``self._t[-1]``, para não desenhar além do que já chegou); e não fica mais que
        ``_MAX_LAG`` atrás dela (limita o buffer). O ponteiro e o corte da linha usam esse
        mesmo valor, então formam-se juntos e sincronizados."""
        now = time.monotonic()
        if self._last_frame_wall is None:
            self._last_frame_wall = now
        dt = now - self._last_frame_wall
        if dt < 0.0:
            dt = 0.0
        elif dt > 0.05:
            dt = 0.05
        self._last_frame_wall = now

        if self._playhead_manual is not None:
            d = self._playhead_manual
        elif self._ended:
            d = self._duration
        else:
            target = self._t[-1] if self._t else 0.0
            d = self._display_t + dt
            if d > target:
                d = target
            if target - d > _MAX_LAG:
                d = target - _MAX_LAG
        if d < 0.0:
            d = 0.0
        elif d > self._duration:
            d = self._duration
        self._display_t = d

    # -- desenho ----------------------------------------------------------
    def _render(self):
        try:
            x0, y0, x1, y1 = self._plot_rect()
        except tk.TclError:
            return
        if x1 - x0 < 20 or y1 - y0 < 20:
            return

        idle = not self._recording and not self._ended

        if not idle:
            self._ingest(x0, x1)
            self._advance_display_clock()
            self._maybe_rescale_y()

        # eixo Y fixo (reescala rara em _maybe_rescale_y); ocioso usa um eixo discreto.
        lo, hi, step = (-1.0, 1.0, 1.0) if idle else self._yscale

        geom = (x0, y0, x1, y1)
        scale = (lo, hi, step)

        def ypx(v):
            return y1 - (v - lo) / (hi - lo) * (y1 - y0)

        def xpx(t):
            d = self._duration if self._duration > 0 else 1.0
            f = t / d
            if f < 0.0:
                f = 0.0
            elif f > 1.0:
                f = 1.0
            return x0 + f * (x1 - x0)

        # redesenho estrutural (grade/eixos/itens) só quando algo relevante muda;
        # nos demais quadros só o tile atual + o playhead são atualizados via coords().
        full = (self._needs_full or geom != self._geom or scale != self._scale
                or idle != self._idle_drawn)
        if full:
            self._geom = geom
            self._scale = scale
            self._idle_drawn = idle
            self._needs_full = False
            self._full_render(x0, y0, x1, y1, lo, hi, step, idle, ypx, xpx)
        elif not idle:
            # os tiles só mudam quando o corte (_display_t) cruza uma nova coluna de pixel —
            # reconstruir a linha todo quadro seria O(largura)/quadro e travaria a UI. O
            # playhead (poucos itens) é atualizado sempre, garantindo o deslize fluido.
            px_cut_int = int(xpx(self._display_t))
            if px_cut_int != self._last_line_px:
                self._update_tiles(x0, x1, xpx, ypx)
                self._last_line_px = px_cut_int
            self._update_playhead(x0, y0, x1, y1, xpx)

    def _maybe_rescale_y(self):
        """Reescala o eixo Y só quando um pico ultrapassa a barreira em ~10% (evento raro).

        Com o eixo praticamente fixo, os tiles já desenhados não precisam ser refeitos; quando
        isso ocorre, expande para conter os dados e força um redesenho completo (grade + tiles)."""
        if self._dmin is math.inf:
            return
        lo, hi, _ = self._yscale
        if self._dmax > hi * 1.1 or self._dmin < lo * 1.1:
            self._yscale = _nice_y_bounds(min(self._dmin, lo), max(self._dmax, hi))
            self._mark_full()

    def _full_render(self, x0, y0, x1, y1, lo, hi, step, idle, ypx, xpx):
        """Redesenha grade/eixos/rótulos e (re)cria os itens persistentes."""
        self.delete("all")
        self._tiles = {}
        self._active_tile = -1
        self._ph_ids = ()
        C = self.CORES
        grid_faint = self._mix(C["bar_bg"], C["border"], 0.5)

        # --- gridlines + rótulos Y ---
        if idle:
            self.create_line(x0, y1, x1, y1, fill=grid_faint)
            self.create_text(x0 - 8, (y0 + y1) / 2, text="0", anchor="e",
                             fill=C["faint2"], font=(self.mono_family, 10))
        else:
            n = 0
            g = lo
            while g <= hi + 1e-6 and n < 40:
                yy = ypx(g)
                is_zero = abs(g) < 1e-6
                self.create_line(x0, yy, x1, yy,
                                 fill=(C["border"] if is_zero else grid_faint),
                                 width=(2 if is_zero else 1))
                self.create_text(x0 - 8, yy, text=self._fmt_val(g), anchor="e",
                                 fill=C["faint"], font=(self.mono_family, 10))
                g += step
                n += 1

        # unidade no topo-esquerdo
        self.create_text(x0 - 8, y0 - 2, text=self.unit, anchor="e",
                         fill=C["faint"], font=(self.mono_family, 10))

        # --- eixo X: marcas adaptativas (rótulos = t - lead; ancoradas no 0 = início da música) ---
        if not idle and self._duration > 0:
            lead = self._lead
            music_dur = self._duration - lead          # trecho de música (rótulos >= 0)
            tstep = _nice_time_step(self._duration)
            # conjunto de rótulos: múltiplos de tstep em [-lead, music_dur] + bordas + o 0
            labels = set()
            k = math.ceil((-lead) / tstep - 1e-9)
            while k * tstep <= music_dur + 1e-6:
                labels.add(round(k * tstep, 6))
                k += 1
            labels.add(round(-lead, 6))                # borda esquerda (ex.: -0:05)
            labels.add(round(music_dur, 6))            # fim da música
            labels.add(0.0)                            # início da música (destacado)
            for label in sorted(labels):
                tt = label + lead                      # coordenada interna do eixo
                if tt < -1e-6 or tt > self._duration + 1e-6:
                    continue
                xx = xpx(tt)
                is_start = abs(label) < 1e-6           # 0s = início da música
                self.create_line(xx, y0, xx, y1,
                                 fill=(C["faint"] if is_start else grid_faint),
                                 width=(2 if is_start else 1))
                self.create_text(xx, y1 + 13, text=_fmt_signed_mmss(label), anchor="n",
                                 fill=(C["muted"] if is_start else C["faint"]),
                                 font=(self.mono_family, 10))

        # --- estado ocioso: mensagem central ---
        if idle:
            self.create_text((x0 + x1) / 2, (y0 + y1) / 2, text=self.idle_text,
                             fill=C["faint2"], font=(self.display_family, 12))
            return

        # --- playhead (itens persistentes; os tiles da linha vêm de _redraw_all_tiles) ---
        ph_line = self.create_line(x0, y0, x0, y1, fill=C["text"], dash=(3, 3))
        ph_dot = self.create_oval(x0 - 3, y0 - 3, x0 + 3, y0 + 3, fill=C["text"], outline="")
        chip_bg = C["accent_tint"] if "accent_tint" in C else C["bar_bg"]
        ph_rect = self.create_rectangle(0, 0, 0, 0, fill=chip_bg, outline=C["accent"], width=1)
        ph_text = self.create_text(0, 0, text="", fill=C["accent"], font=(self.mono_family, 9))
        self._ph_ids = (ph_line, ph_dot, ph_rect, ph_text)

        # redesenha todos os tiles já percorridos (1º render, resize ou reescala de Y).
        self._redraw_all_tiles(x0, x1, xpx, ypx)
        self._last_line_px = int(xpx(self._display_t))
        self._update_playhead(x0, y0, x1, y1, xpx)

    # -- linha do sinal em tiles ------------------------------------------
    def _tile_of(self, px, x0):
        i = int((px - x0) / _TILE_PX)
        return i if i > 0 else 0

    def _redraw_all_tiles(self, x0, x1, xpx, ypx):
        """Redesenha do zero todos os tiles de 0 até o ativo (usado em full render/resize/reescala)."""
        px_cut = xpx(self._display_t)
        active = self._tile_of(px_cut, x0)
        for t in range(active):
            self._draw_tile(t, x0, x0 + (t + 1) * _TILE_PX, ypx, finalize=True)
        self._draw_tile(active, x0, px_cut, ypx, finalize=False)
        self._active_tile = active

    def _update_tiles(self, x0, x1, xpx, ypx):
        """Atualiza só o tile atual; finaliza (uma vez) os que o ponteiro já ultrapassou."""
        px_cut = xpx(self._display_t)
        active = self._tile_of(px_cut, x0)
        if self._active_tile < 0:
            self._active_tile = active
        # finaliza (desenho completo, definitivo) cada tile que ficou para trás
        while self._active_tile < active:
            t = self._active_tile
            self._draw_tile(t, x0, x0 + (t + 1) * _TILE_PX, ypx, finalize=True)
            self._active_tile += 1
        # tile ativo: revelado até o corte (ponta coincide com o ponteiro)
        self._draw_tile(active, x0, px_cut, ypx, finalize=False)

    def _draw_tile(self, idx, x0, up_to_px, ypx, finalize):
        """Desenha/atualiza o item de linha do tile ``idx`` com as colunas no seu intervalo de px.

        Usa um halo de colunas vizinhas para a média móvel não quebrar nas emendas e um ponto de
        ponte (1ª coluna do próximo tile) para não haver costura. `smooth=False` mantém o custo
        de repaint baixo (a média móvel já suaviza)."""
        order = self._bucket_order
        lo_px = int(x0 + idx * _TILE_PX)
        hi_px = int(up_to_px)
        i_lo = bisect.bisect_left(order, lo_px)
        i_hi = bisect.bisect_right(order, hi_px)
        if i_hi - i_lo < 1:
            self._hide_tile(idx)
            return
        halo = _SMOOTH_WINDOW // 2
        a = max(0, i_lo - halo)
        b = min(len(order), i_hi + halo)
        seg = order[a:b]
        vals = [self._buckets[px][0] / self._buckets[px][1] for px in seg]
        sm = self._moving_avg(vals, _SMOOTH_WINDOW)
        coords = []
        for k in range(i_lo - a, i_hi - a):
            coords.append(seg[k])
            coords.append(ypx(sm[k]))
        if finalize and i_hi < len(order):
            # ponto-ponte: conecta ao próximo tile (1ª coluna à direita do intervalo)
            npx = order[i_hi]
            coords.append(npx)
            coords.append(ypx(self._buckets[npx][0] / self._buckets[npx][1]))
        elif not finalize and coords:
            # ponta viva sob o ponteiro (mesmo y da última coluna)
            last_y = coords[-1]
            coords.append(up_to_px)
            coords.append(last_y)
        if len(coords) < 4:
            self._hide_tile(idx)
            return
        item = self._tiles.get(idx)
        if item is None:
            self._tiles[idx] = self.create_line(
                *coords, fill=self.CORES["accent"], width=1.5,
                joinstyle=tk.ROUND, capstyle=tk.ROUND, smooth=False)
        else:
            self.coords(item, *coords)
            self.itemconfigure(item, state="normal")

    def _hide_tile(self, idx):
        item = self._tiles.get(idx)
        if item is not None:
            self.itemconfigure(item, state="hidden")

    @staticmethod
    def _moving_avg(vals, w):
        """Média móvel centrada (janela ``w`` colunas) via somas de prefixo — O(n)."""
        n = len(vals)
        if w <= 1 or n == 0:
            return vals
        half = w // 2
        ps = [0.0]
        for v in vals:
            ps.append(ps[-1] + v)
        out = []
        for i in range(n):
            a = i - half if i - half > 0 else 0
            b = i + half + 1 if i + half + 1 < n else n
            out.append((ps[b] - ps[a]) / (b - a))
        return out

    def _update_playhead(self, x0, y0, x1, y1, xpx):
        """Reposiciona a linha/ponto/chip do playhead (a cada quadro, fluido)."""
        if not self._ph_ids:
            return
        ph = self._display_t
        px = xpx(ph)
        ph_line, ph_dot, ph_rect, ph_text = self._ph_ids
        self.coords(ph_line, px, y0, px, y1)
        self.coords(ph_dot, px - 3, y0 - 3, px + 3, y0 + 3)
        # chip com o tempo (rótulo = ph - lead: negativo durante o lead da contagem)
        text = _fmt_signed_mmss(ph - self._lead)
        self.itemconfigure(ph_text, text=text)
        tw = max(30, 7 * len(text))
        rx0 = px - tw / 2.0
        rx1 = px + tw / 2.0
        if rx0 < x0:
            rx0, rx1 = x0, x0 + tw
        if rx1 > x1:
            rx0, rx1 = x1 - tw, x1
        ry0, ry1 = y0 - 20, y0 - 4
        self.coords(ph_rect, rx0, ry0, rx1, ry1)
        self.coords(ph_text, (rx0 + rx1) / 2.0, (ry0 + ry1) / 2.0)

    # -- utilidades de desenho -------------------------------------------
    def _fmt_val(self, v):
        if abs(v) >= 100 or float(v).is_integer():
            return "%+d" % int(round(v)) if v else "0"
        return "%+.1f" % v if v else "0"

    @staticmethod
    def _mix(a, b, t):
        def h2r(h):
            h = h.lstrip("#")
            return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
        ca, cb = h2r(a), h2r(b)
        return "#%02X%02X%02X" % tuple(
            int(round(ca[i] + (cb[i] - ca[i]) * t)) for i in range(3))

    # -- leitura do valor atual (p/ um readout externo, opcional) --------
    @property
    def current_value(self):
        return self._last_val

    def destroy(self):
        if self._after_id:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
        super().destroy()
