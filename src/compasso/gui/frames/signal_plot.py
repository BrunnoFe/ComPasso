# -*- coding: utf-8 -*-
"""
signal_plot.py
--------------
Gráfico do sinal do BITalino em tempo real, desenhado num ``tkinter.Canvas`` puro
(mesmo padrão do ``LiveEqualizer`` em ``canvas_widgets.py``): recebe as cores do
tema ativo por parâmetro e se anima sozinho via ``after`` enquanto existir.

Eixos:
  * X (tempo): FIXO de 0s à duração total da janela (``antecedencia_s`` da contagem
    regressiva + duração da música, definida por quem chama ``iniciar``). Os
    RÓTULOS mostram ``t - antecedencia_s`` — o eixo vai de ``-antecedencia_s``
    (ex.: -0:05) até a duração da música, com o ``0:00`` (início da música)
    DESTACADO por uma linha mais clara. Marcas com intervalo ADAPTATIVO ancoradas
    no 0; rótulos que ficariam colados nas bordas (início/fim da faixa) são
    descartados a favor delas (ver ``_escolher_rotulos_eixo_x``).
  * Y (sinal): eixo SEMPRE FIXO na escala configurada (default ``_ESCALA_Y_PADRAO_UV``,
    ±30 µV), com marcas/linhas de grade de 10 em 10 µV (``_PASSO_EIXO_Y_UV``). A escala
    é definida no construtor e ajustável pela janela "Configurações do Gráfico" (ver
    ``aplicar_configuracoes``), nunca automaticamente pelos dados — assim o trecho já
    desenhado da linha do sinal nunca precisa ser redesenhado por mudança de escala
    (ver "Desempenho").

Fluidez (linha e ponteiro sempre juntos, sem travar):
  * Um único RELÓGIO DE EXIBIÇÃO (``_tempo_exibicao``) rege ao mesmo tempo o
    ponteiro E o quanto da linha já foi revelado. Ele avança suave por quadro
    (~1 s/s) e fica ancorado à ponta dos dados recebidos (nunca a ultrapassa; nunca
    fica mais que ``_ATRASO_MAXIMO_EXIBICAO_S`` atrás dela). Como os dois usam o
    MESMO valor, o cursor cola na ponta da linha e ambos avançam juntos, mesmo com
    as amostras do LSL chegando em rajadas (a thread de aquisição não entrega em
    intervalos regulares).
  * A linha é DECIMADA de forma INCREMENTAL (uma coluna de pixel por vez, média dos
    pontos que caem nela) e recebe uma MÉDIA MÓVEL leve na exibição — o CSV/XLSX
    gravado pelo ``LSLRecorder`` mantém o dado bruto; a suavização é só visual.

Desempenho (por que não trava mais com músicas longas):
  * A linha do sinal é dividida em vários "BLOCOS" — itens de canvas independentes,
    um por faixa de ``_LARGURA_BLOCO_PX`` pixels (ver ``_desenhar_bloco``/
    ``_atualizar_blocos``). Um ``tkinter.Canvas`` repinta um item sempre que a
    região que ele ocupa fica suja; com a linha inteira num único item, mover o
    ponteiro (a cada quadro) sujava a largura inteira e forçava recalcular/repintar
    TODOS os pontos já desenhados — um custo que crescia com a duração da faixa até
    travar a interface perto do fim. Com blocos, só o bloco sob o ponteiro é
    redesenhado por quadro; os blocos já percorridos são "finalizados" (desenhados
    uma última vez, por completo) e nunca mais tocados — o custo por quadro fica
    CONSTANTE, independente da duração da faixa.
  * Itens de grade/eixos são recriados só quando a geometria ou a escala mudam
    (raro); nada de ``delete('all')`` a cada quadro.

Estados:
  * Ocioso: eixo Y discreto (só a linha de base) + mensagem "Aguardando gravação…".
  * Gravando: linha se formando + ponteiro + leitura do valor atual.
  * Concluído (``finalizar()``): registro inteiro permanece visível, sem mais
    alterações.

Thread-safety:
  ``adicionar_amostra()`` e ``definir_ponteiro_manual()`` são seguros para chamar
  de qualquer thread (ex.: a thread de aquisição do ``LSLRecorder``). As amostras
  entram numa fila e só são processadas no próximo quadro, já na thread da GUI.
  ``iniciar()``/``finalizar()``/``voltar_ao_ocioso()`` tocam o canvas diretamente —
  devem ser chamados na thread da GUI (o ``ExperimentRunner`` já faz isso via
  ``ctx.run_after``).

Uso típico no app:
    grafico = GraficoSinal(pai, paleta=theme.THEME,
                           familia_display=DISPLAY_FAMILY, familia_mono=MONO_FAMILY)
    grafico.pack(fill="both", expand=True)
    ...
    grafico.iniciar(duracao_s=antecedencia_s + player.get_length(),
                    antecedencia_s=antecedencia_s)
    ...                                                  # a cada amostra:
    grafico.adicionar_amostra(tempo_em_segundos, valor_do_sinal)  # (pode ser de outra thread)
    ...
    grafico.finalizar()                                  # fim da faixa
    grafico.voltar_ao_ocioso()                           # entre faixas / desconectar
"""

import math
import time
import bisect
import threading
from collections import deque

import tkinter as tk


# Intervalo (ms) entre quadros de animação (~60 fps). Com os blocos e a decimação
# incremental, cada quadro faz um trabalho ~constante, então esse ritmo fica barato
# mesmo perto do fim de uma música longa (ver docstring do módulo, seção "Desempenho").
_INTERVALO_QUADRO_MS = 16

# Janela (em colunas de pixel) da média móvel leve aplicada só na EXIBIÇÃO da linha
# (o CSV/XLSX gravado pelo LSLRecorder mantém o dado bruto). Suaviza o "serrilhado"
# do sinal sem achatar picos/vales reais.
_JANELA_SUAVIZACAO_COLUNAS = 5

# Atraso máximo (s) que o relógio de exibição pode ficar atrás da última amostra
# recebida. Funciona como um pequeno buffer que absorve as rajadas de amostras do
# LSL sem deixar a linha "pular" — ver _avancar_relogio_exibicao.
_ATRASO_MAXIMO_EXIBICAO_S = 0.4

# Largura (px) de cada "bloco" (pedaço independente) da linha do sinal. Ver a seção
# "Desempenho" na docstring do módulo para o porquê da divisão em blocos.
_LARGURA_BLOCO_PX = 200

# Espaço mínimo (px) entre dois rótulos de tempo do eixo X para não ficarem colados/
# sobrepostos. Estimativa de largura de um rótulo mono ("-0:05") a ~7px por caractere
# (mesma heurística usada na etiqueta do ponteiro, ver _reposicionar_etiqueta_ponteiro).
_ESPACO_MINIMO_ROTULO_X_PX = 34

