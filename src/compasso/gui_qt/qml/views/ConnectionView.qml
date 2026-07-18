// Barra de conexão: logo, MAC, canal, sensor e o estado de conexão do BITalino.
// Equivale ao antigo ConnectionFrame (top_frame.py). Dois estados mutuamente exclusivos:
// desconectado (botão "Conectar") e conectado (pill "● Conectado" + equalizador + "Desconectar").
import QtQuick
import QtQuick.Layouts
import "../components"

Card {
    id: view
    implicitHeight: linha.implicitHeight + 2 * Theme.metrics.padMd

    RowLayout {
        id: linha
        anchors.fill: parent
        spacing: Theme.metrics.padLg

        // ----- logo (desenhada em QML, compacta e à esquerda) -----
        LogoMark {
            Layout.alignment: Qt.AlignVCenter
            Layout.leftMargin: Theme.metrics.padSm
        }

        // divisor
        Rectangle {
            Layout.preferredWidth: 2
            Layout.preferredHeight: 46
            Layout.leftMargin: Theme.metrics.padSm
            radius: 1
            color: Theme.colors.border
        }

        // ----- MAC -----
        ColumnLayout {
            spacing: 5
            Caption { texto: "Endereço MAC" }
            AppTextField {
                id: campoMac
                mono: true
                enabled: !ctx.connected
                placeholderText: "XX:XX:XX:XX:XX:XX"
                Layout.preferredWidth: 210
                // reflete o MAC vindo de um .config carregado (apply_config).
                text: ctx.macAddr
                onAccepted: view._conectar()
            }
        }

        // ----- Canal -----
        ColumnLayout {
            spacing: 5
            Caption { texto: "Canal" }
            AppComboBox {
                id: comboCanal
                enabled: !ctx.connected
                Layout.preferredWidth: 82
                model: ["A1", "A2", "A3", "A4", "A5", "A6"]
                // reflete o canal de um .config carregado (A1 => índice 0).
                currentIndex: Math.max(0, ctx.signalChannel - 1)
                onActivated: connController.definir_canal(currentText)
            }
        }

        // ----- Sensor -----
        ColumnLayout {
            spacing: 5
            Caption { texto: "Sensor" }
            AppComboBox {
                id: comboSensor
                enabled: !ctx.connected
                Layout.preferredWidth: 92
                model: sensoresDisponiveis
                // reflete o sensor de um .config carregado.
                currentIndex: Math.max(0, sensoresDisponiveis.indexOf(ctx.sensorType))
                onActivated: connController.definir_sensor(currentText)
            }
        }

        Item { Layout.fillWidth: true }   // espaçador

        // ----- estado desconectado: botão Conectar -----
        AppButton {
            visible: !ctx.connected
            enabled: !connController.conectando && campoMac.text.length > 0
            text: connController.conectando ? "Conectando…" : "Conectar"
            dica: "Conectar ao Bitalino no endereço MAC informado"
            Layout.preferredWidth: 140
            onClicked: view._conectar()
        }

        // ----- estado conectado: pill + equalizador + Desconectar -----
        RowLayout {
            visible: ctx.connected
            spacing: Theme.metrics.padSm

            Rectangle {
                radius: Theme.metrics.cornerPill
                color: Theme.colors.accent_tint
                border.color: Theme.colors.accent_border
                border.width: 1
                implicitHeight: Theme.metrics.btnH
                implicitWidth: pillLinha.implicitWidth + 2 * Theme.metrics.padMd

                RowLayout {
                    id: pillLinha
                    anchors.centerIn: parent
                    spacing: Theme.metrics.padSm
                    Text {
                        text: "●"
                        color: Theme.colors.success
                        font.pixelSize: Theme.fonts.s10
                    }
                    Text {
                        text: "Conectado"
                        color: Theme.colors.accent
                        font.family: Theme.fonts.display
                        font.pixelSize: Theme.fonts.s13
                        font.bold: true
                    }
                    Equalizer { corBarra: Theme.colors.accent }
                }
            }

            GhostButton {
                text: "Desconectar"
                dica: "Encerrar a conexão com o Bitalino"
                Layout.preferredWidth: 120
                onClicked: connController.solicitar_desconectar()
            }
        }
    }

    function _conectar() {
        if (campoMac.text.length > 0 && !connController.conectando)
            connController.conectar(campoMac.text)
    }
}
