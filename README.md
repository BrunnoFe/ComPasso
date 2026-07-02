<img width="1280" height="320" alt="banner-blend" src="https://github.com/user-attachments/assets/2fd0a973-1433-4083-bbc9-4fd72d5c2d22" />![<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="320" viewBox="0 0 1280 320" font-family="Segoe UI, -apple-system, system-ui, sans-serif">
  <defs><linearGradient id="bg" x1="460.0" y1="0" x2="820.0" y2="0" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#2DD4BF"></stop><stop offset="1" stop-color="#7C74FF"></stop></linearGradient></defs>
  <rect width="1280" height="320" fill="#0E1116"></rect>
  <text x="640" y="150" text-anchor="middle" font-size="92" font-weight="700" letter-spacing="-1" fill="#E6EDF3">ComPasso</text>
  <path d="M460.0 210.0 L463.8 207.1 L467.5 204.5 L471.3 202.1 L475.0 200.0 L478.8 198.1 L482.5 196.5 L486.3 195.1 L490.0 194.0 L493.8 193.1 L497.5 192.5 L501.3 192.1 L505.0 192.0 L508.8 192.1 L512.5 192.5 L516.3 193.1 L520.0 194.0 L523.8 195.1 L527.5 196.5 L531.3 198.1 L535.0 200.0 L538.8 202.1 L542.5 204.5 L546.3 207.1 L550.0 210.0 L550.0 210.0 L553.8 212.9 L557.5 215.5 L561.3 217.9 L565.0 220.0 L568.8 221.9 L572.5 223.5 L576.3 224.9 L580.0 226.0 L583.8 226.9 L587.5 227.5 L591.3 227.9 L595.0 228.0 L598.8 227.9 L602.5 227.5 L606.3 226.9 L610.0 226.0 L613.8 224.9 L617.5 223.5 L621.3 221.9 L625.0 220.0 L628.8 217.9 L632.5 215.5 L636.3 212.9 L640.0 210.0 L645.0 202.0 L650.0 194.0 L655.0 186.0 L660.0 178.0 L665.0 170.0 L670.0 162.0 L675.0 176.4 L680.0 190.8 L685.0 205.2 L690.0 219.6 L695.0 234.0 L700.0 248.4 L705.0 236.4 L710.0 224.4 L715.0 212.4 L720.0 200.4 L725.0 188.4 L730.0 176.4 L735.0 185.2 L740.0 194.0 L745.0 202.8 L750.0 211.6 L755.0 220.4 L760.0 229.2 L765.0 224.4 L770.0 219.6 L775.0 214.8 L780.0 210.0 L785.0 205.2 L790.0 200.4 L795.0 202.0 L800.0 203.6 L805.0 205.2 L810.0 206.8 L815.0 208.4 L820.0 210.0" fill="none" stroke="url(#bg)" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"></path>
  <text x="640" y="292" text-anchor="middle" font-size="20" font-weight="600" letter-spacing="7" fill="#6E7681">MÚSICA &amp; FISIOLOGIA</text>
</svg>Uploading banner-blend.svg…]()

<p>
  <img alt="License" src="https://img.shields.io/github/license/BrunnoFe/Compasso?color=2DD4BF">
  <img alt="Python" src="https://img.shields.io/badge/python-3.12%2B-2DD4BF">
  <img alt="Platform" src="https://img.shields.io/badge/platform-Windows%20%7C%20macOS-2DD4BF">
  <img alt="GUI" src="https://img.shields.io/badge/GUI-CustomTkinter-2DD4BF">
  <a href="https://github.com/BrunnoFe/Compasso/releases"><img alt="Latest release" src="https://img.shields.io/github/v/release/BrunnoFe/Compasso?include_prereleases&color=2DD4BF&label=release"></a>
</p>

**ComPasso** é uma plataforma de pesquisa em psicofisiologia que sincroniza a reprodução de músicas com a aquisição contínua do sinal do **BITalino** (via OpenSignals + Lab Streaming Layer). Amostras e marcadores de evento compartilham um único relógio (`pylsl.local_clock()`), garantindo sincronia precisa entre o estímulo auditivo e os dados fisiológicos.

