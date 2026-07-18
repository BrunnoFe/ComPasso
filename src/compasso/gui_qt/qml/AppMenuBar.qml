// Barra de menus custom (Experimento / Configurações / Tema / Ajuda), tingida pela paleta.
// Substitui o CTkMenuBar. Os itens de "Experimento" ficam desabilitados durante a sessão
// (ctx.experimentUiLocked), como no app antigo. Ações delegadas a appController/Theme.
import QtQuick
import QtQuick.Controls.Basic

Rectangle {
    id: barra
    implicitHeight: 34
    color: Theme.colors.footer_bg

    Rectangle {
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
        height: 1
        color: Theme.colors.border
    }

    // Item de menu estilizado reutilizável.
    component ItemMenu: MenuItem {
        id: mi
        implicitHeight: 32
        implicitWidth: 220
        background: Rectangle {
            color: mi.highlighted ? Theme.colors.accent_tint : "transparent"
        }
        contentItem: Text {
            leftPadding: Theme.metrics.padMd
            rightPadding: Theme.metrics.padMd
            text: mi.text
            color: mi.enabled ? Theme.colors.text : Theme.colors.faint
            font.family: Theme.fonts.display
            font.pixelSize: Theme.fonts.s13
            verticalAlignment: Text.AlignVCenter
        }
    }

    // Botão-título que abre um Menu logo abaixo.
    component BotaoMenu: Item {
        id: bm
        property string titulo: ""
        default property alias itens: menu.contentData
        width: rotulo.implicitWidth + 2 * Theme.metrics.padMd
        height: barra.height

        Rectangle {
            anchors.fill: parent
            color: (hover.hovered || menu.opened) ? Theme.colors.input_bg : "transparent"
            Text {
                id: rotulo
                anchors.centerIn: parent
                text: bm.titulo
                color: Theme.colors.text
                font.family: Theme.fonts.display
                font.pixelSize: Theme.fonts.s13
            }
        }
        HoverHandler { id: hover }
        TapHandler { onTapped: menu.popup(0, bm.height) }

        Menu {
            id: menu
            background: Rectangle {
                implicitWidth: 220
                color: Theme.colors.bar_bg
                border.color: Theme.colors.border
                border.width: 1
                radius: Theme.metrics.cornerSm
            }
        }
    }

    Row {
        anchors.left: parent.left
        anchors.leftMargin: Theme.metrics.padSm
        anchors.verticalCenter: parent.verticalCenter
        height: parent.height
        spacing: 0

        BotaoMenu {
            titulo: "Experimento"
            ItemMenu { text: "Novo…"; enabled: !ctx.experimentUiLocked; onTriggered: appController.pedirNovoConfig() }
            ItemMenu { text: "Abrir…"; enabled: !ctx.experimentUiLocked; onTriggered: appController.pedirAbrirConfig() }
            ItemMenu { text: "Editar…"; enabled: !ctx.experimentUiLocked && ctx.configLoaded; onTriggered: appController.pedirEditarConfig() }
            MenuSeparator {}
            ItemMenu { text: "Sair"; onTriggered: appController.sair() }
        }

        BotaoMenu {
            titulo: "Configurações"
            ItemMenu { text: "Gráfico…"; onTriggered: appController.pedirGraphSettings() }
        }

        BotaoMenu {
            titulo: "Tema"
            Repeater {
                model: Theme.nomes
                delegate: ItemMenu {
                    required property string modelData
                    text: (Theme.nome === modelData ? "✓  " : "     ") + modelData
                    onTriggered: Theme.setTheme(modelData)
                }
            }
        }

        BotaoMenu {
            titulo: "Ajuda"
            ItemMenu { text: "Abrir pasta de logs"; onTriggered: appController.abrir_pasta_logs() }
            ItemMenu { text: "Página do projeto"; onTriggered: appController.abrir_pagina_projeto() }
            ItemMenu { text: "Site do projeto"; onTriggered: appController.abrir_site_projeto() }
        }
    }
}
