"""BITalino simulado: forma dos sinais e controle do simulador em runtime.

Nada aqui publica stream LSL de verdade — só o gerador (lógica pura) é exercitado. Os testes
medem **propriedades do sinal** (faixa, dinâmica, eventos, periodicidade), não valores exatos:
o gerador é aleatório de propósito, e travar amostras específicas engessaria qualquer ajuste
futuro na simulação sem detectar nenhum defeito real.

Contrato com a GUI: o sinal gerado é o do **sensor escolhido pelo usuário**, publicado no
**canal escolhido** (índice 1..6 = A1..A6, sem subtrair 1; o índice 0 é reservado). Quem
determina o tipo de sinal é o sensor plugado, não o número do canal.
"""

import statistics

import pytest

from compasso.core import fake_bitalino
from compasso.core.fake_bitalino import GeradorSinais, N_CANAIS, CANAL_PADRAO
from compasso.core.constants import SENSOR_TYPES, SENSOR_GRAPH_PARAMS

TAXA = 100.0
DT = 1.0 / TAXA


def coletar(sensor: str, segundos: float, semente: int = 7, canal: int = CANAL_PADRAO) -> list:
    """Roda o gerador por N segundos a 100 Hz e devolve a série do canal do sensor."""
    gerador = GeradorSinais(semente=semente)
    return [gerador.amostra(i * DT, sensor, canal)[canal]
            for i in range(int(segundos * TAXA))]


# --------------------------------------------------------------------------- #
# Contrato de canais
# --------------------------------------------------------------------------- #
def test_amostra_tem_o_numero_de_canais_do_bitalino():
    assert len(GeradorSinais(semente=1).amostra(0.0)) == N_CANAIS


def test_canal_zero_e_reservado():
    """Índice 0 é SEQ/digital e a GUI nunca o lê — precisa continuar neutro."""
    gerador = GeradorSinais(semente=1)
    assert all(gerador.amostra(i * DT, "ECG", 3)[0] == 0.0 for i in range(200))


@pytest.mark.parametrize("canal", range(1, 7))
def test_sinal_sai_no_canal_escolhido(canal):
    """O sensor escolhido tem de aparecer no canal escolhido — e só nele.

    É o contrato principal: quem determina o tipo de sinal é o sensor plugado; o canal só diz
    ONDE ele foi plugado. Os demais canais ficam com ruído de fundo, como entradas sem eletrodo.
    """
    gerador = GeradorSinais(semente=5)
    amostras = [gerador.amostra(i * DT, "ECG", canal) for i in range(int(20 * TAXA))]

    pico_escolhido = max(abs(a[canal]) for a in amostras)
    assert pico_escolhido > 0.5, "o canal escolhido não recebeu o sinal do sensor"

    for outro in range(1, 7):
        if outro == canal:
            continue
        pico_outro = max(abs(a[outro]) for a in amostras)
        assert pico_outro < 0.2, (
            f"canal A{outro} deveria ter só ruído de fundo, mas atinge {pico_outro:.2f}")


@pytest.mark.parametrize("sensor", SENSOR_TYPES)
def test_sensor_escolhido_determina_a_forma_do_sinal(sensor):
    """O canal do sensor tem de carregar sinal, não o ruído de fundo dos outros canais.

    A comparação é contra um canal vizinho da MESMA série, e não contra um limiar absoluto:
    as escalas variam muito entre sensores (±3 mV no ECG, ±20 µS no EDA), então qualquer
    número fixo passaria a valer só para alguns deles.
    """
    gerador = GeradorSinais(semente=9)
    amostras = [gerador.amostra(i * DT, sensor, 3) for i in range(int(30 * TAXA))]
    sinal = statistics.pstdev(a[3] for a in amostras)
    fundo = statistics.pstdev(a[4] for a in amostras)
    assert sinal > 5 * fundo, (
        f"{sensor}: variação do canal do sensor ({sinal:.4f}) não se destaca do "
        f"ruído de fundo ({fundo:.4f})")


def test_sensores_diferentes_geram_series_diferentes():
    """Mesma semente, mesmo canal, sensores distintos: os traços não podem coincidir."""
    referencia = coletar("ECG", 10, semente=3)
    for sensor in SENSOR_TYPES:
        if sensor == "ECG":
            continue
        assert coletar(sensor, 10, semente=3) != referencia


