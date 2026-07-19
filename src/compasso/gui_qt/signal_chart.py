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
from bisect import bisect_right
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

# Taxa de quadros fixa. Não é configurável de propósito: 30 fps já entrega uma linha contínua
# para qualquer taxa de amostragem do BITalino (a decimação garante custo por quadro constante),
# e deixar o usuário elevá-la só aumentava o consumo sem ganho visual perceptível.
_FPS = 30
_INTERVALO_QUADRO_MS = max(1, int(round(1000.0 / _FPS)))

# Limite (nº de amostras) da fila entre a thread de aquisição e a da GUI. Se a GUI estagnar, é
# melhor descartar as amostras mais antigas do que crescer sem limite — o CSV é o dado primário,
# o gráfico é só exibição.
_MAX_PENDENTES = 20000

# Hierarquia de marcas do eixo X: linha a cada 1 s (mais apagada), a cada 5 s (peso médio) e em
# t0 (destaque). Os rótulos usam um passo próprio, escolhido pela largura disponível.
_PASSO_MARCA_MENOR_S = 1
_PASSO_MARCA_MEDIA_S = 5
# Passos "bonitos" (s) candidatos para os RÓTULOS, do mais denso ao mais esparso. Começa em 5 —
# nunca de 1 em 1 — por dois motivos: rotular cada segundo faz o eixo mudar de aparência conforme
# a duração da faixa (faixa curta ganhava rótulo a cada 1 s, faixa longa a cada 5 s, sem que nada
# no experimento tivesse mudado), e 5 s é o mesmo intervalo das linhas de destaque médio, então
# texto e grade passam a contar a mesma história. As linhas de 1 s continuam desenhadas, só que
# sem texto.
_PASSOS_ROTULO_X = (5, 10, 15, 30, 60, 120, 300, 600)
# Folga (px) exigida entre rótulos vizinhos, além da largura do próprio texto.
_FOLGA_ROTULO_PX = 14
# Abaixo deste espaçamento (px) uma família de linhas verticais vira ruído visual e é omitida.
_ESPACO_MINIMO_LINHA_PX = 5
# Opacidade (0-255) da grade nos temas claros. Baixa de propósito: sobre fundo branco a grade
# precisa apenas orientar a leitura, nunca competir com a linha do sinal. Com `faint2` do
# Sereno resulta em ~#EFF1F3 — presente, mas atrás do traço.
_ALFA_GRADE_CLARA = 55
# Quanto da opacidade da grade sobra para as linhas de 1 s (o menor dos três destaques).
_FATOR_ALFA_GRADE_MENOR = 0.55


def _passo_rotulo_x(x_min, x_max, largura_px, largura_texto_px=34):
    """Menor passo (s) de `_PASSOS_ROTULO_X` cujos rótulos cabem sem se sobrepor."""
    faixa = x_max - x_min
    if faixa <= 0 or largura_px <= 0:
        return _PASSOS_ROTULO_X[0]
    minimo = largura_texto_px + _FOLGA_ROTULO_PX
    for passo in _PASSOS_ROTULO_X:
        if passo / faixa * largura_px >= minimo:
            return passo
    return _PASSOS_ROTULO_X[-1]


def _marcas_multiplas(x_min, x_max, passo):
    """Múltiplos de ``passo`` dentro de ``[x_min, x_max]``, ancorados em 0 (t0 sempre incluído)."""
    marcas = []
    t = math.ceil(x_min / passo) * passo
    while t <= x_max + 1e-6:
        marcas.append(t)
        t += passo
    return marcas

# Margens (px) da área de plotagem dentro do item.
_MARGEM_ESQ, _MARGEM_DIR, _MARGEM_SUP, _MARGEM_INF = 52, 12, 10, 26

# Paleta de reserva (se o QML ainda não passou a paleta do tema).
_PALETA_RESERVA = {
    "bar_bg": "#161B22", "border": "#21262d", "text": "#E6EDF3",
    "muted": "#8B949E", "faint": "#6E7681", "accent": "#2DD4BF",
}