# Escala Y padrão (µV, simétrica) usada quando nenhuma configuração é passada ao
# construtor. O eixo é SEMPRE fixo nessa escala (marcas de 10 em 10 µV, ver
# _PASSO_EIXO_Y_UV); a janela "Configurações do Gráfico" ajusta esse valor.
_ESCALA_Y_PADRAO_UV = 30.0

# Paleta de reserva (usada só se nenhuma paleta de tema for passada ao construtor).
_PALETA_RESERVA = {
    "bar_bg": "#161B22", "border": "#21262d", "text": "#E6EDF3",
    "muted": "#8B949E", "faint": "#6E7681", "faint2": "#4B525C",
    "accent": "#2DD4BF", "success": "#34D399",
}


# ---------------------------------------------------------------------------
# Conversão das configurações de exibição (janela "Configurações do Gráfico")
# ---------------------------------------------------------------------------
# Passo fixo (µV) entre as marcas/linhas de grade do eixo Y — sempre de 10 em 10.
_PASSO_EIXO_Y_UV = 10.0


def _limites_y_para_escala(escala, passo=_PASSO_EIXO_Y_UV):
    """Converte a escala Y simétrica na tupla ``(mín, máx, passo)`` do eixo.

    O ``passo`` (distância entre marcas/linhas de grade) depende do sensor ativo
    (ver constants.SENSOR_GRAPH_PARAMS): µV usa passo 10; mV usa 0,2/0,1 etc. Ex.:
    escala ±30 com passo 10 dá marcas -30/-20/.../30; escala ±1 com passo 0,2 dá
    marcas -1/-0,8/.../1."""
    try:
        escala = abs(float(escala))
    except (TypeError, ValueError):
        escala = 30.0
    if not math.isfinite(escala) or escala <= 0.0:
        escala = 30.0
    try:
        passo = abs(float(passo))
    except (TypeError, ValueError):
        passo = _PASSO_EIXO_Y_UV
    if not math.isfinite(passo) or passo <= 0.0:
        passo = _PASSO_EIXO_Y_UV
    return (-escala, escala, passo)


def _intervalo_ms_para_fps(fps):
    """Converte FPS no intervalo (ms) entre quadros, limitado a uma faixa sensata."""
    try:
        quadros_por_s = float(fps)
    except (TypeError, ValueError):
        quadros_por_s = 60.0
    quadros_por_s = min(max(quadros_por_s, 1.0), 120.0)
    return max(1, int(round(1000.0 / quadros_por_s)))


# ---------------------------------------------------------------------------
# Funções auxiliares de formatação de tempo do eixo X
# ---------------------------------------------------------------------------
# Intervalos permitidos para as marcas de tempo do eixo X (segundos).
_PASSOS_MARCA_TEMPO_PERMITIDOS = [1, 2, 5, 10, 15, 30, 60, 120, 300, 600]


def _escolher_passo_marca_tempo(duracao_total_s, quantidade_alvo_marcas=7):
    """Escolhe o intervalo entre marcas de tempo do eixo X para ~`quantidade_alvo_marcas` rótulos."""
    if duracao_total_s <= 0:
        return 1
    passo_aproximado = duracao_total_s / quantidade_alvo_marcas
    for passo in _PASSOS_MARCA_TEMPO_PERMITIDOS:
        if passo >= passo_aproximado:
            return passo
    return _PASSOS_MARCA_TEMPO_PERMITIDOS[-1]


