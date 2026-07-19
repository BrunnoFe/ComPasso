import os
import random
import threading

import pandas as pd
from pylsl import local_clock

from . import experiment_logger
from .audio import get_system_volume
from .constants import (MARKER_COUNTDOWN_START, MARKER_BEEP, MARKER_MUSIC_START,
                       MARKER_MUSIC_END, MARKER_STOP, CONDITION_MUSICA, CONDITION_RUIDO,
                       RUIDO_KEYWORDS)
from .recorder import LSLRecorder, build_session_dirname, build_track_filename

# Planilha (uma por sessão) com o resumo de cada faixa executada: ordem, arquivo, fator,
# volume do sistema no momento da reprodução e intervalo de reação até o "continuar".
EXECUCAO_XLSX_FILENAME = "dados_da_execucao.xlsx"
EXECUCAO_COLUNAS = ["n", "audio", "fator", "volume", "intervalo"]


def _classify_condition(fator: str) -> str:
    """Classifica o fator de uma faixa em 'musica' ou 'ruido'.

    Heurística simples baseada em palavras-chave do valor da coluna `fator`.
    Por padrão, qualquer faixa que não seja ruído é tratada como música.
    """
    f = (fator or "").strip().lower()
    if any(kw in f for kw in RUIDO_KEYWORDS):
        return CONDITION_RUIDO
    return CONDITION_MUSICA


def _distribute(files: list, total: int) -> list:
    """Distribui `total` reproduções entre `files` de forma o mais uniforme possível.

    Embaralha `files` (para que o "extra" caia em arquivos aleatórios) e devolve `total`
    itens em round-robin. Ex.: 2 arquivos e `total=5` → um arquivo aparece 3× e o outro 2×.
    Retorna `[]` se `files` estiver vazio ou `total <= 0`.
    """
    if not files or total <= 0:
        return []
    files = list(files)
    random.shuffle(files)
    return [files[i % len(files)] for i in range(total)]


def expand_playlist(mapping: dict, noise_quantity: int) -> list:
    """Expande o mapeamento em um multiconjunto de faixas (não ordenado).

    Cada música (fator classificado como 'musica') aparece uma vez; os arquivos de ruído
    distintos recebem, no total, `noise_quantity` reproduções distribuídas entre eles
    (ver `_distribute`). Arquivos de ruído são distinguidos pelo caminho (nome do arquivo).
    """
    musicas = [p for p, f in mapping.items() if _classify_condition(f) == CONDITION_MUSICA]
    ruidos = [p for p, f in mapping.items() if _classify_condition(f) == CONDITION_RUIDO]
    return musicas + _distribute(ruidos, int(noise_quantity or 0))


def count_totals(playlist: list, mapping: dict) -> dict:
    """Conta quantas faixas de cada condição há em `playlist`."""
    totals = {CONDITION_MUSICA: 0, CONDITION_RUIDO: 0}
    for path in playlist:
        totals[_classify_condition(mapping.get(path, ""))] += 1
    return totals


def session_totals(mapping: dict, noise_quantity: int) -> tuple:
    """Totais da sessão `(total_musicas, total_ruido)` para exibição na GUI.

    Reutiliza `expand_playlist`/`count_totals` para ter uma única fonte de verdade; devolve
    ints simples para que a camada de GUI não precise conhecer as constantes de condição.
    """
    totals = count_totals(expand_playlist(mapping, noise_quantity), mapping)
    return totals[CONDITION_MUSICA], totals[CONDITION_RUIDO]


