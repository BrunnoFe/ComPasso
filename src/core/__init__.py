from src.utils import SetLogger

connection_logger = SetLogger(category='connections', namelogger='connectionLogger')
player_logger = SetLogger(category='player', namelogger='playerLogger')
experiment_logger = SetLogger(category='experiment', namelogger='experimentLogger')
recorder_logger = SetLogger(category='recorder', namelogger='recorderLogger')
musics_logger = SetLogger(category='musics', namelogger='musicsLogger')

from .bitalino_connect import connectar_bitalino, run_scan_devices
from .recorder import LSLRecorder, build_output_basename
from .experiment import ExperimentRunner
from .musics import scan_music_files, match_conditions, MissingConditionError
from .audio import set_master_volume

__all__ = [
    'connection_logger',
    'player_logger',
    'experiment_logger',
    'recorder_logger',
    'musics_logger',
    'connectar_bitalino',
    'run_scan_devices',
    'LSLRecorder',
    'build_output_basename',
    'ExperimentRunner',
    'scan_music_files',
    'match_conditions',
    'MissingConditionError',
    'set_master_volume'
]