# ARCHITECTURE.md — ComPasso

Detalhes de arquitetura, módulos e funcionalidades. Referenciado por `CLAUDE.md` (que mantém só o
que precisa ser lido a cada sessão: regras imutáveis, convenções, gotchas). Leia a seção relevante
antes de mexer no módulo correspondente.

> A GUI foi migrada de CustomTkinter para **PySide6/QML** (`src/compasso/gui_qt/`); o antigo
> `src/compasso/gui/` foi removido. O **core (`compasso.core`) não mudou** nessa migração — as
> seções sobre ele abaixo continuam valendo tal como estão.

## Arquitetura (o que está onde)

```python
main.py                      ← entry; main_logger; chama compasso.gui_qt.executar_app(versao)
src/compasso/utils/
  configs.py                 ← ENCODING_FORMAT, APP_NAME ("ComPasso"), LOG_FORMAT
  paths.py                   ← get_documents_dir/get_app_data_dir/get_data_dir/get_logs_dir/
                                get_errors_log_path/ensure_app_dirs (Documents via SHGetKnownFolderPath
                                no Windows; app-data por SO — LOCALAPPDATA/Application Support/XDG)
  bootstrap.py               ← bootstrap(): cria pastas + handler WARNING+ no logger raiz
  sys_logs.py                ← SetLogger(namelogger, category)
  validation.py / formatting.py
  version.py                  ← get_app_version(): lê a versão do app via importlib.metadata
                                (pyproject.toml é a fonte única — ver "Versionamento e release"
                                no CLAUDE.md); usado por main.py no lugar do antigo hardcode
  resources.py                ← base_recursos(): raiz dos data-files empacotados, AGNÓSTICA de
                                empacotador (PyInstaller via _MEIPASS, Nuitka via __file__/
                                __compiled__, dev via árvore do repo). Consumido por gui_qt/
                                assets.py e gui_qt/app.py (nunca usar _MEIPASS direto — ver CLAUDE.md)
  __init__.py                ← chama bootstrap() AUTOMATICAMENTE na importação; exporta tudo
src/compasso/core/  (__init__ instancia os loggers e exporta a API — INTOCADO pela migração de GUI)
  constants.py                ← constantes de domínio: MARKER_* (eventos), CONDITION_*/RUIDO_KEYWORDS,
                                SESSION_TIMESTAMP_FORMAT, TRACK_ORDER_MIN_WIDTH (literais puros, sem imports);
                                SENSOR_DEFAULT/SENSOR_TYPES/SENSOR_GRAPH_PARAMS (unidade/escala do
                                gráfico por tipo de sensor do BITalino — ver seção própria abaixo)
  bitalino_connect.py        ← connectar_bitalino(mac)->StreamInlet|str (resolve_byprop por MAC);
                                ConnectionWatchdog (thread daemon); LSL_RESOLVE_TIMEOUT/LSL_PULL_TIMEOUT
  player.py                  ← Player (QtMultimedia): load/play/stop/aguardar_fim(timeout)/is_busy/
                                get_pos/get_length ; play_beep() (QMediaPlayer dedicado, pré-carregado
                                no arranque — canal paralelo, não interrompe a faixa) ;
                                SondaDuracao (pré-varre a duração dos áudios, assíncrona)
  recorder.py                ← LSLRecorder (aquisição→CSV em tempo real + XLSX) ; build_session_dirname(ctx),
                                build_track_filename(ordem, total, nome), _sanitize ; on_sample opcional
                                (chamado por amostra, thread de aquisição — alimenta o gráfico em tempo real)
  experiment.py               ← ExperimentRunner (orquestra a sessão em thread) ; _classify_condition ;
                                _esperar_ate(alvo) (espera por INSTANTE absoluto, não por passos) ;
                                PLOT_LEAD_SECONDS/_plot_active/_plot_begin/_plot_push/_plot_end/_plot_reset
                                (orquestração do gráfico do sinal — ver seção própria abaixo); grava
                                dados_da_execucao.xlsx (n/audio/fator/volume/intervalo, 1 por sessão,
                                regravado a cada faixa); beep opcional no t-X (com marcador BEEP)
  musics.py                  ← scan_music_files(folder) ; match_conditions(files, xlsx,
                                music_column="musica", factor_column="fator") ; MissingConditionError
  updates.py                 ← verificar(versao)->Resultado | ErroVerificacao (GitHub /releases/latest
                                via urllib) ; eh_mais_nova/partes_versao (comparação NUMÉRICA) ;
                                RELEASES_URL
  fake_bitalino.py            ← BITalino simulado: stream LSL com o sinal do SENSOR escolhido no
                                canal escolhido, em grade de tempo absoluta. GeradorSinais (estado
                                + eventos por sensor), publicar_amostras, iniciar/parar_simulador,
                                canal_valido/sensor_valido — ver seção própria abaixo
  audio.py                   ← set_system_volume/get_system_volume (multiplataforma: pycaw/osascript/amixer)
  config_manager.py          ← persistência dos arquivos `.config` (JSON), prefs.json (tema +
                                DEFAULT_GRAPH_SETTINGS/get_graph_prefs/set_graph_prefs); chaves opcionais
                                music_column/factor_column, beep_enabled/beep_lead_seconds, sensor_type,
                                calibration_enabled/calibration_audio
  app_prefs.py                ← preferências do APP (≠ protocolo do experimento): schema de 20 chaves
                                (padrão/tipo/faixa), validar/obter/definir/restaurar_padroes,
                                PREFS_SCHEMA_VERSION + _migrar, obter_geometria/definir_geometria
                                (estado da janela, FORA do schema), resumo_para_log/escrever_ambiente
                                (rastreabilidade) — ver seção própria abaixo
  calibration.py              ← lógica pura da calibração de volume (sem GUI/hardware): constantes
                                (CALIB_VOL_MIN/MAX_DEFAULT, CALIB_STEP_PCT_*, CALIB_STEP_SEG_*,
                                CALIB_DIFF_MAX, CALIB_HOLD_SEGUNDOS) e validar_parametros/
                                numero_de_incrementos/duracao_estimada_segundos/volume_no_incremento
                                — ver seção "Calibração de volume" abaixo
src/compasso/gui_qt/  (__init__ instancia gui_logger; expõe executar_app)
  app.py                      ← executar_app(versao): sobe QGuiApplication + QQmlApplicationEngine,
                                cria Context/Theme, registra GraficoSinal (qmlRegisterType) e todos os
                                controllers como propriedades de contexto do QML, carrega qml/Main.qml;
                                _montar_carregador() (fila de etapas do arranque) e
                                _limpar_logs_antigos() — ver "Carregamento em etapas" abaixo
  carregamento.py             ← Carregador(QObject): fila de etapas do arranque com progresso reativo
                                (rotulo/progresso/ativo), etapas síncronas + de espera (com condição
                                e timeout) — consumido por SplashOverlay.qml
  context.py                  ← Context(QObject) ← HUB de estado reativo (ver abaixo)
  theme.py                    ← Theme(QObject) singleton: cores/métricas/fontes reativas ao QML
                                (Property com notify); setTheme(nome) troca em runtime SEM rebuild
  palettes.py                 ← dados puros: 6 paletas (Teal/Iris/Amber/Sereno/Aurora/Floresta),
                                METRICS (raios/alturas/paddings), FONTS (famílias por plataforma)
  assets.py                   ← ASSETS_DIR (resolve `assets/` em dev e via `sys._MEIPASS` quando
                                congelado) + ICON_FILENAME/ICON_PNG_FILENAME/BEEP_FILENAME (a logo
                                não é mais um arquivo de imagem — ver `LogoMark.qml` abaixo)
  signal_chart.py             ← GraficoSinal(QQuickPaintedItem): gráfico do sinal em tempo real,
                                desenhado com QPainter (ver seção própria abaixo)
  controllers/                ← QObjects "backend": um Slot por ação da UI, Property/Signal para
                                estado reativo. Cada view QML liga-se a um controller por nome de
                                propriedade de contexto (ex.: `connController`, `filesController`).
    connection_controller.py  ← ConnectionController: conectar/desconectar BITalino, watchdog,
                                canal/sensor (equivale ao antigo ConnectionFrame)
    participant_controller.py ← ParticipantController: form/resumo do participante, validação,
                                rascunho editável (rascunhoNome/Idade/Genero)
    files_controller.py       ← FilesController: seleção de pasta de músicas/condições/saída,
                                varredura+casamento em thread, contadores do rodapé
    player_controller.py      ← PlayerController: volume (debounce por QTimer), progresso da
                                faixa (QTimer), indicador de gravação, botão calibrar
    experiment_controller.py  ← ExperimentController + validar_prerequisitos(ctx) (função pura,
                                testada em tests/test_button_state_logic.py): comecar/parar/continuar
    app_controller.py         ← AppController: ações do menu Ajuda/Sair, sinais de pedido de
                                janela (pedirNovoConfig/pedirGraphSettings/...)
    graph_settings_controller.py ← GraphSettingsController: estado reativo das 8 configurações do
                                gráfico + preview ao vivo + persistência (ver seção própria abaixo)
    calibration_controller.py ← CalibrationController: máquina de estados da calibração de volume
                                (idle/base/calibrar/salvar) + rampa por QTimer (ver seção própria)
    config_controller.py      ← ConfigController: editor do .config (Novo/Editar), abrir .config
                                do disco, apply_config(data) — mapeia os valores para o Context
    app_settings_controller.py ← AppSettingsController: estado reativo das preferências do app,
                                validação/persistência via core/app_prefs, portão da aba Avançado
                                e aviso "requer reinício" (ver seção própria abaixo)
  qml/
    Main.qml                  ← janela raiz: AppMenuBar + MainContent + FooterView + SplashOverlay +
                                diálogos/janelas auxiliares, dentro do frame borderless (ver abaixo)
    AppWindow.qml              ← frame de janela reutilizável: borderless, cantos arredondados,
                                TitleBar embutida, redimensionamento pelas bordas, transição
                                animada de maximizar/restaurar (minimizar é direto, sem animação) —
                                usado por Main.qml E pelas 3 janelas em windows/ (ver "Janelas
                                (chrome)" abaixo)
    TitleBar.qml               ← barra de título custom (arrasto, min/max opcional/fechar),
                                generalizada (título/ícone customizáveis) para ser reusada por
                                qualquer AppWindow, tingida pela paleta
    AppMenuBar.qml             ← menus Experimento/Configurações/Tema/Ajuda (substitui CTkMenuBar)
    components/                ← Card, Caption, AppButton, GhostButton, AppTextField, AppComboBox,
                                AppSlider, AppSwitch, Equalizer, FormSection (seção de formulário
                                c/ título+divisor), LogoMark (logo do ComPasso desenhada em QML —
                                Canvas, sem arquivo de imagem), Dica (hovertip), MessageDialog,
                                ConfirmDialog, SplashOverlay — blocos reutilizáveis, todos lidos de
                                `Theme` (`CollapsibleCard.qml` foi removido: só tinha um usuário,
                                virou `CartaoConfig.qml` — ver "Cartão único" abaixo)
    views/                     ← ConnectionView, StepperView, CartaoConfig (Participante +
                                Arquivos & Dados, cartão único — ver seção própria abaixo),
                                PlayerBarView, FooterView, SignalChartView, MainContent
                                (composição/scroll)
    windows/                   ← ExperimentConfigWindow, GraphSettingsWindow, CalibrationWindow,
                                AppSettingsWindow (preferências do app, 6 abas) — cada uma é um
                                `AppWindow` modal próprio, aberto sob demanda
tests/                        ← suíte pytest (ver seção Testes em CLAUDE.md)
scripts/
  fake_bitalino.py             ← wrapper CLI fino sobre core/fake_bitalino.py (ver "Ferramenta de
                                desenvolvimento" abaixo)
  generate_version_info.py     ← gera version_info.txt a partir de pyproject.toml antes do build
                                (ver BUILD.md e RELEASE.md, seção "Versionamento e release")
  build_nuitka.py              ← build alternativo com Nuitka (onefile ~71 MB, 3x menor que o
                                PyInstaller); invoca o Nuitka direto com os --include-* que a
                                análise estática não descobre (ver BUILD.md, "Build alternativo")
```

