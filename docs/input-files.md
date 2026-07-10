# 📂 Arquivos de entrada

Para rodar um experimento, você precisa preparar dois itens: uma **pasta de músicas** e uma
**planilha de condições**.

## 1. Pasta de músicas

Uma pasta contendo os arquivos de áudio do experimento. Formatos aceitos:

- `.mp3`
- `.wav`
- `.ogg`

O ComPasso varre a pasta e considera **apenas** os arquivos com essas extensões (a verificação é
insensível a maiúsculas/minúsculas). Se a pasta não contiver nenhum arquivo de áudio compatível,
uma mensagem avisa que nenhum arquivo foi encontrado.

## 2. Planilha de condições (`.xlsx` / `.xls`)

Uma planilha Excel que associa cada arquivo de música à sua **condição/fator** experimental. Ela
precisa conter (pelo menos) duas colunas: uma com o **nome do arquivo de áudio** e outra com a
**condição/fator** daquela faixa.

### Exemplo

| musica | fator |
| --- | --- |
| faixa_01.mp3 | intenso |
| faixa_02.mp3 | calmo |
| branco_01.wav | ruido |

<!-- SCREENSHOT: planilha de condições com as colunas musica e fator -->

### 🆕 Nomes de coluna configuráveis

Por padrão, o ComPasso procura as colunas chamadas **`musica`** e **`fator`** (como no exemplo
acima). Se a sua planilha usa outros nomes (ex.: `arquivo`/`condicao`), **não é preciso renomear
nada**: ao carregar o arquivo de fatores na janela **Experimento → Novo/Editar**, dois menus
suspensos aparecem automaticamente, já listando os nomes reais das colunas encontradas — escolha
ali qual coluna é o nome do áudio e qual é o fator. Veja
[Menus → Colunas da planilha de fatores](experiment-menu.md#-colunas-da-planilha-de-fatores) para
o passo a passo e as regras de validação (as duas colunas escolhidas precisam ser diferentes).

### Regras importantes

- O valor da coluna de música deve **bater exatamente** com o nome do arquivo na pasta de músicas
  (incluindo a extensão).
- Se uma música da pasta **não tiver linha correspondente** na planilha, o ComPasso avisa
  (`Nenhuma condição encontrada para <arquivo>`) e **essa música é ignorada** durante o
  experimento.
- Se a planilha não tiver as colunas configuradas (`musica`/`fator` por padrão), ou estiver vazia,
  o mapeamento não é realizado e uma mensagem de status indica que nenhuma condição foi encontrada.

## Classificação música vs. ruído

O valor da coluna `fator` também define como cada faixa é **contada** e **ordenada**. A
classificação é feita por palavra-chave (insensível a maiúsculas/minúsculas): fatores que contêm
termos como **"ruido"**, **"ruído"**, **"noise"**, **"barulho"**, **"white noise"** ou
**"pink noise"** são tratados como **ruído**; qualquer outro valor é tratado como **música**.

Essa distinção afeta:

- Os contadores do rodapé (**ESTÍMULOS** e **RUÍDO**).
- A regra de ordenação da playlist (o ruído nunca é a primeira faixa e há pelo menos duas músicas
  entre dois ruídos consecutivos — veja [Executando um experimento](running-an-experiment.md)).

---

Anterior: [« Arquivo de configuração](configuration-file.md) · Próximo: [Executando um experimento »](running-an-experiment.md)
