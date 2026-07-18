// Barra do player: faixa atual, indicador de gravação, chip de condição, progresso da faixa,
// volume (com trava) e os botões Parar/Calibrar. Equivale à PlayerBar (mid_frame.py).
// Altura fixa (rec/chip sempre presentes, só texto/cor mudam) — evita "resize" do cartão.
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../components"

Card {
    id: view
    implicitHeight: grade.implicitHeight + 2 * Theme.metrics.padMd

    ColumnLayout {
        id: grade
        anchors.fill: parent
        spacing: Theme.metrics.padMd

        // ---- linha superior: faixa/gravação/condição · volume+calibrar · parar ----
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.metrics.padLg

            // ---- faixa + gravação + condição (altura reservada) ----
            ColumnLayout {
                Layout.preferredWidth: 240
                Layout.alignment: Qt.AlignVCenter
                spacing: 5
                Text {
                    text: ctx.currentMusicText
                    color: Theme.colors.text
                    font.family: Theme.fonts.display
                    font.pixelSize: Theme.fonts.s15
                    font.bold: true
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
                RowLayout {
                    spacing: Theme.metrics.padSm
                    Layout.preferredHeight: 22
                    // indicador GRAVANDO (sempre presente; texto/cor mudam)
                    RowLayout {
                        spacing: 6
                        Text {
                            text: playerController.gravando ? "●" : ""
                            color: Theme.colors.danger
                            font.pixelSize: Theme.fonts.s10
                        }
                        Text {
                            text: playerController.gravando ? "GRAVANDO" : ""
                            color: Theme.colors.danger
                            font.family: Theme.fonts.display
                            font.pixelSize: Theme.fonts.s11
                            font.bold: true
                        }
                    }
                    // chip de condição (sempre presente; fundo/texto mudam)
                    Rectangle {
                        Layout.preferredHeight: 22
                        implicitWidth: chipTexto.implicitWidth + 2 * Theme.metrics.padSm
                        radius: Theme.metrics.cornerChip
                        color: ctx.currentConditionText.length > 0 ? Theme.colors.accent_tint : "transparent"
                        Text {
                            id: chipTexto
                            anchors.centerIn: parent
                            text: ctx.currentConditionText
                            color: Theme.colors.accent
                            font.family: Theme.fonts.display
                            font.pixelSize: Theme.fonts.s11
                            font.bold: true
                        }
                    }
                }
            }

            Item { Layout.fillWidth: true }

            // ---- volume + calibrar ----
            ColumnLayout {
                Layout.alignment: Qt.AlignVCenter
                spacing: 6
                RowLayout {
                    Layout.alignment: Qt.AlignRight
                    spacing: Theme.metrics.padSm
                    Text {
                        text: "Volume"
                        color: Theme.colors.muted
                        font.family: Theme.fonts.display
                        font.pixelSize: Theme.fonts.s12
                    }
                    AppSlider {
                        id: sliderVol
                        from: 0; to: 100; stepSize: 1
                        value: playerController.volume
                        enabled: !playerController.volumeTravado
                        implicitWidth: 150
                        onMovido: playerController.definir_volume(Math.round(valor))
                    }
                    Text {
                        text: ctx.volumeText
                        color: Theme.colors.text
                        font.family: Theme.fonts.mono
                        font.pixelSize: Theme.fonts.s12
                        Layout.preferredWidth: 36
                    }
                }
                GhostButton {
                    visible: playerController.calibrarVisivel
                    enabled: playerController.calibrarHabilitado
                    text: "Calibrar Volume"
                    dica: "Ajustar o volume ideal com o participante antes da sessão"
                    Layout.alignment: Qt.AlignHCenter
                    Layout.preferredHeight: 30
                    onClicked: playerController.calibrar()
                }
            }

            // ---- parar ----
            GhostButton {
                text: "Parar"
                perigo: true
                dica: "Parar o experimento em andamento"
                Layout.preferredWidth: 96
                Layout.preferredHeight: Theme.metrics.actionBtnH
                Layout.alignment: Qt.AlignVCenter
                onClicked: playerController.parar()
            }
        }

        // ---- linha inferior: progresso da faixa (largura total) ----
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.metrics.padMd
            Text {
                text: ctx.timeBeginText
                color: Theme.colors.muted
                font.family: Theme.fonts.mono
                font.pixelSize: Theme.fonts.s12
                Layout.preferredWidth: 40
            }
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 10
                radius: 5
                color: Theme.colors.border
                Rectangle {
                    width: parent.width * playerController.musicProgress
                    height: parent.height
                    radius: parent.radius
                    color: Theme.colors.accent
                }
            }
            Text {
                text: ctx.timeEndText
                color: Theme.colors.muted
                font.family: Theme.fonts.mono
                font.pixelSize: Theme.fonts.s12
                Layout.preferredWidth: 40
                horizontalAlignment: Text.AlignRight
            }
        }
    }
}
