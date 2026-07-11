<img width="1280" height="320" alt="banner-blend" src="https://github.com/user-attachments/assets/2fd0a973-1433-4083-bbc9-4fd72d5c2d22" />

<p align="center">
  <img alt="License" src="https://img.shields.io/github/license/BrunnoFe/Compasso?color=2DD4BF">
  <img alt="Python" src="https://img.shields.io/badge/python-3.12%2B-2DD4BF">
  <img alt="Platform" src="https://img.shields.io/badge/platform-Windows%20%7C%20macOS-2DD4BF">
  <img alt="GUI" src="https://img.shields.io/badge/GUI-CustomTkinter-2DD4BF">
  <a href="https://github.com/BrunnoFe/Compasso/releases"><img alt="Latest release" src="https://img.shields.io/github/v/release/BrunnoFe/Compasso?include_prereleases&color=2DD4BF&label=release"></a>
</p>

🎵🧠 **ComPasso** é uma plataforma de pesquisa em psicofisiologia que sincroniza a reprodução de músicas com a aquisição contínua do sinal do **BITalino** (via OpenSignals + Lab Streaming Layer). Amostras e marcadores de evento compartilham um único relógio (`pylsl.local_clock()`), garantindo sincronia precisa entre o estímulo auditivo e os dados fisiológicos com um **gráfico do sinal em tempo real** que acompanha cada faixa.

---

<img width="1273" height="825" alt="ui" src="https://github.com/user-attachments/assets/6b98ac8d-3784-4ef9-9614-1602e40b31a8" />

## Sumário

