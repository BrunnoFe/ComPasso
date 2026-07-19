"""Build do executável do ComPasso com **Nuitka** (alternativa ao PyInstaller do compasso.spec).

Por que um script próprio em vez do ``pyside6-deploy``:
- o ``pyside6-deploy`` renomeia ``main.py`` para ``deploy_main.py`` quando o comando fica longo e
  depois procura ``main.exe``, falhando ao finalizar (bug de naming);
- ele lista os 34 ``.qml`` um a um na linha de comando (o que estoura o limite do Windows), quando
  ``--include-data-dir`` resolve a pasta inteira de uma vez;
- aqui controlamos exatamente o que entra (assets, lsl.dll do pylsl, openpyxl, metadados de versão),
  cobrindo os pontos que a análise estática do Nuitka não enxerga.

Pré-requisitos (fora do ``uv.lock`` — instale no venv sem tocar o lock):
    uv pip install nuitka ordered_set zstandard

Nuitka baixa o próprio compilador (zig) na primeira execução — daí ``--assume-yes-for-downloads``.
Em Python 3.13+ o Nuitka NÃO aceita ``--mingw64`` (usa MSVC ou o zig auto-baixado).

Uso (da raiz do projeto):
    uv run python scripts/build_nuitka.py            # onefile (padrão)
    uv run python scripts/build_nuitka.py --standalone   # pasta (onedir), startup mais rápido

Saída: ``dist/nuitka/ComPasso.exe`` (onefile) ou ``dist/nuitka/ComPasso.dist/`` (standalone).
Ver BUILD.md, seção "Build alternativo com Nuitka".
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
IS_WIN = sys.platform.startswith("win")
IS_MAC = sys.platform == "darwin"

# DLLs Qt que o '--include-qt-plugins=qml' arrasta junto (o category "qml" inclui o ecossistema
# QML inteiro) mas que o ComPasso NÃO usa. A maior é a qt6webenginecore.dll (~195 MB). Excluídas
# por padrão de filename via '--noinclude-dlls'. NÃO listar aqui nada que a UI use: core/gui/qml/
# quick/quickcontrols2(basic)/quicktemplates2/quicklayouts/quickdialogs2/multimedia/network/
# opengl/svg + o fallback opengl32sw (mantido a pedido).
_QT_DLLS_EXCLUIR = (
    "qt6webengine*.dll", "qt6webview*.dll", "qt6webchannel*.dll", "qt6websockets*.dll",
    "qt63d*.dll", "qt6quick3d*.dll",                         # cena 3D
    "qt6charts*.dll", "qt6datavisualization*.dll", "qt6graphs*.dll",  # gráficos Qt (usamos QPainter)
    "qt6pdf*.dll", "qt6virtualkeyboard*.dll",
    "qt6sql*.dll", "qt6test.dll", "qt6quicktest*.dll",
    "qt6location*.dll", "qt6positioning*.dll", "qt6sensors*.dll",
    "qt6remoteobjects*.dll", "qt6scxml*.dll", "qt6statemachine*.dll",
    "qt6texttospeech*.dll", "qt6spatialaudio*.dll",
    # estilos de Qt Quick Controls que não usamos (a UI usa o estilo "Basic"):
    "qt6quickcontrols2fusion*.dll", "qt6quickcontrols2imagine*.dll",
    "qt6quickcontrols2material*.dll", "qt6quickcontrols2universal*.dll",
    "qt6quickcontrols2fluentwinui3*.dll", "qt6quickcontrols2windows*.dll",
    "qt6labs*.dll",
)


def _versao() -> str:
    """Versão do app (mesma fonte única do resto do projeto: pyproject via importlib.metadata)."""
    sys.path.insert(0, str(RAIZ / "src"))
    from compasso.utils import get_app_version  # import tardio: depende do sys.path acima
    return get_app_version()


def _pylsl_lib_files() -> list[Path]:
    """Binário(s) nativo(s) do pylsl (lsl.dll no Windows; .so/.dylib nos demais).

    O pylsl procura o binário em ``<pacote>/lib/`` — precisa ser empacotado exatamente lá.
    """
    import pylsl
    libdir = Path(pylsl.__file__).resolve().parent / "lib"
    padroes = ("*.dll",) if IS_WIN else ("*.so*", "*.dylib")
    arquivos: list[Path] = []
    for padrao in padroes:
        arquivos.extend(libdir.glob(padrao))
    return arquivos


def _montar_comando(onefile: bool, versao: str, saida: Path) -> list[str]:
    """Monta a lista de argumentos do Nuitka. Um data-dir por pasta (evita comando longo)."""
    args = [
        sys.executable, "-m", "nuitka",
        "--assume-yes-for-downloads",              # deixa o Nuitka baixar o compilador (zig)
        "--enable-plugin=pyside6",                 # trata libs Qt, plugins e QML do PySide6
        # o auto-detector do Nuitka inclui plugins por IMPORT Python; nossos .qml são DADO, então
        # ele não puxa 'qml'/'qmltooling' sozinho, e 'multimedia' (backend de áudio/beep) também
        # precisa ser explícito — sem isso a UI QML e o áudio não sobem no bundle.
        "--include-qt-plugins=qml,qmltooling,multimedia",
        "--onefile" if onefile else "--standalone",
        # --- dados que a análise estática do Nuitka não empacota sozinha ---
        "--include-data-dir=assets=assets",        # icon.ico/png, beep .wav (ver assets.py)
        f"--include-data-dir={Path('src/compasso/gui_qt/qml')}=compasso/gui_qt/qml",  # .qml
        "--include-package=openpyxl",              # engine .xlsx importado dinamicamente por pandas
        "--include-module=et_xmlfile",
        "--include-distribution-metadata=compasso",  # p/ get_app_version() achar a versão no bundle
        "--noinclude-qt-translations",             # app é PT-BR, sem i18n do Qt
        # --- saída ---
        f"--output-dir={saida}",
        "--output-filename=ComPasso",
        "--company-name=ComPasso",
        "--product-name=ComPasso",
        f"--file-version={versao}",
        f"--product-version={versao}",
        "--file-description=ComPasso",
    ]
    # corta as DLLs Qt que o category "qml" arrasta mas o app não usa (WebEngine, 3D, Charts...).
    args += [f"--noinclude-dlls={padrao}" for padrao in _QT_DLLS_EXCLUIR]
    # binário nativo do pylsl (lsl.dll): incluído arquivo-a-arquivo em pylsl/lib. '--include-data-dir'
    # e '--include-package-data' NÃO copiam DLLs; '--include-data-files' (arquivo explícito) copia.
    for lib in _pylsl_lib_files():
        args.append(f"--include-data-files={lib}=pylsl/lib/{lib.name}")
    if IS_WIN:
        # controle de volume no Windows (pycaw usa comtypes, com codegen COM em runtime).
        args += ["--include-package=comtypes", "--include-package=pycaw"]
        args += ["--windows-console-mode=disable"]   # app GUI, sem janela de console
        args.append(f"--windows-icon-from-ico={Path('assets/icon.ico')}")
    elif IS_MAC:
        args += ["--macos-create-app-bundle", f"--macos-app-icon={Path('assets/icon.icns')}"]
    args.append("main.py")
    return args


def main() -> None:
    parser = argparse.ArgumentParser(description="Build do ComPasso com Nuitka.")
    parser.add_argument("--standalone", action="store_true",
                        help="Gera pasta (onedir) em vez de onefile.")
    opcoes = parser.parse_args()

    onefile = not opcoes.standalone
    versao = _versao()
    saida = RAIZ / "build" / "nuitka"
    saida.mkdir(parents=True, exist_ok=True)

    comando = _montar_comando(onefile, versao, saida)
    print(f"[build_nuitka] Versão {versao} · modo {'onefile' if onefile else 'standalone'}")
    print("[build_nuitka] " + " ".join(comando))
    resultado = subprocess.run(comando, cwd=RAIZ)
    if resultado.returncode != 0:
        raise SystemExit(f"[build_nuitka] Nuitka falhou (código {resultado.returncode}).")

    # Copia o artefato final para dist/nuitka/, separando-o dos intermediários de build.
    dist = RAIZ / "dist" / "nuitka"
    dist.mkdir(parents=True, exist_ok=True)
    if onefile:
        exe = saida / ("ComPasso.exe" if IS_WIN else "ComPasso.bin")
        destino = dist / exe.name
        if exe.exists():
            shutil.copy2(exe, destino)
            mb = destino.stat().st_size / (1024 * 1024)
            print(f"[build_nuitka] OK: {destino} ({mb:.1f} MB)")
        else:
            raise SystemExit(f"[build_nuitka] Executável não encontrado em {exe}.")
    else:
        print(f"[build_nuitka] OK: pasta standalone em {saida / 'main.dist'} "
              "(copie o conteúdo para distribuir).")


if __name__ == "__main__":
    main()
