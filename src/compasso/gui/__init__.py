from compasso.utils import SetLogger

gui_logger = SetLogger(category='gui', namelogger='guiLogger')

from .guiconfigs import set_window_configs
from .context import AppContext
from .app import ComPasso

__all__ = [
    'gui_logger',
    'set_window_configs',
    'AppContext',
    'ComPasso'
]
