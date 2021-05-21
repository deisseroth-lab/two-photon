"""Library for determining artefact locations in a 2p dataset."""

import numpy as np
import pandas as pd


def artefact_regions(df_frames, df_stims, shape):
    """Calculate which regions of which frames have stim artefacts.

    Parameters
    ----------
    df_frames: pd.DataFrame with columns "start", "stop"
        List of start/stop times for each acquisition frame.  The length must
        be equal to shape[0] * shape[1].  Frames cannot overlap.
    df_stims: pd.DataFrame with columns "start", "stop"
        List of start/stop times for each stims.  Stims occurring outside of
        any frame are ignored.
    shape: tuple of integers
        The dataset shape in (time, z, y, x) order.
    """

    # Verifies that the number of frames in the shape and the dataframe agree.
    assert np.prod(shape[:2]) == df_frames.shape[0]

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

    shape_tz = shape[:2]
    shape_y = shape[2]

    frame_all = np.empty(2 * df_frames.shape[0])
    frame_all[0::2] = df_frames["start"]
    frame_all[1::2] = df_frames["stop"]

    pixels = np.tile([0, shape[2]], df_frames.shape[0])

    t_start, z_start, pixel_start = interpolate(
        df_stims["start"], df_frames["stop"], frame_all, pixels, shape_tz, 0, offset=1
    )
    t_stop, z_stop, pixel_stop = interpolate(df_stims["stop"], df_frames["start"], frame_all, pixels, shape_tz, shape_y)

    df_artefacts = pd.DataFrame(
        {
            "t_start": t_start,
            "z_start": z_start,
            "pixel_start": pixel_start,
            "t_stop": t_stop,
            "z_stop": z_stop,
            "pixel_stop": pixel_stop,
        },
        index=df_stims.index,
    )
    return split_multi_frame_stim(df_artefacts, shape_tz=shape_tz, shape_y=shape_y)


def interpolate(times, frame_boundaries, all_boundaries, pixels, shape_tz, fill, offset=0):
    frame_interp = np.interp(times, frame_boundaries, range(len(frame_boundaries)), left=-offset) + offset
    frame_interp = frame_interp.astype(np.int)
    frame_t, frame_z = np.unravel_index(frame_interp, shape_tz)

    all_idx = np.interp(times, all_boundaries, range(len(all_boundaries)))
    out_of_frame = (all_idx.astype(np.int) % 2) == 1

    pixel = np.interp(times, all_boundaries, pixels)
    pixel[out_of_frame] = fill

    return frame_t, frame_z, pixel.astype(np.int)


def split_multi_frame_stim(df, shape_tz, shape_y):
    columns = ["t", "z", "pixel_start", "pixel_stop"]
    index = []
    data = []
    for row_index, row in df.iterrows():
        rows = split_multi_frame_stim_row(row, shape_tz, shape_y)
        data.extend(rows)
        index.extend([row_index] * len(rows))
    return pd.DataFrame(data, index=index, columns=columns)


def split_multi_frame_stim_row(row, shape_tz, shape_y):
    if row.t_start == row.t_stop and row.z_start == row.z_stop:
        return [[row.t_start, row.z_start, row.pixel_start, row.pixel_stop]]

    idx_start, idx_stop = np.ravel_multi_index([(row.t_start, row.t_stop), (row.z_start, row.z_stop)], shape_tz)

    data = [[row.t_start, row.z_start, row.pixel_start, shape_y]]
    for idx in range(idx_start + 1, idx_stop):
        frame_t, frame_z = np.unravel_index(idx, shape_tz)
        data.append([frame_t, frame_z, 0, shape_y])
    data.append([row.t_stop, row.z_stop, 0, row.pixel_stop])

    return data
