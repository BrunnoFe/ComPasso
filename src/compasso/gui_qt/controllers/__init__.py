"""Controllers (QObjects "backend") que ligam as views QML à lógica do núcleo.

Cada controller expõe ``Slot``s invocáveis pelo QML e emite ``Signal``s/atualiza propriedades
reativas do ``Context``. Substituem os antigos frames CustomTkinter, que misturavam construção
de widgets com orquestração de conexão/experimento/arquivos.
"""
