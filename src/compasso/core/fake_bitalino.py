"""BITalino fake: gera uma stream LSL simulada para testar a GUI sem hardware real.

Cria um ``StreamOutlet`` cujo ``type`` é o endereço MAC informado (normalizado para
"XX:XX:XX:XX:XX:XX"), exatamente como :func:`compasso.core.bitalino_connect.connectar_bitalino`
espera encontrar via ``resolve_byprop(prop='type', value=mac_addr)``. Assim a resolução LSL
acha esta stream sem precisar do OpenSignals nem de um Bitalino físico.

Segue o layout de canais real do BITalino via OpenSignals: o índice 0 é reservado (SEQ/digital,
não usado pela GUI) e os canais analógicos A1-A6 ficam nos índices 1-6 (``signal_channel =
int("A3"[1])``, ou seja, **sem** subtrair 1).

**O sinal segue a escolha do usuário, não o número do canal.** No BITalino real quem determina o
tipo de sinal é o sensor que o pesquisador plugou, e o canal é só onde ele foi plugado. A
simulação faz o mesmo: gera a forma de onda do **sensor selecionado na GUI** (``ctx.sensor_type``)
e a publica **no canal selecionado** (``ctx.signal_channel``); os demais canais analógicos ficam
com um ruído de fundo baixo, como entradas sem eletrodo. Os valores saem nas **unidades e na
faixa** que ``SENSOR_GRAPH_PARAMS`` usa para desenhar aquele sensor.

Sensor e canal são lidos **a cada amostra**, através de um provedor injetado por quem sobe a
stream (ver :func:`iniciar`). É de propósito: os dois mudam em vários pontos da GUI (combos da
conexão, ``apply_config`` de um ``.config``), e ler o estado atual sempre é mais seguro que
lembrar de notificar o simulador em cada um deles.

**Sinais com dinâmica, não senoides paradas.** A versão anterior somava senoides de amplitude e
frequência fixas: o traço ficava idêntico a cada janela de tempo e não exercitava nada do
gráfico (escala, picos, eventos). Aqui cada canal tem estado e eventos aleatórios — respostas
de condutância, variabilidade de frequência cardíaca, rajadas musculares, sacadas e piscadas,
fusos de alfa e a onda lenta gástrica. O que muda é o **realismo temporal**; as faixas de
amplitude continuam fiéis a cada sensor.

Três usos:
    - CLI standalone: ``python scripts/fake_bitalino.py`` (ver esse script).
    - Preferência do app: "Configurações → App → Simular BITalino" (liga/desliga em runtime).
    - Variável de ambiente ``COMPASSO_FAKE_BITALINO`` no arranque da GUI (ver ``gui_qt/app.py``).
"""

from __future__ import annotations

import math
import random
import threading
import time

from pylsl import StreamInfo, StreamOutlet, local_clock

from . import connection_logger
from .constants import SENSOR_DEFAULT, SENSOR_GRAPH_PARAMS, SENSOR_TYPES

MAC_PADRAO = "20:17:09:18:60:29"
N_CANAIS_ANALOGICOS = 6              # A1..A6
N_CANAIS = N_CANAIS_ANALOGICOS + 1   # + índice 0 reservado (SEQ/digital)
TAXA_PADRAO_HZ = 100.0

# Canal usado quando o app ainda não tem um escolhido (`ctx.signal_channel` nasce 0, que é o
# índice reservado — publicar ali deixaria o gráfico mudo sem explicação).
CANAL_PADRAO = 1

# Atraso a partir do qual a grade de tempo é realinhada em vez de recuperada amostra a amostra
# (suspensão do SO, travamento da máquina). Ver `publicar_amostras`.
_ATRASO_MAXIMO_S = 1.0

