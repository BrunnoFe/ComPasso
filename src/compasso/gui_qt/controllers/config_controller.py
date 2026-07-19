"""Controller da configuração do experimento (equivale a ExperimentConfigWindow + apply_config).

Cobre "Novo"/"Editar" (editor do ``.config``) e "Abrir" (carrega e aplica um ``.config`` ao app).
O editor mantém os campos como propriedades reativas; a validação usa ``config_manager``. Ao
salvar/abrir, ``apply_config`` mapeia os valores para o ``Context`` e emite os *notify* que as
views observam (conexão/arquivos/stepper/calibração), tornando o experimento iniciável.
"""

import os

from PySide6.QtCore import QObject, Property, Signal, Slot, QUrl

from .. import gui_logger
from ..context import Context
from compasso.core import config_manager
from compasso.core.config_manager import (
    save_config, load_config, validate_values, get_experiment_files_dir,
    CHANNEL_OPTIONS, PRE_STIMULUS_MIN, PRE_STIMULUS_MAX, PRE_STIMULUS_DEFAULT,
    MUSIC_COLUMN_DEFAULT, FACTOR_COLUMN_DEFAULT, BEEP_ENABLED_DEFAULT,
    BEEP_LEAD_MIN, BEEP_LEAD_MAX, BEEP_LEAD_DEFAULT, CALIBRATION_ENABLED_DEFAULT)
from compasso.core.constants import SENSOR_TYPES, SENSOR_DEFAULT
# mesma regra usada na conexão real: o campo aceita exatamente o que `connectar_bitalino`
# aceita, então um MAC aprovado aqui nunca é recusado depois pelo botão Conectar.
from compasso.core.bitalino_connect import MAC_RE

_CAMPOS_PADRAO = {
    "music_folder": "", "music_quantity": "", "noise_quantity": "", "factors_file": "",
    "music_column": "", "factor_column": "", "data_save_path": "", "bitalino_channel": "",
    "sensor_type": SENSOR_DEFAULT, "bitalino_mac": "",
    "pre_stimulus_seconds": PRE_STIMULUS_DEFAULT, "beep_enabled": BEEP_ENABLED_DEFAULT,
    "beep_lead_seconds": BEEP_LEAD_DEFAULT, "calibration_enabled": CALIBRATION_ENABLED_DEFAULT,
    "calibration_audio": "",
}


