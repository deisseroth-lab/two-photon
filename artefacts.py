"""Library for determining artefact locations in a 2p dataset."""

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__file__)


def get_bounds(df, size, stim_channel_name, fname):
    """From a dataframe of experiment timings, return a dataframe of artefact locations in the data."""
    logger.info('Calculating artefact regions')

    shape = (size['frames'], size['z_planes'])
    y_px = size['y_px']

    frame_start_cat = df['frame starts'].apply(lambda x: 1 if x > 1 else 0)
    frame_start = frame_start_cat[frame_start_cat.diff() > 0.5].index

    stim = df[stim_channel_name].apply(lambda x: 1 if x > 1 else 0)
    stim_start = stim[stim.diff() > 0.5].index
    stim_stop = stim[stim.diff() < -0.5].index

    ix_start, y_off_start = get_loc(stim_start, frame_start, y_px, shape)
    ix_stop, y_off_stop = get_loc(stim_stop, frame_start, y_px, shape)

    frame = []
    z_plane = []
    y_px_start = []
    y_px_stop = []
    for (ix_start_cyc, ix_start_z), (ix_stop_cyc, ix_stop_z), y_min, y_max in zip(ix_start, ix_stop, y_off_start,
                                                                                  y_off_stop):
        if (ix_start_cyc == ix_stop_cyc) and (ix_start_z == ix_stop_z):
            frame.append(ix_start_cyc)
            z_plane.append(ix_start_z)
            y_px_start.append(y_min)
            y_px_stop.append(y_max)
        else:
            frame.append(ix_start_cyc)
            z_plane.append(ix_start_z)
            y_px_start.append(y_min)
            y_px_stop.append(y_px)

            frame.append(ix_stop_cyc)
            z_plane.append(ix_stop_z)
            y_px_start.append(0)
            y_px_stop.append(y_max)

    df = pd.DataFrame({'frame': frame, 'z_plane': z_plane, 'y_min': y_px_start, 'y_max': y_px_stop})
    df = df.set_index('frame')
    df.to_hdf(fname, 'data', mode='w')

    stim_start.to_series().to_hdf(fname, 'stim_start', mode='a')
    stim_stop.to_series().to_hdf(fname, 'stim_stop', mode='a')
    frame_start.to_series().to_hdf(fname, 'frame_start', mode='a')

    logger.info('Stored calculated artefact positions in %s, preview:\n%s', fname, df.head())
    return df


def get_loc(times, frame_start, y_px, shape):
    """Determine the location of event times within the data, given the frame start times."""
    interp = np.interp(times, frame_start, range(len(frame_start)))
    indices = interp.astype(np.int)
    y_offset = y_px * (interp - indices)
    return np.transpose(np.unravel_index(indices, shape)), y_offset
