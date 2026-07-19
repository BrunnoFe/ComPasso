// Janela "Configurações do Gráfico" (menu Configurações → Gráfico). Preview ao vivo + salvar.
// Modal, borderless (AppWindow), mesmo estilo de cantos arredondados da janela principal.
// Ligada ao graphSettingsController.
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../components"
import "../"

AppWindow {
    id: win
    titulo: "Configurações do Gráfico"
    mostrarMax: false
    width: 600
    height: 660
    minimumWidth: 600
    minimumHeight: 660
    modality: Qt.ApplicationModal

    function abrir() {
        graphSettingsController.abrir()
        win.show()
        win.raise()
        win.requestActivate()
    }

    onClosing: graphSettingsController.cancelar()

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.metrics.padLg
        spacing: Theme.metrics.padMd

        Text {
            text: "Configurações do Gráfico"
            color: Theme.colors.text
            font.family: Theme.fonts.display
            font.pixelSize: Theme.fonts.s17
            font.bold: true
            Layout.alignment: Qt.AlignHCenter
        }

        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentWidth: availableWidth
            clip: true

            ColumnLayout {
                width: parent.width
                spacing: Theme.metrics.padLg

                FormSection {
                    titulo: "Escala"

                    ColumnLayout {
                        Layout.fillWidth: true; spacing: 4
                        Caption { texto: "Escala do eixo Y" }
                        RowLayout {
                            Layout.fillWidth: true
                            Text {
                                text: "−" + graphSettingsController.yScale.toFixed(1) + " " + graphSettingsController.unidade
                                color: Theme.colors.muted; font.family: Theme.fonts.mono; font.pixelSize: Theme.fonts.s11
                                Layout.preferredWidth: 74
                            }
                            AppSlider {
                                Layout.fillWidth: true
                                from: graphSettingsController.yMin; to: graphSettingsController.yMax
                                stepSize: graphSettingsController.yStep
                                value: graphSettingsController.yScale
                                // habilitado TAMBÉM durante a sessão: é o mesmo ajuste dos
                                // botões +/- de zoom ao vivo, que sempre funcionaram gravando.
                                onMovido: graphSettingsController.yScale = valor
                            }
                            Text {
                                text: "+" + graphSettingsController.yScale.toFixed(1) + " " + graphSettingsController.unidade
                                color: Theme.colors.muted; font.family: Theme.fonts.mono; font.pixelSize: Theme.fonts.s11
                                Layout.preferredWidth: 74
                                horizontalAlignment: Text.AlignRight
                            }
                        }
                        Text {
                            visible: graphSettingsController.sessaoAtiva
                            text: "A escala pode ser ajustada durante o experimento — é só exibição, "
                                  + "o dado gravado não muda."
                            color: Theme.colors.faint; font.family: Theme.fonts.display; font.pixelSize: Theme.fonts.s11
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                    }
                }

                FormSection {
                    titulo: "Curva"

                    RowLayout {
                        Layout.fillWidth: true; spacing: Theme.metrics.padLg
                        ColumnLayout {
                            Layout.fillWidth: true; spacing: 4
                            Caption { texto: "Média móvel (suavização)" }
                            RowLayout {
                                Layout.fillWidth: true
                                AppSwitch {
                                    checked: graphSettingsController.smoothingEnabled
                                    onToggled: graphSettingsController.smoothingEnabled = checked
                                }
                                AppSlider {
                                    Layout.fillWidth: true
                                    from: 1; to: 15; stepSize: 1
                                    enabled: graphSettingsController.smoothingEnabled
                                    value: graphSettingsController.smoothingWindow
                                    onMovido: graphSettingsController.smoothingWindow = Math.round(valor)
                                }
                                Text {
                                    text: graphSettingsController.smoothingWindow
                                    color: Theme.colors.muted; font.family: Theme.fonts.mono; font.pixelSize: Theme.fonts.s11
                                    Layout.preferredWidth: 24
                                }
                            }
                        }
                        ColumnLayout {
                            spacing: 4
                            Caption { texto: "Espessura da linha" }
                            RowLayout {
                                spacing: Theme.metrics.padSm
                                AppSlider {
                                    Layout.preferredWidth: 120
                                    from: 0.5; to: 4.0; stepSize: 0.5
                                    value: graphSettingsController.lineWidth
                                    onMovido: graphSettingsController.lineWidth = valor
                                }
                                Text {
                                    text: graphSettingsController.lineWidth.toFixed(1) + " px"
                                    color: Theme.colors.muted; font.family: Theme.fonts.mono; font.pixelSize: Theme.fonts.s11
                                    Layout.preferredWidth: 44
                                }
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true; spacing: Theme.metrics.padLg
                        ColumnLayout {
                            spacing: 2
                            Caption { texto: "Rótulo de valor" }
                            AppComboBox {
                                Layout.preferredWidth: 160
                                model: ["Valor bruto", "Média"]
                                currentIndex: graphSettingsController.valueMode === "mean" ? 1 : 0
                                onActivated: graphSettingsController.valueMode = currentText
                            }
                        }
                        Item { Layout.fillWidth: true }
                    }
                }

                FormSection {
                    titulo: "Exibição"

                    RowLayout {
                        Layout.fillWidth: true; spacing: Theme.metrics.padLg
                        RowLayout {
                            spacing: Theme.metrics.padSm
                            AppSwitch {
                                checked: graphSettingsController.gridVisible
                                onToggled: graphSettingsController.gridVisible = checked
                            }
                            Text { text: "Linhas de grade"; color: Theme.colors.text
                                font.family: Theme.fonts.display; font.pixelSize: Theme.fonts.s13 }
                        }
                        RowLayout {
                            spacing: Theme.metrics.padSm
                            AppSwitch {
                                checked: graphSettingsController.labelsVisible
                                onToggled: graphSettingsController.labelsVisible = checked
                            }
                            Text { text: "Rótulos dos eixos"; color: Theme.colors.text
                                font.family: Theme.fonts.display; font.pixelSize: Theme.fonts.s13 }
                        }
                        Item { Layout.fillWidth: true }
                    }
                }
            }
        }

        RowLayout {
            Layout.alignment: Qt.AlignRight
            spacing: Theme.metrics.padSm
            GhostButton { text: "Restaurar padrões"; onClicked: graphSettingsController.restaurar() }
            GhostButton { text: "Cancelar"; onClicked: { graphSettingsController.cancelar(); win.close() } }
            AppButton { text: "Salvar"; onClicked: { graphSettingsController.salvar(); win.close() } }
        }
    }
}
