// Conteúdo scrollável principal (equivale ao MainFrame/CTkScrollableFrame).
// Empilha ConnectionView, StepperView e a dupla de cartões (Participante | Arquivos).
// O recolhimento é em lockstep: `recolhido` combina o pedido manual (chevron) com o
// bloqueio do experimento (ctx.cardsCollapsed), que também desabilita o chevron.
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../components"
import "../views"

ScrollView {
    id: root
    contentWidth: availableWidth
    clip: true

    // pedido manual de recolher (chevron) + trava do experimento.
    property bool recolherManual: false
    readonly property bool recolhido: ctx.cardsCollapsed || recolherManual

    // se o experimento travar a UI, respeita o estado travado (não deixa "meio-recolhido").
    Connections {
        target: ctx
        function onCardsCollapsedChanged() { root.recolherManual = ctx.cardsCollapsed }
    }

    ColumnLayout {
        width: root.availableWidth
        spacing: Theme.metrics.padMd

        ConnectionView { Layout.fillWidth: true }
        StepperView { Layout.fillWidth: true }

        // Card único (participante | divisor | arquivos), colapsa por um só chevron.
        CartaoConfig {
            Layout.fillWidth: true
            recolhido: root.recolhido
            onAlternar: root.recolherManual = !root.recolherManual
        }

        PlayerBarView { Layout.fillWidth: true }
        SignalChartView { Layout.fillWidth: true }

        Item { Layout.fillHeight: true }
    }
}
