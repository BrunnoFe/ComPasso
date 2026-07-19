"""Reprodução de áudio via PySide6 QtMultimedia (substitui o antigo backend pygame.mixer).

Faixa e beep são tocados pelo **mesmo backend**: dois pares ``QMediaPlayer`` + ``QAudioOutput``
independentes (canais paralelos — o beep nunca interrompe a faixa). Usar o mesmo motor nos dois
é deliberado: a latência entre chamar ``play()`` e o som sair é da ordem de dezenas de ms e
varia por backend; com backends iguais essa latência se **cancela** no intervalo beep→áudio,
que é a grandeza que o experimento precisa ter exata. A duração vem de
``QMediaPlayer.duration()``, do mesmo motor que reproduz, então ``get_length()`` bate com a
reprodução real.

**Threading.** ``QMediaPlayer``/``QAudioOutput`` são QObjects orientados a sinais que precisam
viver na thread com event loop (a da GUI). O ``Player`` é criado nessa thread (em
``Context.__init__``), então os objetos herdam a afinidade correta. O ``ExperimentRunner``,
porém, chama ``load``/``play``/``stop`` de uma **thread worker**; essas chamadas são encaminhadas
à thread da GUI via ``QMetaObject.invokeMethod`` (chamada direta quando já se está na GUI —
invocar ``BlockingQueuedConnection`` da própria thread travaria). O estado consultado em polling
(``is_busy``/``get_pos``/``get_length``) é mantido em atributos cacheados, escritos apenas nos
handlers de sinal (thread da GUI) sob ``Lock`` e lidos de forma barata pela worker.

``play_beep`` é a exceção: despacha em ``QueuedConnection`` (não bloqueante) porque é chamado
dentro da janela cronometrada do experimento, onde bloquear a worker esperando a GUI
introduziria justamente a variação que a refatoração elimina. A source do beep é carregada uma
única vez no arranque (``preload_beep``), então o trabalho restante na GUI é só o ``play()``.

O fim da faixa é sinalizado por ``_fim_faixa`` (``threading.Event``), setado no ``EndOfMedia`` —
a worker espera nele com ``aguardar_fim`` em vez de fazer polling, o que dava um erro de até
200 ms no marcador ``music_end`` e na âncora do eixo X do gráfico.

API pública: ``load(path)->bool``, ``play()``, ``stop()``, ``aguardar_fim(timeout)->bool``,
``is_busy()->bool``, ``get_pos()->float`` (s), ``get_length()->float`` (s),
``preload_beep(path)``, ``play_beep()->bool``.
"""

import os
import threading

from PySide6.QtCore import QObject, Signal, Slot, QThread, QTimer, QUrl, QMetaObject, Qt
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

from . import player_logger

# Tempo máximo (s) de espera pela carga assíncrona de uma faixa antes de desistir.
_LOAD_TIMEOUT_S = 10.0
# Tempo máximo (s) de espera pela duração de um arquivo durante a pré-varredura. Curto de
# propósito: um arquivo problemático não pode segurar a fila inteira.
_SONDA_TIMEOUT_MS = 5000


class SondaDuracao(QObject):
    """Lê a duração de uma lista de arquivos de áudio sem bloquear a thread da GUI.

    Usa um ``QMediaPlayer`` **sem** ``QAudioOutput`` (nunca emite som) que percorre os caminhos
    um a um, encadeado por sinais: cada ``LoadedMedia``/``InvalidMedia`` dispara o próximo. Roda
    na thread da GUI, mas cada passo é só o despacho de um sinal — o custo por quadro é
    desprezível.

    Existe para que o eixo X do gráfico já nasça com a duração correta em ``begin()``, em vez de
    ser reancorado no fim da faixa; e para tirar o ``load()`` bloqueante da janela cronometrada
    do experimento.
    """

    concluida = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sonda = QMediaPlayer()
        self._sonda.mediaStatusChanged.connect(self._on_status)
        self._sonda.durationChanged.connect(self._on_duration)
        self._fila = []
        self._atual = None
        self._duracoes = {}
        self._trava = threading.Lock()
        # um arquivo que carregue mas nunca anuncie duração > 0 travaria a fila inteira; o
        # watchdog o descarta e segue para o próximo.
        self._watchdog = QTimer(self)
        self._watchdog.setSingleShot(True)
        self._watchdog.setInterval(_SONDA_TIMEOUT_MS)
        self._watchdog.timeout.connect(self._on_timeout)

    def duracoes(self) -> dict:
        """Cópia do mapa ``caminho -> duração (s)`` conhecido até agora."""
        with self._trava:
            return dict(self._duracoes)

    def sondar(self, caminhos) -> None:
        """Enfileira os caminhos ainda desconhecidos e inicia a varredura (idempotente)."""
        with self._trava:
            conhecidos = set(self._duracoes)
        novos = [c for c in caminhos if c not in conhecidos and c not in self._fila]
        if not novos:
            self.concluida.emit()
            return
        self._fila.extend(novos)
        if self._atual is None:
            self._proximo()

    def _agendar_proximo(self) -> None:
        """Sai do handler de sinal antes de trocar a source.

        Chamar ``setSource`` de dentro de ``durationChanged``/``mediaStatusChanged`` reentra no
        ``QMediaPlayer`` enquanto ele ainda está emitindo — o que derruba o processo com
        access violation (reproduzido: o crash acontecia no 2º arquivo da fila). O
        ``singleShot(0)`` devolve o controle ao laço de eventos primeiro.
        """
        self._watchdog.stop()
        self._atual = None
        QTimer.singleShot(0, self._proximo)

    def _proximo(self) -> None:
        if not self._fila:
            self._sonda.setSource(QUrl())
            player_logger.logger.info(
                f"Pré-varredura de durações concluída ({len(self._duracoes)} arquivo(s)).")
            self.concluida.emit()
            return
        self._atual = self._fila.pop(0)
        self._sonda.setSource(QUrl.fromLocalFile(self._atual))
        self._watchdog.start()

    def _descartar(self, motivo: str) -> None:
        """Abandona o arquivo corrente e segue a fila; a duração cai no fallback do runner."""
        player_logger.logger.warning(
            f"Duração de '{os.path.basename(self._atual or '')}' não pôde ser lida ({motivo}); "
            "o eixo do gráfico usará a duração informada na carga da faixa.")
        self._agendar_proximo()

    @Slot("qint64")
    def _on_duration(self, ms) -> None:
        # setSource(QUrl()) e as trocas de faixa emitem 0; só um valor real conclui a sondagem.
        if ms > 0 and self._atual is not None:
            with self._trava:
                self._duracoes[self._atual] = ms / 1000.0
            self._agendar_proximo()

    @Slot(QMediaPlayer.MediaStatus)
    def _on_status(self, status) -> None:
        if status == QMediaPlayer.MediaStatus.InvalidMedia and self._atual is not None:
            self._descartar("mídia inválida")

    @Slot()
    def _on_timeout(self) -> None:
        if self._atual is not None:
            self._descartar("tempo esgotado")


