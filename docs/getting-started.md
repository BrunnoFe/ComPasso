# 🚀 Primeiros passos

## 📋 Requisitos

- **Sistema operacional:** Windows 10/11 ou macOS. Linux funciona como melhor esforço (a
  interface roda; o controle de volume via `amixer` pode exigir configuração adicional).
- **Python 3.12+**.
- **OpenSignals (r)evolution** instalado, com o **Lab Streaming Layer (LSL) ativado**
  (veja [Conexão com o BITalino](bitalino-connection.md)).
- **BITalino emparelhado** ao computador e transmitindo pelo OpenSignals com o LSL ativo.

## Executável pronto (sem Python)

Também é possível baixar um build pronto (Windows `.exe` / macOS `.app` [Em breve]) na
[página de Releases do repositório](https://github.com/BrunnoFe/Compasso/releases).

Para gerar o executável você mesmo, consulte o `BUILD.md` na raiz do projeto.

### Dependências Python

As dependências de runtime estão em `requirements.txt`. As principais:

- **CustomTkinter** (+ CTkMessagebox, CTkMenuBar) — interface gráfica e menus.
- **pygame-ce** — reprodução de áudio.
- **pylsl** — comunicação via Lab Streaming Layer.
- **pandas** + **openpyxl** — leitura da planilha de condições e geração do XLSX.
- **pillow** — imagens da interface.
- **pywinstyles** — cor da borda/barra de título da janela no Windows.
- **pycaw** / **comtypes** — controle de volume no Windows (marcados como `win32` no
  `requirements.txt`; em macOS/Linux o volume usa `osascript`/`amixer`, sem dependências extras).

## Instalação

```bash
# 1. Crie e ative um ambiente virtual
python -m venv .venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

# 2. Instale as dependências
pip install -r requirements.txt
```

## Como executar

```bash
python main.py
```

Ao iniciar, o ComPasso exibe uma **tela de carregamento** por alguns segundos. Em
seguida, a janela principal abre com um tamanho mínimo definido.

Na **primeira execução**, o programa cria automaticamente as pastas de dados e de logs (veja
[Dados de saída](output-data.md)). Se houver uma configuração usada anteriormente, ela é
**carregada automaticamente** (veja [Menus](experiment-menu.md)).

---

Próximo: [Conexão com o BITalino »](bitalino-connection.md)
