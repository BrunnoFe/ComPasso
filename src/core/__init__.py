from src.utils import SetLogger

connection_logger = SetLogger(category='connections', namelogger='connectionLogger')
player_logger = SetLogger(category='player', namelogger='playerLogger')
experiment_logger = SetLogger(category='experiment', namelogger='experimentLogger')
recorder_logger = SetLogger(category='recorder', namelogger='recorderLogger')
musics_logger = SetLogger(category='musics', namelogger='musicsLogger')
config_logger = SetLogger(category='config', namelogger='configLogger')

from .bitalino_connect import connectar_bitalino
from .recorder import LSLRecorder, build_session_dirname, build_track_filename
from .experiment import ExperimentRunner
from .musics import scan_music_files, match_conditions, MissingConditionError
from .audio import set_system_volume
from . import config_manager

__all__ = [
    'connection_logger',
    'player_logger',
    'experiment_logger',
    'recorder_logger',
    'musics_logger',
    'config_logger',
    'connectar_bitalino',
    'LSLRecorder',
    'build_session_dirname',
    'build_track_filename',
    'ExperimentRunner',
    'scan_music_files',
    'match_conditions',
    'MissingConditionError',
    'set_system_volume',
    'config_manager'
]