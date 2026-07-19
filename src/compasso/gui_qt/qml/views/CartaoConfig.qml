// Card único de configuração: junta "Participante" e "Arquivos & Dados" num só frame inteiriço,
// separados por um divisor vertical discreto (como o divisor logo↔MAC). Ambos os lados colapsam
// juntos por um único chevron (no canto superior direito do card).
//
// Cabeçalho: os dois títulos, cada um flush à esquerda da sua seção. Corpo (retrátil):
// [ participante (form/resumo) | divisor | arquivos ]. A altura do card é sempre a do formulário
// do participante — ao salvar, o resumo é sobreposto e centralizado (a ocupação não muda).
import QtQuick
import QtQuick.Layouts
import QtQuick.Dialogs
import "../components"

Rectangle {
    id: card
    property bool recolhido: false
    signal alternar()

    // Em janelas estreitas as duas colunas (participante | arquivos) não cabem lado a lado:
    // empilham numa coluna só, cada seção com seu próprio título e um divisor horizontal entre
    // elas. O cabeçalho de dois títulos some no modo compacto (os títulos vão para dentro das
    // seções); o divisor vertical vira horizontal.
    readonly property bool compacto: width > 0 && width < 760

    color: Theme.colors.bar_bg
    border.color: Theme.colors.border
    border.width: 1
    radius: Theme.metrics.cornerCard
    clip: true
    implicitHeight: coluna.implicitHeight + 2 * Theme.metrics.padMd

    // proporção das duas colunas (participante : arquivos), usada no cabeçalho e no corpo.
    // O participante ocupa mais espaço; arquivos fica um pouco mais compacto à direita.
    readonly property int _pesoPart: 3
    readonly property int _pesoArq: 2

    // ------------------------------------------------------------ diálogos nativos
    FolderDialog {
        id: dlgMusicas
        title: "Selecione a pasta contendo os arquivos de música"
        onAccepted: filesController.definir_musicas(selectedFolder)
    }
    FileDialog {
        id: dlgCondicoes
        title: "Selecione o Excel de condições/fatores das músicas"
        nameFilters: ["Planilhas Excel (*.xlsx *.xls)"]
        onAccepted: filesController.definir_condicoes(selectedFile)
    }
    FolderDialog {
        id: dlgSaida
        title: "Selecione o diretório para salvar os dados"
        onAccepted: filesController.definir_saida(selectedFolder)
    }

    // ---------------------------------------------------------------- componentes
    component CampoRotulado: ColumnLayout {
        property alias rotulo: cap.texto
        property alias placeholder: campo.placeholderText
        property alias valorInicial: campo.text
        signal editado(string texto)
        spacing: 2
        Layout.fillWidth: true
        Caption { id: cap }
        AppTextField {
            id: campo
            Layout.fillWidth: true
            onTextEdited: parent.editado(text)
        }
    }

    component LinhaArquivo: RowLayout {
        property alias rotulo: cap.texto
        property string caminho: ""
        property bool ok: false
        property alias textoBotao: botao.text
        property alias dicaBotao: botao.dica
        signal escolher()
        Layout.fillWidth: true
        spacing: Theme.metrics.padMd

        Rectangle {
            width: 22; height: 22; radius: 7
            color: ok ? Theme.colors.accent_tint : Theme.colors.danger_tint
            Text {
                anchors.centerIn: parent
                text: ok ? "✓" : "✕"
                color: ok ? Theme.colors.success : Theme.colors.danger
                font.pixelSize: Theme.fonts.s11
                font.bold: true
            }
        }
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 0
            Caption { id: cap }
            Text {
                text: caminho
                color: Theme.colors.muted
                font.family: Theme.fonts.mono
                font.pixelSize: Theme.fonts.s12
                elide: Text.ElideMiddle
                Layout.fillWidth: true
            }
        }
        GhostButton {
            id: botao
            Layout.preferredWidth: 96
            onClicked: parent.escolher()
        }
    }

    component TituloCard: Text {
        color: Theme.colors.text
        font.family: Theme.fonts.display
        font.pixelSize: Theme.fonts.s15
        font.bold: true
    }

    // chevron de recolher/expandir no canto superior direito (fora do corpo retrátil, então a
    // posição se mantém quando colapsado).
    Rectangle {
        id: btnChevron
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.rightMargin: Theme.metrics.padMd
        anchors.topMargin: Theme.metrics.padMd - 3
        width: 30; height: 30
        radius: Theme.metrics.cornerSm
        z: 2
        color: chevronHover.hovered ? Theme.colors.input_bg : "transparent"
        border.color: Theme.colors.border
        border.width: 1
        enabled: !ctx.experimentUiLocked
        opacity: ctx.experimentUiLocked ? 0.5 : 1
        Text {
            anchors.centerIn: parent
            text: "❯"
            color: Theme.colors.muted
            font.pixelSize: Theme.fonts.s13
            font.bold: true
            rotation: card.recolhido ? 90 : -90
            Behavior on rotation { NumberAnimation { duration: 160; easing.type: Easing.OutQuad } }
        }
        HoverHandler { id: chevronHover; enabled: !ctx.experimentUiLocked; cursorShape: Qt.PointingHandCursor }
        Dica { parent: btnChevron; visible: chevronHover.hovered; text: card.recolhido ? "Expandir" : "Recolher" }
        TapHandler { enabled: !ctx.experimentUiLocked; onTapped: card.alternar() }
    }

    // ------------------------------------------------------------------- conteúdo
    Column {
        id: coluna
        x: Theme.metrics.padMd
        y: Theme.metrics.padMd
        width: parent.width - 2 * Theme.metrics.padMd
        spacing: Theme.metrics.padMd

        // ---- cabeçalho: dois títulos flush à esquerda de cada seção (só no modo largo;
        // no compacto cada título vai para dentro da sua seção empilhada) ----
        RowLayout {
            visible: !card.compacto
            width: parent.width
            spacing: Theme.metrics.padLg

            TituloCard {
                text: "Participante"
                Layout.fillWidth: true
                Layout.horizontalStretchFactor: card._pesoPart
            }
            // divisor curto, alinhado ao divisor do corpo — separa os títulos mesmo colapsado.
            Rectangle {
                Layout.preferredWidth: 1
                Layout.preferredHeight: 20
                Layout.alignment: Qt.AlignVCenter
                color: Theme.colors.border
            }
            RowLayout {
                Layout.fillWidth: true
                Layout.horizontalStretchFactor: card._pesoArq
                spacing: 0
                TituloCard {
                    text: "Arquivos & Dados"
                    Layout.fillWidth: true
                }
                // espaço reservado p/ o chevron (ancorado no canto) não cobrir o título.
                Item { Layout.preferredWidth: 34 }
            }
        }

        // ---- corpo retrátil: participante | divisor | arquivos ----
        Item {
            id: clipCorpo
            width: parent.width
            clip: true
            height: card.recolhido ? 0 : corpo.implicitHeight
            Behavior on height { NumberAnimation { duration: 130; easing.type: Easing.OutQuad } }

            GridLayout {
                id: corpo
                width: parent.width
                opacity: card.recolhido ? 0 : 1
                Behavior on opacity { NumberAnimation { duration: 110 } }
                columns: card.compacto ? 1 : 3
                columnSpacing: Theme.metrics.padLg
                rowSpacing: Theme.metrics.padMd

                // ======================= PARTICIPANTE (form OU resumo) =======================
                // A altura desta coluna é sempre a do formulário; o resumo é sobreposto e
                // centralizado ao salvar, então a ocupação de espaço do card não muda.
                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.horizontalStretchFactor: card._pesoPart
                    spacing: Theme.metrics.padSm

                    // título só no modo compacto (no largo ele vem do cabeçalho).
                    TituloCard { text: "Participante"; visible: card.compacto; Layout.fillWidth: true }

                    Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    implicitHeight: formulario.implicitHeight

                    // ---------- formulário ----------
                    ColumnLayout {
                        id: formulario
                        anchors.fill: parent
                        opacity: partController.salvos ? 0 : 1
                        enabled: !partController.salvos
                        spacing: Theme.metrics.padMd

                        CampoRotulado {
                            rotulo: "Nome"; placeholder: "Digite o nome do participante"
                            valorInicial: partController.rascunhoNome
                            onEditado: (texto) => partController.rascunhoNome = texto
                        }
                        CampoRotulado {
                            rotulo: "Idade"; placeholder: "Digite a idade do participante"
                            valorInicial: partController.rascunhoIdade
                            onEditado: (texto) => partController.rascunhoIdade = texto
                        }
                        CampoRotulado {
                            rotulo: "Gênero"; placeholder: "Digite o gênero do participante"
                            valorInicial: partController.rascunhoGenero
                            onEditado: (texto) => partController.rascunhoGenero = texto
                        }
                        Item { Layout.fillHeight: true; Layout.minimumHeight: Theme.metrics.padSm }
                        GhostButton {
                            text: "Salvar informações"
                            dica: "Salvar as informações do participante"
                            Layout.alignment: Qt.AlignHCenter
                            Layout.preferredWidth: 180
                            onClicked: partController.salvar()
                        }
                    }

                    // ---------- resumo (sobreposto, centralizado) ----------
                    ColumnLayout {
                        anchors.centerIn: parent
                        width: parent.width
                        visible: partController.salvos
                        spacing: 4

                        Rectangle {
                            Layout.alignment: Qt.AlignHCenter
                            width: 56; height: 56; radius: 28
                            color: "transparent"
                            border.color: Theme.colors.accent_border
                            border.width: 2
                            Text {
                                anchors.centerIn: parent
                                text: partController.inicial
                                color: Theme.colors.accent
                                font.family: Theme.fonts.display
                                font.pixelSize: Theme.fonts.s18
                                font.bold: true
                            }
                        }
                        Text {
                            Layout.alignment: Qt.AlignHCenter
                            Layout.topMargin: Theme.metrics.padSm
                            text: partController.nome
                            color: Theme.colors.text
                            font.family: Theme.fonts.display
                            font.pixelSize: Theme.fonts.s17
                            font.bold: true
                            horizontalAlignment: Text.AlignHCenter
                        }
                        Text {
                            Layout.alignment: Qt.AlignHCenter
                            text: partController.idade + " anos · " + partController.genero
                            color: Theme.colors.muted
                            font.family: Theme.fonts.mono
                            font.pixelSize: Theme.fonts.s12
                            horizontalAlignment: Text.AlignHCenter
                        }
                        GhostButton {
                            text: "Editar"
                            dica: "Editar as informações do participante"
                            enabled: ctx.participantEditable
                            Layout.alignment: Qt.AlignHCenter
                            Layout.topMargin: Theme.metrics.padSm
                            Layout.preferredWidth: 120
                            onClicked: partController.editar()
                        }
                    }
                    }
                }

                // ==================== DIVISOR discreto (vertical no largo, horizontal no compacto) ====================
                Rectangle {
                    Layout.fillWidth: card.compacto
                    Layout.fillHeight: !card.compacto
                    Layout.preferredWidth: card.compacto ? 0 : 1
                    Layout.preferredHeight: card.compacto ? 1 : 0
                    Layout.topMargin: 2
                    Layout.bottomMargin: 2
                    color: Theme.colors.border
                }

                // ============================== ARQUIVOS & DADOS ==============================
                // Linhas bem distribuídas (space-around): espaçadores iguais no topo, entre as
                // linhas e na base — ocupam o card de forma harmônica.
                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.horizontalStretchFactor: card._pesoArq
                    spacing: 0

                    // título só no modo compacto (no largo ele vem do cabeçalho).
                    TituloCard {
                        text: "Arquivos & Dados"; visible: card.compacto
                        Layout.fillWidth: true; Layout.bottomMargin: Theme.metrics.padSm
                    }

                    Item { Layout.fillHeight: true; Layout.minimumHeight: 0 }
                    LinhaArquivo {
                        rotulo: "Músicas"; textoBotao: "Carregar"
                        dicaBotao: "Selecionar a pasta com os arquivos de música"
                        caminho: filesController.musicaTexto; ok: filesController.musicaOk
                        onEscolher: dlgMusicas.open()
                    }
                    Item { Layout.fillHeight: true; Layout.minimumHeight: Theme.metrics.padMd }
                    LinhaArquivo {
                        rotulo: "Condições (.xlsx)"; textoBotao: "Buscar"
                        dicaBotao: "Selecionar a planilha de condições/fatores"
                        caminho: filesController.condicoesTexto; ok: filesController.condicoesOk
                        onEscolher: dlgCondicoes.open()
                    }
                    Item { Layout.fillHeight: true; Layout.minimumHeight: Theme.metrics.padMd }
                    LinhaArquivo {
                        rotulo: "Salvar dados em"; textoBotao: "Escolher"
                        dicaBotao: "Selecionar a pasta onde os dados serão salvos"
                        caminho: filesController.saidaTexto; ok: filesController.saidaOk
                        onEscolher: dlgSaida.open()
                    }
                    Item { Layout.fillHeight: true; Layout.minimumHeight: 0 }
                }
            }
        }
    }
}
