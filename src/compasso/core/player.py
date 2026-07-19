"""Reprodução de áudio via PySide6 QtMultimedia (substitui o antigo backend pygame.mixer).

A faixa é tocada por ``QMediaPlayer`` + ``QAudioOutput`` e o beep de aviso por ``QSoundEffect``
(canal independente, toca em paralelo, numa thread própria — ver ``_BeepWorker`` abaixo). A
duração vem de ``QMediaPlayer.duration()`` — do mesmo motor que reproduz o áudio —, então
``get_length()`` bate com a reprodução real (o eixo X do gráfico deixa de sobrar espaço no fim,
ver ``gui_qt/signal_chart.py``).

**Threading (faixa).** ``QMediaPlayer``/``QAudioOutput`` são QObjects orientados a sinais que
precisam viver na thread com event loop (a da GUI). O ``Player`` é criado nessa thread (em
``Context.__init__``), então os objetos herdam a afinidade correta. O ``ExperimentRunner``,
porém, chama ``load``/``play``/``stop`` de uma **thread worker**; essas chamadas são encaminhadas
à thread da GUI via ``QMetaObject.invokeMethod`` (chamada direta quando já se está na GUI —
invocar ``BlockingQueuedConnection`` da própria thread travaria). O estado consultado em polling
(``is_busy``/``get_pos``/``get_length``) é mantido em atributos cacheados, escritos apenas nos
handlers de sinal (thread da GUI) sob ``Lock`` e lidos de forma barata pela worker.

**Threading (beep).** O beep tem sua **própria** ``QThread`` com event loop dedicado (não a da
GUI). ``QSoundEffect.setSource()`` faz, na primeira vez que um caminho é carregado, uma
inicialização síncrona do backend de áudio que trava a thread onde roda por ~250 ms (medido) — um
travamento perceptível se fosse a thread da GUI, no meio da contagem regressiva do experimento.
Rodando numa thread separada, esse custo nunca é sentido pela UI, não importa quando o primeiro
beep aconteça. `preload_beep`/`play_beep` disparam via **sinais Qt** (``Signal``) em vez de
``invokeMethod``: a emissão de sinal entre threads é resolvida para ``QueuedConnection``
automaticamente pelo Qt (a decisão é tomada na emissão, não na conexão), então funciona
corretamente seja chamado da thread da GUI ou da worker — e não bloqueia nenhuma das duas.

API pública (idêntica ao backend antigo): ``load(path)->bool``, ``play()``, ``stop()``,
``is_busy()->bool``, ``get_pos()->float`` (s), ``get_length()->float`` (s), ``play_beep(path)->bool``.
"""

import threading

from PySide6.QtCore import QObject, Signal, Slot, QThread, QUrl, QMetaObject, Qt, QCoreApplication
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput, QSoundEffect

from . import player_logger

# Tempo máximo (s) de espera pela carga assíncrona de uma faixa antes de desistir.
_LOAD_TIMEOUT_S = 10.0


class _BeepWorker(QObject):
    """Dono do ``QSoundEffect`` do beep; vive na thread dedicada de ``Player._beep_thread``.

    Mantém o mesmo cache por caminho que a faixa não tem motivo para repetir (``beep_caminho``
    é fixo pela sessão) — ``carregar`` só chama ``setSource`` quando o caminho muda.
    """

    def __init__(self):
        super().__init__()
        self._beep = QSoundEffect()
        self._beep.setVolume(1.0)
        self._beep_path = None

    @Slot(str)
    def carregar(self, path: str) -> None:
        if self._beep_path != path:
            self._beep.setSource(QUrl.fromLocalFile(path))
            self._beep_path = path

    @Slot(str)
    def tocar(self, path: str) -> None:
        try:
            self.carregar(path)
            self._beep.play()
            player_logger.logger.info(f"Beep tocado: {path}")
        except Exception as e:
            player_logger.logger.error(f"Erro ao tocar beep: {e}")


