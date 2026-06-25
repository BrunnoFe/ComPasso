"""Controle do volume principal do sistema operacional (multiplataforma).

Windows usa `pycaw`; macOS usa `osascript` (AppleScript); Linux usa `amixer` (ALSA/PulseAudio).
Fora desses sistemas (ou se a ferramenta correspondente faltar) o ajuste é um no-op registrado.
"""

import platform
import subprocess

from . import player_logger

try:
    from pycaw.pycaw import AudioUtilities
except Exception:
    AudioUtilities = None

_unavailable_logged = False


def _log_unavailable(motivo: str) -> bool:
    """Registra (uma única vez) a indisponibilidade do controle de volume e retorna False."""
    global _unavailable_logged
    if not _unavailable_logged:
        player_logger.logger.warning(f"Controle de volume indisponível ({motivo}); slider sem efeito.")
        _unavailable_logged = True
    return False


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
