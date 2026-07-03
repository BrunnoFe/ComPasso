# Changelog

Todas as mudanças notáveis deste projeto são documentadas neste arquivo, seguindo o formato
[Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).

## [2026.2.0] - 2026-07-02

### Adicionado
- Tela de carregamento (loading screen) ao abrir o app.
- Sistema de temas em tempo de execução: 3 paletas de cores (Teal/Iris/Amber) selecionáveis
  pelo menu "Tema", com preferência persistida entre execuções.
- `StepperFrame`: indicador visual das 4 etapas do experimento (Conectar → Participante →
  Arquivos → Iniciar), atualizado em tempo real.
- Ajuste automático do volume do sistema na inicialização do app.
- Frame principal com rolagem (`CTkScrollableFrame`) e tamanho mínimo de janela definido.
- Suíte de testes automatizados (`pytest`), cobrindo conexão/watchdog do BITalino, gravação,
  classificação de condições, validação de MAC, formatação, caminhos e lógica de botões —
  substituindo o notebook manual de testes usado anteriormente.

### Corrigido
- Bug na troca de tema em tempo de execução.
- Ícones da tela de carregamento e da janela de configurações de experimento.
- Bug de dimensionamento no frame superior (conexão).
- Bugs na barra de menu ("Experimento"/"Tema").
- Problemas de nomenclatura (variáveis/identificadores) no código da GUI.
- Correções diversas de bugs (commit `bcd157c`, sem detalhamento adicional disponível no
  histórico de commits).

### Melhorado
- Reformulação visual geral da interface (frames superior, central e inferior; novos
  fábricas de widgets estilizados em `widgets.py`).
- Logo e ícones do app atualizados.
- `README.md` reescrito: banner, badges de status, seção de Releases e formatação geral.

### Removido / Interno
- API de playlist morta removida de `Player` (`play_playlist`/`stop_playlist`/`set_playlist`/
  `is_playing`/`is_paused`) — não havia uso real no app.
- Refatoração e limpeza de código morto em `src/gui/assets.py`.
- Infraestrutura de testes adicionada (`pytest.ini`, `requirements-dev.txt`).
- Notebook manual de testes (`tests/tests.ipynb`) removido, substituído pela suíte pytest.
- Ajustes em `compasso.spec` (arquivo de versão do Windows, ícones) e `.gitignore`.

## [2026.1.0] - 2026-06-29

Primeiro release com tag publicado do ComPasso.
