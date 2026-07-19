"""Verificação de nova versão no GitHub Releases.

Nenhum teste toca a rede: `urlopen` é substituído por respostas fabricadas, como o resto da
suíte faz com o hardware. Cobre a comparação de versões (onde o erro clássico é comparar como
texto), a leitura da resposta e o comportamento do controller nos três desfechos.
"""

import io
import json
import types
import urllib.error

import pytest

from compasso.core import updates


def _resposta(payload):
    """Contexto que imita o retorno de `urlopen` (objeto com .read() e context manager)."""
    corpo = json.dumps(payload).encode("utf-8")

    class _Ctx:
        def __enter__(self):
            return io.BytesIO(corpo)

        def __exit__(self, *a):
            return False

    return _Ctx()


# ------------------------------------------------------- comparação de versões
@pytest.mark.parametrize("remota, atual, esperado", [
    ("v2026.4.0", "2026.3.0", True),
    ("2026.3.1", "2026.3.0", True),
    ("v2027.1.0", "2026.12.9", True),
    ("v2026.3.0", "2026.3.0", False),
    ("v2026.2.0", "2026.3.0", False),
    ("2026.3", "2026.3.0", False),      # tamanhos diferentes, mesma versão
    ("2026.3.0", "2026.3", False),
])
def test_comparacao_de_versoes(remota, atual, esperado):
    assert updates.eh_mais_nova(remota, atual) is esperado


def test_comparacao_e_numerica_nao_textual():
    """O erro clássico: como texto, "2026.10.0" viria ANTES de "2026.9.0"."""
    assert "2026.10.0" < "2026.9.0"                      # ordem lexicográfica (errada)
    assert updates.eh_mais_nova("2026.10.0", "2026.9.0")  # ordem numérica (correta)


def test_prefixo_v_e_ignorado():
    assert updates.partes_versao("v2026.3.0") == updates.partes_versao("2026.3.0")


# --------------------------------------------------------------- consulta HTTP
def test_verificar_detecta_versao_nova(mocker):
    mocker.patch.object(updates.urllib.request, "urlopen",
                        return_value=_resposta({"tag_name": "v2026.4.0",
                                                "html_url": "https://exemplo/rel/2026.4.0"}))
    r = updates.verificar("2026.3.0")
    assert r.disponivel
    assert r.versao_remota == "2026.4.0"
    assert r.url == "https://exemplo/rel/2026.4.0"


def test_verificar_reconhece_versao_em_dia(mocker):
    mocker.patch.object(updates.urllib.request, "urlopen",
                        return_value=_resposta({"tag_name": "v2026.3.0"}))
    assert not updates.verificar("2026.3.0").disponivel


def test_falha_de_rede_vira_erro_e_nao_um_falso_negativo(mocker):
    """Sem rede não se pode afirmar "não há atualização" — isso seria mentir para o usuário."""
    mocker.patch.object(updates.urllib.request, "urlopen",
                        side_effect=urllib.error.URLError("sem conexão"))
    with pytest.raises(updates.ErroVerificacao):
        updates.verificar("2026.3.0")


def test_resposta_sem_tag_vira_erro(mocker):
    mocker.patch.object(updates.urllib.request, "urlopen", return_value=_resposta({}))
    with pytest.raises(updates.ErroVerificacao):
        updates.verificar("2026.3.0")


def test_erro_http_vira_erro_de_verificacao(mocker):
    mocker.patch.object(
        updates.urllib.request, "urlopen",
        side_effect=urllib.error.HTTPError("u", 404, "Not Found", None, None))
    with pytest.raises(updates.ErroVerificacao):
        updates.verificar("2026.3.0")


# ------------------------------------------------------------------ controller
@pytest.fixture
def controller():
    """UpdatesController com um `run_async` síncrono (sem thread, determinístico)."""
    pytest.importorskip("PySide6.QtCore")
    from compasso.gui_qt.controllers.updates_controller import UpdatesController

    def run_async(work, on_done=None):
        try:
            resultado = work()
        except Exception as e:
            resultado = e
        if on_done is not None:
            on_done(resultado)

    ctx = types.SimpleNamespace(run_async=run_async)
    return UpdatesController(ctx, versao_atual="2026.3.0")


def test_verificacao_automatica_acende_o_ponto_sem_abrir_janela(controller, mocker):
    aberturas = []
    controller.pedirAbrirJanela.connect(lambda: aberturas.append(1))
    mocker.patch.object(updates, "verificar",
                        return_value=updates.Resultado(True, "2026.3.0", "2026.4.0", "u"))
    controller.verificar_automatico()
    assert controller.temAtualizacao
    assert controller.rotuloItem == "Baixar atualização!"
    assert aberturas == [], "a verificação automática não deve abrir janela"
    assert controller.estado == controller.OCIOSO


def test_verificacao_automatica_silencia_falha_de_rede(controller, mocker):
    """Quem não pediu a verificação não recebe um erro por causa dela."""
    mocker.patch.object(updates, "verificar", side_effect=updates.ErroVerificacao("sem rede"))
    controller.verificar_automatico()
    assert not controller.temAtualizacao
    assert controller.estado == controller.OCIOSO


def test_verificacao_manual_relata_erro(controller, mocker):
    mocker.patch.object(updates, "verificar", side_effect=updates.ErroVerificacao("sem rede"))
    controller.verificar_manual()
    assert controller.estado == controller.ERRO
    assert "sem rede" in controller.erro
    assert not controller.temAtualizacao, "falha não permite afirmar que há atualização"


def test_verificacao_manual_sem_novidade(controller, mocker):
    mocker.patch.object(updates, "verificar",
                        return_value=updates.Resultado(False, "2026.3.0", "2026.3.0", "u"))
    controller.verificar_manual()
    assert controller.estado == controller.ATUALIZADO
    assert not controller.temAtualizacao


def test_ponto_vermelho_sobrevive_ao_fechar_a_janela(controller, mocker):
    mocker.patch.object(updates, "verificar",
                        return_value=updates.Resultado(True, "2026.3.0", "2026.4.0", "u"))
    controller.verificar_manual()
    assert controller.estado == controller.DISPONIVEL
    controller.fechar()
    assert controller.estado == controller.OCIOSO
    assert controller.temAtualizacao, "o menu deve continuar sinalizando após o Cancelar"


def test_item_de_menu_baixa_quando_ja_sabe_da_versao_nova(controller, mocker):
    mocker.patch.object(updates, "verificar",
                        return_value=updates.Resultado(True, "2026.3.0", "2026.4.0", "u"))
    controller.verificar_automatico()
    abrir = mocker.patch.object(controller, "abrir_releases")
    controller.acionar_item()
    abrir.assert_called_once()
