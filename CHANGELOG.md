# Changelog

Todas as mudanças notáveis deste projeto são documentadas neste arquivo, seguindo o formato
[Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).

## [Não lançado]

## [2026.4.0] - 2026-07-19

### Corrigido

- ⏱️ **Dessincronização cumulativa entre beep, áudio e gráfico** — o problema tinha **duas causas
  independentes**, ambas corrigidas:
  - *Relógios distintos tratados como um só.* O timestamp das amostras do LSL vem do relógio do
    **emissor** (host do OpenSignals), não do relógio local. Os dois derivam entre si (~0,17 s ao
    longo de uma sessão de 12 faixas, medido em hardware real), o que deslocava por igual todos os
    marcadores de cada faixa, cada vez mais. As amostras passam a ser convertidas com
    `inlet.time_correction()`, reconsultado periodicamente durante a aquisição.
  - *Contagem regressiva por passos acumulados.* Era um laço de `sleep(1 s)`, e cada volta custava
    um pouco mais que 1 s; um beep configurado para "t-5" tocava progressivamente mais cedo. Os
    instantes do beep, do gráfico e do áudio passam a ser calculados como alvos absolutos a partir
    do início do estímulo. Erro medido: sub-milissegundo, igual na 1ª e na 20ª faixa.
- 📉 **Vão no fim do gráfico** — a cauda de amostras ainda em trânsito no LSL era descartada antes
  de chegar ao traço, que parava antes do fim do eixo enquanto o ponteiro saltava. A aquisição
  agora é encerrada **antes** de fechar o gráfico, garantindo que todas as amostras cheguem.
- 🏷️ **Eixo X do gráfico instável** — os rótulos de tempo ora apareciam de 1 em 1 segundo, ora de
  5 em 5, conforme a duração da faixa, e um rótulo isolado sumia perto do fim. Agora são sempre
  múltiplos de 5 s, e um rótulo só é omitido quando de fato se sobreporia ao rótulo final.
- 💾 **Configurações do gráfico não permaneciam** — salvar e fechar revertia o gráfico ao estado
  anterior (as preferências ficavam corretas em disco, mas só voltavam a valer ao reabrir a
  janela). Ajustes de escala, grade e rótulos também passam a ter preview com a aplicação ociosa.
- 🎨 **Grade escura demais nos temas claros** (Sereno/Aurora) — as linhas competiam com o traço do
  sinal. A grade passou a usar a cor da própria paleta com bem menos opacidade (medido: de
  `#cdd0d4` para `#eff1f3` sobre branco), e o Aurora ganhou uma grade de tom quente.
- 🗂️ **Coluna `audio` vazia em `dados_da_execucao.xlsx`** — divergência de acentuação entre a
  chave gravada e o cabeçalho declarado fazia a planilha sair com a coluna toda em branco.
- 🛡️ **App travado após um erro inesperado** — uma exceção na thread do experimento a encerrava em
  silêncio, deixando a interface bloqueada sem aviso. Agora o erro é registrado, informado e a
  sessão é encerrada de forma limpa.
- 🪟 **Mensagens de erro na janela errada** — ao salvar uma configuração inválida, o aviso abria
  atrás da janela de configuração (que é modal) e ficava inacessível.

### Adicionado

- 🔄 **Menu "Atualizações"** — verifica automaticamente, uma vez por execução e de forma discreta,
  se há uma versão mais recente publicada. Havendo, o menu ganha um ponto vermelho e o item passa a
  "Baixar atualização!", levando à página de releases. A verificação manual mostra uma janela com o
  andamento e informa o resultado, inclusive quando não há conexão.
- 🌗 **Botão sol/lua na barra de menus** — atalho para alternar entre tema claro e escuro, que
  retoma o último tema usado de cada família (sair de Iris para o claro e voltar devolve Iris).
- ✅ **Validação de campos com aviso na hora** — endereço MAC, quantidade de músicas/ruído, colunas
  da planilha (não podem ser a mesma), tempo do beep e faixa de volume da calibração passam a
  contornar o campo de vermelho e explicar o problema logo abaixo dele.
- 🔔 **Marcador `BEEP` nos dados** — o instante do beep passa a ser gravado no CSV/XLSX, tornando o
  intervalo beep→áudio auditável a posteriori.

### Alterado

- 🔊 **Áudio migrado para QtMultimedia** — faixa e beep passam a usar o mesmo backend (o beep num
  canal dedicado e pré-carregado no arranque), o que também elimina a diferença de latência entre
  os dois. A dependência `pygame-ce` deixou de ser necessária.
- 📈 **Taxa de atualização do gráfico fixa em 30 fps** — a opção saiu do menu Gráfico: a decimação
  já mantém o custo constante, e elevar o valor só consumia mais processamento. O gráfico também
  passou a usar memória constante ao longo da faixa, independentemente da duração.
- 🧭 **Eixo X do gráfico sempre de t-5 até o fim exato da faixa**, com marcas em três níveis de
  destaque (1 s, 5 s e o início do áudio).

## [2026.3.0] - 2026-07-11

### Adicionado

