"""Preferências do aplicativo (janela "Configurações → App").

Guarda o que é **conforto do operador e ambiente da máquina** — não o protocolo do experimento.
A separação é deliberada e vale como regra do projeto:

* o que altera **o dado coletado ou o protocolo** vive no ``.config`` (viaja com o experimento,
  fica registrado na pasta da sessão, é rastreável meses depois);
* o que altera **como o operador usa o app naquela máquina** vive aqui, em ``prefs["app"]``.

As poucas opções desta janela que ainda tocam a coleta (faixa etária aceita, palavras-chave de
ruído, volume inicial) ficam na aba "Avançado" da UI, atrás de um consentimento explícito, e
**todas** as preferências efetivas são registradas junto de cada sessão — ver ``resumo_para_log``.

Persistência: a mesma ``prefs.json`` que já guarda tema/última configuração/gráfico, na chave
``app``. Módulo puro (sem Qt) para poder ser testado sem GUI.

Compatibilidade entre versões, deliberadamente em duas camadas:

* **merge por chave** (``obter``) — resolve de graça o caso comum, que é uma chave nova aparecer
  numa versão futura: o que falta no arquivo cai no padrão, sem migração nenhuma;
* **``PREFS_SCHEMA_VERSION`` + ``_migrar``** — reservado para o que o merge *não* resolve:
  renomear uma chave, mudar a unidade de um valor, inverter a semântica de um booleano. Sem o
  número gravado no arquivo, esses casos são indetectáveis depois do fato.

Cuidado para não confundir com os outros números de versão do projeto: ``CONFIG_VERSION``
(``config_manager``) versiona o schema do ``.config``, e a tag ``vAAAA.M.P`` versiona o app.
Este aqui versiona **somente** o schema desta seção de preferências.
"""

import json
import os

from . import config_logger
from .config_manager import get_prefs_path, _read_prefs, _write_prefs
from compasso.utils import ENCODING_FORMAT

# Versão do schema DESTA seção de preferências (não é a versão do app nem a do .config).
PREFS_SCHEMA_VERSION = 1

# Chave da seção dentro de prefs.json (que também guarda "theme", "last_config", "graph").
_SECAO = "app"

# ---------------------------------------------------------------------------
# Opções de enumeração oferecidas pela UI.
# ---------------------------------------------------------------------------
NIVEIS_LOG = ("DEBUG", "INFO", "WARNING", "ERROR")
# Formatos de data/hora da pasta da sessão. O ISO ordena alfabeticamente na listagem de
# arquivos, que é o que costuma ser desejado na hora de analisar os dados.
FORMATOS_TIMESTAMP = {
    "Dia-Mês-Ano (31-12-2026_14-30-00)": "%d-%m-%Y_%H-%M-%S",
    "ISO / Ano-Mês-Dia (2026-12-31_14-30-00)": "%Y-%m-%d_%H-%M-%S",
}

# ---------------------------------------------------------------------------
# Schema: chave -> (padrão, tipo, mínimo, máximo)
# Mínimo/máximo valem só para int/float; para os demais tipos são None.
# ---------------------------------------------------------------------------
_SCHEMA = {
    # --- Geral (arranque) ---
    "auto_carregar_config": (True, bool, None, None),
    "verificar_atualizacoes": (True, bool, None, None),
    "splash_minimo_ms": (900, int, 0, 5000),
    "confirmar_saida_em_experimento": (True, bool, None, None),

    # --- Aparência (escala e geometria exigem reinício) ---
    "escala_ui": (100, int, 90, 150),
    "abrir_maximizado": (False, bool, None, None),
    "lembrar_geometria": (True, bool, None, None),

    # --- Dados & Arquivos ---
    "pasta_dados_padrao": ("", str, None, None),     # "" = padrão do sistema (Documentos/ComPasso)
    "formato_timestamp_sessao": ("%d-%m-%Y_%H-%M-%S", str, None, None),
    "extensoes_audio": ([".mp3", ".wav", ".ogg"], list, None, None),
    "gerar_xlsx": (True, bool, None, None),

    # --- Conexão ---
    "lsl_timeout_s": (2, int, 1, 15),
    "watchdog_timeout_s": (15, int, 5, 60),

    # --- Diagnóstico ---
    "nivel_log": ("INFO", str, None, None),
    "retencao_logs_dias": (30, int, 0, 365),         # 0 = nunca apagar

    # --- Simulação (teste da interface sem hardware) ---
    "simular_bitalino": (False, bool, None, None),

    # --- Avançado (afeta a coleta; a UI exige consentimento) ---
    "idade_minima": (0, int, 0, 120),
    "idade_maxima": (120, int, 0, 120),
    "palavras_ruido": (["ruido", "ruído", "noise", "barulho", "white noise", "pink noise"],
                       list, None, None),
    "volume_inicial": (50, int, 0, 100),
    "controlar_volume_sistema": (True, bool, None, None),
}

