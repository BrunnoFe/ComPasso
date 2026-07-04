# 🔌 Conexão com o BITalino

A comunicação com o BITalino é feita **inteiramente via Lab Streaming Layer (LSL)**, publicado
pelo OpenSignals. O ComPasso não faz varredura Bluetooth: ele localiza a *stream* LSL pelo
**endereço MAC** informado.

## Antes de abrir o programa

A conexão **só funciona** se o OpenSignals estiver compartilhando os dados via LSL. Faça isto
**antes** de conectar no ComPasso:

1. Abra o **OpenSignals (r)evolution**.
2. Ative a opção **Lab Streaming Layer (LSL)** nas configurações de integração.
3. Coloque o dispositivo em modo de aquisição/streaming (*play* do OpenSignals), de forma que o
   BITalino esteja transmitindo amostras.

<!-- SCREENSHOT: OpenSignals com a opção Lab Streaming Layer (LSL) ativada -->

> Sem o LSL ativo e transmitindo, a conexão falha com uma mensagem de erro (a resolução da stream
> tem timeout de ~2 segundos).

## Conectando pela interface

Na barra de conexão (topo da janela):

1. **Endereço MAC** — digite o endereço do BITalino no formato `XX:XX:XX:XX:XX:XX`. São aceitos
   os separadores `:`, espaço ou `-` (ex.: `AA:BB:CC:DD:EE:FF`, `AA BB CC DD EE FF`).
2. **Canal** — selecione o canal do sensor cujo sinal será gravado, de **A1 a A6** (padrão: A1).
3. Clique em **Conectar**.

Em caso de sucesso, o botão dá lugar a um indicador **"● Conectado"** com um pequeno equalizador
animado, e um botão **Desconectar** fica disponível. Os campos de MAC e de canal ficam travados
enquanto a conexão estiver ativa.

<!-- SCREENSHOT: barra de conexão no estado "Conectado" com o equalizador animado -->

### O que acontece internamente

Ao conectar, o ComPasso:

- Resolve a stream LSL cujo `type` corresponde ao MAC informado (timeout de 2 s).
- Aplica processamento de sincronização de relógio, *dejitter* e monotonização aos timestamps.
- Registra no log a taxa nominal (`nominal_srate`) e o número de canais anunciados. Se a taxa for
  **0 (irregular)**, um aviso é registrado — configure a taxa de aquisição (ex.: 100 Hz) no
  próprio OpenSignals, pois o *dejitter* não suaviza timestamps de taxa irregular.
- Puxa uma amostra de verificação para confirmar que há fluxo de dados.

> **Sobre o canal:** a seleção "A1"–"A6" grava diretamente o índice numérico (A1 → 1, A2 → 2, …),
> usado para extrair o valor do sinal de cada amostra (`sample[canal]`). A primeira amostra
> completa recebida é registrada no log no início de cada gravação, permitindo conferir qual
> índice corresponde ao sensor.

## Watchdog de perda de conexão

Após conectar, um **watchdog** (vigia em thread separada) monitora continuamente o fluxo de
amostras:

- Verifica o fluxo a cada **1 segundo**.
- Se **nenhuma amostra** for recebida por **15 segundos**, a conexão é considerada perdida.
- Nesse caso: o experimento em andamento (se houver) é interrompido — finalizando o arquivo da
  faixa atual com o marcador `PARADA_FORCADA` —, o estado de conexão é resetado e uma mensagem de
  aviso é exibida ("Conexão com BITalino perdida. Verifique o sensor.").

Durante a gravação de uma faixa, o watchdog **não puxa amostras** (para não competir com a
gravação): ele lê o instante da última amostra registrada pelo gravador. Entre faixas (ocioso),
faz uma sondagem leve para verificar se ainda há fluxo.

## Desconectando

O botão **Desconectar** encerra manualmente a conexão e restaura a interface de conexão. Se um
experimento estiver em andamento, a desconexão é **bloqueada** com um aviso — pare o experimento
antes de desconectar.

---

Anterior: [« Primeiros passos](getting-started.md) · Próximo: [Menus »](experiment-menu.md)
