"""Controle do volume principal do sistema operacional (multiplataforma).

Windows usa `pycaw`; macOS usa `osascript` (AppleScript); Linux usa `amixer` (ALSA/PulseAudio).
Fora desses sistemas (ou se a ferramenta correspondente faltar) o ajuste é um no-op registrado.
"""

import platform
import re
import subprocess

from . import player_logger

try:
    from pycaw.pycaw import AudioUtilities
except ImportError:
    # pycaw é Windows-only (ver requirements.txt); em outros SOs o controle de volume
    # cai para osascript/amixer abaixo, então a ausência do pacote não pode ser fatal.
    AudioUtilities = None

_unavailable_logged = False


def _log_unavailable(motivo: str) -> bool:
    """Registra (uma única vez) a indisponibilidade do controle de volume e retorna False."""
    global _unavailable_logged
    if not _unavailable_logged:
        player_logger.logger.warning(f"Controle de volume indisponível ({motivo}); slider sem efeito.")
        _unavailable_logged = True
    return False


def get_system_volume(padrao: float | None = 50.0):
    """Lê o volume principal de saída do sistema (0–100), de forma multiplataforma.

    Mesma estrutura de plataforma de `set_system_volume`. Nunca levanta exceção.

    :param padrao: valor devolvido quando a leitura **falha** (pycaw ausente, erro de COM,
        SO não suportado). O default 50.0 preserva o comportamento histórico, mas quem
        **age** sobre o resultado deve passar ``None`` e tratar o "não sei": devolver 50 em
        caso de erro é indistinguível de "o volume é 50", e num laço de sincronização isso
        empurraria o volume real da máquina para 50 sozinho.
    :return: volume atual do sistema (0–100), ou ``padrao`` se não foi possível ler.
    """
    sistema = platform.system()
    try:
        if sistema == "Windows":
            if AudioUtilities is None:
                _log_unavailable("pycaw ausente")
                return padrao
            device = AudioUtilities.GetSpeakers()
            if device is None:
                _log_unavailable("dispositivo de áudio não encontrado")
                return padrao
            volume = device.EndpointVolume  # nova API do pycaw: interface acessada diretamente
            return volume.GetMasterVolumeLevelScalar() * 100.0  # escala 0.0–1.0 -> 0–100

        elif sistema == "Darwin":  # macOS
            resultado = subprocess.run(["osascript", "-e", "output volume of (get volume settings)"],
                                       capture_output=True, text=True, check=True)
            return float(int(resultado.stdout.strip()))

        elif sistema == "Linux":
            resultado = subprocess.run(["amixer", "-D", "pulse", "sget", "Master"],
                                       capture_output=True, text=True, check=True)
            match = re.search(r"\[(\d{1,3})%\]", resultado.stdout)
            if match:
                return float(int(match.group(1)))
            _log_unavailable("não foi possível interpretar a saída do amixer")
            return padrao

        _log_unavailable(f"SO não suportado: {sistema}")
        return padrao
    except Exception as e:
        player_logger.logger.warning(f"Erro ao ler volume em {sistema}: {e}; devolvendo {padrao}.")
        return padrao


def set_system_volume(percentage) -> bool:
    """Ajusta o volume principal do sistema (0–100), de forma multiplataforma.

    O valor é limitado ao intervalo [0, 100] antes de ser aplicado.

    :param percentage: volume desejado, de 0 (mudo) a 100 (máximo).
    :return: True se o volume foi efetivamente aplicado; False se o controle está
        indisponível (ferramenta ausente / SO não suportado) ou se ocorreu erro.
    """
    percentage = max(0, min(100, int(percentage)))
    sistema = platform.system()

    try:
        if sistema == "Windows":
            if AudioUtilities is None:
                return _log_unavailable("pycaw ausente")
            device = AudioUtilities.GetSpeakers()
            if device is None:
                return _log_unavailable("dispositivo de áudio não encontrado")
            volume = device.EndpointVolume  # nova API do pycaw: interface acessada diretamente
            volume.SetMasterVolumeLevelScalar(percentage / 100.0, None)  # escala 0.0–1.0
            return True

        elif sistema == "Darwin":  # macOS
            subprocess.run(["osascript", "-e", f"set volume output volume {percentage}"], check=True)
            return True

        elif sistema == "Linux":
            subprocess.run(["amixer", "-D", "pulse", "sset", "Master", f"{percentage}%"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            return True

        return _log_unavailable(f"SO não suportado: {sistema}")
    except Exception as e:
        player_logger.logger.error(f"Erro ao ajustar volume em {sistema}: {e}")
        return False
