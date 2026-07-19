"""Carregamento em etapas do arranque, exibido pela tela de carregamento (splash).

Antes, todo o trabalho pesado do arranque (backend de áudio, volume do sistema, auto-load do
``.config`` com varredura de músicas/planilha) rodava **antes** de ``engine.load()``: a janela só
aparecia depois de tudo pronto e a splash era puramente decorativa, um temporizador fixo sobre
uma interface que já estava utilizável.

Aqui esse trabalho vira uma fila de etapas executadas **depois** que o QML carregou, cada uma
agendada com ``QTimer.singleShot(0, ...)`` para devolver o controle ao laço de eventos entre
elas — assim a splash pinta, anima e informa em que ponto o carregamento está. O progresso e o
rótulo da etapa são reativos (lidos por *binding* em ``SplashOverlay.qml``).

Há dois tipos de etapa:

* **síncrona** (``adicionar``): um callable que roda e a fila avança;
* **de espera** (``adicionar_espera``): a fila pausa até um sinal Qt chegar, com condição de
  entrada (para pular quando não há o que esperar) e *timeout* de segurança — nenhuma espera
  pode travar o arranque para sempre.

Enquanto o carregamento roda, a splash cobre a janela e intercepta cliques, então o usuário não
alcança o botão "Começar" antes de o beep estar pré-carregado (ver ``Player.preload_beep``).
"""

from PySide6.QtCore import QObject, Property, Signal, Slot, QTimer

from . import gui_logger

# Espera de segurança padrão: nenhuma etapa de espera segura o arranque além disto.
_TIMEOUT_ESPERA_MS = 6000


class Carregador(QObject):
    """Fila de etapas de arranque com progresso reativo, consumida pela splash."""

    mudou = Signal()        # notify comum de etapa/progresso/ativo
    concluido = Signal()    # todas as etapas terminaram

    def __init__(self, parent=None):
        super().__init__(parent)
        self._etapas: list = []      # (rotulo, tipo, payload)
        self._indice = 0
        self._rotulo = "Iniciando..."
        self._progresso = 0.0
        self._ativo = False
        self._timer_timeout = QTimer(self)
        self._timer_timeout.setSingleShot(True)
        self._timer_timeout.timeout.connect(self._espera_expirou)
        self._sinal_aguardado = None

    # ------------------------------------------------------------ propriedades
    def _get_rotulo(self) -> str:
        return self._rotulo

    rotulo = Property(str, _get_rotulo, notify=mudou)

    def _get_progresso(self) -> float:
        return self._progresso

    progresso = Property(float, _get_progresso, notify=mudou)

    def _get_ativo(self) -> bool:
        return self._ativo

    ativo = Property(bool, _get_ativo, notify=mudou)

    # ----------------------------------------------------------------- montagem
    def adicionar(self, rotulo: str, funcao) -> None:
        """Enfileira uma etapa síncrona: ``funcao()`` roda e a fila avança em seguida."""
        self._etapas.append((rotulo, "sync", funcao))

    def adicionar_espera(self, rotulo: str, sinal, condicao=None,
                         timeout_ms: int = _TIMEOUT_ESPERA_MS) -> None:
        """Enfileira uma etapa que pausa a fila até ``sinal`` ser emitido.

        :param condicao: avaliada no momento da etapa; se retornar ``False``, a espera é pulada
            na hora (ex.: não há planilha carregada, então nenhuma varredura vai terminar).
        :param timeout_ms: teto de segurança — vencido o prazo, a fila avança mesmo assim.
        """
        self._etapas.append((rotulo, "espera", (sinal, condicao, timeout_ms)))

    # ------------------------------------------------------------------ execução
    @Slot()
    def iniciar(self) -> None:
        """Começa a executar a fila (retornando imediatamente ao laço de eventos)."""
        self._ativo = True
        self._indice = 0
        self.mudou.emit()
        QTimer.singleShot(0, self._executar_proxima)

    def _executar_proxima(self) -> None:
        if self._indice >= len(self._etapas):
            self._finalizar()
            return

        rotulo, tipo, payload = self._etapas[self._indice]
        self._rotulo = rotulo
        # o progresso mostra a etapa em curso como "já começada", não como concluída.
        self._progresso = self._indice / max(1, len(self._etapas))
        self.mudou.emit()

        if tipo == "espera":
            self._iniciar_espera(payload)
            return

        try:
            payload()
        except Exception as e:
            # uma etapa que falha não pode abortar o arranque: o app abre degradado (é o mesmo
            # contrato dos try/except que envolviam cada uma dessas chamadas em app.py).
            gui_logger.logger.warning(f"Falha na etapa de carregamento '{rotulo}': {e}")
        self._avancar()

    def _iniciar_espera(self, payload) -> None:
        sinal, condicao, timeout_ms = payload
        if condicao is not None:
            try:
                if not condicao():
                    self._avancar()
                    return
            except Exception as e:
                gui_logger.logger.warning(f"Falha ao avaliar condição de espera: {e}")
                self._avancar()
                return
        self._sinal_aguardado = sinal
        try:
            sinal.connect(self._espera_satisfeita)
        except Exception as e:
            gui_logger.logger.warning(f"Falha ao aguardar sinal no carregamento: {e}")
            self._sinal_aguardado = None
            self._avancar()
            return
        self._timer_timeout.start(timeout_ms)

    @Slot()
    def _espera_satisfeita(self) -> None:
        self._timer_timeout.stop()
        self._encerrar_espera()
        self._avancar()

    def _espera_expirou(self) -> None:
        gui_logger.logger.warning(
            f"Etapa de carregamento '{self._rotulo}' excedeu o tempo de espera; seguindo adiante.")
        self._encerrar_espera()
        self._avancar()

    def _encerrar_espera(self) -> None:
        sinal, self._sinal_aguardado = self._sinal_aguardado, None
        if sinal is not None:
            try:
                sinal.disconnect(self._espera_satisfeita)
            except (RuntimeError, TypeError):
                pass   # já desconectado ou objeto destruído — nada a fazer.

    def _avancar(self) -> None:
        self._indice += 1
        QTimer.singleShot(0, self._executar_proxima)

    def _finalizar(self) -> None:
        self._progresso = 1.0
        self._rotulo = "Pronto"
        self._ativo = False
        self.mudou.emit()
        self.concluido.emit()
        gui_logger.logger.info(f"Carregamento concluído ({len(self._etapas)} etapa(s)).")
