# Testes — Com Passo

Suíte em `pytest`. Nenhum teste toca hardware real (BITalino/LSL), rede ou diálogos de
arquivo; o hardware é substituído por *fakes* determinísticos.

## Como rodar

```bash
venv\Scripts\activate           # Windows
pip install -e ".[dev]"         # instala o pacote `compasso` (editável) + ferramentas de teste
pytest                          # a partir da raiz do repositório
```

Com cobertura:

```bash
pytest --cov=compasso --cov-report=term-missing
```

Configuração em [`pyproject.toml`](../pyproject.toml) (`[tool.pytest.ini_options]`):
`testpaths = ["tests"]`. **Não há `pythonpath`**: a descoberta do pacote `compasso` depende da
instalação editável (`pip install -e .`), por isso ela é obrigatória antes de rodar `pytest`.

## O que é coberto

| Arquivo | Foco |
| --- | --- |
| `test_acquisition_sync.py` | `LSLRecorder`: captura de `t0`, descarte de timestamps < t0, `ts−t0`, casamento marcador→amostra, canal, cabeçalho CSV, XLSX |
| `test_recorder_naming.py` | `_sanitize`, `build_track_filename` (zero-pad/largura/extensão), `build_session_dirname` |
| `test_mac_validation.py` | `MAC_RE` (bitalino_connect) + `MAC_REGEX` (config_manager); normalização e rejeição |
| `test_watchdog.py` | `ConnectionWatchdog`: dispara após TIMEOUT, não dispara em gaps curtos, ocioso/desconectado, não puxa amostra durante gravação |
| `test_config_manager.py` | `_is_int`, `validate_values`, round-trip salvar/carregar, preferências |
| `test_musics.py` | `scan_music_files`, `match_conditions`, `MissingConditionError` |
| `test_validation.py` / `test_formatting.py` / `test_classify_condition.py` | lógica pura (participante, MM:SS, ruído/música) |
| `test_audio_volume.py` | `set/get_system_volume` (Windows/macOS/Linux mockados, clamp, fallbacks) |
| `test_paths.py` | estrutura de pastas + `ensure_app_dirs` |
| `test_button_state_logic.py` | `experiment_controller.validar_prerequisitos` via ctx falso (sem renderizar GUI) |
| `test_graph.py` | `GraficoSinal` (QQuickPaintedItem): decimação por coluna, relógio de exibição, `reset_idle`, marcas/rótulos do eixo X sem sobreposição, grade discreta nos temas claros — sem renderizar de verdade (QGuiApplication headless) |
| `test_experiment_timing.py` | Agendamento da faixa por instantes absolutos: intervalo beep→áudio, alvo do áudio e **ausência de deriva ao longo de 20 faixas** (o bug de dessincronização cumulativa) |
| `test_graph_settings.py` | Preview ao vivo + persistência do menu Gráfico; regressão do "salvar e fechar reverte o gráfico" |
| `test_field_validation.py` | Regras de validação de campo (MAC, colunas iguais, quantidades, beep, faixa de volume) |
| `test_updates.py` | Verificação de nova versão: comparação **numérica** de versões, leitura da resposta do GitHub e os três desfechos do controller (sem tocar a rede) |
| `test_player_api.py` | Contrato de superfície do `Player` (mantém o backend *drop-in*) |

## Fakes e fixtures (`conftest.py`)

- **`FakeInlet`** — substitui `pylsl.StreamInlet`: separa buffer de *drain* (`timeout=0.0`)
  do *stream* de aquisição (`timeout>0`) e sinaliza fim via `on_exhausted`, permitindo
  encerrar o loop de aquisição de forma determinística, sem esperas reais.
- **`FakeClock`** — substitui `local_clock`/`time.monotonic`; pode avançar um passo fixo
  por chamada (usado para alcançar o TIMEOUT do watchdog em poucos ticks).
- **`make_factors_xlsx`** — gera um `.xlsx` de condições em `tmp_path` (nada commitado).
- **`valid_config_values`**, **`participant`** — dados de exemplo.

`local_clock`/`time` são *patchados no namespace do próprio módulo* (ex.:
`compasso.core.recorder.local_clock`), pois os módulos fazem `from pylsl import local_clock`.

## Deliberadamente NÃO coberto (e por quê)

- **`player.py`** (reprodução real de áudio via QtMultimedia) e **`connectar_bitalino` end-to-end**
  (resolução LSL real / rede) — dependem de hardware/áudio; apenas a lógica isolável
  (normalização de MAC, ramos de erro) é testada com mocks.
- **Renderização visual do QML** — alto esforço, baixo valor para uma ferramenta de
  pesquisa; testamos a lógica subjacente (controllers, `Context`, `GraficoSinal`) contra um `ctx`
  falso ou headless, sem carregar o engine QML.
- **Diálogos de arquivo / volume real do SO** — mockados.

## Efeito colateral conhecido

Importar `compasso.core`/`compasso.utils` cria arquivos de log em app-data (infraestrutura de
logging do próprio app, via `bootstrap()`), não dados de teste. Os testes não escrevem
DADOS fora de `tmp_path`.
