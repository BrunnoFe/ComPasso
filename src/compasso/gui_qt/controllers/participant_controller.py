"""Controller do participante (equivale ao antigo ParticipantCard).

Valida e salva os dados do participante (nome/idade/gênero), alterna entre formulário e
resumo e permite reeditar. Mantém os valores *rascunho* do formulário (``rascunhoNome`` etc.),
alimentados pela ``ParticipantView`` por *binding* bidirecional — assim o fluxo "Começar"
(``salvar_se_preenchido``) e o botão "Salvar" leem a mesma fonte, sem alcançar widgets do QML.
A edição é travada durante a sessão pela propriedade ``ctx.participantEditable``.
"""

from PySide6.QtCore import QObject, Property, Signal, Slot

from .. import gui_logger
from ..context import Context
from compasso.utils import validar_nome_genero, validar_idade, MIN_IDADE, MAX_IDADE


class ParticipantController(QObject):
    """Valida/salva os dados do participante e expõe o estado (form/resumo) ao QML."""

    salvosChanged = Signal()
    resumoChanged = Signal()
    rascunhoChanged = Signal()
    mensagem = Signal(str, str, str)   # (titulo, texto, tipo)

    def __init__(self, ctx: Context):
        super().__init__()
        self._ctx = ctx
        self._rascunho_nome = ""
        self._rascunho_idade = ""
        self._rascunho_genero = ""
        # exposto ao ExperimentRunner: salva em silêncio se o form estiver preenchido mas não salvo.
        ctx.save_participant_infos_if_filled = self.salvar_se_preenchido

    # -------------------------------------------------- rascunho (form editável)
    def _mk_rascunho(nome_attr):
        def getter(self):
            return getattr(self, nome_attr)

        def setter(self, valor):
            valor = str(valor)
            if getattr(self, nome_attr) != valor:
                setattr(self, nome_attr, valor)
                self.rascunhoChanged.emit()

        return getter, setter

    _gn, _sn = _mk_rascunho("_rascunho_nome")
    rascunhoNome = Property(str, _gn, _sn, notify=rascunhoChanged)
    _gi, _si = _mk_rascunho("_rascunho_idade")
    rascunhoIdade = Property(str, _gi, _si, notify=rascunhoChanged)
    _gg, _sg = _mk_rascunho("_rascunho_genero")
    rascunhoGenero = Property(str, _gg, _sg, notify=rascunhoChanged)
    del _mk_rascunho, _gn, _sn, _gi, _si, _gg, _sg

    # ------------------------------------------------------- estado (resumo)
    def _get_salvos(self) -> bool:
        return bool(self._ctx.infos_saved)

    salvos = Property(bool, _get_salvos, notify=salvosChanged)

    def _get_nome(self) -> str:
        return self._ctx.nome or ""

    nome = Property(str, _get_nome, notify=resumoChanged)

    def _get_idade(self) -> str:
        return str(self._ctx.idade or "")

    idade = Property(str, _get_idade, notify=resumoChanged)

    def _get_genero(self) -> str:
        return self._ctx.genero or ""

    genero = Property(str, _get_genero, notify=resumoChanged)

    def _get_inicial(self) -> str:
        return ((self._ctx.nome or "?")[:1] or "?").upper()

    inicial = Property(str, _get_inicial, notify=resumoChanged)

    # ----------------------------------------------------------------- ações
    @Slot(result=bool)
    def salvar(self) -> bool:
        """Valida e salva os valores rascunho. Retorna True se salvou; False se houve erro."""
        nome = self._rascunho_nome.strip()
        idade = self._rascunho_idade.strip()
        genero = self._rascunho_genero.strip()

        if not (nome and idade and genero):
            self.mensagem.emit("Erro", "Todos os campos são obrigatórios.", "warning")
            return False
        if not validar_nome_genero(nome, genero):
            self.mensagem.emit("Erro", "Nome e gênero devem conter apenas letras e espaços.", "warning")
            return False
        if not validar_idade(idade):
            self.mensagem.emit("Erro", f"Idade deve ser um número entre {MIN_IDADE} e {MAX_IDADE}.",
                               "warning")
            return False

        self._ctx.nome = nome
        self._ctx.idade = idade
        self._ctx.genero = genero
        self._ctx.infos_saved = True
        self.resumoChanged.emit()
        self.salvosChanged.emit()
        self._ctx.notify_stepper()
        gui_logger.logger.info(f"Informações do participante salvas: {nome}, {idade}, {genero}.")
        return True

    @Slot()
    def editar(self) -> None:
        """Reabre o formulário para edição (mantém os valores no rascunho)."""
        self._ctx.infos_saved = False
        self.salvosChanged.emit()
        self._ctx.notify_stepper()
        gui_logger.logger.info("Edição das informações do participante habilitada.")

    @Slot()
    def limpar(self) -> None:
        """Zera participante e formulário, como num app recém-aberto (nova coleta)."""
        self._rascunho_nome = ""
        self._rascunho_idade = ""
        self._rascunho_genero = ""
        self._ctx.nome = None
        self._ctx.idade = None
        self._ctx.genero = None
        self._ctx.infos_saved = False
        self.rascunhoChanged.emit()
        self.resumoChanged.emit()
        self.salvosChanged.emit()
        self._ctx.notify_stepper()
        gui_logger.logger.info("Informações do participante limpas para uma nova coleta.")

    def salvar_se_preenchido(self) -> bool:
        """Salva em silêncio se o form estiver preenchido mas não salvo (usado pelo 'Começar').

        Retorna True apenas se a validação falhou (preenchido porém inválido), para o chamador
        abortar sem duplicar a mensagem — mesmo contrato do antigo ``save_infos_if_filled``.
        """
        if self._ctx.infos_saved:
            return False
        if not (self._rascunho_nome.strip() and self._rascunho_idade.strip()
                and self._rascunho_genero.strip()):
            return False
        return not self.salvar()
