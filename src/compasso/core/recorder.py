import os
import csv
import time
import threading
from datetime import datetime

import pandas as pd
from pylsl import local_clock

from . import recorder_logger
from .constants import SESSION_TIMESTAMP_FORMAT, TRACK_ORDER_MIN_WIDTH
from compasso.utils import ENCODING_FORMAT

# Cabeçalho exato exigido pela especificação (ordem das colunas importa).
CSV_HEADER = ["timestamp", "signal", "markers", "music_file", "fator"]


def _sanitize(value: str) -> str:
    """Remove espaços e caracteres problemáticos para uso em nome de arquivo."""
    value = (str(value) if value is not None else "").strip()
    return "".join(c if (c.isalnum() or c in ("-", "_")) else "_" for c in value)


def build_session_dirname(ctx) -> str:
    """Monta o nome da pasta da sessão de coleta no padrão
    `nome_idade_genero_dia-mes-ano_hora-min-seg`.

    O sufixo de data/hora é gerado uma única vez por sessão (no início do
    experimento), de modo que todas as faixas da mesma coleta fiquem na mesma pasta.
    """
    agora = datetime.now()
    suffix = agora.strftime(SESSION_TIMESTAMP_FORMAT)
    nome = _sanitize(ctx.nome)
    idade = _sanitize(ctx.idade)
    genero = _sanitize(ctx.genero)
    return f"{nome}_{idade}_{genero}_{suffix}"


def build_track_filename(order: int, total: int, music_name: str) -> str:
    """Monta o nome base do arquivo de uma faixa no padrão `ordem_nomedamusica`.

    A ordem é a posição da faixa na playlist (1-based), com zero à esquerda para
    ordenação correta no explorador de arquivos (largura mínima de 2 dígitos). A
    extensão do áudio é removida do nome da música.

    :param order: posição da faixa na sequência de reprodução (começa em 1).
    :param total: total de faixas da sessão (define a largura do preenchimento).
    :param music_name: nome do arquivo de áudio (com ou sem extensão).
    :return: nome base sem extensão, ex.: ``"01_minha_musica"``.
    """
    width = max(TRACK_ORDER_MIN_WIDTH, len(str(total)))
    stem = os.path.splitext(music_name)[0]  # remove a extensão do áudio
    return f"{order:0{width}d}_{_sanitize(stem)}"


