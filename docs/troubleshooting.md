# 🔧 Solução de problemas

Esta página lista comportamentos de erro reais do ComPasso e como resolvê-los. Quando algo dá
errado, o primeiro lugar para olhar é o arquivo central de erros:
`<app-data>/ComPasso/errors.log` (acessível pelo menu **Ajuda → Abrir pasta de logs**).

## Conexão com o BITalino

| Sintoma | Causa provável / solução |
| --- | --- |
| **"Endereço MAC inválido"** | O MAC digitado não está no formato esperado. Use `XX:XX:XX:XX:XX:XX` (separadores `:`, espaço ou `-` são aceitos). |
| **Falha ao conectar / timeout (~2 s)** | O Lab Streaming Layer não está ativo no OpenSignals, o dispositivo não está transmitindo, ou o MAC está incorreto. Ative o LSL, coloque o BITalino em aquisição e confira o endereço. |
| **"Conexão estabelecida, mas não foi possível puxar amostras"** | A stream foi encontrada, mas não há fluxo de dados. Confirme que o compartilhamento pelo LSL está ativo e que o BITalino está transmitindo. |
| **"Conexão com BITalino perdida"** durante o experimento | O watchdog detectou ≥ 15 s sem amostras. O experimento é interrompido automaticamente (marcador `PARADA_FORCADA`). Verifique o sensor e o OpenSignals, e reconecte. |
| **Sinal sempre 0 ou constante** | Canal errado selecionado. Consulte a primeira amostra registrada no log (`recorder`) para descobrir qual índice corresponde ao sensor e ajuste o **Canal** (A1–A6). |
| **Aviso "nominal_srate=0 (taxa irregular)" no log** | A taxa de aquisição no OpenSignals está irregular; o *dejitter* não suaviza os timestamps. Configure uma taxa fixa (ex.: 100 Hz) no OpenSignals. |

Para o fluxo de conexão completo, veja [Conexão com o BITalino](bitalino-connection.md).

## Início do experimento

| Sintoma | Causa provável / solução |
| --- | --- |
| **Mensagem ao clicar em "Começar"** | Falta um dos seis pré-requisitos. A mensagem indica exatamente o quê (configuração, conexão, informações do participante, arquivos, diretório de saída, ou sessão já em andamento). Veja [Executando um experimento](running-an-experiment.md). |
| **"Crie ou abra uma configuração de experimento..."** | Nenhuma configuração foi criada/aberta nesta sessão. Use o menu **Experimento → Novo** ou **Abrir**. |
| **Erro ao criar a pasta de salvamento** | O diretório de saída não pôde ser criado (permissões/caminho). Escolha outra pasta em "Salvar dados em". |

## Participante

| Sintoma | Causa provável / solução |
| --- | --- |
| **"Nome e gênero devem conter apenas letras e espaços"** | Há dígitos ou símbolos nos campos Nome/Gênero. Use apenas letras e espaços. |
| **"Idade deve ser um número entre X e Y"** | A idade está fora da faixa aceita ou não é um número inteiro. A faixa padrão de fábrica é **0 a 120**, mas pode ser restringida em [Configurações → App → Avançado](app-settings.md#avançado). |

## Arquivos de entrada

| Sintoma | Causa provável / solução |
| --- | --- |
| **"Pasta de músicas não encontrada"** | O caminho da pasta de músicas não existe. Verifique e selecione novamente. |
| **"Nenhum arquivo de áudio (.mp3/.wav/.ogg) na pasta"** | A pasta não contém arquivos com extensões suportadas. Adicione os áudios ou escolha outra pasta. |
| **"Nenhuma condição encontrada para \<arquivo\>"** | O nome na coluna `musica` da planilha não bate com o arquivo na pasta. A música é ignorada no experimento. Corrija a planilha e recarregue. Veja [Arquivos de entrada](input-files.md). |
| **"Nenhuma condição encontrada para as músicas selecionadas"** | A planilha não tem as colunas `musica` e `fator`, ou está vazia. Ajuste a planilha. |

## Áudio e volume

| Sintoma | Causa provável / solução |
| --- | --- |
| **Áudio não toca** | Verifique se os arquivos estão em `.mp3`, `.wav` ou `.ogg` e se o volume do sistema não está no mínimo. |
| **"Controle de volume do sistema indisponível"** | O controle de volume não está acessível neste sistema (ferramenta ausente ou SO não suportado). O slider fica sem efeito, mas o experimento funciona normalmente. |

## Tema

| Sintoma | Causa provável / solução |
| --- | --- |
| **Menu "Tema" não responde / pede para desconectar** | A troca de tema é bloqueada enquanto o BITalino está conectado ou um experimento está em andamento. Desconecte/finalize antes de trocar. |

## 📈 Gráfico do sinal em tempo real

| Sintoma | Causa provável / solução |
| --- | --- |
| **Gráfico fica sempre em "Aguardando gravação…"** | O gráfico só recebe dados durante os 5 s finais da contagem regressiva e a reprodução da faixa — confirme que o BITalino está conectado e transmitindo, e que uma faixa está de fato em andamento. |
| **A linha do gráfico não se move / ponteiro parado** | Verifique se o sensor está transmitindo amostras (mesma causa de "Sinal sempre 0 ou constante", acima) — o gráfico reflete exatamente o que chega do BITalino. |

---

Anterior: [« Dados de saída](output-data.md) · [Voltar ao início](index.md)
