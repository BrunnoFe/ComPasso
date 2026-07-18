// Marca (logo) do ComPasso desenhada em QML — sem depender de um arquivo de imagem.
// Empilha o nome "ComPasso", a onda estilo ECG (gradiente teal→azul→roxo, identidade da marca)
// e a legenda "MÚSICA & FISIOLOGIA". Compacta e legível; o texto acompanha a paleta do tema
// (some o problema da logo.png em branco/baixa resolução deslocada no frame).
import QtQuick

Column {
    id: logo
    // fator de escala geral da marca (1.0 = tamanho padrão da barra de conexão).
    property real escala: 1.0
    spacing: 3 * escala

    Text {
        id: titulo
        text: "ComPasso"
        color: Theme.colors.text
        font.family: Theme.fonts.display
        font.pixelSize: Math.round(26 * logo.escala)
        font.bold: true
        font.letterSpacing: 0.5
    }

    // onda ECG com gradiente da marca (cores fixas — é a identidade, não depende do tema).
    Canvas {
        id: onda
        width: titulo.width
        height: Math.round(16 * logo.escala)
        antialiasing: true
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        Component.onCompleted: requestPaint()
        onPaint: {
            var c = getContext("2d")
            c.reset()
            var w = width, h = height
            // pontos normalizados (x 0..1, y 0..1 com 0=topo) traçando uma onda tipo ECG.
            var pts = [[0.00,0.60],[0.14,0.55],[0.24,0.42],[0.36,0.60],[0.46,0.64],
                       [0.51,0.55],[0.55,0.08],[0.60,0.94],[0.65,0.40],[0.70,0.62],
                       [0.80,0.54],[0.90,0.54],[1.00,0.50]]
            var g = c.createLinearGradient(0, 0, w, 0)
            g.addColorStop(0.0, "#2DD4BF")
            g.addColorStop(0.5, "#4F86E8")
            g.addColorStop(1.0, "#7C74FF")
            c.strokeStyle = g
            c.lineWidth = Math.max(1.6, 2.4 * logo.escala)
            c.lineJoin = "round"
            c.lineCap = "round"
            c.beginPath()
            for (var i = 0; i < pts.length; i++) {
                var x = pts[i][0] * w, y = pts[i][1] * h
                if (i === 0) c.moveTo(x, y); else c.lineTo(x, y)
            }
            c.stroke()
        }
    }

    Text {
        text: "MÚSICA & FISIOLOGIA"
        color: Theme.colors.muted
        font.family: Theme.fonts.display
        font.pixelSize: Math.round(8 * logo.escala)
        font.bold: true
        font.letterSpacing: 2 * logo.escala
    }
}
