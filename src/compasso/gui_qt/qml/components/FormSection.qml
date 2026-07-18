// Seção de formulário com título + divisor, usada para agrupar campos relacionados nas
// janelas de configuração (Experimento/Gráfico/Calibração).
import QtQuick
import QtQuick.Layouts

ColumnLayout {
    id: secao
    property string titulo: ""
    default property alias conteudo: host.data

    Layout.fillWidth: true
    spacing: Theme.metrics.padSm

    Text {
        text: secao.titulo.toUpperCase()
        color: Theme.colors.accent
        font.family: Theme.fonts.display
        font.pixelSize: Theme.fonts.s11
        font.bold: true
        font.letterSpacing: 0.6
    }
    Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: 1
        color: Theme.colors.border
    }
    ColumnLayout {
        id: host
        Layout.fillWidth: true
        spacing: Theme.metrics.padMd
    }
}
