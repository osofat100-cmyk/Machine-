from octobot_tentacles_manager.api.inspector import check_tentacle_version
from octobot_commons.logging.logging_util import get_logger

if check_tentacle_version('1.2.0', 'default_memory_agent', 'OctoBot-Default-Tentacles'):
    try:
        from .default_memory_agent import *
    except Exception as e:
        get_logger('TentacleLoader').error(f'Error when loading default_memory_agent: '
                                           f'{e.__class__.__name__}{f" ({e})" if f"{e}" else ""}. If this '
                                           f'error persists, try reinstalling your tentacles via '
                                           f'"python start.py tentacles --install --all".')

if check_tentacle_version('1.2.0', 'sentiment_analysis_agent', 'OctoBot-Default-Tentacles'):
    try:
        from .sentiment_analysis_agent import *
    except Exception as e:
        get_logger('TentacleLoader').error(f'Error when loading sentiment_analysis_agent: '
                                           f'{e.__class__.__name__}{f" ({e})" if f"{e}" else ""}. If this '
                                           f'error persists, try reinstalling your tentacles via '
                                           f'"python start.py tentacles --install --all".')

if check_tentacle_version('1.2.0', 'default_critic_agent', 'OctoBot-Default-Tentacles'):
    try:
        from .default_critic_agent import *
    except Exception as e:
        get_logger('TentacleLoader').error(f'Error when loading default_critic_agent: '
                                           f'{e.__class__.__name__}{f" ({e})" if f"{e}" else ""}. If this '
                                           f'error persists, try reinstalling your tentacles via '
                                           f'"python start.py tentacles --install --all".')

if check_tentacle_version('1.2.0', 'risk_judge_agent', 'OctoBot-Default-Tentacles'):
    try:
        from .risk_judge_agent import *
    except Exception as e:
        get_logger('TentacleLoader').error(f'Error when loading risk_judge_agent: '
                                           f'{e.__class__.__name__}{f" ({e})" if f"{e}" else ""}. If this '
                                           f'error persists, try reinstalling your tentacles via '
                                           f'"python start.py tentacles --install --all".')

if check_tentacle_version('1.2.0', 'bull_bear_research_agent', 'OctoBot-Default-Tentacles'):
    try:
        from .bull_bear_research_agent import *
    except Exception as e:
        get_logger('TentacleLoader').error(f'Error when loading bull_bear_research_agent: '
                                           f'{e.__class__.__name__}{f" ({e})" if f"{e}" else ""}. If this '
                                           f'error persists, try reinstalling your tentacles via '
                                           f'"python start.py tentacles --install --all".')

if check_tentacle_version('1.2.0', 'real_time_analysis_agent', 'OctoBot-Default-Tentacles'):
    try:
        from .real_time_analysis_agent import *
    except Exception as e:
        get_logger('TentacleLoader').error(f'Error when loading real_time_analysis_agent: '
                                           f'{e.__class__.__name__}{f" ({e})" if f"{e}" else ""}. If this '
                                           f'error persists, try reinstalling your tentacles via '
                                           f'"python start.py tentacles --install --all".')

if check_tentacle_version('1.2.0', 'summarization_agent', 'OctoBot-Default-Tentacles'):
    try:
        from .summarization_agent import *
    except Exception as e:
        get_logger('TentacleLoader').error(f'Error when loading summarization_agent: '
                                           f'{e.__class__.__name__}{f" ({e})" if f"{e}" else ""}. If this '
                                           f'error persists, try reinstalling your tentacles via '
                                           f'"python start.py tentacles --install --all".')

if check_tentacle_version('1.2.0', 'signal_agent', 'OctoBot-Default-Tentacles'):
    try:
        from .signal_agent import *
    except Exception as e:
        get_logger('TentacleLoader').error(f'Error when loading signal_agent: '
                                           f'{e.__class__.__name__}{f" ({e})" if f"{e}" else ""}. If this '
                                           f'error persists, try reinstalling your tentacles via '
                                           f'"python start.py tentacles --install --all".')

if check_tentacle_version('1.2.0', 'risk_agent', 'OctoBot-Default-Tentacles'):
    try:
        from .risk_agent import *
    except Exception as e:
        get_logger('TentacleLoader').error(f'Error when loading risk_agent: '
                                           f'{e.__class__.__name__}{f" ({e})" if f"{e}" else ""}. If this '
                                           f'error persists, try reinstalling your tentacles via '
                                           f'"python start.py tentacles --install --all".')

if check_tentacle_version('1.2.0', 'technical_analysis_agent', 'OctoBot-Default-Tentacles'):
    try:
        from .technical_analysis_agent import *
    except Exception as e:
        get_logger('TentacleLoader').error(f'Error when loading technical_analysis_agent: '
                                           f'{e.__class__.__name__}{f" ({e})" if f"{e}" else ""}. If this '
                                           f'error persists, try reinstalling your tentacles via '
                                           f'"python start.py tentacles --install --all".')

if check_tentacle_version('1.2.0', 'distribution_agent', 'OctoBot-Default-Tentacles'):
    try:
        from .distribution_agent import *
    except Exception as e:
        get_logger('TentacleLoader').error(f'Error when loading distribution_agent: '
                                           f'{e.__class__.__name__}{f" ({e})" if f"{e}" else ""}. If this '
                                           f'error persists, try reinstalling your tentacles via '
                                           f'"python start.py tentacles --install --all".')
