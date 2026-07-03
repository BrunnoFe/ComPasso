# ComPasso — Documentação

**ComPasso** é uma plataforma de pesquisa em psicofisiologia que sincroniza a reprodução de
músicas com a aquisição contínua do sinal do **BITalino** (via OpenSignals + Lab Streaming
Layer). As amostras do sinal e os marcadores de evento compartilham um único relógio
(`pylsl.local_clock()`), garantindo sincronia precisa entre o estímulo auditivo e os dados
fisiológicos coletados.

O programa toca uma sequência pseudoaleatória de faixas (músicas e ruído) e grava, para cada
faixa, um par de arquivos (CSV + XLSX) com o sinal e os marcadores de evento alinhados no tempo.

<!-- SCREENSHOT: janela principal do ComPasso com a barra de menu (Experimento / Tema / Ajuda), o stepper de 4 etapas e o player -->

## Para que serve

- **Contexto:** experimento de laboratório (ex.: condutância da pele) em que a reprodutibilidade
  e a rastreabilidade dos dados são prioritárias.
- **O que faz:** conecta ao BITalino, coleta dados do participante, monta uma playlist a partir de
  uma pasta de áudios e de uma planilha de condições, e grava o sinal sincronizado por faixa.
- **Multiplataforma:** Windows e macOS (Linux como melhor esforço).

## Índice da documentação

1. [Primeiros passos](getting-started.md) — requisitos, instalação e como executar.
2. [Conexão com o BITalino](bitalino-connection.md) — OpenSignals, LSL e o watchdog de conexão.
3. [Menus Experimento / Tema / Ajuda](experiment-menu.md) — criação e uso de configurações.
4. [Arquivo de configuração `.config`](configuration-file.md) — o schema real dos campos.
5. [Arquivos de entrada](input-files.md) — pasta de músicas e planilha de condições.
6. [Executando um experimento](running-an-experiment.md) — passo a passo completo de uma sessão.
7. [Dados de saída](output-data.md) — nomes de pastas/arquivos e colunas do CSV/XLSX.
8. [Solução de problemas](troubleshooting.md) — erros comuns e como resolvê-los.

---

> Documentação gerada a partir do código-fonte do projeto. Para o funcionamento interno e
> convenções de desenvolvimento, veja o `README.md` e o `CLAUDE.md` na raiz do repositório.
