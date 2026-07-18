// Switch estilizado pela paleta (trilho no acento quando ligado).
import QtQuick
import QtQuick.Controls.Basic

Switch {
    id: ctrl
    // Reserva a largura do indicador: com contentItem vazio, o Switch não reportava a
    // largura do trilho, e o próximo widget do RowLayout sobrepunha o botão. Fixar
    // padding/implicitWidth garante que o rótulo ao lado comece após o indicador.
    padding: 0
    implicitWidth: 42
    implicitHeight: 22

    // cursor de mãozinha ao passar o mouse (apenas quando habilitado).
    HoverHandler { cursorShape: Qt.PointingHandCursor; enabled: ctrl.enabled }
    indicator: Rectangle {
        implicitWidth: 42
        implicitHeight: 22
        radius: 11
        x: ctrl.leftPadding
        y: parent.height / 2 - height / 2
        color: ctrl.checked ? Theme.colors.accent : Theme.colors.border
        Behavior on color { ColorAnimation { duration: 120 } }
        Rectangle {
            x: ctrl.checked ? parent.width - width - 3 : 3
            y: 3
            width: 16; height: 16; radius: 8
            color: ctrl.checked ? Theme.colors.accent_ink : Theme.colors.text
            Behavior on x { NumberAnimation { duration: 120; easing.type: Easing.OutQuad } }
        }
    }
    contentItem: Item {}
}
