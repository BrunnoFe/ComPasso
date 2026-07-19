# 🚀 Primeiros passos

## 📋 Requisitos

- **Sistema operacional:** Windows 10/11 ou macOS. Linux funciona como melhor esforço (a
  interface roda; o controle de volume via `amixer` pode exigir configuração adicional).
- **Python 3.12+** — só se for rodar a partir do código-fonte; o executável pronto não precisa.
- **OpenSignals (r)evolution** instalado, com o **Lab Streaming Layer (LSL) ativado**
  (veja [Conexão com o BITalino](bitalino-connection.md)) — dispensável se for só testar a
  interface com o [BITalino simulado](bitalino-simulado.md).
- **BITalino emparelhado** ao computador e transmitindo pelo OpenSignals com o LSL ativo.

## Executável pronto (recomendado para a maioria dos usuários)

Não é preciso instalar Python nem nada além do próprio ComPasso: baixe o build pronto (Windows
`.exe` / macOS `.app`) na [página de Releases do repositório](https://github.com/BrunnoFe/Compasso/releases)
e rode direto. Veja o passo a passo em [Primeiros passos do README](../README.md#-instalação).

Quer compilar o executável você mesmo (ou gerar a variante `onefile`)? Consulte o `BUILD.md` na
raiz do projeto.

## Rodando a partir do código-fonte (desenvolvimento)

Gerenciado com **[uv](https://docs.astral.sh/uv/)** — `pyproject.toml` + `uv.lock` são a única
fonte de verdade das dependências, sem `requirements.txt`.

```bash
uv sync            # cria .venv/, instala runtime + dev e o pacote `compasso` em modo editável
uv run main.py      # ponto de entrada (raiz)
```

### Dependências Python

As dependências de runtime estão em `pyproject.toml` (com `uv.lock` fixando as versões). As
principais:

- **PySide6** — interface gráfica (Qt Quick/QML), reprodução de áudio (QtMultimedia) e o
  desenho do gráfico do sinal (QPainter).
- **pylsl** — comunicação via Lab Streaming Layer.
- **pandas** + **openpyxl** — leitura da planilha de condições e geração do XLSX.
- **pycaw** / **comtypes** — controle de volume no Windows (marcados como `sys_platform ==
  "win32"` no `pyproject.toml`; em macOS/Linux o volume usa `osascript`/`amixer`, sem
  dependências extras).

A verificação de atualizações usa apenas `urllib`, da biblioteca padrão — sem dependência extra.

## Como executar

Ao iniciar, o ComPasso exibe uma **tela de carregamento** por alguns segundos. Em
seguida, a janela principal abre com um tamanho mínimo definido.

Na **primeira execução**, o programa cria automaticamente as pastas de dados e de logs (veja
[Dados de saída](output-data.md)). Se houver uma configuração usada anteriormente, ela é
**carregada automaticamente** (veja [Menus](experiment-menu.md)).

> Não tem um BITalino à mão para testar a interface? Veja
> [BITalino simulado](bitalino-simulado.md).

---

Próximo: [Conexão com o BITalino »](bitalino-connection.md)