def _formatar_mmss_com_sinal(segundos):
    """Formata segundos como ``mm:ss`` com sinal (ex.: ``-0:05``, ``0:00``, ``1:35``).

    Usado nos rótulos do eixo X e na etiqueta do ponteiro, que podem ficar negativos
    durante os segundos de "antecedência" da contagem regressiva (antes da música
    começar)."""
    negativo = segundos < -1e-9
    segundos_inteiros = abs(int(round(segundos)))
    formatado = "%d:%02d" % (segundos_inteiros // 60, segundos_inteiros % 60) #formatar como mm:ss
    return ("-" + formatado) if negativo else formatado


# ---------------------------------------------------------------------------
# Widget
# ---------------------------------------------------------------------------
class GraficoSinal(tk.Canvas):
    """Gráfico do sinal do BITalino em tempo real — ponteiro fluido, linha em blocos.

    Ver a docstring do módulo para os detalhes de design (eixos, fluidez, desempenho).
    """

    # margens internas do desenho (px), reservadas para rótulos dos eixos
    MARGEM_ESQUERDA = 52   # espaço p/ rótulos do eixo Y
    MARGEM_DIREITA = 12
    MARGEM_SUPERIOR = 16
    MARGEM_INFERIOR = 26   # espaço p/ rótulos do eixo X

    def __init__(self, master, paleta=None, familia_display="Segoe UI",
                 familia_mono="Consolas", unidade="µV",
                 mensagem_ociosa="Aguardando gravação…",
                 escala_y=_ESCALA_Y_PADRAO_UV, passo_eixo_y=_PASSO_EIXO_Y_UV,
                 suavizacao_ativa=True,
                 janela_suavizacao=_JANELA_SUAVIZACAO_COLUNAS, fps=None,
                 largura_linha=1.5, grade_visivel=True, rotulos_visiveis=True,
                 **kwargs_canvas):
        """
        :param master: widget pai (tipicamente o ``GraphFrame``).
        :param paleta: dict de cores do tema ativo (ver ``theme.py``); usa
            ``_PALETA_RESERVA`` se omitido.
        :param familia_display: família de fonte para textos de destaque (ex.: a
            mensagem do estado ocioso).
        :param familia_mono: família de fonte monoespaçada para rótulos numéricos.
        :param unidade: unidade exibida junto aos rótulos do eixo Y (ex.: ``"µV"``).
        :param mensagem_ociosa: texto mostrado no centro do canvas quando ocioso.

        Configurações de exibição (janela "Configurações do Gráfico"; defaults =
        valores hardcoded anteriores, ver ``aplicar_configuracoes``):

        :param escala_y: escala Y simétrica em µV (ex.: ``30`` -> eixo ±30 µV).
        :param suavizacao_ativa: liga a média móvel leve de exibição.
        :param janela_suavizacao: janela da média móvel (colunas de exibição).
        :param fps: quadros por segundo do gráfico (converte para o intervalo do loop);
            ``None`` mantém o intervalo padrão ``_INTERVALO_QUADRO_MS``.
        :param largura_linha: espessura (px) da linha do sinal.
        :param grade_visivel: desenha as linhas de grade (fora a linha do zero/início).
        :param rotulos_visiveis: desenha os rótulos numéricos/de tempo dos eixos.
        """
        cores = paleta or _PALETA_RESERVA
        super().__init__(master, bg=cores["bar_bg"], highlightthickness=0, bd=0,
                         **kwargs_canvas)
        self._cores = cores
        self.familia_display = familia_display
        self.familia_mono = familia_mono
        self.unidade = unidade
        self.mensagem_ociosa = mensagem_ociosa

        # --- configurações de exibição (ajustáveis em runtime; ver aplicar_configuracoes) ---
        self._escala_y = escala_y
        # passo entre marcas do eixo Y — depende do sensor ativo (µV=10, mV=0,2/0,1, ...).
        self._passo_eixo_y = passo_eixo_y
        self._limites_eixo_y_padrao = _limites_y_para_escala(escala_y, passo_eixo_y)
        self._suavizacao_ativa = bool(suavizacao_ativa)
        self._janela_suavizacao = max(1, int(janela_suavizacao))
        self._intervalo_quadro_ms = _INTERVALO_QUADRO_MS if fps is None else _intervalo_ms_para_fps(fps)
        self._largura_linha = float(largura_linha)
        self._grade_visivel = bool(grade_visivel)
        self._rotulos_visiveis = bool(rotulos_visiveis)

        # --- amostras acumuladas da faixa atual ---
        self._amostras_pendentes = deque()   # fila (tempo_s, valor) vinda de qualquer thread
        self._trava_amostras_pendentes = threading.Lock()
        self._tempos_amostras = []            # tempos acumulados (s), em ordem de chegada
        self._valores_amostras = []           # valores acumulados, mesmo índice dos tempos
        self._duracao_total_s = 0.0           # duração da janela (antecedência + música)
        self._gravando = False
        self._finalizado = False
        self._ultimo_valor = None             # última amostra recebida (leitura ao vivo externa)

        # estatísticas incrementais da janela da MÚSICA (amostras com tempo >= antecedencia_s),
        # do INICIO_MUSICA até o instante atual — alimentam o rótulo de valor (média/mín/máx/DP).
        # Média/variância por Welford (estável); mín/máx acompanhados à parte.
        self._reiniciar_estatisticas_janela()

        # --- relógio de exibição: rege o ponteiro E até onde a linha foi revelada ---
        # (ver docstring do módulo, seção "Fluidez"). _antecedencia_s = duração do
        # trecho inicial de contagem regressiva mostrado antes da música; os rótulos
        # do eixo X mostram tempo relativo ao início da música (t - antecedencia_s).
        self._antecedencia_s = 0.0
        self._tempo_exibicao = 0.0
        self._relogio_ultimo_quadro = None
        self._ponteiro_manual = None          # só usado por demos/testes em tempo acelerado

        self._reiniciar_estado_desenho()

        self._id_after_animacao = None
        self.bind("<Configure>", lambda evento: self._solicitar_redesenho_completo())
        self._executar_quadro_animacao()

    def _reiniciar_estado_desenho(self):
        """Zera a decimação incremental e todos os itens de canvas persistentes.

        Chamado ao iniciar uma nova faixa (``iniciar``), voltar ao ocioso
        (``voltar_ao_ocioso``) e sempre que a geometria/escala força uma reconstrução."""
        # decimação incremental por coluna de pixel (ver _processar_novas_amostras)
        self._baldes_pixel = {}                # coluna de pixel -> [soma_valores, contagem]
        self._ordem_baldes_pixel = []          # colunas em ordem crescente (== de inserção)
        self._quantidade_amostras_processadas = 0  # nº de amostras já decimadas
        self._chave_geometria_baldes = None    # (x0, x1, duração) — muda -> refaz os baldes

        # cache do último redesenho estrutural, p/ saber quando refazer (ver _desenhar_quadro)
        self._ultima_escala_eixo_y = None      # (mínimo, máximo, passo) desenhados
        self._ultimo_retangulo_desenho = None  # (x0, y0, x1, y1) desenhados
        self._ultimo_estado_ocioso = None      # se o último quadro estava ocioso
        self._precisa_redesenho_completo = True  # força reconstrução da grade/eixos/blocos

        self._limites_eixo_y = self._limites_eixo_y_padrao  # (mín, máx, passo) — fixo na escala configurada

        # blocos da linha do sinal (ver docstring do módulo, seção "Desempenho")
        self._itens_blocos = {}                # índice do bloco -> id do item de linha
        self._indice_bloco_ativo = -1          # bloco onde o ponteiro está agora
        self._ultimo_corte_px_redesenhado = -1  # última coluna de pixel já processada
                                                 # (evita retrabalho a cada quadro)

        self._itens_ponteiro = ()              # (linha, ponto, retângulo da etiqueta, texto)

    def _reiniciar_estatisticas_janela(self):
        """Zera os acumuladores de estatística da janela da música (chamado por faixa)."""
        self._est_contagem = 0
        self._est_media = 0.0        # média corrente (Welford)
        self._est_m2 = 0.0           # soma dos quadrados dos desvios (Welford) -> variância
        self._est_minimo = None
        self._est_maximo = None

    def _acumular_estatistica(self, valor):
        """Atualiza os acumuladores da janela com uma amostra da música (Welford + mín/máx)."""
        self._est_contagem += 1
        delta = valor - self._est_media
        self._est_media += delta / self._est_contagem
        self._est_m2 += delta * (valor - self._est_media)
        if self._est_minimo is None or valor < self._est_minimo:
            self._est_minimo = valor
        if self._est_maximo is None or valor > self._est_maximo:
            self._est_maximo = valor

    def _solicitar_redesenho_completo(self):
        """Marca que o próximo quadro deve reconstruir grade/eixos/blocos do zero."""
        self._precisa_redesenho_completo = True

    # -- API pública (thread-safety indicada em cada método) --------------
    def iniciar(self, duracao_s, antecedencia_s=0):
        """Inicia a exibição de uma nova faixa: fixa o eixo X e limpa os dados anteriores.

        Chamar na thread da GUI (o ``ExperimentRunner`` faz isso via ``ctx.run_after``).

        :param duracao_s: duração total da janela do eixo X, em segundos — soma da
            antecedência da contagem regressiva com a duração da música.
        :param antecedencia_s: segundos iniciais que são a antecedência da contagem
            regressiva. Os rótulos do eixo X mostram ``t - antecedencia_s``: o início
            da música (posição interna ``t = antecedencia_s``) vira ``0:00``, e o
            começo da janela (``t = 0``) vira ``-antecedencia_s`` (ex.: ``-0:05``).
        """
        with self._trava_amostras_pendentes:
            self._amostras_pendentes.clear()
        self._tempos_amostras, self._valores_amostras = [], []
        self._duracao_total_s = float(duracao_s) if duracao_s and duracao_s > 0 else 1.0
        self._antecedencia_s = float(antecedencia_s) if antecedencia_s and antecedencia_s > 0 else 0.0
        self._ultimo_valor = None
        self._ponteiro_manual = None
        self._tempo_exibicao = 0.0
        self._relogio_ultimo_quadro = time.monotonic()
        self._gravando = True
        self._finalizado = False
        self._reiniciar_estatisticas_janela()
        self._reiniciar_estado_desenho()
        self._desenhar_quadro()

    def adicionar_amostra(self, tempo_s, valor):
        """Enfileira uma amostra ``(tempo_s, valor)`` para exibição no próximo quadro.

        Thread-safe: seguro para chamar da thread de aquisição do ``LSLRecorder``.
        Amostras não numéricas ou não finitas são silenciosamente descartadas.
        """
        try:
            tempo_s = float(tempo_s)
            valor = float(valor)
        except (TypeError, ValueError):
            return
        if not (math.isfinite(tempo_s) and math.isfinite(valor)):
            return
        with self._trava_amostras_pendentes:
            self._amostras_pendentes.append((tempo_s, valor))

    def definir_ponteiro_manual(self, tempo_s):
        """Sobrepõe manualmente a posição do ponteiro (s), ignorando o relógio de exibição.

        Thread-safe. Não é usado pelo app real (o ponteiro segue o relógio de
        exibição desde ``iniciar``); existe para demos/testes em tempo acelerado."""
        try:
            self._ponteiro_manual = float(tempo_s)
        except (TypeError, ValueError):
            pass

    def finalizar(self):
        """Marca o fim da faixa: o registro completo permanece visível, sem mais alterações."""
        self._gravando = False
        self._finalizado = True
        self._solicitar_redesenho_completo()

    def voltar_ao_ocioso(self):
        """Limpa os dados e volta ao estado ocioso ("Aguardando gravação…")."""
        with self._trava_amostras_pendentes:
            self._amostras_pendentes.clear()
        self._tempos_amostras, self._valores_amostras = [], []
        self._gravando = False
        self._finalizado = False
        self._ultimo_valor = None
        self._tempo_exibicao = 0.0
        self._relogio_ultimo_quadro = None
        self._ponteiro_manual = None
        self._reiniciar_estatisticas_janela()
        self._reiniciar_estado_desenho()
        self._desenhar_quadro()

    def aplicar_configuracoes(self, settings):
        """Aplica novas configurações de exibição (preview ao vivo / persistência).

        Chamar na thread da GUI. A **escala Y** só é reaplicada quando NÃO se está
        gravando (fica fixa durante uma faixa em andamento — muda só na próxima
        ``iniciar()``); as demais valem imediatamente. Força um redesenho completo
        para refletir a nova escala/grade/rótulos/espessura/suavização.

        :param settings: dict com qualquer subconjunto das chaves ``y_scale``,
            ``smoothing_enabled``, ``smoothing_window``, ``fps``, ``line_width``,
            ``grid_visible``, ``axis_labels_visible``.
        """
        if not isinstance(settings, dict):
            return
        # unidade e passo do eixo Y vêm do sensor ativo (ver graph_frame.aplicar_sensor_ao_grafico).
        if "unidade" in settings:
            self.unidade = settings["unidade"]
        recomputar_y = False
        if "y_step" in settings:
            self._passo_eixo_y = settings["y_step"]
            recomputar_y = True
        if "y_scale" in settings:
            self._escala_y = settings["y_scale"]
            recomputar_y = True
        if recomputar_y:
            self._limites_eixo_y_padrao = _limites_y_para_escala(self._escala_y, self._passo_eixo_y)
            if not self._gravando:
                self._limites_eixo_y = self._limites_eixo_y_padrao
        if "smoothing_enabled" in settings:
            self._suavizacao_ativa = bool(settings["smoothing_enabled"])
        if "smoothing_window" in settings:
            try:
                self._janela_suavizacao = max(1, int(settings["smoothing_window"]))
            except (TypeError, ValueError):
                pass
        if "fps" in settings:
            self._intervalo_quadro_ms = _intervalo_ms_para_fps(settings["fps"])
        if "line_width" in settings:
            try:
                self._largura_linha = float(settings["line_width"])
            except (TypeError, ValueError):
                pass
        if "grid_visible" in settings:
            self._grade_visivel = bool(settings["grid_visible"])
        if "axis_labels_visible" in settings:
            self._rotulos_visiveis = bool(settings["axis_labels_visible"])
        self._solicitar_redesenho_completo()

    def _janela_suavizacao_efetiva(self):
        """Janela da média móvel de exibição, ou 1 (sem suavização) quando desligada."""
        return self._janela_suavizacao if self._suavizacao_ativa else 1

    @property
    def valor_atual(self):
        """Última amostra recebida (ou ``None`` se nenhuma), para um leitor externo opcional."""
        return self._ultimo_valor

    @property
    def valor_medio(self):
        """Média das amostras da janela da música até agora (``None`` se ainda não há)."""
        return self._est_media if self._est_contagem > 0 else None

    @property
    def desvio_padrao(self):
        """Desvio-padrão populacional da janela da música (``None`` se < 2 amostras)."""
        if self._est_contagem < 2:
            return None
        return math.sqrt(self._est_m2 / self._est_contagem)

    @property
    def valor_minimo(self):
        """Menor valor da janela da música até agora (``None`` se ainda não há)."""
        return self._est_minimo

    @property
    def valor_maximo(self):
        """Maior valor da janela da música até agora (``None`` se ainda não há)."""
        return self._est_maximo

    def destroy(self):
        """Cancela o loop de animação antes de destruir o widget (evita ``after`` órfão).

        Sobrescreve ``tk.Canvas.destroy`` — nome mantido em inglês porque o Tkinter
        chama este método automaticamente ao destruir o widget pai."""
        if self._id_after_animacao:
            try:
                self.after_cancel(self._id_after_animacao)
            except Exception:
                pass
        super().destroy()

    # -- consumo da fila de amostras (thread da GUI) -----------------------
    def _processar_amostras_pendentes(self):
        """Move as amostras enfileiradas por `adicionar_amostra()` para os arrays acumulados.

        Chamado uma vez por quadro, na thread da GUI. Guarda também a última amostra
        recebida para a leitura ao vivo do valor atual."""
        with self._trava_amostras_pendentes:
            if not self._amostras_pendentes:
                return
            pendentes = list(self._amostras_pendentes)
            self._amostras_pendentes.clear()
        for tempo_s, valor in pendentes:
            self._tempos_amostras.append(tempo_s)
            self._valores_amostras.append(valor)
            self._ultimo_valor = valor
            # estatísticas só a partir do início da música (após a antecedência da contagem)
            if tempo_s >= self._antecedencia_s:
                self._acumular_estatistica(valor)

    # -- loop de animação ---------------------------------------------------
    def _executar_quadro_animacao(self):
        """Um quadro do loop de animação: processa amostras, redesenha, reagenda.

        Envolvido em ``try/except tk.TclError`` porque o widget pode ter sido
        destruído entre o agendamento e a execução deste quadro (ex.: troca de tema
        reconstruindo a UI) — nesse caso simplesmente paramos de reagendar."""
        try:
            self._processar_amostras_pendentes()
            self._desenhar_quadro()
            self._id_after_animacao = self.after(self._intervalo_quadro_ms, self._executar_quadro_animacao)
        except tk.TclError:
            return

    # -- geometria ------------------------------------------------------
    def _calcular_retangulo_desenho(self):
        """Retângulo interno de desenho ``(x0, y0, x1, y1)``, descontando as margens."""
        largura = self.winfo_width() or int(self["width"] or 600)
        altura = self.winfo_height() or int(self["height"] or 220)
        return (self.MARGEM_ESQUERDA, self.MARGEM_SUPERIOR,
                largura - self.MARGEM_DIREITA, altura - self.MARGEM_INFERIOR)

    # -- decimação incremental por coluna de pixel ------------------------
    def _processar_novas_amostras(self, x0, x1):
        """Distribui as amostras ainda não processadas em "baldes" por coluna de pixel.

        Cada amostra cai numa coluna de pixel (proporcional a ``tempo / duração``); um
        balde acumula soma e contagem para permitir a média dos pontos que caem nele.
        Só percorre amostras novas (a partir de ``_quantidade_amostras_processadas``)
        — o custo por quadro é O(amostras novas), não O(total já acumulado).

        Se a geometria X ou a duração mudou (ex.: redimensionamento da janela), os
        baldes são reconstruídos do zero a partir de todas as amostras acumuladas."""
        chave_geometria = (x0, x1, self._duracao_total_s)
        if chave_geometria != self._chave_geometria_baldes:
            self._chave_geometria_baldes = chave_geometria
            self._baldes_pixel = {}
            self._ordem_baldes_pixel = []
            self._quantidade_amostras_processadas = 0

        duracao = self._duracao_total_s if self._duracao_total_s > 0 else 1.0
        largura_desenho = x1 - x0
        for i in range(self._quantidade_amostras_processadas, len(self._tempos_amostras)):
            fracao_tempo = self._tempos_amostras[i] / duracao
            if fracao_tempo < 0.0:
                fracao_tempo = 0.0
            elif fracao_tempo > 1.0:
                fracao_tempo = 1.0
            coluna_pixel = int(x0 + fracao_tempo * largura_desenho)
            balde = self._baldes_pixel.get(coluna_pixel)
            if balde is None:
                self._baldes_pixel[coluna_pixel] = [self._valores_amostras[i], 1]
                self._ordem_baldes_pixel.append(coluna_pixel)
            else:
                balde[0] += self._valores_amostras[i]
                balde[1] += 1
        self._quantidade_amostras_processadas = len(self._tempos_amostras)

    # -- relógio de exibição (rege o ponteiro e a revelação da linha) -----
    def _avancar_relogio_exibicao(self):
        """Avança ``_tempo_exibicao`` suavemente, ancorado à ponta dos dados recebidos.

        Regras: avança ~1 segundo por segundo de tempo real (fluido, independente da
        cadência de chegada das amostras); nunca ultrapassa a última amostra recebida
        (``_tempos_amostras[-1]``, para não desenhar além do que já chegou); e não
        fica mais que ``_ATRASO_MAXIMO_EXIBICAO_S`` atrás dela (limita o tamanho do
        "buffer" que absorve rajadas de amostras). Como o ponteiro e o corte de
        revelação da linha usam o mesmo ``_tempo_exibicao``, os dois sempre avançam
        sincronizados."""
        agora = time.monotonic()
        if self._relogio_ultimo_quadro is None:
            self._relogio_ultimo_quadro = agora
        tempo_decorrido = min(max(agora - self._relogio_ultimo_quadro, 0.0), 0.05)
        self._relogio_ultimo_quadro = agora

        if self._ponteiro_manual is not None:
            novo_tempo_exibicao = self._ponteiro_manual
        elif self._finalizado:
            novo_tempo_exibicao = self._duracao_total_s
        else:
            tempo_ultima_amostra = self._tempos_amostras[-1] if self._tempos_amostras else 0.0
            novo_tempo_exibicao = min(self._tempo_exibicao + tempo_decorrido, tempo_ultima_amostra)
            if tempo_ultima_amostra - novo_tempo_exibicao > _ATRASO_MAXIMO_EXIBICAO_S:
                novo_tempo_exibicao = tempo_ultima_amostra - _ATRASO_MAXIMO_EXIBICAO_S

        self._tempo_exibicao = min(max(novo_tempo_exibicao, 0.0), self._duracao_total_s)

    # -- eixo X: escolha dos rótulos de tempo -------------------------------
    def _escolher_rotulos_eixo_x(self, antecedencia_s, duracao_musica_s, largura_desenho_px):
        """Escolhe quais rótulos de tempo mostrar no eixo X, evitando sobreposição.

        Sempre inclui os "rótulos obrigatórios" (bordas da janela e início da
        música): ``-antecedencia_s`` (começo da janela), ``0.0`` (início da música,
        destacado) e ``duracao_musica_s`` (fim da música). Os demais são as marcas
        regulares do intervalo escolhido por ``_escolher_passo_marca_tempo``.

        Um rótulo regular é descartado quando fica mais perto que
        ``_ESPACO_MINIMO_ROTULO_X_PX`` (convertido para segundos pela largura do
        gráfico) de um rótulo obrigatório — ex.: numa música de 26s, a marca regular
        "0:25" ficaria colada ao rótulo final "0:26" e é descartada, sobrando só o
        rótulo da música. Duas marcas regulares vizinhas também são decoladas pelo
        mesmo critério.

        :return: lista ordenada de rótulos (em segundos, já relativos ao início da
            música — i.e. o que será formatado por ``_formatar_mmss_com_sinal``).
        """
        rotulos_obrigatorios = {round(-antecedencia_s, 6), 0.0, round(duracao_musica_s, 6)}

        passo_marca = _escolher_passo_marca_tempo(self._duracao_total_s)
        indice_marca = math.ceil((-antecedencia_s) / passo_marca - 1e-9)
        rotulos_regulares = set()
        while indice_marca * passo_marca <= duracao_musica_s + 1e-6:
            rotulos_regulares.add(round(indice_marca * passo_marca, 6))
            indice_marca += 1

        espaco_minimo_s = 0.0
        if largura_desenho_px > 0:
            espaco_minimo_s = (_ESPACO_MINIMO_ROTULO_X_PX / largura_desenho_px) * self._duracao_total_s

        rotulos_selecionados = list(rotulos_obrigatorios)
        for rotulo in sorted(rotulos_regulares):
            if rotulo in rotulos_obrigatorios:
                continue
            muito_perto_de_obrigatorio = any(
                abs(rotulo - obrigatorio) < espaco_minimo_s for obrigatorio in rotulos_obrigatorios)
            muito_perto_de_selecionado = (
                rotulos_selecionados
                and abs(rotulo - max(rotulos_selecionados)) < espaco_minimo_s)
            if muito_perto_de_obrigatorio or muito_perto_de_selecionado:
                continue
            rotulos_selecionados.append(rotulo)

        return sorted(rotulos_selecionados)

    # -- desenho -----------------------------------------------------------
    def _desenhar_quadro(self):
        """Desenha um quadro: atualiza dados/relógio e decide entre redesenho completo
        ou apenas os itens que mudam a cada quadro (bloco atual + ponteiro).

        Um redesenho COMPLETO (grade, eixos, todos os blocos) só acontece quando a
        geometria, a escala Y ou o estado ocioso/gravando mudam — eventos raros. No
        caminho comum (quadro a quadro durante a gravação), só o bloco sob o
        ponteiro é atualizado (e só quando o corte realmente cruza para uma nova
        coluna de pixel); o ponteiro em si é sempre reposicionado, garantindo o
        deslize fluido."""
        try:
            x0, y0, x1, y1 = self._calcular_retangulo_desenho()
        except tk.TclError:
            return
        if x1 - x0 < 20 or y1 - y0 < 20:
            return  # canvas ainda não tem um tamanho útil (ex.: primeiro layout)

        ocioso = not self._gravando and not self._finalizado

        if not ocioso:
            self._processar_novas_amostras(x0, x1)
            self._avancar_relogio_exibicao()

        # eixo Y sempre fixo na escala configurada; ocioso usa um eixo discreto simples
        # (só a linha de base, sem valores).
        minimo_y, maximo_y, passo_y = (-1.0, 1.0, 1.0) if ocioso else self._limites_eixo_y

        retangulo_desenho = (x0, y0, x1, y1)
        escala_eixo_y = (minimo_y, maximo_y, passo_y)

        def valor_para_y(valor):
            return y1 - (valor - minimo_y) / (maximo_y - minimo_y) * (y1 - y0)

        def tempo_para_x(tempo_s):
            duracao = self._duracao_total_s if self._duracao_total_s > 0 else 1.0
            fracao = tempo_s / duracao
            fracao = min(max(fracao, 0.0), 1.0)
            return x0 + fracao * (x1 - x0)

        precisa_redesenho = (
            self._precisa_redesenho_completo
            or retangulo_desenho != self._ultimo_retangulo_desenho
            or escala_eixo_y != self._ultima_escala_eixo_y
            or ocioso != self._ultimo_estado_ocioso)

        if precisa_redesenho:
            self._ultimo_retangulo_desenho = retangulo_desenho
            self._ultima_escala_eixo_y = escala_eixo_y
            self._ultimo_estado_ocioso = ocioso
            self._precisa_redesenho_completo = False
            self._redesenhar_tudo(x0, y0, x1, y1, minimo_y, maximo_y, passo_y, ocioso,
                                  valor_para_y, tempo_para_x)
        elif not ocioso:
            coluna_corte = int(tempo_para_x(self._tempo_exibicao))
            if coluna_corte != self._ultimo_corte_px_redesenhado:
                self._atualizar_blocos(x0, tempo_para_x, valor_para_y)
                self._ultimo_corte_px_redesenhado = coluna_corte
            self._reposicionar_ponteiro(x0, y0, x1, y1, tempo_para_x)

    def _redesenhar_tudo(self, x0, y0, x1, y1, minimo_y, maximo_y, passo_y, ocioso,
                        valor_para_y, tempo_para_x):
        """Reconstrói a grade, os eixos, os rótulos e todos os blocos/itens do canvas.

        Chamado só quando algo estrutural muda (geometria, escala Y ou transição
        ocioso/gravando) — ver ``_desenhar_quadro``. Substitui inteiramente o
        conteúdo do canvas (``delete('all')``)."""
        self.delete("all")
        self._itens_blocos = {}
        self._indice_bloco_ativo = -1
        self._itens_ponteiro = ()
        cores = self._cores
        cor_grade_fraca = self._misturar_cores(cores["bar_bg"], cores["border"], 0.5)

        self._desenhar_eixo_y(x0, y0, x1, y1, minimo_y, maximo_y, passo_y, ocioso,
                             valor_para_y, cores, cor_grade_fraca)

        if not ocioso and self._duracao_total_s > 0:
            self._desenhar_eixo_x(x0, y0, x1, y1, tempo_para_x, cores, cor_grade_fraca)

        if ocioso:
            self.create_text((x0 + x1) / 2, (y0 + y1) / 2, text=self.mensagem_ociosa,
                             fill=cores["faint2"], font=(self.familia_display, 12))
            return

        self._criar_itens_ponteiro(x0, y0, y1, cores)

        # redesenha todos os blocos já percorridos (1º quadro, resize ou mudança de configuração)
        self._redesenhar_todos_blocos(x0, tempo_para_x, valor_para_y)
        self._ultimo_corte_px_redesenhado = int(tempo_para_x(self._tempo_exibicao))
        self._reposicionar_ponteiro(x0, y0, x1, y1, tempo_para_x)

    def _desenhar_eixo_y(self, x0, y0, x1, y1, minimo_y, maximo_y, passo_y, ocioso,
                        valor_para_y, cores, cor_grade_fraca):
        """Desenha as linhas de grade horizontais e os rótulos numéricos do eixo Y.

        A unidade (ex.: "µV") é anexada ao rótulo da marca MAIS ALTA em vez de
        desenhada como um texto separado — antes, os dois ficavam na mesma posição
        vertical (topo do gráfico) e se sobrepunham visualmente (bug corrigido)."""
        if ocioso:
            self.create_line(x0, y1, x1, y1, fill=cor_grade_fraca)
            if self._rotulos_visiveis:
                self.create_text(x0 - 8, (y0 + y1) / 2, text="0", anchor="e",
                                 fill=cores["faint2"], font=(self.familia_mono, 10))
            return

        limite_linhas_grade = 40  # proteção contra loop infinito por erro de ponto flutuante
        quantidade_linhas_grade = 0
        valor_y = minimo_y
        while valor_y <= maximo_y + 1e-6 and quantidade_linhas_grade < limite_linhas_grade:
            y_linha_grade = valor_para_y(valor_y)
            linha_zero = abs(valor_y) < 1e-6
            linha_topo = abs(valor_y - maximo_y) < 1e-6
            # linha do zero sempre desenhada (base de referência); demais linhas de grade
            # só quando a grade está ligada.
            if linha_zero or self._grade_visivel:
                self.create_line(x0, y_linha_grade, x1, y_linha_grade,
                                 fill=(cores["border"] if linha_zero else cor_grade_fraca),
                                 width=(2 if linha_zero else 1))
            if self._rotulos_visiveis:
                texto_rotulo = self._formatar_valor_y(valor_y)
                if linha_topo:
                    texto_rotulo = f"{texto_rotulo} {self.unidade}"  # unidade só na marca do topo
                self.create_text(x0 - 8, y_linha_grade, text=texto_rotulo, anchor="e",
                                 fill=cores["faint"], font=(self.familia_mono, 10))
            valor_y += passo_y
            quantidade_linhas_grade += 1

    def _desenhar_eixo_x(self, x0, y0, x1, y1, tempo_para_x, cores, cor_grade_fraca):
        """Desenha as marcas verticais e os rótulos de tempo do eixo X.

        Rótulos são relativos ao início da música (``t - antecedência``); o rótulo
        ``0:00`` (início da música) recebe uma linha vertical mais clara para se
        destacar. A lista de rótulos já vem filtrada por ``_escolher_rotulos_eixo_x``
        para evitar sobreposição entre marcas vizinhas."""
        duracao_musica_s = self._duracao_total_s - self._antecedencia_s
        largura_desenho_px = x1 - x0
        for rotulo in self._escolher_rotulos_eixo_x(self._antecedencia_s, duracao_musica_s,
                                                    largura_desenho_px):
            tempo_eixo = rotulo + self._antecedencia_s  # volta à coordenada interna do eixo
            if tempo_eixo < -1e-6 or tempo_eixo > self._duracao_total_s + 1e-6:
                continue
            x_rotulo = tempo_para_x(tempo_eixo)
            inicio_musica = abs(rotulo) < 1e-6
            # marca do início da música sempre desenhada (referência 0:00); demais linhas
            # verticais só quando a grade está ligada.
            if inicio_musica or self._grade_visivel:
                self.create_line(x_rotulo, y0, x_rotulo, y1,
                                 fill=(cores["faint"] if inicio_musica else cor_grade_fraca),
                                 width=(2 if inicio_musica else 1))
            if self._rotulos_visiveis:
                self.create_text(x_rotulo, y1 + 13, text=_formatar_mmss_com_sinal(rotulo),
                                 anchor="n",
                                 fill=(cores["muted"] if inicio_musica else cores["faint"]),
                                 font=(self.familia_mono, 10))

    def _criar_itens_ponteiro(self, x0, y0, y1, cores):
        """Cria os itens persistentes do ponteiro (linha, ponto e etiqueta de tempo)."""
        linha_ponteiro = self.create_line(x0, y0, x0, y1, fill=cores["text"], dash=(3, 3))
        ponto_ponteiro = self.create_oval(x0 - 3, y0 - 3, x0 + 3, y0 + 3,
                                          fill=cores["text"], outline="")
        fundo_etiqueta = cores.get("accent_tint", cores["bar_bg"])
        retangulo_etiqueta = self.create_rectangle(0, 0, 0, 0, fill=fundo_etiqueta,
                                                   outline=cores["accent"], width=1)
        texto_etiqueta = self.create_text(0, 0, text="", fill=cores["accent"],
                                          font=(self.familia_mono, 9))
        self._itens_ponteiro = (linha_ponteiro, ponto_ponteiro, retangulo_etiqueta, texto_etiqueta)

    # -- linha do sinal em blocos (ver docstring do módulo, seção "Desempenho") ---
    def _indice_bloco_para_x(self, x_pixel, x0):
        """Índice do bloco (faixa de ``_LARGURA_BLOCO_PX`` pixels) que contém `x_pixel`."""
        indice = int((x_pixel - x0) / _LARGURA_BLOCO_PX)
        return max(indice, 0)

    def _redesenhar_todos_blocos(self, x0, tempo_para_x, valor_para_y):
        """Redesenha do zero todos os blocos até o ativo (1º quadro, resize ou mudança de config)."""
        corte_pixel = tempo_para_x(self._tempo_exibicao)
        bloco_ativo = self._indice_bloco_para_x(corte_pixel, x0)
        for indice_bloco in range(bloco_ativo):
            fim_bloco_px = x0 + (indice_bloco + 1) * _LARGURA_BLOCO_PX
            self._desenhar_bloco(indice_bloco, x0, fim_bloco_px, valor_para_y, final=True)
        self._desenhar_bloco(bloco_ativo, x0, corte_pixel, valor_para_y, final=False)
        self._indice_bloco_ativo = bloco_ativo

    def _atualizar_blocos(self, x0, tempo_para_x, valor_para_y):
        """Atualiza só o bloco ativo a cada quadro; finaliza blocos que o ponteiro já passou.

        Um bloco "finalizado" é desenhado por completo uma última vez e nunca mais
        tocado — é isso que mantém o custo por quadro constante (ver docstring do
        módulo)."""
        corte_pixel = tempo_para_x(self._tempo_exibicao)
        bloco_ativo = self._indice_bloco_para_x(corte_pixel, x0)
        if self._indice_bloco_ativo < 0:
            self._indice_bloco_ativo = bloco_ativo

        while self._indice_bloco_ativo < bloco_ativo:
            indice_bloco = self._indice_bloco_ativo
            fim_bloco_px = x0 + (indice_bloco + 1) * _LARGURA_BLOCO_PX
            self._desenhar_bloco(indice_bloco, x0, fim_bloco_px, valor_para_y, final=True)
            self._indice_bloco_ativo += 1

        # bloco ativo: revelado até o corte atual (a ponta acompanha o ponteiro)
        self._desenhar_bloco(bloco_ativo, x0, corte_pixel, valor_para_y, final=False)

    def _desenhar_bloco(self, indice_bloco, x0, revelar_ate_px, valor_para_y, final):
        """Desenha (ou atualiza) o item de linha de um bloco, revelado até `revelar_ate_px`.

        Inclui um "halo" de colunas vizinhas fora do bloco para a média móvel não
        quebrar nas emendas entre blocos, e um ponto de ponte para não haver costura
        visível: blocos finalizados se conectam à primeira coluna do próximo bloco; o
        bloco ativo estende sua última coluna até `revelar_ate_px` para coincidir
        exatamente com o ponteiro (ver ``_reposicionar_ponteiro``).

        :param indice_bloco: índice do bloco (determina a faixa de pixels e o item persistente).
        :param final: True para um bloco já ultrapassado pelo ponteiro (desenho
            definitivo, com ponte para o próximo bloco); False para o bloco ativo
            (desenho parcial, com a ponta estendida até o ponteiro).
        """
        colunas_pixel = self._ordem_baldes_pixel
        inicio_bloco_px = int(x0 + indice_bloco * _LARGURA_BLOCO_PX)
        fim_bloco_px = int(revelar_ate_px)
        indice_inicio = bisect.bisect_left(colunas_pixel, inicio_bloco_px)
        indice_fim = bisect.bisect_right(colunas_pixel, fim_bloco_px)
        if indice_fim - indice_inicio < 1:
            self._ocultar_bloco(indice_bloco)
            return

        janela_suavizacao = self._janela_suavizacao_efetiva()
        colunas_halo = janela_suavizacao // 2
        inicio_halo = max(0, indice_inicio - colunas_halo)
        fim_halo = min(len(colunas_pixel), indice_fim + colunas_halo)
        colunas_com_halo = colunas_pixel[inicio_halo:fim_halo]
        valores_brutos = [self._baldes_pixel[px][0] / self._baldes_pixel[px][1]
                          for px in colunas_com_halo]
        valores_suavizados = self._aplicar_media_movel(valores_brutos, janela_suavizacao)

        coordenadas = []
        for k in range(indice_inicio - inicio_halo, indice_fim - inicio_halo):
            coordenadas.append(colunas_com_halo[k])
            coordenadas.append(valor_para_y(valores_suavizados[k]))

        if final and indice_fim < len(colunas_pixel):
            px_ponte = colunas_pixel[indice_fim]
            valor_ponte = self._baldes_pixel[px_ponte][0] / self._baldes_pixel[px_ponte][1]
            coordenadas.append(px_ponte)
            coordenadas.append(valor_para_y(valor_ponte))
        elif not final and coordenadas:
            ultimo_y = coordenadas[-1]
            coordenadas.append(revelar_ate_px)
            coordenadas.append(ultimo_y)

        if len(coordenadas) < 4:
            self._ocultar_bloco(indice_bloco)
            return

        item_existente = self._itens_blocos.get(indice_bloco)
        if item_existente is None:
            self._itens_blocos[indice_bloco] = self.create_line(
                *coordenadas, fill=self._cores["accent"], width=self._largura_linha,
                joinstyle=tk.ROUND, capstyle=tk.ROUND, smooth=False)
        else:
            self.coords(item_existente, *coordenadas)
            self.itemconfigure(item_existente, width=self._largura_linha, state="normal")

    def _ocultar_bloco(self, indice_bloco):
        """Oculta o item de um bloco sem pontos suficientes para desenhar (ex.: bloco vazio)."""
        item = self._itens_blocos.get(indice_bloco)
        if item is not None:
            self.itemconfigure(item, state="hidden")

    @staticmethod
    def _aplicar_media_movel(valores, tamanho_janela):
        """Média móvel centrada (janela `tamanho_janela`) via somas de prefixo — O(n)."""
        quantidade = len(valores)
        if tamanho_janela <= 1 or quantidade == 0:
            return valores
        metade_janela = tamanho_janela // 2
        somas_prefixo = [0.0]
        for valor in valores:
            somas_prefixo.append(somas_prefixo[-1] + valor)
        resultado = []
        for i in range(quantidade):
            inicio = max(0, i - metade_janela)
            fim = min(quantidade, i + metade_janela + 1)
            resultado.append((somas_prefixo[fim] - somas_prefixo[inicio]) / (fim - inicio))
        return resultado

    # -- ponteiro (posição + etiqueta de tempo, reposicionados todo quadro) ---
    def _reposicionar_ponteiro(self, x0, y0, x1, y1, tempo_para_x):
        """Reposiciona a linha, o ponto e a etiqueta de tempo do ponteiro (todo quadro).

        Barato (poucos itens) mesmo a 60 fps — é o que garante o deslize fluido
        independente do custo, agora constante, da linha em blocos."""
        if not self._itens_ponteiro:
            return
        tempo_ponteiro = self._tempo_exibicao
        x_ponteiro = tempo_para_x(tempo_ponteiro)
        linha_ponteiro, ponto_ponteiro, retangulo_etiqueta, texto_etiqueta = self._itens_ponteiro
        self.coords(linha_ponteiro, x_ponteiro, y0, x_ponteiro, y1)
        self.coords(ponto_ponteiro, x_ponteiro - 3, y0 - 3, x_ponteiro + 3, y0 + 3)
        self._reposicionar_etiqueta_ponteiro(x0, x1, y0, x_ponteiro,
                                             tempo_ponteiro - self._antecedencia_s,
                                             retangulo_etiqueta, texto_etiqueta)

    def _reposicionar_etiqueta_ponteiro(self, x0, x1, y0, x_ponteiro, tempo_rotulo,
                                       retangulo_etiqueta, texto_etiqueta):
        """Reposiciona a etiqueta com o rótulo de tempo do ponteiro, sempre dentro do canvas."""
        texto = _formatar_mmss_com_sinal(tempo_rotulo)
        self.itemconfigure(texto_etiqueta, text=texto)
        largura_etiqueta = max(30, 7 * len(texto))  # ~7px por caractere mono
        x0_etiqueta = x_ponteiro - largura_etiqueta / 2.0
        x1_etiqueta = x_ponteiro + largura_etiqueta / 2.0
        if x0_etiqueta < x0:
            x0_etiqueta, x1_etiqueta = x0, x0 + largura_etiqueta
        if x1_etiqueta > x1:
            x0_etiqueta, x1_etiqueta = x1 - largura_etiqueta, x1
        y0_etiqueta, y1_etiqueta = y0 - 20, y0 - 4
        self.coords(retangulo_etiqueta, x0_etiqueta, y0_etiqueta, x1_etiqueta, y1_etiqueta)
        self.coords(texto_etiqueta, (x0_etiqueta + x1_etiqueta) / 2.0,
                   (y0_etiqueta + y1_etiqueta) / 2.0)

    # -- utilidades de desenho ---------------------------------------------
    def _formatar_valor_y(self, valor):
        """Formata um valor do eixo Y com sinal (ex.: ``+15``, ``-0.5``, ``0``)."""
        if abs(valor) >= 100 or float(valor).is_integer():
            return "%+d" % int(round(valor)) if valor else "0"
        return "%+.1f" % valor if valor else "0"

    @staticmethod
    def _misturar_cores(cor_a, cor_b, fator_mistura):
        """Mistura duas cores hex (``#RRGGBB``) por `fator_mistura` (0 = `cor_a`, 1 = `cor_b`)."""
        def hex_para_rgb(cor_hex):
            cor_hex = cor_hex.lstrip("#")
            return tuple(int(cor_hex[i:i + 2], 16) for i in (0, 2, 4))
        rgb_a, rgb_b = hex_para_rgb(cor_a), hex_para_rgb(cor_b)
        return "#%02X%02X%02X" % tuple(
            int(round(rgb_a[i] + (rgb_b[i] - rgb_a[i]) * fator_mistura)) for i in range(3))