# Amplitude do ruído dos canais sem sensor, como fração da escala do sensor ativo: uma entrada
# sem eletrodo não fica em zero absoluto, mas também não pode competir com o sinal de verdade.
# Fração pequena de propósito: as escalas variam muito entre sensores (±3 mV no ECG, ±20 µS no
# EDA) e 1% da escala mais ampla já era da ordem da própria variação do EDA.
_FRACAO_RUIDO_FUNDO = 0.002


def canal_valido(canal) -> int:
    """Normaliza o índice de canal para a faixa analógica 1..6 (A1..A6)."""
    try:
        canal = int(canal)
    except (TypeError, ValueError):
        return CANAL_PADRAO
    return canal if 1 <= canal <= N_CANAIS_ANALOGICOS else CANAL_PADRAO


def sensor_valido(sensor) -> str:
    """Normaliza o tipo de sensor para um dos suportados."""
    return sensor if sensor in SENSOR_TYPES else SENSOR_DEFAULT


def normalizar_mac(mac_addr: str) -> str:
    """Normaliza um MAC em qualquer separador (":", "-", espaço) para "XX:XX:XX:XX:XX:XX"."""
    partes = [p for p in mac_addr.replace("-", ":").replace(" ", ":").split(":") if p]
    if len(partes) != 6:
        raise ValueError(f'Endereço MAC inválido: "{mac_addr}" (esperado XX:XX:XX:XX:XX:XX).')
    return ":".join(p.upper().zfill(2) for p in partes)


