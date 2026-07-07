# 🗂️ Menus Experimento / Configurações / Tema / Ajuda

A barra de menus da janela principal tem quatro cascatas: **Experimento**, **Configurações**,
**Tema** e **Ajuda**.

<!-- SCREENSHOT: barra de menus com Experimento / Configurações / Tema / Ajuda -->

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
| Pasta de salvamento dos dados | Onde os arquivos da sessão serão gravados |
| Canal ativo do BITalino | Canal do sensor a gravar — **A1 a A6** |
| Endereço MAC do BITalino | Endereço no formato `XX:XX:XX:XX:XX:XX` |

<!-- SCREENSHOT: janela "Configuração do Experimento" com os campos preenchidos -->

Ao clicar em **Salvar**, os valores são validados (veja abaixo). Se estiverem corretos, você
escolhe o nome e o local do arquivo `.config` (pasta padrão sugerida:
`Documentos/ComPasso/Configurações do Experimento/`). A configuração é aplicada imediatamente aos
campos da janela principal.

### Abrir

Abre um seletor de arquivos para carregar um `.config` existente. O arquivo é validado antes de
ser aplicado; se houver problemas, uma mensagem lista os erros específicos e a configuração não é
aplicada.

### Editar

Disponível **somente após** um "Novo" ou "Abrir" bem-sucedido. Reabre a janela de configuração
pré-preenchida com os valores do `.config` atual. Ao salvar, solicita **confirmação antes de
sobrescrever** o arquivo (`Sobrescrever <nome>?`).

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

Ao **abrir** um arquivo, há ainda verificações de estrutura: se o JSON estiver malformado
(`Arquivo de configuração inválido ou ilegível (JSON malformado)`), se faltar a versão
(`Campo ausente: versão da configuração (config_version)`), ou se algum campo obrigatório estiver
ausente/vazio (`Campo ausente: ...` / `Campo vazio: ...`).

## ⚙️ Menu Configurações

Por enquanto tem uma única opção: **Gráfico**, que abre a janela **Configurações do Gráfico** —
ajusta os parâmetros de exibição do gráfico do sinal em tempo real (escala do eixo Y, média
móvel, taxa de atualização, espessura da linha, grade e rótulos dos eixos). Detalhes completos
na seção [📈 Gráfico do sinal em tempo real](running-an-experiment.md#-gráfico-do-sinal-em-tempo-real)
de "Executando um experimento".

<!-- SCREENSHOT: janela "Configurações do Gráfico" com todos os controles visíveis -->

As mudanças têm **preview ao vivo** (aparecem no gráfico na hora, se um gráfico estiver visível)
e são persistidas em `prefs.json` — carregadas automaticamente na próxima abertura do programa,
junto com o tema. A **escala do eixo Y** fica desabilitada durante um experimento em andamento
(é fixa durante a sessão); as demais configurações podem ser ajustadas a qualquer momento. Botões:
**Salvar** (aplica e persiste), **Restaurar padrões** (volta aos valores de fábrica) e
**Cancelar** (fecha sem salvar, revertendo qualquer preview aplicado).

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

> ⚠️ A troca de tema só é permitida com a aplicação **ociosa** — sem BITalino conectado e sem
> experimento em andamento —, pois ela reconstrói toda a interface. Se você tentar trocar o tema
> conectado ou durante uma sessão, uma mensagem pede para desconectar/finalizar antes.

<!-- SCREENSHOT: menu Tema aberto mostrando as 6 paletas (Teal/Iris/Amber/Sereno/Aurora/Floresta) -->

## 🆘 Menu Ajuda

Duas opções:

- **Abrir pasta de logs** — abre a pasta de logs da aplicação no gerenciador de arquivos do SO.
- **Página do projeto (GitHub)** — abre o repositório do projeto no navegador padrão.

---

Anterior: [« Conexão com o BITalino](bitalino-connection.md) · Próximo: [Arquivo de configuração »](configuration-file.md)