# Preferências que a aplicação só consegue honrar num novo arranque — a UI as marca com um
# aviso "requer reinício" em vez de fingir que a mudança já valeu.
REQUEREM_REINICIO = ("escala_ui", "nivel_log", "retencao_logs_dias")

# Cache em memória: lido do disco uma vez e mantido, para os pontos de consumo (validação de
# idade, varredura de músicas...) poderem chamar `obter()` sem custo de I/O a cada chamada.
_cache: dict | None = None


def padroes() -> dict:
    """Retorna um dict novo com todos os valores padrão (nunca a instância interna)."""
    return {chave: _copiar(spec[0]) for chave, spec in _SCHEMA.items()}


def _copiar(valor):
    """Cópia rasa de listas/dicts para o chamador nunca alterar o padrão por referência."""
    if isinstance(valor, list):
        return list(valor)
    if isinstance(valor, dict):
        return dict(valor)
    return valor


def obter() -> dict:
    """Retorna as preferências efetivas (padrões sobrepostos pelo que houver salvo).

    Só lê o disco na primeira chamada; as seguintes usam o cache em memória.
    """
    global _cache
    if _cache is None:
        salvas = _read_prefs().get(_SECAO, {})
        if not isinstance(salvas, dict):
            config_logger.logger.warning(
                "Seção 'app' de prefs.json não é um objeto; usando os padrões.")
            salvas = {}
        salvas = _migrar(salvas)
        limpo, erros = validar(salvas)
        for erro in erros:
            config_logger.logger.warning(f"Preferência do app ignorada: {erro}")
        _cache = limpo
    return dict(_cache)


def definir(novas: dict) -> list:
    """Valida e persiste as preferências informadas. Retorna a lista de erros encontrados.

    Valores inválidos são substituídos pelo padrão (e reportados), em vez de abortar a gravação:
    uma preferência ruim não pode impedir o usuário de salvar as outras.
    """
    global _cache
    limpo, erros = validar(novas)
    prefs = _read_prefs()
    prefs[_SECAO] = dict(limpo, versao_schema=PREFS_SCHEMA_VERSION)
    _write_prefs(prefs)
    _cache = limpo
    config_logger.logger.info(f"Preferências do app salvas ({len(limpo)} chave(s)).")
    return erros


def restaurar_padroes() -> None:
    """Devolve todas as preferências do app aos valores de fábrica e persiste."""
    definir(padroes())
    config_logger.logger.info("Preferências do app restauradas para os padrões.")


def recarregar() -> None:
    """Descarta o cache, forçando a próxima ``obter()`` a reler o disco (usado nos testes)."""
    global _cache
    _cache = None


def validar(valores: dict) -> tuple:
    """Valida um dict de preferências contra o schema.

    Retorna ``(limpo, erros)``: ``limpo`` sempre traz todas as chaves do schema (as inválidas ou
    ausentes caem no padrão) e ``erros`` traz mensagens acionáveis, com o valor recebido e a
    faixa esperada.
    """
    limpo = padroes()
    erros = []
    for chave, valor in (valores or {}).items():
        if chave == "versao_schema":
            continue
        spec = _SCHEMA.get(chave)
        if spec is None:
            # chave desconhecida: provavelmente de uma versão mais nova do app; ignorar em
            # silêncio seria pior que avisar, mas não é motivo para recusar o resto.
            erros.append(f"'{chave}' não é uma preferência conhecida; ignorada.")
            continue
        padrao, tipo, minimo, maximo = spec
        erro = _validar_valor(chave, valor, tipo, minimo, maximo)
        if erro:
            erros.append(erro)
            continue
        limpo[chave] = _copiar(valor)

    # regra entre campos: a faixa etária precisa ser coerente.
    if limpo["idade_minima"] > limpo["idade_maxima"]:
        erros.append(f"Idade mínima ({limpo['idade_minima']}) não pode ser maior que a máxima "
                     f"({limpo['idade_maxima']}); faixa restaurada para o padrão.")
        limpo["idade_minima"] = _SCHEMA["idade_minima"][0]
        limpo["idade_maxima"] = _SCHEMA["idade_maxima"][0]

    if limpo["nivel_log"] not in NIVEIS_LOG:
        erros.append(f"Nível de log '{limpo['nivel_log']}' inválido; "
                     f"esperado um de {', '.join(NIVEIS_LOG)}.")
        limpo["nivel_log"] = _SCHEMA["nivel_log"][0]

    if limpo["pasta_dados_padrao"] and not os.path.isdir(limpo["pasta_dados_padrao"]):
        erros.append(f"Pasta de dados '{limpo['pasta_dados_padrao']}' não existe; "
                     "usando a pasta padrão do sistema.")
        limpo["pasta_dados_padrao"] = ""

    if not limpo["extensoes_audio"]:
        erros.append("A lista de extensões de áudio não pode ficar vazia; padrão restaurado.")
        limpo["extensoes_audio"] = _copiar(_SCHEMA["extensoes_audio"][0])

    return limpo, erros


