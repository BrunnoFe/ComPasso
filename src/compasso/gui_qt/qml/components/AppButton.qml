// Botão de ação primário (acento), equivale a widgets.styled_button.
import QtQuick
import QtQuick.Controls.Basic

Button {
    id: botao
    property color corFundo: Theme.colors.accent
    property color corTexto: Theme.colors.accent_ink
    property alias dica: _dica.text     // hovertip opcional (vazio = sem tooltip)
    implicitHeight: Theme.metrics.btnH
    implicitWidth: Math.max(130, contentItem.implicitWidth + 2 * Theme.metrics.padMd)

    // cursor de mãozinha ao passar o mouse (apenas quando habilitado).
    HoverHandler { cursorShape: Qt.PointingHandCursor; enabled: botao.enabled }
    Dica { id: _dica; parent: botao; visible: _dica.text.length > 0 && botao.hovered }

    background: Rectangle {
        radius: Theme.metrics.cornerSm
        color: !botao.enabled ? Theme.colors.input_bg
               : botao.down ? Qt.darker(botao.corFundo, 1.15)
               : botao.hovered ? Qt.lighter(botao.corFundo, 1.08)
               : botao.corFundo
        border.width: botao.enabled ? 0 : 1
        border.color: Theme.colors.border
    }
    contentItem: Text {
        text: botao.text
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        color: botao.enabled ? botao.corTexto : Theme.colors.faint
        font.family: Theme.fonts.display
        font.pixelSize: Theme.fonts.s13
        font.bold: true
    }
}
