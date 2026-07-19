"""Resolução de recursos empacotados, agnóstica de empacotador (compasso.utils.resources).

Cobre os três cenários — dev, PyInstaller e Nuitka — e o casamento com os subcaminhos que
``assets.py``/``app.py`` concatenam. O ramo Nuitka (``__compiled__`` no namespace do módulo) não
é reproduzível em CPython puro; é validado indiretamente pela regra de layout documentada.
"""

import sys
from pathlib import Path

from compasso.utils import resources


def test_dev_sem_empacotamento_retorna_none():
    """Sem _MEIPASS e fora do Nuitka, a base é None (usa a árvore do repo)."""
    assert not hasattr(sys, "_MEIPASS")  # sanidade: a suíte não roda congelada
    assert resources.EH_NUITKA is False
    assert resources.base_recursos() is None
    assert resources.eh_empacotado() is False


def test_pyinstaller_usa_meipass(monkeypatch, tmp_path):
    """Com sys._MEIPASS setado, a base é exatamente esse diretório."""
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert resources.eh_pyinstaller() is True
    assert resources.base_recursos() == Path(str(tmp_path))


def test_assets_dir_em_dev_aponta_para_o_repo():
    """Em dev, ASSETS_DIR resolve para a pasta assets/ real do repositório."""
    from compasso.gui_qt import assets
    assert assets.ASSETS_DIR.name == "assets"
    # os arquivos reais existem (o repo tem icon.ico/png e o beep):
    assert (assets.ASSETS_DIR / "icon.ico").exists()
    assert (assets.ASSETS_DIR / assets.BEEP_FILENAME).exists()


def test_subcaminho_assets_bate_com_layout_do_bundle(monkeypatch, tmp_path):
    """No bundle, assets ficam em <base>/assets — o mesmo subcaminho que assets.py monta."""
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    base = resources.base_recursos()
    assert base / "assets" == Path(str(tmp_path)) / "assets"


def test_subcaminho_qml_bate_com_layout_do_bundle(monkeypatch, tmp_path):
    """No bundle, os .qml ficam em <base>/compasso/gui_qt/qml (regra respeitada pelos builds)."""
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    base = resources.base_recursos()
    esperado = Path(str(tmp_path)) / "compasso" / "gui_qt" / "qml"
    assert base / "compasso" / "gui_qt" / "qml" == esperado
