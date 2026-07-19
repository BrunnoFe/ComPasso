// Janela auxiliar borderless com cantos arredondados (mesmo estilo do Main.qml), reutilizada
// pelas janelas de configuração (experimento/gráfico/calibração). Fornece barra de título
// própria (arrasto/min/max/fechar), redimensionamento pelas bordas e uma área de conteúdo.
import QtQuick
import QtQuick.Window
import QtQuick.Layouts

Window {
    id: win
    property alias titulo: barra.titulo
    property bool mostrarMax: true
    default property alias conteudo: hostConteudo.data

    flags: Qt.Window | Qt.FramelessWindowHint
    color: "transparent"

    // maximizar/restaurar e minimizar com transição suave (ver Main.qml para o racional).
    property bool maximizado: false
    property rect geomAnterior: Qt.rect(x, y, width, height)

    // Transicao de maximizar/restaurar (mesmo racional do Main.qml: OutQuint + duracao curta).
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
    // Minimizar: deixa a cargo do sistema (ver Main.qml).
    function minimizarSuave() { win.showMinimized() }

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
                id: barra
                Layout.fillWidth: true
                janela: win
                mostrarIcone: false
                mostrarMax: win.mostrarMax
                raioCanto: win.maximizado ? 0 : Theme.metrics.cornerCard
            }

            Item {
                id: hostConteudo
                Layout.fillWidth: true
                Layout.fillHeight: true
            }
        }

        // Redimensionamento nas bordas (janela frameless), igual ao Main.qml.
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