## Context — o hub (src/compasso/gui_qt/context.py)

Um único `QObject` criado em `executar_app`, exposto ao QML via `setContextProperty("ctx", ...)`
e passado a **todo** controller. Equivalente Qt do antigo `AppContext`.

- **Estado (atributos Python simples, lidos/escritos pelos controllers e pelo core)**: `player`,
  `bitalino` (inlet|None), `mac_addr`, `signal_channel`, `sensor_type` (EDA/ECG/EMG/EOG/EEG/EGG,
  default ECG), `runner`, `nome/idade/genero`, `infos_saved`, `music_folder`, `conditions_file`,
  `music_files`, `music_condition_mapping`, `music_column`/`factor_column` (default "musica"/
  "fator"), `save_dir`, `watchdog` (ConnectionWatchdog|None), `beep_habilitado`/
  `beep_antecedencia_segundos`/`beep_caminho`, `config_loaded`, `config_atual`/`config_path`
  (última configuração aplicada — usados por "Editar"), `calibracao_habilitada`/
  `calibracao_caminho`, `volume_calibrado`/`volume_travado` (ver "Calibração de volume" abaixo).
- **Propriedades reativas (`Property` + `Signal` notify)** — o QML faz *binding* direto, sem
  `.set()`/`.get()` manual: `statusText`, `currentMusicText`, `currentConditionText`, `volumeText`,
  `timeBeginText`/`timeEndText`, `musicDoneText`/`musicTotalText`, `ruidoDoneText`/`ruidoTotalText`,
  `sessionProgress`, `sessionStatusText`, `buttonState`, `experimentUiLocked`, `connected`,
  `participantEditable`, `cardsCollapsed`, `calibrarVisible`, `stepperSteps` (lista `{rotulo,
  concluida, atual, pendente}`, calculada em `_calcular_etapas()`), `sensorType`, `configLoaded`,
  `macAddr`, `signalChannel`.
- **Camada de compatibilidade com o core** (`_instalar_camada_compatibilidade`, chamada no
  `__init__`): reexpõe a superfície do antigo `AppContext` sobre as `Property` acima, para que
  `ExperimentRunner`/`ConnectionWatchdog` (que esperam `.set()`/`.get()` e callbacks registrados)
  rodem **sem nenhuma alteração**. `ctx.status_text` etc. viram instâncias de `_VarReativa`
  (`.set(valor)` escreve na `Property` correspondente e dispara o `notify`); `ctx.set_button_state`,
  `ctx.set_experiment_ui_lock` etc. viram closures que escrevem nas `Property` booleanas.
- `ctx.notify_stepper()` agenda o recálculo/emit de `stepperChanged` na thread da GUI — chame após
  qualquer mudança que afete os pré-requisitos (configuração carregada, conexão, infos salvas,
  arquivos mapeados, calibração de volume salva).
- **Threading**: `ctx.run_after(fn)` emite um sinal Qt (`_agendar`) conectado com
  `Qt.QueuedConnection` a um slot que executa `fn()` na thread da GUI — substitui `root.after(0,
  fn)` do Tk; seguro chamar de qualquer thread. `ctx.run_async(work, on_done)` roda `work()` numa
  `threading.Thread(daemon=True)` e entrega o resultado via `run_after` (exceções em `work()` viram
  o `result` passado a `on_done`) — mesmo contrato de antes, implementação trocada.

## Theme — singleton de tema (src/compasso/gui_qt/theme.py + palettes.py)

Substitui o antigo esquema de `compasso.gui.theme` (reescrita de globais de módulo +
`_rebuild_ui`). `Theme(QObject)` expõe `colors`/`metrics`/`fonts` (dicts, `Property("QVariant", ...,
notify=changed)`) e `nome`/`nomes`/`ehClaro`. O QML lê `Theme.colors.accent` etc. em *bindings*
normais; **`setTheme(nome)` troca a paleta ativa e emite `changed` uma vez** — todos os *bindings*
dependentes se reavaliam sozinhos, **sem reconstruir nenhum widget**. Isso elimina a necessidade da
antiga regra "só trocar tema com a app ociosa" (que existia só por causa do `_rebuild_ui`
destruindo/recriando toda a UI — não há mais rebuild, então não há mais estado a perder).
Persistência via `config_manager.get_theme_pref()`/`set_theme_pref()`, igual a antes.

## Janelas (chrome) — bordas, cantos arredondados, transições (AppWindow.qml + TitleBar.qml)

Todas as janelas do app (principal e as 3 auxiliares) são **frameless** (`flags: Qt.Window |
Qt.FramelessWindowHint`, `color: "transparent"`) com **cantos arredondados** e uma **barra de
título custom** — nenhuma usa a moldura nativa do SO.

- **`Main.qml`** monta o próprio frame diretamente (`Rectangle` com `radius: Theme.metrics.
  cornerCard`, `clip: true`, contendo `TitleBar` + `AppMenuBar` + conteúdo + `FooterView`) — é a
  única janela com menu de barra e rodapé.
- **`AppWindow.qml`** é o frame **reutilizável** para as janelas auxiliares
  (`ExperimentConfigWindow`/`GraphSettingsWindow`/`CalibrationWindow`): mesma estrutura de
  `Rectangle` arredondado + `TitleBar`, mas com uma área de conteúdo genérica
  (`default property alias conteudo`). `mostrarMax: false` esconde o botão maximizar em diálogos
  compactos (ex.: `CalibrationWindow`) que não fazem sentido maximizar.
- **`TitleBar.qml`** foi generalizada para servir aos dois: `titulo`/`mostrarIcone`/`mostrarMax`
  são propriedades (Main.qml usa o ícone + "ComPasso · versão"; `AppWindow` usa só o título da
  janela, sem ícone). Arrasto via `startSystemMove()`; os botões min/max/fechar chamam funções da
  janela dona (`janela.minimizarSuave()`/`janela.alternarMaximizar()`/`janela.close()`).
- **Cantos arredondados sincronizados**: o `radius` do frame, o `topLeftRadius`/`topRightRadius`
  da `TitleBar` e o `bottomLeftRadius`/`bottomRightRadius` do `FooterView` (só em `Main.qml`) são
  todos amarrados à mesma propriedade `maximizado` — viram `0` quando maximizada (senão os cantos
  ficariam arredondados numa janela que ocupa a tela toda) e voltam ao `Theme.metrics.cornerCard`
  ao restaurar. O botão de fechar também arredonda seu próprio canto superior direito
  (`topRightRadius: bar.raioCanto`) para acompanhar o canto da janela.
- **Maximizar/restaurar são EMULADOS com animação** (`alternarMaximizar()`): como a janela é
  frameless, não existe o gesto nativo suave do SO — em vez de chamar `showMaximized()` direto, a
  própria **geometria** (x/y/width/height) é animada (`ParallelAnimation`, **`Theme.metrics.
  animJanelaMs` = 220 ms, `OutQuint`**) até a área útil da tela
  (`Screen.desktopAvailableWidth/Height`) e de volta à geometria salva em `geomAnterior`.
  `OutQuint` reage no primeiro quadro e desacelera longo no fim: parece **mais rápida** que o
  `InOutQuart`/320 ms anterior mesmo durando menos, porque o `InOut` gastava o início acelerando —
  e é o início que o olho lê como resposta ao clique. Menos quadros também significa menos reflow
  do conteúdo por transição.
  *Gotcha*: em multi-monitor isso pode não respeitar o monitor onde a janela está.
  *Gotcha 2*: `animJanelaMs` vive em `METRICS`, mas `Theme._escalar` **exclui chaves terminadas em
  `Ms`** da escala da UI — escalar tempo junto com tamanho deixaria as transições lentas a 150%,
  que não é o que "interface maior" significa.
- **Minimizar**: `minimizarSuave()` (nome mantido pelo contrato com a `TitleBar`) chama
  `win.showMinimized()` e nada mais — a animação de encolher para a barra de tarefas é do próprio
  Windows (DWM). **Não tente "melhorar" mexendo no estilo nativo da janela**: já foi tentado
  reativar `WS_MINIMIZEBOX`/`WS_SYSMENU` via `SetWindowLong` (ctypes) partindo da premissa de que
  janelas frameless não animam, e o efeito foi o **inverso** — a animação, que funcionava, parou de
  acontecer; o código foi removido. Animar a geometria em QML também não serve: o Windows restaura
  a janela instantaneamente, então a volta ficaria sem animação (assimetria impossível de esconder).
- Redimensionamento pelas bordas: `Repeater` de `MouseArea`s finas (5px) nas laterais/base
  chamando `startSystemResize(lado)` — replicado em `Main.qml` e `AppWindow.qml`.

### Tamanho da janela e layout responsivo (min 600×400)

`Main.qml` abre no **tamanho preferido 1300×720** (`Theme.metrics.winPrefWidth/winPrefHeight`),
mas encolhe para caber se a tela do usuário for menor — `width`/`height` iniciais são
`Math.max(winMin, Math.min(winPref, Screen.desktopAvailable...))`. O **mínimo absoluto é 600×400**
(`winMinWidth`/`winMinHeight`), permitindo abrir/usar o app em monitores pequenos.

