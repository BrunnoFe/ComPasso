// Botão secundário "fantasma": fundo de campo, texto apagado, borda (widgets.ghost_button).
import QtQuick
import QtQuick.Controls.Basic

Button {
    id: botao
    property bool perigo: false      // variante de perigo (widgets.danger_button)
    property color corBorda: perigo ? Theme.colors.danger_border : Theme.colors.border
    property color corTexto: perigo ? Theme.colors.danger : Theme.colors.muted
    property color corFundo: perigo ? Theme.colors.danger_tint : Theme.colors.input_bg
    property alias dica: _dica.text     // hovertip opcional (vazio = sem tooltip)

    implicitHeight: Theme.metrics.btnH
    implicitWidth: Math.max(110, contentItem.implicitWidth + 2 * Theme.metrics.padMd)

    // cursor de mãozinha ao passar o mouse (apenas quando habilitado).
    HoverHandler { cursorShape: Qt.PointingHandCursor; enabled: botao.enabled }
    Dica { id: _dica; parent: botao; visible: _dica.text.length > 0 && botao.hovered }

    background: Rectangle {
        radius: Theme.metrics.cornerSm
        color: botao.enabled
               ? (botao.down ? Qt.darker(botao.corFundo, 1.1)
                  : botao.hovered ? Qt.lighter(botao.corFundo, 1.12) : botao.corFundo)
               : Theme.colors.input_bg
        border.width: 1
        border.color: botao.enabled ? botao.corBorda : Theme.colors.border
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