@pytest.mark.parametrize("sensor", SENSOR_TYPES)
def test_sinal_cabe_na_escala_padrao_do_seu_sensor(sensor):
    """Nenhum sensor pode estourar a sua escala Y padrão.

    Amarra as duas pontas: o gerador (aqui) e ``SENSOR_GRAPH_PARAMS`` (a escala do gráfico).
    Sem este teste, aumentar a amplitude de um sinal simulado passaria despercebido até alguém
    ver o traço ceifado na tela — foi exatamente o que aconteceu com as piscadas do EOG.
    """
    escala = SENSOR_GRAPH_PARAMS[sensor]["padrao"]
    pico = max(abs(v) for v in coletar(sensor, 120))
    assert pico <= escala, (
        f"{sensor} atinge {pico:.2f}, além da escala padrão ±{escala}: "
        f"o traço sairia da tela sem ninguém pedir")


# --------------------------------------------------------------------------- #
# Normalização de sensor/canal (entradas que a GUI pode entregar)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("entrada, esperado", [
    (1, 1), (6, 6), (3, 3),
    (0, CANAL_PADRAO),        # `ctx.signal_channel` nasce 0 (índice reservado)
    (7, CANAL_PADRAO),        # fora da faixa analógica
    (-1, CANAL_PADRAO),
    (None, CANAL_PADRAO),
    ("4", 4),                 # veio como texto
    ("abc", CANAL_PADRAO),
])
def test_canal_valido(entrada, esperado):
    assert fake_bitalino.canal_valido(entrada) == esperado


@pytest.mark.parametrize("entrada, esperado", [
    ("EDA", "EDA"), ("EEG", "EEG"),
    ("inexistente", "ECG"), (None, "ECG"), ("", "ECG"),
])
def test_sensor_valido(entrada, esperado):
    assert fake_bitalino.sensor_valido(entrada) == esperado


def test_amostra_com_canal_invalido_nao_usa_o_indice_reservado():
    """Canal 0 (não escolhido) precisa cair no canal padrão, não no índice reservado."""
    amostra = GeradorSinais(semente=1).amostra(1.0, "ECG", 0)
    assert amostra[0] == 0.0
    assert amostra[CANAL_PADRAO] != 0.0


# --------------------------------------------------------------------------- #
# Dinâmica — o problema que motivou a mudança era o sinal ser "parado"
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("canal", range(1, 7))
def test_nenhum_canal_e_constante(canal):
    serie = coletar(canal, 20)
    assert statistics.pstdev(serie) > 0.0


@pytest.mark.parametrize("canal", range(1, 7))
def test_sinal_nao_se_repete_identico_entre_janelas(canal):
    """Senoides fixas davam janelas idênticas; com estado/eventos isso não pode acontecer."""
    serie = coletar(canal, 40)
    metade = len(serie) // 2
    primeira, segunda = serie[:metade], serie[metade:]
    assert primeira != segunda
    # e não só deslocadas: a variabilidade local também muda de uma janela para a outra.
    assert statistics.pstdev(primeira) != statistics.pstdev(segunda)


@pytest.mark.parametrize("canal", range(1, 7))
def test_valores_sao_finitos(canal):
    import math

    assert all(math.isfinite(v) for v in coletar(canal, 15))


# --------------------------------------------------------------------------- #
# Fidelidade por sensor (faixas de SENSOR_GRAPH_PARAMS e eventos característicos)
# --------------------------------------------------------------------------- #
def test_eda_fica_na_faixa_fisiologica_e_tem_respostas():
    """EDA: nível tônico em µS plausível e SCRs (subidas rápidas) aparecendo."""
    serie = coletar("EDA", 120)
    assert 1.0 < min(serie) and max(serie) < 12.0        # faixa de µS plausível
    # uma SCR sobe bem mais rápido que a deriva tônica: procura saltos ascendentes.
    subidas = [b - a for a, b in zip(serie, serie[1:]) if b - a > 0.004]
    assert len(subidas) > 50, "nenhuma resposta de condutância detectada em 2 min"


