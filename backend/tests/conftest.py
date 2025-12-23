"""Pytest configuration and shared fixtures."""

import os
import pytest
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables."""
    # Set default test suite name if not already set
    if not os.getenv("LANGSMITH_TEST_SUITE"):
        os.environ["LANGSMITH_TEST_SUITE"] = "Movie Recommendations Tests"
    
    # Set default experiment name if not already set
    if not os.getenv("LANGSMITH_EXPERIMENT"):
        os.environ["LANGSMITH_EXPERIMENT"] = "pytest-evaluation"
    
    yield
    
    # Cleanup if needed
    pass

