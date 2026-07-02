import re
import time
import threading

from pylsl import (StreamInlet, resolve_byprop,
                   proc_clocksync, proc_dejitter, proc_monotonize)

from . import connection_logger

# Aceita os separadores ":", espaço e "-" (ex.: "AA:BB:..", "AA BB..", "AA-BB..").
MAC_RE = re.compile(
    r'^([0-9A-Fa-f]{2})[:\s\-]([0-9A-Fa-f]{2})[:\s\-]([0-9A-Fa-f]{2})'
    r'[:\s\-]([0-9A-Fa-f]{2})[:\s\-]([0-9A-Fa-f]{2})[:\s\-]([0-9A-Fa-f]{2})$'
)

# Timeouts (s) da resolução da stream LSL e da 1ª amostra de verificação. Sem LSL ativo
# no OpenSignals, `resolve_byprop` bloqueia por LSL_RESOLVE_TIMEOUT antes de falhar.
LSL_RESOLVE_TIMEOUT = 2
LSL_PULL_TIMEOUT = 1

def connectar_bitalino(mac_addr: str) -> StreamInlet | str:
    """
    Conecta a um dispositivo Bitalino usando seu endereço MAC. O endereço MAC deve ser fornecido no formato "XX:XX:XX:XX:XX:XX" ou "XX XX XX XX XX XX". 
    Se a conexão for bem-sucedida, retorna um objeto StreamInlet para leitura dos dados. Caso contrário, retorna uma mensagem de erro.

        :param mac_addr: O endereço MAC do dispositivo Bitalino a ser conectado.
        :return: Um objeto StreamInlet se a conexão for bem-sucedida, ou uma mensagem de erro caso contrário.

    """
    mac_match: re.Match[str] | None = MAC_RE.match(mac_addr)

    if mac_match is not None:
        mac_addr = ':'.join(mac_match.groups()).upper()  # forma normalizada, usada daqui em diante
        connection_logger.logger.info(f'Endereço MAC selecionado = {mac_addr}. Conectando a stream ao OpenSignals ...')
        try:
            bitalino_inlet: StreamInlet = StreamInlet(resolve_byprop(prop='type', value=mac_addr,
                                                                      minimum=1, timeout=LSL_RESOLVE_TIMEOUT)[0],
                                                                      recover=False, 
                                                                      processing_flags=proc_clocksync | proc_dejitter | proc_monotonize)

            # Diagnóstico: taxa nominal e nº de canais anunciados pelo OpenSignals.
            # nominal_srate == 0 indica taxa IRREGULAR — nesse caso o dejitter abaixo
            # não tem efeito e a taxa precisa ser corrigida no próprio OpenSignals.
            info = bitalino_inlet.info()
            srate: float = info.nominal_srate()
            n_canais: int = info.channel_count()
            connection_logger.logger.info(f'Stream LSL: nominal_srate={srate} Hz, canais={n_canais}.')
            if srate == 0:
                connection_logger.logger.warning(
                    'nominal_srate=0 (taxa irregular): o dejitter não suavizará os timestamps. '
                    'Configure a taxa de aquisição (ex.: 100 Hz) no OpenSignals.')

            try:
                bitalino_inlet.pull_sample(timeout=LSL_PULL_TIMEOUT)
                connection_logger.logger.info('Conexão bem-sucedida ao Bitalino. Stream conectada ao OpenSignals.')
                return bitalino_inlet
            except Exception as e:
                msg: str = f'Conexão estabelecida, mas não foi possível puxar amostras do Bitalino. Verifique se o compartilhamento pelo "Lab Streaming Layer" está ativo no OpenSignals.\n Erro: {e}'
                connection_logger.logger.error(msg=msg)
                return msg
        except Exception as e:
            msg: str = f'Não foi possível conectar ao Bitalino. Verifique se ele está conectado corretamente ao computador ou se o compartilhamento pelo "Lab Streaming Layer" está ativo no OpenSignals.\n Erro: {e}'
            connection_logger.logger.error(msg=msg)
            return msg
    else:
        msg: str = 'Endereço MAC inválido. Selecione o endereço MAC do Bitalino.'
        connection_logger.logger.error(msg=msg)
        return msg


class ConnectionWatchdog:
    """Vigia a conexão com o BITalino em uma thread daemon separada.

    Durante uma gravação, **lê** o instante da última amostra que o `LSLRecorder`
    publica (via `ctx.runner.last_acquisition_monotonic()`) — não puxa amostras, para
    não roubar dados que estão sendo gravados. Quando conectado mas ocioso (sem faixa em
    gravação), faz uma sondagem leve (`pull_sample`) só para verificar se há fluxo.

    Após `TIMEOUT` segundos sem nenhuma amostra, agenda `ctx.handle_connection_lost`
    na thread da GUI. Lacunas curtas (< TIMEOUT) nunca disparam. Inativo enquanto
    `ctx.bitalino` é None.
    """

    TIMEOUT = 15.0   # s sem amostras até considerar a conexão perdida
    POLL = 1.0       # s entre verificações

    def __init__(self, ctx):
        self.ctx = ctx
        self._stop_event = threading.Event()
        self._thread = None
        self._last_ok = None

    def start(self) -> None:
        self._stop_event.clear()
        self._last_ok = time.monotonic()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        connection_logger.logger.info("Watchdog de conexão iniciado.")

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=self.POLL + 1.0)
        connection_logger.logger.info("Watchdog de conexão encerrado.")

    def _run(self) -> None:
        while not self._stop_event.wait(self.POLL):
            inlet = self.ctx.bitalino
            if inlet is None:                       # inativo quando desconectado
                self._last_ok = time.monotonic()
                continue

            runner = self.ctx.runner
            if runner is not None and runner.is_acquiring():
                # gravando: lê o timestamp compartilhado (não puxa amostras)
                ts = runner.last_acquisition_monotonic()
                if ts is not None:
                    self._last_ok = ts
            else:
                # ocioso / entre faixas: sondagem leve (dados não gravados, sem prejuízo)
                try:
                    sample, _ = inlet.pull_sample(timeout=0.5)
                except Exception:
                    sample = None
                if sample:
                    self._last_ok = time.monotonic()

            if time.monotonic() - self._last_ok >= self.TIMEOUT:
                connection_logger.logger.error(
                    f"Sem amostras do BITalino por >= {self.TIMEOUT}s: conexão considerada perdida.")
                cb = getattr(self.ctx, "handle_connection_lost", None)
                if cb is not None:
                    self.ctx.run_after(cb)
                self._last_ok = time.monotonic()    # reset: permite disparar de novo