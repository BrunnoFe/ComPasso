<img width="1280" height="320" alt="banner-blend" src="https://github.com/user-attachments/assets/2fd0a973-1433-4083-bbc9-4fd72d5c2d22" />

<p align="center">
  <img alt="License" src="https://img.shields.io/github/license/BrunnoFe/Compasso?color=2DD4BF">
  <img alt="Platform" src="https://img.shields.io/badge/platform-Windows%20%7C%20macOS-2DD4BF">
  <img alt="GUI" src="https://img.shields.io/badge/GUI-PySide6%2FQML-2DD4BF">
  <a href="https://github.com/BrunnoFe/Compasso/releases"><img alt="Latest release" src="https://img.shields.io/github/v/release/BrunnoFe/Compasso?include_prereleases&color=2DD4BF&label=release"></a>
  <a href="https://github.com/BrunnoFe/Compasso/releases"><img alt="Downloads" src="https://img.shields.io/github/downloads/BrunnoFe/Compasso/total?color=2DD4BF"></a>
  <a href="https://github.com/BrunnoFe/Compasso/commits/main"><img alt="Last commit" src="https://img.shields.io/github/last-commit/BrunnoFe/Compasso?color=2DD4BF"></a>
</p>

<p align="center"><b>🎵🧠 Toque música. Grave sinal fisiológico. Confie no tempo.</b></p>

**ComPasso** é uma plataforma de pesquisa em psicofisiologia que sincroniza a reprodução de
músicas com a aquisição contínua do sinal do **BITalino** (via OpenSignals + Lab Streaming
Layer). Áudio, marcadores de evento e amostras do sinal compartilham **um único relógio**, então
o que aparece no gráfico e o que fica gravado no CSV correspondem exatamente ao que o participante
ouviu, no mesmo instante.

---

<img width="1273" height="825" alt="Janela principal do ComPasso" src="https://github.com/user-attachments/assets/6b98ac8d-3784-4ef9-9614-1602e40b31a8" />

## Sumário

