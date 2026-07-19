"""Controller do experimento (equivale ao DownFrame de bottom_frame.py).

Valida os pré-requisitos e comanda o ``ExperimentRunner`` (começar/parar/continuar). O estado
do botão principal (``comecar``/``rodando``/``continuar``) é reativo em ``ctx.buttonState`` — o
próprio runner o alterna via ``ctx.run_after``. A validação de pré-requisitos é a mesma do frame
antigo (``_validar_prerequisitos``), agora num método puro fácil de testar.
"""

from PySide6.QtCore import QObject, Signal, Slot

from .. import gui_logger
from ..context import Context
from compasso.core import ExperimentRunner


def validar_prerequisitos(ctx) -> str:
    """Retorna uma mensagem de erro se algum pré-requisito faltar, ou '' se tudo certo.

    Função pura (recebe o ``ctx``) — mesma lógica do antigo ``DownFrame._validar_prerequisitos``,
    extraída para facilitar o teste sem construir a UI.
    """
    if not getattr(ctx, "config_loaded", False):
        return "Crie ou abra uma configuração de experimento (menu Experimento) antes de iniciar."
    if ctx.bitalino is None:
        return "Conecte o Bitalino antes de iniciar o experimento."
    if not ctx.infos_saved:
        return "Salve as informações do participante antes de iniciar."
    if not ctx.music_files:
        return "Carregue os arquivos de música antes de iniciar."
    if not ctx.save_dir:
        return "Escolha o diretório para salvar os dados antes de iniciar."
    if ctx.runner is not None and ctx.runner.is_running():
        return "O experimento já está em andamento."
    return ""


class ExperimentController(QObject):
    """Inicia/para/continua o experimento, validando os pré-requisitos."""

    mensagem = Signal(str, str, str)   # (titulo, texto, tipo)
    coletaFinalizada = Signal()        # sessão chegou ao fim sozinha (QML avisa e rearma o app)

    def __init__(self, ctx: Context, part_controller=None, player_controller=None):
        super().__init__()
        self._ctx = ctx
        self._part_controller = part_controller
        self._player_controller = player_controller
        ctx.on_session_completed = self.coletaFinalizada.emit

    @Slot()
    def comecar(self) -> None:
        """Valida os pré-requisitos e inicia o experimento em thread separada."""
        # Se o form do participante está preenchido mas não salvo, salva em silêncio antes de
        # validar; se a validação do participante falhou, aborta sem duplicar a mensagem.
        cb = getattr(self._ctx, "save_participant_infos_if_filled", None)
        if cb is not None and not self._ctx.infos_saved and cb():
            return

        problema = validar_prerequisitos(self._ctx)
        if problema:
            self.mensagem.emit("Atenção", problema, "warning")
            return

        if self._ctx.runner is None:
            self._ctx.runner = ExperimentRunner(self._ctx)
        self._ctx.status_text.set("Iniciando experimento...")
        self._ctx.runner.start()
        gui_logger.logger.info("Experimento iniciado pelo usuário.")

    @Slot()
    def continuar(self) -> None:
        """Avança para a próxima faixa (botão no estado 'continuar')."""
        if self._ctx.runner is not None:
            self._ctx.status_text.set("Continuando...")
            self._ctx.runner.continuar()

    @Slot()
    def preparar_nova_coleta(self) -> None:
        """Devolve o app ao estado inicial para uma nova coleta, sem fechar/reabrir.

        Zera participante, calibração, gráfico e todos os indicadores da sessão. Deliberadamente
        **não** mexe na conexão do Bitalino nem nos arquivos carregados (pasta de músicas,
        planilha, diretório de saída, .config): a próxima coleta costuma usar exatamente o mesmo
        material, só trocando o participante.
        """
        if self._part_controller is not None:
            self._part_controller.limpar()
        if self._player_controller is not None:
            self._player_controller.limpar_calibracao()

        # gráfico de volta ao repouso.
        plot = getattr(self._ctx, "signal_plot", None)
        if plot is not None:
            try:
                plot.reset_idle()
            except Exception as e:
                gui_logger.logger.warning(f"Falha ao resetar o gráfico do sinal: {e}")

        # indicadores da sessão.
        self._ctx.current_music_text.set("—")
        self._ctx.current_condition_text.set("")
        self._ctx.time_begin_text.set("00:00")
        self._ctx.time_end_text.set("00:00")
        self._ctx.music_done_text.set("0")
        self._ctx.ruido_done_text.set("0")
        self._ctx.session_progress.set(0.0)
        self._ctx.session_status_text.set("0 / 0")
        self._ctx.status_text.set("Pronto para uma nova coleta.")

        # descarta o runner da sessão encerrada (o próximo "Começar" cria um novo).
        self._ctx.runner = None
        gui_logger.logger.info("Interface preparada para uma nova coleta.")

    @Slot()
    def parar(self) -> None:
        """Para o experimento em andamento (usado pelo fluxo de confirmação do PlayerBar)."""
        runner = self._ctx.runner
        if runner is not None and runner.is_running():
            runner.stop()
