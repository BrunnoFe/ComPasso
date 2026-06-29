import re

from pylsl import (StreamInlet, resolve_byprop,
                   proc_clocksync, proc_dejitter, proc_monotonize)

from . import connection_logger

# Aceita os separadores ":", espaço e "-" (ex.: "AA:BB:..", "AA BB..", "AA-BB..").
MAC_RE = re.compile(
    r'^([0-9A-Fa-f]{2})[:\s\-]([0-9A-Fa-f]{2})[:\s\-]([0-9A-Fa-f]{2})'
    r'[:\s\-]([0-9A-Fa-f]{2})[:\s\-]([0-9A-Fa-f]{2})[:\s\-]([0-9A-Fa-f]{2})$'
)


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
                                                                      minimum=1, timeout=2)[0], 
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

            # Pós-processamento do inlet: sincroniza relógios, regride os timestamps para
            # uma grade uniforme (dejitter) e garante monotonicidade. Converte as rajadas
            # de ~15 amostras com timestamps quase idênticos em amostras espaçadas ~10 ms.
            #bitalino_inlet.set_postprocessing(proc_clocksync | proc_dejitter | proc_monotonize)

            try:
                bitalino_inlet.pull_sample(timeout=1)
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


if __name__ == '__main__':
    bitalino = connectar_bitalino(mac_addr='20:17:09:18:60:29')
    while True:
        if isinstance(bitalino, StreamInlet):
            eeg_data, timestamp = bitalino.pull_sample(timeout=1)
            print(f'EEG Data: {eeg_data}, Timestamp: {timestamp}')