// Barra de título custom (janela frameless), tingida pela paleta ativa.
// Substitui o efeito do pywinstyles: desenha título, permite arrasto da janela e
// oferece botões minimizar / maximizar-restaurar / fechar próprios.
import QtQuick
import QtQuick.Window
import QtQuick.Layouts
import "components"

Rectangle {
    id: bar
    // Janela dona desta barra (injetada pelo Main/AppWindow). Usada para arrasto/estado.
    required property var janela
    // Texto/ícone/maximizar são customizáveis para reuso nas janelas auxiliares (AppWindow).
    property string titulo: "ComPasso" + (appVersion ? "  ·  " + appVersion : "")
    property bool mostrarIcone: true
    property bool mostrarMax: true
    // Arredondamento dos cantos superiores (acompanha o canto da janela frameless).
    property real raioCanto: 0

    implicitHeight: Theme.metrics.titleBarH
    color: Theme.colors.bar_bg
    topLeftRadius: raioCanto
    topRightRadius: raioCanto

    // Linha divisória inferior sutil.
    Rectangle {
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
        height: 1
        color: Theme.colors.border
    }

    // Área de arrasto: cobre a barra toda; os botões (acima no z) capturam antes.
    MouseArea {
        anchors.fill: parent
        onPressed: bar.janela.startSystemMove()
        onDoubleClicked: bar.janela.alternarMaximizar()
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.metrics.padMd
        spacing: Theme.metrics.padSm

        Image {
            visible: bar.mostrarIcone
            source: assetsDir + "/icon.png"
            sourceSize.height: 20
            fillMode: Image.PreserveAspectFit
            Layout.preferredHeight: visible ? 20 : 0
            Layout.preferredWidth: visible ? 20 : 0
        }

        Text {
            text: bar.titulo
            color: Theme.colors.text
            font.family: Theme.fonts.display
            font.pixelSize: Theme.fonts.s13
            font.bold: true
            Layout.fillWidth: true
        }

        // Botões de janela (min / max opcional / fechar).
        Repeater {
            model: bar.mostrarMax
                   ? [ { simbolo: "–", acao: "min" }, { simbolo: "□", acao: "max" }, { simbolo: "✕", acao: "close" } ]
                   : [ { simbolo: "–", acao: "min" }, { simbolo: "✕", acao: "close" } ]
            delegate: Rectangle {
                required property var modelData
                Layout.preferredWidth: 46
                Layout.fillHeight: true
                color: hover.hovered
                       ? (modelData.acao === "close" ? Theme.colors.danger : Theme.colors.input_bg)
                       : "transparent"
                // arredonda o canto superior direito no botão de fechar para acompanhar o
                // canto da janela (o clip retangular do pai não segue o raio arredondado).
                topRightRadius: modelData.acao === "close" ? bar.raioCanto : 0

                Text {
                    anchors.centerIn: parent
                    text: parent.modelData.simbolo
                    color: (hover.hovered && parent.modelData.acao === "close")
                           ? Theme.colors.accent_ink : Theme.colors.muted
                    font.family: Theme.fonts.display
                    font.pixelSize: Theme.fonts.s13
                }

                HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
                Dica {
                    parent: parent
                    visible: hover.hovered
                    text: parent.modelData.acao === "min" ? "Minimizar"
                          : parent.modelData.acao === "max" ? "Maximizar / Restaurar" : "Fechar"
                }
                TapHandler {
                    onTapped: {
                        if (parent.modelData.acao === "min") bar.janela.minimizarSuave()
                        else if (parent.modelData.acao === "max") bar.janela.alternarMaximizar()
                        else bar.janela.close()
                    }
                }
            }
        }
    }
}
