// Tooltip (hovertip) temática reutilizável — fundo/borda/texto da paleta ativa.
// Uso típico: instanciar dentro de um controle e ligar `visible` ao estado de hover.
import QtQuick
import QtQuick.Controls.Basic

ToolTip {
    id: dica
    delay: 450
    padding: 7
    font.family: Theme.fonts.display
    font.pixelSize: Theme.fonts.s11

    background: Rectangle {
        color: Theme.colors.bar_bg
        border.color: Theme.colors.border
        border.width: 1
        radius: Theme.metrics.cornerSm
    }
    contentItem: Text {
        text: dica.text
        color: Theme.colors.text
        font: dica.font
    }
}
