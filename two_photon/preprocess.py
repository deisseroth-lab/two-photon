import logging

import click
import dask
import dask.array as da
import h5py
import numpy as np
import pandas as pd

from two_photon import artefact_detect, interpolate

logger = logging.getLogger(__name__)


# TODO: Convert shifts/buffers to pixels.
@click.command()
@click.pass_obj
@click.option("--stim_channel", type=str, help="Channel of stim signal")
@click.option(
    "--shift_ms",
    type=int,
    help="Time (milliseconds) used offset to stim windows, to adjust for unknown jitter in timing.",
)
@click.option(
    "--buffer_ms",
    type=int,
    help="Time (milliseconds) used to lengthen stim windows, to adjust for unknown jitter in timing.",
)
@click.option(
    "--settle_ms",
    type=int,
    help="Time (milleseconds) during a frame time period during which acquisition does not happen.",
)
def preprocess(layout, stim_channel, shift_ms, buffer_ms, settle_ms):
    """Removes artefacts from raw data.

    Parameters
    ----------
    layout: Layout object
        Object used to determine path naming
    shift_ms: float
        Time (milliseconds) used offset to stim windows, to adjust for unknown jitter in timing.
    buffer_ms: float
        Time (milliseconds) used to lengthen stim windows, to adjust for unknown jitter in timing.
    settle_ms: float
        Time (milleseconds) during a frame time period during which acquisition does not happen.
    """
    # Input files
    convert_path = layout.path("convert")
    orig_h5_path = convert_path / "orig.h5"
    voltage_h5_path = convert_path / "voltage.h5"

    # Output files
    preprocess_path = layout.path("preprocess")
    preprocess_path.mkdir(exist_ok=True)
    preprocess_h5_path = preprocess_path / "preprocess.h5"
    artefacts_path = preprocess_path / "artefacts.h5"

    if stim_channel is None:
        preprocess_h5_path.symlink_to(orig_h5_path)
        return

    h5file = h5py.File(orig_h5_path, "r")
    data = da.from_array(h5file["data"])

    df_voltage = pd.read_hdf(voltage_h5_path)

    frames = df_voltage["frame starts"].apply(lambda x: 1 if x > 1 else 0)
    frames = frames[frames.diff() > 0.5].index
    frame_start = frames[:-1]
    frame_stop = frames[1:] - settle_ms
    df_frames = pd.DataFrame({"start": frame_start, "stop": frame_stop})

    stims = df_voltage[stim_channel].apply(lambda x: 1 if x > 1 else 0)
    stim_start = stims[stims.diff() > 0.5].index + shift_ms
    stim_stop = stims[stims.diff() < -0.5].index + shift_ms + buffer_ms
    df_stims = pd.DataFrame({"start": stim_start, "stop": stim_stop})

    num_frames_data = data.shape[0] * data.shape[1]  # time-slices * z-planes
    num_frames_voltage = df_frames.shape[0]

    # Correct ragged edges in the data - if there are extra frames in the
    # data without corresponding frame_starts in the voltage data, or vice-versa.
    if num_frames_data < num_frames_voltage:
        df_frames = df_frames[:num_frames_data]
    elif num_frames_voltage < num_frames_data:
        num_time_slices = num_frames_voltage // data.shape[1]
        data = data[:num_time_slices]

    df_artefacts = artefact_detect.artefact_regions(df_frames, df_stims, data.shape)

    df_artefacts.to_hdf(artefacts_path, "artefacts")
    logger.info("Stored artefacts in %s\npreview:\n%s", artefacts_path, df_artefacts.head())

    # Rechunk data:
    # - interpolation of stim artefacts done along t-dimension (necessary)
    # - masking of stim artefacts done in single z-slice and across all x pixels in a row (efficiency)
    orig_chunks = data.chunks
    data = data.rechunk((-1, 1, "auto", -1))  # t, z, y, x

    # Mask stim regions with nan, and then interpolate values for those pixels.
    for t, z, y0, y1 in df_artefacts[["t", "z", "pixel_start", "pixel"]].values:
        data[t, z, y0:y1] = np.nan
    data = interpolate.interpolate_nan(data)

    # Rechunk to original chunking.
    data = data.rechunk(orig_chunks)

    if preprocess_h5_path.exists():
        logging.warning("Removing existing preprocessed hdf5 image file: %s", orig_h5_path)
        preprocess_h5_path.unlink()
    logger.info("Writing preprocessed image data to hdf5: %s" % preprocess_h5_path)
    # Read/write using single-thread ("synchronous").  If using SSD, could use additional workers.
    # This isn't a piece that needs to be optimized yet, so keep it simple.
    with dask.config.set(scheduler="synchronous"):
        da.to_hdf5(preprocess_h5_path, "data", data, compression="lzf", shuffle=True)
    logger.info("Done writing preprocessed image data hdf5")

    logger.info("Done")