class GeradorSinais:
    """Gera uma amostra de 7 canais por chamada, com estado entre amostras.

    O estado é o que permite eventos com duração (uma resposta de condutância dura ~5 s, uma
    rajada muscular ~1 s): sem ele, só dá para somar funções periódicas do tempo — que foi o
    problema do gerador antigo. Cada chamada de :meth:`amostra` avança o relógio interno para o
    instante pedido, então a forma dos eventos não depende da taxa de amostragem.
    """

    def __init__(self, semente: int | None = None):
        self._rnd = random.Random(semente)
        self._t_anterior = 0.0

        # --- EDA: nível tônico + respostas fásicas (SCRs) ---
        self._eda_tonico = 4.0
        self._eda_scrs: list[dict] = []      # respostas em curso
        self._eda_proxima_scr = 4.0

        # --- ECG: batimento atual e variabilidade ---
        self._ecg_fase = 0.0                 # 0..1 dentro do batimento
        self._ecg_rr = 0.85                  # intervalo entre batimentos (s)

        # --- EMG: rajadas de contração ---
        self._emg_ate = -1.0                 # instante do fim da rajada atual
        self._emg_inicio = 0.0
        self._emg_amplitude = 0.0
        self._emg_proxima = 3.0

        # --- EOG: posição do olhar + piscadas ---
        self._eog_alvo = 0.0
        self._eog_atual = 0.0
        self._eog_proxima_sacada = 2.0
        self._eog_piscada_ate = -1.0
        self._eog_proxima_piscada = 5.0

        # --- EEG: envelope do ritmo alfa (fusos que crescem e somem) ---
        self._eeg_alfa = 0.3
        self._eeg_alvo_alfa = 0.8
        self._eeg_proxima_troca = 3.0

        # --- EGG: amplitude da onda lenta gástrica ---
        self._egg_amplitude = 0.25

    # ------------------------------------------------------------------ público
    def amostra(self, t: float, sensor: str = SENSOR_DEFAULT,
                canal: int = CANAL_PADRAO) -> list[float]:
        """Retorna os 7 valores do instante ``t`` (s desde o início da stream).

        O sinal de ``sensor`` vai para o índice ``canal``; os demais canais analógicos recebem
        ruído de fundo, como entradas sem eletrodo ligado.

        Args:
            t: instante em segundos desde o início da stream.
            sensor: tipo de sensor a simular (um de ``SENSOR_TYPES``).
            canal: índice analógico de destino, 1..6 (A1..A6).
        """
        dt = max(0.0, t - self._t_anterior)
        self._t_anterior = t

        sensor = sensor_valido(sensor)
        canal = canal_valido(canal)
        valor = self._gerar(sensor, t, dt)

        # ruído proporcional à escala do sensor ativo: mudar de canal na GUI mostra uma linha
        # de base plausível, não um zero perfeito que nenhum conversor produz.
        escala = SENSOR_GRAPH_PARAMS[sensor]["padrao"]
        ruido = escala * _FRACAO_RUIDO_FUNDO
        amostra = [0.0]                                   # índice 0: reservado
        amostra += [self._rnd.gauss(0.0, ruido) for _ in range(N_CANAIS_ANALOGICOS)]
        amostra[canal] = valor
        return amostra

    def _gerar(self, sensor: str, t: float, dt: float) -> float:
        """Despacha para o gerador do sensor pedido."""
        return {
            "EDA": self._eda,
            "ECG": self._ecg,
            "EMG": self._emg,
            "EOG": self._eog,
            "EEG": self._eeg,
            "EGG": self._egg,
        }[sensor](t, dt)

    # ------------------------------------------------------------------ canais
    def _eda(self, t: float, dt: float) -> float:
        """A1 — condutância da pele (µS): nível tônico com deriva + SCRs fásicas.

        A resposta de condutância (SCR) é o evento que caracteriza o sinal: subida rápida
        (~1 s) e decaimento lento (~4 s). É também o que o experimento do ComPasso procura,
        então é o que precisa aparecer no gráfico durante um teste.
        """
        # deriva tônica: passeio aleatório suave, preso a uma faixa fisiológica (2–8 µS).
        self._eda_tonico += self._rnd.gauss(0.0, 0.02) * dt * 10
        self._eda_tonico = min(8.0, max(2.0, self._eda_tonico))

        # nasce uma nova SCR de tempos em tempos (agrupadas: às vezes vêm em sequência).
        if t >= self._eda_proxima_scr:
            self._eda_scrs.append({
                "t0": t,
                "amp": self._rnd.uniform(0.15, 1.6),
                "subida": self._rnd.uniform(0.6, 1.1),
                "queda": self._rnd.uniform(3.0, 6.0),
            })
            self._eda_proxima_scr = t + self._rnd.choice([
                self._rnd.uniform(1.0, 3.0),     # em salva
                self._rnd.uniform(6.0, 18.0),    # espaçadas
            ])

        fasico = 0.0
        for scr in list(self._eda_scrs):
            dtr = t - scr["t0"]
            if dtr > scr["queda"] * 4:
                self._eda_scrs.remove(scr)       # já decaiu ao chão; para de custar
                continue
            # biexponencial: diferença entre o decaimento e a subida.
            fasico += scr["amp"] * (math.exp(-dtr / scr["queda"]) - math.exp(-dtr / scr["subida"]))

        # modulação respiratória leve (~0,25 Hz) + ruído do conversor.
        respiracao = 0.03 * math.sin(2 * math.pi * 0.25 * t)
        return self._eda_tonico + fasico + respiracao + self._rnd.gauss(0.0, 0.006)

    def _ecg(self, t: float, dt: float) -> float:
        """A2 — ECG (mV): complexo PQRST com variabilidade de frequência cardíaca.

        O RR é sorteado a cada batimento em torno de uma frequência que oscila com a respiração
        (arritmia sinusal respiratória) — por isso o traço nunca se repete igual, como no real.
        """
        self._ecg_fase += dt / max(0.25, self._ecg_rr)
        if self._ecg_fase >= 1.0:
            self._ecg_fase -= 1.0
            fc_base = 68.0 + 6.0 * math.sin(2 * math.pi * 0.05 * t)      # tendência lenta
            rsa = 4.0 * math.sin(2 * math.pi * 0.25 * t)                 # respiração
            fc = fc_base + rsa + self._rnd.gauss(0.0, 1.5)
            self._ecg_rr = 60.0 / max(40.0, min(150.0, fc))

        f = self._ecg_fase
        # ondas do complexo: (centro, amplitude mV, largura). Proporções do padrão clínico.
        ondas = ((0.16, 0.09, 0.028),     # P
                 (0.27, -0.14, 0.008),    # Q
                 (0.30, 1.15, 0.009),     # R
                 (0.33, -0.28, 0.010),    # S
                 (0.50, 0.26, 0.042))     # T
        valor = sum(a * math.exp(-((f - c) ** 2) / (2 * w * w)) for c, a, w in ondas)
        # oscilação da linha de base (respiração/movimento do eletrodo) + ruído.
        linha_base = 0.05 * math.sin(2 * math.pi * 0.25 * t)
        return valor + linha_base + self._rnd.gauss(0.0, 0.012)

    def _emg(self, t: float, dt: float) -> float:
        """A3 — EMG (mV): repouso ruidoso interrompido por rajadas de contração.

        A rajada tem envelope suave (sobe e desce), não liga/desliga: uma contração real
        recruta fibras progressivamente, e o degrau do gerador antigo não parecia músculo.
        """
        if t >= self._emg_proxima and t > self._emg_ate:
            duracao = self._rnd.uniform(0.4, 2.2)
            self._emg_inicio = t
            self._emg_ate = t + duracao
            self._emg_amplitude = self._rnd.uniform(0.35, 1.0)
            self._emg_proxima = self._emg_ate + self._rnd.uniform(1.5, 7.0)

        envelope = 0.02   # tônus de repouso
        if t <= self._emg_ate:
            prog = (t - self._emg_inicio) / max(1e-6, self._emg_ate - self._emg_inicio)
            # janela de cosseno elevado: 0 → 1 → 0 ao longo da rajada.
            envelope += self._emg_amplitude * (0.5 - 0.5 * math.cos(2 * math.pi * prog))
        return self._rnd.gauss(0.0, envelope * 0.45)

    def _eog(self, t: float, dt: float) -> float:
        """A4 — EOG (mV): posição do olhar em degraus (sacadas) + piscadas.

        Sacada = mudança rápida para uma nova posição, que depois se mantém; piscada = pico
        curto e alto por cima. São os dois eventos que qualquer traço de EOG mostra.
        """
        if t >= self._eog_proxima_sacada:
            self._eog_alvo = self._rnd.uniform(-0.35, 0.35)
            self._eog_proxima_sacada = t + self._rnd.uniform(0.8, 4.0)
        # aproximação exponencial rápida (~50 ms) do alvo: o degrau da sacada.
        self._eog_atual += (self._eog_alvo - self._eog_atual) * min(1.0, dt / 0.05)

        if t >= self._eog_proxima_piscada:
            self._eog_piscada_ate = t + 0.3
            self._eog_proxima_piscada = t + self._rnd.uniform(2.5, 9.0)
        piscada = 0.0
        if t <= self._eog_piscada_ate:
            prog = 1.0 - (self._eog_piscada_ate - t) / 0.3
            piscada = 0.45 * math.sin(math.pi * prog) ** 2

        deriva = 0.02 * math.sin(2 * math.pi * 0.03 * t)
        return self._eog_atual + piscada + deriva + self._rnd.gauss(0.0, 0.006)

    def _eeg(self, t: float, dt: float) -> float:
        """A5 — EEG (µV): mistura de ritmos com fusos de alfa que vão e voltam.

        Alfa (~10 Hz) crescendo e sumindo é a assinatura visual do EEG de repouso; sem essa
        modulação o traço vira um zumbido constante.
        """
        if t >= self._eeg_proxima_troca:
            self._eeg_alvo_alfa = self._rnd.uniform(0.15, 1.0)
            self._eeg_proxima_troca = t + self._rnd.uniform(2.0, 6.0)
        self._eeg_alfa += (self._eeg_alvo_alfa - self._eeg_alfa) * min(1.0, dt / 0.8)

        delta = 8.0 * math.sin(2 * math.pi * 2.0 * t + 0.7)
        theta = 5.0 * math.sin(2 * math.pi * 6.0 * t + 1.9)
        alfa = 18.0 * self._eeg_alfa * math.sin(2 * math.pi * 10.0 * t)
        beta = 3.0 * math.sin(2 * math.pi * 20.0 * t + 2.4)
        return delta + theta + alfa + beta + self._rnd.gauss(0.0, 2.2)

    def _egg(self, t: float, dt: float) -> float:
        """A6 — EGG (mV): onda lenta gástrica de ~3 ciclos por minuto (0,05 Hz).

        É o sinal mais lento do conjunto; a amplitude passeia devagar para o traço não ficar
        idêntico a cada ciclo.
        """
        self._egg_amplitude += self._rnd.gauss(0.0, 0.004) * dt * 10
        self._egg_amplitude = min(0.42, max(0.12, self._egg_amplitude))
        onda = self._egg_amplitude * math.sin(2 * math.pi * 0.05 * t)
        respiracao = 0.03 * math.sin(2 * math.pi * 0.25 * t)
        return onda + respiracao + self._rnd.gauss(0.0, 0.008)


