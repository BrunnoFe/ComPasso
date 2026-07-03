# Dados de saída

## Onde os dados são salvos

| O quê | Local |
| --- | --- |
| **Dados do experimento** | `Documentos/ComPasso/Dados/` (ou a pasta escolhida em "Salvar dados em") |
| **Arquivos de configuração** | `Documentos/ComPasso/Configurações do Experimento/` |
| **Logs por categoria** | `<app-data>/ComPasso/logs/<categoria>/` |
| **Arquivo central de erros** | `<app-data>/ComPasso/errors.log` |

`<app-data>` é resolvido por sistema operacional: `%LOCALAPPDATA%` no Windows,
`~/Library/Application Support` no macOS, `$XDG_DATA_HOME` (ou `~/.local/share`) no Linux. No
Windows, a pasta Documentos é resolvida pela API de "known folders" (à prova do redirecionamento
do OneDrive). As pastas são criadas automaticamente na primeira execução.

## Estrutura dos arquivos

Cada coleta cria **uma pasta por sessão**, nomeada
`nome_idade_genero_dia-mes-ano_hora-min-seg`. Dentro dela, cada faixa gera **um par de arquivos**
(CSV + XLSX) nomeados `ordem_nomedamusica`:

```text
Documentos/ComPasso/Dados/
└── joao_25_masculino_15-06-2025_10-30-00/
    ├── 01_faixa_01.csv
    ├── 01_faixa_01.xlsx
    ├── 02_branco_01.csv
    └── 02_branco_01.xlsx
```

- A **ordem** é a posição da faixa na playlist (começa em 1, com zero à esquerda — largura mínima
  de 2 dígitos).
- A **extensão do áudio** é removida do nome do arquivo.
- Caracteres problemáticos nos nomes (do participante e da música) são substituídos por `_`.
- O **CSV é gravado em tempo real** (com sincronização periódica em disco, resistindo a quedas
  inesperadas); o **XLSX é gerado ao final** de cada faixa, a partir do mesmo conteúdo do CSV.

<!-- SCREENSHOT: exemplo de arquivo de dados aberto (CSV/XLSX) -->

## Colunas do CSV/XLSX

As colunas aparecem exatamente nesta ordem:

| Coluna | Descrição |
| --- | --- |
| `timestamp` | Segundos desde o início da contagem regressiva daquela faixa (`local_clock()` − `t0`, onde `t0` é o instante do `INICIO_CONTAGEM`). |
| `signal` | Valor do sensor do BITalino no canal selecionado (A1–A6). |
| `markers` | Vazio na maioria das linhas; preenchido nos eventos (veja abaixo). |
| `music_file` | Nome do arquivo da faixa; preenchido nas linhas que carregam um marcador. |
| `fator` | Condição/fator da faixa; preenchido nas linhas que carregam um marcador. |

### Marcadores de evento (coluna `markers`)

Os valores possíveis, alinhados à amostra mais próxima do instante do evento:

| Marcador | Momento |
| --- | --- |
| `INICIO_CONTAGEM` | Início da aquisição / início da contagem regressiva (define `t0`). |
| `INICIO_MUSICA` | Início da reprodução do áudio. |
| `FIM_MUSICA` | Fim natural da faixa. |
| `PARADA_FORCADA` | Interrupção manual (botão Parar) ou por perda de conexão. |

> Cada marcador é anexado à primeira amostra cujo timestamp LSL seja maior ou igual ao instante do
> evento. As colunas `music_file` e `fator` acompanham a linha do marcador. Como todas as amostras
> e marcadores usam o mesmo relógio (`pylsl.local_clock()`), o alinhamento entre o áudio e o sinal
> é preciso.

## Logs

- Cada módulo grava em sua própria subpasta dentro de `logs/`. As categorias são: `connections`,
  `player`, `experiment`, `recorder`, `musics`, `config`, `gui`, `main`. Há um arquivo por
  execução, identificado por data e hora.
- O **`errors.log`** (fora da pasta `logs/`) reúne **somente** avisos e erros
  (`WARNING`/`ERROR`/`CRITICAL`) de toda a aplicação — é o primeiro lugar para olhar quando algo
  dá errado. O arquivo tem rotação automática de tamanho.

Você pode abrir a pasta de logs rapidamente pelo menu **Ajuda → Abrir pasta de logs**.

---

Anterior: [« Executando um experimento](running-an-experiment.md) · Próximo: [Solução de problemas »](troubleshooting.md)
