// Diálogo de confirmação Sim/Não (equivale a widgets.confirm). Emite `confirmado` no "Sim" e
// `recusado` no "Não". Use abrir(titulo, texto). Mesmo layout padronizado do MessageDialog.
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

Dialog {
    id: dlg
    signal confirmado()
    signal recusado()
    // rótulos dos botões (padrão Sim/Não; a calibração usa Sim/Reiniciar).
    property string textoSim: "Sim"
    property string textoNao: "Não"
    modal: true
    anchors.centerIn: parent
    padding: 0
    closePolicy: Popup.CloseOnEscape
    implicitWidth: 440

    function abrir(titulo, texto) {
        dlg.title = titulo
        corpo.text = texto
        dlg.open()
    }

    Overlay.modal: Rectangle { color: "#99000000" }

    background: Rectangle {
        radius: Theme.metrics.cornerCard
        color: Theme.colors.bar_bg
        border.color: Theme.colors.border
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
                color: Theme.colors.accent_tint
                Text {
                    anchors.centerIn: parent
                    text: "?"
                    color: Theme.colors.accent
                    font.family: Theme.fonts.display
                    font.pixelSize: Theme.fonts.s17
                    font.bold: true
                }
            }
            Text {
                text: dlg.title
                Layout.fillWidth: true
                color: Theme.colors.text
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

        // ---- rodapé: Não (fantasma) + Sim (perigo) ----
        RowLayout {
            Layout.fillWidth: true
            Layout.margins: Theme.metrics.padLg
            Layout.topMargin: Theme.metrics.padSm
            spacing: Theme.metrics.padSm
            Item { Layout.fillWidth: true }
            GhostButton {
                text: dlg.textoNao
                Layout.preferredWidth: 110
                onClicked: { dlg.recusado(); dlg.close() }
            }
            GhostButton {
                text: dlg.textoSim
                perigo: true
                Layout.preferredWidth: 110
                onClicked: { dlg.confirmado(); dlg.close() }
            }
        }
    }
}
