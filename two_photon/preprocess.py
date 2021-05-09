import logging

import click
import dask.array as da
import h5py
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@click.command()
@click.pass_context
@click.option("--stim_channel", type=str, help="Channel of stim signal")
@click.option("--shift", type=int, help="")
@click.option("--buffer", type=int, help="")
@click.option("--settle", type=int, help="")
def preprocess(ctx, stim_channel, shift, buffer, settle):
    path = ctx.obj["path"]
    acquisition = ctx.obj["acquisition"]

    # Input files
    convert_path = path / "processed" / acquisition / "convert"
    orig_h5_path = convert_path / "orig.h5"
    voltage_h5_path = convert_path / "voltage.h5"

    # Output files
    preprocess_path = path / "processed" / acquisition
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
    frame_stop = frames[1:] - settle
    df_frames = pd.DataFrame({"start": frame_start, "stop": frame_stop})

    stims = df_voltage[stim_channel].apply(lambda x: 1 if x > 1 else 0)
    stim_start = stims[stims.diff() > 0.5].index + shift
    stim_stop = stims[stims.diff() < -0.5].index + shift + buffer
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

    df_artefacts = artefact_regions(df_frames, df_stims, data.shape)

    df_artefacts.to_hdf(artefacts_path, "artefacts")
    logger.info("Stored artefacts in %s\npreview:\n%s", artefacts_path, df_artefacts.head())


def artefact_regions(df_frames, df_stims, shape):
    """Calculate which regions of which frames have stim artefacts."""

    # Verifies that the number of frames in the shape and the dataframe agree.
    assert np.prod(shape[:2]) == df_frames.shape[0]

    # Checks that the dataframes are correctly sorted.
    def check_frame(df):
        assert (df["stop"] > df["start"]).all()
        assert (df["stop"][:-1].values <= df["start"][1:].values).all()

    check_frame(df_frames)
    check_frame(df_stims)

    # Removes stims which do no occur within some frame.
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
    if row.t_start == row.t_stop and row.z_start == row.t_stop:
        return [[row.t_start, row.z_start, row.pixel_start, row.pixel_stop]]

    idx_start, idx_stop = np.ravel_multi_index([(row.t_start, row.t_stop), (row.z_start, row.z_stop)], shape_tz)

    data = [[row.t_start, row.z_start, row.pixel_start, shape_y]]
    for idx in range(idx_start + 1, idx_stop):
        frame_t, frame_z = np.unravel_index(idx, shape_tz)
        data.append([frame_t, frame_z, 0, shape_y])
    data.append([row.t_stop, row.z_stop, 0, row.pixel_stop])

    return data