- [✨ Principais funcionalidades](#-principais-funcionalidades)
- [📋 Requisitos](#-requisitos)
- [📦 Instalação](#-instalação)
- [🔌 Antes de abrir o programa](#-antes-de-abrir-o-programa)
- [🧪 Como funciona uma sessão](#-como-funciona-uma-sessão)
- [💾 Onde os dados ficam](#-onde-os-dados-ficam)
- [📚 Documentação completa](#-documentação-completa)
- [🔧 Algo deu errado?](#-algo-deu-errado)

---

## ✨ Principais funcionalidades

- 🎧 **Sessão sincronizada por um único relógio** — áudio, marcadores (início/fim de faixa, beep,
  interrupção) e amostras do sinal usam o mesmo relógio (`pylsl.local_clock()`), sem deriva
  cumulativa ao longo da sessão.
- 📈 **Gráfico do sinal em tempo real**, com zoom ao vivo do eixo Y (funciona durante a própria
  gravação) e leitura do valor atual na unidade do sensor conectado.
- 🔬 **Seis tipos de sensor** (EDA, ECG, EMG, EOG, EEG, EGG) — cada um com sua própria unidade e
  escala padrão de exibição.
- 🗂️ **Configurações de experimento reutilizáveis** (`.config`), com carga automática da última
  usada e planilha de condições com colunas de nome livre.
- 🔊 **Calibração de volume opcional**, para achar o nível confortável de cada participante antes
  de começar.
- 🎨 **Seis temas** (3 escuros, 3 claros), trocados ao vivo, a qualquer momento — mesmo com o
  BITalino conectado ou uma sessão em andamento.
- 🧪 **BITalino simulado** — dá para testar a interface inteira (conexão, gráfico, gravação) sem
  hardware nenhum. Detalhes em [docs/bitalino-simulado.md](docs/bitalino-simulado.md).
- ⚙️ **Preferências do app configuráveis** (arranque, aparência, arquivos, conexão, diagnóstico),
  separadas do protocolo do experimento e registradas por sessão em `ambiente.json`. Detalhes em
  [docs/app-settings.md](docs/app-settings.md).

---

## 📋 Requisitos

- **Windows 10/11 ou macOS** (Linux funciona como melhor esforço).
- **OpenSignals (r)evolution**, com o **Lab Streaming Layer (LSL) ativado**.
- **BITalino** emparelhado e transmitindo pelo OpenSignals — ou use o
  [BITalino simulado](docs/bitalino-simulado.md) para só testar a interface.

---

## 📦 Instalação

A forma mais simples é baixar o executável pronto — não precisa instalar Python nem nenhuma
dependência:

1. Acesse a [página de Releases](https://github.com/BrunnoFe/Compasso/releases) e baixe o build
   mais recente para o seu sistema (`.exe` para Windows, `.app` para macOS).
2. Extraia a pasta em qualquer lugar — é um app "portátil" (onedir), sem instalador.
3. Rode `ComPasso.exe` (Windows) ou abra `ComPasso.app` (macOS).

Prefere rodar a partir do código-fonte, ou compilar você mesmo? Veja
[docs/getting-started.md](docs/getting-started.md) (fluxo com [`uv`](https://docs.astral.sh/uv/))
e [BUILD.md](BUILD.md). O executável pode ser gerado com **PyInstaller** (padrão) ou, para um
binário bem menor (~71 MB), com **Nuitka** (`scripts/build_nuitka.py`) — detalhes no BUILD.md.

---

## 🔌 Antes de abrir o programa

A conexão com o BITalino só funciona com o **Lab Streaming Layer** ativo no OpenSignals:

1. Abra o **OpenSignals (r)evolution**.
2. Em **Settings → Integration**, ative **Lab Streaming Layer (LSL)**.
3. Coloque o dispositivo para transmitir (botão de *play*).

<img width="1115" height="761" alt="Configurações do OpenSignals com LSL ativado" src="https://github.com/user-attachments/assets/e68e7110-96a6-492d-9be2-84ddcad987e3" />

Passo a passo completo, incluindo o que fazer se a conexão falhar, em
[docs/bitalino-connection.md](docs/bitalino-connection.md).

---

## 🧪 Como funciona uma sessão

1. Conecte o BITalino, salve as informações do participante e carregue a pasta de músicas + a
   planilha de condições (ou abra um `.config` já pronto).
2. Clique em **Começar** — a ordem das faixas é embaralhada, sem repetição.
3. Cada faixa passa por uma contagem regressiva, toca até o fim e é gravada em um par de arquivos
   CSV + XLSX, com o gráfico do sinal acompanhando ao vivo.
4. Entre uma faixa e outra, você decide quando avançar — o tempo dessa pausa também fica
   registrado.

Passo a passo completo, com todas as regras de validação e o fluxo do gráfico do sinal, em
[docs/running-an-experiment.md](docs/running-an-experiment.md).

---

## 💾 Onde os dados ficam

| O quê | Local |
| --- | --- |
| Dados do experimento | `Documentos/ComPasso/Dados/` (ou a pasta escolhida na sessão) |
| Configurações (`.config`) | `Documentos/ComPasso/Configurações do Experimento/` |
| Logs e erros | pasta de dados do app (Windows: `%LOCALAPPDATA%\ComPasso`; macOS: `~/Library/Application Support/ComPasso`) |

Formato exato dos arquivos e das colunas em [docs/output-data.md](docs/output-data.md).

---

## 📚 Documentação completa

Este README cobre o essencial para começar. Para o detalhe de cada tela, cada validação e cada
arquivo gerado, veja o [índice da documentação em `/docs`](docs/index.md) — inclui conexão com o
BITalino, menus, arquivo `.config`, arquivos de entrada, execução de um experimento (com
calibração de volume), dados de saída e solução de problemas.

---

## 🔧 Algo deu errado?

Os erros mais comuns (conexão, planilha de condições, áudio, tema) e como resolvê-los estão em
[docs/troubleshooting.md](docs/troubleshooting.md). O primeiro lugar para olhar quando algo falha
é o arquivo central de erros (`errors.log`), acessível pelo menu **Ajuda → Abrir pasta de logs**.

---

<p align="center">Versionamento em tags <code>vAAAA.M.P</code> — changelog completo em <a href="CHANGELOG.md">CHANGELOG.md</a>.</p>

<!--
IMAGENS PENDENTES (nota para manutenção, não exibida no README renderizado):
As duas screenshots reaproveitadas acima (janela principal, OpenSignals) ainda batem com a
interface atual, mas a barra de menus ganhou itens novos desde a última captura. Vale
adicionar/atualizar:
- Barra de menus completa, mostrando Experimento/Configurações/Tema/Atualizações/Ajuda + o botão
  sol/lua no canto direito (nenhuma imagem atual mostra o menu Atualizações nem o botão).
- Diálogo de confirmação "Conectar (teste)" do BITalino simulado (3 opções), para a seção
  "✨ Principais funcionalidades" ou para docs/bitalino-simulado.md.
- Janela "Configurações do App" com as 6 abas (Geral/Aparência/Arquivos/Conexão/
  Diagnóstico/Avançado) — útil em docs/app-settings.md.
-->
