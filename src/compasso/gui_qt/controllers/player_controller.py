"""Controller do player (equivale à PlayerBar de mid_frame.py).

Cuida do volume (com debounce ao aplicar no sistema), do polling de progresso da faixa
(via ``QTimer``), do indicador "GRAVANDO"/chip de condição e do botão de calibração. Toda a
lógica é preservada; a diferença é que os laços ``after()`` viram ``QTimer`` e o estado vira
propriedades reativas observadas pela ``PlayerBarView``.
"""

import os

from PySide6.QtCore import QObject, Property, Signal, Slot, QTimer

from .. import gui_logger
from ..context import Context
from compasso.core.audio import get_system_volume, set_system_volume
from compasso.utils import format_time

_PROGRESS_MS = 150        # polling de progresso/estado da faixa
_VOLUME_DEBOUNCE_MS = 150  # atraso para aplicar o volume no sistema após o último passo do slider


class PlayerController(QObject):
    """Volume, progresso da faixa, indicador de gravação e botão de calibração."""

    musicProgressChanged = Signal()
    gravandoChanged = Signal()
    volumeChanged = Signal()
    volumeTravadoChanged = Signal()
    calibrarChanged = Signal()
    mensagem = Signal(str, str, str)     # (titulo, texto, tipo)
    confirmarParada = Signal()           # pede confirmação de parada ao QML
    abrirCalibracao = Signal()           # pede ao QML abrir a janela de calibração

    def __init__(self, ctx: Context):
        super().__init__()
        self._ctx = ctx
        self._music_progress = 0.0
        self._gravando = False
        self._volume_travado = False
        self._volume_avisado = False
        self._pending_volume = None

        # volume inicial lido do sistema (só leitura).
        try:
            self._volume = int(round(get_system_volume()))
        except Exception:
            self._volume = 50
        ctx.volume_text.set(f"{self._volume}%")

        # expõe ao app/janela de calibração (mesmos nomes do AppContext antigo).
        ctx.atualizar_botao_calibrar = self._atualizar_calibrar
        ctx.aplicar_volume_calibrado = self.aplicar_volume_calibrado

        # debounce do volume e polling de progresso.
        self._timer_volume = QTimer(self)
        self._timer_volume.setSingleShot(True)
        self._timer_volume.setInterval(_VOLUME_DEBOUNCE_MS)
        self._timer_volume.timeout.connect(self._aplicar_volume_pendente)

        self._timer_progresso = QTimer(self)
        self._timer_progresso.setInterval(_PROGRESS_MS)
        self._timer_progresso.timeout.connect(self._atualizar_progresso)
        self._timer_progresso.start()

        self._atualizar_calibrar()

    # ------------------------------------------------------------ propriedades
    def _get_music_progress(self):
        return self._music_progress

    musicProgress = Property(float, _get_music_progress, notify=musicProgressChanged)

    def _get_gravando(self):
        return self._gravando

    gravando = Property(bool, _get_gravando, notify=gravandoChanged)

    def _get_volume(self):
        return self._volume

    volume = Property(int, _get_volume, notify=volumeChanged)

    def _get_volume_travado(self):
        return self._volume_travado

    volumeTravado = Property(bool, _get_volume_travado, notify=volumeTravadoChanged)

    def _get_calibrar_visivel(self):
        return bool(getattr(self._ctx, "calibracao_habilitada", False))

    calibrarVisivel = Property(bool, _get_calibrar_visivel, notify=calibrarChanged)

    def _get_calibrar_habilitado(self):
        caminho = getattr(self._ctx, "calibracao_caminho", None)
        runner = self._ctx.runner
        ocupado = runner is not None and runner.is_running()
        return bool(caminho) and os.path.isfile(caminho) and not ocupado

    calibrarHabilitado = Property(bool, _get_calibrar_habilitado, notify=calibrarChanged)

    # ----------------------------------------------------------------- volume
    @Slot(int)
    def definir_volume(self, valor: int) -> None:
        """Atualiza o rótulo imediatamente e aplica o volume no sistema com debounce."""
        vol = int(valor)
        if vol != self._volume:
            self._volume = vol
            self.volumeChanged.emit()
        self._ctx.volume_text.set(f"{vol}%")
        self._pending_volume = vol
        self._timer_volume.start()   # reinicia o debounce

    def _aplicar_volume_pendente(self) -> None:
        """Aplica o último volume solicitado (defesa: não aplica com aquisição em andamento)."""
        runner = self._ctx.runner
        if runner is not None and runner.is_acquiring():
            return
        if self._pending_volume is None:
            return
        if not set_system_volume(self._pending_volume) and not self._volume_avisado:
            self._volume_avisado = True
            self._ctx.status_text.set("Controle de volume do sistema indisponível.")

    def aplicar_volume_calibrado(self, volume) -> None:
        """Aplica o volume ótimo achado na calibração ao sistema e ao slider, e trava o slider."""
        try:
            vol = int(volume)
            set_system_volume(vol)
            self._volume = vol
            self.volumeChanged.emit()
            self._ctx.volume_text.set(f"{vol}%")
            self._ctx.volume_calibrado = vol
            self._ctx.volume_travado = True
            self._set_travado(True)
            self._ctx.notify_stepper()   # acende a etapa "Calibragem"
            gui_logger.logger.info(f"Volume calibrado aplicado e travado em {vol}%.")
        except Exception as e:
            gui_logger.logger.warning(f"Falha ao aplicar volume calibrado: {e}")

    @Slot()
    def limpar_calibracao(self) -> None:
        """Descarta o volume calibrado e destrava o slider (nova coleta = novo participante)."""
        self._ctx.volume_calibrado = None
        self._ctx.volume_travado = False
        self._set_travado(False)
        self._ctx.notify_stepper()   # apaga a etapa "Calibragem"
        self._atualizar_calibrar()
        gui_logger.logger.info("Calibração de volume descartada para uma nova coleta.")

    def _set_travado(self, travado: bool) -> None:
        if self._volume_travado != travado:
            self._volume_travado = travado
            self.volumeTravadoChanged.emit()

    # ----------------------------------------------------------------- parar
    @Slot()
    def parar(self) -> None:
        """Para o experimento (pedindo confirmação) ou apenas a reprodução de áudio."""
        runner = self._ctx.runner
        if runner is not None and runner.is_running():
            self.confirmarParada.emit()   # o QML confirma e chama confirmar_parada()
            return
        try:
            self._ctx.player.stop()
        except Exception:
            pass

    @Slot()
    def confirmar_parada(self) -> None:
        """Executa a parada do experimento após a confirmação do usuário no QML."""
        runner = self._ctx.runner
        if runner is not None and runner.is_running():
            runner.stop()

    # ------------------------------------------------------------- calibração
    @Slot()
    def calibrar(self) -> None:
        """Valida pré-requisitos e pede ao QML para abrir a janela de calibração."""
        runner = self._ctx.runner
        if runner is not None and runner.is_running():
            self.mensagem.emit("Atenção", "Não é possível calibrar com um experimento em andamento.",
                               "warning")
            return
        caminho = getattr(self._ctx, "calibracao_caminho", None)
        if not caminho or not os.path.isfile(caminho):
            self.mensagem.emit("Atenção",
                               "Nenhum arquivo de áudio de calibração válido foi definido.\n"
                               "Carregue-o na configuração do experimento (Experimento → Novo/Editar).",
                               "warning")
            return
        self.abrirCalibracao.emit()

    def _atualizar_calibrar(self) -> None:
        """Reavalia visibilidade/habilitação do botão calibrar e reflete em ``ctx.calibrarVisible``."""
        self._ctx.calibrarVisible = self._get_calibrar_visivel()
        self.calibrarChanged.emit()

    # -------------------------------------------------------------- progresso
    def _atualizar_progresso(self) -> None:
        """Polling (QTimer): atualiza tempo/progresso da faixa, indicador de gravação e trava."""
        player = self._ctx.player
        pos = length = 0.0
        try:
            if player and player.is_busy():
                pos = float(player.get_pos() or 0.0)
                length = float(player.get_length() or 0.0)
        except Exception:
            pass

        self._ctx.time_begin_text.set(format_time(pos))
        self._ctx.time_end_text.set(format_time(length))
        prog = max(0.0, min(1.0, pos / length)) if length > 0 else 0.0
        if prog != self._music_progress:
            self._music_progress = prog
            self.musicProgressChanged.emit()

        runner = self._ctx.runner
        gravando = runner is not None and runner.is_acquiring()
        if gravando != self._gravando:
            self._gravando = gravando
            self.gravandoChanged.emit()

        travado = gravando or bool(getattr(self._ctx, "volume_travado", False))
        self._set_travado(travado)
        self._atualizar_calibrar()
