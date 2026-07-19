# 🧪 BITalino simulado

Testa a interface inteira — conexão, gráfico, gravação, marcadores — **sem** um BITalino físico
nem o OpenSignals abertos. Útil para preparar um protocolo, dar manutenção no app ou gravar uma
demonstração.

## Como ligar

**Configurações → App → Diagnóstico → Simular BITalino** (desligado por padrão). É aplicado em
**runtime**, sem precisar reiniciar o app.

<!-- SCREENSHOT: checkbox "Simular BITalino" na aba Diagnóstico -->

Com o modo ligado, o botão **Conectar** da barra de conexão vira **"Conectar (teste)"**, em
vermelho. Ao clicar, um diálogo com três opções intercepta a ação — conectar em modo simulado
**grava dados que não são de um participante real**:

- **Sim** — conecta ao simulador e segue normalmente.
- **Desabilitar teste** — desliga a preferência e cancela a conexão.
- **Cancelar** — fecha o diálogo sem conectar.

## O que o simulador gera

- Uma stream LSL publicada localmente, encontrada pelo mesmo mecanismo de resolução por MAC que
  o BITalino real usa — o resto do app não sabe que é simulado.
- O sinal segue o **tipo de sensor** escolhido na barra de conexão (EDA/ECG/EMG/EOG/EEG/EGG) e é
  publicado no **canal** selecionado — os dois são lidos a cada amostra, então trocar de sensor ou
  canal em runtime também funciona no modo simulado.
- Eventos realistas por tipo de sensor (não senoides fixas): respostas de condutância no EDA,
  variabilidade de frequência cardíaca (PQRST) no ECG, rajadas musculares no EMG, sacadas/piscadas
  no EOG, fusos de alfa no EEG, onda lenta gástrica no EGG.
- Os demais canais analógicos recebem um ruído de fundo baixo, como uma entrada sem eletrodo.

> As amostras simuladas são carimbadas no instante **nominal** de cada amostra, não no instante em
> que a thread de publicação acordou — a mesma regra de agendamento por instante absoluto que vale
> para o resto do app (veja a seção "Regras imutáveis" do `CLAUDE.md`, se estiver desenvolvendo).

## Ferramenta de linha de comando (fora do app)

Para testar sem nem abrir a GUI: `python scripts/fake_bitalino.py` sobe a mesma stream simulada
como processo standalone. Útil para testes automatizados ou para deixar uma stream de teste no ar
enquanto se desenvolve outra parte do app.

---

Anterior: [« Conexão com o BITalino](bitalino-connection.md) · Próximo: [Menus »](experiment-menu.md)
