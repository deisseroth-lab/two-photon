import logging

import click
import numpy as np
import pandas as pd


logger = logging.getLogger(__name__)


@click.command()
@click.pass_context
@click.option("--stim_channel", type=str, help="Channel of stim signal")
@click.option("--shift", type=int, help="")
@click.option("--buffer", type=int, help="")
@click.option("--settle", type=int, help="")
def remove_stim_artefact(ctx, stim_channel, shift, buffer, settle):
    path = ctx.obj["path"]
    acquisition = ctx.obj["acquisition"]
    orig_h5_path = path / "processed" / acquisition / "orig.h5"
    corrected_h5_dir = path / "processed" / acquisition / "remove_stim_artefact"

    corrected_h5_dir.mkdir(exist_ok=True)
    corrected_h5_data = corrected_h5_dir / "corrected.h5"
    if stim_channel is None:
        corrected_h5_data.symlink_to(orig_h5_path)
        return

    fname_voltages = None
    fname_artefacts = corrected_h5_dir / "artefacts.hdf5"

    df_voltage = pd.read_csv(fname_voltages, index_col="Time(ms)", skipinitialspace=True)
    logger.info("Read voltage recordings from: %s, preview:\n%s", fname_voltages, df_voltage.head())

    frames = df_voltage["frame starts"].apply(lambda x: 1 if x > 1 else 0)
    frames = frames[frames.diff() > 0.5].index
    frame_start = frames[:-1]
    frame_end = frames[1:] - settle

    stims = df_voltage[stim_channel].apply(lambda x: 1 if x > 1 else 0)
    stim_start = stims[stims.diff() > 0.5].index + shift
    stim_stop = stims[stims.diff() < -0.5].index + shift + buffer

    size_t = None
    size_z = None
    size_y = None

    df_artefacts = artefact_regions(frame_start, frame_end, stim_start, stim_stop, size_t, size_z, size_y)

    df_artefacts.to_hdf(fname_artefacts, "artefacts")
    logger.info("Stored artefacts in %s\npreview:\n%s", fname_artefacts, df_artefacts.head())


def artefact_regions(frame_start, frame_end, stim_start, stim_stop, size_t, size_z, size_y):
    nframes = frame_start.size

    frame_all = np.empty(2 * nframes, dtype=frame_start.dtype)
    frame_all[0::2] = frame_start
    frame_all[1::2] = frame_end

    pixels = np.tile([0, size_y], nframes)
    shape_tz = (size_t, size_z)

    start_frame, start_pixel = interpolate(stim_start, frame_end, frame_all, pixels, shape_tz, 0)
    stop_frame, stop_pixel = interpolate(stim_stop, frame_start, frame_all, pixels, shape_tz, size_y)


def interpolate(times, frame_boundaries, all_boundaries, pixels, shape_tz, fill):
    frame = np.interp(times, frame_boundaries, range(len(frame_boundaries)))
    frame = frame.astype(np.int)
    frame = np.transpose(np.unravel_index(frame, shape_tz))

    all_idx = np.interp(times, all_boundaries, range(len(all_boundaries)))
    out_of_frame = (all_idx.astype(np.int) % 2) == 0

    pixel = np.interp(times, all_boundaries, pixels)
    pixel[out_of_frame] = fill

    return frame, pixel
