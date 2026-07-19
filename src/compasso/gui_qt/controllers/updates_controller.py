"""Controller da verificação de atualizações (menu "Atualizações").

Duas entradas para a mesma consulta, com apresentações diferentes:

- **automática**, uma vez no arranque (durante a splash): silenciosa. Se houver versão nova, o
  menu ganha um ponto vermelho e o item vira "Baixar atualização!". Falha de rede não incomoda
  ninguém — quem não pediu a verificação não deve receber um erro por causa dela.
- **manual**, pelo item de menu: abre uma janelinha com "Verificando…" e informa o desfecho,
  inclusive quando a consulta falha (o usuário pediu, então merece resposta).

A consulta HTTP roda em thread de trabalho via ``ctx.run_async``; só o resultado volta para a
thread da GUI. O ``estado`` é o que a view observa para decidir o que desenhar.
"""

from PySide6.QtCore import QObject, Property, Signal, Slot

import webbrowser

from .. import gui_logger
from ..context import Context
from compasso.core import updates


class UpdatesController(QObject):
    """Estado da verificação de atualizações e as ações do menu."""

    mudou = Signal()
    pedirAbrirJanela = Signal()     # verificação manual: QML abre a janelinha

    # estados possíveis de `estado`, na ordem em que aparecem para o usuário.
    OCIOSO = "idle"
    VERIFICANDO = "verificando"
    DISPONIVEL = "disponivel"
    ATUALIZADO = "atualizado"
    ERRO = "erro"

    def __init__(self, ctx: Context, versao_atual: str = ""):
        super().__init__()
        self._ctx = ctx
        self._versao_atual = versao_atual
        self._estado = self.OCIOSO
        self._versao_remota = ""
        self._url = updates.RELEASES_URL
        self._erro = ""
        # o ponto vermelho sobrevive ao fechamento da janelinha: uma vez sabido que há versão
        # nova, o menu continua sinalizando até o usuário atualizar.
        self._tem_atualizacao = False
        self._em_curso = False

    # ------------------------------------------------------------- propriedades
    def _get_estado(self):
        return self._estado

    estado = Property(str, _get_estado, notify=mudou)

    def _get_tem_atualizacao(self):
        return self._tem_atualizacao

    temAtualizacao = Property(bool, _get_tem_atualizacao, notify=mudou)

    def _get_versao_remota(self):
        return self._versao_remota

    versaoRemota = Property(str, _get_versao_remota, notify=mudou)

    def _get_versao_atual(self):
        return self._versao_atual

    versaoAtual = Property(str, _get_versao_atual, notify=mudou)

    def _get_erro(self):
        return self._erro

    erro = Property(str, _get_erro, notify=mudou)

    def _get_rotulo_item(self):
        """Texto do item de menu: convida a baixar quando já se sabe que há versão nova."""
        return "Baixar atualização!" if self._tem_atualizacao else "Verificar atualizações"

    rotuloItem = Property(str, _get_rotulo_item, notify=mudou)

    # ------------------------------------------------------------------ ações
    @Slot()
    def verificar_automatico(self) -> None:
        """Verificação silenciosa do arranque: só acende o ponto vermelho, nunca reclama."""
        self._verificar(silencioso=True)

    @Slot()
    def acionar_item(self) -> None:
        """Ação do item de menu: baixar (se já se sabe da versão nova) ou verificar agora."""
        if self._tem_atualizacao:
            self.abrir_releases()
        else:
            self.verificar_manual()

    @Slot()
    def verificar_manual(self) -> None:
        """Verificação pedida pelo usuário: abre a janelinha e informa qualquer desfecho."""
        self._estado = self.VERIFICANDO
        self.mudou.emit()
        self.pedirAbrirJanela.emit()
        self._verificar(silencioso=False)

    @Slot()
    def abrir_releases(self) -> None:
        """Leva o usuário à página de releases do projeto."""
        gui_logger.logger.info(f"Abrindo a página de releases: {self._url}")
        webbrowser.open(self._url)

    @Slot()
    def fechar(self) -> None:
        """Fecha a janelinha (o ponto vermelho do menu permanece, se houver atualização)."""
        self._estado = self.OCIOSO
        self.mudou.emit()

    # ------------------------------------------------------------------ interno
    def _verificar(self, silencioso: bool) -> None:
        """Dispara a consulta em thread de trabalho; o resultado volta na thread da GUI."""
        if self._em_curso:
            return   # evita duas consultas simultâneas (menu clicado durante o arranque)
        self._em_curso = True
        versao = self._versao_atual

        def consultar():
            return updates.verificar(versao)

        self._ctx.run_async(consultar, lambda r: self._concluir(r, silencioso))

    def _concluir(self, resultado, silencioso: bool) -> None:
        """(Thread GUI) Traduz o resultado (ou a exceção) em estado observável pela view."""
        self._em_curso = False

        # `run_async` devolve a própria exceção como resultado quando o trabalho falha.
        if isinstance(resultado, Exception):
            gui_logger.logger.warning(f"Verificação de atualização falhou: {resultado}")
            self._erro = str(resultado)
            # numa falha não se sabe se há atualização: não acender nem apagar o ponto.
            if not silencioso:
                self._estado = self.ERRO
                self.mudou.emit()
            return

        self._versao_remota = resultado.versao_remota
        self._url = resultado.url
        self._tem_atualizacao = resultado.disponivel
        if not silencioso:
            self._estado = self.DISPONIVEL if resultado.disponivel else self.ATUALIZADO
        self.mudou.emit()
