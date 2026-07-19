# -*- mode: python ; coding: utf-8 -*-
"""Spec do PyInstaller para o ComPasso (multiplataforma, onedir + onefile).

Build (a partir da raiz do projeto, com o venv ativo):
    pyinstaller compasso.spec                 # onedir (padrão)
    COMPASSO_ONEFILE=1 pyinstaller compasso.spec   # onefile (Windows: set/$env:)

onedir  -> dist/ComPasso-win/ComPasso.exe   |  dist/ComPasso-mac/ (+ ComPasso.app)
onefile -> dist/ComPasso.exe                |  dist/ComPasso.app

CAVEATS do onefile (tratados aqui / no código):
- O EXE se auto-extrai num diretório TEMP a cada execução (sys._MEIPASS). NÃO escreva
  dados nele: dados/logs vão para pastas do usuário (Documentos/ComPasso, app-data) via
  src/utils/paths.py — independentes do bundle.
- Recursos empacotados (assets/, lsl.dll, .qml) ficam em sys._MEIPASS.
  src/compasso/gui_qt/assets.py resolve ASSETS_DIR a partir de sys._MEIPASS quando congelado;
  app.py resolve a pasta qml/ em sys._MEIPASS/compasso/gui_qt/qml.
- Startup mais lento (extração a cada run) e maior chance de falso-positivo de antivírus
  do que o onedir — por isso o onedir é o alvo primário para o release.
"""
import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_all, copy_metadata

ONEFILE = bool(os.environ.get("COMPASSO_ONEFILE"))
is_win = sys.platform.startswith("win")
is_mac = sys.platform == "darwin"

# --- enxugamento do PySide6 (COMPASSO_TRIM) ----------------------------------
# `collect_all("PySide6")` empacota o PySide6 INTEIRO (~634 MB de venv), inclusive
# subsistemas que o ComPasso nunca usa (WebEngine ~278 MB, Quick3D, Designer, Pdf, estilos
# não-Basic, ferramentas de dev). O app só usa, de fato:
#   Python: QtCore/QtGui/QtQml/QtQuick/QtQuickControls2/QtMultimedia
#   QML:    QtQuick, QtQuick.Window, QtQuick.Controls.Basic, QtQuick.Layouts, QtQuick.Dialogs
#
# TRIM_MODE controla o quanto se corta (as duas partem da MESMA saída do collect_all, então
# a resolução de QML continua a mesma que já funcionava — só muda o que é filtrado):
#   "none"     -> baseline: nada filtrado (comportamento antigo, para reprodução/depuração).
#   "subtract" -> collect_all MENOS uma blacklist de peças pesadas e comprovadamente inúteis
#                 (baixo risco: parte de "tudo funciona" e remove o conhecido-morto).
#   "minimal"  -> collect_all INTERSECÇÃO com uma whitelist do que é sabidamente necessário
#                 (mais enxuto, MAIOR risco: a whitelist pode omitir uma dependência transitiva;
#                 sempre validar lançando o .exe e exercitando as janelas/áudio/gráfico).
TRIM_MODE = os.environ.get("COMPASSO_TRIM", "none").lower()

# Peças a REMOVER no modo "subtract". Casadas por substring no caminho de destino do bundle
# (case-insensitive). opengl32sw (fallback de OpenGL por software) é deliberadamente MANTIDO:
# máquinas sem driver de GPU decente abrem a janela preta/crasham sem ele.
_TRIM_BLACKLIST = (
    "webengine",                                   # navegador embutido (~278 MB) — nunca usado
    "quick3d", "3drender", "3dcore", "3danimation",  # cena 3D — não usada
    "3dextras", "3dinput", "3dlogic", "3dquick",
    "qt6designer", "qtdesigner",                    # Qt Designer — não usado
    "qt6pdf", "qtpdf",                              # renderização de PDF — não usada
    "charts", "datavisualization",                 # gráficos Qt (o nosso é QPainter) — não usado
    "qt6sql", "qtsql", "qt6test", "qttest", "quicktest",
    "bluetooth", "nfc", "sensors", "positioning",  # periféricos — não usados
    "serialport", "serialbus", "websockets",
    "webchannel", "webview", "networkauth",
    # estilos de Qt Quick Controls que não usamos (só "Basic"):
    "controls2fluentwinui3", "controls2imagine", "controls2material",
    "controls2universal", "controls2fusion", "controls/fluentwinui3",
    "controls/imagine", "controls/material", "controls/universal", "controls/fusion",
    # ferramentas de linha de comando/dev empacotadas sem necessidade em runtime:
    "qmlls", "qmllint", "qmlformat", "qmlprofiler", "qmltestrunner", "qmlscene",
    "qsb.exe", "balsam", "linguist", "assistant", "designer.exe", "lupdate", "lrelease",
    "translations",                                # .qm de idiomas — app é PT-BR sem i18n Qt
)