def _validar_valor(chave, valor, tipo, minimo, maximo):
    """Valida um único valor. Retorna a mensagem de erro, ou None se estiver correto."""
    # bool é subclasse de int em Python: sem esta checagem, True passaria por um campo int.
    if tipo is int and isinstance(valor, bool):
        return f"'{chave}' esperava um número, recebeu um booleano ({valor})."
    if tipo is bool and not isinstance(valor, bool):
        return f"'{chave}' esperava verdadeiro/falso, recebeu {valor!r}."
    if not isinstance(valor, tipo):
        return f"'{chave}' esperava {tipo.__name__}, recebeu {type(valor).__name__} ({valor!r})."
    if tipo is int and (valor < minimo or valor > maximo):
        return f"'{chave}' = {valor} fora da faixa aceita ({minimo} a {maximo})."
    if tipo is list and not all(isinstance(item, str) for item in valor):
        return f"'{chave}' deve conter apenas texto; recebeu {valor!r}."
    return None


def _migrar(salvas: dict) -> dict:
    """Adapta preferências gravadas por uma versão anterior do schema.

    Hoje não há nada a migrar (só existe a versão 1) — o merge por chave de ``obter()`` já cobre
    chaves novas. Esta função existe para o dia em que uma chave for renomeada ou mudar de
    unidade, casos em que o merge silenciosamente perderia o valor do usuário.
    """
    versao = salvas.get("versao_schema", PREFS_SCHEMA_VERSION)
    if versao == PREFS_SCHEMA_VERSION:
        return salvas
    if versao > PREFS_SCHEMA_VERSION:
        config_logger.logger.warning(
            f"prefs.json foi gravado por uma versão mais nova do ComPasso (schema {versao} > "
            f"{PREFS_SCHEMA_VERSION}); chaves desconhecidas serão ignoradas.")
    return salvas


# ---------------------------------------------------------------------------
# Geometria da janela — ESTADO, não preferência.
# Fica fora do schema (em prefs["janela"]) de propósito: não é algo que o usuário escolhe na
# janela de configurações, é o app lembrando onde a janela estava. Misturar as duas coisas
# faria "Restaurar padrões" mexer na posição da janela, o que ninguém espera.
# ---------------------------------------------------------------------------
def obter_geometria() -> dict | None:
    """Retorna ``{x, y, largura, altura}`` da última sessão, ou ``None`` se não houver.

    Só devolve algo se a preferência ``lembrar_geometria`` estiver ligada e os valores forem
    plausíveis — uma geometria salva com um monitor que não existe mais deixaria a janela
    invisível fora da área da tela.
    """
    if not obter().get("lembrar_geometria", True):
        return None
    dados = _read_prefs().get("janela")
    if not isinstance(dados, dict):
        return None
    try:
        geo = {chave: int(dados[chave]) for chave in ("x", "y", "largura", "altura")}
    except (KeyError, TypeError, ValueError):
        return None
    if geo["largura"] < 200 or geo["altura"] < 150:
        return None
    return geo


def definir_geometria(x, y, largura, altura) -> None:
    """Guarda a geometria da janela (silencioso: falhar aqui nunca deve atrapalhar o usuário)."""
    if not obter().get("lembrar_geometria", True):
        return
    try:
        prefs = _read_prefs()
        prefs["janela"] = {"x": int(x), "y": int(y),
                           "largura": int(largura), "altura": int(altura)}
        _write_prefs(prefs)
    except Exception as e:
        config_logger.logger.warning(f"Não foi possível salvar a geometria da janela: {e}")


def resumo_para_log() -> str:
    """Uma linha com as preferências que diferem do padrão (vazia se estiver tudo padrão).

    Usada no início de cada sessão: é o que permite, meses depois, saber se aquela coleta rodou
    com a faixa etária ou o volume inicial alterados.
    """
    atual, base = obter(), padroes()
    diferencas = [f"{c}={atual[c]!r}" for c in sorted(atual) if atual[c] != base[c]]
    return ", ".join(diferencas)


def escrever_ambiente(destino: str, extras: dict | None = None) -> str | None:
    """Grava ``ambiente.json`` na pasta da sessão, com as prefs efetivas e o que mais vier.

    O log rotaciona e fica na máquina do operador; este arquivo viaja junto dos CSVs, então é
    ele que responde "com que ajustes esta coleta rodou?" para quem for analisar os dados.

    :return: o caminho escrito, ou ``None`` se a gravação falhar (nunca levanta: uma sessão não
        pode ser perdida porque um arquivo de metadados não gravou).
    """
    caminho = os.path.join(destino, "ambiente.json")
    conteudo = {
        "versao_schema_prefs": PREFS_SCHEMA_VERSION,
        "preferencias_app": obter(),
    }
    if extras:
        conteudo.update(extras)
    try:
        with open(caminho, "w", encoding=ENCODING_FORMAT) as f:
            json.dump(conteudo, f, indent=2, ensure_ascii=False)
        return caminho
    except Exception as e:
        config_logger.logger.warning(f"Não foi possível gravar '{caminho}': {e}")
        return None
