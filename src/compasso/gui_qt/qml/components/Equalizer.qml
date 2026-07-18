// Equalizador animado (barras que pulsam) — equivale ao LiveEqualizer (canvas_widgets.py).
// Usado no indicador "Conectado". As alturas variam por NumberAnimation em loop.
import QtQuick

Row {
    id: eq
    property color corBarra: Theme.colors.accent
    property int qtdBarras: 4
    property int larguraBarra: 3
    property int alturaMax: 16

    spacing: 2
    height: alturaMax

    Repeater {
        model: eq.qtdBarras
        delegate: Rectangle {
            required property int index
            width: eq.larguraBarra
            radius: eq.larguraBarra / 2
            color: eq.corBarra
            anchors.verticalCenter: parent.verticalCenter
            height: eq.alturaMax * 0.4

            SequentialAnimation on height {
                loops: Animation.Infinite
                running: eq.visible
                // fase inicial diferente por barra, para não pulsarem em uníssono.
                PauseAnimation { duration: 120 * index }
                NumberAnimation { to: eq.alturaMax; duration: 260; easing.type: Easing.InOutSine }
                NumberAnimation { to: eq.alturaMax * 0.35; duration: 300; easing.type: Easing.InOutSine }
                NumberAnimation { to: eq.alturaMax * 0.7; duration: 220; easing.type: Easing.InOutSine }
                NumberAnimation { to: eq.alturaMax * 0.45; duration: 280; easing.type: Easing.InOutSine }
            }
        }
    }
}
