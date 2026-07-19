"""Controller da calibração de volume (equivale a CalibrationWindow).

Toca a faixa de calibração enquanto o volume do sistema sobe em rampa (X% a cada X s), para
ajustar o volume ideal com o participante. Máquina de estados (idle→base→idle→calibrar→salvar) e
os temporizadores (rampa + progresso) portados de ``after`` para ``QTimer``. A lógica pura da
rampa vive em ``compasso.core.calibration``. Estado reativo observado pela ``CalibrationWindow``.
"""

import os

from PySide6.QtCore import QObject, Property, Signal, Slot, QTimer

from .. import gui_logger
from ..context import Context
from compasso.utils import format_time
from compasso.core import get_system_volume, set_system_volume, calibration

_INTERVALO_PROGRESSO_MS = 200


class CalibrationController(QObject):
    """Orquestra a calibração de volume e expõe seu estado ao QML."""

    mudou = Signal()                 # notify comum do estado reativo
    mensagem = Signal(str, str, str)  # (titulo, texto, tipo)
    confirmarSalvar = Signal(int)     # pede confirmação do volume ótimo (QML: Reiniciar/Sim)
    fecharJanela = Signal()           # pede ao QML fechar a janela de calibração (após salvar)

    def __init__(self, ctx: Context):
        super().__init__()
        self._ctx = ctx
        self._player = ctx.player

        self._estado = "idle"          # idle | base | calibrar | salvar
        self._modo = None              # rampa em curso: "base" | "calibrar" | None
        self._base_ok = False
        self._params_validos = True
        self._volume_otimo = None
        self._salvo = False
        self._indice = 0
        self._volume_original = 50
        self._vol_atual = 50
        self._vmin = self._vmax = self._step_pct = self._step_seg = 0

        # parâmetros editáveis (defaults da sessão, não persistidos).
        self._vol_min = str(calibration.CALIB_VOL_MIN_DEFAULT)
        self._vol_max = str(calibration.CALIB_VOL_MAX_DEFAULT)
        self._step_pct_v = calibration.CALIB_STEP_PCT_DEFAULT
        self._step_seg_v = calibration.CALIB_STEP_SEG_DEFAULT

        self._t_begin = "00:00"
        self._t_end = "00:00"
        self._progresso = 0.0
        self._vol_label = "50%"

        # timers: rampa (single-shot encadeado, cancelável) e progresso (periódico).
        self._timer_rampa = QTimer(self)
        self._timer_rampa.setSingleShot(True)
        self._timer_rampa.timeout.connect(self._passo_ou_fim)
        self._proximo_passo_e_fim = None   # ("passo"|"fim") a executar no timeout

        self._timer_progresso = QTimer(self)
        self._timer_progresso.setInterval(_INTERVALO_PROGRESSO_MS)
        self._timer_progresso.timeout.connect(self._atualizar_progresso)

    # ------------------------------------------------------------ propriedades
    def _p(nome_attr, tipo, sinal="mudou"):
        def getter(self):
            return getattr(self, nome_attr)
        return getter

    def _get_estado(self):
        return self._estado
    estado = Property(str, _get_estado, notify=mudou)

    def _get_params_validos(self):
        return self._params_validos
    paramsValidos = Property(bool, _get_params_validos, notify=mudou)

    def _get_base_ok(self):
        return self._base_ok
    baseOk = Property(bool, _get_base_ok, notify=mudou)

    def _get_vol_label(self):
        return self._vol_label
    volLabel = Property(str, _get_vol_label, notify=mudou)

    def _get_t_begin(self):
        return self._t_begin
    tBegin = Property(str, _get_t_begin, notify=mudou)

    def _get_t_end(self):
        return self._t_end
    tEnd = Property(str, _get_t_end, notify=mudou)

    def _get_progresso(self):
        return self._progresso
    progresso = Property(float, _get_progresso, notify=mudou)

    # parâmetros editáveis
    def _get_vol_min(self):
        return self._vol_min
    def _set_vol_min(self, v):
        self._vol_min = str(v); self._validar(); self.mudou.emit()
    volMin = Property(str, _get_vol_min, _set_vol_min, notify=mudou)

    def _get_vol_max(self):
        return self._vol_max
    def _set_vol_max(self, v):
        self._vol_max = str(v); self._validar(); self.mudou.emit()
    volMax = Property(str, _get_vol_max, _set_vol_max, notify=mudou)

    def _get_erro_volumes(self):
        """Mensagem sobre a faixa de volume ("" se válida) — usada sob os dois campos.

        Traz para a tela a validação que já existia em ``calibration.validar_parametros`` e
        que, até aqui, só se manifestava indiretamente como um botão desabilitado, sem dizer
        ao usuário o que estava errado. As regras seguem no core; aqui só se escolhe quais
        mensagens pertencem a este par de campos.
        """
        erros = calibration.validar_parametros(self._vol_min, self._vol_max,
                                               int(self._step_pct_v), int(self._step_seg_v))
        for erro in erros:
            if "olume" in erro or "diferenca" in erro or "diferença" in erro:
                return erro
        return ""

    erroVolumes = Property(str, _get_erro_volumes, notify=mudou)

    def _get_step_pct(self):
        return self._step_pct_v
    def _set_step_pct(self, v):
        self._step_pct_v = int(v); self._validar(); self.mudou.emit()
    stepPct = Property(int, _get_step_pct, _set_step_pct, notify=mudou)

    def _get_step_seg(self):
        return self._step_seg_v
    def _set_step_seg(self, v):
        self._step_seg_v = int(v); self._validar(); self.mudou.emit()
    stepSeg = Property(int, _get_step_seg, _set_step_seg, notify=mudou)

    del _p

    # limites dos sliders de passo/intervalo (constantes do core.calibration).
    stepPctMin = Property(int, lambda self: calibration.CALIB_STEP_PCT_MIN, constant=True)
    stepPctMax = Property(int, lambda self: calibration.CALIB_STEP_PCT_MAX, constant=True)
    stepSegMin = Property(int, lambda self: calibration.CALIB_STEP_SEG_MIN, constant=True)
    stepSegMax = Property(int, lambda self: calibration.CALIB_STEP_SEG_MAX, constant=True)

    # -------------------------------------------------------------------- ações
    @Slot()
    def abrir(self) -> None:
        """(Re)inicia a janela: lê o volume original e reseta a máquina de estados."""
        self._volume_original = int(round(_ler_volume()))
        self._vol_atual = self._volume_original
        self._estado = "idle"
        self._modo = None
        self._base_ok = False
        self._volume_otimo = None
        self._salvo = False
        self._definir_volume_label(self._volume_original)
        self._validar()
        self._timer_progresso.start()
        self.mudou.emit()

    @Slot()
    def linha_base(self) -> None:
        if not self._preparar_reproducao():
            return
        self._estado = "base"
        self._iniciar_rampa("base")
        self.mudou.emit()

    @Slot()
    def calibrar(self) -> None:
        if not self._preparar_reproducao():
            return
        self._estado = "calibrar"
        self._iniciar_rampa("calibrar")
        self.mudou.emit()

    @Slot()
    def parar(self) -> None:
        """Interrompe a rampa: base abortada volta a idle; calibração guarda o volume atual."""
        modo = self._modo
        self._parar_reproducao()
        if modo == "base":
            self._estado = "idle"
        else:
            self._volume_otimo = self._vol_atual
            self._estado = "salvar"
        self.mudou.emit()

    @Slot()
    def pedir_salvar(self) -> None:
        """Pede confirmação do volume ótimo ao usuário (QML mostra Reiniciar/Sim)."""
        if self._volume_otimo is not None:
            self.confirmarSalvar.emit(int(self._volume_otimo))

    @Slot(bool)
    def resolver_salvar(self, confirmou: bool) -> None:
        """Trata a resposta do diálogo de confirmação (True=Sim, False=Reiniciar)."""
        if confirmou:
            self._salvo = True
            cb = self._ctx.aplicar_volume_calibrado
            if cb is not None:
                cb(self._volume_otimo)
            gui_logger.logger.info(f"Volume de calibração confirmado: {self._volume_otimo}%")
            self.fechar()
            # fecha a janela automaticamente após confirmar o volume salvo.
            self.fecharJanela.emit()
        else:
            self._volume_otimo = None
            self._estado = "idle"
            self._definir_volume_label(int(round(_ler_volume())))
            self.mudou.emit()

    @Slot()
    def fechar(self) -> None:
        """Fecha: para a rampa/progresso e restaura o volume original se não salvou."""
        self._parar_reproducao()
        self._timer_progresso.stop()
        if not self._salvo:
            set_system_volume(self._volume_original)

    # --------------------------------------------------------------- validação
    def _validar(self) -> list:
        erros = calibration.validar_parametros(self._vol_min, self._vol_max,
                                               int(self._step_pct_v), int(self._step_seg_v))
        self._params_validos = not erros
        return erros

    # ------------------------------------------------------------------ rampa
    def _preparar_reproducao(self) -> bool:
        erros = self._validar()
        if erros:
            self.mensagem.emit("Parâmetros inválidos", "\n".join(erros), "warning")
            return False
        caminho = self._ctx.calibracao_caminho
        if not caminho or not os.path.isfile(caminho):
            self.mensagem.emit("Erro", "Nenhum arquivo de áudio de calibração válido foi definido.\n"
                                       "Carregue-o na configuração do experimento.", "warning")
            return False
        if not self._player.load(caminho):
            self.mensagem.emit("Erro", "Não foi possível carregar o áudio de calibração.\n"
                                       "Verifique o arquivo (use .wav/.ogg/.mp3).", "warning")
            return False
        vmin, vmax, step_pct, step_seg = self._parametros_int()
        duracao = calibration.duracao_estimada_segundos(vmin, vmax, step_pct, step_seg)
        comprimento = self._player.get_length()
        if comprimento and duracao > comprimento:
            self.mensagem.emit("Atenção",
                               f"A faixa de calibração ({comprimento:.0f} s) é mais curta que o "
                               f"teste ({duracao:.0f} s).\nUse um áudio mais longo ou reduza o passo.",
                               "warning")
            return False
        return True

    def _iniciar_rampa(self, modo: str) -> None:
        self._modo = modo
        self._vmin, self._vmax, self._step_pct, self._step_seg = self._parametros_int()
        self._indice = 0
        self._definir_volume_label(self._vmin)
        set_system_volume(self._vmin)
        self._player.play()
        self._proximo_passo_e_fim = "passo"
        self._timer_rampa.start(self._step_seg * 1000)
        gui_logger.logger.info(
            f"Calibração ({modo}) iniciada: {self._vmin}->{self._vmax}%, "
            f"+{self._step_pct}%/{self._step_seg}s")

    def _passo_ou_fim(self) -> None:
        if self._proximo_passo_e_fim == "fim":
            self._fim_rampa()
        else:
            self._passo_rampa()

    def _passo_rampa(self) -> None:
        self._indice += 1
        vol = calibration.volume_no_incremento(self._indice, self._vmin, self._vmax, self._step_pct)
        set_system_volume(vol)
        self._definir_volume_label(vol)
        if vol >= self._vmax:
            self._proximo_passo_e_fim = "fim"
            self._timer_rampa.start(calibration.CALIB_HOLD_SEGUNDOS * 1000)
        else:
            self._proximo_passo_e_fim = "passo"
            self._timer_rampa.start(self._step_seg * 1000)
        self.mudou.emit()

    def _fim_rampa(self) -> None:
        modo = self._modo
        self._parar_reproducao()
        if modo == "base":
            self._base_ok = True
            self._estado = "idle"
        else:
            self._volume_otimo = self._vmax
            self._estado = "salvar"
        self.mudou.emit()

    def _parar_reproducao(self) -> None:
        self._modo = None
        self._timer_rampa.stop()
        try:
            self._player.stop()
        except Exception:
            pass

    def _definir_volume_label(self, vol) -> None:
        self._vol_atual = int(vol)
        self._vol_label = f"{int(vol)}%"

    def _parametros_int(self):
        return (int(self._vol_min), int(self._vol_max), int(self._step_pct_v), int(self._step_seg_v))

    # --------------------------------------------------------------- progresso
    def _atualizar_progresso(self) -> None:
        pos = comprimento = 0.0
        try:
            if self._player and self._player.is_busy():
                pos = float(self._player.get_pos() or 0.0)
                comprimento = float(self._player.get_length() or 0.0)
        except Exception:
            pass
        self._t_begin = format_time(pos)
        self._t_end = format_time(comprimento)
        self._progresso = max(0.0, min(1.0, pos / comprimento)) if comprimento > 0 else 0.0
        self.mudou.emit()


def _ler_volume():
    try:
        return get_system_volume()
    except Exception:
        return 50