# Peças a MANTER no modo "minimal" (tudo que não casar é descartado). Precisa cobrir libs Qt,
# módulos QML, plugins e o ffmpeg do QtMultimedia. Casadas por substring, case-insensitive.
_TRIM_WHITELIST = (
    # libs Qt (Qt6*.dll) usadas direta ou transitivamente pela UI QML + áudio:
    "qt6core", "qt6gui", "qt6network", "qt6opengl", "qt6dbus",
    "qt6qml", "qt6qmlmodels", "qt6qmlworkerscript", "qt6qmlmeta", "qt6qmlcompiler",
    "qt6quick", "qt6quickcontrols2", "qt6quicktemplates2", "qt6quicklayouts",
    "qt6quickdialogs2", "qt6quickshapes", "qt6labsqmlmodels",
    "qt6multimedia", "qt6multimediaquick", "qt6svg",
    # bindings Python (.pyd) e shiboken:
    "pyside6\\qtcore", "pyside6\\qtgui", "pyside6\\qtqml", "pyside6\\qtquick",
    "pyside6\\qtquickcontrols2", "pyside6\\qtmultimedia", "pyside6\\qtnetwork",
    "pyside6\\qtopengl", "pyside6/qtcore", "pyside6/qtgui", "pyside6/qtqml",
    "pyside6/qtquick", "pyside6/qtquickcontrols2", "pyside6/qtmultimedia",
    "pyside6/qtnetwork", "pyside6/qtopengl", "shiboken6",
    # módulos QML (mantém Controls/Basic; Material/Fusion/etc. ficam de fora naturalmente):
    "qml\\qtquick\\controls\\basic", "qml/qtquick/controls/basic",
    "qml\\qtquick\\window", "qml/qtquick/window",
    "qml\\qtquick\\layouts", "qml/qtquick/layouts",
    "qml\\qtquick\\dialogs", "qml/qtquick/dialogs",
    "qml\\qtquick\\templates", "qml/qtquick/templates",
    "qml\\qtqml", "qml/qtqml",
    # a raiz de qml/QtQuick (qmldir + plugin base) — sem barra depois de "quick" para pegar
    # os arquivos diretamente em qml/QtQuick/ (qmldir, qtquick2plugin.dll):
    "qml\\qtquick\\qmldir", "qml/qtquick/qmldir",
    "qtquick2plugin", "qtquickcontrols2plugin", "qtquickcontrols2basicstyleplugin",
    "qtquicklayoutsplugin", "qtquickwindowplugin", "qtquickdialogs2plugin",
    "qtquicktemplates2plugin", "qmlplugin", "qtqmlmeta",
    # plugins nativos essenciais:
    "plugins\\platforms\\qwindows", "plugins/platforms/qwindows",
    "plugins\\imageformats", "plugins/imageformats",       # png/ico do app
    "plugins\\iconengines", "plugins/iconengines",
    "plugins\\multimedia", "plugins/multimedia",           # backend ffmpeg do QtMultimedia
    "plugins\\tls", "plugins/tls", "plugins\\styles", "plugins/styles",
    "plugins\\generic", "plugins/generic",
    # ffmpeg (backend de áudio do QtMultimedia no Qt 6.11) — cortar quebra o beep/faixa:
    "avcodec", "avformat", "avutil", "swresample", "swscale",
    # OpenGL/ANGLE + fallback por software (mantido a pedido) e runtimes:
    "opengl32sw", "libegl", "libglesv2", "d3dcompiler", "qt6svgwidgets",
    "opengl.dll",
    # metadados do pacote + o próprio pacote compasso já entram por outros caminhos.
)


def _filtrar_pyside(entradas, is_hidden=False):
    """Aplica o modo TRIM a uma lista do collect_all (datas/binaries = tuplas; hidden = str)."""
    if TRIM_MODE not in ("subtract", "minimal"):
        return entradas
    mantidas = []
    for item in entradas:
        # datas/binaries são (src, dest); hiddenimports são strings (nome do módulo).
        alvo = item if is_hidden else item[1]
        low = str(alvo).lower()
        if TRIM_MODE == "subtract":
            if not any(t in low for t in _TRIM_BLACKLIST):
                mantidas.append(item)
        else:  # minimal
            if any(t in low for t in _TRIM_WHITELIST):
                mantidas.append(item)
    return mantidas

