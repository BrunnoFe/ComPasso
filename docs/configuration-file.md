# 📁 Arquivo de configuração `.config`

Cada configuração de experimento é salva como um arquivo **`.config`**, que é um **JSON** simples.
Os arquivos ficam, por padrão, em:

```
Documentos/ComPasso/Configurações do Experimento/
```

Eles são criados e editados pelo [menu Experimento](experiment-menu.md) (Novo / Editar) e nunca
são versionados no repositório — pertencem ao ambiente de cada pesquisador.

## Schema

O arquivo contém a versão do schema (`config_version`) e sete campos obrigatórios:

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
  "bitalino_mac": "AA:BB:CC:DD:EE:FF"
}
```

## Como os valores são usados

- `music_folder`, `factors_file`, `data_save_path`, `bitalino_channel` e `bitalino_mac` preenchem
  automaticamente os campos correspondentes na janela principal quando a configuração é aplicada.
- `noise_quantity` define o **total de reproduções de ruído** distribuídas na playlist da sessão
  (veja [Executando um experimento](running-an-experiment.md)).
- `music_quantity` é **validado** (deve ser ≥ 1), mas o experimento reproduz **todas** as músicas
  encontradas e mapeadas — cada música aparece uma vez na playlist, independentemente desse número.

> **Nota:** `config_version` refere-se à versão do **formato do arquivo `.config`**, e não à
> versão do aplicativo ComPasso.

## Preferências do aplicativo (`prefs.json`)

Separado dos `.config`, o ComPasso mantém um arquivo `prefs.json` na pasta de dados do aplicativo
(`<app-data>/ComPasso/prefs.json`) para lembrar:

- `last_config` — o caminho do último `.config` salvo/aberto (usado para a carga automática).
- `theme` — a paleta de tema selecionada (Teal/Iris/Amber/Sereno/Aurora/Floresta).

---

Anterior: [« Menus](experiment-menu.md) · Próximo: [Arquivos de entrada »](input-files.md)
