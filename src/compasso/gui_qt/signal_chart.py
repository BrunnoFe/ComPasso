"""Gráfico do sinal do BITalino em tempo real — implementação nativa PySide6 (QQuickPaintedItem).

Substitui o antigo ``GraficoSinal`` (Tk Canvas). Em vez do QtCharts (que exige um caminho de
render GL/scene-graph problemático em alguns ambientes), desenha diretamente com ``QPainter``
num ``QQuickPaintedItem`` — leve, sem dependência de OpenGL e usando o mesmo scene-graph do
QtQuick já usado pelo resto da UI.

Mantém a **lógica de redução de dados** do original: decimação por coluna (contagem de pontos
limitada → custo por quadro constante), relógio de exibição (linha e ponteiro colados avançando
~1 s/s, ancorados à ponta dos dados), eixo Y fixo por sensor, média móvel de exibição e
estatísticas de Welford. Um ``QTimer`` drena a fila de amostras e agenda o repintar (``update``).

Contrato usado pelo ``ExperimentRunner`` via ``ctx.signal_plot`` (nomes em inglês, iguais ao
antigo GraphFrame): ``begin(duration, lead)``, ``push(t, v)`` (thread-safe), ``end()``,
``reset_idle()``, ``apply_settings(dict)``. ``push`` só enfileira sob lock (thread de aquisição);
os demais tocam o item e são agendados pelo runner na thread da GUI.
"""

import math
import time
import threading
from collections import deque

from PySide6.QtCore import Qt, QObject, QPointF, QRectF, Property, Signal, Slot, QTimer
from PySide6.QtGui import QColor, QPainter, QPen, QFont
from PySide6.QtQuick import QQuickPaintedItem

from compasso.core.constants import SENSOR_DEFAULT, SENSOR_GRAPH_PARAMS

# Nº de colunas de decimação ao longo da duração (limita os pontos desenhados por quadro).
_COLUNAS_DECIMACAO = 1400
_JANELA_SUAVIZACAO = 5
_ATRASO_MAXIMO_EXIBICAO_S = 0.4
_ESCALA_Y_PADRAO = 30.0

# Passos "bonitos" (s) para as marcas do eixo X; escolhe-se o menor que caiba sem aglomerar.
_PASSOS_MARCA_X = (1, 2, 5, 10, 15, 20, 30, 60, 120, 300, 600)
_ALVO_MARCAS_X = 8
# A última marca do eixo X é sempre o tempo total exato da faixa; uma marca regular a menos de
# tantos segundos do fim é omitida para não sobrepor esse rótulo final (ex.: 0:25 e faixa 0:26).
_MARGEM_MARCA_FINAL_S = 2.0


def _marcas_eixo_x(x_min, x_max, passo):
    """Tempos (s) das marcas do eixo X, em ordem; a última é sempre ``x_max`` (fim da faixa).

    Marcas regulares a cada ``passo`` a partir de 0 (cobrindo ``x_min``), omitindo a que ficaria
    a menos de ``_MARGEM_MARCA_FINAL_S`` do fim para não colidir com a marca final — que é o
    tempo total exato do áudio. Ex.: faixa de 26 s → [..., 20, 26]; de 27 s → [..., 25, 27].
    """
    marcas = []
    t = math.ceil(x_min / passo) * passo
    while t < x_max - _MARGEM_MARCA_FINAL_S + 1e-6:
        marcas.append(t)
        t += passo
    marcas.append(x_max)
    return marcas

# Margens (px) da área de plotagem dentro do item.
_MARGEM_ESQ, _MARGEM_DIR, _MARGEM_SUP, _MARGEM_INF = 52, 12, 10, 26

# Paleta de reserva (se o QML ainda não passou a paleta do tema).
_PALETA_RESERVA = {
    "bar_bg": "#161B22", "border": "#21262d", "text": "#E6EDF3",
    "muted": "#8B949E", "faint": "#6E7681", "accent": "#2DD4BF",
}


def _intervalo_ms_para_fps(fps) -> int:
    """Converte FPS no intervalo (ms) entre quadros, limitado a uma faixa sensata."""
    try:
        q = float(fps)
    except (TypeError, ValueError):
        q = 30.0
    q = min(max(q, 1.0), 120.0)
    return max(1, int(round(1000.0 / q)))


def _params_sensor(sensor):
    """Parâmetros de exibição (unidade/escala/passo) do sensor (cai no default se desconhecido)."""
    return SENSOR_GRAPH_PARAMS.get(sensor, SENSOR_GRAPH_PARAMS[SENSOR_DEFAULT])


