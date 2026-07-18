// Rótulo pequeno em maiúsculas, cor apagada (equivale a widgets.caption).
import QtQuick

Text {
    property string texto: ""
    text: texto.toUpperCase()
    color: Theme.colors.faint
    font.family: Theme.fonts.display
    font.pixelSize: Theme.fonts.s11
    font.bold: true
    font.letterSpacing: 0.5
}
