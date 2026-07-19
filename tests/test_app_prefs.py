"""Preferências do aplicativo (``core.app_prefs``): schema, validação e persistência.

Foco na validação — é ela que protege o app de um ``prefs.json`` editado à mão ou gravado por
outra versão. Nenhum teste toca o ``prefs.json`` real: a persistência é redirecionada para
``tmp_path`` via monkeypatch de ``get_prefs_path``.
"""

import json

import pytest

from compasso.core import app_prefs


@pytest.fixture
def prefs_isoladas(tmp_path, monkeypatch):
    """Redireciona a leitura/escrita de prefs.json para um arquivo temporário."""
    caminho = tmp_path / "prefs.json"
    monkeypatch.setattr(app_prefs, "get_prefs_path", lambda: caminho)
    monkeypatch.setattr("compasso.core.config_manager.get_prefs_path", lambda: caminho)
    app_prefs.recarregar()
    yield caminho
    app_prefs.recarregar()


# --------------------------------------------------------------------------- #
# Padrões e schema
# --------------------------------------------------------------------------- #
def test_padroes_traz_todas_as_chaves_do_schema():
    padroes = app_prefs.padroes()
    assert set(padroes) == set(app_prefs._SCHEMA)


def test_padroes_devolve_copias_independentes():
    """Mutar o resultado não pode contaminar o padrão de fábrica de outros chamadores."""
    primeiro = app_prefs.padroes()
    primeiro["extensoes_audio"].append(".flac")
    assert ".flac" not in app_prefs.padroes()["extensoes_audio"]


def test_faixa_etaria_de_fabrica_permite_criancas():
    """A trava antiga (18–100) impedia coleta com crianças; o padrão agora é 0–120."""
    padroes = app_prefs.padroes()
    assert padroes["idade_minima"] == 0
    assert padroes["idade_maxima"] == 120


# --------------------------------------------------------------------------- #
# Validação
# --------------------------------------------------------------------------- #
def test_valores_validos_sobrevivem():
    limpo, erros = app_prefs.validar({"lsl_timeout_s": 8, "gerar_xlsx": False})
    assert erros == []
    assert limpo["lsl_timeout_s"] == 8
    assert limpo["gerar_xlsx"] is False


def test_valor_fora_da_faixa_cai_no_padrao_e_reporta():
    limpo, erros = app_prefs.validar({"lsl_timeout_s": 999})
    assert limpo["lsl_timeout_s"] == app_prefs._SCHEMA["lsl_timeout_s"][0]
    assert any("999" in e and "fora da faixa" in e for e in erros)


def test_booleano_nao_passa_por_campo_numerico():
    """bool é subclasse de int em Python: sem checagem explícita, True viraria 1."""
    limpo, erros = app_prefs.validar({"lsl_timeout_s": True})
    assert limpo["lsl_timeout_s"] == app_prefs._SCHEMA["lsl_timeout_s"][0]
    assert any("booleano" in e for e in erros)


def test_tipo_errado_cai_no_padrao():
    limpo, erros = app_prefs.validar({"gerar_xlsx": "sim"})
    assert limpo["gerar_xlsx"] is True
    assert any("verdadeiro/falso" in e for e in erros)


def test_chave_desconhecida_e_reportada_sem_derrubar_o_resto():
    limpo, erros = app_prefs.validar({"chave_do_futuro": 1, "gerar_xlsx": False})
    assert limpo["gerar_xlsx"] is False           # o resto continua valendo
    assert "chave_do_futuro" not in limpo
    assert any("chave_do_futuro" in e for e in erros)


def test_faixa_etaria_invertida_e_corrigida():
    limpo, erros = app_prefs.validar({"idade_minima": 80, "idade_maxima": 20})
    assert limpo["idade_minima"] <= limpo["idade_maxima"]
    assert any("não pode ser maior" in e for e in erros)


def test_nivel_log_invalido_cai_no_padrao():
    limpo, erros = app_prefs.validar({"nivel_log": "VERBOSO"})
    assert limpo["nivel_log"] == "INFO"
    assert any("VERBOSO" in e for e in erros)


def test_pasta_inexistente_e_recusada(tmp_path):
    limpo, erros = app_prefs.validar({"pasta_dados_padrao": str(tmp_path / "nao_existe")})
    assert limpo["pasta_dados_padrao"] == ""
    assert any("não existe" in e for e in erros)


def test_pasta_existente_e_aceita(tmp_path):
    limpo, erros = app_prefs.validar({"pasta_dados_padrao": str(tmp_path)})
    assert limpo["pasta_dados_padrao"] == str(tmp_path)
    assert erros == []


