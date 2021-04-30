"""Library for reading in TIFFs ripped from Bruker raw data."""
import logging
import warnings

import dask
import dask.array as da
from skimage.io import imread

logger = logging.getLogger(__file__)


def read(base, size, layout, channel):
    """Read 2p dataset of TIFF files into a dask.Array."""
    shape_yx = (size["y_px"], size["x_px"])
    dtype = read_file(base, 0, channel, 0).dtype

    num_cycles = layout["sequences"]
    frames_are_z = num_cycles == 1

    data_cycles = []
    for cycle in range(num_cycles):
        data_frames = []
        for frame in range(layout["frames_per_sequence"]):

            # Reading the first OME TIFF file is slow, so we substitute the following frame/cycle:
            # - use the next frame if a single-cycle where frames are z-planes
            # - use the next cycle if multi-cycle
            if frames_are_z:
                if frame == 0:
                    frame = 1
            else:
                if cycle == 0:
                    cycle = 1

            lazy_image = dask.delayed(read_file)(base, cycle, channel, frame)
            data_frames.append(da.from_delayed(lazy_image, dtype=dtype, shape=shape_yx))
        data_cycles.append(da.stack(data_frames))

    data = da.stack(data_cycles)
    if frames_are_z:
        data = data.swapaxes(0, 1)

    logger.info(
        "Found data with shape(frames, z_planes, y_pixels, x_pixels): %s", data.shape
    )
    return data


def read_file(base, cycle, channel, frame):
    """Read in one TIFF file."""
    fname = str(base) + f"_Cycle{cycle+1:05d}_Ch{channel}_{frame+1:06d}.ome.tif"
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore", "invalid value encountered in true_divide", RuntimeWarning
        )
        return imread(fname)