def pseudo_random_order(playlist: list, mapping: dict) -> list:
    """Ordena `playlist` de forma pseudoaleatória respeitando as regras do ruído.

    Regras: o ruído nunca é a primeira faixa e há ao menos 2 músicas entre dois ruídos
    consecutivos. Usa um método construtivo (combinação uniforme) que garante essas
    restrições sem rejeição por tentativa; se forem infactíveis (ruídos demais para poucas
    músicas), faz melhor-esforço (nunca ruído primeiro) e registra um aviso.
    """
    musicas = [p for p in playlist if _classify_condition(mapping.get(p, "")) == CONDITION_MUSICA]
    ruidos = [p for p in playlist if _classify_condition(mapping.get(p, "")) == CONDITION_RUIDO]
    random.shuffle(musicas)
    random.shuffle(ruidos)

    M, R = len(musicas), len(ruidos)
    if R == 0:
        return musicas

    U = M - 1 - 2 * (R - 1)
    if U < 0:
        experiment_logger.logger.warning(
            f"Restrições de espaçamento do ruído infactíveis ({M} música(s) para {R} ruído(s)); "
            "usando melhor-esforço (ruído nunca em primeiro).")
        # melhor-esforço: começa por uma música (se houver) e intercala o restante.
        rest = musicas[1:] + ruidos
        random.shuffle(rest)
        return (musicas[:1] + rest) if musicas else ruidos

    # g[i] = nº de músicas antes do ruído i (0-based). a não-decrescente em [0, U] garante
    # g[0] >= 1 (não-primeiro) e g[i+1]-g[i] >= 2 (>=2 músicas entre ruídos), g[R-1] <= M.
    a = sorted(random.randint(0, U) for _ in range(R))
    g = [a[i] + 1 + 2 * i for i in range(R)]

    result = []
    gi = 0
    for k, m in enumerate(musicas, start=1):
        result.append(m)
        while gi < R and g[gi] == k:
            result.append(ruidos[gi])
            gi += 1
    while gi < R:  # segurança: ruídos residuais (não deve ocorrer com U >= 0)
        result.append(ruidos[gi])
        gi += 1
    return result


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

    # Fallback do tempo pré-estímulo (s) quando o ctx não informa um valor configurado.
    COUNTDOWN_SECONDS = 5
    # janela de antecedência (s) do gráfico: quantos segundos finais da contagem regressiva
    # já aparecem no traço antes da música começar (eixo X total = lead + duração). O lead
    # efetivo é clampado ao tempo pré-estímulo (não pode ser maior que a própria contagem).
    PLOT_LEAD_SECONDS = 5
    # folga (s) somada à duração da faixa antes de desistir de esperar o sinal de fim.
    MARGEM_FIM_FAIXA_S = 5.0
    # granularidade (s) da espera em `_esperar_ate`: curta o bastante para o botão "parar"
    # responder rápido, longa o bastante para não girar a CPU à toa.
    _PASSO_ESPERA_S = 0.05
    # nos últimos (s) antes de um alvo, nenhum status é postado (ver `_esperar_ate`).
    _MARGEM_STATUS_S = 0.15

    def __init__(self, ctx):
        self.ctx = ctx
        # faixa corrente; inicializados aqui porque `stop()` pode ser chamado antes do
        # primeiro `_run_track` (o botão existe desde o início da sessão).
        self.music_name = ""
        self.music_fator = ""
        # tempo pré-estímulo configurável (menu Experimento / .config); cai no fallback da classe.
        self.countdown_seconds = int(getattr(ctx, "pre_stimulus_seconds", self.COUNTDOWN_SECONDS))
        # beep de aviso na contagem regressiva (opcional): toca a `beep_antecedencia_segundos`
        # segundos antes de cada faixa começar.
        self.beep_habilitado = bool(getattr(ctx, "beep_habilitado", False))
        self.beep_antecedencia_segundos = int(getattr(ctx, "beep_antecedencia_segundos", 1))
        self._stop_event = threading.Event()
        self._continue_event = threading.Event()
        self._order = []
        self._session_dir = None
        self._recorder = None
        self._thread = None
        self._running = False
        self._done = {CONDITION_MUSICA: 0, CONDITION_RUIDO: 0}
        # gate de pushes para o gráfico: só True a partir dos PLOT_LEAD_SECONDS finais da
        # contagem até o FIM_MUSICA, para que amostras fora da janela não corrompam o
        # traço da faixa anterior.
        self._plot_active = False
        # linhas acumuladas da planilha de execução (uma por faixa concluída) e estado da
        # faixa corrente usado para montar cada linha: volume do sistema no play e instante
        # (local_clock) do FIM_MUSICA. _ts_fim_faixa=None sinaliza faixa pulada/abortada.
        self._linhas_execucao = []
        self._volume_faixa = None
        self._ts_fim_faixa = None
        # timestamp (relativo ao início da aquisição) da primeira amostra aceita após a
        # janela abrir — usado para "zerar" o eixo X do gráfico nesse instante, já que o
        # timestamp bruto da amostra é relativo ao início da gravação (antes da contagem).
        self._plot_origin = None

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
        mapping = self.ctx.music_condition_mapping or {}
        nq = int(getattr(self.ctx, "noise_quantity", 0) or 0)
        self._order = pseudo_random_order(expand_playlist(mapping, nq), mapping)
        if not self._order:
            experiment_logger.logger.warning("Nenhuma faixa para iniciar o experimento.")
            return
        self._stop_event.clear() #limpa o evento de parada antes de iniciar
        self._continue_event.clear()
        self._running = True
        self._set_participant_editable(False)
        self._set_experiment_ui_lock(True)  # recolhe os cards e trava o botão de recolher
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
        self._plot_active = False
        self._plot_reset()
        self._set_button("comecar")
        self._set_participant_editable(True)
        self._set_experiment_ui_lock(False)  # expande os cards e libera o botão de recolher
        self._post_condition("")
        self._post_status("Experimento interrompido.")

    def continuar(self) -> None:
        """Libera a transição para a próxima faixa (chamado pelo botão 'continuar')."""
        self._continue_event.set()

    # ------------------------------------------------------------------ #
    def _run_experiment(self) -> None:
        """Corpo da sessão, na thread daemon. Nenhuma exceção pode escapar daqui.

        Esta thread não tem quem a supervisione: uma exceção que escapasse a mataria em
        silêncio, deixando `_running=True` e a UI travada (campos do participante desabilitados,
        botão recusando reiniciar) — sem nenhum sinal para o usuário além do app parecer morto.
        """
        try:
            self._executar_sessao()
        except Exception as e:
            experiment_logger.logger.error(
                f"Erro não tratado na sessão do experimento: {e}", exc_info=True)
            self._post_status(f"Erro inesperado no experimento: {e}. Sessão encerrada.")
            self._encerrar_recorder_em_erro()
        finally:
            self._finish()

    def _encerrar_recorder_em_erro(self) -> None:
        """Fecha o arquivo da faixa corrente após uma falha, para não perder o já gravado."""
        rec = self._recorder
        if rec is None:
            return
        try:
            rec.stop()
            rec.finalize()
        except Exception as e:
            experiment_logger.logger.error(f"Falha ao finalizar o arquivo após erro: {e}")
        finally:
            self._recorder = None
            self._plot_active = False

    def _executar_sessao(self) -> None:
        # pasta única da sessão de coleta (criada uma vez, antes da primeira faixa)
        session_name = build_session_dirname(self.ctx)
        self._session_dir = os.path.join(self.ctx.save_dir, session_name)
        try:
            os.makedirs(self._session_dir, exist_ok=True)
        except OSError as e:
            experiment_logger.logger.error(f"Não foi possível criar a pasta da sessão '{self._session_dir}': {e}")
            self._post_status("Erro ao criar a pasta de salvamento. Experimento abortado.")
            return
        experiment_logger.logger.info(f"Pasta da sessão criada: {self._session_dir}")

        totals = count_totals(self._order, self.ctx.music_condition_mapping or {})
        self._done = {CONDITION_MUSICA: 0, CONDITION_RUIDO: 0}
        self._linhas_execucao = []
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
            # intervalo de reação: do FIM_MUSICA até o clique em "continuar" (mesmo relógio
            # local_clock). music_name/music_fator ainda são os da faixa recém-concluída.
            t_continuar = local_clock()
            if self._ts_fim_faixa is not None:
                intervalo = round(t_continuar - self._ts_fim_faixa, 3)
                self._registrar_execucao(order, self._volume_faixa, intervalo)
            if self._stop_event.is_set():
                break

    def _run_track(self, order: int, path: str, totals: dict) -> None:
        self.music_name = os.path.basename(path)
        self.music_fator = self.ctx.music_condition_mapping.get(path, "")
        cat = _classify_condition(self.music_fator)
        # zera o estado de registro da faixa; só volta a valer se a faixa chegar ao fim.
        self._ts_fim_faixa = None
        self._volume_faixa = None

        self._set_button("rodando")
        self._post_current_music(f"Preparando: {self.music_name}")

        # 1) carga do áudio ANTES da aquisição. `load()` bloqueia (até 10 s) e tem latência
        # variável; rodá-lo depois de t0 jogaria essa variação para dentro da janela
        # cronometrada, deslocando a contagem regressiva de forma diferente a cada faixa.
        if not self.ctx.player.load(path):
            experiment_logger.logger.error(f"Falha ao carregar áudio; pulando faixa: {path}")
            self._post_status(f"Falha ao carregar '{self.music_name}'; pulando faixa.")
            return
        # duração pré-varrida no scan (SondaDuracao); o valor da carga é o fallback.
        duration = self.ctx.duracoes_audio.get(path) or self.ctx.player.get_length()

        # 2) aquisição + captura de t0 (drena buffer -> t0 -> primeira linha, sem lacuna)
        filename = build_track_filename(order, len(self._order), self.music_name)
        csv_path = os.path.join(self._session_dir, filename + ".csv") #type: ignore
        experiment_logger.logger.info(f"Preparando aquisição LSL para '{self.music_name}' (fator: '{self.music_fator}') -> {csv_path}")
        recorder = LSLRecorder(self.ctx.bitalino, self.ctx.signal_channel, csv_path,
                               on_sample=self._plot_push)
        self._recorder = recorder
        t0 = recorder.start()
        recorder.add_marker(MARKER_COUNTDOWN_START, t0, music_file=self.music_name, fator=self.music_fator)

        # 3) alvos absolutos da faixa, todos derivados de t_audio (o início do estímulo é a
        # referência do experimento). Como cada espera é recalculada do relógio em
        # `_esperar_ate`, o erro de despertar do SO não acumula: o intervalo beep->áudio vale o
        # configurado em toda faixa, do início ao fim da sessão.
        t_audio = t0 + self.countdown_seconds
        t_beep = t_audio - self.beep_antecedencia_segundos
        t_grafico = t_audio - self.PLOT_LEAD_SECONDS
        if t_grafico < t0:
            # contagem menor que a janela do gráfico: o traço só pode começar em t0. O eixo
            # continua indo de -PLOT_LEAD_SECONDS, então a região anterior fica sem traço.
            experiment_logger.logger.warning(
                f"Tempo pré-estímulo ({self.countdown_seconds}s) menor que a janela do gráfico "
                f"({self.PLOT_LEAD_SECONDS}s): o traço começará em t0.")
            t_grafico = t0

        eventos = [(t_grafico, "grafico"), (t_audio, "audio")]
        if self.beep_habilitado:
            eventos.append((t_beep, "beep"))
        eventos.sort(key=lambda e: e[0])

        ts_start = None
        for instante, evento in eventos:
            if not self._esperar_ate(instante, t_audio):
                return
            # nada entre a espera e o disparo: qualquer trabalho aqui (postar status, ler o
            # volume do SO) vira atraso direto sobre o instante alvo.
            if evento == "grafico":
                # origem do eixo na mesma base dos timestamps do recorder (relativos a t0).
                self._plot_origin = t_grafico - t0
                self._plot_active = True
                self._plot_begin(self.PLOT_LEAD_SECONDS + duration, self.PLOT_LEAD_SECONDS)
            elif evento == "beep":
                ts_beep = local_clock()
                self.ctx.player.play_beep()
                recorder.add_marker(MARKER_BEEP, ts_beep,
                                    music_file=self.music_name, fator=self.music_fator)
            else:
                ts_start = local_clock()
                self.ctx.player.play()
                recorder.add_marker(MARKER_MUSIC_START, ts_start,
                                    music_file=self.music_name, fator=self.music_fator)

        if ts_start is None or self._stop_event.is_set():
            return

        # trabalho não cronometrado, deliberadamente depois do play(): `get_system_volume()` é
        # uma chamada COM (pycaw) e ficava entre o marcador e o play(), injetando latência não
        # medida no instante mais sensível da faixa.
        self._volume_faixa = int(round(get_system_volume()))
        self._post_current_music(self.music_name)
        if cat == CONDITION_MUSICA:
            self._post_condition(f" {str(self.music_fator).strip().lower()} ")
        else:
            self._post_condition(" ruído ")
        self._post_status(f"Reproduzindo: {self.music_name}")

        # 4) aguarda o fim da faixa pelo sinal EndOfMedia (o timeout é só rede de segurança
        # para o caso de o sinal nunca chegar). O polling anterior atrasava o `music_end` — e,
        # com ele, a âncora do eixo X — em até 200 ms.
        if not self.ctx.player.aguardar_fim(duration + self.MARGEM_FIM_FAIXA_S):
            experiment_logger.logger.warning(
                f"Fim de '{self.music_name}' não sinalizado em {duration:.1f}s + margem; "
                "encerrando a faixa por tempo esgotado.")
            self.ctx.player.stop()
        if self._stop_event.is_set():
            return

        # 5) fim da música + finalização do arquivo
        ts_end = local_clock()
        self._ts_fim_faixa = ts_end
        recorder.add_marker(MARKER_MUSIC_END, ts_end, music_file=self.music_name, fator=self.music_fator)
        # `stop()` faz join na thread de aquisição: quando retorna, TODAS as amostras da faixa
        # já foram entregues e encaminhadas ao gráfico. Fechar o portão (`_plot_active`) antes
        # disso descartava a cauda de amostras que o LSL ainda não tinha entregado — o traço
        # parava antes do fim do eixo e o ponteiro saltava, deixando um vão visível no fim.
        recorder.stop()
        self._plot_active = False
        # a duração real da faixa (do play() ao fim da reprodução, mesmo relógio das amostras)
        # reajusta o eixo X para terminar exatamente onde a música terminou.
        self._plot_end(ts_end - ts_start)
        recorder.finalize()
        self._recorder = None

        self._done[cat] = self._done.get(cat, 0) + 1
        self._update_counters(totals)
        self._post_condition("")

    def _registrar_execucao(self, order: int, volume, intervalo: float) -> None:
        """Acumula a linha da faixa e regrava a planilha da sessão a cada faixa.

        Reescreve o arquivo inteiro (padrão de `LSLRecorder.finalize`); o volume de linhas
        (uma por faixa) é pequeno. Falha de escrita é registrada mas não aborta a sessão.
        """
        # a chave precisa bater com EXECUCAO_COLUNAS (sem acento): `pd.DataFrame(...,
        # columns=...)` não casa "áudio" com "audio" e emitiria uma coluna inteira de NaN,
        # perdendo silenciosamente o nome de todas as faixas da sessão.
        self._linhas_execucao.append({
            "n": order,
            "audio": self.music_name,
            "fator": self.music_fator,
            "volume": volume,
            "intervalo": intervalo,
        })
        if self._session_dir is not None:
            caminho = os.path.join(self._session_dir, EXECUCAO_XLSX_FILENAME)
            try:
                df = pd.DataFrame(self._linhas_execucao, columns=EXECUCAO_COLUNAS)
                df.to_excel(caminho, index=False)
            # amplo de propósito: nem toda falha do openpyxl é OSError, e uma planilha que não
            # grava não pode derrubar a sessão inteira (os CSVs, que são o dado primário, já
            # foram salvos).
            except Exception as e:
                experiment_logger.logger.error(
                    f"Não foi possível gravar a planilha de execução '{caminho}': {e}")

    def _esperar_ate(self, alvo: float, t_audio: float | None = None) -> bool:
        """Espera até o instante `alvo` (local_clock). False se houve pedido de parada.

        Recalcula o restante a partir do relógio a cada volta, então o erro de despertar do SO
        se corrige sozinho em vez de acumular — ao contrário de um laço de `sleep` de duração
        fixa, onde cada volta custa `1.0 s + ε` e o desvio cresce com o número de voltas.

        `t_audio`, quando informado, habilita a atualização do status ("iniciando em Ns"). O
        texto nunca é postado perto do alvo: postar é um `emit` cross-thread, e no último
        instante ele viraria atraso direto sobre o disparo do evento.
        """
        ultimo_segundo_postado = None
        while True:
            restante = alvo - local_clock()
            if restante <= 0:
                return not self._stop_event.is_set()
            if t_audio is not None and restante > self._MARGEM_STATUS_S:
                segundos = int(round(t_audio - local_clock()))
                if segundos > 0 and segundos != ultimo_segundo_postado:
                    ultimo_segundo_postado = segundos
                    self._post_status(
                        f"Preparando '{self.music_name}' — iniciando em {segundos}s")
            if self._stop_event.wait(min(restante, self._PASSO_ESPERA_S)):
                return False

    def _finish(self) -> None:
        self._running = False
        self._set_button("comecar")
        self._set_participant_editable(True)
        self._set_experiment_ui_lock(False)  # expande os cards e libera o botão de recolher
        self._post_condition("")
        if not self._stop_event.is_set():
            experiment_logger.logger.info("Experimento finalizado.")
            self._post_status("Experimento finalizado.")

    # ------------------------------------------------------------------ #
    # Controle do gráfico do sinal (fachada opcional em ctx.signal_plot).
    # begin/end/reset_idle tocam o canvas -> agendados na thread da GUI.
    # push é thread-safe -> chamado direto da thread de aquisição.
    def _plot_begin(self, duration, lead) -> None:
        p = getattr(self.ctx, "signal_plot", None)
        if p is not None:
            self.ctx.run_after(lambda: p.begin(duration, lead))

    def _plot_end(self, duracao_real=None) -> None:
        p = getattr(self.ctx, "signal_plot", None)
        if p is not None:
            self.ctx.run_after(lambda: p.end(duracao_real))

    def _plot_reset(self) -> None:
        p = getattr(self.ctx, "signal_plot", None)
        if p is not None:
            self.ctx.run_after(p.reset_idle)

    def _plot_push(self, t, v) -> None:
        """Encaminha uma amostra ao gráfico (chamado da thread de aquisição).

        `t` vem do `LSLRecorder` relativo ao início da gravação (antes da contagem), mas o eixo
        X do gráfico começa em 0 na abertura da janela (`_plot_begin`). `_plot_origin` é o
        instante dessa abertura na mesma base de `t` — definido em `_run_track` a partir do
        alvo calculado, não da primeira amostra que chegar: ancorar na primeira amostra
        deslocava o traço por até um intervalo de amostragem, variando conforme o momento em
        que a janela abria em relação ao fluxo do BITalino.
        """
        if not self._plot_active:
            return
        p = getattr(self.ctx, "signal_plot", None)
        if p is None:
            return
        try:
            t = float(t)
            if self._plot_origin is None:
                self._plot_origin = t
            rel_t = t - self._plot_origin
            # arredonda só para o gráfico; o CSV mantém o valor bruto.
            p.push(round(rel_t, 3), round(float(v), 2))
        except (TypeError, ValueError):
            pass

    # ------------------------------------------------------------------ #
    def _set_button(self, state: str) -> None:
        cb = getattr(self.ctx, "set_button_state", None)
        if cb is not None:
            self.ctx.run_after(lambda: cb(state))

    def _set_participant_editable(self, enabled: bool) -> None:
        cb = getattr(self.ctx, "set_participant_editable", None)
        if cb is not None:
            self.ctx.run_after(lambda: cb(enabled))

    def _set_experiment_ui_lock(self, active: bool) -> None:
        """Recolhe/expande os cards e trava/destrava o botão de recolher (via MainFrame)."""
        cb = getattr(self.ctx, "set_experiment_ui_lock", None)
        if cb is not None:
            self.ctx.run_after(lambda: cb(active))

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