# --- dados empacotados -------------------------------------------------------
datas = [("assets", "assets")]            # imagens + icon.ico
# arquivos .qml da GUI (a análise estática não os enxerga): preserva a árvore do pacote.
datas += [("src/compasso/gui_qt/qml", "compasso/gui_qt/qml")]
# metadados do próprio pacote (dist-info): sem isso, get_app_version() (via
# importlib.metadata) não encontraria a versão no executável congelado — ver
# src/compasso/utils/version.py.
datas += copy_metadata("compasso")

# --- binários nativos --------------------------------------------------------
# pylsl carrega o liblsl (lsl.dll / liblsl.so / liblsl.dylib) via ctypes; precisa ser incluído.
binaries = collect_dynamic_libs("pylsl")

# --- PySide6/Qt: libs, plugins e MÓDULOS QML (QtQuick/Controls/Dialogs) -------
# collect_all cobre libs Qt, plugins (platforms/imageformats/qmltooling) e os módulos QML
# necessários para o engine carregar a UI em runtime. Em seguida, _filtrar_pyside aplica o
# enxugamento escolhido em COMPASSO_TRIM (subtract/minimal) — ver bloco no topo do arquivo.
_pyside_datas, _pyside_bins, _pyside_hidden = collect_all("PySide6")
_pyside_datas = _filtrar_pyside(_pyside_datas)
_pyside_bins = _filtrar_pyside(_pyside_bins)
_pyside_hidden = _filtrar_pyside(_pyside_hidden, is_hidden=True)
if TRIM_MODE in ("subtract", "minimal"):
    print(f"[compasso.spec] COMPASSO_TRIM={TRIM_MODE}: "
          f"{len(_pyside_datas)} datas, {len(_pyside_bins)} binaries mantidos do PySide6.")
datas += _pyside_datas
binaries += _pyside_bins

# QtMultimedia (reprodução de áudio, ver core/player.py) carrega em runtime o plugin de backend
# de mídia (ffmpeg no Qt 6.11, em plugins/multimedia/) + os codecs (avcodec/avformat/...). O
# collect_all("PySide6") acima já os inclui (verificado); só declaramos o import oculto abaixo
# porque a análise estática não vê o módulo sendo importado por core/player.py.

# --- imports que a análise estática não detecta ------------------------------
hiddenimports = [
    "pylsl",
    "openpyxl",        # engine usado por pandas.to_excel/read_excel (.xlsx)
    "et_xmlfile",
    "comtypes",
    "pycaw",
    "PySide6.QtMultimedia",
] + _pyside_hidden

# NÃO excluir psutil (importado por pycaw.utils) — dependência de runtime real.
#
# A suíte de testes (tests/) e o framework de teste NÃO são importados por main.py,
# então a análise estática já não os empacota; os excludes abaixo são uma salvaguarda
# explícita para garantir que nunca entrem no executável de release.
excludes = [
    "tkinter.test", "numpy.tests",
    "tests", "pytest", "_pytest", "pytest_mock",
]

icon_file = "assets/icon.ico" if is_win else ("assets/icon.icns" if is_mac else None)
version_file = "version_info.txt" if is_win else None
collect_name = "ComPasso-win" if is_win else ("ComPasso-mac" if is_mac else "ComPasso")


a = Analysis(
    ["main.py"],
    # src-layout: o pacote `compasso` mora em src/, não na raiz. "src" no pathex garante
    # que o PyInstaller resolva `import compasso` a partir do main.py sem depender de uma
    # instalação editável prévia. "." mantém a raiz acessível (main.py, assets/ via datas).
    pathex=["src", "."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)

pyz = PYZ(a.pure)

if ONEFILE:
    # Tudo (scripts, binários e dados) embutido em um único EXE auto-extraível.
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name="ComPasso",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,               # sem UPX: reduz falso-positivo de antivírus (decisão de projeto)
        upx_exclude=[],
        runtime_tmpdir=None,      # usa o TEMP padrão do SO para a auto-extração
        console=False,            # app GUI: sem janela de console
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=icon_file,
        version=version_file,
    )
    if is_mac:
        app = BUNDLE(
            exe,
            name="ComPasso.app",
            icon="assets/icon.icns",
            bundle_identifier="com.compasso.app",
        )
else:
    # onedir: EXE leve + pasta _internal com binários/dados (startup rápido).
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="ComPasso",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,               # sem UPX: reduz falso-positivo de antivírus (decisão de projeto)
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=icon_file,
        version=version_file,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=False,               # sem UPX: reduz falso-positivo de antivírus (decisão de projeto)
        upx_exclude=[],
        name=collect_name,
    )
    if is_mac:
        app = BUNDLE(
            coll,
            name="ComPasso.app",
            icon="assets/icon.icns",
            bundle_identifier="com.compasso.app",
        )
