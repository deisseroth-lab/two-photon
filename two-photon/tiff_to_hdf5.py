"""Script to convert Bruker OME TIFF stack to hdf5."""

import argparse
import logging
import os
import pathlib
import re

import dask.array as da
import h5py
import tifffile

logger = logging.getLogger(__name__)

HDF5_KEY = '/data'  # Default key name in Suite2P.

TIFF_RE = r'^.*_Cycle00001_Ch(?P<channel>\d+)_000001.ome.tif$'
TIFF_GLOB = '*_Cycle*_Ch{channel}_*.ome.tif'


class TiffToHdf5Error(Exception):
    """Error during conversion of TIFF stack to HDF5."""


def tiff_to_hdf(infile, outfile, delete_tiffs):
    """Convert a stack of TIFF files ripped from Bruker into a single HDF5 file."""
    os.makedirs(outfile.parent, exist_ok=True)

    logger.info('Locating TIFF files')
    channel = re.match(TIFF_RE, str(infile)).group('channel')
    tiff_files = infile.parent.glob(TIFF_GLOB.format(channel=channel))
    tiff_files = list(tiff_files)
    logger.info('Found %d TIFF files with channel %s', len(tiff_files), channel)

    logger.info('Reading TIFF files')
    try:
        data = tifffile.imread(infile, aszarr=True)
    except TypeError:  # Error generated when infile does not exist (why not FileNotFound?)
        raise TiffToHdf5Error('Error reading input file.  Make sure file exists and is readable:\n%s' % infile)
    logger.info('Found TIFF data with shape %s and type %s', data.shape, data.dtype)

    logger.info('Writing data to hdf5')
    chunks = ('auto', -1, -1, -1)  # (time, z, y, x)
    data_dask = da.from_array(data, chunks=chunks)
    da.to_hdf5(outfile, HDF5_KEY, data_dask)
    logger.info('Done writing hdf5')

    if delete_tiffs:
        logger.info('Deleting TIFF files')
        for tiff_file in tiff_files:
            tiff_file.unlink()
        logger.info('Done deleting TIFF files')

    logger.info('Done')


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s.%(msecs)03d %(module)s:%(lineno)s %(levelname)s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    parser = argparse.ArgumentParser(description='Convert tiff stack of a channel into hdf5 format')
    parser.add_argument('--infile', type=pathlib.Path, required=True, help='First OME TIFF file in the stack.')
    parser.add_argument(
        '--outfile',
        type=pathlib.Path,
        required=True,
        help='Output directory in which to store hdf5 file and metadata json file (must end in .h5 or .hdf5).')
    parser.add_argument('--delete_tiffs', action='store_true', help='Remove all tiff files when complete.')
    args = parser.parse_args()

    if not re.match(TIFF_RE, str(args.infile)):
        raise TiffToHdf5Error('--infile does not fit expected pattern: *_Cycle00001_Ch*_000001.ome.tif')

    if args.outfile.suffix not in {'.h5', '.hdf5'}:
        raise TiffToHdf5Error('--outfile suffix should be .h5 or .hdf5 for compatibility with Suite2p')

    tiff_to_hdf(args.infile, args.outfile, args.delete_tiffs)