class Player(QObject):
    """Reprodutor de áudio (faixa + beep) sobre QtMultimedia, com API thread-safe.

    Ver o docstring do módulo para o modelo de threading. Métodos que tocam os QObjects de
    mídia rodam sempre na thread da GUI (diretamente ou via ``invokeMethod``); os getters de
    estado leem atributos cacheados sob ``self._lock``.
    """

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

        # --- beep de aviso: par independente, mesmo backend (ver docstring do módulo) ---
        # canal separado para que o beep toque em paralelo com a faixa sem interrompê-la;
        # mesmo motor para que as latências de saída se cancelem no intervalo beep->áudio.
        self._beep_out = QAudioOutput()
        self._beep_out.setVolume(1.0)
        self._beep_player = QMediaPlayer()
        self._beep_player.setAudioOutput(self._beep_out)
        self._beep_path = None

        # --- estado cacheado (escrito nos handlers de sinal na GUI, lido pela worker) ---
        self._lock = threading.Lock()
        self._busy = False
        self._duration_s = 0.0
        self._position_s = 0.0
        self._loaded = False

        # fim da faixa: setado no EndOfMedia/stop, aguardado por `aguardar_fim` na worker.
        # Substitui o antigo polling de is_busy() a cada 200 ms, que atrasava o marcador
        # `music_end` e a âncora do eixo X do gráfico na mesma medida.
        self._fim_faixa = threading.Event()

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
        self._fim_faixa.clear()
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
        # libera quem estiver em aguardar_fim(): um stop manual encerra a faixa tanto quanto
        # o fim natural.
        self._fim_faixa.set()
        player_logger.logger.info("Reprodução parada")

    def preload_beep(self, path: str) -> None:
        """Carrega o beep uma única vez, no arranque do app (``beep_caminho`` é fixo na sessão).

        Deixar a source pronta com antecedência é o que permite que ``play_beep`` seja apenas um
        ``play()`` durante a contagem regressiva, sem a inicialização de backend que atrasaria o
        primeiro beep do experimento.
        """
        self._beep_path = path
        self._invocar("_do_preload_beep")

    @Slot()
    def _do_preload_beep(self) -> None:
        """(Thread GUI) Aponta o player do beep para o arquivo e o deixa pronto."""
        if not self._beep_path:
            return
        self._beep_player.setSource(QUrl.fromLocalFile(self._beep_path))
        player_logger.logger.info(f"Beep pré-carregado: {self._beep_path}")

    def play_beep(self) -> bool:
        """Toca o beep pré-carregado em canal separado (não interfere na faixa).

        Despacha em ``QueuedConnection`` e retorna imediatamente: é chamado dentro da janela
        cronometrada do experimento, onde bloquear a worker esperando a GUI reintroduziria a
        variação que o agendamento por instantes absolutos elimina. O retorno indica só que o
        pedido foi despachado.
        """
        if not self._beep_path:
            player_logger.logger.warning("play_beep sem beep pré-carregado; nada a tocar.")
            return False
        if self._na_thread_gui():
            self._do_play_beep()
        else:
            QMetaObject.invokeMethod(self, "_do_play_beep", Qt.QueuedConnection)
        return True

    @Slot()
    def _do_play_beep(self) -> None:
        """(Thread GUI) Rebobina e toca o beep."""
        try:
            self._beep_player.setPosition(0)
            self._beep_player.play()
        except Exception as e:
            player_logger.logger.error(f"Erro ao tocar beep: {e}")

    # ---------------------------------------------- leituras cacheadas (worker)
    def aguardar_fim(self, timeout: float) -> bool:
        """Bloqueia até o fim natural da faixa (ou ``stop``). True se o fim chegou a tempo.

        O `timeout` é uma rede de segurança (duração conhecida + folga): se o ``EndOfMedia``
        nunca vier — backend travado, arquivo corrompido —, a sessão segue em vez de ficar
        pendurada para sempre.
        """
        return self._fim_faixa.wait(timeout)

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
            # fim natural da faixa: acorda `aguardar_fim` no runner no instante real do fim,
            # que é quando o marcador `music_end` é carimbado.
            with self._lock:
                self._busy = False
            self._fim_faixa.set()

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
