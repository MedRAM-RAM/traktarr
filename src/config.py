import os
import yaml
from typing import Dict

def load_settings() -> Dict:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Load default settings
    default_settings_path = os.path.join(script_dir, '..', 'settings.default.yaml')
    with open(default_settings_path, 'r') as f:
        settings = yaml.safe_load(f)

    # Load and merge local settings if they exist
    local_settings_path = os.path.join(script_dir, '..', 'settings.local.yaml')
    if os.path.exists(local_settings_path):
        with open(local_settings_path, 'r') as f:
            local_settings = yaml.safe_load(f)
            if local_settings:
                settings.update(local_settings)

    # Expand paths
    settings['MEDIA_LIBRARY_TV_SHOWS_PATH'] = os.path.expanduser(settings['MEDIA_LIBRARY_TV_SHOWS_PATH'])
    settings['UNORGANIZED_TV_SHOWS_PATH'] = os.path.expanduser(settings['UNORGANIZED_TV_SHOWS_PATH'])

    # Validate required settings
    required_settings = ['TRAKT_CLIENT_ID', 'TRAKT_ACCESS_TOKEN', 'NZBGEEK_API_KEY']
    missing_settings = [s for s in required_settings if not settings.get(s)]
    if missing_settings:
        raise ValueError(f"Missing required settings: {', '.join(missing_settings)}\n"
                        f"Please add them to settings.local.yaml")

    return settings

# Load settings once when module is imported
settings = load_settings()
