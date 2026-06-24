import os
import time
import random
import threading

from pylsl import local_clock

from . import experiment_logger
from .recorder import LSLRecorder, build_output_basename


def _classify_condition(fator: str) -> str:
    """Classifica o fator de uma faixa em 'musica', 'pausa' ou 'ruido'.

    Heurística simples baseada em palavras-chave do valor da coluna `fator`.
    Por padrão, qualquer faixa que não seja pausa nem ruído é tratada como música.
    """
    f = (fator or "").strip().lower()
    if "pausa" in f:
        return "pausa"
    if "ruido" in f or "ruído" in f:
        return "ruido"
    return "musica"


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
        self._recorder = None
        self._thread = None
        self._running = False
        self._done = {"musica": 0, "pausa": 0, "ruido": 0}

    def is_running(self) -> bool:
        return self._running

    def start(self) -> None:
        """Embaralha a ordem das faixas e inicia a sessão em uma thread daemon."""
        if self._running:
            experiment_logger.logger.warning("Experimento já está em execução.")
            return
        files = list(self.ctx.music_files or [])
        if not files:
            experiment_logger.logger.warning("Nenhum arquivo de música para iniciar o experimento.")
            return
        self._order = random.sample(files, len(files))
        self._stop_event.clear()
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
                rec.add_marker("stop", local_clock())
                rec.finalize()
            except Exception as e:
                experiment_logger.logger.error(f"Erro ao finalizar arquivo no stop: {e}")
            self._recorder = None
        self._running = False
        self._set_button("comecar")
        self._post_status("Experimento interrompido.")

    def continuar(self) -> None:
        """Libera a transição para a próxima faixa (chamado pelo botão 'continuar')."""
        self._continue_event.set()

    # ------------------------------------------------------------------ #
    def _run_experiment(self) -> None:
        totals = {"musica": 0, "pausa": 0, "ruido": 0}
        for path in self._order:
            totals[_classify_condition(self.ctx.music_condition_mapping.get(path, ""))] += 1
        self._done = {"musica": 0, "pausa": 0, "ruido": 0}
        self._update_counters(totals)

        for path in self._order:
            if self._stop_event.is_set():
                break
            self._run_track(path, totals)
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

    def _run_track(self, path: str, totals: dict) -> None:
        name = os.path.basename(path)
        fator = self.ctx.music_condition_mapping.get(path, "")
        cat = _classify_condition(fator)

        self._set_button("rodando")

        # 1) aquisição + captura de t0 (drena buffer -> t0 -> primeira linha, sem lacuna)
        csv_path = os.path.join(self.ctx.save_dir, build_output_basename(self.ctx) + ".csv")
        recorder = LSLRecorder(self.ctx.bitalino, self.ctx.signal_channel, csv_path)
        self._recorder = recorder
        t0 = recorder.start()
        recorder.add_marker("countdown_start", t0)

        # 2) contagem regressiva de 10 s
        for remaining in range(self.COUNTDOWN_SECONDS, 0, -1):
            if self._stop_event.is_set():
                return
            self._post_status(f"Preparando '{name}' — iniciando em {remaining}s")
            time.sleep(1.0)
        if self._stop_event.is_set():
            return

        # 3) início da música
        self.ctx.player.load(path)
        ts_start = local_clock()
        recorder.add_marker("music_start", ts_start, music_file=name, fator=fator)
        self.ctx.player.play()
        self._post_current_music(f"Música: {name}")
        self._post_status(f"Reproduzindo: {name}")

        # 4) aguarda o fim da faixa (ou stop)
        self._wait_track_end()
        if self._stop_event.is_set():
            return

        # 5) fim da música + finalização do arquivo
        ts_end = local_clock()
        recorder.add_marker("music_end", ts_end)
        recorder.stop()
        recorder.finalize()
        self._recorder = None

        self._done[cat] = self._done.get(cat, 0) + 1
        self._update_counters(totals)

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

    def _update_counters(self, totals: dict) -> None:
        done = dict(self._done)
        self.ctx.run_after(lambda: self.ctx.music_counter.set(f"Música: {done['musica']} de {totals['musica']}"))
        self.ctx.run_after(lambda: self.ctx.pausa_counter.set(f"Pausa: {done['pausa']} de {totals['pausa']}"))
        self.ctx.run_after(lambda: self.ctx.ruido_counter.set(f"Ruído: {done['ruido']} de {totals['ruido']}"))
