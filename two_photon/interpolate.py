"""Utilities for interpolating stim artefact regions."""

import numpy as np
import scipy.interpolate


def interpolate_nan(data, axis=0):
    """Interpolation of nan pixels along a given axis.

    Used to interpolate all pixels in a z-plane across the time axis."""
    return np.apply_along_axis(interp1d_nan, axis, data)


def interp1d_nan(data, kind="linear"):
    """Interpolation of nan along a 1d array."""
    assert data.ndim == 1
    nans = np.isnan(data)
    x_not_nan = (~nans).nonzero()[0]
    func = scipy.interpolate.interp1d(x_not_nan, data[~nans], kind=kind, copy=False, assume_sorted=True)

    x_nans = nans.nonzero()[0]
    data[nans] = func(x_nans)

    return data
