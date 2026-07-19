# 📁 Arquivo de configuração `.config`

Cada configuração de experimento é salva como um arquivo **`.config`**, que é um **JSON** simples.
Os arquivos ficam, por padrão, em:

```
Documentos/ComPasso/Configurações do Experimento/
```

Eles são criados e editados pelo [menu Experimento](experiment-menu.md) (Novo / Editar) e nunca
são versionados no repositório — pertencem ao ambiente de cada pesquisador.

## Schema

O arquivo contém a versão do schema (`config_version`), sete campos **obrigatórios** e seis campos
**opcionais** (ausentes em `.config`s antigos → caem no valor padrão, sem quebrar a leitura):

| Chave | Tipo | Descrição |
| --- | --- | --- |
| `config_version` | inteiro | Versão do schema do arquivo (atualmente `1`). |
| `music_folder` | string | Caminho da pasta com os arquivos de áudio. |
| `music_quantity` | inteiro ≥ 1 | Quantidade esperada de músicas. |
| `noise_quantity` | inteiro ≥ 0 | Total de reproduções de ruído na sessão. |
| `factors_file` | string | Caminho da planilha `.xlsx`/`.xls` de condições. |
| `data_save_path` | string | Pasta onde os dados da sessão serão gravados. |
| `bitalino_channel` | string | Canal ativo do sensor: `A1` a `A6`. |
| `bitalino_mac` | string | Endereço MAC do BITalino (`XX:XX:XX:XX:XX:XX`). |

### Campos opcionais 🆕

| Chave | Tipo | Padrão | Descrição |
| --- | --- | --- | --- |
| `sensor_type` | string | `"ECG"` | Tipo de sensor do BITalino: `EDA`/`ECG`/`EMG`/`EOG`/`EEG`/`EGG`. Define a unidade e a escala do eixo Y do gráfico — veja [Conexão com o BITalino](bitalino-connection.md#-tipo-de-sensor). |
| `music_column` | string | `"musica"` | Nome da coluna da planilha de fatores com o nome dos áudios. |
| `factor_column` | string | `"fator"` | Nome da coluna da planilha de fatores com a condição/fator. |
| `pre_stimulus_seconds` | inteiro 5–120 | `5` | Duração da contagem regressiva antes de cada faixa. |
| `beep_enabled` | booleano | `false` | Liga/desliga o beep de aviso antes de cada faixa. |
| `beep_lead_seconds` | inteiro 1–10 | `1` | Quantos segundos antes da faixa o beep toca (deve ser **menor** que `pre_stimulus_seconds`). |

## Exemplo

```json
{
  "config_version": 1,
  "music_folder": "C:\\Users\\pesquisa\\musicas",
  "music_quantity": 10,
  "noise_quantity": 3,
  "factors_file": "C:\\Users\\pesquisa\\condicoes.xlsx",
  "data_save_path": "C:\\Users\\pesquisa\\Documents\\ComPasso\\Dados",
  "bitalino_channel": "A1",
  "bitalino_mac": "AA:BB:CC:DD:EE:FF",
  "sensor_type": "ECG",
  "music_column": "musica",
  "factor_column": "fator",
  "pre_stimulus_seconds": 5,
  "beep_enabled": true,
  "beep_lead_seconds": 1
}
```

## Como os valores são usados

- `music_folder`, `factors_file`, `data_save_path`, `bitalino_channel` e `bitalino_mac` preenchem
  automaticamente os campos correspondentes na janela principal quando a configuração é aplicada.
- `noise_quantity` define o **total de reproduções de ruído** distribuídas na playlist da sessão
  (veja [Executando um experimento](running-an-experiment.md)).
- `music_quantity` é **validado** (deve ser ≥ 1), mas o experimento reproduz **todas** as músicas
  encontradas e mapeadas — cada música aparece uma vez na playlist, independentemente desse número.
- `music_column`/`factor_column` só precisam ser diferentes de "musica"/"fator" se a sua planilha
  usar outros nomes de coluna — veja [Arquivos de entrada](input-files.md).
- `sensor_type` **não converte** o valor do sinal gravado (que continua bruto); afeta apenas a
  unidade exibida e a janela padrão da escala do eixo Y do gráfico.
- `beep_lead_seconds` só é aplicado se `beep_enabled` for `true`, e é validado como **menor** que
  `pre_stimulus_seconds` ao salvar (senão o beep nunca soaria antes do fim da contagem).

> **Nota:** `config_version` refere-se à versão do **formato do arquivo `.config`**, e não à
> versão do aplicativo ComPasso.

## Preferências do aplicativo (`prefs.json`)

Separado dos `.config`, o ComPasso mantém um arquivo `prefs.json` na pasta de dados do aplicativo
(`<app-data>/ComPasso/prefs.json`) para lembrar:

- `last_config` — o caminho do último `.config` salvo/aberto (usado para a carga automática).
- `theme` — a paleta de tema selecionada (Teal/Iris/Amber/Sereno/Aurora/Floresta).

---

Anterior: [« Configurações do App](app-settings.md) · Próximo: [Arquivos de entrada »](input-files.md)
