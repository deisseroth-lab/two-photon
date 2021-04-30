"""Script to convert Bruker OME TIFF stack to hdf5."""

import argparse
import logging
import os
import pathlib
import re

import click
import dask.array as da
import h5py
import tifffile

logger = logging.getLogger(__name__)


TIFF_GLOB_INIT = '*_Cycle00001_Ch{channel}_000001.ome.tif'
TIFF_GLOB_ALL = '*_Cycle*_Ch{channel}_*.ome.tif'


class Tiff2Hdf5Error(Exception):
    """Error during conversion of TIFF stack to HDF5."""

@click.command()
@click.pass_context
@click.option('--channel', type=int, required=True,
              help='Channel number of tiff stack to convert to hdf5')
def tiff2hdf5(ctx, channel):
    """Convert an OME TIFF stack to a single HDF5 file."""

    # Bruker software appends the raw_path basename to the given output directory.
    tiff_path = ctx.obj['tiff_path'] / ctx.obj['raw_path'].name
    orig_hdf5_path = ctx.obj['orig_hdf5_path']
    hdf5_key = ctx.obj['hdf5_key']

    os.makedirs(orig_hdf5_path.parent, exist_ok=True)

    # To load OME tiff stacks, it suffices to load just the first file, which contains
    # metadata to allow the tifffile to load the entire stack.
    tiff_init = tiff_file.glob(TIFF_GLOB_INIT.format(channel=channel))
    if len(tiff_init) != 1:
        raise Tiff2Hdf5Error('Expected one initial tifffile, found: %s', tiff_glob)
    tiff_init = tiff_init[0]

    logger.info('Reading TIFF files')
    try:
        data = tifffile.imread(tiff_init, aszarr=True)  # aszarr is lazy and dask-compatible
    except TypeError:  # Error generated when file does not exist (why not FileNotFound?)
        raise Tiff2Hdf5Error('Error reading input tiff file.  Make sure file exists and is readable:\n%s' % tiff_init)
    logger.info('Found TIFF data with shape %s and type %s', data.shape, data.dtype)

    logger.info('Writing data to hdf5')
    chunks = ('auto', -1, -1, -1)  # (time, z, y, x)
    data_dask = da.from_array(data, chunks=chunks)
    da.to_hdf5(orig_hdf5_path, hdf5_key, data_dask)
    logger.info('Done writing hdf5')

    logger.info('Done')
