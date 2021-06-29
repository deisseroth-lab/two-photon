import logging

import click
import h5py
import numpy as np
import pandas as pd

from two_photon import artefact_detect, interpolate, utils

logger = logging.getLogger(__name__)


@click.command()
@click.pass_obj
@click.option("--frame-channel-name", required=True, help="Name of the frame start signal")
@click.option("--stim-channel-name", required=True, help="Name of the stim signal")
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
@click.option("--piezo-period-frames", type=int, help="The period of piezo oscillation, in number of frames.")
@click.option("--piezo-skip-frames", type=int, help="The number of frames skipped in each piezo period.")
@click.option("--max-frames", type=int, help="Read in only max-frames image frames of original data.")
def preprocess(
    layout,
    frame_channel_name,
    stim_channel_name,
    shift_px,
    buffer_px,
    settle_ms,
    piezo_period_frames,
    piezo_skip_frames,
    max_frames,
):
    """Removes artefacts from raw data."""
    # Input files
    convert_path = layout.path("convert")
    orig_h5_path = convert_path / "orig.h5"
    voltage_h5_path = convert_path / "voltage.h5"

    # Output files.  The preprocess.h5 has to be alone in a separate directory, otherwise
    # when Suite2p runs it fail because it tries to read all al the h5 files in the directory,
    # which would included artefacts.h5.
    preprocess_path = layout.path("preprocess")
    preprocess_h5_path = preprocess_path / "preprocess" / "preprocess.h5"
    artefacts_path = preprocess_path / "artefacts" / "artefacts.h5"

    preprocess_h5_path.parent.mkdir(parents=True, exist_ok=True)
    artefacts_path.parent.mkdir(parents=True, exist_ok=True)

    if stim_channel_name is None:
        logger.info("No stim channel given for artefact removal - passing through uncorrected data.")
        preprocess_h5_path.symlink_to(orig_h5_path)
        return

    logger.info("Reading data from %s", orig_h5_path)
    with h5py.File(orig_h5_path, "r") as h5file:
        if max_frames is not None:
            data = h5file["data"][:max_frames]
        else:
            data = h5file["data"][()]

    logger.info("Reading voltage data from %s", voltage_h5_path)
    df_voltage = pd.read_hdf(voltage_h5_path)

    period_sec = utils.frame_period(layout)
    y_px = data.shape[2]  # dims are t, z, y, x
    px_to_ms = 1000 * period_sec / y_px
    shift_ms = shift_px * px_to_ms
    buffer_ms = buffer_px * px_to_ms

    logger.info("Identifying frame and stim windows")
    df_frames = extract_frames(df_voltage[frame_channel_name], settle_ms, piezo_period_frames, piezo_skip_frames)
    df_stims = extract_stims(df_voltage[stim_channel_name], shift_ms, buffer_ms)

    df_artefacts, data_processed = _preprocess(df_frames, df_stims, data)

    # Write output
    df_artefacts.to_hdf(artefacts_path, "artefacts")
    logger.info("Stored artefacts in %s\npreview:\n%s", artefacts_path, df_artefacts.head())

    if preprocess_h5_path.exists():
        logging.warning("Removing existing preprocessed hdf5 image file: %s", preprocess_h5_path)
        preprocess_h5_path.unlink()
    logger.info("Writing preprocessed image data to hdf5: %s" % preprocess_h5_path)

    with h5py.File(preprocess_h5_path, "w") as h5file:
        h5file.create_dataset("data", data=data_processed)

    logger.info("Done")


def _preprocess(df_frames, df_stims, data):
    """Internal method of preprocess with no I/O for testing."""

    num_frames_data = data.shape[0] * data.shape[1]  # time-slices * z-planes
    num_frames_voltage = df_frames.shape[0]

    # Correct ragged edges in the data - if there are extra frames in the
    # data without corresponding frame_starts in the voltage data, or vice-versa.
    if num_frames_data < num_frames_voltage:
        df_frames = df_frames[:num_frames_data]
    elif num_frames_voltage < num_frames_data:
        num_time_slices = num_frames_voltage // data.shape[1]
        data = data[:num_time_slices]

    logger.info("Identifying artefacts")
    df_artefacts = artefact_detect.artefact_regions(df_frames, df_stims, data.shape)

    # Mask stim regions with nan, and then interpolate values for those pixels.
    # Temporarily use float32 in order to use nan.
    logger.info("Marking artefacts")
    data = data.astype(np.float32)
    for t, z, y0, y1 in df_artefacts[["t", "z", "pixel_start", "pixel_stop"]].values:
        data[t, z, y0:y1] = np.nan

    logger.info("Interpolating")
    data = interpolate.interpolate_nan(data)
    data = np.clip(data, 0, 65535)
    data = data.astype(np.uint16)

    return df_artefacts, data


def extract_frames(frame_signal, settle_ms=0, piezo_period_frames=None, piezo_skip_frames=None):
    """Extract frame start/stop times from a voltage recording of the frame trigger signal."""
    frames = frame_signal.apply(lambda x: 1 if x > 1 else 0)
    frames = frames[frames.diff() > 0.5].index
    frame_start = frames[:-1]
    frame_stop = frames[1:] - settle_ms
    df_frames = pd.DataFrame({"start": frame_start, "stop": frame_stop})
    df_frames.index.name = "frame"
    if piezo_period_frames is not None:
        assert piezo_skip_frames, "piezo_skip_frames must be set if piezeo_period_frames is set"
        piezo_sel = (np.arange(len(df_frames.index)) % piezo_period_frames) >= piezo_skip_frames
        df_frames = df_frames[piezo_sel]
    return df_frames


def extract_stims(stim_signal, shift_ms=0, buffer_ms=0):
    """Extract stime start/stop times from a voltage recording of the stim trigger signal."""
    stims = stim_signal.apply(lambda x: 1 if x > 1 else 0)
    stim_start = stims[stims.diff() > 0.5].index + shift_ms
    stim_stop = stims[stims.diff() < -0.5].index + shift_ms + buffer_ms
    df_stims = pd.DataFrame({"start": stim_start, "stop": stim_stop})
    df_stims.index.name = "stim"
    return df_stims