def test_extensoes_vazias_caem_no_padrao():
    limpo, erros = app_prefs.validar({"extensoes_audio": []})
    assert limpo["extensoes_audio"] == app_prefs._SCHEMA["extensoes_audio"][0]
    assert any("vazia" in e for e in erros)


def test_lista_com_item_nao_texto_e_recusada():
    limpo, erros = app_prefs.validar({"palavras_ruido": ["ruido", 42]})
    assert limpo["palavras_ruido"] == app_prefs._SCHEMA["palavras_ruido"][0]
    assert any("apenas texto" in e for e in erros)


# --------------------------------------------------------------------------- #
# Persistência e versão do schema
# --------------------------------------------------------------------------- #
def test_definir_e_obter_fazem_roundtrip(prefs_isoladas):
    app_prefs.definir(dict(app_prefs.padroes(), lsl_timeout_s=7, gerar_xlsx=False))
    app_prefs.recarregar()
    atual = app_prefs.obter()
    assert atual["lsl_timeout_s"] == 7
    assert atual["gerar_xlsx"] is False


def test_grava_a_versao_do_schema(prefs_isoladas):
    app_prefs.definir(app_prefs.padroes())
    dados = json.loads(prefs_isoladas.read_text(encoding="utf-8"))
    assert dados["app"]["versao_schema"] == app_prefs.PREFS_SCHEMA_VERSION


def test_definir_preserva_outras_secoes(prefs_isoladas):
    """prefs.json também guarda tema/última config/gráfico — salvar 'app' não pode apagá-las."""
    prefs_isoladas.write_text(json.dumps({"theme": "Aurora", "last_config": "/x.config"}),
                              encoding="utf-8")
    app_prefs.definir(dict(app_prefs.padroes(), gerar_xlsx=False))
    dados = json.loads(prefs_isoladas.read_text(encoding="utf-8"))
    assert dados["theme"] == "Aurora"
    assert dados["last_config"] == "/x.config"


def test_chave_ausente_no_arquivo_cai_no_padrao(prefs_isoladas):
    """Merge por chave: um arquivo antigo, sem a chave nova, não quebra nada."""
    prefs_isoladas.write_text(json.dumps({"app": {"gerar_xlsx": False}}), encoding="utf-8")
    app_prefs.recarregar()
    atual = app_prefs.obter()
    assert atual["gerar_xlsx"] is False                       # o que estava salvo vale
    assert atual["lsl_timeout_s"] == app_prefs._SCHEMA["lsl_timeout_s"][0]   # o resto, padrão


def test_secao_corrompida_cai_nos_padroes(prefs_isoladas):
    prefs_isoladas.write_text(json.dumps({"app": "isto não é um objeto"}), encoding="utf-8")
    app_prefs.recarregar()
    assert app_prefs.obter() == app_prefs.padroes()


def test_restaurar_padroes(prefs_isoladas):
    app_prefs.definir(dict(app_prefs.padroes(), lsl_timeout_s=11))
    app_prefs.restaurar_padroes()
    assert app_prefs.obter() == app_prefs.padroes()


# --------------------------------------------------------------------------- #
# Rastreabilidade
# --------------------------------------------------------------------------- #
def test_resumo_para_log_vazio_quando_tudo_padrao(prefs_isoladas):
    app_prefs.definir(app_prefs.padroes())
    assert app_prefs.resumo_para_log() == ""


def test_resumo_para_log_lista_apenas_o_que_mudou(prefs_isoladas):
    app_prefs.definir(dict(app_prefs.padroes(), idade_minima=6, idade_maxima=12))
    resumo = app_prefs.resumo_para_log()
    assert "idade_minima=6" in resumo
    assert "idade_maxima=12" in resumo
    assert "gerar_xlsx" not in resumo


def test_escrever_ambiente_grava_prefs_e_extras(tmp_path):
    caminho = app_prefs.escrever_ambiente(str(tmp_path), extras={"sensor": "EDA", "canal_sinal": 1})
    dados = json.loads((tmp_path / "ambiente.json").read_text(encoding="utf-8"))
    assert caminho is not None
    assert dados["sensor"] == "EDA"
    assert dados["canal_sinal"] == 1
    assert dados["preferencias_app"]["idade_maxima"] == 120
    assert dados["versao_schema_prefs"] == app_prefs.PREFS_SCHEMA_VERSION


def test_escrever_ambiente_nao_levanta_em_destino_invalido(tmp_path):
    """Uma sessão não pode ser perdida porque o arquivo de metadados falhou."""
    assert app_prefs.escrever_ambiente(str(tmp_path / "pasta" / "inexistente")) is None
