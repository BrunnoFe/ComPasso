import re
import asyncio

import bleak

from pylsl import StreamInlet, resolve_byprop

from . import connection_logger

try:
    from bleak.backends.winrt.util import allow_sta
    # tell Bleak we are using a graphical user interface that has been properly
    # configured to work with asyncio
    allow_sta()
except ImportError:
    # other OSes and older versions of Bleak will raise ImportError which we
    # can safely ignore
    pass

"""
try:
    from bleak.backends.winrt.util import uninitialize_sta

    uninitialize_sta()  # undo the unwanted side effect
except ImportError:
    # not Windows, so no problem
    pass
    LINK: https://stackoverflow.com/questions/79316741/when-using-pygrabber-and-bleak-together-the-error-thread-is-configured-for-win
"""

def connectar_bitalino(mac_addr: str) -> StreamInlet | str:
    """
    Conecta a um dispositivo Bitalino usando seu endereço MAC. O endereço MAC deve ser fornecido no formato "XX:XX:XX:XX:XX:XX" ou "XX XX XX XX XX XX". 
    Se a conexão for bem-sucedida, retorna um objeto StreamInlet para leitura dos dados. Caso contrário, retorna uma mensagem de erro.

        :param mac_addr: O endereço MAC do dispositivo Bitalino a ser conectado.
        :return: Um objeto StreamInlet se a conexão for bem-sucedida, ou uma mensagem de erro caso contrário.

    """
    mac_pattern: re.Pattern[str] = re.compile(r"\d\d[: ]\d\d[: ]\d\d[: ]\d\d[: ]\d\d[: ]\d\d")
    mac_match: re.Match[str] | None = mac_pattern.match(mac_addr)

    if mac_match is not None:
        connection_logger.logger.info(f'Endereço MAC selecionado = {mac_addr}. Conectando a stream ao OpenSignals ...')
        try:
            bitalino_inlet: StreamInlet = StreamInlet(resolve_byprop(prop='type', value=mac_addr, minimum=1, timeout=2)[0], recover=False)
            try:
                bitalino_inlet.pull_sample(timeout=1)
                connection_logger.logger.info('Conexão bem-sucedida ao Bitalino. Stream conectada ao OpenSignals.')
                return bitalino_inlet
            except Exception:
                msg: str = 'Conexão estabelecida, mas não foi possível puxar amostras do Bitalino. Verifique se o compartilhamento pelo "Lab Streaming Layer" está ativo no OpenSignals.'
                connection_logger.logger.error(msg=msg)
                return msg
        except Exception:
            msg: str = 'Não foi possível conectar ao Bitalino. Verifique se ele está conectado corretamente ao computador ou se o compartilhamento pelo "Lab Streaming Layer" está ativo no OpenSignals.'
            connection_logger.logger.error(msg=msg)
            return msg
    else:
        msg: str = 'Endereço MAC inválido. Selecione o endereço MAC do Bitalino.'
        connection_logger.logger.error(msg=msg)
        return msg

async def scan_devices():
    """
    Função assíncrona para escanear dispositivos Bluetooth Low Energy (LE) próximos usando a biblioteca Bleak.
    Imprime o nome e o endereço de cada dispositivo encontrado. 
    Note que, em sistemas operacionais como macOS, o endereço pode ser um UUID devido a restrições de privacidade do sistema.
     
    :return: None
     
     """
    try:
        connection_logger.logger.info('Iniciando escaneamento de dispositivos Bluetooth LE próximos...')
        devices = await bleak.BleakScanner.discover(timeout=3.0)
        if devices:
            dispositivos = [f'{d.name if d.name is not None else "Nome não disponível"} - {d.address}' for d in devices]
            connection_logger.logger.info(f'{len(devices)} dispositivo(s) encontrado(s) durante o escaneamento.')
            for d in devices:
                connection_logger.logger.info(f'Dispositivo encontrado - Name: {d.name if d.name is not None else "Nome não disponível"}, Address: {d.address}')
            return dispositivos
        else:
            connection_logger.logger.info('Nenhum dispositivo Bluetooth LE encontrado durante o escaneamento.')
            return None
    except Exception as e:
        if isinstance(e, bleak.exc.BleakBluetoothNotAvailableError):
            erro = 'Bluetooh não ligado ou habilitado no computador. Por favor, ligue o bluetooth e escaneie novamente.'
            connection_logger.logger.error(erro)
        else:
            erro = f'Erro durante o escaneamento de dispositivos Bluetooth LE: {e}'
            connection_logger.logger.error(erro)
        return None
    #bleak.exc.BleakBluetoothNotAvailableError: ('Bluetooth radio is not powered on. Turn on Bluetooth and try again.', <BleakBluetoothNotAvailableReason.POWERED_OFF: 3>)
    
def run_scan_devices():
    """
    Função para executar o escaneamento de dispositivos Bluetooth LE de forma síncrona, utilizando a função assíncrona scan_devices.
    
    :return: Lista de dispositivos encontrados ou None se nenhum dispositivo for encontrado ou se ocorrer um erro.
    
    """
    scan_result = asyncio.run(scan_devices()) 
    dispositivos = scan_result if scan_result is not None else None
    return dispositivos

if __name__ == '__main__':
    run_scan_devices()
    bitalino = connectar_bitalino(mac_addr='20:17:09:18:60:29')
    while True:
        if isinstance(bitalino, StreamInlet):
            eeg_data, timestamp = bitalino.pull_sample(timeout=1)
            print(f'EEG Data: {eeg_data}, Timestamp: {timestamp}')