// Tela de carregamento sobreposta à janela principal — cobre a UI no arranque e some com fade.
// Reimaginada: a "signal line" do ComPasso é desenhada progressivamente (spline suave, pontas
// redondas, blend teal→iris), como uma assinatura viva da marca, sobre o fundo do tema ativo.
// Mantém: tamanho da janela inteira, cantos arredondados e transição suave para a interface.
import QtQuick

Rectangle {
    id: splash
    anchors.fill: parent
    z: 1000
    color: Theme.colors.win_bg
    radius: Theme.metrics.cornerCard   // acompanha os cantos arredondados da janela
    clip: true
    property int duracaoMs: 2600

    // leve gradiente radial de profundidade (bar_bg no centro → win_bg nas bordas).
    Rectangle {
        anchors.centerIn: parent
        width: parent.width * 1.2
        height: parent.height * 1.2
        gradient: Gradient {
            GradientStop { position: 0.0; color: Theme.colors.bar_bg }
            GradientStop { position: 1.0; color: Theme.colors.win_bg }
        }
        opacity: 0.55
    }

    Column {
        anchors.centerIn: parent
        spacing: 26

        // ---- traço animado (onda desenhada progressivamente, blend teal→iris) ----
        Canvas {
            id: traco
            width: 360
            height: 190
            anchors.horizontalCenter: parent.horizontalCenter
            antialiasing: true
            renderStrategy: Canvas.Threaded
            property real avanco: 0.0
            property var pts: []
            onAvancoChanged: requestPaint()
            Component.onCompleted: { pts = splash._gerarForma(); requestPaint() }
            onPaint: {
                var c = getContext("2d")
                c.reset()
                var w = width, h = height
                if (!pts || pts.length < 2)
                    return
                var n = Math.max(2, Math.floor(pts.length * avanco))
                var grad = c.createLinearGradient(0, 0, w, 0)
                grad.addColorStop(0.0, "#2DD4BF")
                grad.addColorStop(0.5, "#4F86E8")
                grad.addColorStop(1.0, "#7C74FF")
                c.strokeStyle = grad
                c.lineWidth = 6
                c.lineJoin = "round"
                c.lineCap = "round"
                c.beginPath()
                for (var i = 0; i < n; i++) {
                    var p = pts[i]
                    if (i === 0) c.moveTo(p.x * w, p.y * h)
                    else c.lineTo(p.x * w, p.y * h)
                }
                c.stroke()
            }
            // desenha 0→1, segura no cheio e reinicia (loop) enquanto a splash está visível.
            SequentialAnimation on avanco {
                loops: Animation.Infinite
                running: splash.visible
                NumberAnimation { from: 0.0; to: 1.0; duration: 1700; easing.type: Easing.InOutQuad }
                PauseAnimation { duration: 550 }
            }
        }

        Text {
            text: "ComPasso"
            anchors.horizontalCenter: parent.horizontalCenter
            color: Theme.colors.text
            font.family: Theme.fonts.display
            font.pixelSize: 34
            font.bold: true
            font.letterSpacing: 0.5
        }

        Text {
            text: "MÚSICA & FISIOLOGIA" + (appVersion ? "   ·   " + appVersion : "")
            anchors.horizontalCenter: parent.horizontalCenter
            color: Theme.colors.muted
            font.family: Theme.fonts.display
            font.pixelSize: 10
            font.bold: true
            font.letterSpacing: 2
        }

        Text {
            id: carregando
            anchors.horizontalCenter: parent.horizontalCenter
            color: Theme.colors.faint
            font.family: Theme.fonts.mono
            font.pixelSize: 12
            property int pontos: 1
            text: "CARREGANDO " + ".".repeat(pontos)
            Timer {
                interval: 420; running: splash.visible; repeat: true
                onTriggered: carregando.pontos = (carregando.pontos % 3) + 1
            }
        }
    }

    // Gera os pontos normalizados (0..1) da forma: 2 curvas suaves + espículas tipo EEG,
    // idêntica à assinatura do ComPasso (mesma geometria da loading antiga em Tk).
    function _gerarForma() {
        function cubic(p0, p1, p2, p3, t) {
            var u = 1 - t
            return {
                x: u*u*u*p0[0] + 3*u*u*t*p1[0] + 3*u*t*t*p2[0] + t*t*t*p3[0],
                y: u*u*u*p0[1] + 3*u*u*t*p1[1] + 3*u*t*t*p2[1] + t*t*t*p3[1]
            }
        }
        var raw = []
        var beziers = [
            [[6, 34], [11, 22], [16, 22], [21, 34]],
            [[21, 34], [26, 46], [30, 46], [34, 34]]
        ]
        for (var b = 0; b < beziers.length; b++) {
            var bz = beziers[b]
            for (var i = 0; i <= 40; i++)
                raw.push(cubic(bz[0], bz[1], bz[2], bz[3], i / 40))
        }
        var line = [[34, 34], [38, 10], [42, 54], [46, 16], [50, 44], [54, 26], [58, 34]]
        for (var s = 0; s < line.length - 1; s++) {
            var a = line[s], cpt = line[s + 1]
            for (var j = 1; j <= 14; j++) {
                var t = j / 14
                raw.push({ x: a[0] + (cpt[0]-a[0]) * t, y: a[1] + (cpt[1]-a[1]) * t })
            }
        }
        // normaliza para 0..1 (x em [6,58], y em [10,54]) com uma margem interna.
        var x0 = 6, x1 = 58, y0 = 10, y1 = 54, pad = 0.08
        var out = []
        for (var k = 0; k < raw.length; k++) {
            out.push({
                x: pad + (raw[k].x - x0) / (x1 - x0) * (1 - 2 * pad),
                y: pad + (raw[k].y - y0) / (y1 - y0) * (1 - 2 * pad)
            })
        }
        return out
    }

    // fecha após duracaoMs com fade suave para a interface.
    Timer {
        interval: splash.duracaoMs; running: true; repeat: false
        onTriggered: fade.start()
    }
    NumberAnimation {
        id: fade; target: splash; property: "opacity"; from: 1; to: 0; duration: 420
        easing.type: Easing.InOutQuad
        onFinished: splash.visible = false
    }
    // enquanto visível, intercepta cliques (a UI atrás não deve receber eventos).
    MouseArea { anchors.fill: parent; enabled: splash.visible }
}
