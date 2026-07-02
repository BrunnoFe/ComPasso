import os
import time
import random
import threading

from pylsl import local_clock

from . import experiment_logger
from .constants import (MARKER_COUNTDOWN_START, MARKER_MUSIC_START, MARKER_MUSIC_END,
                       MARKER_STOP, CONDITION_MUSICA, CONDITION_RUIDO, RUIDO_KEYWORDS)
from .recorder import LSLRecorder, build_session_dirname, build_track_filename


def _classify_condition(fator: str) -> str:
    """Classifica o fator de uma faixa em 'musica' ou 'ruido'.

    Heurística simples baseada em palavras-chave do valor da coluna `fator`.
    Por padrão, qualquer faixa que não seja ruído é tratada como música.
    """
    f = (fator or "").strip().lower()
    if any(kw in f for kw in RUIDO_KEYWORDS):
        return CONDITION_RUIDO
    return CONDITION_MUSICA


class ExperimentRunner:
    """Orquestra a sessão experimental em uma thread separada da GUI.

    Para cada faixa (em ordem aleatória, sem repetição):
      1. inicia a aquisição LSL e captura `t0` (= marca `countdown_start`);
      2. exibe a contagem regressiva de 10 s;
      3. toca a faixa até o fim, gravando os sinais continuamente;
      4. finaliza o arquivo (CSV em tempo real + XLSX ao final);
      5. aguarda o "continuar" antes da próxima faixa.

    Todo o tempo (amostras e marcadores) usa o relógio `pylsl.local_clock()`.
    A reprodução, a contagem e a aquisição rodam fora da thread da GUI; atualizações
    de interface são agendadas via `ctx.run_after`.
    """

    COUNTDOWN_SECONDS = 10

    def __init__(self, ctx):
        self.ctx = ctx
        self._stop_event = threading.Event()
        self._continue_event = threading.Event()
        self._order = []
        self._session_dir = None
        self._recorder = None
        self._thread = None
        self._running = False
        self._done = {CONDITION_MUSICA: 0, CONDITION_RUIDO: 0}

    def is_running(self) -> bool:
        return self._running

    def is_acquiring(self) -> bool:
        """True enquanto há um recorder ativo puxando amostras (faixa em gravação)."""
        return self._recorder is not None

    def last_acquisition_monotonic(self):
        """Instante (time.monotonic) da última amostra gravada, ou None se não há recorder."""
        rec = self._recorder
        return rec.last_sample_monotonic if rec is not None else None

    def start(self) -> None:
        """Embaralha a ordem das faixas e inicia a sessão em uma thread daemon."""
        if self._running:
            experiment_logger.logger.warning("Experimento já está em execução.")
            return
        if self._thread is not None and self._thread.is_alive():
            experiment_logger.logger.warning("Sessão anterior ainda finalizando; aguarde um instante.")
            return
        files = list(self.ctx.music_files or [])
        if not files:
            experiment_logger.logger.warning("Nenhum arquivo de música para iniciar o experimento.")
            return
        self._order = random.sample(files, len(files))
        self._stop_event.clear() #limpa o evento de parada antes de iniciar
        self._continue_event.clear()
        self._running = True
        experiment_logger.logger.info(f"Iniciando experimento com {len(self._order)} faixa(s) (ordem aleatória).")
        self._thread = threading.Thread(target=self._run_experiment, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Para a sessão a qualquer momento, finalizando o arquivo atual com a marca 'stop'."""
        if not self._running and self._recorder is None:
            return
        experiment_logger.logger.info("Parando experimento.")
        self._stop_event.set()
        self._continue_event.set()  # desbloqueia a espera por 'continuar'
        try:
            self.ctx.player.stop()
        except Exception:
            pass
        rec = self._recorder
        if rec is not None:
            try:
                rec.add_marker(MARKER_STOP, local_clock(), music_file=self.music_name, fator=self.music_fator)
                rec.finalize()
            except Exception as e:
                experiment_logger.logger.error(f"Erro ao finalizar arquivo no stop: {e}")
            self._recorder = None
        self._running = False
        self._set_button("comecar")
        self._post_condition("")
        self._post_status("Experimento interrompido.")

    def continuar(self) -> None:
        """Libera a transição para a próxima faixa (chamado pelo botão 'continuar')."""
        self._continue_event.set()

    # ------------------------------------------------------------------ #
    def _run_experiment(self) -> None:
        # pasta única da sessão de coleta (criada uma vez, antes da primeira faixa)
        session_name = build_session_dirname(self.ctx)
        self._session_dir = os.path.join(self.ctx.save_dir, session_name)
        try:
            os.makedirs(self._session_dir, exist_ok=True)
        except OSError as e:
            experiment_logger.logger.error(f"Não foi possível criar a pasta da sessão '{self._session_dir}': {e}")
            self._post_status("Erro ao criar a pasta de salvamento. Experimento abortado.")
            self._finish()
            return
        experiment_logger.logger.info(f"Pasta da sessão criada: {self._session_dir}")

        totals = {CONDITION_MUSICA: 0, CONDITION_RUIDO: 0}
        for path in self._order:
            totals[_classify_condition(self.ctx.music_condition_mapping.get(path, ""))] += 1
        self._done = {CONDITION_MUSICA: 0, CONDITION_RUIDO: 0}
        self._update_counters(totals)

        for order, path in enumerate(self._order, start=1):
            if self._stop_event.is_set():
                break
            self._run_track(order, path, totals)
            if self._stop_event.is_set():
                break
            # aguarda o 'continuar' antes da próxima faixa
            self._set_button("continuar")
            self._post_status("Faixa concluída. Clique em continuar para a próxima.")
            self._continue_event.clear()
            self._continue_event.wait()
            if self._stop_event.is_set():
                break

        self._finish()

    def _run_track(self, order: int, path: str, totals: dict) -> None:
        self.music_name = os.path.basename(path)
        self.music_fator = self.ctx.music_condition_mapping.get(path, "")
        cat = _classify_condition(self.music_fator)

        self._set_button("rodando")

        # 1) aquisição + captura de t0 (drena buffer -> t0 -> primeira linha, sem lacuna)
        filename = build_track_filename(order, len(self._order), self.music_name)

        csv_path = os.path.join(self._session_dir, filename + ".csv") #type: ignore
        experiment_logger.logger.info(f"Preparando aquisição LSL para '{self.music_name}' (fator: '{self.music_fator}') -> {csv_path}")
        recorder = LSLRecorder(self.ctx.bitalino, self.ctx.signal_channel, csv_path)
        self._recorder = recorder
        t0 = recorder.start()
        recorder.add_marker(MARKER_COUNTDOWN_START, t0, music_file=self.music_name, fator=self.music_fator)

        # 2) contagem regressiva de 10 s
        for remaining in range(self.COUNTDOWN_SECONDS, 0, -1):
            if self._stop_event.is_set():
                return
            self._post_status(f"Preparando '{self.music_name}' — iniciando em {remaining}s")
            time.sleep(1.0)
        if self._stop_event.is_set():
            return

        # 3) início da música
        if not self.ctx.player.load(path):
            experiment_logger.logger.error(f"Falha ao carregar áudio; pulando faixa: {path}")
            self._post_status(f"Falha ao carregar '{self.music_name}'; pulando faixa.")
            recorder.stop()
            recorder.finalize()
            self._recorder = None
            return
        ts_start = local_clock()
        recorder.add_marker(MARKER_MUSIC_START, ts_start, music_file=self.music_name, fator=self.music_fator)
        self.ctx.player.play()
        self._post_current_music(self.music_name)
        self._post_condition(" música " if cat == CONDITION_MUSICA else " ruído ")
        self._post_status(f"Reproduzindo: {self.music_name}")

        # 4) aguarda o fim da faixa (ou stop)
        self._wait_track_end()
        if self._stop_event.is_set():
            return

        # 5) fim da música + finalização do arquivo
        ts_end = local_clock()
        recorder.add_marker(MARKER_MUSIC_END, ts_end, music_file=self.music_name, fator=self.music_fator)
        recorder.stop()
        recorder.finalize()
        self._recorder = None

        self._done[cat] = self._done.get(cat, 0) + 1
        self._update_counters(totals)
        self._post_condition("")

    def _wait_track_end(self) -> None:
        """Aguarda enquanto o mixer estiver tocando, abortando se houver stop."""
        # pequena folga para o pygame reportar busy=True após o play()
        time.sleep(0.3)
        while self.ctx.player.is_busy():
            if self._stop_event.is_set():
                return
            time.sleep(0.2)

    def _finish(self) -> None:
        self._running = False
        self._set_button("comecar")
        self._post_condition("")
        if not self._stop_event.is_set():
            experiment_logger.logger.info("Experimento finalizado.")
            self._post_status("Experimento finalizado.")

    # ------------------------------------------------------------------ #
    def _set_button(self, state: str) -> None:
        cb = getattr(self.ctx, "set_button_state", None)
        if cb is not None:
            self.ctx.run_after(lambda: cb(state))

    def _post_status(self, text: str) -> None:
        self.ctx.run_after(lambda: self.ctx.status_text.set(text))

    def _post_current_music(self, text: str) -> None:
        self.ctx.run_after(lambda: self.ctx.current_music_text.set(text))

    def _post_condition(self, text: str) -> None:
        self.ctx.run_after(lambda: self.ctx.current_condition_text.set(text))

    def _update_counters(self, totals: dict) -> None:
        done = dict(self._done)
        total_tracks = totals[CONDITION_MUSICA] + totals[CONDITION_RUIDO]
        done_tracks = done[CONDITION_MUSICA] + done[CONDITION_RUIDO]
        frac = (done_tracks / total_tracks) if total_tracks else 0.0

        def apply():
            self.ctx.music_done_text.set(str(done[CONDITION_MUSICA]))
            self.ctx.music_total_text.set(str(totals[CONDITION_MUSICA]))
            self.ctx.ruido_done_text.set(str(done[CONDITION_RUIDO]))
            self.ctx.ruido_total_text.set(str(totals[CONDITION_RUIDO]))
            self.ctx.session_progress.set(frac)
            self.ctx.session_status_text.set(f"{done_tracks} / {total_tracks}")

        self.ctx.run_after(apply)