def _escolher_passo_marca_x(duracao_total):
    """Escolhe o passo (s) entre marcas de tempo do eixo X para caber ~_ALVO_MARCAS_X marcas."""
    if duracao_total <= 0:
        return 1
    ideal = duracao_total / _ALVO_MARCAS_X
    for passo in _PASSOS_MARCA_X:
        if passo >= ideal:
            return passo
    return _PASSOS_MARCA_X[-1]


class GraficoSinal(QQuickPaintedItem):
    """Item QML que desenha o sinal em tempo real com QPainter (sem QtCharts/OpenGL)."""

    leituraChanged = Signal()
    canalChanged = Signal()
    contextoChanged = Signal()
    escalaChanged = Signal()   # escala Y (valor/limites) mudou — atualiza botões +/- no QML

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAntialiasing(True)

        self._ctx = None
        self._paleta = dict(_PALETA_RESERVA)

        # configurações de exibição (defaults; sobrepostas por ctx.graph_settings/apply_settings).
        params = _params_sensor(SENSOR_DEFAULT)
        self._unidade = params["unidade"]
        self._passo_y = params["passo"]
        self._escala_y = params["padrao"]
        self._escala_min = params["minimo"]
        self._escala_max = params["maximo"]
        self._suavizacao_ativa = True
        self._janela_suavizacao = _JANELA_SUAVIZACAO
        self._largura_linha = 2.0
        self._grade_visivel = True
        self._rotulos_visiveis = True
        self._value_mode = "raw"
        self._intervalo_ms = _intervalo_ms_para_fps(30)

        # estado da faixa.
        self._pendentes = deque()
        self._trava = threading.Lock()
        self._tempos = []
        self._valores = []
        self._duracao = 0.0
        self._antecedencia = 0.0
        self._gravando = False
        self._finalizado = False
        self._tempo_exibicao = 0.0
        self._relogio_ultimo = None

        self._reiniciar_decimacao()
        self._reiniciar_estatisticas()
        self._leitura = "—"
        self._canal = "SINAL DO BITALINO"

        # timer de quadro: drena a fila, decima, avança o relógio e agenda o repintar.
        self._timer = QTimer(self)
        self._timer.setInterval(self._intervalo_ms)
        self._timer.timeout.connect(self._quadro)
        self._timer.start()

    # =============================================================== QML props
    def _get_contexto(self):
        return self._ctx

    def _set_contexto(self, ctx):
        """Recebe o Context do QML: registra-se como fachada do gráfico e lê as configs."""
        self._ctx = ctx
        if ctx is not None:
            ctx.signal_plot = self
            settings = getattr(ctx, "graph_settings", None) or {}
            sensor = getattr(ctx, "sensor_type", SENSOR_DEFAULT)
            self.aplicar_sensor(sensor, resetar_escala=False)
            self.apply_settings(settings)
            self._canal = self._texto_canal()
            self.canalChanged.emit()
        self.contextoChanged.emit()

    contexto = Property(QObject, _get_contexto, _set_contexto, notify=contextoChanged)

    def _get_paleta(self):
        return self._paleta

    def _set_paleta(self, paleta):
        if isinstance(paleta, dict) and paleta:
            self._paleta = paleta
            self.update()

    paleta = Property("QVariant", _get_paleta, _set_paleta)

    def _get_leitura(self):
        return self._leitura

    leitura = Property(str, _get_leitura, notify=leituraChanged)

    def _get_canal(self):
        return self._canal

    canal = Property(str, _get_canal, notify=canalChanged)

    # ---- escala Y (para os botões +/- do gráfico) ----
    def _get_escala_atual(self):
        return float(self._escala_y)

    escalaAtual = Property(float, _get_escala_atual, notify=escalaChanged)

    def _get_escala_min(self):
        return float(self._escala_min)

    escalaMin = Property(float, _get_escala_min, notify=escalaChanged)

    def _get_escala_max(self):
        return float(self._escala_max)

    escalaMax = Property(float, _get_escala_max, notify=escalaChanged)

    def _get_unidade(self):
        return str(self._unidade)

    unidade = Property(str, _get_unidade, notify=escalaChanged)

    # =========================================================== contrato runner
    def push(self, t, value) -> None:
        """Enfileira uma amostra (thread-safe; chamado da thread de aquisição)."""
        try:
            t = float(t)
            value = float(value)
        except (TypeError, ValueError):
            return
        if not (math.isfinite(t) and math.isfinite(value)):
            return
        with self._trava:
            self._pendentes.append((t, value))

    def begin(self, duration_s, lead_s=0) -> None:
        """Inicia a exibição de uma nova faixa: fixa o eixo X e limpa os dados anteriores."""
        with self._trava:
            self._pendentes.clear()
        self._tempos, self._valores = [], []
        self._duracao = float(duration_s) if duration_s and duration_s > 0 else 1.0
        self._antecedencia = float(lead_s) if lead_s and lead_s > 0 else 0.0
        self._gravando = True
        self._finalizado = False
        self._tempo_exibicao = 0.0
        self._relogio_ultimo = time.monotonic()
        self._reiniciar_decimacao()
        self._reiniciar_estatisticas()
        self._canal = self._texto_canal()
        self.canalChanged.emit()
        self.update()

    def end(self, duracao_real=None) -> None:
        """Encerra a faixa: o relógio salta para o fim, revelando o registro completo.

        Se ``duracao_real`` (duração real da faixa em segundos, medida pela reprodução) for
        informada, o eixo X é reajustado para terminar exatamente onde a música terminou.
        O eixo é fixado antes da reprodução com uma estimativa (``player.get_length()``) que
        pode divergir da reprodução real; sem este ajuste a linha do sinal termina antes do
        fim do eixo (espaço vazio) ou é comprimida contra a borda direita. Como a decimação
        mapeia tempo→coluna por fração da duração, mudar a duração exige reprocessar as
        amostras cruas com a nova referência.
        """
        self._drenar_pendentes()
        if duracao_real is not None:
            try:
                nova_dur = self._antecedencia + float(duracao_real)
            except (TypeError, ValueError):
                nova_dur = 0.0
            if nova_dur > 0 and abs(nova_dur - self._duracao) > 1e-6:
                self._duracao = nova_dur
                self._reiniciar_decimacao()
        self._decimar_novas()
        self._gravando = False
        self._finalizado = True

    def reset_idle(self) -> None:
        """Volta ao estado ocioso (sem dados, "Aguardando gravação…")."""
        with self._trava:
            self._pendentes.clear()
        self._tempos, self._valores = [], []
        self._gravando = False
        self._finalizado = False
        self._tempo_exibicao = 0.0
        self._relogio_ultimo = None
        self._reiniciar_decimacao()
        self._reiniciar_estatisticas()
        self._leitura = "—"
        self.leituraChanged.emit()
        self.update()

    @Slot()
    def ampliar_zoom(self) -> None:
        """Botão "+": amplia o sinal (zoom in) reduzindo o alcance ± da escala Y em um passo.
        Permitido DURANTE a gravação."""
        self._ajustar_escala(-1)

    @Slot()
    def reduzir_zoom(self) -> None:
        """Botão "−": afasta o sinal (zoom out) aumentando o alcance ± da escala Y em um passo.
        Permitido DURANTE a gravação."""
        self._ajustar_escala(+1)

    def _ajustar_escala(self, sinal: int) -> None:
        """Nudge da escala Y por um passo, com clamp aos limites do sensor. Barato: só troca o
        fator de mapeamento e repinta (a decimação guarda valores brutos, sem reprocessar).

        Ao contrário de ``apply_settings``, é permitido durante a gravação — é justamente o
        controle ao vivo pedido pelos botões +/- ao lado do eixo.
        """
        passo = self._passo_y if self._passo_y > 0 else max(1.0, abs(self._escala_y) * 0.1)
        nova = self._escala_y + sinal * passo
        nova = max(self._escala_min, min(self._escala_max, nova))
        if abs(nova - self._escala_y) < 1e-9:
            return
        self._escala_y = nova
        # persiste no ctx p/ o slider da janela de configurações e a próxima sessão.
        settings = getattr(self._ctx, "graph_settings", None) if self._ctx is not None else None
        if isinstance(settings, dict):
            settings["y_scale"] = nova
        self.escalaChanged.emit()
        self.update()

    def apply_settings(self, settings: dict) -> None:
        """Aplica configurações de exibição ao vivo (escala Y só fora de gravação)."""
        if not isinstance(settings, dict):
            return
        if "unidade" in settings:
            self._unidade = settings["unidade"]
        if "y_step" in settings:
            self._passo_y = settings["y_step"]
        if "y_scale" in settings and not self._gravando:
            try:
                self._escala_y = abs(float(settings["y_scale"])) or self._escala_y
            except (TypeError, ValueError):
                pass
        if "smoothing_enabled" in settings:
            self._suavizacao_ativa = bool(settings["smoothing_enabled"])
        if "smoothing_window" in settings:
            self._janela_suavizacao = max(1, int(settings["smoothing_window"]))
        if "fps" in settings:
            self._intervalo_ms = _intervalo_ms_para_fps(settings["fps"])
            self._timer.setInterval(self._intervalo_ms)
        if "line_width" in settings:
            self._largura_linha = float(settings["line_width"])
        if "grid_visible" in settings:
            self._grade_visivel = bool(settings["grid_visible"])
        if "axis_labels_visible" in settings:
            self._rotulos_visiveis = bool(settings["axis_labels_visible"])
        if "value_mode" in settings:
            self._value_mode = settings["value_mode"]
        # escala/unidade podem ter mudado — atualiza os botões +/- do gráfico.
        self.escalaChanged.emit()
        self.update()

    def aplicar_sensor(self, sensor, resetar_escala=True) -> None:
        """Aplica unidade/escala/passo do sensor (equivale a ``aplicar_sensor_ao_grafico``)."""
        params = _params_sensor(sensor)
        # limites da escala Y passam a ser os do sensor atual (usados pelos botões +/-).
        self._escala_min = params["minimo"]
        self._escala_max = params["maximo"]
        if self._ctx is not None:
            self._ctx.sensor_type = sensor
        settings = {}
        if self._ctx is not None and isinstance(self._ctx.graph_settings, dict):
            settings = self._ctx.graph_settings
        if resetar_escala:
            escala = params["padrao"]
        else:
            try:
                escala = abs(float(settings.get("y_scale", params["padrao"])))
                if not (params["minimo"] <= escala <= params["maximo"]):
                    escala = params["padrao"]
            except (TypeError, ValueError):
                escala = params["padrao"]
        settings["y_scale"] = escala
        if self._ctx is not None:
            self._ctx.graph_settings = settings
        self.apply_settings({"y_scale": escala, "unidade": params["unidade"], "y_step": params["passo"]})

    # =================================================================== interno
    def _texto_canal(self) -> str:
        n = getattr(self._ctx, "signal_channel", 0) if self._ctx is not None else 0
        return f"SINAL DO BITALINO · CANAL A{n}"

    def _reiniciar_decimacao(self) -> None:
        self._baldes = {}
        self._ordem_baldes = []
        self._processadas = 0

    def _reiniciar_estatisticas(self) -> None:
        self._est_n = 0
        self._est_media = 0.0
        self._est_m2 = 0.0
        self._est_min = None
        self._est_max = None

    def _acumular_estatistica(self, valor) -> None:
        self._est_n += 1
        delta = valor - self._est_media
        self._est_media += delta / self._est_n
        self._est_m2 += delta * (valor - self._est_media)
        if self._est_min is None or valor < self._est_min:
            self._est_min = valor
        if self._est_max is None or valor > self._est_max:
            self._est_max = valor

    def _avancar_relogio(self) -> None:
        agora = time.monotonic()
        if self._relogio_ultimo is None:
            self._relogio_ultimo = agora
        dt = min(max(agora - self._relogio_ultimo, 0.0), 0.05)
        self._relogio_ultimo = agora
        if self._finalizado:
            novo = self._duracao
        else:
            ult = self._tempos[-1] if self._tempos else 0.0
            novo = min(self._tempo_exibicao + dt, ult)
            if ult - novo > _ATRASO_MAXIMO_EXIBICAO_S:
                novo = ult - _ATRASO_MAXIMO_EXIBICAO_S
        self._tempo_exibicao = min(max(novo, 0.0), self._duracao)

    def _decimar_novas(self) -> None:
        dur = self._duracao if self._duracao > 0 else 1.0
        for i in range(self._processadas, len(self._tempos)):
            fracao = self._tempos[i] / dur
            fracao = 0.0 if fracao < 0.0 else 1.0 if fracao > 1.0 else fracao
            col = int(fracao * (_COLUNAS_DECIMACAO - 1))
            balde = self._baldes.get(col)
            if balde is None:
                self._baldes[col] = [self._valores[i], 1]
                self._ordem_baldes.append(col)
            else:
                balde[0] += self._valores[i]
                balde[1] += 1
        self._processadas = len(self._tempos)

    @staticmethod
    def _media_movel(valores, janela):
        n = len(valores)
        if janela <= 1 or n == 0:
            return valores
        metade = janela // 2
        prefixo = [0.0]
        for v in valores:
            prefixo.append(prefixo[-1] + v)
        saida = []
        for i in range(n):
            ini = max(0, i - metade)
            fim = min(n, i + metade + 1)
            saida.append((prefixo[fim] - prefixo[ini]) / (fim - ini))
        return saida

    def _pontos_decimados(self):
        """Lista ``(tempo_relativo_s, valor)`` até o corte do relógio de exibição (já suavizada)."""
        dur = self._duracao if self._duracao > 0 else 1.0
        corte_col = int(min(max(self._tempo_exibicao / dur, 0.0), 1.0) * (_COLUNAS_DECIMACAO - 1))
        cols = sorted(c for c in self._ordem_baldes if c <= corte_col)
        valores = [self._baldes[c][0] / self._baldes[c][1] for c in cols]
        janela = self._janela_suavizacao if self._suavizacao_ativa else 1
        valores = self._media_movel(valores, janela)
        return [((c / (_COLUNAS_DECIMACAO - 1)) * dur - self._antecedencia, valores[i])
                for i, c in enumerate(cols)]

    def _drenar_pendentes(self) -> None:
        """Move as amostras enfileiradas (thread de aquisição) para os vetores de exibição."""
        with self._trava:
            novas = list(self._pendentes) if self._pendentes else None
            if novas:
                self._pendentes.clear()
        if novas:
            for t, v in novas:
                self._tempos.append(t)
                self._valores.append(v)
                if t >= self._antecedencia:
                    self._acumular_estatistica(v)

    def _quadro(self) -> None:
        """Um quadro: drena a fila, decima, avança o relógio, atualiza leitura e repinta."""
        self._drenar_pendentes()
        self._decimar_novas()
        self._avancar_relogio()
        self._atualizar_leitura()
        if self._gravando or self._finalizado:
            self.update()

    def _atualizar_leitura(self) -> None:
        texto = self._montar_leitura()
        if texto != self._leitura:
            self._leitura = texto
            self.leituraChanged.emit()

    def _montar_leitura(self) -> str:
        u = self._unidade
        if self._value_mode == "mean":
            if self._est_n == 0:
                return "—"
            texto = f"Média: {self._est_media:.2f} {u}"
            if self._est_n > 1:
                texto += f" ({math.sqrt(self._est_m2 / (self._est_n - 1)):.2f} {u})"
            return texto
        if not self._valores:
            return "—"
        texto = f"Valor: {self._valores[-1]:.2f} {u}"
        if self._est_min is not None and self._est_max is not None:
            texto += f" ({self._est_min:.2f} - {self._est_max:.2f})"
        return texto

    # ===================================================================== paint
    def _cor(self, chave, reserva="#888888"):
        return QColor(self._paleta.get(chave, reserva))

    def _eh_tema_claro(self) -> bool:
        """Heurística: fundo claro (luminância alta) => tema claro (Sereno/Aurora)."""
        c = QColor(self._paleta.get("bar_bg", "#161B22"))
        lum = 0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue()
        return lum > 140

    def _cor_grade(self):
        """Cor das linhas de grade (exceto a de t0). Nos temas claros usa um cinza neutro bem
        claro (a borda cheia ficava escura demais e atrapalhava a leitura do sinal em Sereno/
        Aurora); nos temas escuros mantém a cor de borda da paleta."""
        if self._eh_tema_claro():
            return QColor(150, 156, 165, 70)   # cinza claro translúcido
        return self._cor("border", "#21262d")

    def paint(self, painter: QPainter) -> None:
        """Desenha grade, eixos, a linha do sinal e o ponteiro (chamado pelo scene-graph)."""
        largura = self.width()
        altura = self.height()
        if largura <= 0 or altura <= 0:
            return
        painter.setRenderHint(QPainter.Antialiasing, True)

        x0, y0 = _MARGEM_ESQ, _MARGEM_SUP
        x1, y1 = largura - _MARGEM_DIR, altura - _MARGEM_INF
        if x1 <= x0 or y1 <= y0:
            return

        ativo = self._gravando or self._finalizado or bool(self._tempos)
        if not ativo:
            self._pintar_ocioso(painter, x0, y0, x1, y1)
            return

        esc = self._escala_y if self._escala_y > 0 else _ESCALA_Y_PADRAO
        x_min, x_max = -self._antecedencia, self._duracao - self._antecedencia
        if x_max <= x_min:
            x_max = x_min + 1.0

        def px(t):
            return x0 + (t - x_min) / (x_max - x_min) * (x1 - x0)

        def py(v):
            return y0 + (esc - v) / (2 * esc) * (y1 - y0)

        fonte = QFont(self._paleta.get("_display", "Segoe UI"), 8)
        painter.setFont(fonte)

        # ---- grade Y + rótulos (de -esc a +esc pelo passo) ----
        if self._grade_visivel or self._rotulos_visiveis:
            self._pintar_grade_y(painter, x0, x1, esc, py)
        # ---- grade/rótulos X (tempo relativo ao início da música) ----
        self._pintar_grade_x(painter, y0, y1, x_min, x_max, px)

        # ---- linha do sinal ----
        pontos = self._pontos_decimados()
        if len(pontos) >= 2:
            caminho = [QPointF(px(t), py(v)) for t, v in pontos]
            pen = QPen(self._cor("accent", "#2DD4BF"))
            pen.setWidthF(self._largura_linha)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(pen)
            painter.drawPolyline(caminho)

        # ---- ponteiro (linha vertical no tempo de exibição) ----
        xp = px(self._tempo_exibicao - self._antecedencia)
        pen = QPen(self._cor("muted", "#8B949E"))
        pen.setWidthF(1.0)
        painter.setPen(pen)
        painter.drawLine(QPointF(xp, y0), QPointF(xp, y1))

    def _pintar_grade_y(self, painter, x0, x1, esc, py):
        cor_grade = self._cor_grade()
        cor_texto = self._cor("faint", "#6E7681")
        passo = self._passo_y if self._passo_y > 0 else esc / 3.0
        n = int(esc / passo)
        for k in range(-n, n + 1):
            v = k * passo
            y = py(v)
            if self._grade_visivel:
                painter.setPen(QPen(cor_grade, 1))
                painter.drawLine(QPointF(x0, y), QPointF(x1, y))
            if self._rotulos_visiveis:
                painter.setPen(QPen(cor_texto))
                rot = f"{v:.0f}" if abs(passo) >= 1 else f"{v:.1f}"
                painter.drawText(QRectF(0, y - 8, x0 - 6, 16),
                                 Qt.AlignRight | Qt.AlignVCenter, rot)

    def _pintar_grade_x(self, painter, y0, y1, x_min, x_max, px):
        cor_grade = self._cor_grade()
        cor_texto = self._cor("faint", "#6E7681")
        cor_zero = self._cor("muted", "#8B949E")   # linha de t0 mantém-se forte
        passo = _escolher_passo_marca_x(self._duracao)

        # Marcas de -5 s até o fim: regulares a cada `passo` (t0 destacado) e a final sempre no
        # tempo total exato da faixa (x_max). A grade da marca final é omitida (coincide com a
        # borda direita/ponteiro); seu rótulo é ancorado à direita p/ não vazar da área.
        marcas = _marcas_eixo_x(x_min, x_max, passo)
        for i, t in enumerate(marcas):
            eh_final = (i == len(marcas) - 1)
            destaque = abs(t) < 1e-6   # início da música (0:00) destacado
            x = px(t)
            if self._grade_visivel and not eh_final:
                painter.setPen(QPen(cor_zero if destaque else cor_grade, 1))
                painter.drawLine(QPointF(x, y0), QPointF(x, y1))
            if self._rotulos_visiveis:
                painter.setPen(QPen(cor_zero if destaque else cor_texto))
                if eh_final:
                    painter.drawText(QRectF(x - 48, y1 + 4, 48, 16),
                                     Qt.AlignRight | Qt.AlignTop, self._formatar_tempo(t))
                else:
                    painter.drawText(QRectF(x - 24, y1 + 4, 48, 16),
                                     Qt.AlignHCenter | Qt.AlignTop, self._formatar_tempo(t))

    @staticmethod
    def _formatar_tempo(segundos):
        sinal = "-" if segundos < 0 else ""
        s = int(round(abs(segundos)))
        return f"{sinal}{s // 60}:{s % 60:02d}"

    def _pintar_ocioso(self, painter, x0, y0, x1, y1):
        """Estado ocioso: apenas a mensagem 'Aguardando gravação…' (sem linha de base)."""
        painter.setPen(QPen(self._cor("faint", "#6E7681")))
        painter.setFont(QFont(self._paleta.get("_display", "Segoe UI"), 10))
        painter.drawText(QRectF(x0, y0, x1 - x0, y1 - y0),
                         Qt.AlignCenter, "Aguardando gravação…")
