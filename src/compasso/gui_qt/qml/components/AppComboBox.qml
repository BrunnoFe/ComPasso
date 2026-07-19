// ComboBox estilizado (equivale a widgets.styled_combobox / CTkOptionMenu).
import QtQuick
import QtQuick.Controls.Basic

ComboBox {
    id: combo
    // Seleção inválida: contorna o combo de vermelho (ver AppTextField.erro).
    property bool erro: false
    implicitHeight: Theme.metrics.inputH
    font.family: Theme.fonts.mono
    font.pixelSize: Theme.fonts.s13

    // cursor de mãozinha ao passar o mouse (apenas quando habilitado).
    HoverHandler { cursorShape: Qt.PointingHandCursor; enabled: combo.enabled }

    background: Rectangle {
        radius: Theme.metrics.cornerSm
        color: Theme.colors.input_bg
        border.width: 1
        border.color: combo.erro ? Theme.colors.danger
                    : combo.activeFocus ? Theme.colors.accent : Theme.colors.border
    }

    contentItem: Text {
        leftPadding: Theme.metrics.padSm + 2
        rightPadding: 18
        text: combo.displayText
        color: Theme.colors.text
        font: combo.font
        verticalAlignment: Text.AlignVCenter
        horizontalAlignment: Text.AlignLeft
        elide: Text.ElideRight
    }

    indicator: Text {
        x: combo.width - width - 8
        y: (combo.height - height) / 2
        text: "▾"
        color: Theme.colors.muted
        font.pixelSize: Theme.fonts.s11
    }

    popup: Popup {
        y: combo.height + 2
        width: combo.width
        implicitHeight: Math.min(contentItem.implicitHeight + 2, 260)
        padding: 1
        background: Rectangle {
            radius: Theme.metrics.cornerSm
            color: Theme.colors.bar_bg
            border.color: Theme.colors.border
            border.width: 1
        }
        contentItem: ListView {
            clip: true
            implicitHeight: contentHeight
            model: combo.popup.visible ? combo.delegateModel : null
            currentIndex: combo.highlightedIndex
            ScrollIndicator.vertical: ScrollIndicator {}
        }
    }

    delegate: ItemDelegate {
        width: combo.width
        required property var model
        required property int index
        height: Theme.metrics.inputH
        background: Rectangle {
            color: highlighted ? Theme.colors.accent_tint : "transparent"
        }
        contentItem: Text {
            leftPadding: Theme.metrics.padSm + 2
            text: model[combo.textRole] !== undefined ? model[combo.textRole] : model.modelData
            color: Theme.colors.text
            font: combo.font
            verticalAlignment: Text.AlignVCenter
            horizontalAlignment: Text.AlignLeft
        }
        highlighted: combo.highlightedIndex === index
    }
}
