// Slider estilizado pela paleta (trilho/knob no acento). Emite movido(valor) ao arrastar.
import QtQuick
import QtQuick.Controls.Basic

Slider {
    id: ctrl
    signal movido(real valor)
    onMoved: ctrl.movido(ctrl.value)

    background: Rectangle {
        x: ctrl.leftPadding
        y: ctrl.topPadding + ctrl.availableHeight / 2 - height / 2
        width: ctrl.availableWidth
        height: 4
        radius: 2
        color: Theme.colors.border
        Rectangle {
            width: ctrl.visualPosition * parent.width
            height: parent.height
            radius: parent.radius
            color: ctrl.enabled ? Theme.colors.accent : Theme.colors.faint
        }
    }
    handle: Rectangle {
        x: ctrl.leftPadding + ctrl.visualPosition * (ctrl.availableWidth - width)
        y: ctrl.topPadding + ctrl.availableHeight / 2 - height / 2
        width: 14; height: 14; radius: 7
        color: ctrl.enabled ? Theme.colors.accent : Theme.colors.faint
    }
}
