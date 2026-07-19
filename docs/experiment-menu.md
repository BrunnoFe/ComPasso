# 🗂️ Menus Experimento / Configurações / Tema / Atualizações / Ajuda

A barra de menus da janela principal tem cinco cascatas — **Experimento**, **Configurações**,
**Tema**, **Atualizações** e **Ajuda** — mais um atalho avulso na ponta direita da barra: um
botão **sol/lua** que troca entre a última paleta clara e a última escura usadas, sem precisar
abrir o menu Tema.

![Menu](docs\assets\images\menu.png)

## 📁 Menu Experimento

Centraliza a configuração do experimento em arquivos `.config` reutilizáveis. Cada `.config` é um
arquivo JSON que armazena caminhos, quantidades e parâmetros do BITalino — veja o schema completo
em [Arquivo de configuração](configuration-file.md).

> **Carga automática ao iniciar:** o ComPasso carrega silenciosamente o último `.config` usado
> (se o arquivo ainda existir e for válido) e aplica todos os campos automaticamente. Em sessões
> recorrentes com o mesmo protocolo, basta abrir o programa.

### Novo

Abre a janela de configuração com campos vazios. Preencha todos os campos:

| Campo | Descrição |
| --- | --- |
| Pasta de músicas | Pasta com os arquivos de áudio do experimento (`.mp3` / `.wav` / `.ogg`) |
| Quantidade de músicas | Número inteiro ≥ 1 |
| Quantidade de ruído | Número inteiro ≥ 0 |
| Arquivo de fatores | Planilha `.xlsx` / `.xls` com as condições de cada faixa |
| 🆕 Coluna do nome dos áudios / Coluna dos fatores | Surgem como dois menus suspensos assim que o arquivo de fatores é carregado, já preenchidos com os nomes reais das colunas da planilha — veja [Arquivos de entrada](input-files.md#planilha-de-condições) |
| Pasta de salvamento dos dados | Onde os arquivos da sessão serão gravados |
| Canal ativo do BITalino | Canal do sensor a gravar — **A1 a A6** |
| 🆕 Tipo de sensor | **EDA** / **ECG** (padrão) / **EMG** / **EOG** / **EEG** / **EGG** — define a unidade e a escala do gráfico, veja [Conexão com o BITalino](bitalino-connection.md#-tipo-de-sensor) |
| Endereço MAC do BITalino | Endereço no formato `XX:XX:XX:XX:XX:XX` |
| 🆕 Tempo pré-estímulo (s) | Slider de **5 a 120 segundos** — duração da contagem regressiva antes de cada faixa |
| 🆕 Beep de aviso | Checkbox + slider de **1 a 10 segundos** — toca um beep no t-X da contagem regressiva; desabilitado por padrão |

<!-- SCREENSHOT: janela "Configuração do Experimento" com os campos preenchidos, incluindo os
     menus de coluna, o combobox de sensor e os sliders de pré-estímulo/beep -->

Ao clicar em **Salvar**, os valores são validados (veja abaixo). Se estiverem corretos, você
escolhe o nome e o local do arquivo `.config` (pasta padrão sugerida:
`Documentos/ComPasso/Configurações do Experimento/`). A configuração é aplicada imediatamente aos
campos da janela principal.

### 🔔 Colunas da planilha de fatores

Ao escolher o **Arquivo de fatores**, dois menus suspensos aparecem logo abaixo, listando os
cabeçalhos reais daquela planilha — um para a coluna com o **nome dos arquivos de áudio** e outro
para a coluna com o **fator/condição**. Você **não pode escolher a mesma coluna nos dois**: se
tentar, ambos os menus ficam com a borda vermelha (validação em tempo real), e o botão **Salvar**
recusa com uma mensagem explicando o problema. Isso substitui a exigência antiga de nomear as
colunas exatamente `musica`/`fator` — agora qualquer planilha funciona, desde que as colunas sejam
selecionadas corretamente.

### 🔔 Beep de aviso

Um checkbox ("Tocar um beep antes de cada faixa") habilita um slider de **1 a 10 segundos** que
define quantos segundos antes do início da faixa o beep toca, durante a contagem regressiva. O
tempo do beep **precisa ser menor** que o tempo de contagem regressiva (Tempo pré-estímulo) —
se você definir um valor igual ou maior, o slider fica vermelho e o **Salvar** é bloqueado com uma
mensagem explicando exatamente o conflito. Por padrão o beep vem **desligado**; quando ligado, o
padrão é **t-1s**.

### Abrir

Abre um seletor de arquivos para carregar um `.config` existente. O arquivo é validado antes de
ser aplicado; se houver problemas, uma mensagem lista os erros específicos e a configuração não é
aplicada.

### Editar

Disponível **somente após** um "Novo" ou "Abrir" bem-sucedido. Reabre a janela de configuração
pré-preenchida com os valores do `.config` atual. Ao salvar, solicita **confirmação antes de
sobrescrever** o arquivo (`Sobrescrever <nome>?`).

### 🚪 Sair

Encerra o aplicativo imediatamente. Diferente de Novo/Abrir/Editar, **fica sempre habilitada**,
mesmo durante um experimento em andamento.

> ⚠️ **Novo, Abrir e Editar ficam desabilitados enquanto um experimento está em andamento** — evita
> trocar a configuração ativa no meio de uma sessão de coleta. Eles voltam a ficar disponíveis
> assim que a sessão termina ou é interrompida (Editar só se já havia uma configuração carregada).

### Validações e mensagens de erro

Ao salvar, cada campo é validado. As mensagens são exibidas diretamente ao usuário. Regras reais:

- **Pasta de músicas:** obrigatória e deve existir (`Pasta de músicas: diretório não encontrado`).
- **Quantidade de músicas:** inteiro ≥ 1 (`deve ser um número inteiro maior ou igual a 1`).
- **Quantidade de ruído:** inteiro ≥ 0 (`deve ser um número inteiro maior ou igual a 0`).
- **Arquivo de fatores:** obrigatório, deve existir e terminar em `.xlsx`/`.xls`
  (`deve ser um arquivo .xlsx ou .xls`).
- **Pasta de salvamento dos dados:** obrigatória e deve existir.
- **Canal ativo do BITalino:** obrigatório, entre A1 e A6.
- **Endereço MAC do BITalino:** obrigatório e no formato `XX:XX:XX:XX:XX:XX`
  (`formato inválido (use XX:XX:XX:XX:XX:XX)`).
- **Coluna do nome dos áudios / Coluna dos fatores:** ambas obrigatórias e **diferentes** entre si
  (`devem ser colunas diferentes`); também precisam existir de fato na planilha carregada.
- **Tipo de sensor:** deve ser um dos seis sensores válidos.
- **Tempo do beep:** se o beep estiver habilitado, precisa ser um inteiro de 1 a 10 segundos e
  **menor** que o tempo pré-estímulo configurado.

Ao **abrir** um arquivo, há ainda verificações de estrutura: se o JSON estiver malformado
(`Arquivo de configuração inválido ou ilegível (JSON malformado)`), se faltar a versão
(`Campo ausente: versão da configuração (config_version)`), ou se algum campo obrigatório estiver
ausente/vazio (`Campo ausente: ...` / `Campo vazio: ...`).

## ⚙️ Menu Configurações

Duas opções:

- **App…** — abre a janela **Configurações do App**, com as preferências do operador/máquina
  (arranque, aparência, conexão, diagnóstico, e o modo **Simular BITalino**). Detalhes completos
  em [Configurações do App](app-settings.md).
- **Gráfico…** — abre a janela **Configurações do Gráfico** — ajusta os parâmetros de exibição do
  gráfico do sinal em tempo real (escala do eixo Y, média móvel, espessura da linha, grade e
  rótulos dos eixos). Detalhes completos na seção
  [📈 Gráfico do sinal em tempo real](running-an-experiment.md#-gráfico-do-sinal-em-tempo-real)
  de "Executando um experimento".

<!-- SCREENSHOT: janela "Configurações do Gráfico" com todos os controles visíveis -->

As mudanças têm **preview ao vivo** (aparecem no gráfico na hora, se um gráfico estiver visível)
e são persistidas em `prefs.json` — carregadas automaticamente na próxima abertura do programa,
junto com o tema. A **escala do eixo Y** fica desabilitada durante um experimento em andamento
(é fixa durante a sessão); as demais configurações podem ser ajustadas a qualquer momento. Botões:
**Salvar** (aplica e persiste), **Restaurar padrões** (volta aos valores de fábrica) e
**Cancelar** (fecha sem salvar, revertendo qualquer preview aplicado).

> 🆕 A **unidade e os limites do slider de escala Y** agora dependem do **tipo de sensor**
> selecionado na barra de conexão (µV para EEG, mV para ECG/EMG/EOG/EGG, µS para EDA) — veja
> [Conexão com o BITalino](bitalino-connection.md#-tipo-de-sensor). Trocar de sensor reseta a
> escala ao padrão daquele sensor.

## 🎨 Menu Tema

Troca a paleta de cores de toda a aplicação **ao vivo**, sem reiniciar. **Seis** opções
disponíveis — três escuras e duas claras:

| Paleta | Estilo |
| --- | --- |
| 🌊 **Teal** (padrão) | Escura, acento verde-azulado |
| 🔮 **Iris** | Escura, acento violeta |
| 🟠 **Amber** | Escura, acento âmbar |
| ☀️ **Sereno** | Clara, acento azul-céu suave |
| 🌅 **Aurora** | Clara, acento coral-pêssego |
| 🌲 **Floresta** | Escura, acento verde-menta |

A escolha é lembrada entre execuções (persistida em `prefs.json`).

> A troca de tema é **instantânea**, a qualquer momento — inclusive com o BITalino conectado ou
> um experimento em andamento: a interface inteira recolore ao vivo, sem reiniciar nem perder o
> estado da sessão. Além do menu Tema, o botão **sol/lua** no canto direito da barra alterna
> rapidamente entre a última paleta clara e a última escura usadas.

<!-- SCREENSHOT: menu Tema aberto mostrando as 6 paletas (Teal/Iris/Amber/Sereno/Aurora/Floresta) -->

## 🔔 Menu Atualizações

Verifica, na inicialização (se habilitado em [Configurações → App](app-settings.md)) e sob
demanda, se há uma versão mais nova publicada nas Releases do GitHub. Quando há, um ponto
vermelho marca o título do menu e o item passa a "Baixar atualização!" — clicar abre a página de
Releases no navegador. A verificação usa só a biblioteca padrão (`urllib`), sem telemetria.

## 🆘 Menu Ajuda

Três opções:

- **Abrir pasta de logs** — abre a pasta de logs da aplicação no gerenciador de arquivos do SO.
- **Página do projeto (GitHub)** — abre o repositório do projeto no navegador padrão.
- **Site do projeto** — abre a página pública do projeto no navegador padrão.

---

Anterior: [« BITalino simulado](bitalino-simulado.md) · Próximo: [Configurações do App »](app-settings.md)