# Instância padrão usada por `gerar_amostra` (compatibilidade com quem já chamava a função).
_gerador_padrao = GeradorSinais()


def gerar_amostra(t: float, sensor: str = SENSOR_DEFAULT,
                  canal: int = CANAL_PADRAO) -> list[float]:
    """Gera uma amostra de N_CANAIS valores no instante t (s) para o sensor/canal informados.

    Mantida por compatibilidade; internamente delega a um :class:`GeradorSinais` compartilhado.
    Para simulações independentes (ex.: testes), instancie o gerador diretamente — assim o
    estado não é compartilhado e uma semente fixa torna a sequência reproduzível.
    """
    return _gerador_padrao.amostra(t, sensor, canal)


def _criar_outlet(mac_normalizado: str, taxa_hz: float) -> StreamOutlet:
    info = StreamInfo(
        name="FakeBITalino",
        type=mac_normalizado,
        channel_count=N_CANAIS,
        nominal_srate=taxa_hz,
        channel_format="float32",
        source_id=f"fake-bitalino-{mac_normalizado}",
    )
    return StreamOutlet(info)


def executar(mac_addr: str = MAC_PADRAO, taxa_hz: float = TAXA_PADRAO_HZ,
             parar: threading.Event | None = None, provedor_config=None) -> None:
    """Publica a stream fake e empurra amostras até ``parar`` ser setado (ou para sempre).

    Args:
        mac_addr: MAC simulado (qualquer separador; é normalizado).
        taxa_hz: taxa de amostragem em Hz.
        parar: evento opcional para encerrar o laço de forma limpa (usado no modo embutido).
        provedor_config: chamável sem argumentos que devolve ``(sensor, canal)`` — consultado a
            cada amostra, para a simulação acompanhar o que o usuário escolher enquanto a stream
            já está no ar. Se ``None``, usa o sensor padrão no canal padrão.
    """
    mac_normalizado = normalizar_mac(mac_addr)
    outlet = _criar_outlet(mac_normalizado, taxa_hz)
    connection_logger.logger.info(
        f'BITalino fake publicado: type="{mac_normalizado}", {N_CANAIS} canais, {taxa_hz:.0f} Hz. '
        f'O sinal simulado segue o sensor e o canal escolhidos na interface. '
        f'Use este MAC no ComPasso e clique em Conectar.')

    publicar_amostras(outlet, taxa_hz=taxa_hz, parar=parar, provedor_config=provedor_config)
    connection_logger.logger.info("BITalino fake encerrado.")


