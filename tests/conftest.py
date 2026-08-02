"""Shared pytest configuration for the repository test suite."""


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "slow: opt-in tests that build TauP models or run other multi-second work",
    )
