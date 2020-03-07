"""Library for reading in TIFFs ripped from Bruker raw data."""
import logging
import warnings

import dask
import dask.array as da
from skimage.io import imread

logger = logging.getLogger(__file__)


def read(base, size, channel):
    """Read 2p dataset of TIFF files into a dask.Array."""
    shape_yx = (size['y_px'], size['x_px'])
    dtype = read_file(base, 0, channel, 0).dtype
    data_frames = []
    for frame in range(size['frames']):
        data_z_planes = []
        for z_plane in range(size['z_planes']):
            lazy_image = dask.delayed(read_file)(base, frame, channel, z_plane)
            data_z_planes.append(da.from_delayed(lazy_image, dtype=dtype, shape=shape_yx))
        data_frames.append(da.stack(data_z_planes))
    data = da.stack(data_frames)
    logger.info('Found data with shape(frames, z_planes, y_pixels, x_pixels): %s', data.shape)
    return data


def read_file(base, frame, channel, z_plane):
    """Read in one TIFF file."""
    # TODO: Frame 0 has OME-TIFF metadata which makes reading slow.  Figure out how to read OME faster!
    if frame == 0:
        frame = 1
    fname = str(base) + f'_Cycle{frame+1:05d}_Ch{channel}_{z_plane+1:06d}.ome.tif'
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", "invalid value encountered in true_divide", RuntimeWarning)
        return imread(fname)
