"""Bootstrap da aplicação PySide6/QML do ComPasso.

Sobe o ``QApplication``, cria o ``Context`` e o ``Theme`` (expostos ao QML), carrega
``qml/Main.qml`` e entra no laço de eventos do Qt. Equivalente ao antigo ``ComPasso(ctk.CTk)``
+ ``app.mainloop()``, porém a construção da UI passa a ser declarativa (QML).
"""

import logging
import os
import sys
import time
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterType
from PySide6.QtQuickControls2 import QQuickStyle

from . import gui_logger
from .carregamento import Carregador
from .context import Context
from .theme import Theme
from .assets import ASSETS_DIR, ICON_FILENAME, BEEP_FILENAME
from .controllers.connection_controller import ConnectionController
from .controllers.participant_controller import ParticipantController
from .controllers.files_controller import FilesController
from .controllers.player_controller import PlayerController
from .controllers.experiment_controller import ExperimentController
from .controllers.app_controller import AppController
from .controllers.graph_settings_controller import GraphSettingsController
from .controllers.calibration_controller import CalibrationController
from .controllers.config_controller import ConfigController
from .controllers.updates_controller import UpdatesController
from .controllers.app_settings_controller import AppSettingsController
from .signal_chart import GraficoSinal
from compasso.core import config_manager, set_system_volume, app_prefs
from compasso.core.constants import SENSOR_TYPES
from compasso.utils import get_logs_dir

# Volume principal do sistema aplicado uma única vez no arranque (como no app antigo).
_INIT_VOLUME = 50

# Modo de teste sem hardware: se COMPASSO_FAKE_BITALINO estiver setado (truthy), o app sobe uma
# stream LSL fake no arranque e pré-preenche o MAC — ver core/fake_bitalino.py.
_FAKE_ENV = "COMPASSO_FAKE_BITALINO"


def _fake_bitalino_habilitado() -> bool:
    return os.environ.get(_FAKE_ENV, "").strip().lower() not in ("", "0", "false", "no")

# Diretório dos arquivos .qml (ao lado deste módulo; resolve em dev e empacotado).
QML_DIR = Path(__file__).resolve().parent / "qml"


def _resolver_qml_dir() -> Path:
    """Retorna o diretório dos .qml, considerando execução congelada (PyInstaller)."""
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", ".")) / "compasso" / "gui_qt" / "qml"
        if base.exists():
            return base
    return QML_DIR


def _limpar_logs_antigos(dias: int) -> None:
    """Apaga arquivos de log com mais de ``dias`` dias (preferência ``retencao_logs_dias``).

    Só remove ``*.log`` dentro da pasta de logs — nunca toca em dados de participante, que
    ficam em outra árvore (Documentos/ComPasso/Dados).
    """
    limite = time.time() - dias * 86400
    removidos = 0
    try:
        for arquivo in get_logs_dir().rglob("*.log"):
            try:
                if arquivo.stat().st_mtime < limite:
                    arquivo.unlink()
                    removidos += 1
            except OSError:
                # arquivo em uso (o log desta execução) ou sem permissão: seguir adiante.
                continue
    except Exception as e:
        gui_logger.logger.warning(f"Falha ao limpar logs antigos: {e}")
        return
    if removidos:
        gui_logger.logger.info(f"Logs antigos removidos: {removidos} arquivo(s) (> {dias} dias).")


