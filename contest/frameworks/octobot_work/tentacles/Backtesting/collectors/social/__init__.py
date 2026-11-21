from octobot_tentacles_manager.api.inspector import check_tentacle_version
from octobot_commons.logging.logging_util import get_logger

if check_tentacle_version('1.2.0', 'social_live_collector', 'OctoBot-Default-Tentacles'):
    try:
        from .social_live_collector import *
    except Exception as e:
        get_logger('TentacleLoader').error(f'Error when loading social_live_collector: '
                                           f'{e.__class__.__name__}{f" ({e})" if f"{e}" else ""}. If this '
                                           f'error persists, try reinstalling your tentacles via '
                                           f'"python start.py tentacles --install --all".')

if check_tentacle_version('1.2.0', 'social_history_collector', 'OctoBot-Default-Tentacles'):
    try:
        from .social_history_collector import *
    except Exception as e:
        get_logger('TentacleLoader').error(f'Error when loading social_history_collector: '
                                           f'{e.__class__.__name__}{f" ({e})" if f"{e}" else ""}. If this '
                                           f'error persists, try reinstalling your tentacles via '
                                           f'"python start.py tentacles --install --all".')
