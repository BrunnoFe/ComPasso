// Janela "Configurações → App" (preferências do aplicativo). Modal, borderless (AppWindow).
// Organizada em abas porque a lista é longa e heterogênea — arranque, aparência, arquivos,
// conexão, diagnóstico e avançado não competem pela atenção do usuário ao mesmo tempo.
//
// A aba "Avançado" reúne o que ainda toca a coleta (faixa etária, palavras de ruído, volume) e
// por isso nasce desabilitada, atrás de um consentimento explícito: o app é distribuído
// publicamente, e essas opções mudam o dado, não o conforto.
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import QtQuick.Dialogs
import "../components"
import "../"

AppWindow {
    id: win
    titulo: "Configurações do App"
    mostrarMax: false
    width: 680
    height: 620
    minimumWidth: 680
    minimumHeight: 620
    modality: Qt.ApplicationModal

    function abrir() {
        appSettingsController.abrir()
        win.show()
        win.raise()
        win.requestActivate()
    }

    onClosing: appSettingsController.cancelar()

    // janelas modais precisam do PRÓPRIO diálogo: um aberto na janela principal ficaria atrás
    // desta e inalcançável.
    MessageDialog { id: dialogo }
    Connections {
        target: appSettingsController
        function onMensagem(titulo, texto, tipo) { dialogo.abrir(titulo, texto, tipo) }
        function onFecharJanela() { win.close() }
    }

    FolderDialog {
        id: dlgPasta
        title: "Pasta padrão para salvar os dados"
        onAccepted: appSettingsController.definir_pasta_dados(selectedFolder.toString())
    }

    // ---- helpers de layout, para as abas não repetirem o mesmo boilerplate ----
    component LinhaSwitch: RowLayout {
        property alias marcado: sw.checked
        property string rotulo: ""
        property string descricao: ""
        signal alternado(bool valor)
        Layout.fillWidth: true
        spacing: Theme.metrics.padMd
        AppSwitch { id: sw; onToggled: alternado(checked) }
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 1
            Text {
                text: rotulo; color: Theme.colors.text
                font.family: Theme.fonts.display; font.pixelSize: Theme.fonts.s13
            }
            Text {
                visible: descricao !== ""
                text: descricao; color: Theme.colors.faint
                font.family: Theme.fonts.display; font.pixelSize: Theme.fonts.s11
                wrapMode: Text.WordWrap; Layout.fillWidth: true
            }
        }
    }

    component LinhaSlider: ColumnLayout {
        id: linha
        property string rotulo: ""
        property string sufixo: ""
        property real minimo: 0
        property real maximo: 100
        property real passo: 1
        property real valorAtual: 0
        signal movido(real valor)
        Layout.fillWidth: true
        spacing: 2
        Caption { texto: rotulo }
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.metrics.padSm
            AppSlider {
                Layout.fillWidth: true
                from: linha.minimo; to: linha.maximo; stepSize: linha.passo
                value: linha.valorAtual
                // via id do componente, não parent.parent: a cadeia de parents muda ao mexer
                // no layout e quebraria silenciosamente.
                onMovido: linha.movido(valor)
            }
            Text {
                text: Math.round(linha.valorAtual) + linha.sufixo
                color: Theme.colors.muted
                font.family: Theme.fonts.mono; font.pixelSize: Theme.fonts.s11
                Layout.preferredWidth: 68
                horizontalAlignment: Text.AlignRight
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.metrics.padLg
        spacing: Theme.metrics.padMd

        Text {
            text: "Configurações do App"
            color: Theme.colors.text
            font.family: Theme.fonts.display
            font.pixelSize: Theme.fonts.s17
            font.bold: true
            Layout.alignment: Qt.AlignHCenter
        }

        TabBar {
            id: abas
            Layout.fillWidth: true
            background: Rectangle { color: "transparent" }

            component Aba: TabButton {
                id: tb
                implicitHeight: 32
                background: Rectangle {
                    color: tb.checked ? Theme.colors.accent_tint : "transparent"
                    radius: Theme.metrics.cornerSm
                }
                contentItem: Text {
                    text: tb.text
                    color: tb.checked ? Theme.colors.accent : Theme.colors.muted
                    font.family: Theme.fonts.display
                    font.pixelSize: Theme.fonts.s12
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                HoverHandler { cursorShape: Qt.PointingHandCursor }
            }

            Aba { text: "Geral" }
            Aba { text: "Aparência" }
            Aba { text: "Arquivos" }
            Aba { text: "Conexão" }
            Aba { text: "Diagnóstico" }
            Aba { text: "Avançado" }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: abas.currentIndex

            // ------------------------------------------------------------- Geral
            ScrollView {
                contentWidth: availableWidth
                clip: true
                ColumnLayout {
                    width: parent.width
                    spacing: Theme.metrics.padMd

                    LinhaSwitch {
                        rotulo: "Carregar a última configuração ao abrir"
                        descricao: "Deixa o app já configurado com o último .config usado."
                        marcado: appSettingsController.autoCarregarConfig
                        onAlternado: appSettingsController.autoCarregarConfig = valor
                    }
                    LinhaSwitch {
                        rotulo: "Verificar atualizações ao abrir"
                        descricao: "Desligue em laboratórios sem internet: evita a espera pela rede a cada arranque."
                        marcado: appSettingsController.verificarAtualizacoes
                        onAlternado: appSettingsController.verificarAtualizacoes = valor
                    }
                    LinhaSwitch {
                        rotulo: "Confirmar antes de sair durante um experimento"
                        descricao: "Protege uma coleta em andamento de um fechamento acidental."
                        marcado: appSettingsController.confirmarSaida
                        onAlternado: appSettingsController.confirmarSaida = valor
                    }
                    LinhaSlider {
                        rotulo: "Tempo mínimo da tela de carregamento"
                        sufixo: " ms"
                        minimo: 0; maximo: 5000; passo: 100
                        valorAtual: appSettingsController.splashMinimoMs
                        onMovido: appSettingsController.splashMinimoMs = Math.round(valor)
                    }

                    // Modo de teste: destacado numa moldura própria para não ser confundido com
                    // uma preferência de uso normal — quem liga isto não está coletando dados.
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.topMargin: Theme.metrics.padSm
                        implicitHeight: linhaSim.implicitHeight + 2 * Theme.metrics.padMd
                        radius: Theme.metrics.cornerSm
                        color: Theme.colors.input_bg
                        border.color: appSettingsController.simularBitalino
                                      ? Theme.colors.accent : Theme.colors.border
                        border.width: 1

                        LinhaSwitch {
                            id: linhaSim
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.margins: Theme.metrics.padMd
                            rotulo: "Simular BITalino  (modo de teste)"
                            descricao: "Publica uma stream de sinais simulados para testar a interface "
                                       + "sem hardware nem OpenSignals. Os canais A1 a A6 simulam, nesta "
                                       + "ordem: EDA, ECG, EMG, EOG, EEG e EGG. Liga e desliga na hora."
                            marcado: appSettingsController.simularBitalino
                            onAlternado: appSettingsController.simularBitalino = valor
                        }
                    }
                    Item { Layout.fillHeight: true }
                }
            }

            // --------------------------------------------------------- Aparência
            ScrollView {
                contentWidth: availableWidth
                clip: true
                ColumnLayout {
                    width: parent.width
                    spacing: Theme.metrics.padMd

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        Caption { texto: "Tema" }
                        AppComboBox {
                            Layout.preferredWidth: 220
                            model: Theme.nomes
                            currentIndex: Theme.nomes.indexOf(Theme.nome)
                            onActivated: Theme.setTheme(currentText)
                        }
                        Text {
                            text: "O tema é aplicado imediatamente."
                            color: Theme.colors.faint
                            font.family: Theme.fonts.display; font.pixelSize: Theme.fonts.s11
                        }
                    }

                    LinhaSlider {
                        rotulo: "Escala da interface  (requer reinício)"
                        sufixo: " %"
                        minimo: 90; maximo: 150; passo: 5
                        valorAtual: appSettingsController.escalaUi
                        onMovido: appSettingsController.escalaUi = Math.round(valor)
                    }
                    LinhaSwitch {
                        rotulo: "Abrir maximizado"
                        marcado: appSettingsController.abrirMaximizado
                        onAlternado: appSettingsController.abrirMaximizado = valor
                    }
                    LinhaSwitch {
                        rotulo: "Lembrar tamanho e posição da janela"
                        marcado: appSettingsController.lembrarGeometria
                        onAlternado: appSettingsController.lembrarGeometria = valor
                    }
                    Item { Layout.fillHeight: true }
                }
            }

            // ---------------------------------------------------------- Arquivos
            ScrollView {
                contentWidth: availableWidth
                clip: true
                ColumnLayout {
                    width: parent.width
                    spacing: Theme.metrics.padMd

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        Caption { texto: "Pasta padrão para salvar os dados" }
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.metrics.padSm
                            AppTextField {
                                Layout.fillWidth: true
                                readOnly: true
                                text: appSettingsController.pastaDadosPadrao || "(padrão do sistema)"
                            }
                            GhostButton { text: "Escolher…"; onClicked: dlgPasta.open() }
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        Caption { texto: "Nome das pastas de sessão" }
                        AppComboBox {
                            Layout.preferredWidth: 340
                            model: appSettingsController.rotulosTimestamp
                            currentIndex: appSettingsController.rotulosTimestamp
                                          .indexOf(appSettingsController.rotuloTimestampAtual)
                            onActivated: appSettingsController.definir_timestamp_por_rotulo(currentText)
                        }
                        Text {
                            text: "O formato ISO ordena as pastas cronologicamente no explorador de arquivos."
                            color: Theme.colors.faint
                            font.family: Theme.fonts.display; font.pixelSize: Theme.fonts.s11
                            wrapMode: Text.WordWrap; Layout.fillWidth: true
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        Caption { texto: "Extensões de áudio aceitas" }
                        AppTextField {
                            Layout.fillWidth: true
                            text: appSettingsController.extensoesAudio
                            onEditingFinished: appSettingsController.extensoesAudio = text
                        }
                        Text {
                            text: "Separadas por vírgula (ex.: .wav, .mp3, .ogg)."
                            color: Theme.colors.faint
                            font.family: Theme.fonts.display; font.pixelSize: Theme.fonts.s11
                        }
                    }

                    LinhaSwitch {
                        rotulo: "Gerar planilha XLSX além do CSV"
                        descricao: "O XLSX é derivado do CSV, que é o dado primário. Desligar acelera o fim de cada faixa."
                        marcado: appSettingsController.gerarXlsx
                        onAlternado: appSettingsController.gerarXlsx = valor
                    }
                    Item { Layout.fillHeight: true }
                }
            }

            // ----------------------------------------------------------- Conexão
            ScrollView {
                contentWidth: availableWidth
                clip: true
                ColumnLayout {
                    width: parent.width
                    spacing: Theme.metrics.padMd

                    LinhaSlider {
                        rotulo: "Tempo limite para localizar a stream LSL"
                        sufixo: " s"
                        minimo: 1; maximo: 15; passo: 1
                        valorAtual: appSettingsController.lslTimeout
                        onMovido: appSettingsController.lslTimeout = Math.round(valor)
                    }
                    Text {
                        text: "Aumente se o OpenSignals demora a responder nesta máquina."
                        color: Theme.colors.faint
                        font.family: Theme.fonts.display; font.pixelSize: Theme.fonts.s11
                        wrapMode: Text.WordWrap; Layout.fillWidth: true
                    }

                    LinhaSlider {
                        rotulo: "Tempo sem amostras até alertar perda de conexão"
                        sufixo: " s"
                        minimo: 5; maximo: 60; passo: 1
                        valorAtual: appSettingsController.watchdogTimeout
                        onMovido: appSettingsController.watchdogTimeout = Math.round(valor)
                    }
                    Text {
                        text: "Valores baixos demais geram alarmes falsos; altos demais atrasam o aviso real."
                        color: Theme.colors.faint
                        font.family: Theme.fonts.display; font.pixelSize: Theme.fonts.s11
                        wrapMode: Text.WordWrap; Layout.fillWidth: true
                    }
                    Item { Layout.fillHeight: true }
                }
            }

            // ------------------------------------------------------- Diagnóstico
            ScrollView {
                contentWidth: availableWidth
                clip: true
                ColumnLayout {
                    width: parent.width
                    spacing: Theme.metrics.padMd

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        Caption { texto: "Nível de log  (requer reinício)" }
                        AppComboBox {
                            Layout.preferredWidth: 180
                            model: appSettingsController.niveisLog
                            currentIndex: appSettingsController.niveisLog
                                          .indexOf(appSettingsController.nivelLog)
                            onActivated: appSettingsController.nivelLog = currentText
                        }
                        Text {
                            text: "Use DEBUG apenas para investigar um problema: os arquivos crescem rápido."
                            color: Theme.colors.faint
                            font.family: Theme.fonts.display; font.pixelSize: Theme.fonts.s11
                            wrapMode: Text.WordWrap; Layout.fillWidth: true
                        }
                    }

                    LinhaSlider {
                        rotulo: "Apagar logs mais antigos que  (requer reinício)"
                        sufixo: " dias"
                        minimo: 0; maximo: 365; passo: 5
                        valorAtual: appSettingsController.retencaoLogs
                        onMovido: appSettingsController.retencaoLogs = Math.round(valor)
                    }
                    Text {
                        text: "0 = nunca apagar."
                        color: Theme.colors.faint
                        font.family: Theme.fonts.display; font.pixelSize: Theme.fonts.s11
                    }

                    Caption { texto: "Atalhos" }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.metrics.padSm
                        GhostButton {
                            text: "Abrir pasta de dados"
                            onClicked: appSettingsController.abrir_pasta_dados()
                        }
                        GhostButton {
                            text: "Abrir pasta de logs"
                            onClicked: appSettingsController.abrir_pasta_logs()
                        }
                        GhostButton {
                            text: "Abrir configurações"
                            onClicked: appSettingsController.abrir_pasta_configs()
                        }
                    }
                    Item { Layout.fillHeight: true }
                }
            }

            // ---------------------------------------------------------- Avançado
            ScrollView {
                contentWidth: availableWidth
                clip: true
                ColumnLayout {
                    width: parent.width
                    spacing: Theme.metrics.padMd

                    // portão de consentimento: estas opções afetam o dado coletado.
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: aviso.implicitHeight + 2 * Theme.metrics.padMd
                        radius: Theme.metrics.cornerSm
                        color: Theme.colors.danger_tint
                        border.color: Theme.colors.danger_border
                        border.width: 1

                        RowLayout {
                            id: aviso
                            anchors.fill: parent
                            anchors.margins: Theme.metrics.padMd
                            spacing: Theme.metrics.padMd
                            AppSwitch {
                                checked: appSettingsController.avancadoLiberado
                                onToggled: appSettingsController.avancadoLiberado = checked
                            }
                            Text {
                                Layout.fillWidth: true
                                text: "Entendo que estas opções afetam a coleta de dados.\n"
                                      + "Elas são registradas no ambiente.json de cada sessão."
                                color: Theme.colors.text
                                font.family: Theme.fonts.display
                                font.pixelSize: Theme.fonts.s12
                                wrapMode: Text.WordWrap
                            }
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Theme.metrics.padMd
                        enabled: appSettingsController.avancadoLiberado
                        opacity: enabled ? 1.0 : 0.45

                        Caption { texto: "Faixa etária aceita do participante" }
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.metrics.padMd
                            ColumnLayout {
                                spacing: 2
                                Caption { texto: "Mínima" }
                                AppTextField {
                                    Layout.preferredWidth: 90
                                    text: appSettingsController.idadeMinima
                                    onEditingFinished: appSettingsController.idadeMinima = parseInt(text || "0")
                                }
                            }
                            ColumnLayout {
                                spacing: 2
                                Caption { texto: "Máxima" }
                                AppTextField {
                                    Layout.preferredWidth: 90
                                    text: appSettingsController.idadeMaxima
                                    onEditingFinished: appSettingsController.idadeMaxima = parseInt(text || "0")
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            Caption { texto: "Palavras que classificam um fator como ruído" }
                            AppTextField {
                                Layout.fillWidth: true
                                text: appSettingsController.palavrasRuido
                                onEditingFinished: appSettingsController.palavrasRuido = text
                            }
                            Text {
                                text: "Separadas por vírgula. Compara sem diferenciar maiúsculas, por trecho do texto."
                                color: Theme.colors.faint
                                font.family: Theme.fonts.display; font.pixelSize: Theme.fonts.s11
                                wrapMode: Text.WordWrap; Layout.fillWidth: true
                            }
                        }

                        LinhaSwitch {
                            rotulo: "Permitir que o ComPasso controle o volume do sistema"
                            marcado: appSettingsController.controlarVolume
                            onAlternado: appSettingsController.controlarVolume = valor
                        }
                        LinhaSlider {
                            rotulo: "Volume do sistema aplicado ao abrir"
                            sufixo: " %"
                            minimo: 0; maximo: 100; passo: 5
                            valorAtual: appSettingsController.volumeInicial
                            onMovido: appSettingsController.volumeInicial = Math.round(valor)
                        }
                    }
                    Item { Layout.fillHeight: true }
                }
            }
        }

        // aviso persistente depois de salvar algo que só vale no próximo arranque.
        Rectangle {
            Layout.fillWidth: true
            visible: appSettingsController.pendenteReinicio
            implicitHeight: 34
            radius: Theme.metrics.cornerSm
            color: Theme.colors.accent_tint
            Text {
                anchors.centerIn: parent
                text: "Algumas preferências só valem quando o ComPasso for aberto novamente."
                color: Theme.colors.accent
                font.family: Theme.fonts.display
                font.pixelSize: Theme.fonts.s12
            }
        }

        RowLayout {
            Layout.alignment: Qt.AlignRight
            spacing: Theme.metrics.padSm
            GhostButton {
                text: "Restaurar padrões"
                perigo: true
                dica: "Devolve todas as preferências do app aos valores de fábrica"
                onClicked: appSettingsController.restaurar_padroes()
            }
            GhostButton { text: "Cancelar"; onClicked: { appSettingsController.cancelar(); win.close() } }
            AppButton { text: "Salvar"; onClicked: appSettingsController.salvar() }
        }
    }
}