class ConfigController(QObject):
    """Editor do .config (Novo/Editar), abertura de .config e aplicação ao Context."""

    mudou = Signal()
    mensagem = Signal(str, str, str)       # (titulo, texto, tipo)
    pedirCaminhoSalvar = Signal()          # Novo: QML abre "salvar como"
    pedirConfirmarSobrescrever = Signal(str)  # Editar: QML confirma sobrescrever <nome>
    fecharJanela = Signal()

    def __init__(self, ctx: Context, files_controller=None):
        super().__init__()
        self._ctx = ctx
        self._files = files_controller
        self._d = dict(_CAMPOS_PADRAO)
        self._colunas = []
        self._modo = "novo"
        self._config_path = None

    def definir_files_controller(self, files_controller) -> None:
        self._files = files_controller

    # ------------------------------------------------------------- opções/limites
    channels = Property("QVariantList", lambda self: list(CHANNEL_OPTIONS), constant=True)
    sensores = Property("QVariantList", lambda self: list(SENSOR_TYPES), constant=True)
    preStimulusMin = Property(int, lambda self: PRE_STIMULUS_MIN, constant=True)
    preStimulusMax = Property(int, lambda self: PRE_STIMULUS_MAX, constant=True)
    beepLeadMin = Property(int, lambda self: BEEP_LEAD_MIN, constant=True)
    beepLeadMax = Property(int, lambda self: BEEP_LEAD_MAX, constant=True)

    def _get_titulo(self):
        return "Editar Configuração" if self._modo == "editar" else "Nova Configuração"

    titulo = Property(str, _get_titulo, notify=mudou)

    def _get_colunas(self):
        return self._colunas

    colunas = Property("QVariantList", _get_colunas, notify=mudou)

    def _get_beep_invalido(self):
        if not self._d.get("beep_enabled"):
            return False
        return int(self._d.get("beep_lead_seconds", 1)) >= int(self._d.get("pre_stimulus_seconds", 5))

    beepInvalido = Property(bool, _get_beep_invalido, notify=mudou)

    # -------------------------------------------------------------- validação de campos
    # Cada propriedade abaixo devolve a mensagem a exibir sob o campo ("" quando está tudo
    # certo), para que a view não precise repetir nenhuma regra: a borda vermelha é apenas
    # `texto !== ""`. As regras em si continuam vindo do core (`MAC_RE`, `validate_values`).
    def _get_erro_beep(self):
        if not self._get_beep_invalido():
            return ""
        return (f"O beep deve tocar antes do áudio: use um valor menor que o tempo "
                f"pré-estímulo ({self._d.get('pre_stimulus_seconds')} s).")

    erroBeep = Property(str, _get_erro_beep, notify=mudou)

    def _get_erro_colunas(self):
        musica = str(self._d.get("music_column", "")).strip()
        fator = str(self._d.get("factor_column", "")).strip()
        if not musica or not fator or musica != fator:
            return ""
        return "As colunas de áudios e de fatores não podem ser a mesma."

    erroColunas = Property(str, _get_erro_colunas, notify=mudou)

    def _get_erro_mac(self):
        mac = str(self._d.get("bitalino_mac", "")).strip()
        if not mac or MAC_RE.match(mac):
            return ""   # vazio não é "inválido": é só um campo ainda não preenchido.
        return "Formato inválido. Use XX:XX:XX:XX:XX:XX (ou com espaço/hífen)."

    erroMac = Property(str, _get_erro_mac, notify=mudou)

    @staticmethod
    def _erro_quantidade(valor, minimo, rotulo):
        """Mensagem para um campo de quantidade (inteiro >= mínimo); "" se válido ou vazio."""
        texto = str(valor).strip()
        if not texto:
            return ""
        try:
            quantidade = int(texto)
        except ValueError:
            return f"{rotulo} deve ser um número inteiro."
        if quantidade < minimo:
            return f"{rotulo} deve ser no mínimo {minimo}."
        return ""

    def _get_erro_musicas(self):
        return self._erro_quantidade(self._d.get("music_quantity", ""), 1, "A quantidade de músicas")

    erroMusicQuantity = Property(str, _get_erro_musicas, notify=mudou)

    def _get_erro_ruido(self):
        return self._erro_quantidade(self._d.get("noise_quantity", ""), 0, "A quantidade de ruído")

    erroNoiseQuantity = Property(str, _get_erro_ruido, notify=mudou)

    # ------------------------------------------------- propriedades dos campos
    def _mk(chave, tipo):
        def getter(self):
            return tipo(self._d.get(chave, _CAMPOS_PADRAO[chave]))

        def setter(self, valor):
            self._d[chave] = tipo(valor)
            self.mudou.emit()

        return getter, setter

    _g, _s = _mk("music_folder", str);       musicFolder = Property(str, _g, _s, notify=mudou)
    _g, _s = _mk("music_quantity", str);     musicQuantity = Property(str, _g, _s, notify=mudou)
    _g, _s = _mk("noise_quantity", str);     noiseQuantity = Property(str, _g, _s, notify=mudou)
    _g, _s = _mk("factors_file", str);       factorsFile = Property(str, _g, _s, notify=mudou)
    _g, _s = _mk("music_column", str);       musicColumn = Property(str, _g, _s, notify=mudou)
    _g, _s = _mk("factor_column", str);      factorColumn = Property(str, _g, _s, notify=mudou)
    _g, _s = _mk("data_save_path", str);     dataSavePath = Property(str, _g, _s, notify=mudou)
    _g, _s = _mk("bitalino_channel", str);   bitalinoChannel = Property(str, _g, _s, notify=mudou)
    _g, _s = _mk("sensor_type", str);        sensorTypeSel = Property(str, _g, _s, notify=mudou)
    _g, _s = _mk("bitalino_mac", str);       bitalinoMac = Property(str, _g, _s, notify=mudou)
    _g, _s = _mk("pre_stimulus_seconds", int); preStimulus = Property(int, _g, _s, notify=mudou)
    _g, _s = _mk("beep_enabled", bool);      beepEnabled = Property(bool, _g, _s, notify=mudou)
    _g, _s = _mk("beep_lead_seconds", int);  beepLead = Property(int, _g, _s, notify=mudou)
    _g, _s = _mk("calibration_enabled", bool); calibrationEnabled = Property(bool, _g, _s, notify=mudou)
    _g, _s = _mk("calibration_audio", str);  calibrationAudio = Property(str, _g, _s, notify=mudou)
    del _mk, _g, _s

    # ------------------------------------------------------------------ pickers
    @Slot(QUrl)
    def definir_musicas(self, url: QUrl):
        self._d["music_folder"] = url.toLocalFile(); self.mudou.emit()

    @Slot(QUrl)
    def definir_saida(self, url: QUrl):
        self._d["data_save_path"] = url.toLocalFile(); self.mudou.emit()

    @Slot(QUrl)
    def definir_calibracao(self, url: QUrl):
        self._d["calibration_audio"] = url.toLocalFile(); self.mudou.emit()

    @Slot(QUrl)
    def definir_fatores(self, url: QUrl):
        caminho = url.toLocalFile()
        self._d["factors_file"] = caminho
        self._d["music_column"] = ""
        self._d["factor_column"] = ""
        self._carregar_colunas(caminho)
        self.mudou.emit()

    def _carregar_colunas(self, caminho: str):
        """Lê os cabeçalhos do Excel de fatores (nrows=0) e popula os dropdowns de coluna."""
        self._colunas = []
        if not caminho or not os.path.isfile(caminho):
            return
        try:
            import pandas as pd   # import tardio (custo fora do arranque) — ver core/musics.py.

            self._colunas = [str(c) for c in pd.read_excel(caminho, nrows=0).columns]
        except Exception as e:
            gui_logger.logger.warning(f"Não foi possível ler as colunas de '{caminho}': {e}")
            self.mensagem.emit("Erro", f"Não foi possível ler as colunas da planilha:\n{e}", "warning")

    # ------------------------------------------------------------------- abrir
    @Slot()
    def abrir_novo(self):
        self._modo = "novo"
        self._config_path = None
        self._d = dict(_CAMPOS_PADRAO)
        self._colunas = []
        self.mudou.emit()

    @Slot()
    def abrir_editar(self):
        """Abre o editor pré-preenchido com a configuração atualmente carregada."""
        atual = getattr(self._ctx, "config_atual", None)
        if not isinstance(atual, dict) or not self._ctx.config_loaded:
            self.mensagem.emit("Editar", "Nenhuma configuração carregada para editar.", "info")
            return
        self._modo = "editar"
        self._config_path = getattr(self._ctx, "config_path", None)
        self._d = {**_CAMPOS_PADRAO, **{k: atual.get(k, _CAMPOS_PADRAO[k]) for k in _CAMPOS_PADRAO}}
        self._carregar_colunas(self._d.get("factors_file", ""))
        self.mudou.emit()

    @Slot(QUrl)
    def abrir_arquivo(self, url: QUrl):
        """Menu "Abrir": carrega um .config do disco e o aplica ao app."""
        caminho = url.toLocalFile()
        try:
            data, erros = load_config(caminho)   # load_config retorna (data, erros)
        except Exception as e:
            self.mensagem.emit("Erro", f"Não foi possível abrir a configuração:\n{e}", "warning")
            return
        if not isinstance(data, dict):
            msg = "\n".join(erros) if erros else "Arquivo de configuração inválido."
            self.mensagem.emit("Erro", msg, "warning")
            return
        if erros:
            self.mensagem.emit("Atenção", "Configuração carregada com avisos:\n" + "\n".join(erros), "warning")
        self.apply_config(data, caminho)
        self.mensagem.emit("Configuração", f"Configuração carregada: {os.path.basename(caminho)}", "info")

    # -------------------------------------------------------------------- salvar
    def _validar(self) -> bool:
        erros = validate_values(self._d)
        if erros:
            self.mensagem.emit("Configuração inválida", "\n".join(erros), "warning")
            return False
        # colunas escolhidas devem existir na planilha de fatores.
        fatores = self._d.get("factors_file", "")
        if fatores and os.path.isfile(fatores):
            try:
                import pandas as pd   # import tardio — ver core/musics.py.

                cols = {str(c) for c in pd.read_excel(fatores, nrows=0).columns}
            except Exception as e:
                self.mensagem.emit("Erro", f"Não foi possível ler as colunas da planilha:\n{e}", "warning")
                return False
            faltando = [self._d[k] for k in ("music_column", "factor_column")
                        if self._d[k] and self._d[k] not in cols]
            if faltando:
                self.mensagem.emit("Configuração inválida",
                                   "Colunas inexistentes na planilha: " + ", ".join(faltando), "warning")
                return False
        return True

    @Slot()
    def salvar(self):
        """Valida e decide o caminho: Editar confirma sobrescrever; Novo pede "salvar como"."""
        if not self._validar():
            return
        if self._modo == "editar" and self._config_path:
            self.pedirConfirmarSobrescrever.emit(os.path.basename(self._config_path))
        else:
            self.pedirCaminhoSalvar.emit()

    @Slot()
    def confirmar_sobrescrever(self):
        self._salvar_em(self._config_path)

    @Slot(QUrl)
    def salvar_como(self, url: QUrl):
        self._salvar_em(url.toLocalFile())

    def _salvar_em(self, caminho: str):
        if not caminho:
            return
        if not caminho.endswith(".config"):
            caminho += ".config"
        try:
            os.makedirs(str(get_experiment_files_dir()), exist_ok=True)
            save_config(caminho, self._d)
        except Exception as e:
            gui_logger.logger.error(f"Falha ao salvar configuração: {e}")
            self.mensagem.emit("Erro", f"Não foi possível salvar a configuração:\n{e}", "warning")
            return
        self.apply_config(self._d, caminho)
        gui_logger.logger.info(f"Configuração salva: {caminho}")
        self.fecharJanela.emit()

    # ---------------------------------------------------------------- apply_config
    def apply_config(self, data: dict, caminho: str = None) -> None:
        """Mapeia os valores da configuração para o ``Context`` e notifica as views.

        Porta o antigo ``ComPasso.apply_config``: cada campo é tratado individualmente e, ao
        final, marca ``config_loaded`` e atualiza stepper/checks/contadores/botão de calibração.
        """
        ctx = self._ctx
        ctx.config_atual = dict(data)
        ctx.config_path = caminho

        def s(v):
            return str(v).strip()

        # conexão
        mac = s(data.get("bitalino_mac", ""))
        if mac:
            ctx.mac_addr = mac
        canal = s(data.get("bitalino_channel", "")).upper()
        if canal.startswith("A") and canal[1:].isdigit():
            ctx.signal_channel = int(canal[1:])
        ctx.marcar_conexao_info_mudou()

        # sensor (aplica escala do gráfico se já registrado)
        sensor = s(data.get("sensor_type", SENSOR_DEFAULT)).upper()
        if sensor not in SENSOR_TYPES:
            sensor = SENSOR_DEFAULT
        ctx.sensor_type = sensor
        ctx.marcar_sensor_mudou()
        plot = getattr(ctx, "signal_plot", None)
        if plot is not None and hasattr(plot, "aplicar_sensor"):
            plot.aplicar_sensor(sensor, resetar_escala=False)

        # arquivos / condições / saída
        if s(data.get("music_folder", "")):
            ctx.music_folder = s(data.get("music_folder"))
        if s(data.get("factors_file", "")):
            ctx.conditions_file = s(data.get("factors_file"))
        ctx.music_column = s(data.get("music_column", "musica")) or MUSIC_COLUMN_DEFAULT
        ctx.factor_column = s(data.get("factor_column", "fator")) or FACTOR_COLUMN_DEFAULT
        if s(data.get("data_save_path", "")):
            ctx.save_dir = s(data.get("data_save_path"))

        # quantidades / tempos
        nq = data.get("noise_quantity", 0)
        ctx.noise_quantity = int(nq) if s(nq).isdigit() else 0
        ps = data.get("pre_stimulus_seconds", PRE_STIMULUS_DEFAULT)
        ps = int(ps) if s(ps).lstrip("-").isdigit() else PRE_STIMULUS_DEFAULT
        ctx.pre_stimulus_seconds = max(PRE_STIMULUS_MIN, min(PRE_STIMULUS_MAX, ps))

        # beep
        ctx.beep_habilitado = bool(data.get("beep_enabled", BEEP_ENABLED_DEFAULT))
        lead = data.get("beep_lead_seconds", BEEP_LEAD_DEFAULT)
        lead = int(lead) if s(lead).lstrip("-").isdigit() else BEEP_LEAD_DEFAULT
        ctx.beep_antecedencia_segundos = max(BEEP_LEAD_MIN, min(BEEP_LEAD_MAX, lead))

        # calibração
        ctx.calibracao_habilitada = bool(data.get("calibration_enabled", CALIBRATION_ENABLED_DEFAULT))
        audio = s(data.get("calibration_audio", ""))
        ctx.calibracao_caminho = audio or None
        if ctx.atualizar_botao_calibrar is not None:
            ctx.atualizar_botao_calibrar()

        ctx.config_loaded = True
        ctx.marcar_config_mudou()

        # lembra este .config como o último usado (auto-carregado no próximo arranque).
        if caminho:
            try:
                config_manager.set_last_config(caminho)
            except Exception as e:
                gui_logger.logger.warning(f"Não foi possível registrar o último .config: {e}")

        # reflete arquivos/contadores/stepper; se o config trouxe pasta de músicas + planilha,
        # dispara a varredura+casamento (senão o mapeamento nunca seria feito ao carregar um .config).
        if self._files is not None:
            self._files.estadoChanged.emit()
            if s(data.get("music_folder", "")) and s(data.get("factors_file", "")):
                self._files.revarrer()
            else:
                self._files._atualizar_contadores()
        ctx.notify_stepper()

    def carregar_ultima(self) -> bool:
        """Carrega e aplica o último .config usado (se existir e for válido). Chamado no arranque.

        Retorna True se aplicou algo. Falhas são silenciosas (só logadas) — arranque não deve
        quebrar por um .config ausente/movido.
        """
        try:
            caminho = config_manager.get_last_config_path()
        except Exception as e:
            gui_logger.logger.warning(f"Falha ao ler o último .config das preferências: {e}")
            return False
        if not caminho or not os.path.isfile(caminho):
            return False
        try:
            data, erros = load_config(caminho)
        except Exception as e:
            gui_logger.logger.warning(f"Não foi possível auto-carregar '{caminho}': {e}")
            return False
        if not isinstance(data, dict):
            gui_logger.logger.warning(f"Último .config inválido, ignorado: {caminho}")
            return False
        self.apply_config(data, caminho)
        gui_logger.logger.info(f"Configuração auto-carregada do último uso: {caminho}")
        return True
