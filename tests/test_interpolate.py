"""Tests of interpolate.py module."""

import numpy as np
import pytest

from two_photon import interpolate


def test_interpolate_nan_small():
    data = np.array([1.0, np.nan, 3.0]).reshape((3, 1, 1))
    expected = np.array([1.0, 2.0, 3.0]).reshape((3, 1, 1))
    result = interpolate.interpolate_nan(data)
    np.testing.assert_equal(result, expected)


def test_interpolate_nan_large():
    data = np.array(
        [
            [
                [[1.0, 4.0], [2.0, 0.0]],
            ],
            [
                [[np.nan, np.nan], [3.0, np.nan]],
            ],
            [
                [[np.nan, 4.0], [np.nan, -5.0]],
            ],
            [
                [[7.0, 4.0], [2.0, 3.0]],
            ],
        ]
    )
    expected = np.array(
        [
            [
                [[1.0, 4.0], [2.0, 0.0]],
            ],
            [
                [[3.0, 4.0], [3.0, -2.5]],
            ],
            [
                [[5.0, 4.0], [2.5, -5.0]],
            ],
            [
                [[7.0, 4.0], [2.0, 3.0]],
            ],
        ]
    )

    result = interpolate.interpolate_nan(data)
    np.testing.assert_equal(result, expected)


def test_interpolate_nan_extrapolation_error():
    data = np.array([1.0, 2.0, np.nan]).reshape((3, 1, 1))
    with pytest.raises(ValueError):
        interpolate.interpolate_nan(data).compute()