class LSLRecorder:
    """Aquisição contínua de amostras do BITalino via LSL, gravadas em CSV em tempo real.

    Todas as marcas de tempo — de amostras e de eventos — acabam no relógio local
    (`pylsl.local_clock()`), mas o timestamp devolvido por `pull_sample` **não** nasce nesse
    domínio: ele vem do relógio de quem envia (o host do OpenSignals). Os dois são cristais
    independentes e derivam entre si, então cada amostra é convertida somando
    `inlet.time_correction()`, reconsultado periodicamente — ver `_atualizar_correcao_tempo`.
    Tratar os dois domínios como um só era a causa do deslocamento cumulativo dos marcadores
    ao longo de uma sessão.

    Uso típico:
        rec = LSLRecorder(inlet, channel, csv_path)
        t0 = rec.start()                      # drena o buffer e captura t0, sem lacuna
        rec.add_marker("countdown_start", t0)
        ...
        rec.add_marker("music_start", local_clock(), music_file=nome, fator=fator)
        ...
        rec.add_marker("music_end", local_clock())
        rec.stop()
        csv_path, xlsx_path = rec.finalize()
    """

    PULL_TIMEOUT = 1.0       # s — espera por amostra no loop de aquisição
    FSYNC_INTERVAL = 0.5     # s — intervalo entre fsyncs (durabilidade)
    DRAIN_AFTER_STOP = 2.0   # s — janela para capturar marcadores pendentes após o stop
    # s — com que frequência a correção de relógio é reconsultada durante a aquisição.
    # A deriva entre os dois cristais é da ordem de centenas de ppm (~0.3 ms/s medido no
    # hardware real), então reconsultar a cada 5 s mantém o erro bem abaixo de um intervalo
    # de amostragem.
    INTERVALO_CORRECAO_S = 5.0
    # s — teto para a consulta de `time_correction` (ela troca mensagens com o emissor e
    # poderia travar o loop de aquisição).
    TIMEOUT_CORRECAO_S = 2.0

    def __init__(self, inlet, channel: int, csv_path: str, on_sample=None):
        self.inlet = inlet
        self.channel = int(channel) if channel is not None else 0
        self.csv_path = csv_path
        self.xlsx_path = os.path.splitext(csv_path)[0] + ".xlsx"

        # callback opcional chamado por amostra (timestamp, valor) — usado pelo gráfico
        # em tempo real. Roda na thread de aquisição; deve ser thread-safe e leve.
        self._on_sample = on_sample

        self.t0 = None
        # deslocamento (s) a somar aos timestamps das amostras para levá-los ao domínio do
        # `local_clock()` local — ver `_atualizar_correcao_tempo`.
        self._correcao_tempo = 0.0
        self._ultima_correcao_monotonic = None
        # instante (time.monotonic) da última amostra recebida; lido pelo watchdog de conexão
        self.last_sample_monotonic = None
        self._pending = []           # lista de marcadores ordenada por lsl_time
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = None
        self._first_sample_logged = False

    def _atualizar_correcao_tempo(self) -> None:
        """Reconsulta o deslocamento entre o relógio do emissor e o `local_clock()` local.

        ``pull_sample`` devolve o timestamp no relógio de **quem envia** (o host do
        OpenSignals), que é um cristal diferente do que alimenta ``local_clock()``. Os dois
        derivam um em relação ao outro — medido no hardware real: ~0.17 s acumulados ao longo
        de uma sessão de 12 faixas (~300 ppm). Sem esta correção, todos os marcadores de uma
        faixa aparecem deslocados por igual e o deslocamento cresce faixa a faixa: era esse o
        bug de dessincronização cumulativa.

        ``time_correction()`` é o mecanismo que o próprio LSL oferece para isso. Precisa ser
        **reconsultado periodicamente**, não só uma vez: é a deriva, não o offset inicial, que
        causa o acúmulo.
        """
        consultar = getattr(self.inlet, "time_correction", None)
        if consultar is None:
            return   # inlets de teste não implementam a chamada; a correção fica em 0.
        try:
            self._correcao_tempo = float(consultar(self.TIMEOUT_CORRECAO_S))
        except Exception as e:
            # manter a última correção conhecida é melhor que zerá-la: um zero repentino
            # reintroduziria de uma vez todo o deslocamento que já havia sido compensado.
            recorder_logger.logger.warning(
                f"Falha ao consultar a correção de relógio do LSL "
                f"(mantendo {self._correcao_tempo:.6f}s): {e}")
        else:
            self._ultima_correcao_monotonic = time.monotonic()

    def start(self) -> float:
        """Drena o buffer do inlet, captura `t0` e inicia a thread de aquisição.

        :return: `t0` (instante LSL do início da captura) — use como marca
            `countdown_start`.
        """
        self._atualizar_correcao_tempo()
        self._drain_inlet()
        self.t0 = local_clock()
        self.last_sample_monotonic = time.monotonic()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        recorder_logger.logger.info(f"Aquisição iniciada (t0={self.t0:.6f}, canal={self.channel}) -> {self.csv_path}")
        return self.t0

    def _drain_inlet(self) -> None:
        """Esvazia amostras antigas em buffer para que a primeira amostra salva seja ~t0."""
        try:
            while True:
                sample, _ = self.inlet.pull_sample(timeout=0.0)
                if not sample:
                    break
        except Exception as e:
            recorder_logger.logger.warning(f"Falha ao drenar o buffer do inlet: {e}")

    def add_marker(self, name: str, lsl_time: float, music_file: str, fator: str) -> None:
        """Registra um marcador de evento a ser anexado à amostra mais próxima.

        Thread-safe. O marcador será anexado à primeira amostra cujo timestamp LSL
        seja >= `lsl_time` (dentro de um intervalo de amostragem).
        """
        with self._lock:
            self._pending.append({"name": name, "lsl_time": lsl_time,
                                  "music_file": music_file, "fator": fator})
            self._pending.sort(key=lambda m: m["lsl_time"])
        recorder_logger.logger.info(f"Marcador '{name}' em t={lsl_time:.6f}")

    def _take_marker_for(self, ts: float):
        """Retorna (name, music_file, fator) se houver marcador devido para esta amostra."""
        with self._lock:
            if self._pending and self._pending[0]["lsl_time"] <= ts:
                m = self._pending.pop(0)
                return m["name"], m["music_file"], m["fator"]
        return "", None, None

    def _has_pending(self) -> bool:
        with self._lock:
            return bool(self._pending)

    def _signal_value(self, sample):
        """Extrai o valor do canal selecionado, com proteção contra índice inválido."""
        if not sample:
            return ""
        if 0 <= self.channel < len(sample):
            return sample[self.channel]
        return sample[-1]

    def _run(self) -> None:
        stop_requested_at = None
        last_fsync = time.time()
        last_sample = (None, None)
        try:
            with open(self.csv_path, "w", newline="", encoding=ENCODING_FORMAT) as f:
                writer = csv.writer(f)
                writer.writerow(CSV_HEADER)
                f.flush()

                while True:
                    sample, ts = self.inlet.pull_sample(timeout=self.PULL_TIMEOUT)

                    if self._stop_event.is_set() and stop_requested_at is None:
                        stop_requested_at = time.time()

                    # reconsulta periódica da correção: é a deriva ao longo da sessão que
                    # precisa ser acompanhada, não apenas o offset inicial.
                    if (self._ultima_correcao_monotonic is None
                            or time.monotonic() - self._ultima_correcao_monotonic
                            >= self.INTERVALO_CORRECAO_S):
                        self._atualizar_correcao_tempo()

                    if sample:
                        # traz o timestamp do relógio do emissor para o `local_clock()` local,
                        # domínio em que os marcadores são carimbados. Sem isto os dois
                        # domínios divergem ao longo da sessão e todos os marcadores de uma
                        # faixa saem deslocados por igual (ver `_atualizar_correcao_tempo`).
                        ts = ts + self._correcao_tempo
                        last_sample = (sample, ts)
                        self.last_sample_monotonic = time.monotonic()
                        if not self._first_sample_logged:
                            recorder_logger.logger.info(f"Primeira amostra completa (verificação de canal): {sample}")
                            self._first_sample_logged = True

                        # Descarta amostras anteriores a t0 (timestamp negativo): garante
                        # que a primeira linha gravada tenha timestamp >= 0.
                        if ts >= self.t0:
                            timestamp = ts - self.t0
                            signal_value = self._signal_value(sample)
                            marker, music_file, fator = self._take_marker_for(ts)
                            writer.writerow([timestamp, signal_value, marker,
                                            music_file if music_file is not None else "",
                                            fator if fator is not None else ""])
                            f.flush()
                            if time.time() - last_fsync >= self.FSYNC_INTERVAL:
                                os.fsync(f.fileno())
                                last_fsync = time.time()
                            # encaminha a amostra ao gráfico (nunca deixa o gráfico
                            # derrubar ou atrasar a aquisição — só loga em caso de erro).
                            if self._on_sample is not None:
                                try:
                                    self._on_sample(timestamp, signal_value)
                                except Exception as e:
                                    recorder_logger.logger.warning(f"Callback on_sample falhou: {e}")

                    # condição de término: stop pedido e todos os marcadores já anexados
                    if self._stop_event.is_set() and not self._has_pending():
                        break
                    # proteção: stream parado mas ainda há marcadores pendentes
                    if stop_requested_at is not None and (time.time() - stop_requested_at) > self.DRAIN_AFTER_STOP:
                        self._flush_remaining_markers(writer, last_sample)
                        break

                f.flush()
                os.fsync(f.fileno())
        except Exception as e:
            recorder_logger.logger.error(f"Erro durante a aquisição: {e}")
        recorder_logger.logger.info("Aquisição finalizada.")

    def _flush_remaining_markers(self, writer, last_sample) -> None:
        """Anexa marcadores pendentes a uma linha final (caso o stream tenha parado)."""
        sample, ts = last_sample
        if ts is None:
            ts = local_clock()
        with self._lock:
            pending = list(self._pending)
            self._pending.clear()
        for m in pending:
            recorder_logger.logger.warning(f"Marcador '{m['name']}' anexado à linha final (stream sem novas amostras).")
            writer.writerow([ts - self.t0, self._signal_value(sample), m["name"],
                            m["music_file"] if m["music_file"] is not None else "",
                            m["fator"] if m["fator"] is not None else ""])

    def stop(self) -> None:
        """Sinaliza a parada da aquisição e aguarda a thread encerrar."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=self.DRAIN_AFTER_STOP + 1.0)

    def finalize(self):
        """Garante o término da thread e gera o XLSX a partir do mesmo CSV.

        :return: (csv_path, xlsx_path)
        """
        self.stop()
        try:
            df = pd.read_csv(self.csv_path)
            df.to_excel(self.xlsx_path, index=False)
            recorder_logger.logger.info(f"Arquivos finalizados: {self.csv_path} | {self.xlsx_path}")
        except Exception as e:
            recorder_logger.logger.error(f"Falha ao gerar o XLSX a partir do CSV: {e}")
        return self.csv_path, self.xlsx_path
