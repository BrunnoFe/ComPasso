# Executando um experimento

Esta página descreve o fluxo completo de uma sessão de coleta, do preparo ao encerramento.

## Interface, painel por painel

<!-- SCREENSHOT: janela principal completa com todos os painéis -->

- **Barra de conexão** — endereço MAC, canal (A1–A6), botão Conectar/Desconectar. Veja
  [Conexão com o BITalino](bitalino-connection.md).
- **Indicador de progresso (stepper)** — 4 etapas (**Conectar → Participante → Arquivos →
  Iniciar**) que acendem conforme o estado real: BITalino conectado, informações salvas, e
  arquivos mapeados + diretório de saída escolhido.
- **Painel do participante** — campos **Nome**, **Idade** e **Gênero** + "Salvar informações".
- **Painel de arquivos** — carregamento da pasta de músicas, da planilha de condições e do
  diretório de saída; cada linha ganha um check verde quando resolvida.
- **Player** — nome da faixa atual, chip de condição, indicador **● GRAVANDO**, barra de
  progresso, controle de volume e botão **Parar**.
- **Rodapé** — contadores **ESTÍMULOS** / **RUÍDO**, status e barra de progresso da sessão, e o
  botão principal (**Começar** / **Executando…** / **Continuar →**).

## Informações do participante

Preencha **Nome**, **Idade** e **Gênero** e clique em **Salvar informações**. Validações reais:

- **Nome** e **Gênero:** apenas letras e espaços.
- **Idade:** número inteiro entre **18 e 100**.
- Todos os campos são obrigatórios.

Após salvar, o cartão passa a mostrar um resumo (avatar com a inicial do nome + "idade anos ·
gênero") com um botão **Editar**.

> Se você clicar em **Começar** com o formulário preenchido mas ainda não salvo, o ComPasso tenta
> salvá-lo automaticamente antes de validar os pré-requisitos.

## Pré-requisitos para iniciar

O botão **Começar** fica sempre habilitado; a validação ocorre **no clique**. São verificados, em
ordem, **seis** pré-requisitos — se algum faltar, uma mensagem indica exatamente o quê:

1. **Configuração criada ou aberta** (menu Experimento) — *"Crie ou abra uma configuração de
   experimento (menu Experimento) antes de iniciar."*
2. **BITalino conectado.**
3. **Informações do participante salvas.**
4. **Arquivos de música carregados** (ao menos um arquivo compatível encontrado).
5. **Diretório de saída escolhido.**
6. **Nenhuma sessão já em andamento.**

## Como a playlist é montada

Ao iniciar, a sequência de faixas é construída assim:

1. **Expansão:** cada **música** entra na playlist **uma vez**. Os arquivos de **ruído** são
   distribuídos de forma equilibrada até totalizar `noise_quantity` reproduções (definido na
   configuração). Ex.: 2 arquivos de ruído com `noise_quantity = 5` → um aparece 3× e o outro 2×.
2. **Ordenação pseudoaleatória com regras:**
   - o **ruído nunca é a primeira faixa**;
   - há **pelo menos duas músicas entre dois ruídos** consecutivos.

   Se as restrições forem impossíveis (ruídos demais para poucas músicas), o ComPasso usa um
   melhor-esforço (garantindo apenas que o ruído não seja o primeiro) e registra um aviso no log.

## O ciclo de cada faixa

Para cada faixa da sequência:

1. **Início da aquisição** — o gravador LSL começa a capturar o sinal e captura o instante `t0`;
   é registrado o marcador **`INICIO_CONTAGEM`**. O botão principal vai para **Executando…**
   (desabilitado).
2. **Contagem regressiva de 10 segundos** — a gravação já está em curso durante a contagem.
3. **Reprodução** — ao iniciar o áudio, é registrado o marcador **`INICIO_MUSICA`** (com o nome
   do arquivo e o fator). O indicador **● GRAVANDO** e o chip de condição (música/ruído) ficam
   visíveis. A faixa toca até o fim.
4. **Fim da faixa** — é registrado o marcador **`FIM_MUSICA`**, o par CSV + XLSX é finalizado e os
   contadores são atualizados.
5. **Pausa entre faixas** — o botão muda para **Continuar →** e a sessão aguarda o pesquisador
   clicar para avançar à próxima faixa. Use este intervalo conforme o protocolo (instruções ao
   participante, anotações etc.).

<!-- SCREENSHOT: player com o indicador GRAVANDO e o chip de condição visíveis -->

Quando todas as faixas terminam, a sessão é finalizada automaticamente e o status indica
"Experimento finalizado."

## Interrompendo a sessão

O botão **Parar** (no player) encerra a sessão a qualquer momento: interrompe a reprodução,
registra o marcador **`PARADA_FORCADA`**, finaliza o arquivo da faixa em andamento e volta o botão
principal para **Começar**.

> A perda de conexão detectada pelo watchdog (15 s sem amostras) também interrompe a sessão da
> mesma forma. Veja [Conexão com o BITalino](bitalino-connection.md).

## Volume do sistema

Ao abrir o programa, o volume principal do sistema é ajustado automaticamente para **50%**. O
slider de volume no player controla o volume principal do SO (a aplicação é feita com um pequeno
atraso após o último ajuste, para não sobrecarregar o sistema).

---

Anterior: [« Arquivos de entrada](input-files.md) · Próximo: [Dados de saída »](output-data.md)
