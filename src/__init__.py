# `src/` é apenas o diretório de layout (convenção "src-layout"); o pacote importável de
# verdade é `compasso` (em `src/compasso/`). Este arquivo é mantido vazio de propósito —
# NÃO reexportar nada aqui. Importe sempre pelo pacote real, ex.:
# `from compasso.gui import ComPasso`, `from compasso.core import connectar_bitalino`.
