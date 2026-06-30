# -*- mode: python ; coding: utf-8 -*-
"""Spec do PyInstaller para o Compasso (multiplataforma).

Build (a partir da raiz do projeto, com o venv ativo):
    pyinstaller compasso.spec

Windows -> dist/Compasso-win/Compasso.exe
macOS   -> dist/Compasso-mac/ + dist/Compasso.app  (gere assets/icon.icns antes; ver BUILD.md)
"""
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

is_win = sys.platform.startswith("win")
is_mac = sys.platform == "darwin"

# --- dados empacotados -------------------------------------------------------
datas = [("assets", "assets")]            # imagens + icon.ico
datas += collect_data_files("customtkinter")   # temas/fontes (o PyInstaller não acha sozinho)
datas += collect_data_files("CTkMessagebox")   # ícones do CTkMessagebox

# --- binários nativos --------------------------------------------------------
# pylsl carrega o liblsl (lsl.dll / liblsl.so / liblsl.dylib) via ctypes; precisa ser incluído.
binaries = collect_dynamic_libs("pylsl")

# --- imports que a análise estática não detecta ------------------------------
hiddenimports = [
    "pylsl",
    "openpyxl",        # engine usado por pandas.to_excel/read_excel (.xlsx)
    "et_xmlfile",
    "comtypes",
    "pycaw",
    "darkdetect",
    "CTkMessagebox",
]

# pygame-ce traz o próprio hook do PyInstaller — não precisa entrar aqui.

# NÃO excluir psutil (importado por pycaw.utils) nem packaging (importado por
# customtkinter.windows.ctk_tk/ctk_toplevel) — são dependências de runtime reais.
excludes = ["tkinter.test", "pygame.tests", "numpy.tests"]

icon_file = "assets/icon.ico" if is_win else ("assets/icon.icns" if is_mac else None)
version_file = "version_info.txt" if is_win else None
collect_name = "Compasso-win" if is_win else ("Compasso-mac" if is_mac else "Compasso")


a = Analysis(
    ["main.py"],
    pathex=["."],
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

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Compasso",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,                 # ignorado de forma graciosa se o UPX não estiver no PATH
    console=False,            # app GUI: sem janela de console
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
        name="Compasso.app",
        icon="assets/icon.icns",
        bundle_identifier="com.compasso.app",
    )
