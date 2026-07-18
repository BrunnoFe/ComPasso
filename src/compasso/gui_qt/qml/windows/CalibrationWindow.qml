// Janela de Calibração de Volume (botão "Calibrar Volume" do PlayerBar). Modal, borderless
// (AppWindow), mesmo estilo de cantos arredondados da janela principal.
// Rampa de volume + máquina de estados (idle→base→idle→calibrar→salvar) no calibController.
import QtQuick
import QtQuick.Layouts
import "../components"
import "../"

AppWindow {
    id: win
    titulo: "Calibração de Volume"
    mostrarMax: false
    width: 600
    height: 480
    minimumWidth: 600
    minimumHeight: 480
    modality: Qt.ApplicationModal

    function abrir() {
        calibController.abrir()
        win.show(); win.raise(); win.requestActivate()
    }
    onClosing: calibController.fechar()

    // Mensagens e confirmação de salvamento.
    Connections {
        target: calibController
        function onMensagem(t, x, tipo) { dlgMsg.abrir(t, x, tipo) }
        function onConfirmarSalvar(volume) { dlgConfirmar.abrir(
            "Confirmar volume", "Confirma esse volume de " + volume + "%?") }
        // fecha a janela automaticamente após o volume ser confirmado/salvo.
        function onFecharJanela() { win.close() }
    }
    MessageDialog { id: dlgMsg }
    ConfirmDialog {
        id: dlgConfirmar
        textoSim: "Sim"
        textoNao: "Reiniciar"
        onConfirmado: calibController.resolver_salvar(true)
        onRecusado: calibController.resolver_salvar(false)
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.metrics.padLg
        spacing: Theme.metrics.padMd

        Text {
            text: "Calibração de Volume"
            color: Theme.colors.text
            font.family: Theme.fonts.display; font.pixelSize: Theme.fonts.s17; font.bold: true
            Layout.alignment: Qt.AlignHCenter
        }
        Text {
            text: "Ajuste o volume ideal para o participante antes da sessão."
            color: Theme.colors.faint
            font.family: Theme.fonts.display; font.pixelSize: Theme.fonts.s12
            Layout.alignment: Qt.AlignHCenter
        }

        FormSection {
            titulo: "Parâmetros"
            enabled: calibController.estado === "idle"
            opacity: enabled ? 1 : 0.5

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.metrics.padLg

                ColumnLayout {
                    spacing: 4
                    Caption { texto: "Vol. mínimo (%)" }
                    AppTextField {
                        Layout.preferredWidth: 78
                        horizontalAlignment: TextInput.AlignHCenter
                        text: calibController.volMin
                        onTextEdited: calibController.volMin = text
                    }
                }
                ColumnLayout {
                    spacing: 4
                    Caption { texto: "Vol. máximo (%)" }
                    AppTextField {
                        Layout.preferredWidth: 78
                        horizontalAlignment: TextInput.AlignHCenter
                        text: calibController.volMax
                        onTextEdited: calibController.volMax = text
                    }
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4
                    Caption { texto: "Aumentar X% do volume, a cada Y segundos" }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.metrics.padSm
                        AppSlider {
                            Layout.fillWidth: true
                            from: calibController.stepPctMin; to: calibController.stepPctMax; stepSize: 1
                            value: calibController.stepPct
                            onMovido: calibController.stepPct = Math.round(valor)
                        }
                        Text { text: calibController.stepPct + "%"; color: Theme.colors.muted
                               font.family: Theme.fonts.mono; font.pixelSize: Theme.fonts.s12; Layout.preferredWidth: 32 }
                        AppSlider {
                            Layout.fillWidth: true
                            from: calibController.stepSegMin; to: calibController.stepSegMax; stepSize: 1
                            value: calibController.stepSeg
                            onMovido: calibController.stepSeg = Math.round(valor)
                        }
                        Text { text: calibController.stepSeg + "s"; color: Theme.colors.muted
                               font.family: Theme.fonts.mono; font.pixelSize: Theme.fonts.s12; Layout.preferredWidth: 28 }
                    }
                }
            }
        }

        FormSection {
            titulo: "Reprodução"

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.metrics.padSm
                Text { text: calibController.tBegin; color: Theme.colors.muted
                       font.family: Theme.fonts.mono; font.pixelSize: Theme.fonts.s12 }
                Rectangle {
                    Layout.fillWidth: true; Layout.preferredHeight: 8; radius: 4; color: Theme.colors.border
                    Rectangle {
                        width: parent.width * calibController.progresso
                        height: parent.height; radius: parent.radius; color: Theme.colors.accent
                    }
                }
                Text { text: calibController.tEnd; color: Theme.colors.muted
                       font.family: Theme.fonts.mono; font.pixelSize: Theme.fonts.s12 }
            }

            Text {
                text: calibController.volLabel
                color: Theme.colors.text
                font.family: Theme.fonts.display; font.pixelSize: Theme.fonts.s19; font.bold: true
                Layout.alignment: Qt.AlignHCenter
                Layout.topMargin: Theme.metrics.padSm
            }
        }

        Item { Layout.fillHeight: true }

        // ---- botões (morfam conforme o estado) ----
        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            spacing: Theme.metrics.padSm

            GhostButton {
                Layout.preferredWidth: 160
                property bool ehParar: calibController.estado === "base"
                perigo: ehParar
                text: ehParar ? "Parar" : "Linha de Base"
                enabled: calibController.estado === "idle"
                        ? calibController.paramsValidos
                        : calibController.estado === "base"
                onClicked: calibController.estado === "base"
                          ? calibController.parar() : calibController.linha_base()
            }

            // Botão direito: Calibrar (accent) → Parar (danger) → Salvar (accent).
            Loader {
                sourceComponent: (calibController.estado === "calibrar") ? compParar
                                : (calibController.estado === "salvar") ? compSalvar : compCalibrar
            }
            Component {
                id: compCalibrar
                AppButton {
                    text: "Calibrar"; implicitWidth: 160
                    enabled: calibController.paramsValidos && calibController.baseOk
                             && calibController.estado === "idle"
                    onClicked: calibController.calibrar()
                }
            }
            Component {
                id: compParar
                GhostButton { text: "Parar"; perigo: true; implicitWidth: 160
                    onClicked: calibController.parar() }
            }
            Component {
                id: compSalvar
                AppButton { text: "Salvar"; implicitWidth: 160
                    onClicked: calibController.pedir_salvar() }
            }
        }
    }
}
