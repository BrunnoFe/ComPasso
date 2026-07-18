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

    def __init__(self, ctx: Context):
        super().__init__()
        self._ctx = ctx

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
    def parar(self) -> None:
        """Para o experimento em andamento (usado pelo fluxo de confirmação do PlayerBar)."""
        runner = self._ctx.runner
        if runner is not None and runner.is_running():
            runner.stop()
