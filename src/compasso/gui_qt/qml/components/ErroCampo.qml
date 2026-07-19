// Aviso curto de validação, centralizado abaixo do campo a que se refere. Some por completo
// quando não há erro (`visible: false` + altura zero), para o formulário não "pular" de tamanho
// ao aparecer e desaparecer.
//
// Acompanha a borda vermelha de `AppTextField.erro`/`AppComboBox.erro`: a borda aponta ONDE
// está o problema, este texto diz QUAL é.
import QtQuick
import QtQuick.Layouts

Text {
    id: aviso
    property string texto: ""

    text: texto
    visible: texto.length > 0
    color: Theme.colors.danger
    font.family: Theme.fonts.display
    font.pixelSize: Theme.fonts.s11
    wrapMode: Text.WordWrap
    horizontalAlignment: Text.AlignHCenter

    Layout.fillWidth: true
    Layout.topMargin: visible ? 2 : 0
    Layout.preferredHeight: visible ? implicitHeight : 0
}
