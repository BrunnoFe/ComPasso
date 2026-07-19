"""Controller de arquivos & dados (equivale ao antigo FilesCard).

Recebe da view os caminhos escolhidos (pasta de músicas, Excel de condições, diretório de
saída), dispara a varredura/casamento em thread de trabalho e atualiza o ``Context`` e os
contadores do rodapé. A seleção de caminhos usa os diálogos nativos do QML (``QtQuick.Dialogs``);
aqui só chegam os caminhos já escolhidos. Estado reativo (textos + marcas ✓/✗) observado pela
``FilesView`` via *binding*.
"""

import os

from PySide6.QtCore import QObject, Property, Signal, Slot, QUrl

from .. import gui_logger
from ..context import Context
from compasso.core.musics import scan_music_files, match_conditions
from compasso.core.experiment import session_totals

_MUSIC_HINT = "Pasta contendo os arquivos de música"
_COND_HINT = "Excel contendo as condições ou fatores das músicas"
_SAVE_HINT = "Diretório para salvar os dados"


class FilesController(QObject):
    """Seleção de arquivos, varredura de músicas e casamento com condições."""

    estadoChanged = Signal()
    mensagem = Signal(str, str, str)   # (titulo, texto, tipo)

    def __init__(self, ctx: Context):
        super().__init__()
        self._ctx = ctx
        self._scan_em_curso = False
        self._ctx.sonda_duracao.concluida.connect(self._on_duracoes_prontas)

    def _get_pasta_dados_padrao_url(self) -> str:
        """URL (file://) da pasta padrão de dados, ou "" se não houver preferência definida.

        Usada como ponto de partida do diálogo "Salvar dados em" — é o que dá utilidade prática
        à preferência ``pasta_dados_padrao``.
        """
        from compasso.core import app_prefs

        caminho = app_prefs.obter().get("pasta_dados_padrao", "")
        if caminho and os.path.isdir(caminho):
            return QUrl.fromLocalFile(caminho).toString()
        return ""

    pastaDadosPadraoUrl = Property(str, _get_pasta_dados_padrao_url, notify=estadoChanged)

    # ------------------------------------------------------------ propriedades
    def _texto(self, caminho, hint):
        return caminho if caminho else hint

    def _get_musica_texto(self):
        return self._texto(self._ctx.music_folder, _MUSIC_HINT)

    musicaTexto = Property(str, _get_musica_texto, notify=estadoChanged)

    def _get_condicoes_texto(self):
        return self._texto(self._ctx.conditions_file, _COND_HINT)

    condicoesTexto = Property(str, _get_condicoes_texto, notify=estadoChanged)

    def _get_saida_texto(self):
        return self._texto(self._ctx.save_dir, _SAVE_HINT)

    saidaTexto = Property(str, _get_saida_texto, notify=estadoChanged)

    def _get_musica_ok(self):
        return bool(self._ctx.music_folder)

    musicaOk = Property(bool, _get_musica_ok, notify=estadoChanged)

    def _get_condicoes_ok(self):
        return bool(self._ctx.conditions_file)

    condicoesOk = Property(bool, _get_condicoes_ok, notify=estadoChanged)

    def _get_saida_ok(self):
        return bool(self._ctx.save_dir)

    saidaOk = Property(bool, _get_saida_ok, notify=estadoChanged)

    # ----------------------------------------------------- seleção de caminhos
    @Slot(QUrl)
    def definir_musicas(self, url: QUrl) -> None:
        self._definir_caminho(url, "music_folder", "Erro ao carregar pasta com as músicas")

    @Slot(QUrl)
    def definir_condicoes(self, url: QUrl) -> None:
        self._definir_caminho(url, "conditions_file", "Erro ao carregar arquivo com as condições")

    @Slot(QUrl)
    def definir_saida(self, url: QUrl) -> None:
        self._definir_caminho(url, "save_dir", "Erro ao carregar diretório para salvar dados")

    def _definir_caminho(self, url: QUrl, ctx_attr: str, erro_msg: str) -> None:
        """Valida o caminho escolhido, grava no contexto e tenta a varredura se tudo estiver pronto."""
        caminho = url.toLocalFile() if isinstance(url, QUrl) else str(url)
        if not caminho:
            return
        try:
            if not os.path.exists(caminho):
                self.mensagem.emit("Erro", f"{erro_msg}: caminho inexistente.", "warning")
                return
        except Exception as e:
            self.mensagem.emit("Erro", f"{erro_msg}: {e}", "warning")
            return

        setattr(self._ctx, ctx_attr, caminho)
        # trocar a pasta/planilha invalida um mapeamento anterior (permite refazer a varredura).
        if ctx_attr in ("music_folder", "conditions_file"):
            self._ctx.music_condition_mapping = {}
        self.estadoChanged.emit()
        self._ctx.notify_stepper()
        gui_logger.logger.info(f"{ctx_attr} = {caminho}")
        self._tentar_varredura()

    # ------------------------------------------------------------- varredura
    @Slot()
    def revarrer(self) -> None:
        """Força uma nova varredura+casamento (ex.: após aplicar um .config). Limpa o mapeamento
        anterior para o gate de _tentar_varredura não abortar."""
        self._ctx.music_condition_mapping = {}
        self._scan_em_curso = False
        self._tentar_varredura()

    def _tentar_varredura(self) -> None:
        """Dispara a varredura+casamento (em thread) quando pasta e condições existem.

        A pasta de saída **não** é exigida aqui: casar músicas com condições depende só da pasta
        de áudios e da planilha; a saída só é necessária para iniciar o experimento (validada
        separadamente). Exigi-la aqui impedia o casamento quando o usuário carregava só os dois.
        """
        folder = self._ctx.music_folder
        cond = self._ctx.conditions_file
        if not (folder and cond):
            return
        if self._ctx.music_condition_mapping or self._scan_em_curso:
            return
        self._scan_em_curso = True
        self._ctx.status_text.set("Arquivos selecionados! Verificando condições...")
        self._ctx.run_async(lambda: self._varrer_e_casar(folder, cond))

    def _varrer_e_casar(self, folder: str, cond_path: str) -> None:
        """Varre as músicas e casa com as condições (thread de trabalho). Grava no contexto."""
        try:
            music_files = scan_music_files(folder)
        except FileNotFoundError as e:
            erro = str(e)
            self._scan_em_curso = False
            self._ctx.run_after(lambda: self.mensagem.emit(
                "Erro", f"Pasta de músicas não encontrada: {erro}.", "warning"))
            return

        if not music_files:
            self._scan_em_curso = False
            self._ctx.run_after(lambda: self._ctx.status_text.set(
                "Nenhum arquivo de áudio (.mp3/.wav/.ogg) na pasta selecionada."))
            gui_logger.logger.warning("Pasta selecionada não contém arquivos de áudio.")
            return

        self._ctx.music_files = music_files
        try:
            mapping, _ignoradas = match_conditions(
                music_files, cond_path,
                music_column=getattr(self._ctx, "music_column", "musica"),
                factor_column=getattr(self._ctx, "factor_column", "fator"))
        except FileNotFoundError:
            self._scan_em_curso = False
            self._ctx.run_after(lambda: self.mensagem.emit(
                "Erro", f"Arquivo de condições não encontrado: {cond_path}.", "warning"))
            return

        if not mapping:
            self._scan_em_curso = False
            texto = ("Nenhuma das músicas tem condição correspondente no arquivo selecionado.\n"
                     "Verifique os nomes dos arquivos e a planilha.")
            self._ctx.run_after(lambda: self.mensagem.emit("Atenção", texto, "warning"))
            return

        self._ctx.music_condition_mapping = mapping
        self._scan_em_curso = False
        self._sondar_duracoes(list(mapping.keys()))
        self._ctx.run_after(lambda: self._ctx.status_text.set(
            "Mapeamento de músicas para condições realizado com sucesso!"))
        self._ctx.run_after(self.estadoChanged.emit)
        self._atualizar_contadores()
        self._ctx.notify_stepper()
        gui_logger.logger.info("Mapeamento de músicas e condições realizado com sucesso.")

    def _sondar_duracoes(self, caminhos: list) -> None:
        """Pré-varre a duração das faixas casadas (assíncrono, na thread da GUI).

        O resultado alimenta ``ctx.duracoes_audio``, de onde o ``ExperimentRunner`` monta o eixo
        X do gráfico antes de a faixa começar. Roda muito antes do experimento e ninguém espera
        por ela: se não terminar a tempo, o runner cai no ``player.get_length()`` da carga.
        """
        self._ctx.run_after(lambda: self._ctx.sonda_duracao.sondar(caminhos))

    def _on_duracoes_prontas(self) -> None:
        """(Thread GUI) Publica no contexto o mapa de durações que a sonda terminou de ler."""
        self._ctx.duracoes_audio = self._ctx.sonda_duracao.duracoes()
        gui_logger.logger.info(
            f"Durações pré-varridas: {len(self._ctx.duracoes_audio)} arquivo(s).")

    def _atualizar_contadores(self) -> None:
        """Atualiza os contadores do rodapé a partir do mapeamento e da ``noise_quantity``."""
        mapping = self._ctx.music_condition_mapping or {}
        if not mapping:
            return
        mt, nt = session_totals(mapping, int(self._ctx.noise_quantity or 0))

        def aplicar():
            self._ctx.music_done_text.set("0")
            self._ctx.ruido_done_text.set("0")
            self._ctx.music_total_text.set(str(mt))
            self._ctx.ruido_total_text.set(str(nt))
            self._ctx.session_progress.set(0.0)
            self._ctx.session_status_text.set(f"0 / {mt + nt}")

        self._ctx.run_after(aplicar)
