// Janela principal do ComPasso (frameless): barra de título + menus + conteúdo + rodapé fixo.
// Fase 3 completa: todas as views principais. Diálogos de mensagem/confirmação e pedidos de
// janelas auxiliares (config/gráfico/calibração — Fase 6) são roteados aqui.
import QtQuick
import QtQuick.Window
import QtQuick.Controls.Basic
import QtQuick.Layouts
import QtQuick.Dialogs
import "components"
import "views"
import "windows"

Window {
    id: win
    visible: true
    // Abre no tamanho preferido (1300x720); se a tela do usuario for menor, encolhe para caber
    // (limitado ao minimo absoluto 600x400). O layout continua intacto porque o conteudo
    // principal e rolavel — reduzir a janela so ativa a barra de rolagem, nao desconfigura nada.
    width: Math.max(Theme.metrics.winMinWidth,
                    Math.min(Theme.metrics.winPrefWidth, Screen.desktopAvailableWidth))
    height: Math.max(Theme.metrics.winMinHeight,
                     Math.min(Theme.metrics.winPrefHeight, Screen.desktopAvailableHeight))
    minimumWidth: Theme.metrics.winMinWidth
    minimumHeight: Theme.metrics.winMinHeight
    title: "ComPasso" + (appVersion ? " " + appVersion : "")
    flags: Qt.Window | Qt.FramelessWindowHint
    color: "transparent"

    // ---- maximizar/restaurar e minimizar com transição suave (janela frameless) ----
    // Maximização é "emulada" (anima a geometria até a área útil da tela e volta), pois a janela
    // é frameless — assim ganhamos a expansão graciosa em vez do salto do showMaximized().
    property bool maximizado: false
    property rect geomAnterior: Qt.rect(x, y, width, height)

    // Transicao de maximizar/restaurar. `OutQuint` reage no primeiro quadro e desacelera longo
    // no fim — parece mais rapida que o `InOutQuart` anterior mesmo com duracao MENOR (220 ms
    // contra 320), porque o InOut gastava o inicio acelerando, e e o inicio que o olho le como
    // "resposta ao clique". Menos quadros tambem significa menos reflow do conteudo por
    // transicao, o que suaviza o resultado numa janela real.
    ParallelAnimation {
        id: animGeom
        property real nx; property real ny; property real nw; property real nh
        readonly property int dur: Theme.metrics.animJanelaMs
        NumberAnimation { target: win; property: "x"; to: animGeom.nx; duration: animGeom.dur; easing.type: Easing.OutQuint }
        NumberAnimation { target: win; property: "y"; to: animGeom.ny; duration: animGeom.dur; easing.type: Easing.OutQuint }
        NumberAnimation { target: win; property: "width"; to: animGeom.nw; duration: animGeom.dur; easing.type: Easing.OutQuint }
        NumberAnimation { target: win; property: "height"; to: animGeom.nh; duration: animGeom.dur; easing.type: Easing.OutQuint }
    }
    function _animarGeom(nx, ny, nw, nh) {
        animGeom.stop()
        animGeom.nx = nx; animGeom.ny = ny; animGeom.nw = nw; animGeom.nh = nh
        animGeom.start()
    }
    function alternarMaximizar() {
        if (maximizado) {
            maximizado = false
            _animarGeom(geomAnterior.x, geomAnterior.y, geomAnterior.width, geomAnterior.height)
        } else {
            geomAnterior = Qt.rect(win.x, win.y, win.width, win.height)
            maximizado = true
            _animarGeom(Screen.virtualX, Screen.virtualY,
                        Screen.desktopAvailableWidth, Screen.desktopAvailableHeight)
        }
    }

    // Minimizar: `showMinimized()` e so isso. A animacao de encolher para a barra de tarefas e
    // do proprio Windows (DWM) e ja acontece — NAO tente "melhorar" mexendo no estilo nativo da
    // janela (WS_MINIMIZEBOX/WS_SYSMENU via SetWindowLong): ja foi tentado e o efeito foi o
    // inverso, a animacao parou de acontecer. Animar a geometria em QML tambem nao serve: o
    // Windows restaura a janela instantaneamente, entao a volta ficaria sem animacao.
    function minimizarSuave() { win.showMinimized() }

    // Preferência "abrir maximizado": aplicada sem animação (não faz sentido animar uma
    // expansão que o usuário nunca viu começar) — apenas assume o estado maximizado.
    Component.onCompleted: {
        // geometria lembrada da última sessão (só quando a preferência está ligada e o app não
        // vai abrir maximizado, caso em que ela seria imediatamente sobrescrita).
        if (!prefsApp.abrir_maximizado && geometriaSalva.largura !== undefined) {
            win.x = geometriaSalva.x
            win.y = geometriaSalva.y
            win.width = Math.max(win.minimumWidth, geometriaSalva.largura)
            win.height = Math.max(win.minimumHeight, geometriaSalva.altura)
        }
        if (prefsApp.abrir_maximizado) {
            geomAnterior = Qt.rect(win.x, win.y, win.width, win.height)
            maximizado = true
            win.x = Screen.virtualX; win.y = Screen.virtualY
            win.width = Screen.desktopAvailableWidth
            win.height = Screen.desktopAvailableHeight
        }
    }

    // Diálogo de mensagem (erros/avisos), acionado por qualquer controller.
    MessageDialog { id: dialogoMensagem }
    Connections {
        target: connController
        function onMensagem(titulo, texto, tipo) { dialogoMensagem.abrir(titulo, texto, tipo) }
        function onPedirConfirmarDesconectar() {
            dialogoDesconectar.abrir("Desconectar Bitalino",
                                     "Tem certeza que deseja desconectar o Bitalino?")
        }
        function onPedirConfirmarConectarTeste(mac) {
            dialogoConectarTeste.carga = mac
            dialogoConectarTeste.abrir(
                "Modo de teste ativo",
                "Modo de testes com Bitalino simulado habilitado.\n\nOs dados coletados serão "
                + "SIMULADOS, não vêm do participante. Deseja prosseguir?")
        }
    }

    // Aviso ao conectar com o simulador ligado. Três saídas: prosseguir mesmo assim, desligar
    // o teste e conectar de verdade, ou desistir.
    ConfirmDialog {
        id: dialogoConectarTeste
        textoSim: "Sim"
        textoNao: "Cancelar"
        textoAlternativo: "Desabilitar teste"
        onConfirmado: connController.conectar(carga)
        onAlternativo: {
            var macSimulado = appSettingsController.desativar_simulacao()
            // se o MAC na tela era o do próprio simulador, ele acabou de sumir: conectar agora
            // só produziria "não foi possível conectar" sem explicar o porquê.
            if (carga.toUpperCase() === macSimulado.toUpperCase())
                dialogoMensagem.abrir(
                    "Modo de teste desligado",
                    "O BITalino simulado foi encerrado.\n\nInforme o endereço MAC do aparelho "
                    + "real e clique em Conectar.", "info")
            else
                connController.conectar(carga)
        }
    }
    Connections {
        target: partController
        function onMensagem(titulo, texto, tipo) { dialogoMensagem.abrir(titulo, texto, tipo) }
    }
    Connections {
        target: filesController
        function onMensagem(titulo, texto, tipo) { dialogoMensagem.abrir(titulo, texto, tipo) }
    }
    Connections {
        target: playerController
        function onMensagem(titulo, texto, tipo) { dialogoMensagem.abrir(titulo, texto, tipo) }
        function onConfirmarParada() { dialogoParada.abrir("Parar experimento",
                                        "Tem certeza que deseja parar o experimento?") }
        function onAbrirCalibracao() { janelaCalibracao.abrir() }
    }
    Connections {
        target: experimentController
        function onMensagem(titulo, texto, tipo) { dialogoMensagem.abrir(titulo, texto, tipo) }
        // fim natural da sessão: avisa e, ao fechar o aviso, rearma o app para a próxima coleta.
        function onColetaFinalizada() {
            dialogoFimColeta.abrir("Coleta finalizada",
                                   "Coleta de dados finalizada!\n\nOs arquivos da sessão já foram "
                                   + "salvos. Ao continuar, o aplicativo fica pronto para uma nova "
                                   + "coleta (o Bitalino permanece conectado).", "info")
        }
    }

    // Aviso de fim de coleta: instância própria porque só ele dispara o reset ao ser fechado.
    MessageDialog {
        id: dialogoFimColeta
        onClosed: experimentController.preparar_nova_coleta()
    }
    // Pedidos de janelas auxiliares.
    Connections {
        target: appController
        function onPedirNovoConfig() { configController.abrir_novo(); janelaConfig.abrir() }
        function onPedirAbrirConfig() { dlgAbrirConfig.open() }
        function onPedirEditarConfig() {
            if (ctx.configLoaded) { configController.abrir_editar(); janelaConfig.abrir() }
            else dialogoMensagem.abrir("Editar", "Abra ou crie uma configuração primeiro.", "info")
        }
        function onPedirGraphSettings() { janelaGrafico.abrir() }
        function onPedirAppSettings() { janelaAppSettings.abrir() }
    }
    Connections {
        target: configController
        // enquanto o editor (modal) está aberto, ele mesmo exibe as mensagens — ver
        // ExperimentConfigWindow. Aqui só chegam as de fora do editor (ex.: "Abrir .config").
        enabled: !janelaConfig.visible
        function onMensagem(titulo, texto, tipo) { dialogoMensagem.abrir(titulo, texto, tipo) }
    }

    // Verificação de atualizações: a janelinha só aparece na verificação MANUAL; a automática
    // do arranque é silenciosa e apenas acende o ponto vermelho no menu.
    UpdateDialog { id: dialogoAtualizacao }
    Connections {
        target: updatesController
        function onPedirAbrirJanela() { dialogoAtualizacao.abrir() }
    }

    // Diálogo para abrir um .config existente (menu Experimento → Abrir).
    FileDialog {
        id: dlgAbrirConfig
        title: "Abrir configuração"
        nameFilters: ["Configuração (*.config)"]
        onAccepted: configController.abrir_arquivo(selectedFile)
    }

    // Janelas auxiliares.
    ExperimentConfigWindow { id: janelaConfig }
    GraphSettingsWindow { id: janelaGrafico }
    CalibrationWindow { id: janelaCalibracao }
    AppSettingsWindow { id: janelaAppSettings }

    // Confirmação de parada do experimento (Sim/Não).
    ConfirmDialog {
        id: dialogoParada
        onConfirmado: playerController.confirmar_parada()
    }

    // Confirmação de desconexão manual do Bitalino (Sim/Não).
    ConfirmDialog {
        id: dialogoDesconectar
        onConfirmado: connController.desconectar()
    }

    // Fechar a janela com uma coleta em andamento perderia a faixa corrente: pede confirmação
    // (comportamento desligável na preferência "confirmar_saida_em_experimento").
    property bool _saidaConfirmada: false
    ConfirmDialog {
        id: dialogoSaida
        onConfirmado: { win._saidaConfirmada = true; win.close() }
    }
    onClosing: function(evento) {
        // guarda a geometria RESTAURADA: salvar a maximizada faria a janela reabrir ocupando a
        // tela inteira mesmo com "abrir maximizado" desligado.
        var g = win.maximizado ? win.geomAnterior
                               : Qt.rect(win.x, win.y, win.width, win.height)
        appController.salvar_geometria(g.x, g.y, g.width, g.height)

        if (win._saidaConfirmada || !prefsApp.confirmar_saida_em_experimento)
            return
        if (ctx.buttonState === "rodando" || ctx.buttonState === "continuar") {
            evento.accepted = false
            dialogoSaida.abrir("Sair do ComPasso",
                               "Há um experimento em andamento. Sair agora encerra a coleta e a "
                               + "faixa atual não será concluída.\n\nDeseja sair mesmo assim?")
        }
    }

    Rectangle {
        id: quadro
        anchors.fill: parent
        color: Theme.colors.win_bg
        border.color: Theme.colors.border_win
        border.width: 1
        radius: win.maximizado ? 0 : Theme.metrics.cornerCard
        clip: true

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 1
            spacing: 0

            TitleBar {
                Layout.fillWidth: true
                janela: win
                raioCanto: win.maximizado ? 0 : Theme.metrics.cornerCard
            }

            AppMenuBar { Layout.fillWidth: true }

            // ---- Conteúdo scrollável (equivale ao CTkScrollableFrame do MainFrame) ----
            MainContent {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.margins: Theme.metrics.padMd
            }

            // ---- Rodapé fixo (fora do scroll, como o DownFrame) ----
            FooterView {
                Layout.fillWidth: true
                raioInferior: win.maximizado ? 0 : Theme.metrics.cornerCard
            }
        }

        // Tela de carregamento (some após alguns segundos).
        SplashOverlay {}

        // Redimensionamento nas bordas (janela frameless).
        Repeater {
            model: [
                { lado: Qt.LeftEdge }, { lado: Qt.RightEdge }, { lado: Qt.BottomEdge }
            ]
            delegate: MouseArea {
                required property var modelData
                property bool horizontal: modelData.lado === Qt.LeftEdge || modelData.lado === Qt.RightEdge
                width: horizontal ? 5 : parent.width
                height: horizontal ? parent.height : 5
                x: modelData.lado === Qt.RightEdge ? parent.width - width : 0
                y: modelData.lado === Qt.BottomEdge ? parent.height - height : 0
                cursorShape: horizontal ? Qt.SizeHorCursor : Qt.SizeVerCursor
                onPressed: win.startSystemResize(modelData.lado)
            }
        }
    }
}