def test_ecg_tem_picos_r_com_intervalo_variavel():
    """ECG: complexos R periódicos, mas com variabilidade (o RR não pode ser constante)."""
    serie = coletar("ECG", 60)
    limiar = 0.6
    picos = [i for i in range(1, len(serie) - 1)
             if serie[i] > limiar and serie[i] >= serie[i - 1] and serie[i] > serie[i + 1]]
    assert len(picos) >= 45, f"poucos batimentos em 60 s: {len(picos)}"

    rr = [(b - a) * DT for a, b in zip(picos, picos[1:])]
    media = statistics.mean(rr)
    assert 0.4 < media < 1.5, f"frequência cardíaca implausível (RR médio {media:.2f}s)"
    assert statistics.pstdev(rr) > 0.005, "RR constante: falta variabilidade cardíaca"


def test_ecg_fica_na_faixa_de_mv():
    serie = coletar("ECG", 30)
    assert max(serie) < 3.0 and min(serie) > -1.5


def test_emg_alterna_repouso_e_rajadas():
    """EMG: a amplitude local precisa variar muito entre repouso e contração."""
    serie = coletar("EMG", 60)
    janela = int(0.5 * TAXA)
    amplitudes = [statistics.pstdev(serie[i:i + janela])
                  for i in range(0, len(serie) - janela, janela)]
    assert min(amplitudes) < 0.05, "sem trechos de repouso"
    assert max(amplitudes) > 0.15, "sem rajadas de contração"
    assert max(amplitudes) > 5 * min(amplitudes), "contraste repouso/contração fraco demais"


def test_eog_tem_eventos_rapidos_sobre_plato():
    """EOG: sacadas/piscadas são transições rápidas; entre elas o sinal se mantém."""
    serie = coletar("EOG", 60)
    saltos = [abs(b - a) for a, b in zip(serie, serie[1:])]
    assert max(saltos) > 0.02, "nenhum evento rápido (sacada/piscada)"
    # a maior parte do tempo o olhar fica parado: a mediana das variações é bem menor.
    assert statistics.median(saltos) < max(saltos) / 5


def test_eeg_tem_amplitude_em_microvolts_e_alfa_modulado():
    """EEG: dezenas de µV e fusos de alfa (a amplitude local varia ao longo do tempo)."""
    serie = coletar("EEG", 60)
    assert 5.0 < statistics.pstdev(serie) < 60.0
    janela = int(1.0 * TAXA)
    amplitudes = [statistics.pstdev(serie[i:i + janela])
                  for i in range(0, len(serie) - janela, janela)]
    assert max(amplitudes) > 1.5 * min(amplitudes), "alfa sem modulação (traço uniforme)"


def test_egg_e_o_sinal_mais_lento():
    """EGG: onda gástrica ~0,05 Hz — deve variar muito menos entre amostras que o EEG."""
    egg = coletar("EGG", 60)
    eeg = coletar("EEG", 60)
    var_egg = statistics.mean(abs(b - a) for a, b in zip(egg, egg[1:]))
    var_eeg = statistics.mean(abs(b - a) for a, b in zip(eeg, eeg[1:]))
    assert var_egg < var_eeg
    assert max(egg) < 1.0 and min(egg) > -1.0     # faixa de mV


# --------------------------------------------------------------------------- #
# Reprodutibilidade e independência entre instâncias
# --------------------------------------------------------------------------- #
def test_mesma_semente_gera_a_mesma_sequencia():
    assert coletar("ECG", 5, semente=42) == coletar("ECG", 5, semente=42)


def test_sementes_diferentes_geram_sequencias_diferentes():
    assert coletar("ECG", 5, semente=1) != coletar("ECG", 5, semente=2)


def test_geradores_nao_compartilham_estado():
    """Instâncias separadas com a mesma semente não podem interferir uma na outra."""
    a, b = GeradorSinais(semente=3), GeradorSinais(semente=3)
    serie_a = [a.amostra(i * DT)[1] for i in range(300)]
    serie_b = [b.amostra(i * DT)[1] for i in range(300)]
    assert serie_a == serie_b


