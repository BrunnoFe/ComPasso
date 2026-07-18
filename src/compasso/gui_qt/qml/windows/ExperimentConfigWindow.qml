// Janela de Configuração do Experimento (menu Experimento → Novo/Editar). Modal, borderless
// (AppWindow), com o mesmo estilo de cantos arredondados da janela principal.
// Editor do .config: campos ligados ao configController; salvar valida e aplica ao app.
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import QtQuick.Dialogs
import "../components"
import "../"

AppWindow {
    id: win
    titulo: configController.titulo
    mostrarMax: true
    width: 640
    height: 760
    minimumWidth: 640
    minimumHeight: 600
    modality: Qt.ApplicationModal

    function abrir() { win.show(); win.raise(); win.requestActivate() }

    // Diálogos de arquivo/pasta e de salvamento.
    FolderDialog { id: dlgMusicas; title: "Pasta de músicas"; onAccepted: configController.definir_musicas(selectedFolder) }
    FileDialog { id: dlgFatores; title: "Arquivo de fatores"; nameFilters: ["Excel (*.xlsx *.xls)"]; onAccepted: configController.definir_fatores(selectedFile) }
    FolderDialog { id: dlgSaida; title: "Pasta de salvamento"; onAccepted: configController.definir_saida(selectedFolder) }
    FileDialog { id: dlgCalib; title: "Faixa de áudio da calibração"; nameFilters: ["Áudio (*.wav *.ogg *.mp3)"]; onAccepted: configController.definir_calibracao(selectedFile) }
    FileDialog {
        id: dlgSalvarComo
        title: "Salvar configuração"; fileMode: FileDialog.SaveFile
        nameFilters: ["Configuração (*.config)"]; defaultSuffix: "config"
        onAccepted: configController.salvar_como(selectedFile)
    }
    ConfirmDialog { id: dlgSobrescrever; onConfirmado: configController.confirmar_sobrescrever() }
    Connections {
        target: configController
        function onPedirCaminhoSalvar() { dlgSalvarComo.open() }
        function onPedirConfirmarSobrescrever(nome) { dlgSobrescrever.abrir("Confirmar", "Sobrescrever " + nome + "?") }
        function onFecharJanela() { win.close() }
    }

    // Linha "caminho" reutilizável (rótulo + caminho read-only + botão Procurar).
    component LinhaCaminho: RowLayout {
        property alias rotulo: cap.texto
        property string caminho: ""
        signal procurar()
        Layout.fillWidth: true
        spacing: Theme.metrics.padSm
        ColumnLayout {
            Layout.fillWidth: true; spacing: 2
            Caption { id: cap }
            Text {
                text: caminho || "—"; color: Theme.colors.muted
                font.family: Theme.fonts.mono; font.pixelSize: Theme.fonts.s12
                elide: Text.ElideMiddle; Layout.fillWidth: true
            }
        }
        GhostButton { text: "Procurar"; Layout.preferredWidth: 96; onClicked: parent.procurar() }
    }

    // Campo de texto rotulado (rótulo + AppTextField), reutilizado nas várias seções.
    component CampoTexto: ColumnLayout {
        property alias rotulo: cap.texto
        property alias placeholder: campo.placeholderText
        property alias valor: campo.text
        property alias mono: campo.mono
        signal editado(string texto)
        Layout.fillWidth: true
        spacing: 2
        Caption { id: cap }
        AppTextField {
            id: campo
            Layout.fillWidth: true
            onTextEdited: parent.editado(text)
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.metrics.padLg
        spacing: Theme.metrics.padMd

        Text {
            text: configController.titulo
            color: Theme.colors.text; font.family: Theme.fonts.display
            font.pixelSize: Theme.fonts.s17; font.bold: true
            Layout.alignment: Qt.AlignHCenter
        }

        ScrollView {
            Layout.fillWidth: true; Layout.fillHeight: true
            contentWidth: availableWidth; clip: true

            ColumnLayout {
                width: parent.width
                spacing: Theme.metrics.padLg

                // ---- Músicas & Condições ----
                FormSection {
                    titulo: "Músicas & Condições"

                    LinhaCaminho { rotulo: "Pasta de músicas"; caminho: configController.musicFolder; onProcurar: dlgMusicas.open() }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.metrics.padLg
                        CampoTexto {
                            rotulo: "Quantidade de músicas"; placeholder: "Mín. 1"
                            valor: configController.musicQuantity
                            onEditado: (texto) => configController.musicQuantity = texto
                        }
                        CampoTexto {
                            rotulo: "Quantidade de ruído"; placeholder: "Mín. 0"
                            valor: configController.noiseQuantity
                            onEditado: (texto) => configController.noiseQuantity = texto
                        }
                    }

                    LinhaCaminho { rotulo: "Arquivo de fatores (.xlsx)"; caminho: configController.factorsFile; onProcurar: dlgFatores.open() }

                    // colunas (só quando há um arquivo de fatores lido)
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.metrics.padLg
                        visible: configController.colunas.length > 0
                        ColumnLayout {
                            Layout.fillWidth: true; spacing: 2
                            Caption { texto: "Coluna do nome dos áudios" }
                            AppComboBox {
                                Layout.fillWidth: true; model: configController.colunas
                                currentIndex: configController.colunas.indexOf(configController.musicColumn)
                                onActivated: configController.musicColumn = currentText
                            }
                        }
                        ColumnLayout {
                            Layout.fillWidth: true; spacing: 2
                            Caption { texto: "Coluna dos fatores" }
                            AppComboBox {
                                Layout.fillWidth: true; model: configController.colunas
                                currentIndex: configController.colunas.indexOf(configController.factorColumn)
                                onActivated: configController.factorColumn = currentText
                            }
                        }
                    }
                }

                // ---- Saída de dados ----
                FormSection {
                    titulo: "Saída de dados"
                    LinhaCaminho { rotulo: "Pasta de salvamento dos dados"; caminho: configController.dataSavePath; onProcurar: dlgSaida.open() }
                }

                // ---- BITalino ----
                FormSection {
                    titulo: "BITalino"

                    RowLayout {
                        Layout.fillWidth: true; spacing: Theme.metrics.padLg
                        ColumnLayout {
                            spacing: 2
                            Caption { texto: "Canal do BITalino" }
                            AppComboBox { Layout.preferredWidth: 110; model: configController.channels
                                currentIndex: configController.channels.indexOf(configController.bitalinoChannel)
                                onActivated: configController.bitalinoChannel = currentText }
                        }
                        ColumnLayout {
                            spacing: 2
                            Caption { texto: "Tipo de sensor" }
                            AppComboBox { Layout.preferredWidth: 120; model: configController.sensores
                                currentIndex: configController.sensores.indexOf(configController.sensorTypeSel)
                                onActivated: configController.sensorTypeSel = currentText }
                        }
                        Item { Layout.fillWidth: true }
                    }

                    CampoTexto {
                        rotulo: "Endereço MAC do BITalino"; placeholder: "XX:XX:XX:XX:XX:XX"; mono: true
                        valor: configController.bitalinoMac
                        onEditado: (texto) => configController.bitalinoMac = texto
                    }
                }

                // ---- Estímulo ----
                FormSection {
                    titulo: "Estímulo"

                    ColumnLayout {
                        Layout.fillWidth: true; spacing: 2
                        Caption { texto: "Tempo pré-estímulo (s)" }
                        RowLayout {
                            Layout.fillWidth: true
                            AppSlider { Layout.fillWidth: true
                                from: configController.preStimulusMin; to: configController.preStimulusMax; stepSize: 1
                                value: configController.preStimulus
                                onMovido: configController.preStimulus = Math.round(valor) }
                            Text { text: configController.preStimulus + " s"; color: Theme.colors.muted
                                font.family: Theme.fonts.mono; font.pixelSize: Theme.fonts.s12; Layout.preferredWidth: 40 }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true; spacing: Theme.metrics.padSm
                        AppSwitch { checked: configController.beepEnabled
                            onToggled: configController.beepEnabled = checked }
                        Text { text: "Tocar um beep antes de cada faixa"; color: Theme.colors.text
                            font.family: Theme.fonts.display; font.pixelSize: Theme.fonts.s13 }
                    }
                    RowLayout {
                        Layout.fillWidth: true; spacing: Theme.metrics.padSm
                        enabled: configController.beepEnabled
                        opacity: enabled ? 1 : 0.5
                        Text { text: "Tocar em t-"; color: Theme.colors.muted
                            font.family: Theme.fonts.display; font.pixelSize: Theme.fonts.s12 }
                        AppSlider { Layout.fillWidth: true
                            from: configController.beepLeadMin; to: configController.beepLeadMax; stepSize: 1
                            value: configController.beepLead
                            onMovido: configController.beepLead = Math.round(valor) }
                        Text { text: configController.beepLead + " s"
                            color: configController.beepInvalido ? Theme.colors.danger : Theme.colors.muted
                            font.family: Theme.fonts.mono; font.pixelSize: Theme.fonts.s12; Layout.preferredWidth: 40 }
                    }
                }

                // ---- Calibração ----
                FormSection {
                    titulo: "Calibração de volume"

                    RowLayout {
                        Layout.fillWidth: true; spacing: Theme.metrics.padSm
                        AppSwitch { checked: configController.calibrationEnabled
                            onToggled: configController.calibrationEnabled = checked }
                        Text { text: "Habilitar calibração de volume do participante"; color: Theme.colors.text
                            font.family: Theme.fonts.display; font.pixelSize: Theme.fonts.s13 }
                    }
                    LinhaCaminho {
                        enabled: configController.calibrationEnabled
                        opacity: enabled ? 1 : 0.5
                        rotulo: "Faixa de áudio da calibração"
                        caminho: configController.calibrationAudio; onProcurar: dlgCalib.open()
                    }
                }
            }
        }

        RowLayout {
            Layout.alignment: Qt.AlignRight
            spacing: Theme.metrics.padSm
            GhostButton { text: "Cancelar"; onClicked: win.close() }
            AppButton { text: "Salvar"; onClicked: configController.salvar() }
        }
    }
}
