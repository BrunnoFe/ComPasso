"""Controle de volume principal do sistema operacional (Windows via pycaw)."""

import platform

from . import player_logger

try:
    from pycaw.pycaw import AudioUtilities
except Exception:
    AudioUtilities = None


def set_master_volume(percentage) -> None:
    """Ajusta o volume principal do sistema (0–100). No-op fora do Windows.

    O valor é limitado ao intervalo [0, 100] antes de ser aplicado.
    """
    percentage = max(0, min(100, percentage))

    if platform.system() != "Windows" or AudioUtilities is None:
        return

    try:
        device = AudioUtilities.GetSpeakers()
        volume = device.EndpointVolume  # nova API do pycaw: interface acessada diretamente
        volume.SetMasterVolumeLevelScalar(percentage / 100.0, None)  # escala 0.0–1.0
    except Exception as e:
        player_logger.logger.error(f"Erro ao ajustar volume no Windows: {e}")
