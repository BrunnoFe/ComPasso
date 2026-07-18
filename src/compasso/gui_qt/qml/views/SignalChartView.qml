// Gráfico do sinal do BITalino em tempo real. Equivale ao GraphFrame/GraficoSinal antigos.
// Usa o item nativo GraficoSinal (QQuickPaintedItem/QPainter) — leve, sem QtCharts/OpenGL. O
// item recebe o Context (registra-se em ctx.signal_plot para o runner) e a paleta do tema.
// Cabeçalho: canal + leitura ao vivo, ambos vindos do próprio item.
import QtQuick
import QtQuick.Layouts
import Compasso 1.0
import "../components"

Card {
    id: view
    implicitHeight: 300 + cabecalho.implicitHeight + 3 * Theme.metrics.padMd

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.metrics.padSm

        RowLayout {
            id: cabecalho
            Layout.fillWidth: true
            Caption { texto: grafico.canal; Layout.fillWidth: true }
            Text {
                text: grafico.leitura
                color: Theme.colors.accent
                font.family: Theme.fonts.mono
                font.pixelSize: Theme.fonts.s13
                horizontalAlignment: Text.AlignRight
            }
        }

        // Área do gráfico: o item pintado + os botões de escala numa sobreposição irmã (o
        // GraficoSinal permanece SEM filhos — pôr filhos num QQuickPaintedItem atrapalhava o
        // desenho em tempo real da linha e do ponteiro).
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            GraficoSinal {
                id: grafico
                anchors.fill: parent
                contexto: ctx
                // paleta do tema (recolore a grade/linha/rótulos ao trocar de tema).
                paleta: {
                    var p = Theme.colors
                    var m = {}
                    for (var k in p) m[k] = p[k]
                    m["_display"] = Theme.fonts.display
                    return m
                }
            }

            // ---- botões de escala Y (+/-) ao lado do eixo, ativos mesmo durante a gravação ----
            // "+" amplia o sinal (zoom in); "−" afasta. Só trocam o fator de escala e repintam
            // (barato — a decimação guarda valores brutos, sem reprocessar).
            component BotaoEscala: Rectangle {
                id: botEsc
                property alias simbolo: txt.text
                property bool habilitado: true
                property string dica: ""
                signal acionado()
                width: 26; height: 26
                radius: Theme.metrics.cornerSm
                color: escHover.hovered && habilitado ? Theme.colors.input_bg : Theme.colors.bar_bg
                opacity: habilitado ? 0.92 : 0.4
                border.color: Theme.colors.border
                border.width: 1
                Text {
                    id: txt
                    anchors.centerIn: parent
                    color: escHover.hovered && botEsc.habilitado ? Theme.colors.accent : Theme.colors.muted
                    font.family: Theme.fonts.display
                    font.pixelSize: Theme.fonts.s16
                    font.bold: true
                }
                HoverHandler { id: escHover; enabled: botEsc.habilitado; cursorShape: Qt.PointingHandCursor }
                Dica { parent: botEsc; visible: escHover.hovered && botEsc.dica.length > 0; text: botEsc.dica }
                TapHandler { enabled: botEsc.habilitado; onTapped: botEsc.acionado() }
            }

            ColumnLayout {
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.leftMargin: 58   // logo à direita do eixo/rótulos Y
                anchors.topMargin: 12
                spacing: 6

                BotaoEscala {
                    simbolo: "+"
                    dica: "Ampliar o sinal (reduzir a escala do eixo Y)"
                    habilitado: grafico.escalaAtual > grafico.escalaMin
                    onAcionado: grafico.ampliar_zoom()
                }
                BotaoEscala {
                    simbolo: "−"
                    dica: "Afastar o sinal (aumentar a escala do eixo Y)"
                    habilitado: grafico.escalaAtual < grafico.escalaMax
                    onAcionado: grafico.reduzir_zoom()
                }
            }
        }
    }
}
