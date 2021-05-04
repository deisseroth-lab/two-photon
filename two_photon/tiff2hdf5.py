"""Script to convert Bruker OME TIFF stack to hdf5."""

import logging
import shutil

import click
import dask
import dask.array as da
import tifffile
import zarr

from two_photon import correct_omexml

logger = logging.getLogger(__name__)


TIFF_GLOB_INIT = "*_Cycle00001_Ch{channel}_000001.ome.tif"


class Tiff2Hdf5Error(Exception):
    """Error during conversion of TIFF stack to HDF5."""


@click.command()
@click.pass_context
@click.option(
    "--channel",
    type=int,
    required=True,
    help="Channel number of tiff stack to convert to hdf5",
)
@click.option("--fix_bruker_tiff", is_flag=True, default=False)
def tiff2hdf5(ctx, channel, fix_bruker_tiff):
    """Convert an OME TIFF stack to a single HDF5 file.

    Parameters:
    ctx: click's context object
        The underlying object should contain "path" an "acquisition" global flags
    channel: int
        The channel of the TIFF stack to process
    fix_bruker_tiff: boolean
        Whether to first fix the broken OME XML metadata store in the tiff stack's master file.
    """
    path = ctx.obj["path"]
    acquisition = ctx.obj["acquisition"]

    tiff_path = path / "processed" / acquisition / "tiff"
    orig_h5_path = path / "processed" / acquisition / "orig.h5"

    # To load OME tiff stacks, it suffices to load just the first file, which contains
    # metadata to allow the tifffile to load the entire stack.
    tiff_glob = TIFF_GLOB_INIT.format(channel=channel)
    tiff_init = list(tiff_path.glob(tiff_glob))
    if len(tiff_init) != 1:
        raise Tiff2Hdf5Error(
            "Expected one initial tifffile, found: %s.  Pattern: %s" % (tiff_init, tiff_path / tiff_glob)
        )
    tiff_init = tiff_init[0]

    if fix_bruker_tiff:
        tiff_init_fixed = tiff_init.with_suffix(".fixed" + tiff_init.suffix)
        if tiff_init_fixed.exists():
            logger.warning("Deleting previously corrected Burker tiff: %s", str(tiff_init))
            tiff_init_fixed.unlink()
        shutil.copy(tiff_init, tiff_init_fixed)
        correct_omexml.correct_tiff(tiff_init_fixed)
        tiff_init = tiff_init_fixed

    logger.info("Reading TIFF metadata")
    zarr_store = tifffile.imread(tiff_init, aszarr=True)
    data = zarr.open(zarr_store, mode="r")
    logger.info("Found TIFF data with shape %s and type %s", data.shape, data.dtype)

    # TODO: This is a guess on what the axes will be. Find out if there is metadata with
    # axes naming.
    if data.ndim == 4:  # (time, z, y, x)
        logging.info("Assuming axes are time, z, y, x")
        chunks = ("auto", -1, -1, -1)
    elif data.ndim == 3:  # (time, y, x)
        logging.info("Assuming axes are time, y, x")
        chunks = ("auto", -1, -1)
    else:
        chunks = -1

    data_dask = da.from_array(data, chunks=chunks)

    if orig_h5_path.exists():
        logging.warning("Removing existing hdf5 file: %s", orig_h5_path)
        orig_h5_path.unlink()
    logger.info("Writing data to hdf5: %s" % orig_h5_path)
    # Read/write using single-thread ("synchronous").  If using SSD, could use additional workers.
    # This isn't a piece that needs to be optimized yet, so keep it simple.
    with dask.config.set(scheduler="synchronous"):
        da.to_hdf5(orig_h5_path, "/data", data_dask, compression="lzf", shuffle=True)
    logger.info("Done writing hdf5")

    logger.info("Done")