def _montar_carregador(app, ctx, config_controller) -> Carregador:
    """Monta a fila de etapas do arranque, na ordem em que devem rodar sob a splash.

    A ordem importa: o áudio vem primeiro (é a etapa mais cara e o beep precisa estar pronto
    antes de o usuário alcançar o botão "Começar"); o MAC do modo fake é escrito depois do
    auto-load do ``.config``, senão o ``.config`` o sobrescreveria.
    """
    carregador = Carregador(app)
    estado: dict = {}   # carrega o MAC fake entre as etapas.

    def preparar_audio() -> None:
        # pré-carrega o beep aqui para pagar o custo de inicialização do backend de áudio fora
        # da contagem regressiva do experimento: durante o experimento, tocar o beep precisa
        # ser só um play(), sem latência variável — ver Player.preload_beep.
        ctx.player.preload_beep(ctx.beep_caminho)

    def aplicar_diagnostico() -> None:
        """Aplica nível de log e retenção — daí serem preferências de reinício.

        Os loggers são criados no import de cada pacote, antes de qualquer preferência poder
        ser lida; por isso o nível é reaplicado aqui, a todos os loggers já existentes.
        """
        prefs = app_prefs.obter()
        nivel = logging.getLevelName(str(prefs.get("nivel_log", "INFO")).upper())
        if isinstance(nivel, int):
            for nome in list(logging.Logger.manager.loggerDict):
                logger = logging.getLogger(nome)
                if logger.handlers:            # só os nossos (SetLogger anexa handlers)
                    logger.setLevel(nivel)
            gui_logger.logger.info(f"Nível de log aplicado: {prefs.get('nivel_log')}")

        dias = int(prefs.get("retencao_logs_dias", 0))
        if dias > 0:
            _limpar_logs_antigos(dias)

    def ajustar_volume() -> None:
        prefs = app_prefs.obter()
        if not prefs.get("controlar_volume_sistema", True):
            gui_logger.logger.info("Controle de volume do sistema desabilitado nas preferências.")
            return
        set_system_volume(int(prefs.get("volume_inicial", _INIT_VOLUME)))

    def iniciar_bitalino_fake() -> None:
        """Sobe o simulador se a preferência OU a variável de ambiente pedirem.

        As duas portas coexistem: a variável de ambiente serve a scripts/CI (e continua tendo a
        última palavra sobre o MAC), a preferência serve ao usuário pela janela de configurações.
        """
        from compasso.core import fake_bitalino

        por_env = _fake_bitalino_habilitado()
        por_pref = app_prefs.obter().get("simular_bitalino", False)
        if not (por_env or por_pref):
            return

        mac_pedido = os.environ.get("COMPASSO_FAKE_BITALINO_MAC", fake_bitalino.MAC_PADRAO)
        # o provedor faz o sinal simulado seguir o sensor/canal escolhidos na GUI, inclusive
        # quando o usuário os troca com a stream já publicada.
        mac_fake = fake_bitalino.iniciar(
            mac_pedido,
            provedor_config=lambda: (ctx.sensor_type, ctx.signal_channel))
        if mac_fake is None:
            return
        estado["mac_fake"] = mac_fake
        ctx.simulacaoAtiva = True     # a barra de conexão avisa que os dados não são reais.
        origem = _FAKE_ENV if por_env else "preferência 'Simular BITalino'"
        gui_logger.logger.info(
            f"BITalino simulado ativo ({origem}): stream em {mac_fake} — clique em Conectar.")

    def carregar_ultima_config() -> None:
        if app_prefs.obter().get("auto_carregar_config", True):
            config_controller.carregar_ultima()
        else:
            gui_logger.logger.info("Auto-carregamento do último .config desabilitado nas preferências.")
        mac_fake = estado.get("mac_fake")
        if mac_fake:
            # depois do auto-load, para o modo de teste vencer o MAC do .config.
            ctx.mac_addr = mac_fake
            ctx.marcar_conexao_info_mudou()

    def ha_varredura_pendente() -> bool:
        """Só espera pelas durações se há de fato músicas+planilha para varrer."""
        return bool(ctx.music_folder and ctx.conditions_file and not ctx.duracoes_audio)

    carregador.adicionar("Preparando o áudio...", preparar_audio)
    carregador.adicionar("Aplicando preferências de diagnóstico...", aplicar_diagnostico)
    carregador.adicionar("Ajustando o volume do sistema...", ajustar_volume)
    carregador.adicionar("Iniciando sensor simulado...", iniciar_bitalino_fake)
    carregador.adicionar("Carregando a última configuração...", carregar_ultima_config)
    # a varredura de músicas/planilha disparada acima é assíncrona; a splash segura aqui até a
    # pré-varredura de durações terminar, para o app abrir com o material já pronto.
    carregador.adicionar_espera("Analisando as faixas de áudio...",
                                ctx.sonda_duracao.concluida, condicao=ha_varredura_pendente)
    return carregador