- **Cuidado com os nomes** em `palettes.py`: `winPrefWidth/winPrefHeight` = 1300×720 (abertura);
  `winMinWidth/winMinHeight` = 600×400 (mínimo). Antes `winMinWidth` valia 1300 e era usado como
  abertura **e** mínimo — código que assuma isso deve passar a usar `winPrefWidth`.
- Como o `MainContent` só rola na **vertical** (`contentWidth: availableWidth`), qualquer linha que
  exija mais largura que a janela seria **cortada** (não há scroll horizontal). Por isso as três
  linhas naturalmente largas têm **layout responsivo** por breakpoint (lendo a própria `width`):
  - **`ConnectionView`** (`compacto: width < 860`): larga = uma linha (logo · MAC · canal · sensor
    ···· [Conectar] à direita, empurrado por um espaçador `fillWidth`); compacta = os campos quebram
    num `Flow` e o estado de conexão (`EstadoConexao`) desce para baixo. As duas montagens (larga e
    compacta) usam os **mesmos** componentes inline (`GrupoMac`/`GrupoCanal`/`GrupoSensor`/
    `EstadoConexao`) e compartilham o estado via a propriedade `view.macDigitado` (+ ctx/
    controllers), então **não há duplicação de dados** entre elas — só uma fica `visible` por vez.
  - **`StepperView`** (`compacto: width < 1180`): larga = as etapas numa fileira com conectores
    (`RowLayout`→ na verdade um `Flow` com `spacing: 0`); compacta = o `Flow` quebra em várias linhas
    e os **conectores somem** (`visible: !compacto`, pois só fazem sentido numa fileira única).
  - **`CartaoConfig`** (`compacto: width < 760`): largo = duas colunas (participante | divisor
    vertical | arquivos) com o cabeçalho de dois títulos; compacto = as seções **empilham** numa
    coluna só (`GridLayout` com `columns: compacto ? 1 : 3`), o divisor vira **horizontal**
    (`fillWidth`/altura 1) e cada seção mostra seu **próprio título** (`TituloCard` com
    `visible: compacto`) — o cabeçalho de dois títulos some (`visible: !compacto`).
- Ao mexer nessas views, **preserve o layout largo intacto** (é o caso comum) e teste em ~600px de
  largura para garantir que nada corta. `scripts/fake_bitalino.py`/`COMPASSO_FAKE_BITALINO=1`
  permitem abrir a GUI e redimensionar sem hardware.

## Diálogos (MessageDialog/ConfirmDialog) e hovertips (Dica.qml)

`components/MessageDialog.qml` (1 botão OK, tipo `"warning"`/`"info"`) e
`components/ConfirmDialog.qml` (`confirmado`/`recusado`, botões `textoSim`/`textoNao`
configuráveis — usados como Sim/Não por padrão, e Sim/Reiniciar na calibração) compartilham o
**mesmo layout padronizado**: badge circular de ícone ("!" vermelho para aviso, "i"/"?" no acento
para info/confirmação) + título + corpo + rodapé com o(s) botão(ões) à direita — antes cada um
tinha um layout ligeiramente diferente.

- **Terceira via opcional no `ConfirmDialog`**: `textoAlternativo` + sinal `alternativo` criam um
  botão entre "recusar" e "confirmar", visível **só quando o texto é preenchido** — os diálogos de
  duas opções que já existiam seguem idênticos. Usado pelo aviso de conexão em modo de teste
  (Sim / Desabilitar teste / Cancelar). A propriedade `carga` transporta um dado até a resposta
  (ex.: o MAC a conectar), para quem abre o diálogo não precisar manter estado paralelo.
- **Ações destrutivas/irreversíveis pedem confirmação** — padrão já usado por "Parar experimento";
  estendido nesta sessão para **"Desconectar" o BITalino**
  (`ConnectionController.solicitar_desconectar()` emite `pedirConfirmarDesconectar`, tratado em
  `Main.qml` abrindo um `ConfirmDialog`; só o `Slot desconectar()` de fato encerra a conexão, agora
  chamado só após confirmar).
- `CalibrationWindow` **fecha automaticamente** após o usuário confirmar o volume ótimo
  (`CalibrationController.resolver_salvar(True)` emite `fecharJanela`, tratado em
  `CalibrationWindow.qml` com `win.close()`) — antes a janela ficava aberta esperando um fechamento
  manual mesmo depois de já ter salvo.
- **Hovertips**: `components/Dica.qml` é um `ToolTip` temático (cores da paleta, delay 450ms),
  usado via a propriedade `dica` de `AppButton`/`GhostButton` (`dica: "texto..."` — vazio = sem
  tooltip). Todo botão/combo/switch também ganha cursor de mãozinha
  (`HoverHandler { cursorShape: Qt.PointingHandCursor }`, já embutido nesses componentes).

## Indicador de progresso (stepper) — src/compasso/gui_qt/qml/views/StepperView.qml

Data-driven: `StepperView.qml` apenas itera `ctx.stepperSteps` (lista calculada em
`Context._calcular_etapas()`) com um `Repeater` — não há mais reconstrução imperativa de widgets.

- **Etapas** (nesta ordem): **Configurações** (`ctx.config_loaded`) → **Conectar**
  (`ctx.bitalino is not None`) → **Participante** (`ctx.infos_saved`) → **Arquivos**
  (`ctx.music_condition_mapping` e `ctx.save_dir` preenchidos) → **Calibragem** (só aparece se
  `ctx.calibracao_habilitada`; concluída quando `ctx.volume_calibrado is not None`) → **Começar**
  (concluída enquanto `ctx.buttonState` é `"rodando"` ou `"continuar"` — ou seja, fica verde
  durante o experimento em andamento; antes disso, é a etapa atual/pendente como as demais). Sem
  calibração habilitada, "Começar" é a 5ª etapa; com calibração, é a 6ª. `Context._set_button_state`
  reemite `stepperChanged` a cada troca de estado, para o stepper reavaliar junto.
- **Cores**: etapa concluída → verde (`Theme.colors.accent`) com "✓"; etapa **atual** (a primeira
  ainda não concluída) → destacada em `accent`/"AGORA"; qualquer outra etapa pendente (ainda não
  concluída e não é a atual) → **vermelha** (`danger`/`danger_tint`, rótulo "PENDENTE"). O
  vermelho é o sinal visual de "ainda falta fazer isso" — não trocar por uma cor neutra.
- Cada `{rotulo, concluida, atual, pendente}` já vem pré-calculado do `Context`; o QML só
  colore/rotula por *binding*, sem lógica de estado própria. **Todo lugar que muda um dos estados
  acima precisa chamar `ctx.notify_stepper()`** — incluindo `ConfigController.apply_config`
  (config carregada/aplicada) e `PlayerController.aplicar_volume_calibrado` (calibração salva),
  além dos pontos já existentes (conexão, infos do participante, arquivos mapeados).
- **Layout responsivo, com DOIS contêineres para o mesmo delegate**: em janelas largas as etapas
  ficam numa `Row` **centrada** no cartão (sobra folga igual nas duas pontas); em janelas estreitas
  (`width < 1180`) um `Flow` quebra em várias linhas e os conectores somem. Só um dos dois recebe
  modelo por vez (`model: view.compacto ? [] : ctx.stepperSteps` e o inverso), e o delegate é um
  `Component` único compartilhado. A separação existe porque **`Flow` não tem alinhamento** (sempre
  encosta à esquerda): centralizar o próprio `Flow` exigiria amarrar a largura dele ao conteúdo, e
  como o conteúdo do `Flow` depende da largura para saber onde quebrar, isso vira laço de binding.
  Ver "Tamanho da janela e layout responsivo" na seção "Janelas (chrome)".

## Menu "Experimento"/"Configurações"/"Tema"/"Atualizações"/"Ajuda" (AppMenuBar.qml + config_controller.py)

Barra de menu custom (`qml/AppMenuBar.qml`), tingida pela paleta — substitui o `CTkMenuBar`.
Cinco cascatas: **Experimento** (Novo/Abrir/Editar/Sair — os três primeiros desabilitados durante
o experimento via `ctx.experimentUiLocked`, "Sair" sempre habilitado), **Configurações** (App… e
Gráfico…),
**Tema** (lista `Theme.nomes`, marca com "✓" o ativo), **Atualizações** (ver seção própria) e
**Ajuda** (abrir pasta de logs / página do projeto / site do projeto). Cliques emitem sinais no
`AppController` (`pedirNovoConfig`/`pedirAbrirConfig`/`pedirEditarConfig`/`pedirGraphSettings`) que
`Main.qml` conecta à abertura das janelas correspondentes (`ExperimentConfigWindow.qml`,
`GraphSettingsWindow.qml`). `BotaoMenu` tem `notificar` (ponto vermelho sobre o título).

Na ponta direita da barra fica o **`ThemeToggle.qml`** — atalho claro/escuro. Mostra o *destino*,
não o estado: sol no tema escuro, lua no claro. Os ícones são desenhados em `Canvas` (acompanham
a cor do tema por binding, nítidos em qualquer DPI, sem asset novo no bundle); a lua usa
`destination-out` para o recorte da crescente — desenhar o segundo disco na cor do fundo falharia
sobre o realce de hover. `Theme.alternarClaroEscuro()` **retoma o último tema usado de cada
família** (`_ultimo_claro`/`_ultimo_escuro`, semeados do tema ativo no arranque; padrões em
`palettes.TEMA_CLARO_PADRAO`/`TEMA_ESCURO_PADRAO`): saindo de Iris para o claro e voltando,
volta-se a Iris — o botão é atalho, não substitui o menu Tema.

Cada `.config` é um JSON (`CONFIG_VERSION`, campos em `REQUIRED_KEYS`: `music_folder`,
`music_quantity`, `noise_quantity`, `factors_file`, `data_save_path`, `bitalino_channel` (A1–A6),
`bitalino_mac`; `OPTIONAL_KEYS` com default para `.config`s antigos: `pre_stimulus_seconds`,
`music_column`/`factor_column`, `beep_enabled`/`beep_lead_seconds`, `sensor_type`,
`calibration_enabled`/`calibration_audio`) salvo em `Documentos/ComPasso/Configurações do
Experimento/` (`EXPERIMENT_FILES_DIRNAME`). `validate_values`/`load_config` retornam mensagens de
erro específicas por campo (em português, exibidas via `MessageDialog`). `load_config` retorna a
tupla `(data, erros)` — `ConfigController.abrir_arquivo` desempacota os dois. O `ExperimentConfigWindow.qml`
(editor Novo/Editar) grava/lê esses arquivos via `ConfigController.salvar()`; "Editar" só é aceito
com uma configuração já carregada e pede confirmação (`ConfirmDialog`) antes de sobrescrever.
`ConfigController.apply_config(data, caminho)` é o ponto único que mapeia os valores para o
`Context` (equivalente ao antigo `ComPasso.apply_config`) — usado tanto por "Abrir" quanto por
"Salvar" no editor. Se `music_folder`+`factors_file` vierem preenchidos, `apply_config` também
dispara `FilesController.revarrer()` para casar músicas↔condições (sem isso, carregar um
`.config` preenchia os caminhos mas não fazia o casamento — só selecionar os caminhos manualmente
pela UI disparava).

