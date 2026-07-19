"""Singleton de tema exposto ao QML.

Substitui o esquema antigo (``compasso.gui.theme``), em que trocar de tema reescrevia
globais de módulo e exigia reconstruir toda a UI. Aqui o tema é um ``QObject`` com
propriedades reativas: ``colors``, ``metrics`` e ``fonts`` são lidas pelo QML via *binding*
(``Theme.colors.accent``); ao chamar ``setTheme(nome)`` um único sinal ``changed`` dispara e
todos os *bindings* se reavaliam — **troca instantânea, sem reconstruir a interface**.

Como não há mais reconstrução da UI, a antiga regra "só trocar tema com a app ociosa" deixa
de ser necessária (não há estado de conexão/experimento a resetar).
"""

from PySide6.QtCore import QObject, Property, Signal, Slot

from . import gui_logger
from . import palettes
from compasso.core import config_manager, app_prefs


class Theme(QObject):
    """Fornece cores/dimensões/fontes reativas ao QML e persiste a paleta escolhida.

    As três propriedades expostas (``colors``/``metrics``/``fonts``) retornam dicionários
    lidos no QML como objetos JS. Todas usam o mesmo sinal ``changed`` como *notify*, então
    qualquer *binding* que dependa delas se atualiza quando a paleta muda.
    """

    changed = Signal()

    def __init__(self, nome_inicial: str | None = None):
        super().__init__()
        # Preferência salva > argumento > padrão. Valida contra as paletas conhecidas.
        salvo = config_manager.get_theme_pref()
        escolhido = salvo or nome_inicial or palettes.PALETTE_PADRAO
        if escolhido not in palettes.PALETTES:
            escolhido = palettes.PALETTE_PADRAO
        self._nome = escolhido
        # Último tema usado de cada família, para o botão sol/lua ser um atalho que não anula
        # a escolha feita no menu Tema: saindo de Iris para o claro e voltando, volta-se a
        # Iris — não a um padrão. A família oposta começa no padrão de cada uma.
        claro = self._nome in palettes.PALETAS_CLARAS
        self._ultimo_claro = self._nome if claro else palettes.TEMA_CLARO_PADRAO
        self._ultimo_escuro = palettes.TEMA_ESCURO_PADRAO if claro else self._nome
        self._escalar(int(app_prefs.obter().get("escala_ui", 100)))
        gui_logger.logger.info(f"Tema inicial: {self._nome}")

    # ------------------------------------------------------------------ nome
    def _get_nome(self) -> str:
        return self._nome

    nome = Property(str, _get_nome, notify=changed)

    def _get_nomes(self):
        return palettes.THEME_NAMES

    nomes = Property("QVariantList", _get_nomes, constant=True)

    def _get_eh_claro(self) -> bool:
        return self._nome in palettes.PALETAS_CLARAS

    ehClaro = Property(bool, _get_eh_claro, notify=changed)

    # -------------------------------------------------------------- dicts QML
    def _get_colors(self):
        return palettes.PALETTES[self._nome]

    colors = Property("QVariant", _get_colors, notify=changed)

    def _get_metrics(self):
        return self._metrics

    metrics = Property("QVariant", _get_metrics, constant=True)

    def _get_fonts(self):
        return self._fonts

    fonts = Property("QVariant", _get_fonts, constant=True)

    def _escalar(self, escala: int) -> None:
        """Aplica a escala da UI (preferência ``escala_ui``) a métricas e tamanhos de fonte.

        Feito uma única vez, na construção: ambas as propriedades são ``constant=True`` no QML
        (nenhum *binding* as reavalia), e é por isso que a mudança de escala exige reinício —
        ao contrário da paleta, que é reativa e troca a quente.

        Só valores numéricos são escalados: as chaves de fonte trazem também nomes de família
        (strings), que precisam passar intactas.
        """
        self._metrics = dict(palettes.METRICS)
        self._fonts = dict(palettes.FONTS)
        if escala == 100:
            return
        fator = escala / 100.0
        for origem, destino in ((palettes.METRICS, self._metrics), (palettes.FONTS, self._fonts)):
            for chave, valor in origem.items():
                if isinstance(valor, bool) or not isinstance(valor, (int, float)):
                    continue
                destino[chave] = max(1, int(round(valor * fator)))
        gui_logger.logger.info(f"Escala da interface aplicada: {escala}%")

    # ---------------------------------------------------------------- troca
    @Slot(str, result=bool)
    def setTheme(self, nome: str) -> bool:
        """Troca a paleta ativa (e persiste). Retorna False se o nome for desconhecido."""
        if nome not in palettes.PALETTES:
            gui_logger.logger.warning(f"Tema desconhecido ignorado: {nome!r}")
            return False
        if nome == self._nome:
            return True
        self._nome = nome
        if nome in palettes.PALETAS_CLARAS:
            self._ultimo_claro = nome
        else:
            self._ultimo_escuro = nome
        try:
            config_manager.set_theme_pref(nome)
        except Exception as e:
            gui_logger.logger.error(f"Falha ao salvar preferência de tema: {e}")
        self.changed.emit()
        gui_logger.logger.info(f"Tema alterado para: {nome}")
        return True

    @Slot(result=bool)
    def alternarClaroEscuro(self) -> bool:
        """Alterna entre a família clara e a escura, retomando o último tema usado em cada.

        É o botão sol/lua da barra de menus: um atalho para as duas famílias, sem substituir o
        menu Tema (que segue dando acesso às seis paletas).
        """
        alvo = self._ultimo_escuro if self._get_eh_claro() else self._ultimo_claro
        return self.setTheme(alvo)
