#!/usr/bin/env python3
"""
Pytest configuration for HP Tuners AI Agent tests
"""

import pytest
import sys
from pathlib import Path

# Add skills to path
sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "hpt_converter"))
sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "j2534_passthru"))


def pytest_configure(config):
    """Configure pytest environment"""
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")


@pytest.fixture
def temp_directory(tmp_path):
    """Provide a temporary directory for tests"""
    return tmp_path


@pytest.fixture
def sample_hpt_header():
    """Create a sample HPT header for testing"""
    return {
        "platform": "GM_E37",
        "metadata_offset": 512,
        "binary_offset": 1024,
        "binary_size": 1048576
    }