**Carga automática do último `.config` no arranque**: `ConfigController.carregar_ultima()`
(chamada em `app.py` logo depois de instanciar os controllers) lê `config_manager.
get_last_config_path()` e aplica via `apply_config` se o arquivo ainda existir e for válido —
falha silenciosa (só loga) se o `.config` foi movido/apagado. `apply_config` chama
`config_manager.set_last_config(caminho)` toda vez que aplica um config (Abrir/Salvar/auto-load),
mantendo o ponteiro sempre atualizado em `prefs.json["last_config"]`.

## Saída de dados e logs (paths resolvidos em src/compasso/utils/paths.py)

*(Inalterado pela migração de GUI — lógica 100% em `compasso.core`/`compasso.utils`.)*

- Dados: `Documentos/ComPasso/Dados/` (`DATA_DIRNAME`; default do diálogo "Escolher"). **Uma pasta
  por sessão de coleta**, nome `nome_idade_genero_dia-mes-ano_hora-min-seg` (criada uma vez ao
  iniciar). Dentro dela, **um par CSV+XLSX por faixa**, nome `ordem_nomedamusica` (ordem 1-based na
  playlist, com zero à esquerda — largura mín. 2; extensão do áudio removida). Ex.: `01_minha_musica.csv`.
  Também **uma `dados_da_execucao.xlsx` por sessão** (colunas `n, áudio, fator, volume, intervalo`
  — ver "Fluxo do experimento" acima), regravada por inteiro a cada faixa concluída.
- Logs: `<app-data>/ComPasso/logs/<categoria>/<categoria>_<ts>.log`, uma por execução. Categorias
  atuais: `connections`, `player`, `experiment`, `recorder`, `musics`, `config`, `gui` (agora
  `guiQtLogger`, categoria `gui`), `main`.
- `<app-data>/ComPasso/errors.log`: só WARNING/ERROR/CRITICAL de tudo (handler no logger raiz,
  rotativo). `bootstrap()` cria as pastas na 1ª execução.
- `<app-data>/ComPasso/logs/full/full.log`: **consolidado, TODOS os níveis de TODOS os módulos**
  (handler DEBUG no logger raiz, rotativo 5 MB × 5 backups, `delay=True`) — coexiste com os
  arquivos por categoria e o `errors.log`, não os substitui. Cada linha traz `[%(session)s)]`
  (`LOG_FORMAT` em `configs.py`): o nome da pasta da sessão de coleta em curso, ou `"-"` fora de
  uma coleta — carimbado via `logging.setLogRecordFactory` (`bootstrap.py`), lido de
  `utils/log_context.py` (`definir_sessao`/`limpar_sessao`/`sessao_atual`; thread-safe).
  `ExperimentRunner._executar_sessao`/`_finish` chamam `definir_sessao`/`limpar_sessao` — correlaciona
  linhas de recorder/experiment/player de uma mesma coleta no `full.log`. Loggers de terceiros
  excessivamente verbosos (`comtypes`, da camada COM do pycaw) são elevados a WARNING em
  `bootstrap._silenciar_terceiros_ruidosos` para não afogar o consolidado.
- CSV/XLSX colunas (ordem exata): `timestamp, signal, markers, music_file, fator`.
  `markers` ∈ {`INICIO_CONTAGEM`, `INICIO_MUSICA`, `FIM_MUSICA`, `PARADA_FORCADA`} (constantes
  `MARKER_*` em `constants.py`) na amostra mais próxima do evento; `music_file`/`fator` são
  gravados em toda linha com marcador (não só no `INICIO_MUSICA`). `signal` = `sample[signal_channel]`.

## Fluxo do experimento (ExperimentRunner)

### Agendamento por instantes absolutos (não por passos)

**A regra mais importante desta seção.** A contagem regressiva já foi um laço de
`time.sleep(1.0)`. Cada volta custava `1.0 s + ε` (o SO nunca acorda exato, e havia um
`_post_status` cruzando threads no meio), então um beep configurado para "t-5" tocava em
`5 × (1.0 + ε)` antes do áudio — erro que crescia com o número de esperas e deixava a sessão
visivelmente dessincronizada. **Nunca reintroduzir contagem por passos acumulados.**

Hoje, no início de cada faixa, calculam-se os três instantes de uma vez, todos derivados de
`t_audio` (o início do estímulo é a referência do experimento):

```text
t_audio   = t0 + pre_stimulus_seconds
t_beep    = t_audio - beep_antecedencia_segundos
t_grafico = t_audio - PLOT_LEAD_SECONDS
```

Os eventos são ordenados por instante e cada espera usa `_esperar_ate(alvo)`, que recalcula o
restante do relógio a cada volta (`_stop_event.wait(min(restante, 0.05))`) — o erro se corrige
sozinho em vez de acumular. **Nada entre a espera e o disparo do evento**: postar status ou ler
o volume do SO ali vira atraso direto sobre o alvo (por isso `get_system_volume()` foi movido
para depois do `play()`). Medido com hardware real: erro sub-milissegundo no intervalo
beep→áudio, idêntico na 1ª e na 20ª faixa (`tests/test_experiment_timing.py`).

### Ordem dentro de `_run_track`

1. **`player.load(path)` ANTES da aquisição** — `load()` bloqueia (até 10 s) com latência
   variável; rodá-lo depois de `t0` jogava essa variação para dentro da janela cronometrada.
   A duração vem de `ctx.duracoes_audio` (pré-varrida no scan por `SondaDuracao`), com
   `player.get_length()` como fallback.
2. `recorder.start()` → `t0` → marcador `INICIO_CONTAGEM`.
3. Laço de eventos (gráfico / beep / áudio) por instante absoluto. No beep: carimba
   `local_clock()`, chama `play_beep()` e grava o marcador **`BEEP`** — o offset real passa a
   ser auditável no CSV, o que antes não era.
4. Fim da faixa por **sinal `EndOfMedia`** (`player.aguardar_fim(duração + margem)`), não por
   polling — o antigo laço de 200 ms atrasava o `FIM_MUSICA` e, com ele, a âncora do eixo X.
5. **`recorder.stop()` ANTES de `_plot_active = False`**: `stop()` faz join na thread de
   aquisição, então quando retorna todas as amostras já chegaram ao gráfico. Fechar o portão
   antes descartava a cauda ainda em trânsito no LSL e deixava um vão no fim do traço.

`_run_experiment` envolve tudo num `try/except/finally` que sempre chama `_finish()`: esta
thread não tem supervisor, e uma exceção escapando a matava em silêncio, deixando
`_running=True` e a UI travada sem nenhum sinal ao usuário.

### Fim natural da coleta e rearme para a próxima

Quando a última faixa termina, `_finish()` dispara `ctx.on_session_completed` (via `run_after`) →
`ExperimentController.coletaFinalizada` → `Main.qml` mostra "Coleta de dados finalizada!" num
`MessageDialog` próprio, cujo `onClosed` chama `ExperimentController.preparar_nova_coleta()`.

O callback **só dispara no fim natural**: está dentro do `if not self._stop_event.is_set()`, então
uma sessão interrompida pelo usuário não avisa nem rearma (ele parou por algum motivo; reconfigurar
a tela por baixo dele seria hostil). `preparar_nova_coleta()` zera participante, calibração (destrava
o slider e apaga a etapa do stepper), gráfico (`reset_idle`), contadores/tempos/progresso e o
`runner`. **Mantém** o BITalino conectado e os arquivos/`.config` carregados: a próxima coleta
normalmente usa o mesmo material, trocando só o participante.

Botão **Começar** (`FooterView.qml`, dirigido por `ExperimentController.comecar()`) fica sempre
habilitado; a validação dos 6 pré-requisitos (`validar_prerequisitos(ctx)`, função pura em
`experiment_controller.py`, **nesta ordem**: `config_loaded` (config criada/aberta), bitalino
conectado, infos salvas, `music_files`, `save_dir`, sem sessão já em andamento) ocorre **no
clique**, mostrando uma mensagem (`MessageDialog`) se algo faltar. Ao iniciar:
`ExperimentRunner.start()` também recolhe os cartões Participante/Arquivos (via
`ctx.cardsCollapsed`, observado em *lockstep* por `MainContent.qml`) e trava o botão "▴/▾" e o
botão "Editar" do participante (`_set_experiment_ui_lock(True)` + `_set_participant_editable(False)`
— ver "Cartões retráteis" abaixo) — travas revertidas em `stop()` e `_finish()`. A playlist é
montada por `expand_playlist` (cada música 1×; ruídos distribuídos para totalizar
`noise_quantity`) e ordenada por `pseudo_random_order` (**ruído nunca em 1º e ≥2 músicas entre
ruídos consecutivos**, com melhor-esforço se infactível). Por faixa → `LSLRecorder.start()` (drena
buffer→t0), marca `INICIO_CONTAGEM`, rótulo do player mostra **"Preparando: {música}"** durante
toda a contagem (`ctx.pre_stimulus_seconds`, inclusive logo após o usuário clicar "Continuar →",
antes de a faixa seguinte começar), depois `INICIO_MUSICA`+play (rótulo passa a mostrar só o nome
da faixa), espera o `EndOfMedia`, `FIM_MUSICA`, finaliza arquivo; botão vai a
**"Continuar →"** e aguarda o usuário. **Parar** (`PlayerBarView.qml` → `PlayerController.parar()`)
pede confirmação (`ConfirmDialog`, "Tem certeza que deseja parar o experimento?") antes de abortar
(marca `PARADA_FORCADA`) — só quando `runner.is_running()`; sem runner ativo, para a reprodução
direto sem perguntar.

**Volume travado durante a faixa**: o slider de volume (`PlayerBarView`) fica desabilitado
(`playerController.volumeTravado`) enquanto `runner.is_acquiring()` (contagem + reprodução) —
reusa o `QTimer` de `_atualizar_progresso`; reabilita entre faixas. **Beep de aviso opcional**: se
`ctx.beep_habilitado`, toca `ctx.beep_caminho` (`assets/edit_beep_1000Hz.wav`, via
`Player.play_beep` — canal separado, não interrompe a música) no t-X da contagem regressiva
(`ctx.beep_antecedencia_segundos`, 1–10s, deve ser **menor** que o tempo de contagem — validado em
`config_manager.validate_values` e visualmente na janela de config). **Planilha de execução**: a
cada faixa concluída (ao clicar "Continuar →"), o runner grava/regrava `dados_da_execucao.xlsx` na
pasta da sessão com colunas `n, áudio, fator, volume, intervalo` (`volume` = volume do sistema no
instante do play; `intervalo` = segundos entre `FIM_MUSICA` e o clique em "Continuar", ambos via
`local_clock()`). Estados do botão principal: `comecar`/`rodando`(disabled)/`continuar` via
`ctx.buttonState`, trocado pelo runner via `ctx.run_after` (que escreve na `Property`). O
`StepperView` (ver "Indicador de progresso" acima) e o indicador "GRAVANDO"/chip de condição no
`PlayerBarView` refletem o mesmo estado em tempo real por *binding*.