# --------------------------------------------------------------------------- #
# Utilidades e controle do simulador (sem publicar stream de verdade)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("entrada, esperado", [
    ("20:17:09:18:60:29", "20:17:09:18:60:29"),
    ("20-17-09-18-60-29", "20:17:09:18:60:29"),
    ("20 17 09 18 60 29", "20:17:09:18:60:29"),
    ("a0:b1:c2:d3:e4:f5", "A0:B1:C2:D3:E4:F5"),
    ("2:17:9:18:60:29", "02:17:09:18:60:29"),
])
def test_normalizar_mac(entrada, esperado):
    assert fake_bitalino.normalizar_mac(entrada) == esperado


@pytest.mark.parametrize("invalido", ["", "20:17:09", "20:17:09:18:60:29:99", "sem-mac"])
def test_normalizar_mac_recusa_invalido(invalido):
    with pytest.raises(ValueError):
        fake_bitalino.normalizar_mac(invalido)


# --------------------------------------------------------------------------- #
# Provedor de configuração: é ele que faz a stream seguir o usuário
# --------------------------------------------------------------------------- #
def test_provedor_ausente_usa_os_padroes():
    assert fake_bitalino._ler_config(None) == ("ECG", CANAL_PADRAO)


def test_provedor_e_lido_a_cada_consulta():
    """Trocar sensor/canal na GUI precisa valer na amostra seguinte, sem reiniciar a stream."""
    estado = {"sensor": "EDA", "canal": 2}
    provedor = lambda: (estado["sensor"], estado["canal"])

    assert fake_bitalino._ler_config(provedor) == ("EDA", 2)
    estado.update(sensor="EEG", canal=5)
    assert fake_bitalino._ler_config(provedor) == ("EEG", 5)


def test_provedor_com_valores_invalidos_cai_nos_padroes():
    assert fake_bitalino._ler_config(lambda: ("inexistente", 99)) == ("ECG", CANAL_PADRAO)


def test_provedor_que_levanta_nao_derruba_a_stream():
    """A thread de publicação não tem supervisor: uma exceção do provedor a mataria em silêncio."""
    def provedor_quebrado():
        raise RuntimeError("contexto destruído durante o encerramento")

    assert fake_bitalino._ler_config(provedor_quebrado) == ("ECG", CANAL_PADRAO)


# --------------------------------------------------------------------------- #
# Grade de tempo — regressão do bug de dessincronização cumulativa
# --------------------------------------------------------------------------- #
class OutletEspiao:
    """Substituto do StreamOutlet que só guarda o que seria publicado."""

    def __init__(self):
        self.amostras = []

    def push_sample(self, amostra, timestamp=None):
        self.amostras.append((timestamp, amostra))


class RelogioFalso:
    """Relógio controlado pelo teste, com avanço arbitrário a cada consulta.

    Modela o que o SO realmente faz: `sleep(x)` dorme *pelo menos* x, às vezes muito mais
    (no Windows a granularidade do temporizador é ~15,6 ms).
    """

    def __init__(self, atrasos):
        self.agora = 1000.0            # origem arbitrária, como o local_clock()
        self._atrasos = list(atrasos)
        self._i = 0

    def __call__(self):
        return self.agora

    def esperar(self, segundos):
        # dorme o pedido MAIS um excesso variável — a fonte da deriva no código antigo.
        excesso = self._atrasos[self._i % len(self._atrasos)]
        self._i += 1
        self.agora += segundos + excesso
        return False


def _publicar(n_amostras, atrasos, taxa_hz=100.0):
    """Roda o laço de publicação até coletar n amostras, com um relógio irregular."""
    import threading

    outlet = OutletEspiao()
    relogio = RelogioFalso(atrasos)
    parar = threading.Event()

    def esperar(segundos):
        if len(outlet.amostras) >= n_amostras:
            parar.set()
            return True
        return relogio.esperar(segundos)

    fake_bitalino.publicar_amostras(
        outlet, taxa_hz=taxa_hz, parar=parar,
        gerador=GeradorSinais(semente=1), relogio=relogio, esperar=esperar)
    return [ts for ts, _ in outlet.amostras]


