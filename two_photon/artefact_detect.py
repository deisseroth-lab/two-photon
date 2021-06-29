"""Library for determining artefact locations in a 2p dataset."""

import numpy as np
import pandas as pd


def artefact_regions(df_frames, df_stims):
    """Calculate which regions of which frames have stim artefacts.

    Parameters
    ----------
    df_frames: pd.DataFrame with columns "start", "stop"
        List of start/stop times for each acquisition frame.  The length must
        be equal to shape[0] * shape[1].  Frames cannot overlap.
    df_stims: pd.DataFrame with columns "start", "stop"
        List of start/stop times for each stims.  Stims occurring outside of
        any frame are ignored.
    """
    df_frames = df_frames.sort_values("start")
    df_stims = df_stims.sort_values("start")

    # Checks that the dataframes are correctly sorted.
    def check_frame(df):
        assert (df["stop"] > df["start"]).all()
        assert (df["stop"][:-1].values <= df["start"][1:].values).all()

    check_frame(df_frames)
    check_frame(df_stims)

    # Removes stims which do not occur within the df_frames limits.
    df_stims = df_stims[df_stims["stop"] > df_frames["start"].iloc[0]]
    df_stims = df_stims[df_stims["start"] < df_frames["stop"].iloc[-1]]

    frame_all = np.empty(2 * df_frames.shape[0])
    frame_all[0::2] = df_frames["start"]
    frame_all[1::2] = df_frames["stop"]

    frame_start, frac_start = interpolate(df_stims["start"], df_frames["stop"], frame_all, fill=0, offset=1)
    frame_stop, frac_stop = interpolate(df_stims["stop"], df_frames["start"], frame_all, fill=1)

    df_artefacts = pd.DataFrame(
        {
            "frame_start": frame_start,
            "frac_start": frac_start,
            "frame_stop": frame_stop,
            "frac_stop": frac_stop,
        },
        index=df_stims.index,
    )
    return split_multi_frame_stim(df_artefacts)


def interpolate(times, frame_boundaries, all_boundaries, fill, offset=0):
    frame = np.interp(times, frame_boundaries, range(len(frame_boundaries)), left=-offset) + offset
    frame = frame.astype(np.int)

    all_idx = np.interp(times, all_boundaries, range(len(all_boundaries)))
    out_of_frame = (all_idx.astype(np.int) % 2) == 1

    img_frac = np.tile([0, 1], frame_boundaries.shape[0])
    frac = np.interp(times, all_boundaries, img_frac)
    frac[out_of_frame] = fill

    return frame, frac


def split_multi_frame_stim(df):
    columns = ["frame", "frac_start", "frac_stop"]
    index = []
    data = []
    for row in df.itertuples():
        rows = split_multi_frame_stim_row(row)
        data.extend(rows)
        index.extend([row.Index] * len(rows))
    return pd.DataFrame(data, index=index, columns=columns)


def split_multi_frame_stim_row(row):
    if row.frame_start == row.frame_stop:
        return [[row.frame_start, row.frac_start, row.frac_stop]]

    data = [[row.frame_start, row.frac_start, 1]]
    for frame in range(row.frame_start + 1, row.frame_stop):
        data.append([frame, 0, 1])
    data.append([row.frame_stop, 0, row.frac_stop])

    return data
