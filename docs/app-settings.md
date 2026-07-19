# ⚙️ Configurações do App

A janela **Configurações → App…** guarda as preferências do **operador e da máquina** — não o
protocolo do experimento. A regra que organiza essa separação:

> O que muda **o dado coletado ou o protocolo** vive no [`.config`](configuration-file.md)
> (viaja com o experimento, fica registrado na pasta da sessão). O que muda **como o operador usa
> o app naquela máquina** vive aqui, em `prefs.json` (chave `app`).

A janela é organizada em **seis abas**: Geral, Aparência, Arquivos, Conexão, Diagnóstico e
Avançado.

<!-- SCREENSHOT: janela "Configurações do App" com as abas visíveis -->

## Geral

| Preferência | Padrão | Descrição |
| --- | --- | --- |
| Carregar última configuração ao iniciar | ligado | Aplica automaticamente o último `.config` usado ao abrir o app. |
| Verificar atualizações ao iniciar | ligado | Consulta as Releases do GitHub na abertura (veja [menu Atualizações](experiment-menu.md#-menu-atualizações)). |
| Duração mínima da tela de carregamento | 900 ms | Evita um "flash" da splash em máquinas rápidas. |
| Confirmar antes de sair durante um experimento | ligado | Pede confirmação ao fechar o app com uma sessão em andamento. |

## Aparência

| Preferência | Padrão | Descrição |
| --- | --- | --- |
| Escala da interface | 100% (90–150%) | ⚠️ Requer reiniciar o app. |
| Abrir maximizado | desligado | ⚠️ Requer reiniciar o app. |
| Lembrar posição/tamanho da janela | ligado | Restaura a geometria da última sessão. |

## Arquivos

| Preferência | Padrão | Descrição |
| --- | --- | --- |
| Pasta de dados padrão | (a padrão do sistema) | Substitui `Documentos/ComPasso/Dados` como sugestão inicial. |
| Formato do nome da pasta de sessão | Dia-Mês-Ano | Alterna para ISO (Ano-Mês-Dia), que ordena melhor em listagens de arquivos. |
| Extensões de áudio aceitas | `.mp3`, `.wav`, `.ogg` | Lista customizável. |
| Gerar também o XLSX | ligado | Além do CSV gravado em tempo real. |

## Conexão

| Preferência | Padrão | Descrição |
| --- | --- | --- |
| Timeout de resolução LSL | 2 s (1–15) | Tempo de espera ao procurar a stream do BITalino. |
| Timeout do watchdog | 15 s (5–60) | Segundos sem amostras até considerar a conexão perdida — veja [Watchdog](bitalino-connection.md#watchdog-de-perda-de-conexão). |

## Diagnóstico

| Preferência | Padrão | Descrição |
| --- | --- | --- |
| Nível de log | INFO | ⚠️ Requer reiniciar o app. |
| Retenção de logs | 30 dias (0 = nunca apagar) | ⚠️ Requer reiniciar o app. |
| **Simular BITalino** | desligado | Liga/desliga em runtime — veja [BITalino simulado](bitalino-simulado.md). |

## Avançado

Reúne o que **ainda afeta a coleta** (não é só conforto do operador) e por isso nasce
**desabilitada**, atrás de um consentimento explícito antes de liberar a edição:

| Preferência | Padrão | Descrição |
| --- | --- | --- |
| Faixa etária aceita | 0 a 120 | Mínimo/máximo aceitos no campo Idade do participante. |
| Palavras-chave de ruído | `ruido`, `ruído`, `noise`, `barulho`, `white noise`, `pink noise` | Usadas para classificar uma faixa como ruído a partir da coluna de fator — veja [Arquivos de entrada](input-files.md#classificação-música-vs-ruído). |
| Volume inicial | 50% | Volume do sistema aplicado ao abrir o app. |
| Controlar volume do sistema | ligado | Desligar impede o ComPasso de ajustar o volume do SO (útil em máquinas onde isso não deve acontecer). |

## Persistência e rastreabilidade

- Botões **Salvar**, **Restaurar padrões** e **Cancelar**, como nas demais janelas do app.
- Preferências marcadas com ⚠️ mostram um aviso "requer reinício" em vez de fingir que a mudança
  já valeu.
- Toda sessão grava um **`ambiente.json`** na própria pasta de coleta, com as preferências
  efetivas daquela execução — responde "com que ajustes esta coleta rodou?" para quem for
  analisar os dados meses depois.

---

Anterior: [« Menus](experiment-menu.md) · Próximo: [Arquivo de configuração »](configuration-file.md)