def test_timestamps_ficam_na_grade_exata_mesmo_com_relogio_irregular():
    """O carimbo é o instante AGENDADO da amostra, não o instante em que o laço acordou.

    Regressão do bug que dessincronizava a coleta: com `push_sample` sem timestamp, o jitter
    do agendador do SO virava jitter de timestamp, o `proc_dejitter` do inlet ajustava a reta
    errada e os marcadores chegavam cada vez mais tarde ao longo da sessão.
    """
    # excessos de sleep bem irregulares, incluindo um pico de 6 ms.
    timestamps = _publicar(300, atrasos=[0.0, 0.002, 0.006, 0.001, 0.003])

    assert len(timestamps) >= 300
    origem = timestamps[0]
    for i, ts in enumerate(timestamps):
        esperado = origem + i * 0.01
        assert abs(ts - esperado) < 1e-9, (
            f"amostra {i} carimbada em {ts - origem:.6f}s, esperado {i * 0.01:.6f}s")


def test_taxa_efetiva_nao_deriva_ao_longo_do_tempo():
    """Em 30 s simulados, a taxa média tem de ser a nominal — era 75–95 Hz na versão antiga."""
    timestamps = _publicar(3000, atrasos=[0.0, 0.004, 0.0156, 0.001])
    duracao = timestamps[-1] - timestamps[0]
    taxa = (len(timestamps) - 1) / duracao
    assert abs(taxa - 100.0) < 1e-6, f"taxa efetiva {taxa:.3f} Hz, esperado 100 Hz"


def test_intervalo_entre_amostras_e_constante():
    """Nenhum par de amostras consecutivas pode ter intervalo diferente do nominal."""
    timestamps = _publicar(500, atrasos=[0.0, 0.009, 0.002])
    intervalos = [b - a for a, b in zip(timestamps, timestamps[1:])]
    assert max(intervalos) - min(intervalos) < 1e-9


def test_atraso_extremo_realinha_a_grade_em_vez_de_despejar_amostras():
    """Uma pausa longa (suspensão do SO) não pode gerar uma avalanche de amostras velhas."""
    import threading

    outlet = OutletEspiao()
    relogio = RelogioFalso([0.0])
    parar = threading.Event()
    estado = {"saltou": False}

    def esperar(segundos):
        if len(outlet.amostras) >= 50:
            parar.set()
            return True
        if not estado["saltou"] and len(outlet.amostras) == 10:
            estado["saltou"] = True
            relogio.agora += 5.0          # 5 s de congelamento = 500 amostras perdidas
            return False
        return relogio.esperar(segundos)

    fake_bitalino.publicar_amostras(
        outlet, taxa_hz=100.0, parar=parar,
        gerador=GeradorSinais(semente=1), relogio=relogio, esperar=esperar)

    timestamps = [ts for ts, _ in outlet.amostras]
    # sem realinhamento, o laço teria emitido ~500 amostras de uma vez para "recuperar".
    assert len(timestamps) < 120, f"avalanche de {len(timestamps)} amostras após a pausa"
    # e a grade recomeça do zero, sem carimbos retroativos.
    assert all(b >= a for a, b in zip(timestamps, timestamps[1:]))


def test_simulador_comeca_desligado():
    assert fake_bitalino.esta_ativo() is False
    assert fake_bitalino.mac_ativo() is None


def test_parar_simulador_desligado_nao_levanta():
    fake_bitalino.parar_simulador()      # idempotente
    assert fake_bitalino.esta_ativo() is False


def test_iniciar_e_parar_controlam_o_estado(monkeypatch):
    """Fluxo ligar/desligar sem tocar em LSL: a thread real é substituída por uma inócua."""
    import threading

    def iniciar_falso(mac_addr, taxa_hz=100.0, provedor_config=None):
        evento = threading.Event()
        thread = threading.Thread(target=evento.wait, daemon=True)
        thread.start()
        return thread, evento

    monkeypatch.setattr(fake_bitalino, "iniciar_em_thread", iniciar_falso)
    try:
        mac = fake_bitalino.iniciar("aa:bb:cc:dd:ee:ff")
        assert mac == "AA:BB:CC:DD:EE:FF"
        assert fake_bitalino.esta_ativo() is True
        assert fake_bitalino.mac_ativo() == "AA:BB:CC:DD:EE:FF"
        # idempotente: ligar de novo com o mesmo MAC não cria uma segunda stream.
        assert fake_bitalino.iniciar("AA:BB:CC:DD:EE:FF") == "AA:BB:CC:DD:EE:FF"
    finally:
        fake_bitalino.parar_simulador()
    assert fake_bitalino.esta_ativo() is False