## Dois relógios, não um: `time_correction()` (recorder.py)

**Armadilha central da sincronização.** O timestamp devolvido por `pull_sample()` **não** está
no mesmo domínio de `local_clock()`: ele vem do relógio de **quem envia** (o host do
OpenSignals), um cristal diferente do que alimenta o relógio local. Os dois derivam entre si.
O código tratava os dois como um só — e o `recorder.py` até documentava essa premissa falsa.

Sintoma medido em hardware real, numa sessão de 12 faixas: os marcadores da 1ª faixa saíam em
`0.01 / 4.00 / 5.00` e os da 12ª em `0.18 / 4.15 / 5.15`. Repare que **os intervalos internos
estavam corretos** em ambas (beep→áudio = 1.00 s); o que crescia era um deslocamento constante
aplicado a todos os marcadores da faixa — assinatura de deriva entre relógios, não de um
contador acumulando. Os ~0.173 s ao longo da sessão dão ~300 ppm, típico de dois cristais
independentes.

Correção: `LSLRecorder._atualizar_correcao_tempo()` consulta `inlet.time_correction()` — o
mecanismo que o próprio LSL oferece para isso — e cada amostra é convertida com
`ts = ts + self._correcao_tempo` antes de qualquer comparação. **É reconsultado
periodicamente** (`INTERVALO_CORRECAO_S = 5`): é a deriva, não o offset inicial, que causa o
acúmulo. Numa falha da consulta, mantém-se a última correção conhecida — zerá-la
reintroduziria de uma vez todo o deslocamento já compensado.

Regressão coberta em `tests/test_acquisition_sync.py` (inlet falso com relógio deslocado).

## Cartão único — Participante + Arquivos & Dados (CartaoConfig.qml)

Participante e Arquivos & Dados eram dois `CollapsibleCard.qml` lado a lado; como sempre
colapsavam **juntos**, viraram **um único `Rectangle`** (`qml/views/CartaoConfig.qml`) — um
cabeçalho com os dois títulos e um corpo em `RowLayout` (`participante | divisor | arquivos`),
proporção `_pesoPart:_pesoArq` = **3:2** (participante ocupa mais espaço). `CollapsibleCard.qml`
foi removido (só tinha esse único uso).

- **Cabeçalho**: os dois títulos ("Participante"/"Arquivos & Dados") ficam cada um flush à
  esquerda da sua seção, separados por um divisor vertical curto (mesmo padrão do divisor
  logo↔MAC na `ConnectionView`) — a separação visual se mantém mesmo com o card colapsado. O
  chevron (símbolo "❯", gira 90°/−90° com `Behavior on rotation`) fica **ancorado no canto
  superior direito do card** (fora do corpo retrátil, `z: 2`), não dentro do cabeçalho de um dos
  lados — assim sua posição não some/desloca quando o card recolhe.
- **Corpo retrátil**: um `Item` com `clip: true` cuja `height` anima entre `0` e
  `corpo.implicitHeight` via `Behavior on height` (mais `opacity` no layout interno) — mesmo
  padrão do antigo `CollapsibleCard`.
- **Layout responsivo** (`compacto: width < 760`): tanto o cabeçalho quanto o corpo são
  `GridLayout` com `columns: compacto ? 1 : 3`. Largo = duas colunas + divisor vertical (como
  acima). Compacto = participante e arquivos **empilham** numa coluna só, o divisor entre eles vira
  **horizontal** (`fillWidth`/altura 1) e cada seção mostra seu **próprio título** (`TituloCard`
  com `visible: compacto`), enquanto o cabeçalho de dois títulos some (`visible: !compacto`) — isso
  mantém cada título junto do seu conteúdo quando empilhado. Ver "Tamanho da janela e layout
  responsivo" na seção "Janelas (chrome)".
- **Lado do participante**: a coluna usa `implicitHeight: formulario.implicitHeight` fixo — o
  formulário (Nome/Idade/Gênero + "Salvar informações") e o resumo pós-salvamento (avatar + nome +
  "idade · gênero" + "Editar", tudo centralizado) são **sobrepostos** (`anchors.fill`/
  `anchors.centerIn` no mesmo `Item`, alternando `opacity`/`visible` via `partController.salvos`)
  em vez de dois irmãos empilhados — isso garante que a altura ocupada pelo card **não muda** ao
  salvar/editar as informações.
- **Lado de arquivos**: as 3 `LinhaArquivo` (Músicas/Condições/Salvar em) ficam **agrupadas e
  centradas na vertical**. Os espaçadores internos têm teto (`Layout.maximumHeight: padMd`, mínimo
  `padSm`), então as linhas ficam próximas entre si; os das pontas continuam sem teto e absorvem a
  sobra, mantendo o grupo centrado. Sem o teto, `fillHeight` esticava os quatro por igual e as
  linhas se afastavam conforme a coluna vizinha (Participante) crescia.
- O diálogo "Salvar dados em" abre já na **pasta padrão de dados** das preferências
  (`FilesController.pastaDadosPadraoUrl` → `currentFolder`), quando houver uma definida.
- Um único `signal alternar()` recolhe/expande os dois lados juntos: `MainContent.recolherManual`
  (propriedade local) combina com `ctx.cardsCollapsed` (travado pelo `ExperimentRunner`) em
  `root.recolhido`, passado ao `CartaoConfig`. Quando o experimento trava a UI, um `Connections`
  em `MainContent.qml` sincroniza `recolherManual` com `ctx.cardsCollapsed` — o chevron também
  fica desabilitado (`enabled: !ctx.experimentUiLocked`) para impedir destravar manualmente
  durante a sessão.

## Gráfico do sinal em tempo real (signal_chart.py)

`GraficoSinal` (`src/compasso/gui_qt/signal_chart.py`) é um **`QQuickPaintedItem` nativo** (desenha
com `QPainter.paint`, registrado no QML via `qmlRegisterType(GraficoSinal, "Compasso", 1, 0,
"GraficoSinal")`) que desenha o sinal do BITalino conforme ele chega, sem travar a interface mesmo
em faixas longas. **Não usa QtCharts** — o `ChartView` do QtCharts trava (segfault) em alguns
ambientes (problema no caminho de render GL/scene-graph do QtCharts, não do restante da UI QtQuick,
que renderiza normalmente); `GraficoSinal` evita esse problema sendo leve e sem OpenGL. O item
recebe o `Context` via `contexto` (registra-se em `ctx.signal_plot`) e a paleta ativa via `paleta`
(dict passado pelo QML a partir de `Theme.colors`, recolorindo grade/linha/rótulos ao trocar de
tema). `SignalChartView.qml` é o cartão-fachada: cabeçalho com o rótulo do canal
(`grafico.canal`) e a leitura ao vivo (`grafico.leitura`).

- **Contrato com o `ExperimentRunner`** (mantido em inglês, mesmos 4 nomes de antes):
  `begin(duration_s, lead_s)`, `push(t, v)` (thread-safe — só enfileira sob lock, processado no
  próximo quadro), `end()`, `reset_idle()`, mais `apply_settings(dict)`.
- **Configurável em runtime**: `apply_settings(settings)` atualiza `escala_y` (µV),
  `suavizacao_ativa`/`janela_suavizacao` (colunas de exibição), `largura_linha`, `grade_visivel`,
  `rotulos_visiveis`, `value_mode` — ver seção "Menu Configurações → Gráfico" abaixo.
- **Taxa de quadros FIXA em 30 fps** (`_FPS`, não configurável — a opção foi removida do menu):
  a decimação já garante custo por quadro constante, então elevar o FPS só consumia mais CPU sem
  ganho visual. O `QTimer` roda **só entre `begin()` e `end()`**; antes girava 30×/s durante toda
  a vida do app, mesmo ocioso.
- **Janela do eixo X**: `PLOT_LEAD_SECONDS = 5` — o eixo vai **sempre de t-5 até o fim exato da
  faixa**, independentemente do tempo pré-estímulo configurado (que pode ser 120 s). A duração
  vem pré-varrida (`SondaDuracao`), então o eixo já nasce correto; `end(duracao_real)` é apenas
  correção fina (`_remapear_baldes`, que reescala as colunas sem guardar amostras cruas).
  `_plot_origin` é ancorado no **instante calculado** da abertura da janela, não na primeira
  amostra que chegar — ancorar na amostra deslocava o traço por até um intervalo de amostragem.
- **Relógio de exibição único** (`_tempo_exibicao`) rege ponteiro E revelação da linha juntos:
  avança ~1 s/s, ancorado à última amostra (nunca ultrapassa; nunca fica >0,4s atrás — absorve
  rajadas do LSL). Mesma lógica do antigo `signal_plot.py`, portada linha a linha.
- **Desempenho — decimação por coluna**: as amostras são consumidas **direto nos baldes** em
  `_drenar_pendentes` (`_COLUNAS_DECIMACAO=1400`, soma+contagem) e **descartadas**: as listas de
  amostras cruas foram eliminadas (custavam ~10⁶ floats numa faixa longa a 1000 Hz, só para
  permitir uma rebucketização que deixou de ser o caso comum). A fila entre a thread de aquisição
  e a da GUI tem `maxlen` (`_MAX_PENDENTES`): se a GUI estagnar, descarta-se o antigo em vez de
  crescer sem limite — o CSV é o dado primário, o gráfico é só exibição.
  A polilinha é **cacheada** (`_recalcular_pontos`, invalidada por `_cache_sujo`) e recortada por
  busca binária sobre `_colunas`; antes se refazia ordenação + média + 1400 `QPointF` a cada
  quadro, mesmo com o traço parado. `paint()` desenha no máximo ~1400 pontos — **custo constante
  independente da duração da faixa** (verificado com 120 mil amostras em `tests/test_graph.py`).
  **Nunca reintroduzir uma estrutura que cresça com o total de amostras no caminho de desenho** —
  foi exatamente esse padrão que travava a UI antiga perto do fim de músicas longas.
