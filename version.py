"""Version management — single source of truth for the version string."""
import os

_VERSION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'VERSION')

def get_version() -> str:
    """Read the current version number from the VERSION file."""
    try:
        with open(_VERSION_FILE, 'r') as f:
            return f.read().strip()
    except:
        return '0.0.0'

__version__ = get_version()
