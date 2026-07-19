"""Hub de estado compartilhado da aplicação (QObject exposto ao QML).

Equivalente Qt do antigo ``AppContext`` (``compasso.gui.context``). Centraliza:

- serviços/estado: o ``Player``, o inlet do Bitalino, dados do participante, arquivos de
  música e mapeamento de condições, diretório de saída, o ``ExperimentRunner`` etc.;
- **textos/valores reativos** como ``Property`` com sinal ``notify`` — o QML faz *binding*
  (``ctx.statusText``) e se atualiza sozinho, substituindo os antigos ``StringVar``;
- **estado de UI reativo** (``buttonState``, ``experimentUiLocked``, ``connected`` ...) que o
  runner/controllers alteram e o QML observa (substitui os callbacks registrados por frames);
- utilitários de threading (``run_after``/``run_async``) que agendam trabalho na thread da GUI.

Regra imutável preservada: **nunca tocar propriedades/serviços da GUI fora da thread da GUI**
— use ``run_after()`` para agendar a atualização na thread principal. ``run_after`` emite um
sinal com conexão em fila (``Qt.QueuedConnection``): postar na thread da GUI é seguro a partir
de qualquer thread, replicando o antigo ``root.after(0, fn)`` do Tk.
"""

import threading

from PySide6.QtCore import QObject, Property, Signal, Slot, Qt

from . import gui_logger
from compasso.core.player import Player, SondaDuracao
from compasso.core.constants import SENSOR_DEFAULT


class _VarReativa:
    """Adaptador compatível com a API ``.set()``/``.get()`` das antigas ``StringVar``/``DoubleVar``.

    O núcleo (``ExperimentRunner`` e afins) continua chamando ``ctx.status_text.set(...)`` sem
    conhecer as ``Property`` reativas do Qt: cada ``.set()`` encaminha o valor para o *setter* da
    propriedade correspondente do ``Context``, disparando o *notify* e atualizando os *bindings*
    do QML. Assim a camada core permanece intocada durante a migração.
    """

    __slots__ = ("_ler", "_escrever")

    def __init__(self, ler, escrever):
        self._ler = ler
        self._escrever = escrever

    def set(self, valor) -> None:
        self._escrever(valor)

    def get(self):
        return self._ler()


