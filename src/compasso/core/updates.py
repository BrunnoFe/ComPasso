"""Verificação de nova versão publicada no GitHub Releases.

Consulta a API pública do GitHub (``/releases/latest``, que já ignora rascunhos e pré-releases)
e compara a tag publicada com a versão em execução. Usa apenas ``urllib`` da biblioteca padrão:
uma única requisição GET não justifica uma dependência nova, e o executável empacotado fica
menor sem ela.

Nada aqui toca a interface nem bloqueia: quem chama é responsável por rodar fora da thread da
GUI (o ``UpdatesController`` usa ``ctx.run_async``). Falha de rede é sinalizada por
``ErroVerificacao`` — nunca por um resultado "não há atualização", que seria mentira.
"""

import json
import re
import urllib.error
import urllib.request
from typing import NamedTuple

from . import updates_logger

# Endpoint do último release ESTÁVEL. O GitHub exclui daqui rascunhos e pré-releases, então
# participantes de experimento não são avisados de versões de teste.
API_ULTIMO_RELEASE = "https://api.github.com/repos/BrunnoFe/ComPasso/releases/latest"
# Página para onde o usuário é levado ao escolher "Baixar".
RELEASES_URL = "https://github.com/BrunnoFe/ComPasso/releases"

# s — teto da requisição. Curto de propósito: a verificação automática roda durante a splash e
# não pode atrasar a abertura do app.
TIMEOUT_S = 6.0

_UA = "ComPasso-update-check"


class ErroVerificacao(Exception):
    """A verificação não pôde ser concluída (rede, HTTP ou resposta inesperada)."""


class Resultado(NamedTuple):
    """Desfecho de uma verificação bem-sucedida."""
    disponivel: bool
    versao_atual: str
    versao_remota: str
    url: str


def partes_versao(versao: str) -> tuple:
    """Converte "v2026.3.0" (ou "2026.3.0") na tupla (2026, 3, 0) para comparação numérica.

    Comparar como texto erraria: "2026.10.0" < "2026.9.0" na ordem lexicográfica. Trechos não
    numéricos são ignorados, então sufixos como "-beta" não quebram a leitura.
    """
    numeros = re.findall(r"\d+", str(versao or ""))
    return tuple(int(n) for n in numeros) or (0,)


def eh_mais_nova(remota: str, atual: str) -> bool:
    """True se `remota` for posterior a `atual` (comparação numérica por componente).

    Tuplas de tamanhos diferentes são igualadas com zeros à direita, para que "2026.3" e
    "2026.3.0" contem como a mesma versão.
    """
    a, b = partes_versao(remota), partes_versao(atual)
    tamanho = max(len(a), len(b))
    a += (0,) * (tamanho - len(a))
    b += (0,) * (tamanho - len(b))
    return a > b


def verificar(versao_atual: str, timeout: float = TIMEOUT_S) -> Resultado:
    """Consulta o último release e diz se há versão mais nova que `versao_atual`.

    :raises ErroVerificacao: sem rede, HTTP fora de 2xx ou corpo inesperado.
    """
    requisicao = urllib.request.Request(
        API_ULTIMO_RELEASE,
        headers={"Accept": "application/vnd.github+json", "User-Agent": _UA},
    )
    try:
        with urllib.request.urlopen(requisicao, timeout=timeout) as resposta:
            dados = json.loads(resposta.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise ErroVerificacao(f"O GitHub respondeu {e.code}.") from e
    except urllib.error.URLError as e:
        raise ErroVerificacao(f"Não foi possível alcançar o GitHub: {e.reason}") from e
    except (ValueError, TimeoutError, OSError) as e:
        raise ErroVerificacao(f"Resposta inesperada do GitHub: {e}") from e

    tag = str(dados.get("tag_name") or "").strip()
    if not tag:
        raise ErroVerificacao("O último release não informa uma tag de versão.")

    url = str(dados.get("html_url") or RELEASES_URL)
    disponivel = eh_mais_nova(tag, versao_atual)
    updates_logger.logger.info(
        f"Verificação de atualização: instalada={versao_atual!r}, publicada={tag!r}, "
        f"atualização disponível={disponivel}.")
    return Resultado(disponivel=disponivel, versao_atual=versao_atual,
                     versao_remota=tag.lstrip("vV"), url=url)
