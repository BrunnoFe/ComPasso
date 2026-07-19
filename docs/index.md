# 🎵🧭 ComPasso — Documentação

**ComPasso** é uma plataforma de pesquisa em psicofisiologia que sincroniza a reprodução de
músicas com a aquisição contínua do sinal do **BITalino** (via OpenSignals + Lab Streaming
Layer). As amostras do sinal e os marcadores de evento compartilham um único relógio
(`pylsl.local_clock()`), garantindo sincronia precisa entre o estímulo auditivo e os dados
fisiológicos coletados. Um **gráfico do sinal em tempo real** 📈 acompanha cada faixa durante a
gravação.

O programa toca uma sequência pseudoaleatória de faixas (músicas e ruído) e grava, para cada
faixa, um par de arquivos (CSV + XLSX) com o sinal e os marcadores de evento alinhados no tempo.

<!-- SCREENSHOT: janela principal do ComPasso com a barra de menu completa (Experimento /
     Configurações / Tema / Atualizações / Ajuda + botão sol/lua), o indicador de progresso em
     etapas, o player e o gráfico do sinal em tempo real -->

## 🔎 Para que serve

- **Contexto:** experimento de laboratório (ex.: condutância da pele) em que a reprodutibilidade
  e a rastreabilidade dos dados são prioritárias.
- **O que faz:** conecta ao BITalino (com suporte a diferentes tipos de sensor — EDA/ECG/EMG/EOG/
  EEG/EGG), coleta dados do participante, monta uma playlist a partir de uma pasta de áudios e de
  uma planilha de condições, grava o sinal sincronizado por faixa e exibe um gráfico do sinal em
  tempo real durante a coleta.
- **Multiplataforma:** Windows e macOS (Linux como melhor esforço).

## 📚 Índice da documentação

1. [Primeiros passos](getting-started.md) — requisitos, instalação e como executar.
2. [Conexão com o BITalino](bitalino-connection.md) — OpenSignals, LSL e o watchdog de conexão.
3. [BITalino simulado](bitalino-simulado.md) — teste a interface inteira sem hardware.
4. [Menus Experimento / Configurações / Tema / Atualizações / Ajuda](experiment-menu.md) — criação
   e uso de configurações, incluindo as opções do gráfico do sinal.
5. [Configurações do App](app-settings.md) — preferências do operador/máquina (6 abas) e
   `ambiente.json`.
6. [Arquivo de configuração `.config`](configuration-file.md) — o schema real dos campos.
7. [Arquivos de entrada](input-files.md) — pasta de músicas e planilha de condições.
8. [Executando um experimento](running-an-experiment.md) — passo a passo completo de uma sessão,
   incluindo o gráfico do sinal em tempo real e a calibração de volume.
9. [Dados de saída](output-data.md) — nomes de pastas/arquivos e colunas do CSV/XLSX.
10. [Solução de problemas](troubleshooting.md) — erros comuns e como resolvê-los.

---
