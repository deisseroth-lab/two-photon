"""Useful testing fixtures."""

import pathlib

import pytest


@pytest.fixture
def testdata():
    return pathlib.Path(__file__).parent / "testdata"
