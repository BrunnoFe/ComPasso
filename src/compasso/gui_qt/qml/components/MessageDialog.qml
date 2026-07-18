// Diálogo de mensagem (erro/aviso/info) — um só botão "OK". Estilizado pela paleta e
// centralizado sobre a janela. Use abrir(titulo, texto, tipo). Layout padronizado com o
// ConfirmDialog: badge de ícone + título, corpo, rodapé com botão à direita.
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

Dialog {
    id: dlg
    property string tipo: "info"     // "warning" | "info"
    readonly property bool ehAviso: tipo === "warning"
    modal: true
    anchors.centerIn: parent
    padding: 0
    closePolicy: Popup.CloseOnEscape
    implicitWidth: 440

    function abrir(titulo, texto, tipoMsg) {
        dlg.title = titulo
        corpo.text = texto
        dlg.tipo = tipoMsg || "info"
        dlg.open()
    }

    // escurece o fundo atrás do diálogo.
    Overlay.modal: Rectangle { color: "#99000000" }

    background: Rectangle {
        radius: Theme.metrics.cornerCard
        color: Theme.colors.bar_bg
        border.color: dlg.ehAviso ? Theme.colors.danger_border : Theme.colors.border
        border.width: 1
    }

    header: null
    footer: null

    contentItem: ColumnLayout {
        spacing: Theme.metrics.padMd

        // ---- cabeçalho: badge de ícone + título ----
        RowLayout {
            Layout.fillWidth: true
            Layout.margins: Theme.metrics.padLg
            Layout.bottomMargin: 0
            spacing: Theme.metrics.padMd

            Rectangle {
                Layout.preferredWidth: 34; Layout.preferredHeight: 34
                radius: 17
                color: dlg.ehAviso ? Theme.colors.danger_tint : Theme.colors.accent_tint
                Text {
                    anchors.centerIn: parent
                    text: dlg.ehAviso ? "!" : "i"
                    color: dlg.ehAviso ? Theme.colors.danger : Theme.colors.accent
                    font.family: Theme.fonts.display
                    font.pixelSize: Theme.fonts.s17
                    font.bold: true
                }
            }
            Text {
                text: dlg.title
                Layout.fillWidth: true
                color: dlg.ehAviso ? Theme.colors.danger : Theme.colors.text
                font.family: Theme.fonts.display
                font.pixelSize: Theme.fonts.s15
                font.bold: true
                wrapMode: Text.WordWrap
                verticalAlignment: Text.AlignVCenter
            }
        }

        // ---- corpo ----
        Text {
            id: corpo
            Layout.fillWidth: true
            Layout.leftMargin: Theme.metrics.padLg
            Layout.rightMargin: Theme.metrics.padLg
            color: Theme.colors.muted
            font.family: Theme.fonts.display
            font.pixelSize: Theme.fonts.s13
            lineHeight: 1.25
            wrapMode: Text.WordWrap
        }

        // ---- rodapé ----
        RowLayout {
            Layout.fillWidth: true
            Layout.margins: Theme.metrics.padLg
            Layout.topMargin: Theme.metrics.padSm
            Item { Layout.fillWidth: true }
            AppButton {
                text: "OK"
                Layout.preferredWidth: 110
                onClicked: dlg.close()
            }
        }
    }
}
