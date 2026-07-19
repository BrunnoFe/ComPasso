"""Bootstrap da aplicação PySide6/QML do ComPasso.

Sobe o ``QApplication``, cria o ``Context`` e o ``Theme`` (expostos ao QML), carrega
``qml/Main.qml`` e entra no laço de eventos do Qt. Equivalente ao antigo ``ComPasso(ctk.CTk)``
+ ``app.mainloop()``, porém a construção da UI passa a ser declarativa (QML).
"""

import os
import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterType
from PySide6.QtQuickControls2 import QQuickStyle

from . import gui_logger
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
from .signal_chart import GraficoSinal
from compasso.core import config_manager, set_system_volume
from compasso.core.constants import SENSOR_TYPES

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
    # carrega o beep aqui (arranque do app) para pagar o custo de inicialização do backend de
    # áudio fora da contagem regressiva do experimento: durante o experimento, tocar o beep
    # precisa ser só um play(), sem latência variável — ver Player.preload_beep.
    ctx.player.preload_beep(ctx.beep_caminho)
    try:
        ctx.graph_settings = config_manager.get_graph_prefs()
    except Exception as e:
        gui_logger.logger.warning(f"Falha ao carregar preferências do gráfico: {e}")

    # Modo de teste sem hardware: sobe a stream LSL fake (o MAC é pré-preenchido depois do
    # auto-load do .config, para não ser sobrescrito). Ativado por COMPASSO_FAKE_BITALINO=1.
    mac_fake = None
    if _fake_bitalino_habilitado():
        try:
            from compasso.core.fake_bitalino import MAC_PADRAO, iniciar_em_thread
            mac_fake = os.environ.get("COMPASSO_FAKE_BITALINO_MAC", MAC_PADRAO)
            thread, parar = iniciar_em_thread(mac_fake)
            # mantém referências vivas (evita GC do evento/thread durante a execução).
            app._compasso_fake = (thread, parar)          # type: ignore[attr-defined]
            gui_logger.logger.info(
                f"Modo BITalino FAKE ativo ({_FAKE_ENV}): stream em {mac_fake} — clique em Conectar.")
        except Exception as e:
            gui_logger.logger.warning(f"Falha ao iniciar o BITalino fake: {e}")
            mac_fake = None

    theme = Theme()

    # volume principal do sistema no arranque (uma única vez, como no app antigo).
    try:
        set_system_volume(_INIT_VOLUME)
    except Exception as e:
        gui_logger.logger.warning(f"Falha ao definir o volume inicial do sistema: {e}")

    # Controllers (backend das views). Ligados ao Context; expostos ao QML por nome.
    conn_controller = ConnectionController(ctx)
    part_controller = ParticipantController(ctx)
    files_controller = FilesController(ctx)
    player_controller = PlayerController(ctx)
    experiment_controller = ExperimentController(ctx)
    app_controller = AppController()
    graph_settings_controller = GraphSettingsController(ctx)
    calibration_controller = CalibrationController(ctx)
    config_controller = ConfigController(ctx, files_controller)
    updates_controller = UpdatesController(ctx, versao_atual=versao)
    # O gráfico (GraficoSinal) é instanciado pelo QML e se registra em ctx.signal_plot ao
    # receber o `contexto` — não é criado aqui.

    # Auto-carrega o último .config usado (se existir), deixando o app já configurado no arranque.
    try:
        config_controller.carregar_ultima()
    except Exception as e:
        gui_logger.logger.warning(f"Falha ao auto-carregar a última configuração: {e}")

    # Pré-preenche o MAC fake DEPOIS do auto-load, para o modo de teste vencer o MAC do .config.
    if mac_fake:
        ctx.mac_addr = mac_fake
        ctx.marcar_conexao_info_mudou()

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

    # Verificação silenciosa de nova versão, uma vez por execução. Roda em thread de trabalho
    # e cabe folgada na splash; se a rede falhar, ninguém é incomodado.
    updates_controller.verificar_automatico()
    # Mantém referências vivas enquanto o app roda (evita coleta pelo GC).
    app._compasso_ctx = ctx                       # type: ignore[attr-defined]
    app._compasso_theme = theme                   # type: ignore[attr-defined]
    app._compasso_controllers = [                    # type: ignore[attr-defined]
        conn_controller, part_controller, files_controller,
        player_controller, experiment_controller, app_controller,
        graph_settings_controller, calibration_controller, config_controller,
        updates_controller,
    ]
    return app.exec()
