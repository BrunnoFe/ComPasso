// Indicador de progresso das etapas do experimento (equivale ao StepperFrame).
// Dirigido por dados: lê ctx.stepperSteps (lista de {rotulo, concluida, atual, pendente}).
// Cores: concluída = accent/"✓"; atual = accent-tint/"AGORA"; pendente = danger/"PENDENTE".
import QtQuick
import QtQuick.Layouts
import "../components"

Card {
    id: view
    // Em janelas estreitas as 6 etapas nao cabem numa linha: vira um Flow que quebra em varias
    // linhas e esconde os conectores (que so fazem sentido numa fileira unica horizontal).
    readonly property bool compacto: width > 0 && width < 1180
    implicitHeight: linha.implicitHeight + 2 * Theme.metrics.padMd

    Flow {
        id: linha
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        // sem conectores (modo compacto) o espacamento entre etapas vem daqui; na fileira unica
        // ele fica 0 e a separacao vem dos proprios conectores.
        spacing: view.compacto ? Theme.metrics.padLg : 0

        Repeater {
            model: ctx.stepperSteps
            delegate: RowLayout {
                required property var modelData
                required property int index
                spacing: 0

                // ---- etapa (badge + textos) ----
                RowLayout {
                    spacing: 11
                    Rectangle {
                        width: 28; height: 28; radius: 14
                        color: modelData.concluida ? Theme.colors.accent
                               : modelData.atual ? Theme.colors.accent_tint
                               : Theme.colors.danger_tint
                        Text {
                            anchors.centerIn: parent
                            text: modelData.concluida ? "✓" : (index + 1)
                            color: modelData.concluida ? Theme.colors.accent_ink
                                   : modelData.atual ? Theme.colors.accent : Theme.colors.danger
                            font.family: Theme.fonts.display
                            font.pixelSize: Theme.fonts.s13
                            font.bold: true
                        }
                    }
                    ColumnLayout {
                        spacing: 0
                        Text {
                            text: modelData.concluida ? "ETAPA " + (index + 1)
                                  : modelData.atual ? "AGORA" : "PENDENTE"
                            color: modelData.concluida ? Theme.colors.faint
                                   : modelData.atual ? Theme.colors.accent : Theme.colors.danger
                            font.family: Theme.fonts.display
                            font.pixelSize: Theme.fonts.s10
                            font.bold: true
                        }
                        Text {
                            text: modelData.rotulo
                            color: modelData.concluida ? Theme.colors.text
                                   : modelData.atual ? Theme.colors.accent : Theme.colors.danger
                            font.family: Theme.fonts.display
                            font.pixelSize: Theme.fonts.s14
                            font.bold: true
                        }
                    }
                }

                // ---- conector (some depois da última etapa e no modo compacto) ----
                Rectangle {
                    visible: !view.compacto && index < ctx.stepperSteps.length - 1
                    Layout.leftMargin: 18
                    Layout.rightMargin: 18
                    Layout.preferredWidth: 56
                    height: 2
                    radius: 2
                    color: modelData.concluida ? Theme.colors.accent : Theme.colors.border
                }
            }
        }
    }
}
