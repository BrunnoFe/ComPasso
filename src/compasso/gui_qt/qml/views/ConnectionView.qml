// Barra de conexão: logo, MAC, canal, sensor e o estado de conexão do BITalino.
// Equivale ao antigo ConnectionFrame (top_frame.py). Dois estados mutuamente exclusivos:
// desconectado (botão "Conectar") e conectado (pill "● Conectado" + equalizador + "Desconectar").
//
// Layout responsivo: em janelas largas, tudo numa linha (logo · MAC · canal · sensor ····
// [Conectar] à direita). Em janelas estreitas (`compacto`), os campos quebram num Flow e o
// estado de conexão desce para baixo — nada fica cortado. As duas montagens compartilham o
// mesmo estado (view.macDigitado + ctx/controllers), então não há duplicação de dados.
import QtQuick
import QtQuick.Layouts
import "../components"

Card {
    id: view
    readonly property bool compacto: width > 0 && width < 860
    // MAC digitado (ou vindo de um .config via ctx.macAddr); ligado às duas montagens.
    property string macDigitado: ctx.macAddr
    implicitHeight: (compacto ? compactoCol.implicitHeight : linhaWide.implicitHeight)
                    + 2 * Theme.metrics.padMd

    // -------------------------------------------------------- componentes reutilizáveis
    component GrupoMac: ColumnLayout {
        spacing: 5
        Caption { texto: "Endereço MAC" }
        AppTextField {
            mono: true
            enabled: !ctx.connected
            placeholderText: "XX:XX:XX:XX:XX:XX"
            Layout.preferredWidth: 210
            text: view.macDigitado
            onTextEdited: view.macDigitado = text
            onAccepted: view._conectar()
        }
    }
    component GrupoCanal: ColumnLayout {
        spacing: 5
        Caption { texto: "Canal" }
        AppComboBox {
            enabled: !ctx.connected
            Layout.preferredWidth: 82
            model: ["A1", "A2", "A3", "A4", "A5", "A6"]
            // reflete o canal de um .config carregado (A1 => índice 0).
            currentIndex: Math.max(0, ctx.signalChannel - 1)
            onActivated: connController.definir_canal(currentText)
        }
    }
    component GrupoSensor: ColumnLayout {
        spacing: 5
        Caption { texto: "Sensor" }
        AppComboBox {
            enabled: !ctx.connected
            Layout.preferredWidth: 92
            model: sensoresDisponiveis
            // reflete o sensor de um .config carregado.
            currentIndex: Math.max(0, sensoresDisponiveis.indexOf(ctx.sensorType))
            onActivated: connController.definir_sensor(currentText)
        }
    }
    // Estado de conexão (Conectar OU pill "Conectado" + equalizador + Desconectar).
    component EstadoConexao: RowLayout {
        spacing: Theme.metrics.padSm

        AppButton {
            visible: !ctx.connected
            enabled: !connController.conectando && view.macDigitado.length > 0
            // com o simulador no ar o botão fica VERMELHO e assumido como "(teste)": os dados
            // que virão não são do participante, e isso precisa saltar aos olhos antes do
            // clique, não só no diálogo depois dele.
            text: connController.conectando ? "Conectando…"
                  : ctx.simulacaoAtiva ? "Conectar (teste)" : "Conectar"
            corFundo: ctx.simulacaoAtiva ? Theme.colors.danger : Theme.colors.accent
            // o "ink" do acento não tem contraste sobre o vermelho; o fundo da janela tem.
            corTexto: ctx.simulacaoAtiva ? Theme.colors.win_bg : Theme.colors.accent_ink
            dica: ctx.simulacaoAtiva
                  ? "Modo de teste ativo: conectará ao BITalino SIMULADO, não ao aparelho real"
                  : "Conectar ao Bitalino no endereço MAC informado"
            Layout.preferredWidth: ctx.simulacaoAtiva ? 170 : 140
            onClicked: view._conectar()
        }

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

    // ------------------------------------------------------------ montagem larga (1 linha)
    RowLayout {
        id: linhaWide
        visible: !view.compacto
        anchors.fill: parent
        spacing: Theme.metrics.padLg

        LogoMark {
            Layout.alignment: Qt.AlignVCenter
            Layout.leftMargin: Theme.metrics.padSm
        }
        Rectangle {
            Layout.preferredWidth: 2
            Layout.preferredHeight: 46
            Layout.leftMargin: Theme.metrics.padSm
            radius: 1
            color: Theme.colors.border
        }
        GrupoMac {}
        GrupoCanal {}
        GrupoSensor {}
        Item { Layout.fillWidth: true }   // espaçador empurra o estado para a direita
        EstadoConexao {}
    }

    // ------------------------------------------------- montagem compacta (campos + estado abaixo)
    ColumnLayout {
        id: compactoCol
        visible: view.compacto
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        spacing: Theme.metrics.padMd

        Flow {
            Layout.fillWidth: true
            spacing: Theme.metrics.padLg
            LogoMark {}
            GrupoMac {}
            GrupoCanal {}
            GrupoSensor {}
        }
        EstadoConexao { Layout.fillWidth: true }
    }

    function _conectar() {
        // passa por `solicitar_conectar`: é ele que intercepta o modo de teste e pede
        // confirmação antes de conectar ao simulador.
        if (view.macDigitado.length > 0 && !connController.conectando)
            connController.solicitar_conectar(view.macDigitado)
    }
}
