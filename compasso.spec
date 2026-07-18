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
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_all

ONEFILE = bool(os.environ.get("COMPASSO_ONEFILE"))
is_win = sys.platform.startswith("win")
is_mac = sys.platform == "darwin"

# --- dados empacotados -------------------------------------------------------
datas = [("assets", "assets")]            # imagens + icon.ico
# arquivos .qml da GUI (a análise estática não os enxerga): preserva a árvore do pacote.
datas += [("src/compasso/gui_qt/qml", "compasso/gui_qt/qml")]

# --- binários nativos --------------------------------------------------------
# pylsl carrega o liblsl (lsl.dll / liblsl.so / liblsl.dylib) via ctypes; precisa ser incluído.
binaries = collect_dynamic_libs("pylsl")

# --- PySide6/Qt: libs, plugins e MÓDULOS QML (QtQuick/Controls/Dialogs) -------
# collect_all cobre libs Qt, plugins (platforms/imageformats/qmltooling) e os módulos QML
# necessários para o engine carregar a UI em runtime.
_pyside_datas, _pyside_bins, _pyside_hidden = collect_all("PySide6")
datas += _pyside_datas
binaries += _pyside_bins

# --- imports que a análise estática não detecta ------------------------------
hiddenimports = [
    "pylsl",
    "openpyxl",        # engine usado por pandas.to_excel/read_excel (.xlsx)
    "et_xmlfile",
    "comtypes",
    "pycaw",
] + _pyside_hidden

# pygame-ce traz o próprio hook do PyInstaller — não precisa entrar aqui.

# NÃO excluir psutil (importado por pycaw.utils) — dependência de runtime real.
#
# A suíte de testes (tests/) e o framework de teste NÃO são importados por main.py,
# então a análise estática já não os empacota; os excludes abaixo são uma salvaguarda
# explícita para garantir que nunca entrem no executável de release.
excludes = [
    "tkinter.test", "pygame.tests", "numpy.tests",
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
        upx=True,                 # ignorado de forma graciosa se o UPX não estiver no PATH
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
        upx=True,
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
        upx=True,
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
