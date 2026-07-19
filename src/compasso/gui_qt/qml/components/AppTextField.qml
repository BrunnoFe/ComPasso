// Campo de texto estilizado (equivale a widgets.styled_entry). Fonte mono opcional (MAC).
import QtQuick
import QtQuick.Controls.Basic

TextField {
    id: campo
    property bool mono: false
    // Entrada inválida: contorna o campo de vermelho. Acompanha o `ErroCampo` que descreve o
    // problema logo abaixo — a borda chama atenção, o texto explica.
    property bool erro: false
    implicitHeight: Theme.metrics.inputH
    color: Theme.colors.text
    placeholderTextColor: Theme.colors.faint
    font.family: mono ? Theme.fonts.mono : Theme.fonts.display
    font.pixelSize: Theme.fonts.s13
    leftPadding: Theme.metrics.padSm + 2
    rightPadding: Theme.metrics.padSm + 2
    selectByMouse: true

    background: Rectangle {
        radius: Theme.metrics.cornerSm
        color: Theme.colors.input_bg
        border.width: 1
        // o erro vence o foco: um campo inválido em foco continua sinalizando o problema.
        border.color: campo.erro ? Theme.colors.danger
                    : campo.activeFocus ? Theme.colors.accent : Theme.colors.border
    }
}