- 🧭 **Indicador de progresso (stepper) redesenhado** — ganhou as etapas "Configurações" (config de
  experimento criada/aberta) e "Calibragem" (opcional, só aparece com a calibração de volume
  habilitada); "Iniciar" foi renomeada para "Começar". Etapas pendentes que não são a atual agora
  ficam **vermelhas** em vez de usar a mesma cor neutra da etapa em andamento.
- 🔒 **Volume travado durante a faixa** — o slider de volume fica desabilitado enquanto uma faixa
  está em contagem regressiva ou reprodução, evitando mudar o volume no meio de uma gravação.
- 📄 **Planilha `dados_da_execucao.xlsx`** — uma planilha por sessão (regravada a cada faixa
  concluída) com colunas `n`, `áudio`, `fator`, `volume` (do sistema, no instante do play) e
  `intervalo` (segundos entre o fim da faixa e o clique em "Continuar →").
- 🔤 **Colunas da planilha de fatores configuráveis** — dois menus suspensos na janela de
  configuração do experimento permitem escolher, pelos cabeçalhos reais do arquivo carregado, qual
  coluna traz o nome do áudio e qual traz o fator (antes, os nomes `musica`/`fator` eram fixos).
  Validação em tempo real (borda vermelha) impede escolher a mesma coluna nos dois.
- 🔔 **Beep de aviso opcional** — checkbox + slider (1 a 10 s) na janela de configuração tocam um
  aviso sonoro alguns segundos antes de cada faixa começar, durante a contagem regressiva; validado
  para ser sempre menor que o tempo de contagem.
- 🎚️ **Tempo pré-estímulo como slider** — a contagem regressiva antes de cada faixa (5 a 120 s)
  agora é ajustada por um slider, em vez de um campo de texto.
- 🚪 **Opção "Sair" no menu Experimento** — encerra o app; permanece sempre habilitada. Novo/Abrir/
  Editar passam a ficar **desabilitados** durante um experimento em andamento.
- 🔬 **Tipo de sensor do BITalino** — combobox na barra de conexão (EDA/ECG/EMG/EOG/EEG/EGG,
  padrão ECG) e na janela de configuração, escolhido antes de conectar. Define a unidade e a janela
  padrão da escala do eixo Y do gráfico do sinal em tempo real (o dado gravado continua bruto —
  é só uma mudança de exibição). Trocar de sensor reseta a escala ao padrão daquele sensor.
- 🔊 **Calibração de volume (opcional)** — checkbox + carregador de faixa de áudio na janela de
  configuração habilitam um botão "Calibrar Volume" no player, que abre uma janela dedicada: uma
  linha de base demonstrativa, seguida da calibração em si, em que o volume do sistema sobe
  gradualmente (X% a cada X s, entre um mínimo e um máximo configuráveis na própria janela)
  enquanto a faixa toca, até o participante indicar que o volume está confortável. O volume ótimo
  encontrado é aplicado ao sistema e trava o slider de volume do player pelo resto da sessão.
  Desabilitada por padrão.

## [2026.2.0] - 2026-07-02

### Adicionado
- Tela de carregamento (loading screen) ao abrir o app.
- Sistema de temas em tempo de execução: 3 paletas de cores (Teal/Iris/Amber) selecionáveis
  pelo menu "Tema", com preferência persistida entre execuções.
- `StepperFrame`: indicador visual das 4 etapas do experimento (Conectar → Participante →
  Arquivos → Iniciar), atualizado em tempo real.
- Ajuste automático do volume do sistema na inicialização do app.
- Frame principal com rolagem (`CTkScrollableFrame`) e tamanho mínimo de janela definido.
- Suíte de testes automatizados (`pytest`), cobrindo conexão/watchdog do BITalino, gravação,
  classificação de condições, validação de MAC, formatação, caminhos e lógica de botões —
  substituindo o notebook manual de testes usado anteriormente.

### Corrigido
- Bug na troca de tema em tempo de execução.
- Ícones da tela de carregamento e da janela de configurações de experimento.
- Bug de dimensionamento no frame superior (conexão).
- Bugs na barra de menu ("Experimento"/"Tema").
- Problemas de nomenclatura (variáveis/identificadores) no código da GUI.
- Correções diversas de bugs (commit `bcd157c`, sem detalhamento adicional disponível no
  histórico de commits).

### Melhorado
- Reformulação visual geral da interface (frames superior, central e inferior; novos
  fábricas de widgets estilizados em `widgets.py`).
- Logo e ícones do app atualizados.
- `README.md` reescrito: banner, badges de status, seção de Releases e formatação geral.

### Removido / Interno
- API de playlist morta removida de `Player` (`play_playlist`/`stop_playlist`/`set_playlist`/
  `is_playing`/`is_paused`) — não havia uso real no app.
- Refatoração e limpeza de código morto em `src/gui/assets.py`.
- Infraestrutura de testes adicionada (`pytest.ini`, `requirements-dev.txt`).
- Notebook manual de testes (`tests/tests.ipynb`) removido, substituído pela suíte pytest.
- Ajustes em `compasso.spec` (arquivo de versão do Windows, ícones) e `.gitignore`.

## [2026.1.0] - 2026-06-29

Primeiro release com tag publicado do ComPasso.
