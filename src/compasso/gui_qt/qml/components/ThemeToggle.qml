// Botão discreto de alternância claro/escuro, no canto direito da barra de menus.
// Mostra o destino, não o estado atual: no tema escuro desenha um SOL (clique = clarear); no
// claro, uma LUA (clique = escurecer).
//
// Os dois ícones são desenhados em Canvas em vez de fonte/imagem: acompanham a cor do tema por
// binding, ficam nítidos em qualquer DPI e não exigem um asset novo no bundle.
import QtQuick

Item {
    id: raiz
    width: 30
    height: 30

    readonly property bool mostrarSol: !Theme.ehClaro
    // realce sutil no hover, no mesmo tom dos botões da barra.
    readonly property color corIcone: hover.hovered ? Theme.colors.accent : Theme.colors.muted

    Rectangle {
        anchors.fill: parent
        anchors.margins: 3
        radius: Theme.metrics.cornerSm
        color: hover.hovered ? Theme.colors.input_bg : "transparent"
    }

    Canvas {
        id: icone
        anchors.centerIn: parent
        width: 18
        height: 18
        antialiasing: true
        // repinta quando o tema ou o hover mudam (a cor entra no desenho).
        property color cor: raiz.corIcone
        property bool sol: raiz.mostrarSol
        onCorChanged: requestPaint()
        onSolChanged: requestPaint()

        onPaint: {
            var c = getContext("2d")
            c.reset()
            var w = width, h = height, cx = w / 2, cy = h / 2
            c.strokeStyle = cor
            c.fillStyle = cor
            c.lineCap = "round"
            c.lineWidth = 1.6

            if (sol) {
                // Sol: núcleo cheio + 8 raios curtos, deixando respiro entre núcleo e raios.
                var r = w * 0.24
                c.beginPath()
                c.arc(cx, cy, r, 0, Math.PI * 2)
                c.fill()
                var interno = r + w * 0.10
                var externo = r + w * 0.24
                for (var i = 0; i < 8; i++) {
                    var a = i * Math.PI / 4
                    c.beginPath()
                    c.moveTo(cx + Math.cos(a) * interno, cy + Math.sin(a) * interno)
                    c.lineTo(cx + Math.cos(a) * externo, cy + Math.sin(a) * externo)
                    c.stroke()
                }
            } else {
                // Lua: disco cheio "mordido" por um segundo disco deslocado. O recorte usa
                // destination-out para a crescente ficar com borda limpa — desenhar o segundo
                // disco na cor do fundo falharia sobre o realce de hover.
                c.beginPath()
                c.arc(cx, cy, w * 0.38, 0, Math.PI * 2)
                c.fill()
                c.globalCompositeOperation = "destination-out"
                c.beginPath()
                c.arc(cx + w * 0.26, cy - w * 0.20, w * 0.36, 0, Math.PI * 2)
                c.fill()
                c.globalCompositeOperation = "source-over"
            }
        }
    }

    HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
    TapHandler { onTapped: Theme.alternarClaroEscuro() }

    Dica {
        parent: raiz
        text: raiz.mostrarSol ? "Mudar para o tema claro" : "Mudar para o tema escuro"
        visible: hover.hovered
    }
}
