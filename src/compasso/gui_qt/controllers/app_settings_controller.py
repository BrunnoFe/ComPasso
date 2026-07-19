"""Controller da janela "Configurações → App" (preferências do aplicativo).

Expõe cada preferência de ``core.app_prefs`` como propriedade reativa lida pela
``AppSettingsWindow``, e concentra a política de aplicação:

* o que dá para aplicar **a quente** é aplicado ao salvar (tema, volume, splash, timeouts —
  estes últimos porque são lidos a cada nova conexão/watchdog);
* o que só vale num novo arranque (``app_prefs.REQUEREM_REINICIO``) é sinalizado à UI por
  ``pendenteReinicio``, que exibe o aviso em vez de fingir que a mudança já valeu.

O padrão de edição segue o ``GraphSettingsController``: um dict de trabalho (``_v``) alimentado
na abertura, com *snapshot* para o cancelar. Diferente dele, **não há preview ao vivo** — estas
preferências afetam o app inteiro, e aplicar a cada tecla digitada seria imprevisível.
"""

from PySide6.QtCore import QObject, Property, Signal, Slot

from .. import gui_logger
from ..context import Context
from compasso.core import app_prefs, set_system_volume
from compasso.utils import get_logs_dir, open_path


class AppSettingsController(QObject):
    """Estado reativo das preferências do app + validação, persistência e aplicação."""

    mudou = Signal()                   # notify comum de todas as preferências
    mensagem = Signal(str, str, str)   # (titulo, texto, tipo)
    fecharJanela = Signal()

    def __init__(self, ctx: Context):
        super().__init__()
        self._ctx = ctx
        self._v = app_prefs.obter()
        self._snapshot = dict(self._v)
        self._avancado_liberado = False
        self._pendente_reinicio = False

    # ------------------------------------------------------- propriedades geradas
    def _mk(chave, tipo):
        """Cria getter/setter para uma preferência do schema, com coerção de tipo."""
        def getter(self):
            return tipo(self._v.get(chave, app_prefs.padroes()[chave]))

        def setter(self, valor):
            valor = tipo(valor)
            if self._v.get(chave) != valor:
                self._v[chave] = valor
                self.mudou.emit()

        return getter, setter

    _g, _s = _mk("auto_carregar_config", bool)
    autoCarregarConfig = Property(bool, _g, _s, notify=mudou)
    _g, _s = _mk("verificar_atualizacoes", bool)
    verificarAtualizacoes = Property(bool, _g, _s, notify=mudou)
    _g, _s = _mk("splash_minimo_ms", int)
    splashMinimoMs = Property(int, _g, _s, notify=mudou)
    _g, _s = _mk("confirmar_saida_em_experimento", bool)
    confirmarSaida = Property(bool, _g, _s, notify=mudou)

    _g, _s = _mk("escala_ui", int)
    escalaUi = Property(int, _g, _s, notify=mudou)
    _g, _s = _mk("abrir_maximizado", bool)
    abrirMaximizado = Property(bool, _g, _s, notify=mudou)
    _g, _s = _mk("lembrar_geometria", bool)
    lembrarGeometria = Property(bool, _g, _s, notify=mudou)

    _g, _s = _mk("pasta_dados_padrao", str)
    pastaDadosPadrao = Property(str, _g, _s, notify=mudou)
    _g, _s = _mk("formato_timestamp_sessao", str)
    formatoTimestamp = Property(str, _g, _s, notify=mudou)
    _g, _s = _mk("gerar_xlsx", bool)
    gerarXlsx = Property(bool, _g, _s, notify=mudou)

    _g, _s = _mk("lsl_timeout_s", int)
    lslTimeout = Property(int, _g, _s, notify=mudou)
    _g, _s = _mk("watchdog_timeout_s", int)
    watchdogTimeout = Property(int, _g, _s, notify=mudou)

    _g, _s = _mk("nivel_log", str)
    nivelLog = Property(str, _g, _s, notify=mudou)
    _g, _s = _mk("retencao_logs_dias", int)
    retencaoLogs = Property(int, _g, _s, notify=mudou)

    _g, _s = _mk("idade_minima", int)
    idadeMinima = Property(int, _g, _s, notify=mudou)
    _g, _s = _mk("idade_maxima", int)
    idadeMaxima = Property(int, _g, _s, notify=mudou)
    _g, _s = _mk("volume_inicial", int)
    volumeInicial = Property(int, _g, _s, notify=mudou)
    _g, _s = _mk("controlar_volume_sistema", bool)
    controlarVolume = Property(bool, _g, _s, notify=mudou)
    del _mk, _g, _s

    # ------------------------------------------------ listas (texto separado por vírgula)
    # Listas viram texto na UI porque um editor de lista completo não se paga aqui: são duas
    # preferências, ambas pequenas e raramente tocadas.
    def _get_extensoes(self) -> str:
        return ", ".join(self._v.get("extensoes_audio", []))

    def _set_extensoes(self, texto) -> None:
        itens = [p.strip().lower() for p in str(texto).split(",") if p.strip()]
        # tolera o usuário digitar "wav" em vez de ".wav" — o erro é óbvio e a correção também.
        itens = [p if p.startswith(".") else f".{p}" for p in itens]
        if self._v.get("extensoes_audio") != itens:
            self._v["extensoes_audio"] = itens
            self.mudou.emit()

    extensoesAudio = Property(str, _get_extensoes, _set_extensoes, notify=mudou)

    def _get_palavras_ruido(self) -> str:
        return ", ".join(self._v.get("palavras_ruido", []))

    def _set_palavras_ruido(self, texto) -> None:
        itens = [p.strip() for p in str(texto).split(",") if p.strip()]
        if self._v.get("palavras_ruido") != itens:
            self._v["palavras_ruido"] = itens
            self.mudou.emit()

    palavrasRuido = Property(str, _get_palavras_ruido, _set_palavras_ruido, notify=mudou)

    # ------------------------------------------------------------------- estado da UI
    def _get_avancado_liberado(self) -> bool:
        return self._avancado_liberado

    def _set_avancado_liberado(self, valor) -> None:
        valor = bool(valor)
        if self._avancado_liberado != valor:
            self._avancado_liberado = valor
            self.mudou.emit()
            if valor:
                gui_logger.logger.info("Aba 'Avançado' das preferências liberada pelo usuário.")

    avancadoLiberado = Property(bool, _get_avancado_liberado, _set_avancado_liberado, notify=mudou)

    def _get_pendente_reinicio(self) -> bool:
        return self._pendente_reinicio

    pendenteReinicio = Property(bool, _get_pendente_reinicio, notify=mudou)

    def _get_niveis_log(self):
        return list(app_prefs.NIVEIS_LOG)

    niveisLog = Property(list, _get_niveis_log, constant=True)

    def _get_rotulos_timestamp(self):
        return list(app_prefs.FORMATOS_TIMESTAMP.keys())

    rotulosTimestamp = Property(list, _get_rotulos_timestamp, constant=True)

    def _get_rotulo_timestamp_atual(self) -> str:
        atual = self._v.get("formato_timestamp_sessao")
        for rotulo, formato in app_prefs.FORMATOS_TIMESTAMP.items():
            if formato == atual:
                return rotulo
        return next(iter(app_prefs.FORMATOS_TIMESTAMP))

    rotuloTimestampAtual = Property(str, _get_rotulo_timestamp_atual, notify=mudou)

    @Slot(str)
    def definir_timestamp_por_rotulo(self, rotulo: str) -> None:
        """Traduz o rótulo legível do combo para o formato strftime correspondente."""
        formato = app_prefs.FORMATOS_TIMESTAMP.get(rotulo)
        if formato and self._v.get("formato_timestamp_sessao") != formato:
            self._v["formato_timestamp_sessao"] = formato
            self.mudou.emit()

    @Slot(result=bool)
    def ha_alteracoes(self) -> bool:
        """True se algo mudou desde a abertura (a janela avisa antes de descartar)."""
        return self._v != self._snapshot

    # ------------------------------------------------------------------------ ações
    @Slot()
    def abrir(self) -> None:
        """Carrega as preferências efetivas e guarda o snapshot para o cancelar."""
        self._v = app_prefs.obter()
        self._snapshot = dict(self._v)
        self._pendente_reinicio = False
        self._avancado_liberado = False   # o consentimento vale por abertura, não para sempre.
        self.mudou.emit()

    @Slot()
    def salvar(self) -> None:
        """Valida, persiste e aplica a quente o que for aplicável."""
        erros = app_prefs.definir(self._v)
        if erros:
            # os valores inválidos já caíram no padrão dentro de `definir`; recarrega para a UI
            # mostrar o que de fato ficou salvo, em vez do que o usuário digitou.
            self._v = app_prefs.obter()
            self.mudou.emit()
            self.mensagem.emit("Preferências ajustadas",
                               "Algumas preferências foram corrigidas ao salvar:\n\n• "
                               + "\n• ".join(erros), "warning")

        self._aplicar_a_quente()
        self._pendente_reinicio = self._precisa_reiniciar()
        self._snapshot = dict(self._v)
        self.mudou.emit()

        if self._pendente_reinicio:
            self.mensagem.emit(
                "Requer reinício",
                "As preferências foram salvas.\n\nAlgumas delas (escala da interface, nível e "
                "retenção de logs) só passam a valer quando o ComPasso for aberto novamente.",
                "info")
        else:
            self.fecharJanela.emit()

    @Slot()
    def cancelar(self) -> None:
        """Descarta as alterações não salvas, voltando ao snapshot de abertura."""
        self._v = dict(self._snapshot)
        self.mudou.emit()

    @Slot()
    def restaurar_padroes(self) -> None:
        """Devolve todos os campos aos valores de fábrica (só persiste ao salvar)."""
        self._v = app_prefs.padroes()
        self.mudou.emit()
        gui_logger.logger.info("Preferências do app restauradas aos padrões (ainda não salvas).")

    @Slot(str)
    def definir_pasta_dados(self, url: str) -> None:
        """Recebe a pasta escolhida no diálogo do QML (chega como file:// URL)."""
        caminho = url.replace("file:///", "").replace("file://", "") if url else ""
        self._v["pasta_dados_padrao"] = caminho
        self.mudou.emit()

    # ------------------------------------------------------------- atalhos de pastas
    @Slot()
    def abrir_pasta_logs(self) -> None:
        self._abrir(str(get_logs_dir()))

    @Slot()
    def abrir_pasta_dados(self) -> None:
        from compasso.core import config_manager
        from compasso.utils import get_documents_dir, APP_NAME, DATA_DIRNAME

        destino = self._v.get("pasta_dados_padrao") or str(
            get_documents_dir() / APP_NAME / DATA_DIRNAME)
        self._abrir(destino)

    @Slot()
    def abrir_pasta_configs(self) -> None:
        from compasso.core import config_manager

        self._abrir(str(config_manager.get_experiment_files_dir()))

    def _abrir(self, caminho: str) -> None:
        try:
            open_path(caminho)
        except Exception as e:
            gui_logger.logger.warning(f"Falha ao abrir '{caminho}': {e}")
            self.mensagem.emit("Erro", f"Não foi possível abrir a pasta:\n{caminho}", "warning")

    # ----------------------------------------------------------------- aplicação
    def _precisa_reiniciar(self) -> bool:
        """True se alguma preferência que só vale no arranque mudou nesta edição."""
        return any(self._v.get(c) != self._snapshot.get(c) for c in app_prefs.REQUEREM_REINICIO)

    def _aplicar_a_quente(self) -> None:
        """Aplica agora o que não depende de reinício.

        Timeouts de LSL/watchdog não aparecem aqui de propósito: são lidos de ``app_prefs`` a
        cada nova conexão e a cada novo watchdog, então já valem sem nada a fazer.
        """
        if self._v.get("controlar_volume_sistema"):
            try:
                set_system_volume(int(self._v.get("volume_inicial", 50)))
            except Exception as e:
                gui_logger.logger.warning(f"Falha ao aplicar o volume das preferências: {e}")
        gui_logger.logger.info(f"Preferências do app aplicadas: {app_prefs.resumo_para_log()}")
