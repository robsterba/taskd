"""Application version information."""
import os
import pathlib

# Read version from VERSION file in the project root
# Falls back to hardcoded version if file not found
VERSION_FILE = pathlib.Path(__file__).parent.parent.parent / "VERSION"

try:
    with open(VERSION_FILE, 'r') as f:
        VERSION = f.read().strip()
except (FileNotFoundError, IOError):
    # Fallback version
    VERSION = "1.0.0"