def publicar_amostras(outlet, taxa_hz: float = TAXA_PADRAO_HZ,
                      parar: threading.Event | None = None, provedor_config=None,
                      gerador: "GeradorSinais | None" = None,
                      relogio=local_clock, esperar=None) -> None:
    """Empurra amostras numa **grade de tempo absoluta**, como faz o hardware real.

    Esta função é o coração da fidelidade temporal da simulação, e a versão anterior errava
    exatamente aqui. Ela fazia::

        t = time.monotonic() - inicio
        outlet.push_sample(gerador.amostra(t))   # sem timestamp
        time.sleep(intervalo)                    # 1/100 s

    Três defeitos encadeados:

    1. **Passo acumulado.** Cada volta custava ``intervalo + trabalho + granularidade do sleep``
       (no Windows, ~15,6 ms). A stream declarava 100 Hz e entregava 75–95 Hz, com a taxa
       passeando conforme a carga da máquina.
    2. **Carimbo na hora do acordar.** ``push_sample`` sem ``timestamp`` faz o LSL carimbar a
       amostra quando o Python acordou — ou seja, o jitter do agendador virava jitter de
       timestamp. Um conversor real carimba no instante da **aquisição**, não no da entrega.
    3. **Dejitter enganado.** O inlet do app usa ``proc_dejitter``, que regulariza os carimbos
       ajustando uma reta. Com um emissor de taxa errante, essa reta se descola do tempo real —
       e como o estado do ajuste vive no ``StreamInlet``, que sobrevive a todas as faixas, o
       erro **se acumulava faixa a faixa** em vez de zerar a cada arquivo. Era isso que fazia
       os marcadores chegarem cada vez mais tarde ao longo da sessão.

    A correção segue a mesma regra que o ``ExperimentRunner`` já obedece: **instante absoluto,
    nunca passo acumulado**. A amostra ``n`` pertence ao instante ``inicio + n/taxa`` e é
    carimbada com ele, independentemente de quando o Python conseguiu acordar para enviá-la.
    Atrasos viram jitter de entrega (que o LSL absorve com folga), não deriva de relógio.

    Args:
        outlet: destino das amostras (qualquer objeto com ``push_sample(amostra, timestamp)``).
        taxa_hz: taxa nominal — a mesma anunciada no ``StreamInfo``, agora honrada de fato.
        parar: evento de parada; também é usado como espera (permite encerrar na hora).
        provedor_config: chamável que devolve ``(sensor, canal)`` — ver :func:`executar`.
        gerador: gerador de sinais (um novo é criado se omitido).
        relogio: fonte de tempo, no mesmo domínio dos timestamps do LSL (injetável nos testes).
        esperar: espera bloqueante ``(segundos) -> bool``, onde True significa "pare agora".
    """
    if gerador is None:
        gerador = GeradorSinais()
    if esperar is None:
        esperar = parar.wait if parar is not None else time.sleep

    intervalo = 1.0 / taxa_hz
    inicio = relogio()
    n = 0
    ultimo_log = None

    while parar is None or not parar.is_set():
        alvo = inicio + n * intervalo
        atraso = relogio() - alvo

        if atraso > _ATRASO_MAXIMO_S:
            # ficamos muito para trás (máquina travou, suspensão do SO...). Emitir de uma vez
            # as milhares de amostras atrasadas entupiria o inlet com dados velhos; é mais
            # honesto reconhecer a lacuna, realinhar a grade e avisar — como um dispositivo
            # real que perdeu amostras.
            perdidas = int(atraso / intervalo)
            connection_logger.logger.warning(
                f"BITalino simulado atrasado {atraso:.2f}s ({perdidas} amostras): "
                f"realinhando a grade de tempo.")
            inicio = relogio()
            n = 0
            continue

        if atraso < 0:
            # ainda não é hora desta amostra: espera até o instante exato dela.
            if esperar(-atraso):
                break
            continue

        sensor, canal = _ler_config(provedor_config)
        if (sensor, canal) != ultimo_log:
            connection_logger.logger.info(
                f"BITalino simulado: gerando {sensor} no canal A{canal}.")
            ultimo_log = (sensor, canal)

        # o sinal é avaliado no instante NOMINAL da amostra (n/taxa), não no relógio de parede:
        # é isso que dá ao traço a mesma regularidade de um conversor real.
        outlet.push_sample(gerador.amostra(n * intervalo, sensor, canal), timestamp=alvo)
        n += 1


