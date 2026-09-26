"""Application version information."""
import pathlib

# Path to VERSION file in the project root
VERSION_FILE = pathlib.Path(__file__).parent.parent.parent / "VERSION"


def get_version():
    """Read version from VERSION file. Returns '1.0.0' if file not found."""
    try:
        with open(VERSION_FILE, 'r') as f:
            return f.read().strip()
    except (FileNotFoundError, IOError):
        # Fallback version
        return "1.0.0"


# Read version at module load time for compatibility
VERSION = get_version()
