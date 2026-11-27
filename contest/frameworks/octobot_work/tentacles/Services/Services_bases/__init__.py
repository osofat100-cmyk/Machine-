from octobot_tentacles_manager.api.inspector import check_tentacle_version
from octobot_commons.logging.logging_util import get_logger

if check_tentacle_version('1.2.0', 'telegram_api_service', 'OctoBot-Default-Tentacles'):
    try:
        from .telegram_api_service import *
    except Exception as e:
        get_logger('TentacleLoader').error(f'Error when loading telegram_api_service: '
                                           f'{e.__class__.__name__}{f" ({e})" if f"{e}" else ""}. If this '
                                           f'error persists, try reinstalling your tentacles via '
                                           f'"python start.py tentacles --install --all".')

if check_tentacle_version('1.2.0', 'tavily_service', 'OctoBot-Default-Tentacles'):
    try:
        from .tavily_service import *
    except Exception as e:
        get_logger('TentacleLoader').error(f'Error when loading tavily_service: '
                                           f'{e.__class__.__name__}{f" ({e})" if f"{e}" else ""}. If this '
                                           f'error persists, try reinstalling your tentacles via '
                                           f'"python start.py tentacles --install --all".')

if check_tentacle_version('1.2.0', 'coingecko_service', 'OctoBot-Default-Tentacles'):
    try:
        from .coingecko_service import *
    except Exception as e:
        get_logger('TentacleLoader').error(f'Error when loading coingecko_service: '
                                           f'{e.__class__.__name__}{f" ({e})" if f"{e}" else ""}. If this '
                                           f'error persists, try reinstalling your tentacles via '
                                           f'"python start.py tentacles --install --all".')

if check_tentacle_version('1.2.0', 'node_api_service', 'OctoBot-Default-Tentacles'):
    try:
        from .node_api_service import *
    except Exception as e:
        get_logger('TentacleLoader').error(f'Error when loading node_api_service: '
                                           f'{e.__class__.__name__}{f" ({e})" if f"{e}" else ""}. If this '
                                           f'error persists, try reinstalling your tentacles via '
                                           f'"python start.py tentacles --install --all".')

if check_tentacle_version('1.2.0', 'web_service', 'OctoBot-Default-Tentacles'):
    try:
        from .web_service import *
    except Exception as e:
        get_logger('TentacleLoader').error(f'Error when loading web_service: '
                                           f'{e.__class__.__name__}{f" ({e})" if f"{e}" else ""}. If this '
                                           f'error persists, try reinstalling your tentacles via '
                                           f'"python start.py tentacles --install --all".')

if check_tentacle_version('1.2.0', 'lunarcrush_service', 'OctoBot-Default-Tentacles'):
    try:
        from .lunarcrush_service import *
    except Exception as e:
        get_logger('TentacleLoader').error(f'Error when loading lunarcrush_service: '
                                           f'{e.__class__.__name__}{f" ({e})" if f"{e}" else ""}. If this '
                                           f'error persists, try reinstalling your tentacles via '
                                           f'"python start.py tentacles --install --all".')

if check_tentacle_version('1.2.0', 'reddit_service', 'OctoBot-Default-Tentacles'):
    try:
        from .reddit_service import *
    except Exception as e:
        get_logger('TentacleLoader').error(f'Error when loading reddit_service: '
                                           f'{e.__class__.__name__}{f" ({e})" if f"{e}" else ""}. If this '
                                           f'error persists, try reinstalling your tentacles via '
                                           f'"python start.py tentacles --install --all".')

if check_tentacle_version('1.2.0', 'gpt_service', 'OctoBot-Default-Tentacles'):
    try:
        from .gpt_service import *
    except Exception as e:
        get_logger('TentacleLoader').error(f'Error when loading gpt_service: '
                                           f'{e.__class__.__name__}{f" ({e})" if f"{e}" else ""}. If this '
                                           f'error persists, try reinstalling your tentacles via '
                                           f'"python start.py tentacles --install --all".')

if check_tentacle_version('1.2.0', 'bird_service', 'OctoBot-Default-Tentacles'):
    try:
        from .bird_service import *
    except Exception as e:
        get_logger('TentacleLoader').error(f'Error when loading bird_service: '
                                           f'{e.__class__.__name__}{f" ({e})" if f"{e}" else ""}. If this '
                                           f'error persists, try reinstalling your tentacles via '
                                           f'"python start.py tentacles --install --all".')