- **Eixo Y SEMPRE FIXO** na escala configurada (default ±30 µV) — **sem reescala automática pelos
  dados** (decisão explícita, não reintroduzir); marcas/linhas de grade fixas de **10 em 10 µV**
  por padrão (`_passo_y`, depende do sensor). Mudança de escala pelo menu (`apply_settings`,
  "Configurações → Gráfico") ignora `y_scale` enquanto `self._gravando` — só vale na **próxima**
  faixa.
- **Zoom +/- ao vivo do eixo Y** (`ampliar_zoom()`/`reduzir_zoom()`, `Slot`s): diferente do menu
  acima, **funciona DURANTE a gravação** — nudge de um passo (`_passo_y`) na escala, com clamp a
  `escala_min`/`escala_max` do sensor ativo (`_ajustar_escala`). Barato: só troca o fator de
  mapeamento em `paint()` e repinta — a decimação já guarda valores brutos, nada é reprocessado.
  Propriedades expostas ao QML: `escalaAtual`/`escalaMin`/`escalaMax`/`unidade`
  (`Signal escalaChanged`). `SignalChartView.qml` desenha dois botões discretos (+/-) perto do
  eixo — **numa `Item` irmã do `GraficoSinal`, nunca como filho dele** (ver gotcha em
  `CLAUDE.md`: dar filhos QML a um `QQuickPaintedItem` quebrou o repaint em tempo real da
  linha/ponteiro na prática).
- **Estado ocioso** (`_pintar_ocioso`, sem faixa ativa): desenha a **grade do eixo Y** + o texto
  "Aguardando gravação…". A grade existe aí para que o preview ao vivo da janela de configurações
  seja real: antes o item ocioso pintava só a mensagem, então mexer em escala/grade/rótulos
  parecia "não fazer nada" enquanto não houvesse gravação na tela.
- **Grade em temas claros** (`_cor_grade()`, quando `_eh_tema_claro()`): usa o `faint2` da própria
  paleta com opacidade baixa (`_ALFA_GRADE_CLARA`) — além de discreto, acompanha a temperatura do
  tema (frio no Sereno, quente no Aurora), o que um cinza neutro fixo não fazia. **Cada instante
  recebe UMA linha só**, da família de maior destaque a que pertence: desenhar as famílias de 1 s
  e de 5 s inteiras sobrepunha os múltiplos de 5, as transparências se compunham e a linha saía
  bem mais escura que o pretendido (medido: `#cdd0d4` sobre branco; hoje `#eff1f3`). A linha de
  **t0** continua com a cor `muted` (maior destaque) em qualquer tema — não remover.
- **Suavização**: média móvel leve (default 5 colunas, `_media_movel`, somas de prefixo O(n)) só na
  exibição — CSV/XLSX sempre bruto.
- **Estatísticas ao vivo**: Welford incremental (`_acumular_estatistica`) para média/desvio-padrão
  e mín/máx da janela da música (amostras com `t >= antecedência`); alimentam `leitura`
  (`_montar_leitura`, modos "raw"/"mean").
- **Marcas do eixo X em três pesos** (`_pintar_grade_x`): linha a cada **1 s** (mais apagada), a
  cada **5 s** (peso médio) e em **t0** (destaque). Cada família só é desenhada se suas linhas
  ficarem a ≥ `_ESPACO_MINIMO_LINHA_PX` umas das outras (numa faixa de 5 min as de 1 s virariam
  uma mancha).
- **Rótulos do eixo X nunca de 1 em 1** (`_PASSOS_ROTULO_X` começa em 5): rotular cada segundo
  fazia o eixo mudar de aparência conforme a duração — uma faixa de 18 s ganhava rótulo a cada
  1 s e uma de 30 s a cada 5 s, sem nada ter mudado no experimento. Sempre múltiplos de 5 s
  (coarsening para 10/15/30/60 quando não couber), o que também casa com as linhas de destaque
  médio. O último rótulo é o comprimento real da faixa, ancorado à direita; um rótulo regular só
  é suprimido quando os textos **de fato** se tocariam (largura medida com `QFontMetrics`) — a
  margem fixa e generosa de antes apagava rótulos legítimos (o "0:19" que sumia numa faixa de
  20 s).

## Menu "Configurações → Gráfico" (GraphSettingsWindow.qml + graph_settings_controller.py)

`GraphSettingsWindow.qml` (janela modal própria) ajusta as 7 chaves acima com **preview ao vivo**:
cada `Property` do `GraphSettingsController` (`yScale`, `smoothingEnabled`, `smoothingWindow`,
`lineWidth`, `gridVisible`, `labelsVisible`, `valueMode`) chama `_preview()` no *setter*, que
aplica em `ctx.signal_plot.apply_settings(...)` imediatamente. Persistidas em `prefs.json["graph"]`
via `config_manager.get_graph_prefs()`/`set_graph_prefs()` (mescla com `DEFAULT_GRAPH_SETTINGS` —
chave ausente/tipo errado cai no default; nunca mexe em `theme`/`last_config`). Slider de escala Y:
limites/passo do sensor ativo (`GraphSettingsController.yMin/yMax/yStep`, fracionário para mV, ex.:
±0,4 a ±3 passo 0,2), **desabilitado com sessão em andamento** (`sessaoAtiva`,
`ctx.runner.is_running()`). Botões Salvar/Restaurar padrões/Cancelar (`abrir()` tira um snapshot na
abertura; `cancelar()` reaplica esse snapshot ao gráfico sem persistir).

**`salvar()` adota o estado salvo como novo snapshot** — e isso não é detalhe. O botão Salvar
fecha a janela, e o `onClosing` da janela chama `cancelar()`: sem essa adoção, o snapshot de
abertura era reaplicado logo após salvar. As preferências ficavam corretas em disco, mas o
gráfico voltava ao estado anterior, e as alterações só "reapareciam" ao reabrir a janela (que
relê o que foi gravado). Regressão coberta em `tests/test_graph_settings.py`.

## Menu "Configurações → App" (AppSettingsWindow.qml + app_settings_controller.py + core/app_prefs.py)

**A regra que decide onde uma opção mora** (vale como critério do projeto):

> Se altera **o dado coletado ou o protocolo**, vai no `.config` — viaja com o experimento, fica
> registrado na pasta da sessão, é rastreável meses depois. Se altera **como o operador usa o app
> naquela máquina**, vai em `prefs["app"]`.

Isto importa porque o app é de pesquisa e distribuído publicamente: uma configuração global e
invisível que mude o dado é um pesadelo de reprodutibilidade. As poucas opções desta janela que
ainda tocam a coleta (faixa etária, palavras de ruído, volume inicial) ficam na aba **Avançado**,
atrás de um switch de consentimento explícito — e o consentimento **expira a cada abertura** da
janela, não fica ligado para sempre.

**`core/app_prefs.py`** — schema de 20 chaves, cada uma `(padrão, tipo, mínimo, máximo)`.
`validar(dict) -> (limpo, erros)` sempre devolve todas as chaves (inválida/ausente cai no padrão)
e mensagens acionáveis com valor recebido + faixa esperada; `definir()` persiste mesmo havendo
erros — uma preferência ruim não pode impedir o usuário de salvar as outras. Cache em memória
(`obter()` só lê o disco na 1ª chamada), pois os pontos de consumo chamam a cada uso.

Detalhes que não são óbvios:

- **Duas camadas de compatibilidade, de propósito.** O *merge por chave* de `obter()` resolve de
  graça o caso comum (chave nova numa versão futura cai no padrão). O `PREFS_SCHEMA_VERSION` +
  `_migrar()` fica reservado para o que o merge **não** resolve: renomear chave, mudar unidade,
  inverter a semântica de um booleano — sem o número gravado no arquivo, esses casos são
  indetectáveis depois do fato. **Não confundir** com `CONFIG_VERSION` (schema do `.config`) nem
  com a tag `vAAAA.M.P` (versão do app): são três números independentes.
- **`bool` é subclasse de `int`.** Sem a checagem explícita em `_validar_valor`, `True` passaria
  por um campo numérico e viraria `1`. Coberto em `tests/test_app_prefs.py`.
- **Geometria da janela fica FORA do schema** (em `prefs["janela"]`, via `obter_geometria`/
  `definir_geometria`): é **estado**, não preferência. Dentro do schema, "Restaurar padrões" moveria
  a janela do usuário — o que ninguém espera. Geometrias absurdas (< 200×150, monitor que sumiu)
  são descartadas na leitura, senão a janela reabriria inutilizável.
- **Rastreabilidade.** `escrever_ambiente()` grava `ambiente.json` **na pasta da sessão** (prefs
  efetivas + sensor/canal/pré-estímulo/`.config` usado) e `resumo_para_log()` loga só o que difere
  do padrão. O log rotaciona e fica na máquina; o `ambiente.json` viaja com os CSVs — é ele que
  responde "com que ajustes esta coleta rodou?".

**Aplicação a quente vs. reinício.** O que dá para aplicar na hora é aplicado ao salvar; o resto
está em `app_prefs.REQUEREM_REINICIO` (`escala_ui`, `nivel_log`, `retencao_logs_dias`) e a janela
mostra o aviso em vez de fingir que já valeu. Os timeouts de LSL/watchdog **não** aparecem em
`_aplicar_a_quente()` de propósito: são lidos de `app_prefs` a cada nova conexão e a cada novo
watchdog, então já valem sozinhos. `escala_ui` exige reinício porque `Theme.metrics`/`Theme.fonts`
são `constant=True` no QML (nenhum *binding* as reavalia) — ao contrário da paleta, que é reativa.

**Onde cada preferência é consumida** (nenhuma é um switch morto):
`auto_carregar_config`/`verificar_atualizacoes`/`volume_inicial`/`controlar_volume_sistema`/
`nivel_log`/`retencao_logs_dias` em `app.py` (etapas do carregamento); `splash_minimo_ms` e
`confirmar_saida_em_experimento`/`abrir_maximizado`/`lembrar_geometria` no QML (`SplashOverlay`/
`Main.qml`); `escala_ui` em `theme.py` (`_escalar`); `formato_timestamp_sessao` em
`recorder.build_session_dirname`; `extensoes_audio` em `musics.scan_music_files`; `gerar_xlsx` em
`recorder.finalize` **e** no `dados_da_execucao.xlsx` de `experiment.py`; `lsl_timeout_s` em
`connectar_bitalino`; `watchdog_timeout_s` no `__init__` do `ConnectionWatchdog`; `idade_minima`/
`idade_maxima` em `participant_controller`; `palavras_ruido` em `_classify_condition`;
`pasta_dados_padrao` no `currentFolder` do diálogo de saída (`FilesController.pastaDadosPadraoUrl`).

