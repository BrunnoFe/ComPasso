"""Controle de volume principal do sistema operacional (Windows via pycaw)."""

import platform

from . import player_logger

try:
    from pycaw.pycaw import AudioUtilities
except Exception:
    AudioUtilities = None

_unavailable_logged = False


def set_master_volume(percentage) -> bool:
    """Ajusta o volume principal do sistema (0–100). No-op fora do Windows.

    O valor é limitado ao intervalo [0, 100] antes de ser aplicado.

    :return: True se o volume foi efetivamente aplicado; False se o controle de volume
        está indisponível (pycaw ausente / SO não-Windows) ou se ocorreu erro.
    """
    global _unavailable_logged
    percentage = max(0, min(100, percentage))

    if platform.system() != "Windows" or AudioUtilities is None:
        if not _unavailable_logged:
            player_logger.logger.warning(
                "Controle de volume indisponível (pycaw ausente ou SO não-Windows); slider sem efeito.")
            _unavailable_logged = True
        return False

    try:
        device = AudioUtilities.GetSpeakers()
        volume = device.EndpointVolume  # nova API do pycaw: interface acessada diretamente
        volume.SetMasterVolumeLevelScalar(percentage / 100.0, None)  # escala 0.0–1.0
        return True
    except Exception as e:
        player_logger.logger.error(f"Erro ao ajustar volume no Windows: {e}")
        return False
