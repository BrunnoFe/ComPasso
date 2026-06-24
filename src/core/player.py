import threading
import time

from . import player_logger

try:
    import pygame
except Exception:
    pygame = None


class Player:
    """Audio player with playlist support using pygame.mixer.

    Methods:
      - load(path) -> bool
      - play()
      - stop()
      - is_busy()
      - play_playlist(list_of_paths)
      - stop_playlist()
      - get_pos()
    """
    def __init__(self):
        self._loaded = False
        self._playing = False
        self._paused = False
        self._path = None
        self._current_length = 0.0
        self._current_index = None
        self._playlist_loaded = False

        self._playlist_thread = None
        self._playlist = []
        self._stop_event = threading.Event()

        if pygame is not None:
            try:
                pygame.mixer.init()
            except Exception as e:
                player_logger.logger.warning(f'pygame.mixer.init() failed: {e}')

    def load(self, path: str) -> bool:
        """Load a single audio file. Returns True on success."""
        if pygame is None:
            player_logger.logger.error('pygame not available — install pygame to enable audio playback')
            return False

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

        Diferente de `is_playing()`, reflete o estado real do pygame e fica False
        automaticamente quando a faixa termina sozinha."""
        try:
            return bool(pygame.mixer.music.get_busy())
        except Exception:
            return False

    def is_playing(self) -> bool:
        return bool(self._playing and not self._paused)

    def is_paused(self) -> bool:
        return bool(self._paused)

    def set_playlist(self, paths: list) -> None:
        """Set playlist without starting playback."""
        self._playlist = paths or []
        self._playlist_loaded = bool(self._playlist)
        self._current_index = 0 if self._playlist else None

    def play_playlist(self, paths: list, start_index: int = 0,
                      on_track_start=None, on_finished=None) -> None:
        """Play a list of audio files sequentially in a background thread.

        :param paths: lista de caminhos de áudio.
        :param start_index: índice inicial da playlist.
        :param on_track_start: callback opcional `on_track_start(idx, path)` chamado no
            início de cada faixa, a partir da thread da playlist.
        :param on_finished: callback opcional `on_finished(finished_naturally)` chamado
            ao terminar (naturalmente ou por stop), a partir da thread da playlist.

        Observação: os callbacks rodam na thread da playlist — quem consome deve
        repassar para a thread da GUI (ex.: `AppContext.post`) antes de tocar widgets.
        """
        if pygame is None:
            player_logger.logger.error('pygame not available — install pygame to enable audio playback')
            return

        if not paths:
            player_logger.logger.warning('Empty playlist')
            return

        # stop any running playlist
        self.stop_playlist()

        self._playlist = paths
        self._stop_event.clear()
        self._playlist_thread = threading.Thread(
            target=self._playlist_worker, args=(start_index, on_track_start, on_finished), daemon=True)
        self._playlist_thread.start()

    def _playlist_worker(self, start_index: int = 0, on_track_start=None, on_finished=None):
        player_logger.logger.info(f'Starting playlist with {len(self._playlist)} tracks (start_index={start_index})')
        finished_naturally = True
        for idx in range(start_index, len(self._playlist)):
            if self._stop_event.is_set():
                finished_naturally = False
                break
            self._current_index = idx
            path = self._playlist[idx]
            ok = self.load(path)
            if not ok:
                player_logger.logger.error(f'Skipping track due to load failure: {path}')
                continue
            if on_track_start is not None:
                try:
                    on_track_start(idx, path)
                except Exception as e:
                    player_logger.logger.error(f'on_track_start callback error: {e}')
            try:
                pygame.mixer.music.play()
                self._playing = True
                self._paused = False
                player_logger.logger.info(f'Playing track {idx+1}/{len(self._playlist)}: {path}')
                # wait until playback finishes or stop requested
                while pygame.mixer.music.get_busy():
                    if self._stop_event.is_set():
                        pygame.mixer.music.stop()
                        finished_naturally = False
                        break
                    time.sleep(0.2)
            except Exception as e:
                player_logger.logger.error(f'Error during playback of {path}: {e}')

        self._playing = False
        # ao terminar a playlist inteira, reinicia o índice para permitir nova reprodução do começo
        if finished_naturally:
            self._current_index = 0
        player_logger.logger.info('Playlist finished or stopped')
        if on_finished is not None:
            try:
                on_finished(finished_naturally)
            except Exception as e:
                player_logger.logger.error(f'on_finished callback error: {e}')

    def stop_playlist(self):
        """Para a playlist em execução, preservando a lista carregada para permitir nova reprodução."""
        self._stop_event.set()
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass
        if self._playlist_thread and self._playlist_thread.is_alive():
            # give thread a moment to exit
            self._playlist_thread.join(timeout=1.0)
        self._playlist_thread = None
        self._playing = False
        self._paused = False
        # mantém self._playlist e self._playlist_loaded para permitir tocar novamente;
        # reinicia o índice para o começo (Stop reinicia, ao contrário de Pause)
        self._current_index = 0 if self._playlist else None
