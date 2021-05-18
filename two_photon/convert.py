"""Command to convert Bruker OME TIFF stack to hdf5."""

import logging
import shutil

import click
import h5py
import pandas as pd
import tifffile

from two_photon import correct_omexml

logger = logging.getLogger(__name__)


TIFF_GLOB_INIT = "*_Cycle00001_Ch{channel}_000001.ome.tif"


class ConvertError(Exception):
    """Error during conversion of TIFF stack to HDF5."""


@click.command()
@click.pass_obj
@click.option(
    "--channel",
    type=int,
    required=True,
    help="Channel number of tiff stack to convert to hdf5",
)
@click.option(
    "--fix-tiff/--no-fix-tiff",
    default=True,
    help="Rewrite the master OME tiff to fix mis-specification by Bruker scopes",
    show_default=True,
)
def convert(layout, channel, fix_tiff):
    """Convert OME TIFF stack and voltage recording data to HDF5."""
    # Input filenames
    voltage_csv_path = layout.raw_voltage_path()
    tiff_path = layout.path("tiff")

    # Output filenames
    convert_path = layout.path("convert")
    convert_path.mkdir(parents=True, exist_ok=True)
    orig_h5_path = convert_path / "orig.h5"
    voltage_h5_path = convert_path / "voltage.h5"

    logger.info("Reading voltage recordings from: %s", voltage_csv_path)
    df_voltage = pd.read_csv(voltage_csv_path, index_col="Time(ms)", skipinitialspace=True)
    logger.info("Voltage recordings head:\n%s", df_voltage.head())

    logger.info("Writing volatage data to hdf5: %s" % voltage_h5_path)
    if voltage_h5_path.exists():
        logging.warning("Removing existing voltage hdf5 file: %s", voltage_h5_path)
        voltage_h5_path.unlink()
    df_voltage.to_hdf(voltage_h5_path, "voltage")
    logger.info("Done writing voltage data to hdf5")

    # To load OME tiff stacks, it suffices to load just the first file, which contains
    # metadata to allow `tifffile` to load the entire stack.
    tiff_glob = TIFF_GLOB_INIT.format(channel=channel)
    tiff_init = list(tiff_path.glob(tiff_glob))
    if len(tiff_init) != 1:
        raise ConvertError(
            "Expected one initial tifffile, found: %s.  Pattern: %s" % (tiff_init, tiff_path / tiff_glob)
        )
    tiff_init = tiff_init[0]

    if fix_tiff:
        tiff_init_fixed = tiff_init.with_suffix(".fixed" + tiff_init.suffix)
        if tiff_init_fixed.exists():
            logger.warning("Deleting previously corrected Burker tiff: %s", str(tiff_init))
            tiff_init_fixed.unlink()
        shutil.copy(tiff_init, tiff_init_fixed)
        correct_omexml.correct_tiff(tiff_init_fixed)
        tiff_init = tiff_init_fixed

    logger.info("Reading TIFF metadata")
    data = tifffile.imread(tiff_init)
    logger.info("Found TIFF data with shape %s and type %s", data.shape, data.dtype)

    if orig_h5_path.exists():
        logging.warning("Removing existing hdf5 image file: %s", orig_h5_path)
        orig_h5_path.unlink()
    logger.info("Writing image data to hdf5: %s" % orig_h5_path)

    with h5py.File(orig_h5_path, "w") as h5file:
        h5file.create_dataset("data", data=data)
    logger.info("Done writing image data hdf5")

    logger.info("Done")
