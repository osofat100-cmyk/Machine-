from octobot_tentacles_manager.api.inspector import check_tentacle_version
from octobot_commons.logging.logging_util import get_logger

if check_tentacle_version('1.2.0', 'default_manager_agent', 'OctoBot-Default-Tentacles'):
    try:
        from .default_manager_agent import *
    except Exception as e:
        get_logger('TentacleLoader').error(f'Error when loading default_manager_agent: '
                                           f'{e.__class__.__name__}{f" ({e})" if f"{e}" else ""}. If this '
                                           f'error persists, try reinstalling your tentacles via '
                                           f'"python start.py tentacles --install --all".')

if check_tentacle_version('1.2.0', 'simple_ai_evaluator_agents_team', 'OctoBot-Default-Tentacles'):
    try:
        from .simple_ai_evaluator_agents_team import *
    except Exception as e:
        get_logger('TentacleLoader').error(f'Error when loading simple_ai_evaluator_agents_team: '
                                           f'{e.__class__.__name__}{f" ({e})" if f"{e}" else ""}. If this '
                                           f'error persists, try reinstalling your tentacles via '
                                           f'"python start.py tentacles --install --all".')
