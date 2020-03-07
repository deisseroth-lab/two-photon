"""Library to transform data from ripped TIFF files to HDF5."""

import logging
import os

import dask.array as da
from dask import diagnostics
import h5py

logger = logging.getLogger(__name__)

HDF5_KEY = '/data'


# In python 3.8:
# fname.unlink(missing_ok=True)
def unlink(fname):
    """Helper script to delete a file."""
    try:
        os.remove(fname)
    except OSError:
        pass


def convert(data, fname_data, df_artefacts=None, fname_uncorrected=None, artefact_shift=None, artefact_buffer=None):
    """Convert TIFF files from 2p dataset in HDF5.  Optionally create artefact-removed dataset."""
    # Important: code expects no chunking in z, y, z -- need to have -1 for these dimensions.
    data = data.rechunk((64, -1, -1, -1))

    with diagnostics.ProgressBar():
        if df_artefacts is None:
            logger.info('Writing data to %s', fname_data)
            unlink(fname_data)
            data.to_hdf5(fname_data, HDF5_KEY)

        else:
            logger.info('Writing uncorrected data to %s', fname_uncorrected)
            unlink(fname_uncorrected)
            data.to_hdf5(fname_uncorrected, HDF5_KEY)

            logger.info('Writing corrected data to %s', fname_uncorrected)
            with h5py.File(fname_uncorrected, 'r') as hfile:
                arr = da.from_array(hfile[HDF5_KEY])
                depth = (1, 0, 0, 0)
                data_corrected = arr.map_overlap(remove_artefacts,
                                                 depth=depth,
                                                 dtype=data.dtype,
                                                 df=df_artefacts,
                                                 shift=artefact_shift,
                                                 buffer=artefact_buffer,
                                                 mydepth=depth)
                unlink(fname_data)
                data_corrected.to_hdf5(fname_data, HDF5_KEY)


def remove_artefacts(chunk, df, shift, buffer, mydepth, block_info):
    """Remove artefacts from a chunk representing a set of frames."""
    chunk = chunk.copy()
    frame_min, frame_max = block_info[0]['array-location'][0]

    # The array-location is not the frame number -- it is offset by depth when using map_overlap.
    frame_chunk = block_info[0]['chunk-location'][0]
    frame_offset = mydepth[0] * (1 + 2 * frame_chunk)
    frame_min -= frame_offset
    frame_max -= frame_offset

    for index, frame in enumerate(range(frame_min, frame_max)):
        # Skip first/last frames, which are just overlaps for computation purposes
        if index in (0, chunk.shape[0] - 1):
            continue

        # Skip if the frame does not have an artefact.
        if frame not in df.index:
            continue

        for row in df.loc[frame:frame].itertuples():
            y_slice = slice(int(row.y_min) + shift, int(row.y_max) + shift + buffer + 1)
            before = chunk[index - 1, row.z_plane, y_slice]
            after = chunk[index + 1, row.z_plane, y_slice]
            chunk[index, row.z_plane, y_slice] = (before + after) / 2
    return chunk
