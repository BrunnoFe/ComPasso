"""CLI do BITalino fake: publica uma stream LSL simulada para testar a GUI sem hardware.

A lógica de geração/publicação vive em :mod:`compasso.core.fake_bitalino` (reutilizada pelo
modo embutido da GUI, via a variável de ambiente ``COMPASSO_FAKE_BITALINO``). Este script é só
o invólucro de linha de comando.

Uso:
    python scripts/fake_bitalino.py                              # MAC padrão, 100 Hz
    python scripts/fake_bitalino.py --mac AA:BB:CC:DD:EE:FF
    python scripts/fake_bitalino.py --taxa 1000

Alternativa (subir a stream junto com o app): defina COMPASSO_FAKE_BITALINO=1 antes de rodar a
GUI — ela sobe a stream fake sozinha e já pré-preenche o campo MAC. Ver BUILD.md / app.py.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Permite rodar o script diretamente (sem `pip install -e .`) achando o pacote em src/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from compasso.core.fake_bitalino import MAC_PADRAO, TAXA_PADRAO_HZ, executar

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Publica uma stream LSL fake de um BITalino, para testar a GUI sem hardware.")
    parser.add_argument("--mac", default=MAC_PADRAO, help=f'MAC simulado (padrão: "{MAC_PADRAO}").')
    parser.add_argument("--taxa", type=float, default=TAXA_PADRAO_HZ,
                        help=f"Taxa de amostragem em Hz (padrão: {TAXA_PADRAO_HZ:.0f}).")
    args = parser.parse_args()

    logging.info('BITalino fake em "%s" a %.0f Hz. Ctrl+C para encerrar.', args.mac, args.taxa)
    try:
        executar(args.mac, args.taxa)
    except KeyboardInterrupt:
        logging.info("Interrompido pelo usuário. Encerrando stream fake.")


if __name__ == "__main__":
    main()
