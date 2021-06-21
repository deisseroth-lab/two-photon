"""Library to transform data from ripped TIFF files to HDF5."""

import logging
import os

import dask.array as da
from dask import diagnostics
import h5py
import pdb

logger = logging.getLogger(__name__)

HDF5_KEY = '/data'  # Default key name in Suite2P.


# In python 3.8:
# fname.unlink(missing_ok=True)
def unlink(fname):
    """Helper script to delete a file."""
    try:
        os.remove(fname)
    except OSError:
        pass


def convert(data, fname_data, df_artefacts=None, fname_uncorrected=None):
    """Convert TIFF files from 2p dataset in HDF5.  Optionally create artefact-removed dataset."""
    # Important: code expects no chunking in z, y, z -- need to have -1 for these dimensions.
    data = data.rechunk((64, -1, -1, -1))  # 64 frames will be processed together for artefact removal.
    #with diagnostics.ProgressBar():
    if df_artefacts is None:
        logger.info('Writing data to %s', fname_data)
        unlink(fname_data)
        os.makedirs(fname_data.parent, exist_ok=True)
        data.to_hdf5(fname_data, HDF5_KEY)
    else:
        # This writes 2 hdf5 files, where the 2nd one depends on the same data being
        # written to the first.  Ideally, both would be written simultaneously, but
        # that cannot be done using dask.  Instead, the 1st file is written and then
        # read back to write the 2nd one.
        logger.info('Writing uncorrected data to %s', fname_uncorrected)
        unlink(fname_uncorrected)
        os.makedirs(fname_uncorrected.parent, exist_ok=True)
        #pdb.set_trace()
        data.to_hdf5(fname_uncorrected, HDF5_KEY) #set proper chunksize here?

        logger.info('Writing corrected data to %s', fname_data)
        with h5py.File(fname_uncorrected, 'r') as hfile:
            arr = da.from_array(hfile[HDF5_KEY],chunks = data.chunksize) #problem, if we don't define chunks, it seems to 
            
            # Depth of 1 in the first coordinate means to bring in the frames before and after
            # the chunk -- needed for doing diffs.
            depth = (1, 0, 0, 0)

            data_corrected = arr.map_overlap(remove_artefacts,
                                                depth=depth,
                                                dtype=data.dtype,
                                                df=df_artefacts,
                                                mydepth=depth)
            unlink(fname_data)
            os.makedirs(fname_data.parent, exist_ok=True)
            data_corrected.to_hdf5(fname_data, HDF5_KEY)


def remove_artefacts(chunk, df, mydepth, block_info):
    """Remove artefacts from a chunk representing a set of frames."""
    chunk = chunk.copy()
    frame_min, frame_max = block_info[0]['array-location'][0]

    # The array-location is not the frame number -- it is offset by depth when using map_overlap.
    frame_chunk = block_info[0]['chunk-location'][0]
    frame_offset = mydepth[0] * (1 + 2 * frame_chunk)
    frame_min -= frame_offset
    frame_max -= frame_offset

    for index, frame in enumerate(range(frame_min, frame_max)):
        # Skip first/last frames, which are just the edge frames pulled in to allow
        # computation using before/after.
        if index in (0, chunk.shape[0] - 1):
            continue

        # Skip if the frame does not have an artefact.
        if frame not in df.index:
            continue

        # Use `frame:frame` so the following slice always returns a frame.  Using just `frame`
        # would lead to a series being returned if there was only one present.
        for row in df.loc[frame:frame].itertuples():
            y_slice = slice(int(row.y_min), int(row.y_max) + 1)
            #pdb.set_trace()
            before = chunk[index - 1, row.z_plane, y_slice]
            after = chunk[index + 1, row.z_plane, y_slice]
            chunk[index, row.z_plane, y_slice] = (before + after) / 2
    return chunk
