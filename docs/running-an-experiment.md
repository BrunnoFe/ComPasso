# 🧪 Executando um experimento

Esta página descreve o fluxo completo de uma sessão de coleta, do preparo ao encerramento.

## 🧭 Interface, painel por painel

<!-- SCREENSHOT: janela principal completa com todos os painéis, incluindo o gráfico do sinal em tempo real -->

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
- **📈 Gráfico do sinal em tempo real** — desenha o sinal do canal selecionado ao vivo durante a
  gravação, com um ponteiro fluido e leitura do valor atual (µV); veja a seção
  [Gráfico do sinal em tempo real](#-gráfico-do-sinal-em-tempo-real) abaixo.
- **Rodapé** — contadores **ESTÍMULOS** / **RUÍDO**, status e barra de progresso da sessão, e o
  botão principal (**Começar** / **Executando…** / **Continuar →**).
- **Recolher os painéis Participante/Arquivos** — um botão **▴/▾** no canto superior direito do
  painel "Arquivos & Dados" recolhe/expande os dois painéis juntos (animação de slide), liberando
  espaço para o player e o gráfico depois que os formulários já foram preenchidos.

## Informações do participante

Preencha **Nome**, **Idade** e **Gênero** e clique em **Salvar informações**. Validações reais:

- **Nome** e **Gênero:** apenas letras e espaços.
- **Idade:** número inteiro entre **18 e 100**.
- Todos os campos são obrigatórios.

Após salvar, o cartão passa a mostrar um resumo (avatar com a inicial do nome + "idade anos ·
gênero") com um botão **Editar**.

> Se você clicar em **Começar** com o formulário preenchido mas ainda não salvo, o ComPasso tenta
> salvá-lo automaticamente antes de validar os pré-requisitos.
>
> ⚠️ Durante um experimento em andamento, o botão **Editar** fica desabilitado (evita alterar as
> informações do participante no meio de uma sessão de coleta) e os painéis Participante/Arquivos
> recolhem automaticamente, com o botão **▴/▾** travado até a sessão terminar ou ser interrompida.

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
2. **Contagem regressiva de 10 segundos** — a gravação já está em curso durante a contagem, e o
   rótulo do player mostra **"Preparando: {nome da música}"** (inclusive logo após clicar em
   **Continuar →**, antes da faixa seguinte começar de fato). Nos **5 segundos finais**, o
   gráfico do sinal já se abre e começa a mostrar o que está sendo captado (veja
   [📈 Gráfico do sinal em tempo real](#-gráfico-do-sinal-em-tempo-real) abaixo).
3. **Reprodução** — ao iniciar o áudio, é registrado o marcador **`INICIO_MUSICA`** (com o nome
   do arquivo e o fator). O indicador **● GRAVANDO** e o chip de condição (música/ruído) ficam
   visíveis. A faixa toca até o fim.
4. **Fim da faixa** — é registrado o marcador **`FIM_MUSICA`**, o par CSV + XLSX é finalizado e os
   contadores são atualizados. O gráfico permanece com o registro completo da faixa visível.
5. **Pausa entre faixas** — o botão muda para **Continuar →** e a sessão aguarda o pesquisador
   clicar para avançar à próxima faixa. Use este intervalo conforme o protocolo (instruções ao
   participante, anotações etc.). Ao clicar em **Continuar →**, o ComPasso grava uma linha em
   `dados_da_execucao.xlsx` com o tempo de reação daquela pausa — veja
   [🕒 Planilha de execução](#-planilha-de-execução) abaixo.

> 🔔 **Beep de aviso (opcional):** se habilitado em **Experimento → Novo/Editar**, um beep toca
> durante a contagem regressiva, alguns segundos antes do início da faixa (configurável de 1 a 10
> segundos) — um sinal sonoro para avisar o participante que o áudio está prestes a começar.

<!-- SCREENSHOT: player com o indicador GRAVANDO e o chip de condição visíveis -->

Quando todas as faixas terminam, a sessão é finalizada automaticamente e o status indica
"Experimento finalizado."

## 🕒 Planilha de execução

Além do CSV/XLSX por faixa, o ComPasso mantém **uma planilha por sessão** chamada
`dados_da_execucao.xlsx`, na mesma pasta da sessão. Ela é regravada a cada faixa concluída, com
uma linha por faixa:

| Coluna | Descrição |
| --- | --- |
| `n` | Ordem da faixa na sessão (1, 2, 3, ...). |
| `áudio` | Nome do arquivo de áudio daquela faixa. |
| `fator` | Condição/fator daquela faixa. |
| `volume` | Volume do sistema (0–100) no instante em que a faixa começou a tocar. |
| `intervalo` | Segundos entre o **fim** daquela faixa e o clique em **Continuar →** — útil para medir o tempo de reação/preparo entre as faixas. |

<!-- SCREENSHOT: dados_da_execucao.xlsx aberto, mostrando as colunas n/áudio/fator/volume/intervalo -->

## 📈 Gráfico do sinal em tempo real

<!-- SCREENSHOT: cartão do gráfico durante uma gravação, mostrando a linha do sinal se formando, o ponteiro e o chip de tempo -->

Abaixo do player, um cartão desenha o sinal do BITalino do canal selecionado **ao vivo**, faixa
por faixa — útil para conferir visualmente, durante a coleta, que o sensor está captando um sinal
plausível (sem precisar abrir o CSV depois):

- O eixo de tempo começa em **`-0:05`** (os 5 segundos finais da contagem regressiva) e vai até o
  fim da música; o instante **`0:00`** (início da faixa) é destacado por uma linha vertical mais
  clara.
- A linha se forma **continuamente**, com um ponteiro que acompanha a formação e mostra o valor
  atual no canto superior direito do cartão, na **unidade do sensor ativo** (veja
  [🔬 Tipo de sensor](bitalino-connection.md#-tipo-de-sensor) — µV para EEG, mV para ECG/EMG/EOG/EGG,
  µS para EDA).
- O eixo vertical é **sempre fixo** na escala configurada (padrão do sensor ativo, ex.: **±30 µV**
  para EEG ou **±1 mV** para ECG), com marcas e linhas de grade no passo do sensor — não há mais
  reescala automática pelos dados.
- Ao final da faixa, o registro completo permanece visível durante a pausa "Continuar →" e some
  ~1 segundo antes do início da contagem da próxima faixa.
- Ao clicar em **Parar**, o gráfico volta imediatamente ao estado ocioso ("Aguardando gravação…").

> 💡 O gráfico é só uma conferência visual — os arquivos CSV/XLSX sempre gravam o valor **bruto**
> do sinal, sem qualquer suavização aplicada à exibição. Veja [Dados de saída](output-data.md).

### ⚙️ Configurações do gráfico

O menu **Configurações → Gráfico** (veja [Menus](experiment-menu.md#-menu-configurações)) abre
uma janela para ajustar como o gráfico é exibido, com **preview ao vivo** e persistência entre
execuções:

| Configuração | Faixa | Padrão |
| --- | --- | --- |
| Escala do eixo Y (µV, simétrica) | ±10 a ±50 (passo 10) | ±30 |
| Média móvel (suavização visual) | liga/desliga + janela de 1 a 15 colunas | ligada, janela 5 |
| Atualização (FPS) | 10 / 15 / 30 / 60 | 60 |
| Espessura da linha | 0.5 a 4.0 px | 1.5 |
| Linhas de grade | liga/desliga | ligadas |
| Rótulos dos eixos | liga/desliga | ligados |

> ⚠️ A **escala do eixo Y** fica travada durante um experimento em andamento; as demais
> configurações podem ser ajustadas a qualquer momento. Botões: **Salvar**, **Restaurar padrões**
> e **Cancelar**.

## Interrompendo a sessão

O botão **Parar** (no player) encerra a sessão a qualquer momento: pede confirmação ("Tem certeza
que deseja parar o experimento?") e, se confirmado, interrompe a reprodução, registra o marcador
**`PARADA_FORCADA`**, finaliza o arquivo da faixa em andamento, volta o botão principal para
**Começar** e reabre os painéis Participante/Arquivos (se estavam recolhidos).

> A perda de conexão detectada pelo watchdog (15 s sem amostras) também interrompe a sessão da
> mesma forma. Veja [Conexão com o BITalino](bitalino-connection.md).

## Volume do sistema

Ao abrir o programa, o volume principal do sistema é ajustado automaticamente para **50%**. O
slider de volume no player controla o volume principal do SO (a aplicação é feita com um pequeno
atraso após o último ajuste, para não sobrecarregar o sistema).

> 🔒 **O slider de volume fica travado durante a contagem regressiva e a reprodução de cada
> faixa**, evitando que o volume mude no meio de uma gravação. Ele volta a ficar disponível durante
> a pausa "Continuar →", entre uma faixa e a próxima.

---

Anterior: [« Arquivos de entrada](input-files.md) · Próximo: [Dados de saída »](output-data.md)
