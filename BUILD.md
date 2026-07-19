# Build do ComPasso (executável)

Gera um executável otimizado do ComPasso com **PyInstaller** (build em pasta única,
`--onedir`). O `compasso.spec` é multiplataforma, mas **PyInstaller não faz
cross-compilação**: o `.exe` é gerado no Windows e o `.app` no macOS.

## Pré-requisitos

- Python 3.12+ (o projeto foi validado em 3.14).
- [`uv`](https://docs.astral.sh/uv/) instalado.
- (Opcional) **UPX** para comprimir os binários (PyInstaller). Aponte com `--upx-dir` se não
  estiver no `PATH`. Ver a nota de tamanho abaixo — no onefile o ganho é pequeno.
- (Opcional) **Nuitka** para o build enxuto — ver "Build alternativo com Nuitka".
- OpenSignals/`liblsl` **não** são necessários para *buildar*, apenas para usar o app.

## Preparar o ambiente

```bash
uv sync
```

`uv sync` cria `.venv/` e instala dependências de runtime + build/teste (grupo `dev`) a
partir de `pyproject.toml`/`uv.lock`, num único comando.

## Antes de buildar: sincronizar a versão

A versão do app é centralizada em **`pyproject.toml`** (`[project].version`) — é a única linha
editada à mão a cada release. Antes de gerar o build, regenere `version_info.txt` (recurso de
versão do executável Windows) a partir dela:

```bash
uv run python scripts/generate_version_info.py
```

`main.py` já lê a versão em runtime via `get_app_version()` (`importlib.metadata`), sem hardcode —
não precisa de passo manual para isso. O que o script acima resolve é só `version_info.txt`, que é
um arquivo estático que o PyInstaller não consegue gerar dinamicamente. Esqueceu de rodar o
script depois de mudar a versão? `pytest tests/test_versioning.py` falha para avisar.

## Gerar o build

### onedir (padrão, recomendado para release)

```bash
uv run pyinstaller compasso.spec
```

Saída:

- **Windows:** `dist/ComPasso-win/ComPasso.exe` (apoio em `dist/ComPasso-win/_internal/`).
- **macOS:** `dist/ComPasso-mac/` e o bundle `dist/ComPasso.app`.

Teste rápido no Windows: `dist\ComPasso-win\ComPasso.exe`

### onefile (variante de arquivo único)

Defina `COMPASSO_ONEFILE` antes de buildar. Além dela, o `compasso.spec` aceita toggles por env
var para **enxugar** o bundle (o PySide6 tem ~634 MB e o `collect_all` puxava tudo, inclusive o
WebEngine de ~278 MB que o app nunca usa):

| Env var | Efeito | Padrão |
| --- | --- | --- |
| `COMPASSO_ONEFILE=1` | Arquivo único auto-extraível (em vez de onedir) | onedir |
| `COMPASSO_TRIM=subtract` | `collect_all` **menos** peças pesadas inúteis (WebEngine, Quick3D, Designer, Pdf, estilos não-Basic, dev tools) — **seguro** | `none` |
| `COMPASSO_TRIM=minimal` | Mantém só o que é sabidamente necessário — menor, **valide bem** (diálogos/janelas) | `none` |
| `COMPASSO_UPX=1` | Comprime as DLLs com UPX (precisa do `upx.exe`; ver abaixo) | off |
| `COMPASSO_STRIP=1` | `strip=True` no EXE/COLLECT (quase no-op no Windows) | off |

```powershell
# Windows (PowerShell) — onefile enxuto e seguro (recomendado):
$env:COMPASSO_ONEFILE = "1"; $env:COMPASSO_TRIM = "minimal"
uv run pyinstaller compasso.spec
Remove-Item Env:\COMPASSO_ONEFILE, Env:\COMPASSO_TRIM

# onefile minimal + UPX (menor ainda; UPX não vem no PATH, aponte com --upx-dir):
$env:COMPASSO_ONEFILE = "1"; $env:COMPASSO_TRIM = "minimal"; $env:COMPASSO_UPX = "1"
uv run pyinstaller compasso.spec --upx-dir "C:\caminho\para\upx"
Remove-Item Env:\COMPASSO_ONEFILE, Env:\COMPASSO_TRIM, Env:\COMPASSO_UPX
```

Tamanhos medidos (onefile, Windows, Python 3.14): baseline `none` ~450 MB · `subtract` ~252 MB ·
`minimal` ~191 MB · `minimal`+UPX ~179 MB. Saída em `dist/ComPasso.exe` (ou o `--distpath` que
você passar). **Nota:** o onefile do PyInstaller já comprime o arquivo, então o UPX rende pouco
(191→179 MB, ~6%) e ainda aumenta o risco de antivírus — geralmente **não compensa**. Para um
executável realmente menor, veja o build com Nuitka abaixo (~71 MB).

**Caveats do onefile** (por que o onedir é o alvo primário):

- O EXE se **auto-extrai num diretório TEMP** a cada execução → **startup mais lento** que o onedir.
- **Nunca grave dados dentro do bundle**: ele é descartado ao fechar. Os dados/logs do ComPasso já
  vão para pastas do usuário via `src/compasso/utils/paths.py`, independentes do bundle.
- Recursos (imagens, `lsl.dll`, `.qml`) são resolvidos de forma **agnóstica de empacotador** por
  `src/compasso/utils/resources.py` (PyInstaller via `sys._MEIPASS`; Nuitka via `__file__`) —
  ver o gotcha em `CLAUDE.md`. Não dependa de caminhos relativos ao `.exe`.
- **UPX** aumenta a chance de **falso-positivo de antivírus** e deixa o startup um pouco mais lento
  (descompressão); por isso o padrão é **sem UPX**. Use só se o tamanho for crítico.
- `--strip` no Windows é quase no-op (depende do `strip.exe` do binutils, ausente no Python de
  MSVC) e pode corromper DLLs Qt — deixe desligado no Windows.
- As saídas onedir/onefile coexistem em `dist/`; use `--distpath` distinto por variante.

## Build alternativo com Nuitka (executável bem menor)

O **Nuitka** compila o Python para C e gera um onefile **muito menor** que o PyInstaller
(medido: **~71 MB** contra ~252 MB do `subtract` / ~191 MB do `minimal`), com startup tipicamente
mais rápido. É o caminho oficial da Qt (`pyside6-deploy` usa Nuitka por baixo), mas exige mais
cuidado — por isso o PyInstaller segue como alvo primário e o Nuitka é a alternativa "enxuta".

O build é feito por **`scripts/build_nuitka.py`** (invoca o Nuitka direto, com todos os `--include-*`
que a análise estática não descobre sozinha). **Não** use o `pyside6-deploy`: ele renomeia
`main.py`→`deploy_main.py`, depois procura `main.exe` e falha ao finalizar (bug de naming), além de
varrer lixo (`.pytest_cache`) para o bundle.

```powershell
# 1. Ferramentas do Nuitka — instale NO VENV, fora do uv.lock (não são deps do projeto):
uv pip install nuitka ordered_set zstandard

# 2. Build (use o python do venv direto; `uv run` re-sincroniza e REMOVERIA o nuitka do venv):
.venv\Scripts\python.exe scripts\build_nuitka.py            # onefile (padrão)
.venv\Scripts\python.exe scripts\build_nuitka.py --standalone   # pasta (onedir)
```

Saída: **`dist/nuitka/ComPasso.exe`**. O Nuitka baixa o próprio compilador (zig) na 1ª execução —
não precisa de MSVC nem MinGW (aliás, em Python 3.13+ o Nuitka **não aceita** `--mingw64`).

**Gotchas do Nuitka já resolvidos no script** (não regredir):

- **`lsl.dll` do pylsl** — o Nuitka **não** copia DLLs via `--include-data-dir` nem
  `--include-package-data` (ambos pulam `.dll`); só `--include-data-files` (arquivo explícito)
  copia. Sem ela, o app aborta no import do pylsl. O script inclui `pylsl/lib/lsl.dll` file-a-file.
- **Plugins QML/multimídia** — o auto-detector do Nuitka inclui plugins por *import Python*; os
  `.qml` são **dado**, então `qml`/`qmltooling` e o backend `multimedia` (áudio/beep) precisam de
  `--include-qt-plugins=qml,qmltooling,multimedia` explícito.
- **Peso morto do Qt** — o category `qml` arrasta o QML inteiro (WebEngine ~195 MB, Quick3D,
  Charts, Pdf, estilos não-Basic...). O script corta tudo isso com `--noinclude-dlls=...`.
- **Assets e versão** — `--include-data-dir=assets=assets` (ícone/beep) e
  `--include-distribution-metadata=compasso` (para `get_app_version()` achar a versão no bundle).
- **Python 3.14 é "experimental"** no Nuitka 4.1.3 (ele avisa). Funciona (validado: abre, renderiza
  o QML, toca áudio), mas para um release de máxima estabilidade considere Python 3.12.

## macOS

1. Rode o build **em um Mac** (não é possível a partir do Windows).
2. Gere o ícone `.icns` a partir do PNG antes de buildar, por exemplo:

   ```bash
   mkdir icon.iconset
   sips -z 16 16   assets/icon.png --out icon.iconset/icon_16x16.png
   sips -z 32 32   assets/icon.png --out icon.iconset/icon_32x32.png
   sips -z 128 128 assets/icon.png --out icon.iconset/icon_128x128.png
   sips -z 256 256 assets/icon.png --out icon.iconset/icon_256x256.png
   sips -z 512 512 assets/icon.png --out icon.iconset/icon_512x512.png
   iconutil -c icns icon.iconset -o assets/icon.icns
   ```

3. `uv run pyinstaller compasso.spec`.

## Publicando um release no GitHub

1. Gere os builds `onedir` no Windows (`dist/ComPasso-win/`) e no macOS (`dist/ComPasso.app`).
2. Compacte cada saída (`ComPasso-win.zip`, `ComPasso-mac.zip`) — não suba o conteúdo solto.
3. Crie a tag e o release (`vX.Y.Z`) no GitHub e anexe os `.zip`. Veja a seção
   [Releases do README](README.md#-releases) para a convenção de nomes dos artefatos.

## Notas

- `dist/` e `build/` não são versionados (ver `.gitignore`). `compasso.spec` é versionado.
- Dependências de runtime ficam em `[project.dependencies]`; ferramentas de build
  (PyInstaller, pyflakes, pytest) ficam em `[dependency-groups].dev` — ambos em
  `pyproject.toml`, travados por versão exata em `uv.lock`.
- Se o app empacotado acusar erro de `liblsl`/`lsl`, confirme que a biblioteca nativa do
  `pylsl` foi copiada para `dist/ComPasso-win/_internal/` (o `compasso.spec` já faz isso via
  `collect_dynamic_libs("pylsl")`).
- **GUI em PySide6/QML** (desde a migração do CustomTkinter): `compasso.spec` parte de
  `collect_all("PySide6")` (traz libs Qt, plugins e os módulos QML necessários ao
  `QQmlApplicationEngine`) e, quando `COMPASSO_TRIM` está setado, **filtra** a saída para remover o
  peso morto (WebEngine etc.) — ver a função `_filtrar_pyside` e as listas `_TRIM_BLACKLIST`/
  `_TRIM_WHITELIST` no topo do spec. Os `.qml` são copiados via `datas` preservando a árvore do
  pacote (`compasso/gui_qt/qml/...`), pois a análise estática não os enxerga. Se o app empacotado
  abrir e fechar sem janela, **capture o stderr** (`Start-Process -RedirectStandardError`) para ver
  o traceback — foi assim que diagnosticamos os erros de empacotamento do Nuitka.