def _ler_config(provedor_config) -> tuple[str, int]:
    """Lê (sensor, canal) do provedor, caindo nos padrões se ele falhar.

    Blindado de propósito: este código roda na thread de publicação, e uma exceção vinda do
    provedor (ex.: contexto sendo destruído no encerramento do app) mataria a stream em silêncio.
    """
    if provedor_config is None:
        return SENSOR_DEFAULT, CANAL_PADRAO
    try:
        sensor, canal = provedor_config()
    except Exception:
        return SENSOR_DEFAULT, CANAL_PADRAO
    return sensor_valido(sensor), canal_valido(canal)


def iniciar_em_thread(mac_addr: str = MAC_PADRAO, taxa_hz: float = TAXA_PADRAO_HZ,
                      provedor_config=None) -> tuple[threading.Thread, threading.Event]:
    """Sobe o BITalino fake numa thread daemon. Retorna (thread, evento_de_parada).

    Setar o evento retornado encerra a publicação; como a thread é daemon, também morre com o app.
    """
    parar = threading.Event()
    thread = threading.Thread(
        target=executar, args=(mac_addr, taxa_hz, parar, provedor_config),
        name="FakeBITalino", daemon=True)
    thread.start()
    return thread, parar


# ---------------------------------------------------------------------------
# Controle em runtime (usado pela preferência "Simular BITalino").
# Um único simulador por processo: ligar duas vezes publicaria duas streams com o mesmo `type`,
# e a resolução LSL passaria a escolher uma delas de forma imprevisível.
# ---------------------------------------------------------------------------
_ativo: dict = {"thread": None, "parar": None, "mac": None}
_trava = threading.Lock()