class Context(QObject):
    """Estado compartilhado + ponte de threading para a GUI em QML."""

    # ------------------------------------------------------------------ sinais
    # Ponte de agendamento na thread da GUI (ver run_after).
    _agendar = Signal(object)

    # notify de cada propriedade reativa (um por propriedade, para bindings finos).
    statusTextChanged = Signal()
    currentMusicTextChanged = Signal()
    currentConditionTextChanged = Signal()
    volumeTextChanged = Signal()
    timeBeginTextChanged = Signal()
    timeEndTextChanged = Signal()
    musicDoneTextChanged = Signal()
    musicTotalTextChanged = Signal()
    ruidoDoneTextChanged = Signal()
    ruidoTotalTextChanged = Signal()
    sessionProgressChanged = Signal()
    sessionStatusTextChanged = Signal()

    buttonStateChanged = Signal()
    experimentUiLockedChanged = Signal()
    connectedChanged = Signal()
    participantEditableChanged = Signal()
    cardsCollapsedChanged = Signal()
    calibrarVisibleChanged = Signal()
    stepperChanged = Signal()
    sensorTypeChanged = Signal()
    configLoadedChanged = Signal()
    macAddrChanged = Signal()
    signalChannelChanged = Signal()

    def __init__(self):
        super().__init__()

        # Ponte GUI-thread: conexão em fila para que emitir de qualquer thread poste no
        # laço de eventos da thread onde o Context vive (a GUI).
        self._agendar.connect(self._executar_na_gui, Qt.ConnectionType.QueuedConnection)

        # --- serviços / estado (não reativos; acessados pelo Python) ---
        self.player: Player = Player()
        self.beep_caminho: str = ""       # resolvido no bootstrap (assets/)
        # sonda de duração dos áudios (vive na GUI) e o mapa `caminho -> segundos` que ela
        # preenche. Pré-varrer as durações no scan permite que o eixo X do gráfico já nasça
        # correto em `begin()`, sem depender da carga da faixa dentro da janela cronometrada
        # do experimento — ver core/player.py:SondaDuracao.
        self.sonda_duracao: SondaDuracao = SondaDuracao()
        self.duracoes_audio: dict = {}
        self.bitalino = None              # StreamInlet | None
        self.mac_addr: str | None = None
        self.signal_channel: int = 0
        self.sensor_type: str = SENSOR_DEFAULT
        self.runner = None                # ExperimentRunner | None
        self.watchdog = None              # ConnectionWatchdog | None
        self.signal_plot = None           # fachada do gráfico (registrada pelo backend do chart)
        self.graph_settings: dict = {}

        # dados do participante
        self.nome = None
        self.idade = None
        self.genero = None
        self.infos_saved = False

        # arquivos / condições / saída
        self.music_folder: str | None = None
        self.conditions_file: str | None = None
        self.save_dir: str | None = None
        self.music_files: list = []
        self.music_condition_mapping: dict = {}
        self.music_column: str = "musica"
        self.factor_column: str = "fator"

        # configuração do experimento (.config)
        self.noise_quantity: int = 0
        self.pre_stimulus_seconds: int = 5
        self.beep_habilitado: bool = False
        self.beep_antecedencia_segundos: int = 1
        self.calibracao_habilitada: bool = False
        self.calibracao_caminho: str | None = None
        self.volume_calibrado: int | None = None
        self.volume_travado: bool = False
        self.config_loaded: bool = False
        # última configuração aplicada (.config) e seu caminho — usados por "Editar".
        self.config_atual: dict | None = None
        self.config_path: str | None = None

        # --- valores reativos (backing dos Property) ---
        self._status_text = "Conecte o Bitalino"
        self._current_music_text = "—"
        self._current_condition_text = ""
        self._volume_text = "Volume: 50%"
        self._time_begin_text = "00:00"
        self._time_end_text = "00:00"
        self._music_done_text = "0"
        self._music_total_text = "0"
        self._ruido_done_text = "0"
        self._ruido_total_text = "0"
        self._session_progress = 0.0
        self._session_status_text = "0 / 0"

        self._button_state = "comecar"    # comecar | rodando | continuar
        self._experiment_ui_locked = False
        self._participant_editable = True
        self._cards_collapsed = False
        self._calibrar_visible = False

        # Camada de compatibilidade com o antigo AppContext (mantém o core intocado).
        self._instalar_camada_compatibilidade()

        gui_logger.logger.info("Context (Qt) inicializado.")

    def _instalar_camada_compatibilidade(self) -> None:
        """Expõe a superfície do antigo ``AppContext`` sobre as propriedades reativas do Qt.

        O ``ExperimentRunner``/``ConnectionWatchdog`` esperam variáveis com ``.set()`` e
        *callbacks* registrados (``set_button_state``, ``status_text`` ...). Aqui esses nomes
        são recriados como adaptadores que escrevem nas ``Property`` reativas — então o núcleo
        roda sem alteração e o QML se atualiza por *binding*.
        """
        # Variáveis reativas com API .set()/.get() (equivalentes às StringVar/DoubleVar).
        self.status_text = _VarReativa(lambda: self.statusText,
                                       lambda v: setattr(self, "statusText", v))
        self.current_music_text = _VarReativa(lambda: self.currentMusicText,
                                              lambda v: setattr(self, "currentMusicText", v))
        self.current_condition_text = _VarReativa(lambda: self.currentConditionText,
                                                  lambda v: setattr(self, "currentConditionText", v))
        self.volume_text = _VarReativa(lambda: self.volumeText,
                                       lambda v: setattr(self, "volumeText", v))
        self.time_begin_text = _VarReativa(lambda: self.timeBeginText,
                                           lambda v: setattr(self, "timeBeginText", v))
        self.time_end_text = _VarReativa(lambda: self.timeEndText,
                                         lambda v: setattr(self, "timeEndText", v))
        self.music_done_text = _VarReativa(lambda: self.musicDoneText,
                                           lambda v: setattr(self, "musicDoneText", v))
        self.music_total_text = _VarReativa(lambda: self.musicTotalText,
                                            lambda v: setattr(self, "musicTotalText", v))
        self.ruido_done_text = _VarReativa(lambda: self.ruidoDoneText,
                                           lambda v: setattr(self, "ruidoDoneText", v))
        self.ruido_total_text = _VarReativa(lambda: self.ruidoTotalText,
                                            lambda v: setattr(self, "ruidoTotalText", v))
        self.session_progress = _VarReativa(lambda: self.sessionProgress,
                                            lambda v: setattr(self, "sessionProgress", v))
        self.session_status_text = _VarReativa(lambda: self.sessionStatusText,
                                               lambda v: setattr(self, "sessionStatusText", v))

        # Callbacks de estado de UI (o runner os invoca já na thread da GUI, via run_after).
        self.set_button_state = lambda estado: setattr(self, "buttonState", estado)
        self.set_participant_editable = lambda habilitado: setattr(self, "participantEditable",
                                                                    habilitado)
        self.set_experiment_ui_lock = self._aplicar_lock_experimento

        # Callbacks registrados por controllers em fases posteriores (default: sem efeito).
        self.handle_connection_lost = None
        self.refresh_stepper = None
        self.save_participant_infos_if_filled = None
        self.atualizar_botao_calibrar = None
        self.aplicar_volume_calibrado = None
        # invocado (já na thread da GUI) quando a sessão termina por conta própria — registrado
        # pelo ExperimentController, que avisa o usuário e rearma o app para uma nova coleta.
        self.on_session_completed = None

    def _aplicar_lock_experimento(self, ativo: bool) -> None:
        """Trava/destrava a UI durante uma sessão: recolhe os cards e marca o bloqueio global.

        No QML, ``experimentUiLocked`` e ``cardsCollapsed`` guiam, por *binding*, o recolhimento
        dos cartões e o bloqueio do menu "Experimento"/botão de recolher (substitui o antigo
        callback registrado pelo MainFrame).
        """
        self.experimentUiLocked = ativo
        self.cardsCollapsed = ativo

    # =====================================================================
    # Ponte de threading
    # =====================================================================
    @Slot(object)
    def _executar_na_gui(self, fn) -> None:
        """Executa, na thread da GUI, o callable recebido pela fila do sinal ``_agendar``."""
        try:
            fn()
        except Exception as e:
            gui_logger.logger.error(f"Erro em callback agendado na GUI: {e}")

    def run_after(self, func) -> None:
        """Agenda ``func()`` para rodar na thread da GUI (seguro de qualquer thread)."""
        try:
            self._agendar.emit(func)
        except Exception as e:
            gui_logger.logger.error(f"Falha ao agendar callback na GUI: {e}")

    def run_async(self, work, on_done=None) -> None:
        """Executa ``work()`` numa thread daemon e agenda ``on_done(resultado)`` na GUI.

        Exceções em ``work()`` são registradas e repassadas como resultado (instância de
        ``Exception``) para ``on_done``, se fornecido — mesmo contrato do antigo AppContext.
        """
        def runner():
            try:
                resultado = work()
            except Exception as e:
                gui_logger.logger.error(f"Erro em run_async: {e}")
                resultado = e
            if on_done is not None:
                self.run_after(lambda: on_done(resultado))

        threading.Thread(target=runner, daemon=True).start()

    def notify_stepper(self) -> None:
        """Sinaliza (na thread da GUI) que o stepper deve reavaliar suas etapas."""
        self.run_after(self.stepperChanged.emit)

    # =====================================================================
    # Propriedades reativas — textos/valores (substituem StringVar/DoubleVar)
    # =====================================================================
    def _mk_str_prop(nome_attr, sinal):
        def getter(self):
            return getattr(self, nome_attr)

        def setter(self, valor):
            valor = str(valor)
            if getattr(self, nome_attr) != valor:
                setattr(self, nome_attr, valor)
                getattr(self, sinal).emit()

        return getter, setter

    _g, _s = _mk_str_prop("_status_text", "statusTextChanged")
    statusText = Property(str, _g, _s, notify=statusTextChanged)
    _g, _s = _mk_str_prop("_current_music_text", "currentMusicTextChanged")
    currentMusicText = Property(str, _g, _s, notify=currentMusicTextChanged)
    _g, _s = _mk_str_prop("_current_condition_text", "currentConditionTextChanged")
    currentConditionText = Property(str, _g, _s, notify=currentConditionTextChanged)
    _g, _s = _mk_str_prop("_volume_text", "volumeTextChanged")
    volumeText = Property(str, _g, _s, notify=volumeTextChanged)
    _g, _s = _mk_str_prop("_time_begin_text", "timeBeginTextChanged")
    timeBeginText = Property(str, _g, _s, notify=timeBeginTextChanged)
    _g, _s = _mk_str_prop("_time_end_text", "timeEndTextChanged")
    timeEndText = Property(str, _g, _s, notify=timeEndTextChanged)
    _g, _s = _mk_str_prop("_music_done_text", "musicDoneTextChanged")
    musicDoneText = Property(str, _g, _s, notify=musicDoneTextChanged)
    _g, _s = _mk_str_prop("_music_total_text", "musicTotalTextChanged")
    musicTotalText = Property(str, _g, _s, notify=musicTotalTextChanged)
    _g, _s = _mk_str_prop("_ruido_done_text", "ruidoDoneTextChanged")
    ruidoDoneText = Property(str, _g, _s, notify=ruidoDoneTextChanged)
    _g, _s = _mk_str_prop("_ruido_total_text", "ruidoTotalTextChanged")
    ruidoTotalText = Property(str, _g, _s, notify=ruidoTotalTextChanged)
    _g, _s = _mk_str_prop("_session_status_text", "sessionStatusTextChanged")
    sessionStatusText = Property(str, _g, _s, notify=sessionStatusTextChanged)

    def _get_session_progress(self):
        return self._session_progress

    def _set_session_progress(self, v):
        v = float(v)
        if self._session_progress != v:
            self._session_progress = v
            self.sessionProgressChanged.emit()

    sessionProgress = Property(float, _get_session_progress, _set_session_progress,
                               notify=sessionProgressChanged)

    # =====================================================================
    # Propriedades reativas — estado de UI (substituem callbacks registrados)
    # =====================================================================
    def _get_button_state(self):
        return self._button_state

    def _set_button_state(self, v):
        v = str(v)
        if self._button_state != v:
            self._button_state = v
            self.buttonStateChanged.emit()
            # a etapa "Começar" do stepper depende deste estado — reavalia junto.
            self.stepperChanged.emit()

    buttonState = Property(str, _get_button_state, _set_button_state, notify=buttonStateChanged)

    def _mk_bool_prop(nome_attr, sinal):
        def getter(self):
            return getattr(self, nome_attr)

        def setter(self, valor):
            valor = bool(valor)
            if getattr(self, nome_attr) != valor:
                setattr(self, nome_attr, valor)
                getattr(self, sinal).emit()

        return getter, setter

    _gb, _sb = _mk_bool_prop("_experiment_ui_locked", "experimentUiLockedChanged")
    experimentUiLocked = Property(bool, _gb, _sb, notify=experimentUiLockedChanged)
    _gb, _sb = _mk_bool_prop("_participant_editable", "participantEditableChanged")
    participantEditable = Property(bool, _gb, _sb, notify=participantEditableChanged)
    _gb, _sb = _mk_bool_prop("_cards_collapsed", "cardsCollapsedChanged")
    cardsCollapsed = Property(bool, _gb, _sb, notify=cardsCollapsedChanged)
    _gb, _sb = _mk_bool_prop("_calibrar_visible", "calibrarVisibleChanged")
    calibrarVisible = Property(bool, _gb, _sb, notify=calibrarVisibleChanged)

    def _get_connected(self):
        return self.bitalino is not None

    connected = Property(bool, _get_connected, notify=connectedChanged)

    # ------------------------------------------------------- etapas (stepper)
    def _calcular_etapas(self) -> list:
        """Monta a lista de etapas do experimento a partir do estado atual.

        Etapas: Configurações → Conectar → Participante → Arquivos → [Calibragem] →
        Começar. "Calibragem" só entra quando a calibração de volume está habilitada.
        Cada item traz ``rotulo``, ``concluida`` e ``atual`` (a primeira ainda não feita),
        mais ``pendente`` (não feita e não atual) para o QML colorir sem recalcular.
        """
        etapas = [
            ("Configurações", bool(self.config_loaded)),
            ("Conectar", self.bitalino is not None),
            ("Participante", bool(self.infos_saved)),
            ("Arquivos", bool(self.music_condition_mapping) and bool(self.save_dir)),
        ]
        if self.calibracao_habilitada:
            etapas.append(("Calibragem", self.volume_calibrado is not None))
        # "Começar" fica concluída (verde) enquanto o experimento está em andamento — o runner
        # alterna buttonState p/ "rodando"/"continuar" (ver _set_button_state, que reavalia o stepper).
        etapas.append(("Começar", self._button_state in ("rodando", "continuar")))

        concluidas = [c for _, c in etapas]
        atual = next((i for i, c in enumerate(concluidas) if not c), len(concluidas) - 1)
        return [
            {"rotulo": rotulo, "concluida": concluida,
             "atual": (i == atual), "pendente": (not concluida and i != atual)}
            for i, (rotulo, concluida) in enumerate(etapas)
        ]

    def _get_stepper_steps(self):
        return self._calcular_etapas()

    stepperSteps = Property("QVariantList", _get_stepper_steps, notify=stepperChanged)

    # ``sensor_type`` é atributo simples (usado pelo core); ``sensorType`` é a leitura reativa
    # para o QML. Chame ``marcar_sensor_mudou()`` após alterar ``sensor_type`` fora da GUI.
    def _get_sensor_type(self):
        return self.sensor_type

    sensorType = Property(str, _get_sensor_type, notify=sensorTypeChanged)

    def marcar_sensor_mudou(self) -> None:
        self.sensorTypeChanged.emit()

    # ``config_loaded`` é atributo simples (usado pelo core/controllers); ``configLoaded`` é a
    # leitura reativa para o QML. Chame ``marcar_config_mudou()`` após alterar ``config_loaded``.
    def _get_config_loaded(self):
        return bool(self.config_loaded)

    configLoaded = Property(bool, _get_config_loaded, notify=configLoadedChanged)

    def marcar_config_mudou(self) -> None:
        self.configLoadedChanged.emit()

    # ``mac_addr``/``signal_channel`` são atributos simples (core); as versões camelCase são a
    # leitura reativa para o QML (ex.: a ConnectionView popula os campos ao carregar um .config).
    def _get_mac_addr(self):
        return self.mac_addr or ""

    macAddr = Property(str, _get_mac_addr, notify=macAddrChanged)

    def _get_signal_channel(self):
        return int(self.signal_channel or 0)

    signalChannel = Property(int, _get_signal_channel, notify=signalChannelChanged)

    def marcar_conexao_info_mudou(self) -> None:
        self.macAddrChanged.emit()
        self.signalChannelChanged.emit()

    def marcar_conexao_mudou(self) -> None:
        """Emite o notify de ``connected`` (chamar após alterar ``self.bitalino``)."""
        self.connectedChanged.emit()

    # Limpa os nomes auxiliares do namespace da classe.
    del _mk_str_prop, _mk_bool_prop, _g, _s, _gb, _sb
