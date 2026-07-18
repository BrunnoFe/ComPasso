"""BITalino fake: gera uma stream LSL simulada para testar a GUI sem hardware real.

Cria um ``StreamOutlet`` cujo ``type`` é o endereço MAC informado (normalizado para
"XX:XX:XX:XX:XX:XX"), exatamente como :func:`compasso.core.bitalino_connect.connectar_bitalino`
espera encontrar via ``resolve_byprop(prop='type', value=mac_addr)``. Assim a resolução LSL
acha esta stream sem precisar do OpenSignals nem de um Bitalino físico.

Segue o layout de canais real do BITalino via OpenSignals: o índice 0 é reservado (SEQ/digital,
não usado pela GUI) e os canais analógicos A1-A6 ficam nos índices 1-6 (``signal_channel =
int("A3"[1])``, ou seja, **sem** subtrair 1). Cada canal analógico gera uma forma de onda
simulada diferente para deixar o gráfico visualmente vivo em qualquer canal/sensor.

Dois usos:
    - CLI standalone: ``python scripts/fake_bitalino.py`` (ver esse script).
    - Embutido no app: :func:`iniciar_em_thread`, acionado pela variável de ambiente
      ``COMPASSO_FAKE_BITALINO`` no arranque da GUI (ver ``gui_qt/app.py``).
"""

from __future__ import annotations

import math
import random
import threading
import time

from pylsl import StreamInfo, StreamOutlet

from . import connection_logger

MAC_PADRAO = "20:17:09:18:60:29"
N_CANAIS_ANALOGICOS = 6              # A1..A6
N_CANAIS = N_CANAIS_ANALOGICOS + 1   # + índice 0 reservado (SEQ/digital)
TAXA_PADRAO_HZ = 100.0


def normalizar_mac(mac_addr: str) -> str:
    """Normaliza um MAC em qualquer separador (":", "-", espaço) para "XX:XX:XX:XX:XX:XX"."""
    partes = [p for p in mac_addr.replace("-", ":").replace(" ", ":").split(":") if p]
    if len(partes) != 6:
        raise ValueError(f'Endereço MAC inválido: "{mac_addr}" (esperado XX:XX:XX:XX:XX:XX).')
    return ":".join(p.upper().zfill(2) for p in partes)


def gerar_amostra(t: float) -> list[float]:
    """Gera uma amostra de N_CANAIS valores no instante t (s), um sinal plausível por canal."""
    amostra = [0.0]  # índice 0: reservado, não lido pela GUI

    # A1: deriva lenta tipo EDA (condutância da pele) + ruído fino.
    amostra.append(2.0 + 0.4 * math.sin(t * 0.15) + random.uniform(-0.02, 0.02))
    # A2: "batimentos" tipo ECG — picos estreitos e periódicos sobre uma linha de base.
    fase_ecg = (t % 0.8) / 0.8
    pico = math.exp(-((fase_ecg - 0.1) ** 2) / 0.0006) if fase_ecg < 0.3 else 0.0
    amostra.append(0.3 + 1.2 * pico + random.uniform(-0.01, 0.01))
    # A3: rajadas tipo EMG — bursts de ruído de amplitude variável.
    burst = 1.0 if math.sin(t * 0.7) > 0.3 else 0.15
    amostra.append(random.uniform(-burst, burst))
    # A4: respiração — senoide lenta e suave.
    amostra.append(1.5 * math.sin(t * 0.35) + random.uniform(-0.03, 0.03))
    # A5: deriva térmica muito lenta, quase constante.
    amostra.append(0.8 + 0.05 * math.sin(t * 0.02) + random.uniform(-0.005, 0.005))
    # A6: ruído genérico de banda larga.
    amostra.append(random.uniform(-0.5, 0.5))

    return amostra


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
             parar: threading.Event | None = None) -> None:
    """Publica a stream fake e empurra amostras até ``parar`` ser setado (ou para sempre).

    Args:
        mac_addr: MAC simulado (qualquer separador; é normalizado).
        taxa_hz: taxa de amostragem em Hz.
        parar: evento opcional para encerrar o laço de forma limpa (usado no modo embutido).
    """
    mac_normalizado = normalizar_mac(mac_addr)
    outlet = _criar_outlet(mac_normalizado, taxa_hz)
    connection_logger.logger.info(
        f'BITalino fake publicado: type="{mac_normalizado}", {N_CANAIS} canais, {taxa_hz:.0f} Hz. '
        f'Use este MAC no ComPasso e clique em Conectar.')

    intervalo = 1.0 / taxa_hz
    inicio = time.monotonic()
    while parar is None or not parar.is_set():
        t = time.monotonic() - inicio
        outlet.push_sample(gerar_amostra(t))
        time.sleep(intervalo)
    connection_logger.logger.info("BITalino fake encerrado.")


def iniciar_em_thread(mac_addr: str = MAC_PADRAO, taxa_hz: float = TAXA_PADRAO_HZ
                      ) -> tuple[threading.Thread, threading.Event]:
    """Sobe o BITalino fake numa thread daemon. Retorna (thread, evento_de_parada).

    Setar o evento retornado encerra a publicação; como a thread é daemon, também morre com o app.
    """
    parar = threading.Event()
    thread = threading.Thread(
        target=executar, args=(mac_addr, taxa_hz, parar),
        name="FakeBITalino", daemon=True)
    thread.start()
    return thread, parar
