from . import player_logger

import pygame

class Player:
    """Audio player using pygame.mixer.

    Methods:
      - load(path) -> bool
      - play()
      - stop()
      - is_busy()
      - get_pos()
      - get_length()
    """
    def __init__(self):
        self._loaded = False
        self._playing = False
        self._paused = False
        self._path = None
        self._current_length = 0.0
        # beep de aviso (canal separado): Sound cacheado por caminho para não recarregar a
        # cada faixa. Toca em paralelo à faixa carregada em pygame.mixer.music, sem pará-la.
        self._beep_sound = None
        self._beep_path = None

        try:
            pygame.mixer.init()
        except Exception as e:
            player_logger.logger.warning(f'pygame.mixer.init() failed: {e}')

    def load(self, path: str) -> bool:
        """Load a single audio file. Returns True on success."""
        try:
            pygame.mixer.music.load(path)
            self._loaded = True
            self._path = path
            # try to determine track length
            try:
                sound = pygame.mixer.Sound(path)
                self._current_length = float(sound.get_length())
            except Exception:
                # leave at 0.0 if not available
                self._current_length = 0.0
            player_logger.logger.info(f'Loaded audio: {path}')
            return True
        except Exception as e:
            player_logger.logger.error(f'Failed to load audio: {e}')
            self._loaded = False
            return False

    def play(self):
        if not self._loaded:
            player_logger.logger.warning('No audio loaded')
            return
        try:
            pygame.mixer.music.play()
            self._playing = True
            self._paused = False
            player_logger.logger.info('Playback started')
        except Exception as e:
            player_logger.logger.error(f'Playback error: {e}')

    def play_beep(self, path: str) -> bool:
        """Toca um beep curto em um canal separado (não interfere na música carregada).

        Usa ``pygame.mixer.Sound`` (canal próprio) em vez de ``pygame.mixer.music``, para
        não parar a faixa carregada. O Sound é cacheado por caminho. Retorna True se tocou.
        """
        try:
            if self._beep_sound is None or self._beep_path != path:
                self._beep_sound = pygame.mixer.Sound(path)
                self._beep_path = path
            self._beep_sound.play()
            player_logger.logger.info(f'Beep played: {path}')
            return True
        except Exception as e:
            player_logger.logger.error(f'Beep playback error: {e}')
            return False

    def stop(self):
        try:
            pygame.mixer.music.stop()
            self._playing = False
            self._paused = False
            player_logger.logger.info('Playback stopped')
        except Exception as e:
            player_logger.logger.error(f'Stop error: {e}')

    def get_pos(self) -> float:
        """Return current playback position in seconds (approx)."""
        try:
            ms = pygame.mixer.music.get_pos()
            if ms == -1:
                return 0.0
            return ms / 1000.0
        except Exception:
            return 0.0

    def get_length(self) -> float:
        """Return current track length in seconds if known, else 0.0."""
        return float(self._current_length or 0.0)

    def is_busy(self) -> bool:
        """Retorna True enquanto o mixer estiver realmente reproduzindo áudio.

        Reflete o estado real do pygame e fica False automaticamente quando a
        faixa termina sozinha."""
        try:
            return bool(pygame.mixer.music.get_busy())
        except Exception:
            return False