**Faixa etária.** O padrão de fábrica passou de 18–100 para **0–120**: a trava antiga impedia, sem
aviso, qualquer coleta com crianças e adolescentes. `validar_idade(idade, minimo, maximo)` recebe a
faixa por argumento — `compasso.utils` continua puro, sem importar `compasso.core` (seria ciclo);
quem conhece as preferências é o chamador. A mensagem de erro cita a faixa **configurada**, não a
de fábrica, senão o usuário conferiria um limite que não é mais o dele.

> **Testes:** `tests/test_app_prefs.py` (schema/validação/persistência/geometria/rastreabilidade) e
> `tests/test_app_settings_controller.py` (parsing das listas, reinício, ciclo abrir/cancelar).
> Uma fixture `autouse` em `conftest.py` fixa os padrões em memória — sem ela, a suíte leria o
> `prefs.json` REAL da máquina e passaria ou falharia conforme os ajustes de quem a roda.

## Carregamento em etapas (carregamento.py + SplashOverlay.qml)

Antes, todo o trabalho pesado do arranque rodava **antes** de `engine.load()`: a janela só aparecia
depois de tudo pronto e a splash era decorativa — um temporizador fixo de 2,6 s sobre uma interface
que já estava utilizável. Agora esse trabalho é uma fila de etapas executadas **depois** que o QML
carregou, e a splash mostra a etapa e o progresso reais.

`Carregador` (QObject) expõe `rotulo`/`progresso`/`ativo` reativos e dois tipos de etapa:
**síncrona** (`adicionar`) e **de espera** (`adicionar_espera`), que pausa a fila até um sinal Qt,
com *condição de entrada* (pula na hora quando não há o que esperar — ex.: nenhuma planilha
carregada) e *timeout* de 6 s, para nenhuma espera poder travar o arranque para sempre. Cada etapa é
agendada com `QTimer.singleShot(0, ...)` para **devolver o controle ao laço de eventos entre elas** —
sem isso a splash congelaria. Uma etapa que falha só loga um warning e a fila segue (mesmo contrato
dos `try/except` que envolviam cada chamada em `app.py`).

A fila (em `app.py::_montar_carregador`) é: preparar áudio → diagnóstico (nível/retenção de logs) →
volume do sistema → sensor simulado → último `.config` → **esperar** a pré-varredura de durações. A
ordem importa: o áudio vem primeiro (mais caro, e o beep precisa estar pronto); o MAC do modo fake é
escrito **depois** do auto-load, senão o `.config` o sobrescreveria.

> **O que NÃO pode entrar nesta fila.** As preferências do gráfico são lidas **antes** do
> `engine.load()`, e não como etapa. O `GraficoSinal` lê `ctx.graph_settings` no instante em que o
> QML o cria (`signal_chart._set_contexto`) e **não relê depois**; adiar a leitura para a fila fazia
> o gráfico nascer com os defaults do sensor e só assumir as preferências salvas quando o usuário
> abrisse "Configurações → Gráfico" — que é o que as reaplica. Sintoma relatado: "começo uma coleta
> e o gráfico está no padrão; abro a janela de configurações e a aparência muda sozinha". Vale como
> critério geral: **qualquer estado que o QML leia na criação precisa existir antes do
> `engine.load()`** — a fila é para trabalho cujo resultado a UI consome depois. Há ainda uma rede
> de segurança logo após o load, que reaplica `ctx.graph_settings` ao gráfico se ele já existir.

A splash fecha por `!carregador.ativo && tempoMinimoCumprido` (piso configurável em
`splash_minimo_ms`, para o caso "tudo em cache" não virar um flash), não por tempo fixo, e continua
interceptando cliques enquanto carrega — é isso que impede o usuário de alcançar o "Começar" antes
de o beep estar pré-carregado.

**Ganho medido:** janela na tela de 1,14 s → **0,47 s**; tudo pronto em 1,32 s (antes: 2,6 s de
timer fixo). Parte disso veio de tornar **tardios os imports de `pandas`** (`musics.py`,
`recorder.py`, `experiment.py`, `config_controller.py`) — é o import mais caro da stack e era
alcançado por `from compasso.core import ...` no arranque. Os quatro precisavam sair juntos: deixar
um só no topo já pagava o custo inteiro.

## Planilha de condições (.xlsx / .xls)

*(Inalterado — lógica em `compasso.core.musics`.)*

Colunas: nome do arquivo (COM extensão) e fator/condição — nomes **configuráveis** via
`match_conditions(files, xlsx, music_column="musica", factor_column="fator")` (default reproduz o
comportamento antigo). No `ExperimentConfigWindow.qml`, ao escolher o arquivo de fatores
(`ConfigController.definir_fatores`) surgem dois `AppComboBox` com os cabeçalhos reais da planilha
(lidos via `pandas.read_excel(nrows=0)`); a validação de "colunas iguais"/"coluna inexistente"
acontece em `ConfigController._validar()` ao salvar (mensagem via `MessageDialog`, não mais borda
vermelha em tempo real — a lógica de bloqueio é a mesma). Sem correspondência →
`MissingConditionError` (avisa e aborta a verificação). Contadores classificam por palavra-chave no
valor do fator (`_classify_condition`, em `experiment.py`): "ruido"/"ruído"→ruído, demais→música.

## Tipo de sensor e escala do gráfico

*(Lógica de domínio inalterada — só o caminho de aplicação mudou.)*

`ctx.sensor_type` (EDA/ECG/EMG/EOG/EEG/EGG, default **ECG**) é escolhido num `AppComboBox` na
`ConnectionView` (travado após conectar, `enabled: !ctx.connected`) e espelhado no
`ExperimentConfigWindow.qml`/`.config` (`sensor_type`). `constants.SENSOR_GRAPH_PARAMS` mapeia cada
sensor para `unidade`/`padrao`/`minimo`/`maximo`/`passo` do eixo Y do gráfico — **só exibição**: o
dado gravado em CSV/XLSX continua **bruto**, sem conversão (decisão explícita — não reintroduzir
conversão de unidade sem pedido). Trocar o sensor **reseta a escala Y ao padrão do sensor**
(`ConnectionController.definir_sensor` → `GraficoSinal.aplicar_sensor(sensor, resetar_escala=True)`);
aplicar um `.config` salvo mantém a escala salva se estiver dentro dos limites do novo sensor
(`ConfigController.apply_config` → `aplicar_sensor(sensor, resetar_escala=False)`). O slider de
escala em `GraphSettingsWindow.qml` usa os limites/passo do sensor ativo
(`GraphSettingsController.yMin/yMax/yStep`).

**`padrao` == `maximo` para todos os sensores, de propósito.** O padrão de cada sensor é a escala
**mais ampla** que ele oferece, para que nenhum sinal saia da tela sem que ninguém tenha pedido.
Um padrão apertado corta picos legítimos (um artefato de piscada no EOG, uma resposta grande de
EDA) e o usuário vê um traço ceifado sem saber por quê. Apertar a escala é fácil e reversível pelos
botões +/- de zoom ao vivo; sair da tela por padrão, não. A contrapartida aceita: sinais pequenos
aparecem achatados no início (o EDA fica em ~4-5 µS numa escala de ±20), e o zoom resolve em dois
cliques. Regra derivada: **quando o dado não cabe na escala, amplie a escala — nunca encolha o
dado** (foi a correção pedida quando se tentou reduzir a amplitude simulada do EOG para caber).

**Escala e zoom ao vivo são o MESMO ajuste.** O slider da janela e os botões +/- do gráfico
escrevem no mesmo valor e ambos persistem: `_ajustar_escala` grava em `ctx.graph_settings` **e** em
disco (`config_manager.set_graph_prefs`). Antes só o slider persistia, então o zoom evaporava no
arranque seguinte e os dois controles pareciam discordar. A escala também pode ser alterada
**durante a gravação** pelos dois caminhos: bloquear o slider e liberar os botões era incoerente, e
mudar a escala é seguro a qualquer momento porque a decimação guarda valores **brutos** — a escala
só entra no mapeamento na hora de pintar, e nada do dado gravado depende dela. `apply_settings`
limita o valor a `[minimo, maximo]` do sensor: um `y_scale` salvo por outro sensor (ou editado à
mão no `prefs.json`) jogaria o traço para fora da tela.

## Verificação de atualizações (core/updates.py + updates_controller.py)

Compara a versão em execução com o último release **estável** publicado
(`api.github.com/repos/BrunnoFe/ComPasso/releases/latest` — o endpoint `/latest` já exclui
rascunhos e pré-releases). Usa `urllib` da stdlib: uma requisição GET não justifica dependência
nova, e o bundle do PyInstaller fica menor sem ela.

- **Comparação numérica por componente** (`eh_mais_nova`/`partes_versao`). Como texto,
  `"2026.10.0" < "2026.9.0"` — o app deixaria de avisar em outubro. Tem teste explícito.
- **Falha de rede nunca vira "não há atualização"**: `verificar()` levanta `ErroVerificacao`.
  Afirmar que está tudo em dia sem ter conseguido consultar seria mentir para o usuário.
- **Duas entradas, apresentações diferentes**: a **automática** roda uma vez no arranque (dentro
  da splash, via `ctx.run_async`) e é silenciosa — só acende o ponto vermelho no menu e troca o
  item para "Baixar atualização!". A **manual** (item de menu) abre o `UpdateDialog.qml` com anel
  girando e reticências animadas, e informa qualquer desfecho, inclusive a falha. Em nenhum dos
  dois o ponto vermelho é apagado por uma falha — não se sabe.
- O ponto vermelho **sobrevive ao "Cancelar"**: uma vez sabido que há versão nova, o menu segue
  sinalizando.

## Validação de entrada nos formulários

Cada regra vive no controller e é exposta como **mensagem pronta** (`""` = válido); a view não
repete nenhuma regra — a borda vermelha é apenas `erro !== ""`. Componentes: `AppTextField.erro`
/ `AppComboBox.erro` (borda `danger`, vence o foco) e `ErroCampo.qml` (label `s11` centralizado,
altura zero quando vazio, para o formulário não "pular").

| Campo | Propriedade | Quando aparece |
| --- | --- | --- |
| Colunas áudios/fatores iguais | `erroColunas` | imediato |
| Beep ≥ pré-estímulo | `erroBeep` | imediato |
| MAC fora do formato | `erroMac` | ao sair do campo ou no Salvar |
| Qtd. músicas / ruído | `erroMusicQuantity`/`erroNoiseQuantity` | ao sair do campo ou no Salvar |
| Faixa de volume da calibração | `erroVolumes` | ao sair do campo |

Combos e sliders avisam na hora (seleções discretas); campos de texto esperam o *blur* (`tocado`)
ou o clique em Salvar (`win.tentouSalvar`), senão o MAC ficaria vermelho durante toda a digitação.
O MAC reusa o **`MAC_RE` de `bitalino_connect.py`** — o que o campo aceita é exatamente o que o
botão Conectar aceita; antes eram regras independentes.