def _params_sensor(sensor):
    """Parâmetros de exibição (unidade/escala/passo) do sensor (cai no default se desconhecido)."""
    return SENSOR_GRAPH_PARAMS.get(sensor, SENSOR_GRAPH_PARAMS[SENSOR_DEFAULT])


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

        # estado da faixa.
        self._pendentes = deque(maxlen=_MAX_PENDENTES)
        self._trava = threading.Lock()
        # as amostras cruas NÃO são acumuladas: alimentam os baldes de decimação diretamente e
        # são descartadas. Guardá-las custava ~10^6 floats numa faixa longa a 1000 Hz, sem
        # utilidade — o eixo X já nasce correto em `begin()` graças à duração pré-varrida.
        # Destas só o último par é útil (relógio de exibição e leitura numérica).
        self._ultimo_tempo = None
        self._ultimo_valor = None
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

        # timer de quadro: drena a fila, decima, avança o relógio e agenda o repintar. Só roda
        # entre `begin()` e `end()` — antes girava 30x/s durante toda a vida do app, inclusive
        # com a aplicação ociosa.
        self._timer = QTimer(self)
        self._timer.setInterval(_INTERVALO_QUADRO_MS)
        self._timer.timeout.connect(self._quadro)

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
        self._ultimo_tempo = self._ultimo_valor = None
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
        self._timer.start()
        self.update()

    def end(self, duracao_real=None) -> None:
        """Encerra a faixa: o relógio salta para o fim, revelando o registro completo.

        ``duracao_real`` é uma correção fina do eixo X. Com a duração pré-varrida no scan e o
        fim da faixa detectado pelo sinal ``EndOfMedia`` (não mais por polling de 200 ms), a
        divergência para a duração usada em ``begin()`` é de milissegundos — a reancoragem
        deixou de ser o caso comum e virou rede de segurança.
        """
        self._drenar_pendentes()
        if duracao_real is not None:
            try:
                nova_dur = self._antecedencia + float(duracao_real)
            except (TypeError, ValueError):
                nova_dur = 0.0
            if nova_dur > 0 and abs(nova_dur - self._duracao) > 1e-6:
                self._remapear_baldes(nova_dur)
        self._gravando = False
        self._finalizado = True
        self._timer.stop()
        # último quadro: o relógio salta para o fim e revela o traço completo.
        self._avancar_relogio()
        self._atualizar_leitura()
        self.update()

    def reset_idle(self) -> None:
        """Volta ao estado ocioso (sem dados, "Aguardando gravação…")."""
        self._timer.stop()
        with self._trava:
            self._pendentes.clear()
        self._ultimo_tempo = self._ultimo_valor = None
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
        if "line_width" in settings:
            self._largura_linha = float(settings["line_width"])
        if "grid_visible" in settings:
            self._grade_visivel = bool(settings["grid_visible"])
        if "axis_labels_visible" in settings:
            self._rotulos_visiveis = bool(settings["axis_labels_visible"])
        if "value_mode" in settings:
            self._value_mode = settings["value_mode"]
        # a suavização entra no cálculo dos pontos cacheados: mudá-la exige recalculá-los, ou a
        # pré-visualização ao vivo da janela de configurações não teria efeito visível.
        if "smoothing_enabled" in settings or "smoothing_window" in settings:
            self._cache_sujo = True
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
        self._colunas = []          # colunas ocupadas, mantidas ordenadas
        self._pontos_cache = []     # [(t, valor_suavizado)] reaproveitado entre quadros
        self._cache_sujo = True

    def _remapear_baldes(self, nova_duracao: float) -> None:
        """Reancora os baldes numa nova duração total, sem as amostras cruas.

        Cada balde é a média de uma janela de tempo; reposicioná-lo é reescalar sua coluna pela
        razão entre as durações. É uma aproximação (dois baldes podem cair na mesma coluna e são
        combinados pela média ponderada), aceitável porque a correção é de milissegundos — e
        muito mais barata que guardar todas as amostras cruas só para este caso.
        """
        dur_antiga = self._duracao if self._duracao > 0 else 1.0
        razao = dur_antiga / nova_duracao
        novos = {}
        for col, (soma, cont) in self._baldes.items():
            nova_col = int(round(col * razao))
            nova_col = max(0, min(_COLUNAS_DECIMACAO - 1, nova_col))
            alvo = novos.get(nova_col)
            if alvo is None:
                novos[nova_col] = [soma, cont]
            else:
                alvo[0] += soma
                alvo[1] += cont
        self._duracao = nova_duracao
        self._baldes = novos
        self._colunas = sorted(novos)
        self._cache_sujo = True

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
            ult = self._ultimo_tempo if self._ultimo_tempo is not None else 0.0
            novo = min(self._tempo_exibicao + dt, ult)
            if ult - novo > _ATRASO_MAXIMO_EXIBICAO_S:
                novo = ult - _ATRASO_MAXIMO_EXIBICAO_S
        self._tempo_exibicao = min(max(novo, 0.0), self._duracao)

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

    def _recalcular_pontos(self):
        """Recalcula a lista ``(tempo_relativo_s, valor_suavizado)`` de todas as colunas.

        Só roda quando chegaram amostras novas (``_cache_sujo``), não a cada quadro: o conjunto
        de colunas cresce monotonicamente, então entre dois quadros sem dados novos o resultado
        é idêntico. Antes isto era refeito 30x/s — ordenação, média por balde, média móvel e a
        materialização de até 1400 pontos — mesmo com o traço parado.
        """
        dur = self._duracao if self._duracao > 0 else 1.0
        valores = [self._baldes[c][0] / self._baldes[c][1] for c in self._colunas]
        janela = self._janela_suavizacao if self._suavizacao_ativa else 1
        valores = self._media_movel(valores, janela)
        escala_t = dur / (_COLUNAS_DECIMACAO - 1)
        self._pontos_cache = [(c * escala_t - self._antecedencia, valores[i])
                              for i, c in enumerate(self._colunas)]
        self._cache_sujo = False

    def _pontos_decimados(self):
        """Pontos visíveis: o cache truncado no corte do relógio de exibição."""
        if self._cache_sujo:
            self._recalcular_pontos()
        dur = self._duracao if self._duracao > 0 else 1.0
        fracao = min(max(self._tempo_exibicao / dur, 0.0), 1.0)
        corte_col = int(fracao * (_COLUNAS_DECIMACAO - 1))
        # `_colunas` é uma lista ordenada de inteiros alinhada com `_pontos_cache`: a busca
        # binária dá o corte em O(log n), sem materializar nada.
        return self._pontos_cache[:bisect_right(self._colunas, corte_col)]

    def _drenar_pendentes(self) -> None:
        """Consome as amostras enfileiradas direto nos baldes de decimação.

        As amostras cruas não são guardadas (ver ``__init__``): cada uma entra na média do seu
        balde e é descartada, mantendo o uso de memória constante ao longo da faixa,
        independentemente da duração e da taxa de amostragem.
        """
        with self._trava:
            if not self._pendentes:
                return
            novas = list(self._pendentes)
            self._pendentes.clear()

        dur = self._duracao if self._duracao > 0 else 1.0
        novas_colunas = False
        for t, v in novas:
            if t >= self._antecedencia:
                self._acumular_estatistica(v)
            fracao = t / dur
            fracao = 0.0 if fracao < 0.0 else 1.0 if fracao > 1.0 else fracao
            col = int(fracao * (_COLUNAS_DECIMACAO - 1))
            balde = self._baldes.get(col)
            if balde is None:
                self._baldes[col] = [v, 1]
                novas_colunas = True
            else:
                balde[0] += v
                balde[1] += 1
        self._ultimo_tempo, self._ultimo_valor = novas[-1]
        if novas_colunas:
            # as amostras chegam em ordem cronológica, então as colunas novas são as maiores;
            # reordenar o conjunto todo seria desnecessário na prática, mas sorted() sobre
            # uma lista quase ordenada é linear (Timsort) e blinda contra amostras fora de ordem.
            self._colunas = sorted(self._baldes)
        self._cache_sujo = True

    def _quadro(self) -> None:
        """Um quadro: drena a fila, avança o relógio, atualiza leitura e repinta."""
        self._drenar_pendentes()
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
        if self._ultimo_valor is None:
            return "—"
        texto = f"Valor: {self._ultimo_valor:.2f} {u}"
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
        """Cor base da grade (grade Y e linhas de 5 s do eixo X; t0 tem cor própria).

        Nos temas claros a borda cheia da paleta é escura demais sobre o fundo branco e disputa
        atenção com a linha do sinal. Usa-se o cinza mais claro da própria paleta (``faint2``),
        bem transparente: além de discreto, ele já acompanha a temperatura do tema — frio no
        Sereno, quente no Aurora —, o que um cinza neutro fixo não fazia.
        """
        if self._eh_tema_claro():
            cor = QColor(self._paleta.get("faint2", "#B4BCC7"))
            cor.setAlpha(_ALFA_GRADE_CLARA)
            return cor
        return self._cor("border", "#21262d")

    @staticmethod
    def _cor_grade_menor(cor_grade):
        """Variante mais apagada da grade, para as linhas de 1 s (menor destaque)."""
        cor = QColor(cor_grade)
        cor.setAlpha(max(1, int(cor_grade.alpha() * _FATOR_ALFA_GRADE_MENOR)))
        return cor

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

        ativo = self._gravando or self._finalizado or bool(self._baldes)
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
        """Grade e rótulos do eixo X, em três pesos visuais.

        Linhas a cada 1 s (mais apagadas), a cada 5 s (peso médio) e em t0 (destaque). Cada
        família só é desenhada se suas linhas ficarem a pelo menos ``_ESPACO_MINIMO_LINHA_PX``
        umas das outras — numa faixa de 5 minutos as linhas de 1 s seriam centenas, virando uma
        mancha. Os rótulos usam um passo próprio, calculado da largura disponível, porque é a
        colisão de textos (não de linhas) que limita a densidade legível.
        """
        cor_grade = self._cor_grade()
        cor_texto = self._cor("faint", "#6E7681")
        cor_zero = self._cor("muted", "#8B949E")   # linha de t0 mantém-se forte
        largura_px = px(x_max) - px(x_min)
        faixa = max(x_max - x_min, 1e-6)

        def espacamento_px(passo):
            return passo / faixa * largura_px

        if self._grade_visivel:
            # cada instante recebe UMA linha só, da família de maior destaque a que pertence.
            # Desenhar as duas famílias inteiras sobrepunha os múltiplos de 5 s (que também são
            # múltiplos de 1 s): as duas transparências se compunham e a linha saía bem mais
            # escura que o pretendido, achatando a hierarquia de destaques.
            for passo, cor in ((_PASSO_MARCA_MENOR_S, self._cor_grade_menor(cor_grade)),
                               (_PASSO_MARCA_MEDIA_S, cor_grade)):
                if espacamento_px(passo) < _ESPACO_MINIMO_LINHA_PX:
                    continue
                painter.setPen(QPen(cor, 1))
                for t in _marcas_multiplas(x_min, x_max, passo):
                    if abs(t) < 1e-6:
                        continue   # t0 é desenhado à parte, com destaque
                    if passo == _PASSO_MARCA_MENOR_S and abs(t % _PASSO_MARCA_MEDIA_S) < 1e-6:
                        continue   # pertence à família de 5 s, que o desenha com mais peso
                    x = px(t)
                    painter.drawLine(QPointF(x, y0), QPointF(x, y1))
            # t0: o instante de início do áudio, a referência de leitura do gráfico.
            if x_min <= 0.0 <= x_max:
                pen_zero = QPen(cor_zero)
                pen_zero.setWidthF(1.6)
                painter.setPen(pen_zero)
                x = px(0.0)
                painter.drawLine(QPointF(x, y0), QPointF(x, y1))

        if not self._rotulos_visiveis:
            return

        # Rótulos regulares (múltiplos do passo, sempre >= 5 s) + o final, que é o tempo total
        # exato da faixa e fica ancorado à direita para não vazar da área de plotagem.
        metricas = painter.fontMetrics()
        texto_final = self._formatar_tempo(x_max)
        largura_final = metricas.horizontalAdvance(texto_final)
        passo_rotulo = _passo_rotulo_x(x_min, x_max, largura_px,
                                       metricas.horizontalAdvance("-00:00"))
        x_final = px(x_max)
        for t in _marcas_multiplas(x_min, x_max, passo_rotulo):
            texto = self._formatar_tempo(t)
            x = px(t)
            # só omite quando os dois textos realmente se tocariam — antes uma margem fixa e
            # generosa apagava um rótulo legítimo (o "0:19" que sumia com a faixa de 20 s).
            meia_largura = metricas.horizontalAdvance(texto) / 2.0
            if x + meia_largura > x_final - largura_final - _FOLGA_ROTULO_PX:
                continue
            destaque = abs(t) < 1e-6
            painter.setPen(QPen(cor_zero if destaque else cor_texto))
            painter.drawText(QRectF(x - 24, y1 + 4, 48, 16),
                             Qt.AlignHCenter | Qt.AlignTop, texto)
        painter.setPen(QPen(cor_texto))
        painter.drawText(QRectF(x_final - 48, y1 + 4, 48, 16),
                         Qt.AlignRight | Qt.AlignTop, texto_final)

    @staticmethod
    def _formatar_tempo(segundos):
        sinal = "-" if segundos < 0 else ""
        s = int(round(abs(segundos)))
        return f"{sinal}{s // 60}:{s % 60:02d}"

    def _pintar_ocioso(self, painter, x0, y0, x1, y1):
        """Estado ocioso: a grade do eixo Y e a mensagem 'Aguardando gravação…'.

        A grade é desenhada mesmo sem dados para que a janela de configurações tenha um
        preview ao vivo real: antes o item ocioso pintava só a mensagem, então mexer em escala
        Y, grade ou rótulos parecia "não fazer nada" enquanto não houvesse uma gravação na
        tela — a origem da impressão de que os ajustes só às vezes reagiam. O eixo X fica de
        fora porque sem faixa carregada ele não tem duração para representar.
        """
        esc = self._escala_y if self._escala_y > 0 else _ESCALA_Y_PADRAO

        def py(v):
            return y0 + (esc - v) / (2 * esc) * (y1 - y0)

        painter.setFont(QFont(self._paleta.get("_display", "Segoe UI"), 8))
        if self._grade_visivel or self._rotulos_visiveis:
            self._pintar_grade_y(painter, x0, x1, esc, py)

        painter.setPen(QPen(self._cor("faint", "#6E7681")))
        painter.setFont(QFont(self._paleta.get("_display", "Segoe UI"), 10))
        painter.drawText(QRectF(x0, y0, x1 - x0, y1 - y0),
                         Qt.AlignCenter, "Aguardando gravação…")