if check_tentacle_version('1.2.0', 'alternative_me_service', 'OctoBot-Default-Tentacles'):
    try:
        from .alternative_me_service import *
    except Exception as e:
        get_logger('TentacleLoader').error(f'Error when loading alternative_me_service: '
                                           f'{e.__class__.__name__}{f" ({e})" if f"{e}" else ""}. If this '
                                           f'error persists, try reinstalling your tentacles via '
                                           f'"python start.py tentacles --install --all".')

if check_tentacle_version('1.2.0', 'telegram_service', 'OctoBot-Default-Tentacles'):
    try:
        from .telegram_service import *
    except Exception as e:
        get_logger('TentacleLoader').error(f'Error when loading telegram_service: '
                                           f'{e.__class__.__name__}{f" ({e})" if f"{e}" else ""}. If this '
                                           f'error persists, try reinstalling your tentacles via '
                                           f'"python start.py tentacles --install --all".')

if check_tentacle_version('1.2.0', 'twitter_service', 'OctoBot-Default-Tentacles'):
    try:
        from .twitter_service import *
    except Exception as e:
        get_logger('TentacleLoader').error(f'Error when loading twitter_service: '
                                           f'{e.__class__.__name__}{f" ({e})" if f"{e}" else ""}. If this '
                                           f'error persists, try reinstalling your tentacles via '
                                           f'"python start.py tentacles --install --all".')

if check_tentacle_version('1.2.0', 'trading_view_service', 'OctoBot-Default-Tentacles'):
    try:
        from .trading_view_service import *
    except Exception as e:
        get_logger('TentacleLoader').error(f'Error when loading trading_view_service: '
                                           f'{e.__class__.__name__}{f" ({e})" if f"{e}" else ""}. If this '
                                           f'error persists, try reinstalling your tentacles via '
                                           f'"python start.py tentacles --install --all".')

if check_tentacle_version('1.2.0', 'langchain_service', 'OctoBot-Default-Tentacles'):
    try:
        from .langchain_service import *
    except Exception as e:
        get_logger('TentacleLoader').error(f'Error when loading langchain_service: '
                                           f'{e.__class__.__name__}{f" ({e})" if f"{e}" else ""}. If this '
                                           f'error persists, try reinstalling your tentacles via '
                                           f'"python start.py tentacles --install --all".')

if check_tentacle_version('1.2.0', 'google_service', 'OctoBot-Default-Tentacles'):
    try:
        from .google_service import *
    except Exception as e:
        get_logger('TentacleLoader').error(f'Error when loading google_service: '
                                           f'{e.__class__.__name__}{f" ({e})" if f"{e}" else ""}. If this '
                                           f'error persists, try reinstalling your tentacles via '
                                           f'"python start.py tentacles --install --all".')

if check_tentacle_version('1.2.0', 'coindesk_service', 'OctoBot-Default-Tentacles'):
    try:
        from .coindesk_service import *
    except Exception as e:
        get_logger('TentacleLoader').error(f'Error when loading coindesk_service: '
                                           f'{e.__class__.__name__}{f" ({e})" if f"{e}" else ""}. If this '
                                           f'error persists, try reinstalling your tentacles via '
                                           f'"python start.py tentacles --install --all".')

if check_tentacle_version('1.2.0', 'webhook_service', 'OctoBot-Default-Tentacles'):
    try:
        from .webhook_service import *
    except Exception as e:
        get_logger('TentacleLoader').error(f'Error when loading webhook_service: '
                                           f'{e.__class__.__name__}{f" ({e})" if f"{e}" else ""}. If this '
                                           f'error persists, try reinstalling your tentacles via '
                                           f'"python start.py tentacles --install --all".')

if check_tentacle_version('1.2.0', 'searxng_service', 'OctoBot-Default-Tentacles'):
    try:
        from .searxng_service import *
    except Exception as e:
        get_logger('TentacleLoader').error(f'Error when loading searxng_service: '
                                           f'{e.__class__.__name__}{f" ({e})" if f"{e}" else ""}. If this '
                                           f'error persists, try reinstalling your tentacles via '
                                           f'"python start.py tentacles --install --all".')
