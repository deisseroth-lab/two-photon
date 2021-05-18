import logging

import click
import h5py
import numpy as np
import pandas as pd

from two_photon import artefact_detect, interpolate, utils

logger = logging.getLogger(__name__)


@click.command()
@click.pass_obj
@click.option("--stim-channel-name", help="Name of the stim signal")
@click.option(
    "--shift-px",
    type=float,
    default=0,
    help="Number of pixel rows to offset stim windows, to adjust for unknown jitter in timing.",
)
@click.option(
    "--buffer-px",
    type=float,
    default=0,
    help="Number for pixel rows to lengthen stim windows, to adjust for unknown jitter in timing.",
)
@click.option(
    "--settle-ms",
    type=float,
    default=0,
    help="Time (milleseconds) during a frame time period during which acquisition does not happen.",
)
def preprocess(layout, stim_channel_name, shift_px, buffer_px, settle_ms):
    """Removes artefacts from raw data."""
    # Input files
    convert_path = layout.path("convert")
    orig_h5_path = convert_path / "orig.h5"
    voltage_h5_path = convert_path / "voltage.h5"

    # Output files
    preprocess_path = layout.path("preprocess")
    preprocess_h5_path = preprocess_path / "preprocess" / "preprocess.h5"
    artefacts_path = preprocess_path / "artefacts" / "artefacts.h5"

    preprocess_h5_path.parent.mkdir(parents=True, exist_ok=True)
    artefacts_path.parent.mkdir(parents=True, exist_ok=True)

    if stim_channel_name is None:
        preprocess_h5_path.symlink_to(orig_h5_path)
        return

    with h5py.File(orig_h5_path, "r") as h5file:
        data = h5file["data"][()]

    df_voltage = pd.read_hdf(voltage_h5_path)

    period = utils.frame_period(layout)
    y_px = data.shape[2]  # shape is t, z, y, x
    capture_time_ms = 1000 * period
    shift_ms = capture_time_ms * shift_px / y_px
    buffer_ms = capture_time_ms * buffer_px / y_px

    df_artefacts, data_processed = _preprocess(df_voltage, data, stim_channel_name, shift_ms, buffer_ms, settle_ms)

    df_artefacts.to_hdf(artefacts_path, "artefacts")
    logger.info("Stored artefacts in %s\npreview:\n%s", artefacts_path, df_artefacts.head())

    if preprocess_h5_path.exists():
        logging.warning("Removing existing preprocessed hdf5 image file: %s", preprocess_h5_path)
        preprocess_h5_path.unlink()
    logger.info("Writing preprocessed image data to hdf5: %s" % preprocess_h5_path)

    with h5py.File(preprocess_h5_path, "w") as h5file:
        h5file.create_dataset("data", data=data_processed)

    logger.info("Done writing preprocessed image data hdf5")

    logger.info("Done")


def _preprocess(df_voltage, data, stim_channel_name, shift_ms, buffer_ms, settle_ms):
    """Internal method of preprocess with no I/O for testing."""
    frames = df_voltage["frame starts"].apply(lambda x: 1 if x > 1 else 0)
    frames = frames[frames.diff() > 0.5].index
    frame_start = frames[:-1]
    frame_stop = frames[1:] - settle_ms
    df_frames = pd.DataFrame({"start": frame_start, "stop": frame_stop})

    stims = df_voltage[stim_channel_name].apply(lambda x: 1 if x > 1 else 0)
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

    # Mask stim regions with nan, and then interpolate values for those pixels.
    # Temporarily use float32 in order to use nan.
    logger.info("Identifying artefacts")
    data = data.astype(np.float32)
    for t, z, y0, y1 in df_artefacts[["t", "z", "pixel_start", "pixel_stop"]].values:
        data[t, z, y0:y1] = np.nan

    logger.info("Interpolating")
    data = interpolate.interpolate_nan(data)
    data[data < 0] = 0
    data[data > 65535] = 65535
    data = data.astype(np.uint16)
