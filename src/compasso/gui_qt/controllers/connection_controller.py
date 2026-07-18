"""Controller de conexão com o BITalino (equivalente ao antigo ConnectionFrame).

Orquestra a conexão LSL fora da thread da GUI, o watchdog de conexão e a desconexão/
teardown — toda a lógica preservada de ``compasso.gui.frames.top_frame``. A view QML
(``ConnectionView``) apenas dispara ``conectar``/``desconectar`` e observa o estado
(``ctx.connected``, ``conectando``) e as mensagens de erro (sinal ``mensagem``).
"""

from PySide6.QtCore import QObject, Property, Signal, Slot

from .. import gui_logger
from ..context import Context
from compasso.core import connectar_bitalino, ConnectionWatchdog
from compasso.core.constants import SENSOR_GRAPH_PARAMS, SENSOR_DEFAULT


class ConnectionController(QObject):
    """Conecta/desconecta o BITalino e gerencia o watchdog, dirigindo o ``Context``."""

    conectandoChanged = Signal()
    # (titulo, texto, tipo) — tipo em {"warning", "info"} para o diálogo do QML.
    mensagem = Signal(str, str, str)
    pedirConfirmarDesconectar = Signal()   # pede ao QML confirmar a desconexão manual

    def __init__(self, ctx: Context):
        super().__init__()
        self._ctx = ctx
        self._conectando = False
        # o watchdog agenda esta rotina na thread da GUI ao perder o sinal.
        ctx.handle_connection_lost = self._ao_perder_conexao

    # ------------------------------------------------------------ propriedade
    def _get_conectando(self) -> bool:
        return self._conectando

    conectando = Property(bool, _get_conectando, notify=conectandoChanged)

    def _set_conectando(self, valor: bool) -> None:
        if self._conectando != valor:
            self._conectando = valor
            self.conectandoChanged.emit()

    # ---------------------------------------------------------------- canais
    @Slot(str)
    def definir_canal(self, canal: str) -> None:
        """Atualiza o canal LSL usado na coluna 'signal' (padrão 0 se inválido).

        Mantém a convenção do app: "A1" grava índice 1 (sem subtrair 1).
        """
        try:
            self._ctx.signal_channel = int(canal[1])
        except (TypeError, ValueError):
            self._ctx.signal_channel = 0
        gui_logger.logger.info(f"Canal de sinal selecionado: {self._ctx.signal_channel}")

    @Slot(str)
    def definir_sensor(self, sensor: str) -> None:
        """Aplica o tipo de sensor (unidade/escala do gráfico); reseta a escala ao padrão dele."""
        if sensor not in SENSOR_GRAPH_PARAMS:
            sensor = SENSOR_DEFAULT
        self._ctx.sensor_type = sensor
        # Se o gráfico já existir, aplica a escala do sensor (Fase 5 registra ctx.signal_plot).
        plot = getattr(self._ctx, "signal_plot", None)
        if plot is not None and hasattr(plot, "aplicar_sensor"):
            self._ctx.run_after(lambda: plot.aplicar_sensor(sensor, True))
        gui_logger.logger.info(f"Tipo de sensor selecionado: {sensor}")

    # --------------------------------------------------------------- conexão
    @Slot(str)
    def conectar(self, mac_addr: str) -> None:
        """Conecta ao BITalino fora da thread da GUI; trata o resultado na thread principal."""
        # aceita tanto o MAC puro quanto o formato "Nome - MAC".
        mac = mac_addr.split(" - ")[-1].strip()
        gui_logger.logger.info(f"Solicitada conexão ao BITalino com MAC: {mac!r}")
        self._set_conectando(True)
        self._ctx.run_async(lambda: connectar_bitalino(mac_addr=mac),
                            on_done=lambda resultado: self._tratar_resultado(mac, resultado))

    def _tratar_resultado(self, mac: str, resultado) -> None:
        """Trata o retorno de ``connectar_bitalino``: ``str``/``Exception`` é erro; senão é o inlet."""
        self._set_conectando(False)
        if isinstance(resultado, (str, Exception)):
            texto = resultado if isinstance(resultado, str) else f"Erro inesperado ao conectar: {resultado}"
            gui_logger.logger.error(f"Falha na conexão: {texto}")
            self.mensagem.emit("Erro na conexão", str(texto), "warning")
            return

        self._ctx.bitalino = resultado
        self._ctx.mac_addr = mac
        self._ctx.marcar_conexao_mudou()
        self._ctx.status_text.set("Bitalino conectado")

        # inicia o watchdog (detecta perda de sinal por >= 15 s).
        self._ctx.watchdog = ConnectionWatchdog(self._ctx)
        self._ctx.watchdog.start()
        self._ctx.notify_stepper()
        gui_logger.logger.info("BITalino conectado com sucesso.")

    @Slot()
    def solicitar_desconectar(self) -> None:
        """Pedido de desconexão vindo do botão: valida e pede confirmação ao usuário (QML)."""
        runner = self._ctx.runner
        if runner is not None and runner.is_running():
            self.mensagem.emit("Atenção", "Pare o experimento antes de desconectar o Bitalino.", "warning")
            return
        self.pedirConfirmarDesconectar.emit()

    @Slot()
    def desconectar(self) -> None:
        """Desconecta manualmente. Bloqueia (com aviso) se houver experimento em andamento."""
        runner = self._ctx.runner
        if runner is not None and runner.is_running():
            self.mensagem.emit("Atenção", "Pare o experimento antes de desconectar o Bitalino.", "warning")
            return
        self._teardown()
        self._ctx.status_text.set("Bitalino desconectado")
        gui_logger.logger.info("BITalino desconectado manualmente pelo usuário.")

    def _teardown(self) -> None:
        """Encerra o watchdog e o stream, limpa o estado de conexão e notifica a UI.

        Reutilizado pela desconexão manual e pela perda de conexão detectada pelo watchdog.
        """
        watchdog = self._ctx.watchdog
        if watchdog is not None:
            try:
                watchdog.stop()
            except Exception as e:
                gui_logger.logger.warning(f"Falha ao encerrar o watchdog: {e}")
            self._ctx.watchdog = None

        inlet = self._ctx.bitalino
        if inlet is not None:
            try:
                inlet.close_stream()
            except Exception as e:
                gui_logger.logger.warning(f"Falha ao encerrar o stream do Bitalino: {e}")
        self._ctx.bitalino = None
        self._ctx.mac_addr = None
        self._ctx.marcar_conexao_mudou()
        self._ctx.notify_stepper()

    def _ao_perder_conexao(self) -> None:
        """Perda de conexão sinalizada pelo watchdog (já na thread da GUI).

        Para o experimento em andamento (finalizando o arquivo com a marca 'stop'), reseta a
        conexão e avisa o usuário — mesma rotina do antigo ``_handle_connection_lost``.
        """
        runner = self._ctx.runner
        if runner is not None and runner.is_running():
            runner.stop()
        self._teardown()
        self._ctx.status_text.set("Conexão com BITalino perdida")
        self.mensagem.emit("Atenção", "Conexão com BITalino perdida. Verifique o sensor.", "warning")
