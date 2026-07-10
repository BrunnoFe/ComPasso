# Imagens da documentação

Coloque aqui os screenshots referenciados nas páginas de `docs/`. Cada ponto onde uma imagem é
esperada está marcado no conteúdo com um comentário HTML no formato:

```html
<!-- SCREENSHOT: descrição do que a imagem deve mostrar -->
```

## Capturas pendentes

- **index.md** — janela principal completa (barra de menu Experimento/Tema/Ajuda, stepper, player,
  gráfico do sinal em tempo real).
- **getting-started.md** — (nenhuma obrigatória).
- **bitalino-connection.md** — OpenSignals com o LSL ativado; barra de conexão no estado "Conectado".
- **experiment-menu.md** — barra de menus (incluindo a opção "Sair"); janela "Configuração do
  Experimento" com os campos preenchidos (incluindo os menus de coluna da planilha de fatores, o
  combobox de tipo de sensor e os sliders de tempo pré-estímulo/beep); menu Tema aberto mostrando
  as 6 paletas (Teal/Iris/Amber/Sereno/Aurora/Floresta).
- **input-files.md** — planilha de condições com as colunas `musica` e `fator`.
- **bitalino-connection.md** — OpenSignals com o LSL ativado; barra de conexão no estado
  "Conectado"; combobox "Sensor" aberto mostrando as 6 opções (EDA/ECG/EMG/EOG/EEG/EGG).
- **running-an-experiment.md** — janela principal completa; player com "GRAVANDO" e chip de
  condição; 📈 **cartão do gráfico do sinal em tempo real durante uma gravação** (linha se
  formando + ponteiro + chip de tempo visíveis — um GIF curto comunica melhor a fluidez);
  `dados_da_execucao.xlsx` aberto mostrando as colunas n/áudio/fator/volume/intervalo.
- **output-data.md** — exemplo de arquivo de dados (CSV/XLSX) aberto.

Ao adicionar uma imagem, substitua o comentário correspondente por, por exemplo:

```markdown
![Descrição](assets/images/nome-do-arquivo.png)
```
