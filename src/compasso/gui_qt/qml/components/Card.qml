// Cartão base: fundo da barra, borda de 1px e cantos arredondados (equivale a widgets.Card).
import QtQuick

Rectangle {
    default property alias conteudo: area.data
    property alias padding: area.anchors.margins

    color: Theme.colors.bar_bg
    border.color: Theme.colors.border
    border.width: 1
    radius: Theme.metrics.cornerCard

    Item {
        id: area
        anchors.fill: parent
        anchors.margins: Theme.metrics.padMd
    }
}
