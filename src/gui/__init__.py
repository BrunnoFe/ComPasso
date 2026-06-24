from src.utils import SetLogger

gui_logger = SetLogger(category='gui', namelogger='guiLogger')

from .guiconfigs import set_window_grid, set_window_configs, set_grids
from .context import AppContext
from .main import Compasso

__all__ = [
    'gui_logger',
    'set_window_grid',
    'set_window_configs',
    'set_grids',
    'AppContext',
    'Compasso'
]