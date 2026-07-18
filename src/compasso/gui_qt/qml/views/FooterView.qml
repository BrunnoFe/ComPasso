// Rodapé fixo: contadores (Estímulos/Ruído), status + progresso da sessão e botão principal.
// Equivale ao DownFrame (bottom_frame.py). O botão alterna comecar/rodando/continuar por
// ctx.buttonState (dirigido pelo ExperimentRunner). Os contadores/progresso são reativos no ctx.
import QtQuick
import QtQuick.Layouts
import "../components"

Rectangle {
    id: rodape
    color: Theme.colors.footer_bg
    implicitHeight: linha.implicitHeight + 2 * Theme.metrics.padMd
    // Arredondamento dos cantos inferiores (acompanha o canto da janela frameless).
    property real raioInferior: 0
    bottomLeftRadius: raioInferior
    bottomRightRadius: raioInferior

    Rectangle {
        anchors { left: parent.left; right: parent.right; top: parent.top }
        height: 1
        color: Theme.colors.border
    }

    RowLayout {
        id: linha
        anchors.fill: parent
        anchors.margins: Theme.metrics.padMd
        anchors.leftMargin: Theme.metrics.padLg
        anchors.rightMargin: Theme.metrics.padLg
        spacing: Theme.metrics.padLg

        // ---- contadores ----
        component Contador: ColumnLayout {
            property alias rotulo: cap.texto
            property string feito: "0"
            property string total: "0"
            spacing: 0
            Caption { id: cap }
            RowLayout {
                spacing: 2
                Text {
                    text: feito
                    color: Theme.colors.text
                    font.family: Theme.fonts.display
                    font.pixelSize: Theme.fonts.s19
                    font.bold: true
                }
                Text {
                    text: " / " + total
                    color: Theme.colors.faint2
                    font.family: Theme.fonts.display
                    font.pixelSize: Theme.fonts.s14
                    Layout.alignment: Qt.AlignBottom
                    bottomPadding: 2
                }
            }
        }

        Contador { rotulo: "Estímulos"; feito: ctx.musicDoneText; total: ctx.musicTotalText }
        Contador { rotulo: "Ruído"; feito: ctx.ruidoDoneText; total: ctx.ruidoTotalText }

        // ---- status + progresso da sessão ----
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 6
            RowLayout {
                Layout.fillWidth: true
                Text {
                    text: ctx.statusText
                    color: Theme.colors.muted
                    font.family: Theme.fonts.display
                    font.pixelSize: Theme.fonts.s12
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
                Text {
                    text: ctx.sessionStatusText
                    color: Theme.colors.faint
                    font.family: Theme.fonts.mono
                    font.pixelSize: Theme.fonts.s12
                }
            }
            // barra de progresso da sessão (pill)
            Rectangle {
                Layout.fillWidth: true
                height: 6
                radius: 3
                color: Theme.colors.border
                Rectangle {
                    width: parent.width * Math.max(0, Math.min(1, ctx.sessionProgress))
                    height: parent.height
                    radius: parent.radius
                    color: Theme.colors.accent
                    Behavior on width { NumberAnimation { duration: 200 } }
                }
            }
        }

        // ---- botão principal ----
        AppButton {
            id: botaoPrincipal
            Layout.preferredWidth: 176
            Layout.preferredHeight: Theme.metrics.actionBtnH
            enabled: ctx.buttonState !== "rodando"
            text: ctx.buttonState === "rodando" ? "Executando…"
                  : ctx.buttonState === "continuar" ? "Continuar  →" : "Começar"
            dica: ctx.buttonState === "rodando" ? "Experimento em andamento"
                  : ctx.buttonState === "continuar" ? "Avançar para a próxima faixa"
                  : "Iniciar o experimento"
            onClicked: {
                if (ctx.buttonState === "continuar") experimentController.continuar()
                else experimentController.comecar()
            }
        }
    }
}
