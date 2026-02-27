"""
Pytest configuration for backend tests.

Sets up import paths and fixtures for testing.
"""

import sys
from pathlib import Path

# Add backend directory to path so imports work correctly
backend_dir = Path(__file__).parent.parent.absolute()
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)


def pytest_configure(config):
    """Configure pytest with custom markers and settings."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as an async test"
    )
