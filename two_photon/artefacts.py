"""Library for determining artefact locations in a 2p dataset."""

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__file__)


def get_frame_start(df_voltage, fname):
    frame_start_cat = df_voltage["frame starts"].apply(lambda x: 1 if x > 1 else 0)
    frame_start = frame_start_cat[frame_start_cat.diff() > 0.5].index
    frame_start.to_series().to_hdf(fname, "frame_start", mode="a")
    logger.info(
        "Stored calculated frame starts in %s, preview:\n%s", fname, frame_start[:5]
    )
    return frame_start


def get_bounds(
    df_voltage, frame_start, size, stim_channel_name, fname, buffer, shift, settle_time
):
    """From a dataframe of experiment timings, return a dataframe of artefact locations in the data."""
    logger.info("Calculating artefact regions")

    shape = (size["frames"], size["z_planes"])
    n_frames = shape[0] * shape[1]
    frame_start = frame_start[0:n_frames]
    y_px = size["y_px"]

    stim = df_voltage[stim_channel_name].apply(lambda x: 1 if x > 1 else 0)
    stim_start = stim[stim.diff() > 0.5].index + shift
    stim_stop = stim[stim.diff() < -0.5].index + shift + buffer

    frame, z_plane, y_px_start, y_px_stop = get_start_stop(
        stim_start, stim_stop, frame_start, y_px, shape, settle_time
    )

    df = pd.DataFrame(
        {"frame": frame, "z_plane": z_plane, "y_min": y_px_start, "y_max": y_px_stop}
    )
    df = df.set_index("frame")
    df.to_hdf(fname, "data", mode="w")

    stim_start.to_series().to_hdf(fname, "stim_start", mode="a")
    stim_stop.to_series().to_hdf(fname, "stim_stop", mode="a")

    logger.info(
        "Stored calculated artefact positions in %s, preview:\n%s", fname, df.head()
    )
    return df


def get_start_stop(stim_start, stim_stop, frame_start, y_px, shape, settle_time):
    ix_start, y_off_start = get_loc(stim_start, frame_start, y_px, shape, settle_time)
    y_off_start = np.floor(y_off_start).astype(np.int)
    ix_stop, y_off_stop = get_loc(stim_stop, frame_start, y_px, shape, settle_time)
    y_off_stop = np.ceil(y_off_stop).astype(np.int)

    frame = []
    z_plane = []
    y_px_start = []
    y_px_stop = []
    for (ix_start_cyc, ix_start_z), (ix_stop_cyc, ix_stop_z), y_min, y_max in zip(
        ix_start, ix_stop, y_off_start, y_off_stop
    ):
        if (ix_start_cyc == ix_stop_cyc) and (ix_start_z == ix_stop_z):
            # If a single-frame stim begins+ends during stim, skip it
            if y_min == y_max:
                continue
            frame.append(ix_start_cyc)
            z_plane.append(ix_start_z)
            y_px_start.append(y_min)
            y_px_stop.append(y_max)
        else:  # Stim spans >1 plane.
            frame.append(ix_start_cyc)
            z_plane.append(ix_start_z)
            y_px_start.append(y_min)
            y_px_stop.append(y_px)

            frame.append(ix_stop_cyc)
            z_plane.append(ix_stop_z)
            y_px_start.append(0)
            y_px_stop.append(y_max)
    return frame, z_plane, y_px_start, y_px_stop


def get_loc(times, frame_start, y_px, shape, settle_time):
    """Determine the location of event times within the data, given the frame start times."""
    v_idx = times < frame_start.max()
    interp = np.interp(times[v_idx], frame_start, range(len(frame_start)))
    indices = interp.astype(np.int)
    idx = np.transpose(np.unravel_index(indices, shape))

    frame_times = frame_start[1:] - frame_start[:-1]
    frame_times_stims = frame_times[indices]

    offset = (interp - indices) * frame_times_stims
    acquisition_times = frame_times_stims - settle_time
    y_offset = y_px * offset / acquisition_times

    # If offset is greater than y_px, it has occurred during stim.  Cap at y_px.
    y_offset = np.minimum(y_px, y_offset)

    return idx, y_offset
