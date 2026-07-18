// Cartão com corpo retrátil (equivale a _CollapsibleCard/mid_frame.py).
// Cabeçalho (título + área extra à direita) fica sempre visível; o corpo anima altura/opacidade
// ao recolher. O recolhimento é dirigido pela propriedade `recolhido` (controlada em lockstep
// pelo pai — ver MainContent) — substitui a animação por after()/spacer do Tk.
import QtQuick
import QtQuick.Layouts

Rectangle {
    id: card
    property string titulo: ""
    property bool recolhido: false
    property alias cabecalhoExtra: extra.data     // widgets opcionais à direita do título
    default property alias corpo: corpoHost.data  // conteúdo do corpo retrátil
    // Altura do corpo imposta de fora (mesma unidade de alturaCorpo), usada para igualar a
    // altura de cartões lado a lado (ex.: Participante x Arquivos & Dados) — ver MainContent.
    property real alturaForcada: -1
    readonly property alias alturaCorpo: corpoHost.implicitHeight

    color: Theme.colors.bar_bg
    border.color: Theme.colors.border
    border.width: 1
    radius: Theme.metrics.cornerCard
    implicitHeight: coluna.implicitHeight + 2 * Theme.metrics.padMd
    clip: true

    Column {
        id: coluna
        x: Theme.metrics.padMd
        y: Theme.metrics.padMd
        width: parent.width - 2 * Theme.metrics.padMd
        spacing: Theme.metrics.padSm

        // ---- cabeçalho (sempre visível) ----
        RowLayout {
            width: parent.width
            spacing: Theme.metrics.padSm
            Text {
                text: card.titulo
                color: Theme.colors.text
                font.family: Theme.fonts.display
                font.pixelSize: Theme.fonts.s15
                font.bold: true
                Layout.fillWidth: true
            }
            Row { id: extra; spacing: Theme.metrics.padSm; Layout.alignment: Qt.AlignVCenter }
        }

        // ---- corpo retrátil ----
        Item {
            id: clip
            width: parent.width
            clip: true
            height: card.recolhido ? 0 : Math.max(corpoHost.implicitHeight, card.alturaForcada)
            Behavior on height { NumberAnimation { duration: 130; easing.type: Easing.OutQuad } }

            ColumnLayout {
                id: corpoHost
                width: parent.width
                height: parent.height
                spacing: Theme.metrics.padSm
                opacity: card.recolhido ? 0 : 1
                Behavior on opacity { NumberAnimation { duration: 110 } }
            }
        }
    }
}