---

<img width="1263" height="814" alt="ui" src="https://github.com/user-attachments/assets/105450bb-c452-425d-bdfa-80cee88764b9" />


## Sumário

- [Requisitos](#requisitos)
- [Instalação](#instalação)
- [Antes de abrir o programa](#antes-de-abrir-o-programa)
- [Menu "Experimento" e "Tema"](#menu-experimento-e-tema)
- [Arquivos que você precisa preparar](#arquivos-que-você-precisa-preparar)
- [Como executar](#como-executar)
- [A interface, painel por painel](#a-interface-painel-por-painel)
- [Executando um experimento](#executando-um-experimento)
- [Onde os dados são salvos](#onde-os-dados-são-salvos)
- [Formato dos arquivos de saída](#formato-dos-arquivos-de-saída)
- [Logs e diagnóstico de erros](#logs-e-diagnóstico-de-erros)
- [🚀 Releases](#-releases)
- [Solução de problemas](#solução-de-problemas)

---

## Requisitos

- **Windows 10/11 ou macOS** (suporte a Linux como melhor esforço: a interface funciona, mas o controle de volume via `amixer` pode exigir configuração adicional dependendo da distribuição).
- **Python 3.12+**.
- **OpenSignals (r)evolution** instalado, com o **Lab Streaming Layer (LSL) ativado** (veja [Antes de abrir o programa](#antes-de-abrir-o-programa)).
- **BITalino emparelhado** ao computador e transmitindo pelo OpenSignals (LSL ativo).

As dependências Python estão em [`requirements.txt`](requirements.txt) (CustomTkinter, pygame-ce, pylsl, pandas, openpyxl, pillow, entre outras). O controle de volume usa `pycaw` no Windows, `osascript` no macOS e `amixer` no Linux (sem dependências extras para macOS/Linux).

---

## Instalação

```bash
# 1. Crie e ative um ambiente virtual
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

# 2. Instale as dependências
pip install -r requirements.txt
```

Para gerar um executável distribuível (`.exe` no Windows, `.app` no macOS), consulte [BUILD.md](BUILD.md), ou baixe um build pronto na seção [🚀 Releases](#-releases).

---

## Antes de abrir o programa

A conexão com o BITalino **só funciona** se o OpenSignals estiver compartilhando os dados via Lab Streaming Layer. Faça isto **antes** de iniciar o ComPasso:

1. Abra o **OpenSignals (r)evolution**.
2. Entre em **Settings** (engrenagem) → aba **Integration** (ou *Advanced*).
3. Ative a opção **Lab Streaming Layer (LSL)**.
4. Coloque o dispositivo em modo de aquisição/streaming (botão de *play* do OpenSignals), de forma que o BITalino esteja transmitindo amostras.

> Sem o LSL ativo e transmitindo, a conexão do ComPasso falha com uma mensagem de erro (timeout de ~2 s ao procurar a stream).


<img width="1115" height="761" alt="opensignals" src="https://github.com/user-attachments/assets/e68e7110-96a6-492d-9be2-84ddcad987e3" />


---

## Menu "Experimento" e "Tema"

O menu **Experimento** (barra de menus da janela principal) centraliza toda a configuração do experimento em arquivos `.config` reutilizáveis. Cada `.config` é um arquivo JSON que armazena caminhos, quantidades esperadas e parâmetros do BITalino — basta abri-lo em sessões futuras para restaurar toda a configuração de uma vez.


<img width="700" height="499" alt="configs" src="https://github.com/user-attachments/assets/dd4003c8-acf3-42ee-8c6b-71b3e9aee3f2" />


> **Carga automática ao iniciar:** o ComPasso carrega silenciosamente o último `.config` usado (se o arquivo ainda existir e for válido) e aplica todos os campos automaticamente. Em sessões recorrentes com o mesmo protocolo, basta abrir o programa e clicar em **Começar**.

### Novo

Abre a janela de configuração com campos vazios. Preencha todos os campos:

| Campo | Descrição |
| --- | --- |
| Pasta de músicas | Pasta contendo os arquivos de áudio do experimento (.mp3 / .wav / .ogg) |
| Quantidade de músicas | Número esperado de músicas (inteiro ≥ 1) |
| Quantidade de ruído | Número esperado de faixas de ruído (inteiro ≥ 0) |
| Arquivo de fatores | Planilha `.xlsx` / `.xls` com as condições de cada faixa |
| Pasta de salvamento dos dados | Onde os arquivos da sessão serão gravados |
| Canal ativo do BITalino | Canal do sensor a gravar — **A1 a A6** |
| Endereço MAC do BITalino | Endereço do dispositivo no formato `XX:XX:XX:XX:XX:XX` |

Ao clicar em **Salvar**, escolha o nome e o local do arquivo `.config` (pasta padrão sugerida: `Documentos/ComPasso/Experiment files/`). A configuração é aplicada imediatamente a todos os campos da janela principal.

### Abrir

Abre um seletor de arquivos para carregar um `.config` existente da pasta `Documentos/ComPasso/Experiment files/`. O arquivo é validado campo a campo antes de ser aplicado; erros específicos são exibidos ao usuário.

### Editar

Disponível somente após um **Novo** ou **Abrir** bem-sucedido. Reabre a janela de configuração pré-preenchida com os valores do `.config` atual. Ao salvar, solicita confirmação antes de sobrescrever o arquivo.

### 🎨 Tema

Novidade da interface redesenhada: o menu **Tema** troca a paleta de cores da aplicação inteira ao vivo, sem reiniciar o programa. Três opções disponíveis — **Teal** (padrão), **Iris** e **Amber** — a escolha é lembrada entre execuções.

> A troca de tema só é permitida com a aplicação **ociosa** (sem BITalino conectado e sem experimento em andamento), pois reconstrói toda a interface.

<!-- SCREENSHOT: menu "Tema" aberto, mostrando as 3 opções de paleta (Teal/Iris/Amber) -->

---

## Arquivos que você precisa preparar

### 1. Pasta com as músicas

Uma pasta contendo os arquivos de áudio do experimento. Formatos aceitos:

- `.mp3`, `.wav`, `.ogg`

### 2. Planilha de condições (`.xlsx` / `.xls`)

Uma planilha Excel que associa cada arquivo de música à sua **condição/fator** experimental. Ela **precisa** conter exatamente estas duas colunas:

| Coluna | Descrição |
| --- | --- |
| `musica` | Nome do arquivo de áudio **com a extensão** (ex.: `faixa_01.mp3`) |
| `fator` | Condição daquela faixa (ex.: `musica`, `ruido`, ou outros rótulos) |

Exemplo:

| musica | fator |
| --- | --- |
| faixa_01.mp3 | intenso |
| branco_01.wav | ruido |


<img width="497" height="122" alt="fatores" src="https://github.com/user-attachments/assets/980f1e33-5da6-4e78-a25a-7db569695c06" />


> **Importante:** o valor da coluna `musica` deve bater exatamente com o nome do arquivo na pasta. Se uma música não tiver linha correspondente, o programa avisa e interrompe a verificação — corrija a planilha e recarregue. Os contadores **Música / Ruído** são calculados a partir da coluna `fator`: valores que contêm "ruido"/"ruído" contam como ruído; qualquer outro valor conta como música.

---

## Como executar

```bash
python main.py
```

A janela do ComPasso abre maximizada/centralizada (tamanho mínimo 1280×768). Na **primeira execução**, o programa cria automaticamente as pastas de dados e de logs (veja [Onde os dados são salvos](#onde-os-dados-são-salvos)).

---

## A interface, painel por painel

A interface foi redesenhada em cartões escuros com um indicador de progresso em etapas. A tela é dividida em:

### Barra de conexão — BITalino


<img width="1219" height="109" alt="bit_conect" src="https://github.com/user-attachments/assets/dceb5366-353b-4206-8f35-cbf82716692a" />


<img width="1233" height="110" alt="contedado" src="https://github.com/user-attachments/assets/b75c39f7-55de-4f9a-9aef-b6357ac3ec1a" />


1. **Endereço MAC** — campo de texto para digitar o endereço MAC do BITalino no formato `XX:XX:XX:XX:XX:XX`. É por ele que o ComPasso localiza a *stream* LSL publicada pelo OpenSignals.
2. **Canal** — caixa de seleção ao lado do endereço MAC. Escolha o canal do sensor cujo sinal será gravado (**A1 a A6**). O padrão ao abrir o programa é **A1**.
3. **Botão "Conectar"** — conecta ao BITalino via LSL. Em caso de sucesso, o botão dá lugar a um indicador "● Conectado" com um pequeno equalizador animado, e um botão **Desconectar** passa a ficar disponível; o campo de MAC e o canal ficam travados.
4. **Botão "Desconectar"** — encerra manualmente a conexão com o BITalino e restaura a UI de conexão. Bloqueia (com aviso) se houver um experimento em andamento — pare o experimento antes de desconectar.

> **Watchdog de conexão:** após conectar, o ComPasso monitora continuamente o fluxo de amostras. Se nenhuma amostra for recebida por ~15 segundos, a conexão é encerrada automaticamente, o experimento em andamento é interrompido com marcador `stop`, e uma mensagem de aviso é exibida.

<!-- SCREENSHOT: barra de conexão no estado "Conectado", com o equalizador animado visível -->

### Indicador de progresso (stepper)

Logo abaixo da barra de conexão, uma faixa com 4 etapas — **Conectar → Participante → Arquivos → Iniciar** — mostra visualmente o que já foi concluído e qual é o próximo passo, atualizando em tempo real conforme o BITalino conecta, as informações do participante são salvas e os arquivos são mapeados.

<!-- SCREENSHOT: stepper de 4 etapas, com pelo menos uma etapa concluída e outra "AGORA" -->

### Painel do participante

<img width="486" height="360" alt="participantes" src="https://github.com/user-attachments/assets/6aac6a2a-c4b6-4d3b-84ac-706c84e1d0dc" />

Preencha **Nome**, **Idade** e **Gênero** e clique em **Salvar informações**. Regras de validação:

- **Nome** e **Gênero**: apenas letras e espaços.
- **Idade**: número inteiro entre 0 e 100.
- Todos os campos são obrigatórios.

Após salvar, o cartão muda para um resumo (avatar com a inicial do nome + "idade anos · gênero") com um botão **Editar**, caso precise corrigir algo.

### Painel de arquivos e diretório de saída

<img width="728" height="359" alt="arquivos" src="https://github.com/user-attachments/assets/24246385-d591-4ae7-863e-4ad7902a9725" />

Três seleções, que também são preenchidas automaticamente ao carregar um `.config` pelo menu **Experimento**:

1. **Músicas → Carregar** — escolha a **pasta** com os áudios.
2. **Condições (.xlsx) → Buscar** — escolha a **planilha `.xlsx`** de condições. Ao concluir a seleção, o mapeamento entre arquivos e fatores é verificado automaticamente em segundo plano.
3. **Salvar dados em → Escolher** — escolha a **pasta de saída** dos dados.

Cada linha tem um ícone de check que fica verde assim que o respectivo item é resolvido com sucesso. A linha de status no rodapé indica o que ainda falta selecionar e, quando tudo está pronto, confirma que os arquivos foram encontrados e mapeados com sucesso.

### Player

<img width="1259" height="299" alt="comecar" src="https://github.com/user-attachments/assets/6d69ac3e-5a44-4301-98b6-ed887bf81586" />

- **Nome da faixa atual** (com um chip indicando a condição/fator) e um indicador **● GRAVANDO** enquanto a aquisição de sinal está ativa.
- **Barra de progresso** com tempos de início/fim da faixa.
- **Volume** — slider que controla o volume principal do sistema; ao abrir o programa, o volume é ajustado automaticamente para 50%.
- **Parar** — interrompe **a qualquer momento** o experimento e a reprodução, gravando o marcador `stop` e finalizando o arquivo da faixa atual.

### Espaço para o gráfico em tempo real

Abaixo do player há um painel reservado para um futuro gráfico do sinal do BITalino em tempo real — ainda não implementado, hoje é apenas uma legenda "EM BREVE".

### Rodapé — Progresso e início do experimento

- Contadores **Música: X de Y** / **Ruído: X de Y**, atualizados a cada faixa concluída.
- Linha de **status** e uma barra de progresso da sessão (faixa N / total).
- **Botão principal**, que muda de texto/estado durante o experimento:
  - **Começar** — sempre visível; ao clicar, os pré-requisitos são verificados e uma mensagem de aviso indica o que falta;
  - **Executando…** — desabilitado enquanto a gravação e reprodução de uma faixa estão em andamento;
  - **Continuar →** — habilitado ao fim de cada faixa, para avançar à próxima.

---

## Executando um experimento

### Pré-requisitos

Ao clicar em **Começar**, o ComPasso verifica se todos os cinco pré-requisitos estão satisfeitos — caso contrário, uma mensagem indica o que falta:

1. BITalino **conectado**;
2. Informações do participante **salvas**;
3. **Pasta de músicas** carregada (ao menos um arquivo compatível encontrado);
4. **Planilha de condições** carregada e mapeamento concluído;
5. **Diretório de saída** escolhido.

### Passo a passo

1. Configure o OpenSignals com o LSL ativo (veja [Antes de abrir o programa](#antes-de-abrir-o-programa)).
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
   4. O botão muda para **Continuar →**: a sessão aguarda o pesquisador clicar para ir à próxima faixa. Use este intervalo conforme o protocolo (instruções ao participante, anotações etc.).
9. Quando todas as faixas terminam, a sessão é finalizada automaticamente.
10. O botão **Parar** (painel do player) encerra a sessão a qualquer momento, gravando um marcador `stop` e finalizando o arquivo da faixa em andamento.

---

## Onde os dados são salvos

| O quê | Local |
| --- | --- |
| **Dados do experimento** | `Documentos/ComPasso/data/` (ou a pasta escolhida em "Salvar dados em") |
| **Arquivos de configuração** | `Documentos/ComPasso/Experiment files/` |
| **Logs por categoria** | `%LOCALAPPDATA%\ComPasso\logs\<categoria>\` (Windows) / `~/Library/Application Support/ComPasso/logs/` (macOS) |
| **Arquivo central de erros** | `%LOCALAPPDATA%\ComPasso\errors.log` (Windows) / `~/Library/Application Support/ComPasso/errors.log` (macOS) |

As pastas são criadas automaticamente na primeira execução.

---

## Formato dos arquivos de saída

Cada coleta cria **uma pasta** nomeada `nome_idade_genero_dia-mes-ano_hora-min-seg` dentro do diretório de saída. Dentro dessa pasta, cada faixa gera **um par de arquivos** (CSV + XLSX) nomeados `ordem_nomedamusica`:

```text
Documentos/ComPasso/data/
└── joao_25_masculino_15-06-2025_10-30-00/
    ├── 01_faixa_01.csv
    ├── 01_faixa_01.xlsx
    ├── 02_branco_01.csv
    └── 02_branco_01.xlsx
```

- A **ordem** é a posição da faixa na playlist embaralhada (começa em 1, com zero à esquerda — largura mínima de 2 dígitos).
- A **extensão do áudio** é removida do nome do arquivo.
- O **CSV é gravado em tempo real** (com fsync periódico, resistindo a quedas inesperadas); o **XLSX é gerado ao final** de cada faixa a partir do mesmo conteúdo.

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

## Logs e diagnóstico de erros

- Cada módulo grava em sua **própria subpasta** dentro de `logs/` (`connections/`, `gui/`, `main/`, `player/`, `recorder/`, `experiment/`, `musics/`), com um arquivo por execução identificado por data e hora.
- O **`errors.log`** (fora da pasta `logs/`) reúne **somente** avisos e erros (`WARNING`/`ERROR`/`CRITICAL`) de toda a aplicação — é o primeiro lugar para olhar quando algo der errado. O arquivo tem rotação automática de tamanho.

---

## 🚀 Releases

Builds prontos (Windows `.exe` / macOS `.app`, gerados com PyInstaller) são publicados na [página de Releases do repositório](https://github.com/BrunnoFe/Compasso/releases).

| Plataforma | Artefato | Como usar |
| --- | --- | --- |
| Windows | `ComPasso-win.zip` (onedir) | Extraia e execute `ComPasso.exe` — mantenha a pasta `_internal` junto. |
| macOS | `ComPasso-mac.zip` (`ComPasso.app`) | Extraia e abra `ComPasso.app`. |

- Não há instalador: é um app "portátil" (onedir) — copie a pasta inteira para onde preferir.
- Versionamento segue tags `vX.Y.Z`; o changelog de cada versão fica na descrição do release no GitHub.
- Quer compilar você mesmo (ou gerar a variante `onefile`)? Veja o passo a passo em [BUILD.md](BUILD.md).
- Ainda não há releases publicados? Acompanhe o [changelog de commits](https://github.com/BrunnoFe/Compasso/commits/main) ou abra uma build local a partir do código-fonte.

---

## Solução de problemas

| Sintoma | Causa provável / solução |
| --- | --- |
| **Mensagem de aviso ao clicar em "Começar"** | Falta um dos cinco pré-requisitos. Verifique a mensagem exibida e o que ainda está pendente. |
| **Erro ao conectar o BITalino** | O **Lab Streaming Layer** não está ativo no OpenSignals, ou o dispositivo não está transmitindo. Reative e tente novamente. |
| **Falha ao conectar / timeout** | OpenSignals sem LSL ativo ou sem transmitir, ou MAC incorreto. Ative o LSL, coloque o BITalino em aquisição e confira o endereço MAC. |
| **"Conexão com BITalino perdida" durante o experimento** | O watchdog detectou ≥ 15 s sem amostras. Verifique o sensor e o OpenSignals, e reconecte. |
| **"Nenhuma condição encontrada para X"** | O nome na coluna `musica` da planilha não bate com o arquivo na pasta. Corrija a planilha e recarregue. |
| **Sinal sempre 0 ou constante** | Canal errado selecionado. Consulte a primeira amostra registrada no log (linha "Primeira amostra completa") e ajuste o **Canal** na barra de conexão ou em **Experimento → Editar**. |
| **Áudio não toca** | Verifique se os arquivos estão em `.mp3`, `.wav` ou `.ogg` e se o volume do sistema não está no mínimo. |
| **Menu "Tema" não responde** | A troca de tema é bloqueada enquanto o BITalino está conectado ou um experimento está em andamento — desconecte/finalize antes de trocar. |
| **Onde estão os arquivos de erro?** | `%LOCALAPPDATA%\ComPasso\errors.log` (Windows) / `~/Library/Application Support/ComPasso/errors.log` (macOS). |

---

## 📸 Imagens sugeridas para atualizar

A interface passou por um redesign completo (cartões, indicador de etapas, temas, menu de barra reconstruído) desde as últimas capturas de tela. Vale renovar/adicionar:

- Captura geral da janela principal já com a barra de menu corrigida ("Experimento" + "Tema" lado a lado).
- Menu **Tema** aberto, mostrando as 3 paletas (Teal/Iris/Amber) — idealmente 3 capturas, uma por paleta.
- Barra de conexão no estado **Conectado** (equalizador animado) — um GIF curto comunica melhor que uma imagem estática.
- Indicador de progresso (stepper) em pelo menos dois estados (início e com etapas concluídas).
- Painel do player com o indicador **● GRAVANDO** e o chip de condição visíveis durante uma faixa em execução.
- Ícone/logo do app em alta resolução para o topo do README (hoje o cabeçalho usa uma captura de tela cheia).
