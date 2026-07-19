// Janelinha da verificação manual de atualizações (menu "Atualizações").
// Um único diálogo que muda de conteúdo conforme `updatesController.estado`:
//   verificando → círculo girando + "Verificando" com reticências animadas
//   disponivel  → versão publicada, com "Baixar" e "Cancelar"
//   atualizado  → "Você está utilizando a versão mais recente!", com "OK"
//   erro        → motivo da falha, com "OK"
// Segue o layout padronizado do MessageDialog/ConfirmDialog (badge + título + corpo + rodapé).
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

Dialog {
    id: dlg
    modal: true
    anchors.centerIn: parent
    padding: 0
    implicitWidth: 420
    // durante a consulta não há decisão a tomar: fechar no Esc cancelaria só a janela, não a
    // verificação, e deixaria o usuário sem a resposta que pediu.
    closePolicy: estado === "verificando" ? Popup.NoAutoClose : Popup.CloseOnEscape

    readonly property string estado: updatesController.estado
    readonly property bool ehErro: estado === "erro"
    readonly property bool ehDisponivel: estado === "disponivel"

    function abrir() { dlg.open() }
    onClosed: updatesController.fechar()

    Overlay.modal: Rectangle { color: "#99000000" }

    background: Rectangle {
        radius: Theme.metrics.cornerCard
        color: Theme.colors.bar_bg
        border.color: dlg.ehDisponivel ? Theme.colors.accent_border : Theme.colors.border
        border.width: 1
    }

    header: null
    footer: null

    contentItem: ColumnLayout {
        spacing: Theme.metrics.padMd

        // ---- cabeçalho: badge + título ----
        RowLayout {
            Layout.fillWidth: true
            Layout.margins: Theme.metrics.padLg
            Layout.bottomMargin: 0
            spacing: Theme.metrics.padMd

            // Badge: durante a consulta é um anel girando; depois, um ícone de estado.
            Item {
                Layout.preferredWidth: 34; Layout.preferredHeight: 34

                Rectangle {
                    anchors.fill: parent
                    radius: 17
                    visible: dlg.estado !== "verificando"
                    color: dlg.ehErro ? Theme.colors.danger_tint : Theme.colors.accent_tint
                    Text {
                        anchors.centerIn: parent
                        text: dlg.ehErro ? "!" : dlg.ehDisponivel ? "↓" : "✓"
                        color: dlg.ehErro ? Theme.colors.danger : Theme.colors.accent
                        font.family: Theme.fonts.display
                        font.pixelSize: Theme.fonts.s17
                        font.bold: true
                    }
                }

                // anel de carregamento: arco de 270° girando continuamente.
                Canvas {
                    id: anel
                    anchors.fill: parent
                    visible: dlg.estado === "verificando"
                    antialiasing: true
                    property real angulo: 0
                    property color cor: Theme.colors.accent
                    onAnguloChanged: requestPaint()
                    onCorChanged: requestPaint()
                    onPaint: {
                        var c = getContext("2d")
                        c.reset()
                        var cx = width / 2, cy = height / 2, r = width / 2 - 3
                        c.lineWidth = 3
                        c.lineCap = "round"
                        c.strokeStyle = cor
                        c.beginPath()
                        c.arc(cx, cy, r, angulo, angulo + Math.PI * 1.5)
                        c.stroke()
                    }
                    NumberAnimation on angulo {
                        running: anel.visible
                        loops: Animation.Infinite
                        from: 0; to: Math.PI * 2; duration: 900
                    }
                }
            }

            Text {
                Layout.fillWidth: true
                text: dlg.estado === "verificando" ? "Verificando" + pontos.texto
                    : dlg.ehDisponivel ? "Atualização disponível"
                    : dlg.ehErro ? "Não foi possível verificar"
                    : "Tudo em dia"
                color: dlg.ehErro ? Theme.colors.danger : Theme.colors.text
                font.family: Theme.fonts.display
                font.pixelSize: Theme.fonts.s15
                font.bold: true
                wrapMode: Text.WordWrap
                verticalAlignment: Text.AlignVCenter

                // reticências animadas ("." → ".." → "...") enquanto a consulta corre.
                QtObject {
                    id: pontos
                    property int n: 1
                    readonly property string texto: ".".repeat(n)
                }
                Timer {
                    interval: 420; repeat: true; running: dlg.estado === "verificando"
                    onTriggered: pontos.n = (pontos.n % 3) + 1
                }
            }
        }

        // ---- corpo ----
        Text {
            Layout.fillWidth: true
            Layout.leftMargin: Theme.metrics.padLg
            Layout.rightMargin: Theme.metrics.padLg
            text: dlg.estado === "verificando"
                    ? "Consultando a página de releases do projeto…"
                : dlg.ehDisponivel
                    ? "A versão " + updatesController.versaoRemota + " já está publicada. "
                      + "Você está usando a " + updatesController.versaoAtual + "."
                : dlg.ehErro
                    ? updatesController.erro + "\n\nVerifique sua conexão e tente novamente."
                    : "Você está utilizando a versão mais recente!"
            color: Theme.colors.muted
            font.family: Theme.fonts.display
            font.pixelSize: Theme.fonts.s13
            lineHeight: 1.25
            wrapMode: Text.WordWrap
        }

        // ---- rodapé ----
        RowLayout {
            Layout.fillWidth: true
            Layout.margins: Theme.metrics.padLg
            Layout.topMargin: Theme.metrics.padSm
            spacing: Theme.metrics.padSm
            Item { Layout.fillWidth: true }

            GhostButton {
                text: "Cancelar"
                visible: dlg.ehDisponivel
                Layout.preferredWidth: 110
                onClicked: dlg.close()
            }
            AppButton {
                text: dlg.ehDisponivel ? "Baixar" : "OK"
                visible: dlg.estado !== "verificando"
                Layout.preferredWidth: 110
                onClicked: {
                    if (dlg.ehDisponivel)
                        updatesController.abrir_releases()
                    dlg.close()
                }
            }
        }
    }
}
