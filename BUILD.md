# Build do ComPasso (executável)

Gera um executável otimizado do ComPasso com **PyInstaller** (build em pasta única,
`--onedir`). O `compasso.spec` é multiplataforma, mas **PyInstaller não faz
cross-compilação**: o `.exe` é gerado no Windows e o `.app` no macOS.

## Pré-requisitos

- Python 3.12+ (o projeto foi validado em 3.14).
- (Opcional) **UPX** no `PATH` para comprimir os binários. Sem UPX, o build funciona
  normalmente — a compressão é apenas ignorada.
- OpenSignals/`liblsl` **não** são necessários para *buildar*, apenas para usar o app.

## Preparar o ambiente

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt -r requirements-dev.txt
```

## Gerar o build

### onedir (padrão, recomendado para release)

```bash
pyinstaller compasso.spec
```

Saída:

- **Windows:** `dist/ComPasso-win/ComPasso.exe` (apoio em `dist/ComPasso-win/_internal/`).
- **macOS:** `dist/ComPasso-mac/` e o bundle `dist/ComPasso.app`.

Teste rápido no Windows: `dist\ComPasso-win\ComPasso.exe`

### onefile (variante de arquivo único)

Defina a variável `COMPASSO_ONEFILE` antes de buildar:

```bash
# Windows (PowerShell)
$env:COMPASSO_ONEFILE = "1"; pyinstaller compasso.spec; Remove-Item Env:\COMPASSO_ONEFILE
# Windows (cmd)
set COMPASSO_ONEFILE=1 && pyinstaller compasso.spec
# macOS/Linux
COMPASSO_ONEFILE=1 pyinstaller compasso.spec
```

Saída: **`dist/ComPasso.exe`** (Windows, ~47 MB) ou **`dist/ComPasso.app`** (macOS).

**Caveats do onefile** (por que o onedir é o alvo primário):

- O EXE se **auto-extrai num diretório TEMP** (`sys._MEIPASS`) a cada execução →
  **startup mais lento** que o onedir.
- **Nunca grave dados dentro do bundle**: ele é descartado ao fechar. Os dados/logs do
  ComPasso já vão para pastas do usuário (Documentos/ComPasso, app-data) via
  `src/compasso/utils/paths.py` — independentes do `_MEIPASS`, então funciona normalmente.
- Recursos lidos (imagens, `lsl.dll`) são resolvidos a partir de `sys._MEIPASS`
  (`src/compasso/gui/assets.py` já trata isso) — não dependa de caminhos relativos ao `.exe`.
- Maior chance de **falso-positivo de antivírus** e de o `lsl.dll` ser bloqueado.
- As saídas têm nomes distintos (`ComPasso-win/` vs `ComPasso.exe`), então coexistem em
  `dist/`. Atenção: `--clean` limpa o cache e o `build/`, mas **não remove a saída da outra
  variante** — apague `dist/` manualmente entre builds de release se quiser um diretório limpo.

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

3. `pyinstaller compasso.spec`.

## Publicando um release no GitHub

1. Gere os builds `onedir` no Windows (`dist/ComPasso-win/`) e no macOS (`dist/ComPasso.app`).
2. Compacte cada saída (`ComPasso-win.zip`, `ComPasso-mac.zip`) — não suba o conteúdo solto.
3. Crie a tag e o release (`vX.Y.Z`) no GitHub e anexe os `.zip`. Veja a seção
   [Releases do README](README.md#-releases) para a convenção de nomes dos artefatos.

## Notas

- `dist/` e `build/` não são versionados (ver `.gitignore`). `compasso.spec` é versionado.
- Dependências de runtime ficam em `requirements.txt`; ferramentas de build (PyInstaller,
  pyflakes) ficam em `requirements-dev.txt`.
- Se o app empacotado acusar erro de `liblsl`/`lsl`, confirme que a biblioteca nativa do
  `pylsl` foi copiada para `dist/ComPasso-win/_internal/` (o `compasso.spec` já faz isso via
  `collect_dynamic_libs("pylsl")`).
