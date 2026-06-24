# Compasso

**Compasso** é uma interface gráfica de pesquisa que sincroniza a reprodução de músicas
com a aquisição de sinais eletrofisiológicos do **BITalino** (via OpenSignals + Lab
Streaming Layer). Durante a sessão, o software toca uma sequência aleatória de faixas e
grava continuamente o sinal do sensor em disco, com marcadores de evento e amostras
compartilhando **o mesmo relógio**, garantindo sincronia precisa entre o áudio e os dados.

---

## Sumário

- [Requisitos](#requisitos)
- [Instalação](#instalação)
- [Antes de abrir o programa](#antes-de-abrir-o-programa)
- [Arquivos que você precisa preparar](#arquivos-que-você-precisa-preparar)
- [Como executar](#como-executar)
- [A interface, painel por painel](#a-interface-painel-por-painel)
- [Executando um experimento](#executando-um-experimento)
- [Onde os dados são salvos](#onde-os-dados-são-salvos)
- [Formato dos arquivos de saída](#formato-dos-arquivos-de-saída)
- [Logs e diagnóstico de erros](#logs-e-diagnóstico-de-erros)
- [Solução de problemas](#solução-de-problemas)

---

## Requisitos

- **Windows 10/11** (o controle de volume e a conexão Bluetooth são otimizados para Windows).
- **Python 3.12+**.
- **BITalino** emparelhado via Bluetooth.
- **OpenSignals (r)evolution** instalado, com o **Lab Streaming Layer (LSL) ativado**
  (veja [Antes de abrir o programa](#antes-de-abrir-o-programa)).
- **Bluetooth ligado** no computador.

As dependências Python estão em [`requirements.txt`](requirements.txt) (CustomTkinter,
pygame-ce, pylsl, bleak, pandas, openpyxl, pillow, entre outras).

---

## Instalação

```bash
# 1. Crie e ative um ambiente virtual
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac

# 2. Instale as dependências
pip install -r requirements.txt
```

---

## Antes de abrir o programa

A conexão com o BITalino **só funciona** se o OpenSignals estiver compartilhando os dados
via Lab Streaming Layer. Faça isto **antes** de iniciar o Compasso:

1. Abra o **OpenSignals (r)evolution**.
2. Entre em **Settings** (engrenagem) → aba **Integration** (ou *Advanced*).
3. Ative a opção **Lab Streaming Layer (LSL)**.
4. Coloque o dispositivo em modo de aquisição/streaming (botão de *play* do OpenSignals),
   de forma que o BITalino esteja transmitindo amostras.
5. Garanta que o **Bluetooth do computador esteja ligado**.

> Sem o LSL ativo, o Compasso até localiza o dispositivo no escaneamento, mas a conexão
> falha com uma mensagem de erro.

---

## Arquivos que você precisa preparar

### 1. Pasta com as músicas

Uma pasta contendo os arquivos de áudio do experimento. Formatos aceitos:

- `.mp3`, `.wav`, `.ogg`

### 2. Planilha de condições (`.xlsx` / `.xls`)

Uma planilha Excel que associa cada arquivo de música à sua **condição/fator**
experimental. Ela **precisa** conter exatamente estas duas colunas:

| Coluna   | Descrição                                                                 |
|----------|---------------------------------------------------------------------------|
| `musica` | Nome do arquivo de áudio **com a extensão** (ex.: `faixa_01.mp3`).        |
| `fator`  | Condição daquela faixa (ex.: `musica`, `pausa`, `ruido`, ou seus rótulos).|

Exemplo:

| musica          | fator   |
|-----------------|---------|
| faixa_01.mp3    | musica  |
| silencio_01.wav | pausa   |
| branco_01.wav   | ruido   |

> **Importante:**
> - O valor da coluna `musica` deve **bater exatamente** com o nome do arquivo na pasta.
>   Se uma música não tiver linha correspondente, o programa avisa e interrompe a
>   verificação — corrija a planilha e recarregue.
> - Os contadores **Música / Pausa / Ruído** da tela são preenchidos a partir da coluna
>   `fator`: valores que contêm "pausa" contam como pausa, "ruido"/"ruído" como ruído, e
>   qualquer outro valor como música.

---

## Como executar

```bash
python main.py
```

A janela do Compasso abre maximizada/centralizada. Na **primeira execução**, o programa
cria automaticamente as pastas de dados e de logs (veja
[Onde os dados são salvos](#onde-os-dados-são-salvos)).

---

## A interface, painel por painel

A tela é dividida em quatro regiões:

### 🔵 Painel superior — Conexão com o BITalino

1. **Escanear** — procura dispositivos Bluetooth próximos (~3 s). Ao final, a lista de
   endereços aparece no campo de seleção.
2. **Selecione o endereço MAC** — escolha o seu BITalino na caixa de seleção. O endereço
   tem o formato `XX:XX:XX:XX:XX:XX`.
3. **Canal** — caixa ao lado do botão *Escanear*. Selecione o **número do canal** do
   sensor cujo sinal será gravado (na coluna `signal`). As opções vão de **1 a 6**
   (correspondendo aos canais do BITalino); se nada for escolhido, o canal padrão é usado.
4. **Botão de conexão (imagem à direita)** — conecta ao dispositivo selecionado. Em caso
   de sucesso, a imagem muda para "conectado" e os controles de conexão são travados; em
   caso de falha, aparece uma mensagem explicando o motivo (geralmente LSL desativado).

> **Dica sobre o canal:** ao iniciar a gravação, o programa registra no log a primeira
> amostra completa do BITalino. Use esse registro para confirmar qual posição da lista
> carrega o sinal do seu sensor (os canais de sequência costumam ser constantes/incrementais).

### 🟣 Painel central esquerdo — Dados do participante

Preencha **Nome**, **Idade** e **Gênero** e clique em **Salvar informações**. Regras de
validação:

- **Nome** e **Gênero**: apenas letras e espaços.
- **Idade**: número inteiro entre **0 e 100**.
- Todos os campos são obrigatórios.

Após salvar, os campos ficam travados e surge o botão **Editar informações**, caso precise
corrigir algo.

### 🟣 Painel central direito — Arquivos e diretório de saída

Três seleções, nesta ordem:

1. **Arquivos de músicas → Carregar** — escolha a **pasta** com os áudios.
2. **Condições → Buscar** — escolha a **planilha `.xlsx`** de condições.
3. **Salvar dados em → Escolher** — escolha a **pasta de saída** dos dados
   (sugestão padrão: `Documentos/Compasso/data`).

A linha de status (texto grande no rodapé deste painel, também repetido no painel inferior)
vai te guiando: ela indica o que ainda falta selecionar e, quando tudo está pronto, confirma
que as músicas foram encontradas e mapeadas às condições com sucesso.

### 🟣 Painel central inferior — Player

- **Nome da faixa atual**, **Volume** (controla o volume principal do sistema) e a **barra
  de progresso** com tempos.
- **Parar** — interrompe **a qualquer momento** o experimento e a reprodução, finalizando o
  arquivo da faixa atual com um marcador `stop`.

### 🟣 Painel inferior — Progresso e início do experimento

- Contadores **Música / Pausa / Ruído** (`X de Y`), atualizados a cada faixa concluída.
- Linha de **status** da sessão.
- **Botão principal** (imagem à direita), que muda de estado durante o experimento:
  - **começar** — só fica **habilitado** quando os cinco pré-requisitos abaixo estão prontos;
  - **rodando** — desabilitado, enquanto uma faixa está em contagem/reprodução/gravação;
  - **continuar** — habilitado, ao fim de cada faixa, para avançar à próxima.

#### Os cinco pré-requisitos para "começar"

O botão **começar** só habilita quando **todos** estão satisfeitos:

1. BITalino **conectado**;
2. Informações do participante **salvas**;
3. **Pasta de músicas** carregada;
4. **Planilha de condições** carregada e mapeada;
5. **Diretório de saída** escolhido.

---

## Executando um experimento

1. Conclua os cinco pré-requisitos. O botão **começar** habilita.
2. Clique em **começar**. A ordem das faixas é **embaralhada** (sem repetições).
3. Para cada faixa, o ciclo é:
   1. **Contagem regressiva de 10 segundos** — a gravação do sinal **já começa neste
      instante** (marcador `countdown_start`). O botão fica em **rodando** (desabilitado).
   2. **Reprodução da faixa** — ao iniciar o áudio, é gravado o marcador `music_start`
      (com o nome do arquivo e o fator). A faixa toca até o fim.
   3. **Fim da faixa** — grava o marcador `music_end`, finaliza o arquivo de dados (CSV +
      XLSX) e atualiza os contadores.
   4. O botão muda para **continuar**: a sessão **aguarda você** clicar para ir à próxima
      faixa. Use esse intervalo conforme o protocolo (instruções ao participante, etc.).
4. Quando todas as faixas terminam, a sessão é finalizada automaticamente.
5. O botão **Parar** encerra a sessão a qualquer momento de forma segura, gravando um
   marcador `stop` e finalizando o arquivo da faixa em andamento.

> Cada faixa gera **um par de arquivos** (CSV + XLSX). A coluna de tempo é contada a partir
> do início da contagem regressiva daquela faixa.

---

## Onde os dados são salvos

| O quê                  | Local                                                                 |
|------------------------|-----------------------------------------------------------------------|
| **Dados do experimento** | `Documentos/Compasso/data/` (ou a pasta que você escolher em "Salvar dados em") |
| **Logs por categoria**   | `%LOCALAPPDATA%\Compasso\logs\<categoria>\` (Windows)               |
| **Arquivo central de erros** | `%LOCALAPPDATA%\Compasso\errors.log`                            |

As pastas são criadas automaticamente na primeira execução. Em macOS/Linux, os logs ficam
no diretório de dados do sistema (`~/Library/Application Support/Compasso` ou
`~/.local/share/Compasso`).

---

## Formato dos arquivos de saída

Cada faixa gera dois arquivos com o mesmo conteúdo, nomeados assim:

```text
nome_idade_genero_dia-mes-ano_hora-min-seg.csv
nome_idade_genero_dia-mes-ano_hora-min-seg.xlsx
```

O **CSV é gravado em tempo real** (resiste a quedas inesperadas) e o **XLSX é gerado ao
final** da faixa, a partir do mesmo conteúdo.

### Colunas (nesta ordem exata)

| Coluna       | Descrição                                                                                  |
|--------------|--------------------------------------------------------------------------------------------|
| `timestamp`  | Segundos desde o início da contagem regressiva (relógio LSL — mesmo das amostras).         |
| `signal`     | Valor do sensor do BITalino no canal selecionado.                                          |
| `markers`    | Vazio, exceto nas linhas dos eventos: `countdown_start`, `music_start`, `music_end`, `stop`. |
| `music_file` | Preenchido **apenas** na linha `music_start` (nome do arquivo da faixa).                    |
| `fator`      | Preenchido **apenas** na linha `music_start` (condição daquela faixa).                      |

> Os marcadores são alinhados à amostra mais próxima do instante do evento. A primeira
> amostra gravada fica a, no máximo, um intervalo de amostragem do `countdown_start`,
> garantindo que a captura começa junto com a contagem.

---

## Logs e diagnóstico de erros

- Cada módulo grava em sua **própria subpasta** dentro de `logs/`
  (`connections/`, `gui/`, `main/`, `player/`, `recorder/`, `experiment/`, `musics/`),
  com um arquivo por execução, identificado por data e hora.
- O **`errors.log`** (fora da pasta `logs/`) reúne **somente** avisos e erros
  (`WARNING`/`ERROR`/`CRITICAL`) de toda a aplicação — é o primeiro lugar para olhar quando
  algo der errado. O arquivo tem rotação automática de tamanho.

---

## Solução de problemas

| Sintoma | Causa provável / solução |
|---|---|
| **"começar" não habilita** | Falta um dos cinco pré-requisitos. Verifique conexão, dados do participante, pasta de músicas, planilha de condições e diretório de saída. |
| **Erro ao conectar o BITalino** | O **Lab Streaming Layer** não está ativo no OpenSignals, ou o dispositivo não está transmitindo. Reative e tente novamente. |
| **Nenhum dispositivo no escaneamento** | Bluetooth desligado ou BITalino fora de alcance/desligado. Ligue o Bluetooth e reescaneie. |
| **"Nenhuma condição encontrada para X"** | O nome na coluna `musica` da planilha não bate com o arquivo na pasta. Corrija a planilha e recarregue. |
| **Sinal sempre 0 ou constante** | Canal errado selecionado. Veja a primeira amostra registrada no log e ajuste o número do **Canal**. |
| **Áudio não toca** | Verifique se os arquivos estão em `.mp3`, `.wav` ou `.ogg` e se o volume do sistema não está no mínimo. |
| **Onde estão os arquivos com erros?** | `%LOCALAPPDATA%\Compasso\errors.log`. |