class Player(QObject):
    """Reprodutor de áudio (faixa + beep) sobre QtMultimedia, com API thread-safe.

    Ver o docstring do módulo para o modelo de threading. Métodos que tocam os QObjects de
    mídia rodam sempre na thread da GUI (diretamente ou via ``invokeMethod``); os getters de
    estado leem atributos cacheados sob ``self._lock``.
    """

    # sinais que disparam o worker do beep (thread própria); a emissão cross-thread é
    # resolvida para QueuedConnection automaticamente pelo Qt — ver docstring do módulo.
    _pedirCarregarBeep = Signal(str)
    _pedirTocarBeep = Signal(str)

    def __init__(self):
        super().__init__()

        # --- objetos de áudio da faixa (afinidade: thread da GUI) ---
        self._audio_out = QAudioOutput()
        # volume cheio: a intensidade continua governada pelo volume master do SO
        # (core/audio.py), preservando a semântica da coluna "volume" gravada.
        self._audio_out.setVolume(1.0)
        self._qplayer = QMediaPlayer()
        self._qplayer.setAudioOutput(self._audio_out)   # obrigatório, senão não há som

        self._qplayer.mediaStatusChanged.connect(self._on_media_status)
        self._qplayer.playbackStateChanged.connect(self._on_playback_state)
        self._qplayer.durationChanged.connect(self._on_duration)
        self._qplayer.positionChanged.connect(self._on_position)

        # beep de aviso: thread própria com event loop dedicado (ver _BeepWorker/docstring do
        # módulo) para que a inicialização do QSoundEffect nunca trave a thread da GUI.
        self._beep_thread = QThread()
        self._beep_thread.setObjectName("ComPassoBeepThread")
        self._beep_worker = _BeepWorker()
        self._beep_worker.moveToThread(self._beep_thread)
        self._pedirCarregarBeep.connect(self._beep_worker.carregar)
        self._pedirTocarBeep.connect(self._beep_worker.tocar)
        self._beep_thread.start()
        app = QCoreApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self._encerrar_beep_thread)

        # --- estado cacheado (escrito nos handlers de sinal na GUI, lido pela worker) ---
        self._lock = threading.Lock()
        self._busy = False
        self._duration_s = 0.0
        self._position_s = 0.0
        self._loaded = False

        # sincronização da carga assíncrona de faixa. A carga só é dada por concluída quando
        # a faixa chega a LoadedMedia E uma nova duração (>0) é anunciada — ver _do_load.
        self._load_event = threading.Event()
        self._load_ok = False
        self._got_duration = False
        self._pending_path = None

    # ------------------------------------------------------------------ helpers
    def _na_thread_gui(self) -> bool:
        """True se o chamador já está na thread onde os QObjects de mídia vivem."""
        return QThread.currentThread() == self.thread()

    def _invocar(self, nome_slot: str) -> None:
        """Executa o slot ``nome_slot`` na thread da GUI (direto se já estiver nela).

        Usa ``BlockingQueuedConnection`` a partir de outra thread para que a operação
        complete antes de retornar; chamar assim da própria thread da GUI travaria, por isso
        o desvio para chamada direta.
        """
        if self._na_thread_gui():
            getattr(self, nome_slot)()
        else:
            QMetaObject.invokeMethod(self, nome_slot, Qt.BlockingQueuedConnection)

    # -------------------------------------------------------------- API pública
    def load(self, path: str) -> bool:
        """Carrega uma faixa. Retorna True em sucesso (mídia válida e pronta).

        A carga do ``QMediaPlayer`` é assíncrona (a duração só é conhecida em
        ``LoadedMedia``); por isso bloqueia a thread chamadora num evento até o resultado
        chegar (ou ``_LOAD_TIMEOUT_S`` esgotar). Após o retorno True, ``get_length()`` já
        reflete a duração real.
        """
        self._pending_path = path
        self._load_ok = False
        self._got_duration = False
        self._load_event.clear()
        if self._na_thread_gui():
            self._do_load()
        else:
            QMetaObject.invokeMethod(self, "_do_load", Qt.QueuedConnection)
        if not self._load_event.wait(_LOAD_TIMEOUT_S):
            player_logger.logger.error(f"Timeout ao carregar áudio: {path}")
            return False
        return self._load_ok

    @Slot()
    def _do_load(self) -> None:
        """(Thread GUI) Reseta o estado e dispara a carga da nova faixa."""
        with self._lock:
            self._loaded = False
            self._duration_s = 0.0
            self._position_s = 0.0
            self._busy = False
        self._got_duration = False
        self._load_ok = False
        self._qplayer.stop()
        # limpa a source antes de trocar: força o QMediaPlayer a reemitir durationChanged para a
        # nova faixa. Sem isso, logo após um EndOfMedia (ou ao recarregar o mesmo arquivo), o
        # LoadedMedia chega com a duração da faixa ANTERIOR ainda em cache — e load()/get_length()
        # devolveriam o valor antigo, deixando o eixo X do gráfico com a duração da faixa passada.
        self._qplayer.setSource(QUrl())
        self._qplayer.setSource(QUrl.fromLocalFile(self._pending_path))
        # a conclusão (LoadedMedia + durationChanged>0) ou a falha (InvalidMedia) liberam o evento.

    def play(self) -> None:
        """Inicia a reprodução da faixa carregada (do início)."""
        self._invocar("_do_play")

    @Slot()
    def _do_play(self) -> None:
        """(Thread GUI) Toca a faixa do início; marca _busy antes de retornar."""
        if not self._loaded:
            player_logger.logger.warning("Nenhum áudio carregado")
            return
        self._qplayer.setPosition(0)
        self._qplayer.play()
        # marca _busy imediatamente para fechar a corrida com o sinal PlayingState (a worker
        # pode consultar is_busy() antes de o estado de reprodução chegar).
        with self._lock:
            self._busy = True
        player_logger.logger.info("Reprodução iniciada")

    def stop(self) -> None:
        """Para a reprodução da faixa."""
        self._invocar("_do_stop")

    @Slot()
    def _do_stop(self) -> None:
        """(Thread GUI) Para a faixa e zera _busy."""
        self._qplayer.stop()
        with self._lock:
            self._busy = False
        player_logger.logger.info("Reprodução parada")

    def preload_beep(self, path: str) -> None:
        """Prepara o beep com antecedência, na thread própria do beep (não bloqueia nada).

        Chamado uma vez no arranque do app (``beep_caminho`` é fixo pela sessão) para que a
        inicialização do ``QSoundEffect`` (~250 ms medido) aconteça cedo; como roda numa thread
        separada da GUI (ver docstring do módulo), isso é só uma otimização de latência — sem
        preload, o primeiro ``play_beep`` funcionaria igual, só que com um leve atraso na thread
        do beep (nunca na da GUI).
        """
        self._pedirCarregarBeep.emit(path)

    def play_beep(self, path: str) -> bool:
        """Toca um beep curto em canal separado (não interfere na faixa).

        Fica inteiramente na thread do beep, então este método nunca bloqueia a chamadora. O
        retorno indica apenas que o pedido foi despachado (nenhum chamador atual usa o valor
        para decidir algo — ver ``ExperimentRunner``).
        """
        self._pedirTocarBeep.emit(path)
        return True

    def _encerrar_beep_thread(self) -> None:
        """Encerra a thread do beep de forma limpa ao fechar o app (evita warning do Qt)."""
        self._beep_thread.quit()
        self._beep_thread.wait(2000)

    # ---------------------------------------------- leituras cacheadas (worker)
    def is_busy(self) -> bool:
        """True enquanto a faixa está tocando; vira False sozinho ao terminar (EndOfMedia)."""
        with self._lock:
            return self._busy

    def get_pos(self) -> float:
        """Posição atual da reprodução, em segundos."""
        with self._lock:
            return self._position_s

    def get_length(self) -> float:
        """Duração da faixa carregada, em segundos (0.0 se desconhecida)."""
        with self._lock:
            return self._duration_s

    # ------------------------------------------------ handlers de sinal (GUI)
    @Slot(QMediaPlayer.MediaStatus)
    def _on_media_status(self, status) -> None:
        """(Thread GUI) Traduz o status da mídia em carga/fim de faixa.

        A duração vem de ``_on_duration`` (não daqui): ``duration()`` pode estar defasada no
        instante do ``LoadedMedia`` (valor da faixa anterior). A carga só conclui quando
        ``LoadedMedia`` e uma duração nova (>0) tiverem chegado (ver ``_talvez_concluir_carga``).
        """
        if status == QMediaPlayer.MediaStatus.LoadedMedia:
            with self._lock:
                self._loaded = True
            self._load_ok = True
            self._talvez_concluir_carga()
        elif status == QMediaPlayer.MediaStatus.InvalidMedia:
            with self._lock:
                self._loaded = False
            self._load_ok = False
            self._load_event.set()
            player_logger.logger.error(f"Falha ao carregar áudio: {self._pending_path}")
        elif status == QMediaPlayer.MediaStatus.NoMedia:
            # transitório: limpeza da source em _do_load (setSource(QUrl())). Não é falha.
            with self._lock:
                self._loaded = False
        elif status == QMediaPlayer.MediaStatus.EndOfMedia:
            # fim natural da faixa: libera o polling de _wait_track_end no runner.
            with self._lock:
                self._busy = False

    @Slot(QMediaPlayer.PlaybackState)
    def _on_playback_state(self, state) -> None:
        """(Thread GUI) Reflete o estado de reprodução em _busy."""
        with self._lock:
            self._busy = (state == QMediaPlayer.PlaybackState.PlayingState)

    @Slot("qint64")
    def _on_duration(self, ms) -> None:
        """(Thread GUI) Atualiza a duração cacheada (ms -> s); >0 sinaliza duração nova pronta."""
        with self._lock:
            self._duration_s = ms / 1000.0
        if ms > 0:
            self._got_duration = True
            self._talvez_concluir_carga()

    def _talvez_concluir_carga(self) -> None:
        """(Thread GUI) Conclui load() só quando a faixa carregou E a duração nova (>0) chegou."""
        if self._load_event.is_set():
            return
        with self._lock:
            pronto = self._loaded and self._got_duration
            dur = self._duration_s
        if pronto:
            self._load_event.set()
            player_logger.logger.info(f"Áudio carregado ({dur:.2f}s): {self._pending_path}")

    @Slot("qint64")
    def _on_position(self, ms) -> None:
        """(Thread GUI) Atualiza a posição cacheada (ms -> s)."""
        with self._lock:
            self._position_s = ms / 1000.0
