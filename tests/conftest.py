"""Shared pytest fixtures for the agentobs-validate test suite."""

from __future__ import annotations

import pytest
from click.testing import CliRunner


@pytest.fixture()
def runner() -> CliRunner:
    """Return a Click CliRunner that mixes stderr into stdout (default)."""
    return CliRunner()


@pytest.fixture()
def isolated_runner() -> CliRunner:
    """Return a Click CliRunner with stderr separated from stdout."""
    return CliRunner(mix_stderr=False)