def executar_app(versao: str = "") -> int:
    """Cria e executa a aplicação Qt/QML. Retorna o código de saída do ``exec()``."""
    app = QGuiApplication(sys.argv)
    app.setApplicationName("ComPasso")
    app.setOrganizationName("ComPasso")

    # Estilo dos Qt Quick Controls: "Basic" permite customização total de cores/formas
    # (o estilo nativo do SO ignora muitas propriedades visuais).
    QQuickStyle.setStyle("Basic")

    # Gráfico do sinal: item nativo QQuickPaintedItem (QPainter), sem QtCharts/OpenGL.
    qmlRegisterType(GraficoSinal, "Compasso", 1, 0, "GraficoSinal")

    icone = ASSETS_DIR / ICON_FILENAME
    if icone.exists():
        app.setWindowIcon(QIcon(str(icone)))

    # Estado + tema, expostos ao QML como propriedades de contexto globais.
    ctx = Context()
    ctx.beep_caminho = str(ASSETS_DIR / BEEP_FILENAME)

    # As preferências do gráfico precisam existir ANTES do `engine.load()`: o `GraficoSinal` lê
    # `ctx.graph_settings` no instante em que o QML o cria (ver `signal_chart._set_contexto`) e
    # não relê depois. Levá-las para a fila de carregamento (que roda após o load) fazia o
    # gráfico nascer com os defaults e só assumir as preferências salvas quando o usuário
    # abrisse a janela "Configurações → Gráfico" — que é o que as reaplica. É uma leitura de
    # um JSON pequeno; não há o que ganhar adiando-a.
    try:
        ctx.graph_settings = config_manager.get_graph_prefs()
    except Exception as e:
        gui_logger.logger.warning(f"Falha ao carregar preferências do gráfico: {e}")

    theme = Theme()

    # Controllers (backend das views). Ligados ao Context; expostos ao QML por nome.
    conn_controller = ConnectionController(ctx)
    part_controller = ParticipantController(ctx)
    files_controller = FilesController(ctx)
    player_controller = PlayerController(ctx)
    experiment_controller = ExperimentController(ctx, part_controller, player_controller)
    app_controller = AppController()
    graph_settings_controller = GraphSettingsController(ctx)
    calibration_controller = CalibrationController(ctx)
    config_controller = ConfigController(ctx, files_controller)
    updates_controller = UpdatesController(ctx, versao_atual=versao)
    app_settings_controller = AppSettingsController(ctx)
    # O gráfico (GraficoSinal) é instanciado pelo QML e se registra em ctx.signal_plot ao
    # receber o `contexto` — não é criado aqui.

    # Fila de carregamento: tudo que antes bloqueava o arranque roda agora DEPOIS do
    # engine.load(), sob a splash, que mostra a etapa e o progresso — ver carregamento.py.
    carregador = _montar_carregador(app, ctx, config_controller)

    engine = QQmlApplicationEngine()
    ctx_qml = engine.rootContext()
    ctx_qml.setContextProperty("ctx", ctx)
    ctx_qml.setContextProperty("Theme", theme)
    ctx_qml.setContextProperty("connController", conn_controller)
    ctx_qml.setContextProperty("partController", part_controller)
    ctx_qml.setContextProperty("filesController", files_controller)
    ctx_qml.setContextProperty("playerController", player_controller)
    ctx_qml.setContextProperty("experimentController", experiment_controller)
    ctx_qml.setContextProperty("appController", app_controller)
    ctx_qml.setContextProperty("graphSettingsController", graph_settings_controller)
    ctx_qml.setContextProperty("calibController", calibration_controller)
    ctx_qml.setContextProperty("configController", config_controller)
    ctx_qml.setContextProperty("updatesController", updates_controller)
    ctx_qml.setContextProperty("carregador", carregador)
    ctx_qml.setContextProperty("appSettingsController", app_settings_controller)
    # preferências que o QML lê direto no arranque (splash, geometria da janela).
    ctx_qml.setContextProperty("prefsApp", app_prefs.obter())
    # geometria da última sessão (ou {} se desligado/ausente) — aplicada por Main.qml.
    ctx_qml.setContextProperty("geometriaSalva", app_prefs.obter_geometria() or {})
    ctx_qml.setContextProperty("appVersion", versao)
    ctx_qml.setContextProperty("assetsDir", QUrl.fromLocalFile(str(ASSETS_DIR)).toString())
    ctx_qml.setContextProperty("sensoresDisponiveis", list(SENSOR_TYPES))

    qml_dir = _resolver_qml_dir()
    engine.addImportPath(str(qml_dir))
    main_qml = qml_dir / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(main_qml)))

    if not engine.rootObjects():
        gui_logger.logger.critical(f"Falha ao carregar {main_qml} — nenhum objeto raiz criado.")
        return 1

    gui_logger.logger.info("Interface QML carregada com sucesso.")

    # Rede de segurança do ponto acima: se por algum motivo o gráfico foi criado antes de
    # `ctx.graph_settings` existir, ele ficaria com os defaults até alguém abrir a janela de
    # configurações. Reaplicar aqui é barato e idempotente (nada está gravando ainda).
    plot = getattr(ctx, "signal_plot", None)
    if plot is not None and ctx.graph_settings:
        try:
            plot.apply_settings(dict(ctx.graph_settings))
        except Exception as e:
            gui_logger.logger.warning(f"Falha ao aplicar as preferências ao gráfico: {e}")

    # A janela já existe (só a splash é visível): agora sim roda o trabalho pesado, etapa a
    # etapa, com o progresso aparecendo na tela de carregamento.
    carregador.iniciar()

    # Verificação silenciosa de nova versão, uma vez por execução. Roda em thread de trabalho
    # e cabe folgada na splash; se a rede falhar, ninguém é incomodado. Desligável para quem
    # roda em laboratório sem internet, onde a espera pela rede só atrasa o arranque.
    if app_prefs.obter().get("verificar_atualizacoes", True):
        updates_controller.verificar_automatico()
    app._compasso_carregador = carregador          # type: ignore[attr-defined]
    # Mantém referências vivas enquanto o app roda (evita coleta pelo GC).
    app._compasso_ctx = ctx                       # type: ignore[attr-defined]
    app._compasso_theme = theme                   # type: ignore[attr-defined]
    app._compasso_controllers = [                    # type: ignore[attr-defined]
        conn_controller, part_controller, files_controller,
        player_controller, experiment_controller, app_controller,
        graph_settings_controller, calibration_controller, config_controller,
        updates_controller, app_settings_controller,
    ]
    return app.exec()