- [📋 Requisitos](#-requisitos)
- [📦 Instalação](#-instalação)
- [🔌 Antes de abrir o programa](#-antes-de-abrir-o-programa)
- [📁 Menu "Experimento", "Configurações" e "Tema"](#-menu-experimento-configurações-e-tema)
- [📂 Arquivos que você precisa preparar](#-arquivos-que-você-precisa-preparar)
- [🎬 Como executar](#-como-executar)
- [🧭 A interface, painel por painel](#-a-interface-painel-por-painel)
- [🧪 Executando um experimento](#-executando-um-experimento)
- [💾 Onde os dados são salvos](#-onde-os-dados-são-salvos)
- [📊 Formato dos arquivos de saída](#-formato-dos-arquivos-de-saída)
- [🔎 Logs e diagnóstico de erros](#-logs-e-diagnóstico-de-erros)
- [🚀 Releases](#-releases)
- [🔧 Solução de problemas](#-solução-de-problemas)

---

## 📋 Requisitos

- **Windows 10/11 ou macOS** (suporte a Linux como melhor esforço: a interface funciona, mas o controle de volume via `amixer` pode exigir configuração adicional dependendo da distribuição).
- **Python 3.12+**.
- **OpenSignals (r)evolution** instalado, com o **Lab Streaming Layer (LSL) ativado** (veja [Antes de abrir o programa](#-antes-de-abrir-o-programa)).
- **BITalino emparelhado** ao computador e transmitindo pelo OpenSignals (LSL ativo).

As dependências Python estão em [`requirements.txt`](requirements.txt) (CustomTkinter, pygame-ce, pylsl, pandas, openpyxl, pillow, entre outras). O controle de volume usa `pycaw` no Windows, `osascript` no macOS e `amixer` no Linux (sem dependências extras para macOS/Linux).

---

## 📦 Instalação

```bash
# 1. Crie e ative um ambiente virtual
python -m venv .venv
.venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

# 2. Instale as dependências
pip install -r requirements.txt

# 3. Instale o pacote `compasso` em modo editável (habilita `import compasso`, testes e dev)
pip install -e .
```

Para gerar um executável distribuível (`.exe` no Windows, `.app` no macOS), consulte [BUILD.md](BUILD.md), ou baixe um build pronto na seção [🚀 Releases](#-releases).

---

## 🔌 Antes de abrir o programa

A conexão com o BITalino **só funciona** se o OpenSignals estiver compartilhando os dados via Lab Streaming Layer. Faça isto **antes** de iniciar o ComPasso:

1. Abra o **OpenSignals (r)evolution**.
2. Entre em **Settings** (engrenagem) → aba **Integration** (ou *Advanced*).
3. Ative a opção **Lab Streaming Layer (LSL)**.
4. Coloque o dispositivo em modo de aquisição/streaming (botão de *play* do OpenSignals), de forma que o BITalino esteja transmitindo amostras.

> Sem o LSL ativo e transmitindo, a conexão do ComPasso falha com uma mensagem de erro (timeout de ~2 s ao procurar a stream).

<img width="1115" height="761" alt="opensignals" src="https://github.com/user-attachments/assets/e68e7110-96a6-492d-9be2-84ddcad987e3" />

---

## 📁 Menu "Experimento", "Configurações" e "Tema"

O menu **Experimento** (barra de menus da janela principal) centraliza toda a configuração do experimento em arquivos `.config` reutilizáveis. Cada `.config` é um arquivo JSON que armazena caminhos, quantidades esperadas e parâmetros do BITalino — basta abri-lo em sessões futuras para restaurar toda a configuração de uma vez.

<img width="704" height="530" alt="configs" src="https://github.com/user-attachments/assets/91b43053-6089-4816-bc6b-ea10a1ffca57" />

> **Carga automática ao iniciar:** o ComPasso carrega silenciosamente o último `.config` usado (se o arquivo ainda existir e for válido) e aplica todos os campos automaticamente. Em sessões recorrentes com o mesmo protocolo, basta abrir o programa e clicar em **Começar**.

### Novo

Abre a janela de configuração com campos vazios. Preencha todos os campos:

| Campo | Descrição |
| --- | --- |
| Pasta de músicas | Pasta contendo os arquivos de áudio do experimento (.mp3 / .wav / .ogg) |
| Quantidade de músicas | Número esperado de músicas (inteiro ≥ 1) |
| Quantidade de ruído | Número esperado de faixas de ruído (inteiro ≥ 0) |
| Arquivo de fatores | Planilha `.xlsx` / `.xls` com as condições de cada faixa |
| 🆕 Coluna do nome dos áudios / Coluna dos fatores | Dois menus suspensos que surgem ao carregar o arquivo de fatores, já com os nomes reais das colunas da planilha — não escolha a mesma coluna nos dois |
| Pasta de salvamento dos dados | Onde os arquivos da sessão serão gravados |
| Canal ativo do BITalino | Canal do sensor a gravar — **A1 a A6** |
| 🆕 Tipo de sensor | **EDA** / **ECG** (padrão) / **EMG** / **EOG** / **EEG** / **EGG** — define a unidade e a escala do gráfico |
| Endereço MAC do BITalino | Endereço do dispositivo no formato `XX:XX:XX:XX:XX:XX` |
| 🆕 Tempo pré-estímulo (s) | Slider de **5 a 120 segundos** — duração da contagem regressiva antes de cada faixa |
| 🆕 Beep de aviso | Checkbox + slider de **1 a 10 segundos** — toca um beep no t-X da contagem regressiva (desligado por padrão) |

Ao clicar em **Salvar**, escolha o nome e o local do arquivo `.config` (pasta padrão sugerida: `Documentos/ComPasso/Experiment files/`). A configuração é aplicada imediatamente a todos os campos da janela principal.

<!-- SCREENSHOT: janela "Configuração do Experimento" com os novos campos (colunas da planilha, sensor, sliders de pré-estímulo/beep) -->

> 🔔 **Colunas da planilha e beep de aviso:** escolher a mesma coluna nos dois menus de coluna, ou
> um tempo de beep maior/igual ao tempo pré-estímulo, deixa os controles com a borda vermelha e
> bloqueia o **Salvar** com uma mensagem explicando o problema.

### Abrir

Abre um seletor de arquivos para carregar um `.config` existente da pasta `Documentos/ComPasso/Experiment files/`. O arquivo é validado campo a campo antes de ser aplicado; erros específicos são exibidos ao usuário.

### Editar

Disponível somente após um **Novo** ou **Abrir** bem-sucedido. Reabre a janela de configuração pré-preenchida com os valores do `.config` atual. Ao salvar, solicita confirmação antes de sobrescrever o arquivo.

### 🚪 Sair

Encerra o aplicativo. Ao contrário de Novo/Abrir/Editar (que ficam **desabilitados** durante um
experimento em andamento, para não trocar a configuração no meio de uma sessão), **Sair fica
sempre habilitada**.

### ⚙️ Configurações → Gráfico

Abre a janela **Configurações do Gráfico**, para ajustar como o gráfico do sinal em tempo real é exibido — veja a seção [📈 Gráfico do sinal em tempo real](#-gráfico-do-sinal-em-tempo-real) para a lista completa de opções, faixas e padrões. As mudanças são salvas em `prefs.json` e recarregadas automaticamente na próxima abertura do programa.

> 🆕 A unidade e os limites do slider de **escala do eixo Y** dependem do **tipo de sensor**
> selecionado na barra de conexão (µV para EEG, mV para ECG/EMG/EOG/EGG, µS para EDA) — veja
> [🔬 Tipo de sensor](#-tipo-de-sensor) abaixo.

### 🎨 Temas

O menu **Tema** troca a paleta de cores da aplicação inteira ao vivo, sem reiniciar o programa. **Seis paletas** disponíveis — a escolha é lembrada entre execuções:

| Paleta | Estilo |
| --- | --- |
| 🌊 **Teal** (padrão) | Escura, acento verde-azulado |
| 🔮 **Iris** | Escura, acento violeta |
| 🟠 **Amber** | Escura, acento âmbar |
| ☀️ **Sereno** | Clara, acento azul-céu suave |
| 🌅 **Aurora** | Clara, acento coral-pêssego |
| 🌲 **Floresta** | Escura, acento verde-menta |

> ⚠️ A troca de tema só é permitida com a aplicação **ociosa** (sem BITalino conectado e sem experimento em andamento), pois reconstrói toda a interface.

<img width="1270" height="824" alt="iris" src="https://github.com/user-attachments/assets/746422aa-91c0-44e9-a4fe-48944c241222" />

<img width="1274" height="820" alt="ambar" src="https://github.com/user-attachments/assets/166bc524-956b-4759-8c71-0d1c041a55ae" />

<!-- SCREENSHOT: capturas das 3 paletas novas (Sereno/Aurora/Floresta), mesmo enquadramento das duas acima -->

---

## 📂 Arquivos que você precisa preparar

### 1. Pasta com as músicas

Uma pasta contendo os arquivos de áudio do experimento. Formatos aceitos:

- `.mp3`, `.wav`, `.ogg`

### 2. Planilha de condições (`.xlsx` / `.xls`)

Uma planilha Excel que associa cada arquivo de música à sua **condição/fator** experimental. Ela **precisa** conter exatamente estas duas colunas:

| Coluna | Descrição |
| --- | --- |
| `musica` | Nome do arquivo de áudio **com a extensão** (ex.: `faixa_01.mp3`) |
| `fator` | Condição daquela faixa (ex.: `intenso`, `orgânico`, `ruido`, ou outros rótulos) |

Exemplo:

<img width="497" height="122" alt="fatores" src="https://github.com/user-attachments/assets/980f1e33-5da6-4e78-a25a-7db569695c06" />

> **Importante:** o valor da coluna `música` deve bater exatamente com o nome do arquivo na pasta. Se uma música não tiver linha correspondente, o programa avisa e interrompe a verificação — corrija a planilha e recarregue. Os contadores **Música / Ruído** são calculados a partir da coluna `fator`: valores que contêm "ruido"/"ruído" contam como ruído; qualquer outro valor conta como música.
>
> 🆕 **Nomes de coluna configuráveis:** se sua planilha usar outros nomes (ex.: `arquivo`/`condicao`), não é preciso renomear nada — ao carregar o arquivo em **Experimento → Novo/Editar**, dois menus suspensos surgem automaticamente com os nomes reais das colunas, para você escolher qual é o nome do áudio e qual é o fator.

---

## 🎬 Como executar

```bash
python main.py
```

Uma **tela de carregamento** é exibida por alguns segundos antes da janela principal abrir (puramente decorativa — se falhar por qualquer motivo, o programa segue direto para a interface). A janela do ComPasso abre maximizada/centralizada (tamanho mínimo 1280×768). Na **primeira execução**, o programa cria automaticamente as pastas de dados e de logs (veja [Onde os dados são salvos](#-onde-os-dados-são-salvos)).

---

## 🧭 A interface, painel por painel

A interface foi redesenhada em cartões escuros com um indicador de progresso em etapas. A tela é dividida em:

### Barra de conexão — BITalino

<img width="1224" height="112" alt="conc" src="https://github.com/user-attachments/assets/20f4a719-5d1a-4b9d-b206-de9267ab4a46" />

<img width="1518" height="121" alt="conectado" src="https://github.com/user-attachments/assets/1acfe196-eaf0-4b87-9f77-c3e1498e3b7e" />

1. **Endereço MAC** — campo de texto para digitar o endereço MAC do BITalino no formato `XX:XX:XX:XX:XX:XX`. É por ele que o ComPasso localiza a *stream* LSL publicada pelo OpenSignals.
2. **Canal** — caixa de seleção ao lado do endereço MAC. Escolha o canal do sensor cujo sinal será gravado (**A1 a A6**). O padrão ao abrir o programa é **A1**.
3. **Sensor** 🆕 — caixa de seleção do tipo de sensor conectado ao canal (veja [🔬 Tipo de sensor](#-tipo-de-sensor) abaixo).
4. **Botão "Conectar"** — conecta ao BITalino via LSL. Em caso de sucesso, o botão dá lugar a um indicador "● Conectado" com um pequeno equalizador animado, e um botão **Desconectar** passa a ficar disponível; os campos de MAC, canal e sensor ficam travados.
5. **Botão "Desconectar"** — encerra manualmente a conexão com o BITalino e restaura a UI de conexão. Bloqueia (com aviso) se houver um experimento em andamento — pare o experimento antes de desconectar.

> **Watchdog de conexão:** após conectar, o ComPasso monitora continuamente o fluxo de amostras. Se nenhuma amostra for recebida por ~15 segundos, a conexão é encerrada automaticamente, o experimento em andamento é interrompido com marcador `stop`, e uma mensagem de aviso é exibida.

<!-- SCREENSHOT: barra de conexão no estado "Conectado", com o equalizador animado visível -->

### 🔬 Tipo de sensor

O BITalino aceita sensores diferentes, cada um com sua própria unidade e faixa de valores. Escolha o tipo **antes de conectar** (o menu fica travado depois) — isso ajusta a unidade e a escala padrão do [gráfico do sinal em tempo real](#-gráfico-do-sinal-em-tempo-real):

| Sensor | Unidade | Escala padrão | Faixa do slider (passo) |
| --- | --- | --- | --- |
| EDA | µS | ±6 µS | ±4 a ±30 µS (passo 2) |
| **ECG** (padrão) | mV | ±1 mV | ±0,4 a ±3 mV (passo 0,2) |
| EMG | mV | ±1 mV | ±0,4 a ±3 mV (passo 0,2) |
| EOG | mV | ±0,5 mV | ±0,1 a ±2 mV (passo 0,1) |
| EEG | µV | ±30 µV | ±10 a ±50 µV (passo 10) |
| EGG | mV | ±0,5 mV | ±0,1 a ±2 mV (passo 0,1) |

> 💡 A escolha do sensor **não converte** o sinal — o valor gravado no CSV/XLSX continua bruto, exatamente como antes. O sensor só muda o rótulo da unidade e a janela padrão de exibição do gráfico. Trocar de sensor **reseta a escala do eixo Y** para o padrão daquele sensor.

<!-- SCREENSHOT: combobox "Sensor" aberto na barra de conexão, mostrando as 6 opções -->

### Indicador de progresso (stepper)

Logo abaixo da barra de conexão, uma faixa com as etapas — **Configurações → Conectar →
Participante → Arquivos → Calibragem → Começar** — mostra visualmente o que já foi concluído e
qual é o próximo passo. A etapa **Calibragem** só aparece quando a calibração de volume está
habilitada na configuração do experimento; sem ela, "Começar" é a 5ª etapa. Cada etapa fica:

- **verde**, com um "✓", quando já foi concluída;
- **em destaque** ("AGORA"), quando é a próxima a ser feita;
- **vermelha**, quando ainda está pendente e não é a etapa atual.

<!-- SCREENSHOT: stepper com uma etapa concluída (verde), uma "AGORA" e outra(s) pendente(s) em vermelho -->

### Recolher os cartões Participante / Arquivos & Dados

Um botão **▴/▾** no canto superior direito do cartão "Arquivos & Dados" recolhe os dois cartões
juntos (Participante + Arquivos & Dados) numa animação de slide suave, deixando visível só o
título de cada um — útil para dar mais espaço ao player e ao gráfico do sinal depois que os
formulários já foram preenchidos. Ao clicar em **Começar**, os cartões recolhem automaticamente
(se ainda abertos) e o botão fica travado durante toda a sessão; ao finalizar o experimento
(sozinho, ao fim das faixas, ou pelo botão **Parar**) eles reabrem sozinhos e o botão volta a
funcionar.

<!-- SCREENSHOT/GIF: botão ▴/▾ recolhendo os dois cartões -->

### Painel do participante

<img width="488" height="307" alt="partic_info" src="https://github.com/user-attachments/assets/fbc951a0-6ea4-4e7e-bead-706f69baa17b" />

Preencha **Nome**, **Idade** e **Gênero** e clique em **Salvar informações**. Regras de validação:

- **Nome** e **Gênero**: apenas letras e espaços.
- **Idade**: número inteiro entre **18 e 100**.
- Todos os campos são obrigatórios.

Após salvar, o cartão muda para um resumo (avatar com a inicial do nome + "idade anos · gênero") com um botão **Editar**, caso precise corrigir algo. O botão **Editar** fica desabilitado durante um experimento em andamento (evita alterar as informações do participante no meio de uma sessão de coleta) e volta a funcionar assim que o experimento finaliza ou é interrompido.

<img width="489" height="309" alt="partic_card" src="https://github.com/user-attachments/assets/b4d4f495-fafa-4660-927a-58721aa30633" />

### Painel de arquivos e diretório de saída

<img width="732" height="307" alt="arquivos" src="https://github.com/user-attachments/assets/ba3d5178-c9e8-467c-9d08-4562ff2e9914" />

Três seleções, que também são preenchidas automaticamente ao carregar um `.config` pelo menu **Experimento**:

1. **Músicas → Carregar** — escolha a **pasta** com os áudios.
2. **Condições (.xlsx) → Buscar** — escolha a **planilha `.xlsx`** de condições. Ao concluir a seleção, o mapeamento entre arquivos e fatores é verificado automaticamente em segundo plano.
3. **Salvar dados em → Escolher** — escolha a **pasta de saída** dos dados.

Cada linha tem um ícone de check que fica verde assim que o respectivo item é resolvido com sucesso. A linha de status no rodapé indica o que ainda falta selecionar e, quando tudo está pronto, confirma que os arquivos foram encontrados e mapeados com sucesso.

### Player

<img width="1560" height="244" alt="gravando" src="https://github.com/user-attachments/assets/6fc273c7-6d83-43fc-b245-c87d181c2cc3" />

- **Nome da faixa atual** (com um chip indicando a condição/fator) e um indicador **● GRAVANDO** enquanto a aquisição de sinal está ativa. Durante a contagem regressiva antes de cada faixa (inclusive logo após clicar em **Continuar →**), o rótulo mostra "Preparando: {nome da música}" até a reprodução começar de fato.
- **Barra de progresso** com tempos de início/fim da faixa.
- **Volume** — slider que controla o volume principal do sistema; ao abrir o programa, o volume é ajustado automaticamente para 50%. 🔒 **Fica travado durante a contagem regressiva e a reprodução de cada faixa**, liberando entre uma faixa e a próxima.
- **Parar** — interrompe **a qualquer momento** o experimento e a reprodução, gravando o marcador `stop` e finalizando o arquivo da faixa atual. Pede confirmação ("Tem certeza que deseja parar o experimento?") antes de interromper, para evitar cliques acidentais em uma sessão em andamento.

> 🔔 **Beep de aviso (opcional):** se habilitado em **Experimento → Novo/Editar**, um beep toca durante a contagem regressiva, alguns segundos antes do início da faixa (1 a 10 s, configurável).

### 📈 Gráfico do sinal em tempo real

<!-- SCREENSHOT: cartão do gráfico durante uma gravação, mostrando a linha do sinal se formando, o ponteiro e o chip de tempo -->

Abaixo do player, um cartão desenha o sinal do BITalino do canal selecionado **ao vivo**, faixa por faixa:

- O gráfico se abre nos **últimos 5 segundos** da contagem regressiva (eixo de tempo começa em `-0:05`) e mostra a música inteira até o fim (`0:00` = início da faixa, destacado por uma linha mais clara).
- A linha se forma **continuamente e sem travar a interface**, com um ponteiro que acompanha a formação em tempo real e mostra o valor atual, na **unidade do sensor ativo** 🆕 (µV para EEG, mV para ECG/EMG/EOG/EGG, µS para EDA — veja [🔬 Tipo de sensor](#-tipo-de-sensor)), no canto superior.
- O eixo Y é **sempre fixo** na escala configurada (padrão do sensor ativo, ex.: **±30 µV** para EEG ou **±1 mV** para ECG), com marcas e linhas de grade no passo do sensor — não há ajuste automático pelos dados.
- Ao final de cada faixa, o registro completo permanece visível até ~1 segundo antes da próxima música começar, quando o gráfico se limpa para a faixa seguinte.
- Ao **parar** o experimento, o gráfico volta ao estado ocioso ("Aguardando gravação…").

> 💡 O gráfico é só uma conferência visual em tempo real — os dados salvos em CSV/XLSX sempre trazem o valor **bruto** do sinal, sem qualquer suavização aplicada à exibição.

#### ⚙️ Configurações do gráfico

O menu **Configurações → Gráfico** abre uma janela para ajustar como o gráfico é exibido, com **preview ao vivo** (as mudanças aparecem no gráfico na hora) e persistência entre execuções:

| Configuração | Faixa | Padrão |
| --- | --- | --- |
| Escala do eixo Y (µV, simétrica) | ±10 a ±50 (passo 10) | ±30 |
| Média móvel (suavização visual) | liga/desliga + janela de 1 a 15 colunas | ligada, janela 5 |
| Atualização (FPS) | 10 / 15 / 30 / 60 | 60 |
| Espessura da linha | 0.5 a 4.0 px | 1.5 |
| Linhas de grade | liga/desliga | ligadas |
| Rótulos dos eixos | liga/desliga | ligados |

> ⚠️ A **escala do eixo Y** não pode ser alterada enquanto um experimento está em andamento (fica travada durante a sessão, para não mudar a referência visual no meio de uma gravação); as demais configurações podem ser ajustadas a qualquer momento. Os botões **Salvar**, **Restaurar padrões** e **Cancelar** funcionam como nas demais janelas do app.

### Rodapé — Progresso e início do experimento

- Contadores **Música: X de Y** / **Ruído: X de Y**, atualizados a cada faixa concluída.
- Linha de **status** e uma barra de progresso da sessão (faixa N / total).
- **Botão principal**, que muda de texto/estado durante o experimento:
  - **Começar** — sempre visível; ao clicar, os pré-requisitos são verificados e uma mensagem de aviso indica o que falta;
  - **Executando…** — desabilitado enquanto a gravação e reprodução de uma faixa estão em andamento;
  - **Continuar →** — habilitado ao fim de cada faixa, para avançar à próxima.

---

## 🧪 Executando um experimento

### Pré-requisitos

Ao clicar em **Começar**, o ComPasso verifica se todos os seis pré-requisitos estão satisfeitos — caso contrário, uma mensagem indica o que falta:

1. **Configuração** de experimento criada ou aberta (menu Experimento);
2. BITalino **conectado**;
3. Informações do participante **salvas**;
4. **Pasta de músicas** carregada (ao menos um arquivo compatível encontrado);
5. **Diretório de saída** escolhido;
6. Nenhuma sessão já em andamento.

### Passo a passo

1. Configure o OpenSignals com o LSL ativo (veja [Antes de abrir o programa](#-antes-de-abrir-o-programa)).
2. Abra o ComPasso — o último `.config` é carregado automaticamente se existir.
3. Se necessário, use **Experimento → Novo** para criar uma configuração ou **Experimento → Abrir** para carregar uma existente.
4. Confirme o endereço MAC e o canal (**A1–A6**) na barra de conexão e clique em **Conectar**.
5. Preencha Nome, Idade e Gênero e clique em **Salvar informações**.
6. Verifique que a linha de status confirma o mapeamento bem-sucedido entre músicas e condições.
7. Clique em **Começar**. A ordem das faixas é **embaralhada** (aleatória, sem repetição).
8. Para cada faixa, o ciclo é:
   1. **Contagem regressiva de 10 segundos** — a gravação do sinal começa neste instante (marcador `countdown_start`). O botão vai para **Executando…** (desabilitado).
   2. **Reprodução da faixa** — ao iniciar o áudio, é gravado o marcador `music_start` (com o nome do arquivo e o fator). A faixa toca até o fim.
   3. **Fim da faixa** — grava o marcador `music_end`, finaliza o par CSV + XLSX e atualiza os contadores.
   4. O botão muda para **Continuar →**: a sessão aguarda o pesquisador clicar para ir à próxima faixa. Use este intervalo conforme o protocolo (instruções ao participante, anotações etc.). Ao clicar, uma linha é gravada em `dados_da_execucao.xlsx` 🆕 com o tempo de reação dessa pausa.
9. Quando todas as faixas terminam, a sessão é finalizada automaticamente.
10. O botão **Parar** (painel do player) encerra a sessão a qualquer momento, gravando um marcador `stop` e finalizando o arquivo da faixa em andamento.

---

## 💾 Onde os dados são salvos

| O quê | Local |
| --- | --- |
| **Dados do experimento** | `Documentos/ComPasso/data/` (ou a pasta escolhida em "Salvar dados em") |
| **Arquivos de configuração** | `Documentos/ComPasso/Experiment files/` |
| **Logs por categoria** | `%LOCALAPPDATA%\ComPasso\logs\<categoria>\` (Windows) / `~/Library/Application Support/ComPasso/logs/` (macOS) |
| **Arquivo central de erros** | `%LOCALAPPDATA%\ComPasso\errors.log` (Windows) / `~/Library/Application Support/ComPasso/errors.log` (macOS) |

As pastas são criadas automaticamente na primeira execução.

---

## 📊 Formato dos arquivos de saída

Cada coleta cria **uma pasta** nomeada `nome_idade_genero_dia-mes-ano_hora-min-seg` dentro do diretório de saída. Dentro dessa pasta, cada faixa gera **um par de arquivos** (CSV + XLSX) nomeados `ordem_nomedamusica`:

```text
Documentos/ComPasso/data/
└── joao_25_masculino_15-06-2025_10-30-00/
    ├── 01_faixa_01.csv
    ├── 01_faixa_01.xlsx
    ├── 02_branco_01.csv
    ├── 02_branco_01.xlsx
    └── dados_da_execucao.xlsx
```

- A **ordem** é a posição da faixa na playlist embaralhada (começa em 1, com zero à esquerda — largura mínima de 2 dígitos).
- A **extensão do áudio** é removida do nome do arquivo.
- O **CSV é gravado em tempo real** (com fsync periódico, resistindo a quedas inesperadas); o **XLSX é gerado ao final** de cada faixa a partir do mesmo conteúdo.
- 🆕 **`dados_da_execucao.xlsx`** — uma única planilha **por sessão** (não por faixa), regravada a cada faixa concluída, com as colunas `n`, `áudio`, `fator`, `volume` (volume do sistema quando a faixa tocou) e `intervalo` (segundos entre o fim da faixa e o clique em "Continuar →").

<!-- SCREENSHOT: Example data file -->

### Colunas (nesta ordem exata)

| Coluna | Descrição |
| --- | --- |
| `timestamp` | Segundos desde o início da contagem regressiva daquela faixa (`local_clock()` − t0, onde t0 = instante do `countdown_start`). |
| `signal` | Valor do sensor do BITalino no canal selecionado. |
| `markers` | Vazio na maioria das linhas; preenchido nos eventos: `countdown_start`, `music_start`, `music_end`, `stop`. |
| `music_file` | Preenchido **apenas** na linha `music_start` (nome do arquivo da faixa). |
| `fator` | Preenchido **apenas** na linha `music_start` (condição/fator da faixa). |

> Os marcadores são alinhados à amostra mais próxima do instante do evento (primeira amostra com timestamp LSL ≥ ao instante do marcador).

---

## 🔎 Logs e diagnóstico de erros

- Cada módulo grava em sua **própria subpasta** dentro de `logs/` (`connections/`, `gui/`, `main/`, `player/`, `recorder/`, `experiment/`, `musics/`), com um arquivo por execução identificado por data e hora.
- O **`errors.log`** (fora da pasta `logs/`) reúne **somente** avisos e erros (`WARNING`/`ERROR`/`CRITICAL`) de toda a aplicação — é o primeiro lugar para olhar quando algo der errado. O arquivo tem rotação automática de tamanho.

---

## 🚀 Releases

Builds prontos (Windows `.exe` / macOS `.app`, gerados com PyInstaller) são publicados na [página de Releases do repositório](https://github.com/BrunnoFe/Compasso/releases).

- Não há instalador: é um app "portátil" (onedir) — copie a pasta inteira para onde preferir.
- Versionamento segue tags `vAAAA.M.P` (ano.minor.patch); o histórico completo de mudanças de cada versão fica em [`CHANGELOG.md`](CHANGELOG.md), além da descrição de cada release no GitHub.
- Quer compilar você mesmo (ou gerar a variante `onefile`)? Veja o passo a passo em [BUILD.md](BUILD.md).

---

## 🔧 Solução de problemas

| Sintoma | Causa provável / solução |
| --- | --- |
| **Mensagem de aviso ao clicar em "Começar"** | Falta um dos seis pré-requisitos. Verifique a mensagem exibida e o que ainda está pendente. |
| **Erro ao conectar o BITalino** | O **Lab Streaming Layer** não está ativo no OpenSignals, ou o dispositivo não está transmitindo. Reative e tente novamente. |
| **Falha ao conectar / timeout** | OpenSignals sem LSL ativo ou sem transmitir, ou MAC incorreto. Ative o LSL, coloque o BITalino em aquisição e confira o endereço MAC. |
| **"Conexão com BITalino perdida" durante o experimento** | O watchdog detectou ≥ 15 s sem amostras. Verifique o sensor e o OpenSignals, e reconecte. |
| **"Nenhuma condição encontrada para X"** | O nome na coluna `musica` da planilha não bate com o arquivo na pasta. Corrija a planilha e recarregue. |
| **Sinal sempre 0 ou constante** | Canal errado selecionado. Consulte a primeira amostra registrada no log (linha "Primeira amostra completa") e ajuste o **Canal** na barra de conexão ou em **Experimento → Editar**. |
| **Áudio não toca** | Verifique se os arquivos estão em `.mp3`, `.wav` ou `.ogg` e se o volume do sistema não está no mínimo. |
| **Menu "Tema" não responde** | A troca de tema é bloqueada enquanto o BITalino está conectado ou um experimento está em andamento — desconecte/finalize antes de trocar. |
| **Gráfico fica "Aguardando gravação…" o tempo todo** | O BITalino não está conectado/transmitindo, ou nenhuma faixa está em reprodução no momento — o gráfico só recebe dados durante os 5 s finais da contagem e a reprodução da faixa. |
| 🆕 **"Salvar" recusa a configuração por causa das colunas** | As duas colunas escolhidas (nome do áudio / fator) são iguais, ou não existem na planilha carregada — recarregue o arquivo e escolha colunas diferentes. |
| 🆕 **"Salvar" recusa por causa do beep** | O tempo do beep está igual ou maior que o tempo pré-estímulo. Diminua o tempo do beep ou aumente o tempo pré-estímulo. |
| 🆕 **Menu "Experimento" com Novo/Abrir/Editar apagados** | Um experimento está em andamento — esses itens ficam desabilitados até a sessão terminar ou ser interrompida. Use **Sair** se precisar fechar o app mesmo assim. |
| **Onde estão os arquivos de erro?** | `%LOCALAPPDATA%\ComPasso\errors.log` (Windows) / `~/Library/Application Support/ComPasso/errors.log` (macOS). |

<!--
IMAGENS PENDENTES (nota para manutenção, não exibida no README renderizado):
A interface passou por um redesign completo (cartões, indicador de etapas, temas, menu de
barra reconstruído) desde as últimas capturas de tela. Vale renovar/adicionar:
- Captura geral da janela principal com a barra de menu ("Experimento" + "Tema" lado a lado).
- Menu "Tema" aberto, mostrando as 6 paletas (Teal/Iris/Amber/Sereno/Aurora/Floresta) — idealmente
  1 captura (ou 3, para as novas Sereno/Aurora/Floresta) por paleta.
- Barra de conexão no estado "Conectado" (equalizador animado) — GIF curto comunica melhor.
- Indicador de progresso (stepper) em pelo menos dois estados (início e com etapas concluídas).
- Painel do player com o indicador "GRAVANDO" e o chip de condição durante uma faixa em execução.
- Cartão do gráfico do sinal em tempo real, durante uma gravação real (linha se formando + ponteiro
  + chip de tempo visíveis) — um GIF curto comunica bem a fluidez da animação.
- Ícone/logo do app em alta resolução para o topo do README.
- GIF do botão "▴/▾" recolhendo/expandindo os cartões Participante + Arquivos & Dados (animação de
  slide de ~100 ms), incluindo o momento em que o experimento inicia (cartões recolhem e o botão
  trava sozinho) e finaliza/para (reabrem e o botão destrava).

Adicionados nesta sessão (funcionalidades novas, ainda sem captura):
- Janela "Configuração do Experimento" com os menus de coluna da planilha de fatores, o combobox
  de tipo de sensor e os sliders de tempo pré-estímulo/beep de aviso.
- Combobox "Sensor" aberto na barra de conexão, mostrando as 6 opções (EDA/ECG/EMG/EOG/EEG/EGG).
- Menu "Experimento" com Novo/Abrir/Editar desabilitados durante um experimento e a opção "Sair".
- `dados_da_execucao.xlsx` aberto, mostrando as colunas n/áudio/fator/volume/intervalo.
-->