**Diálogos na janela certa**: `ExperimentConfigWindow` tem o seu próprio `MessageDialog` e a
conexão do `Main.qml` fica inativa enquanto ele está aberto (`enabled: !janelaConfig.visible`).
Como o editor é `ApplicationModal`, um diálogo aberto na janela principal ficava atrás dele,
bloqueado e inalcançável. `CalibrationWindow` já seguia esse padrão.

## Calibração de volume (opcional)

*(Fluxo/lógica de domínio inalterados — a máquina de estados e a rampa migraram de `after()` para
`QTimer`; ver `calibration_controller.py`.)*

Ajuda a achar o volume confortável para cada participante antes da sessão: toca uma faixa dedicada
enquanto o volume do sistema sobe em degraus (X% a cada X s) entre um mínimo e um máximo, até o
participante indicar que está bom. **Desabilitada por padrão.**

- **Habilitação**: switch + carregador de áudio (`.wav`/`.ogg`/`.mp3`) no
  `ExperimentConfigWindow.qml` (`calibration_enabled`/`calibration_audio`, chaves opcionais gated
  do `.config` — só validadas quando `calibration_enabled=True`, seguindo o mesmo padrão do beep de
  aviso). Quando habilitada, `PlayerBarView` mostra um botão "Calibrar Volume" abaixo do slider de
  volume (`playerController.calibrarVisivel`/`calibrarHabilitado` decidem visibilidade/estado —
  some se desabilitada, desabilita se não há sessão em andamento ou arquivo válido) e o stepper
  ganha a etapa "Calibragem" (ver "Indicador de progresso" acima).
- **Lógica pura em `core/calibration.py`** (sem GUI/hardware, testável, inalterada pela migração):
  `validar_parametros` (mín/máx 0–100, mín ≤ máx, diferença máx-mín ≤ `CALIB_DIFF_MAX`=40, passo %
  e intervalo em segundos 1–5), `numero_de_incrementos`/`duracao_estimada_segundos` (usada para
  **bloquear** o início se a faixa de calibração for mais curta que o teste — `mensagem` e não
  inicia, não toca em loop), `volume_no_incremento` (limitado ao máximo). Os parâmetros da rampa
  (mín/máx/passo%/intervalo) são **só defaults de sessão** — ajustáveis na própria
  `CalibrationWindow.qml`, **não** persistidos no `.config` (só o flag `calibration_enabled` e o
  `calibration_audio` são).
- **`CalibrationController`** (`calibration_controller.py`, estado consumido por
  `CalibrationWindow.qml`): fluxo em duas etapas — "Linha de Base" (demonstrativa, precisa concluir
  a rampa inteira) libera o botão "Calibrar"; "Calibrar" morfa para "Parar" (estilo *perigo*)
  durante a rampa — parar = volume confortável, o botão vira "Salvar"; "Salvar"
  (`pedir_salvar()`/`confirmarSalvar` sinal) pede confirmação via `ConfirmDialog`
  (textoSim="Sim"/textoNao="Reiniciar"). Rampa orquestrada por dois `QTimer` (rampa
  single-shot encadeado + progresso periódico) na thread da GUI (nunca thread separada); reusa
  `ctx.player` (instância única; sem conflito pois o botão "Calibrar" fica desabilitado
  durante o experimento). Fechar sem salvar restaura o volume do sistema ao valor de antes de abrir
  (`fechar()`).
- **Volume ótimo confirmado**: `ctx.aplicar_volume_calibrado(volume)` (registrado por
  `PlayerController.__init__`) aplica `set_system_volume`, reflete na `Property volume` e **trava-a**
  (`ctx.volume_travado=True`) pelo resto da sessão — `PlayerController._atualizar_progresso`
  estende a mesma trava usada durante a aquisição (`gravando or ctx.volume_travado`); também chama
  `ctx.notify_stepper()` para acender a etapa "Calibragem" no stepper. `CalibrationWindow` fecha
  sozinha ao confirmar (ver "Diálogos" acima).

## BITalino simulado (modo de teste, sem hardware/OpenSignals)

`core/fake_bitalino.py` publica uma stream LSL simulada para exercitar o app de ponta a ponta sem
BITalino nem OpenSignals. Deixou de ser só um utilitário de desenvolvimento: virou uma preferência
de primeira classe, com aviso na conexão e sinal fiel por tipo de sensor.

**Contrato de stream.** Um `pylsl.StreamOutlet` cujo `type` é o MAC normalizado (`normalizar_mac`,
aceita `:`/`-`/espaço) — exatamente o que `connectar_bitalino` resolve via
`resolve_byprop(prop='type', value=mac)`. 7 canais: índice 0 reservado (SEQ/digital) e 1-6 = A1-A6,
mesma convenção "A1 grava índice 1, **sem** subtrair 1" do resto do app.

**O sinal segue o SENSOR escolhido, não o número do canal.** No aparelho real quem determina o tipo
de sinal é o sensor plugado; o canal só diz onde ele foi plugado. A simulação faz igual: gera a
forma de onda de `ctx.sensor_type` e publica em `ctx.signal_channel`, com os demais canais em ruído
de fundo (entrada sem eletrodo). Sensor e canal são lidos **a cada amostra**, através de um
`provedor_config` injetado por quem sobe a stream — de propósito: os dois mudam em vários pontos da
GUI (combos da conexão, `apply_config` de um `.config`), e ler o estado atual é mais seguro que
lembrar de notificar o simulador em cada um deles.

**Sinais com dinâmica, não senoides paradas.** `GeradorSinais` tem estado e eventos aleatórios, com
as assinaturas que cada exame realmente mostra: SCRs no EDA (subida ~1 s, queda ~4 s — o evento que
este experimento procura), PQRST com variabilidade de frequência cardíaca no ECG, rajadas com
envelope suave no EMG, sacadas e piscadas no EOG, fusos de alfa no EEG e a onda lenta gástrica
(~0,05 Hz) no EGG. As amplitudes ficam nas unidades de `SENSOR_GRAPH_PARAMS`, e um teste amarra as
duas pontas: nenhum sensor pode estourar a própria escala padrão.

### Grade de tempo absoluta (a causa da dessincronização cumulativa)

**A parte mais importante deste módulo.** A primeira versão publicava assim:

```python
t = time.monotonic() - inicio
outlet.push_sample(gerador.amostra(t))   # sem timestamp
time.sleep(intervalo)                    # 1/100 s
```

Três defeitos encadeados, e o resultado eram marcadores chegando **cada vez mais tarde** ao longo
da sessão (medido: `INICIO_MUSICA` +0,93 s na 3ª faixa):

1. **Passo acumulado** — cada volta custava `intervalo + trabalho + granularidade do sleep`
   (~15,6 ms no Windows). A stream declarava 100 Hz e entregava 75–95 Hz, com a taxa passeando.
2. **Carimbo na hora do acordar** — `push_sample` sem `timestamp` faz o LSL carimbar quando o
   Python acordou, então o jitter do agendador virava jitter de timestamp. Um conversor real
   carimba no instante da **aquisição**.
3. **Dejitter enganado** — o inlet usa `proc_dejitter`, que regulariza os carimbos ajustando uma
   reta. Com um emissor de taxa errante a reta se descola do tempo real, e como o estado do ajuste
   vive no `StreamInlet` (que sobrevive a todas as faixas), o erro **acumulava faixa a faixa** em
   vez de zerar a cada arquivo.

`publicar_amostras` corrige seguindo a mesma regra que o `ExperimentRunner` já obedece — **instante
absoluto, nunca passo acumulado**: a amostra `n` pertence a `início + n/taxa` e é carimbada com
esse instante, independentemente de quando o Python conseguiu enviá-la. Atraso vira jitter de
entrega (o LSL absorve), não deriva de relógio. O sinal também é avaliado no instante *nominal*.
Atraso acima de `_ATRASO_MAXIMO_S` (1 s: suspensão do SO) **realinha a grade e loga um aviso**, em
vez de despejar milhares de amostras velhas. Medido depois: 100,000 Hz, intervalo 10,000 ms, zero
perdas e erro de marcador que **não cresce** entre faixas.

> **Limite de fidelidade conhecido.** Na coleta real são dois relógios e o app corrige com
> `inlet.time_correction()`. Como o simulador roda no mesmo processo, esse valor é ~0 e essa
> correção **não é exercitada** pelo fake. Injetar um deslocamento artificial seria pior: o
> `time_correction` mede a diferença real entre os endpoints LSL e devolveria 0, deixando o
> deslocamento sem correção — a simulação passaria a mentir em vez de exercitar.

### Como ligar, e a guarda na conexão

Três portas, todas convergindo para `fake_bitalino.iniciar()/parar_simulador()` (um simulador por
processo, com trava — duas streams com o mesmo `type` fazem a resolução LSL escolher uma delas de
forma imprevisível):

1. **Preferência** "Configurações → App → Geral → Simular BITalino" (`simular_bitalino`), que liga
   e desliga **em runtime** e pré-preenche `ctx.mac_addr` com o MAC simulado.
2. **Variável de ambiente** `COMPASSO_FAKE_BITALINO=1` (`COMPASSO_FAKE_BITALINO_MAC` sobrescreve o
   MAC), para scripts/CI — continua tendo a última palavra sobre o MAC.
3. **CLI standalone** — `python scripts/fake_bitalino.py [--mac ...] [--taxa ...]`, em processo
   separado.

Com o simulador no ar, `ctx.simulacaoAtiva` é verdadeiro e a UI de conexão muda de cara: o botão
vira **"Conectar (teste)" em vermelho** (`Theme.colors.danger` via `corFundo`/`corTexto` do
`AppButton`), e o clique passa por `ConnectionController.solicitar_conectar`, que intercepta e pede
confirmação em vez de conectar. O diálogo tem **três saídas** (`ConfirmDialog` ganhou um terceiro
botão opcional, visível só quando `textoAlternativo` é preenchido — os diálogos de duas opções que
já existiam seguem idênticos): *Sim* prossegue, *Desabilitar teste* chama
`AppSettingsController.desativar_simulacao()`, *Cancelar* desiste.

`desativar_simulacao()` **retorna o MAC que estava sendo simulado**, e isso não é detalhe: se o MAC
na tela era o do simulador, ele acabou de deixar de existir e conectar em seguida só produziria
"não foi possível conectar" sem explicar o porquê — nesse caso o QML mostra uma mensagem pedindo o
MAC do aparelho real, e só conecta direto quando o MAC é outro.

O motivo de toda essa cerimônia: conectar com o simulador ligado grava dados que **não são do
participante**. É um engano fácil (o modo fica ligado de uma sessão para a outra) e caro, porque só
se descobre com a coleta inteira já gravada.