def esta_ativo() -> bool:
    """True se há um simulador publicando neste processo."""
    with _trava:
        thread = _ativo["thread"]
        return thread is not None and thread.is_alive()


def mac_ativo() -> str | None:
    """MAC do simulador em execução, ou None."""
    with _trava:
        return _ativo["mac"]


def iniciar(mac_addr: str = MAC_PADRAO, taxa_hz: float = TAXA_PADRAO_HZ,
            provedor_config=None) -> str | None:
    """Liga o simulador (idempotente). Retorna o MAC publicado, ou None em caso de falha.

    Se já houver um simulador ativo com outro MAC, o anterior é encerrado primeiro.

    :param provedor_config: chamável que devolve ``(sensor, canal)``; ver :func:`executar`.
    """
    mac_normalizado = normalizar_mac(mac_addr)
    if esta_ativo():
        if mac_ativo() == mac_normalizado:
            return mac_normalizado
        parar_simulador()
    try:
        thread, evento = iniciar_em_thread(mac_normalizado, taxa_hz, provedor_config)
    except Exception as e:
        connection_logger.logger.error(f"Falha ao iniciar o BITalino simulado: {e}")
        return None
    with _trava:
        _ativo.update(thread=thread, parar=evento, mac=mac_normalizado)
    return mac_normalizado


def parar_simulador() -> None:
    """Encerra o simulador, se estiver ativo (espera a thread sair para liberar a porta LSL)."""
    with _trava:
        evento, thread = _ativo["parar"], _ativo["thread"]
        _ativo.update(thread=None, parar=None, mac=None)
    if evento is not None:
        evento.set()
    if thread is not None and thread.is_alive():
        # join curto: a thread só precisa terminar o sleep do intervalo corrente.
        thread.join(timeout=1.0)
