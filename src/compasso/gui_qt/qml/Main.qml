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

    // Transicao de maximizar/restaurar mais fluida: duracao maior e easing InOutQuart, que
    // acelera e desacelera suavemente (sem o arranque abrupto do OutCubic anterior).
    ParallelAnimation {
        id: animGeom
        property real nx; property real ny; property real nw; property real nh
        NumberAnimation { target: win; property: "x"; to: animGeom.nx; duration: 320; easing.type: Easing.InOutQuart }
        NumberAnimation { target: win; property: "y"; to: animGeom.ny; duration: 320; easing.type: Easing.InOutQuart }
        NumberAnimation { target: win; property: "width"; to: animGeom.nw; duration: 320; easing.type: Easing.InOutQuart }
        NumberAnimation { target: win; property: "height"; to: animGeom.nh; duration: 320; easing.type: Easing.InOutQuart }
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

    // Minimizar: sem animacao (vai direto para a barra de tarefas).
    function minimizarSuave() { win.showMinimized() }

    // Diálogo de mensagem (erros/avisos), acionado por qualquer controller.
    MessageDialog { id: dialogoMensagem }
    Connections {
        target: connController
        function onMensagem(titulo, texto, tipo) { dialogoMensagem.abrir(titulo, texto, tipo) }
        function onPedirConfirmarDesconectar() {
            dialogoDesconectar.abrir("Desconectar Bitalino",
                                     "Tem certeza que deseja desconectar o Bitalino?")
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
