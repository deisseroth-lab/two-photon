"""Utilities for interpolating stim artefact regions."""

import dask.array as da
import numpy as np
import scipy.interpolate


def interpolate_nan(data, axis=0, kind="linear"):
    """Interpolation of nan pixels along a given axis.

    Parameters
    ----------
    data : array
        Data array with nan values to be interpolated.
    axis : int
        The axis dimension over which the interpolation is performed
    kind : string
        The mode of interpolation. See `scipy.interpolate.interp1d`.

    Returns
    -------
    interpolated : dask.array
        Data with same shape as original data, with nan filled by interpolation.
    """
    shape = (data.shape[axis],)
    return da.apply_along_axis(interp1d_nan, axis, data, dtype=data.dtype, shape=shape, kind=kind)


def interp1d_nan(data, kind="linear"):
    """Interpolation of nan along a 1d array."""
    assert data.ndim == 1

    nans = np.isnan(data)
    x_nans = nans.nonzero()[0]
    x_not_nan = (~nans).nonzero()[0]

    func = scipy.interpolate.interp1d(x_not_nan, data[~nans], kind=kind, copy=False, assume_sorted=True)

    data[nans] = func(x_nans)
    return data
