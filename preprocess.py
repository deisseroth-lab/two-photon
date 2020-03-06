import argparse
import logging
import os
import pathlib
import pprint
import shutil
import subprocess
from xml.etree import ElementTree

import h5py
import numpy as np
import pandas as pd
from skimage.io import imread
#from tifffile import imread

STIM_CHANNEL_NUM = 7

LOGGER = logging.getLogger(__file__)
logging.getLogger('tifffile').setLevel(logging.ERROR)


def rip(base, ripper):
    LOGGER.info('Ripping')
    fname = patlib.Path(str(base) + '_Filelist.txt')
    dirname = fname.parent
    # Normally, the fname is passed to -AddRawFile.  But there is a bug in the software, so
    # we have to pop up one level and use -AddRawFileWithSubFolders.
    subprocess.run([
        ripper, '-SetOutputDirectory', dirname, '-IncludeSubFolders', '-AddRawFileWithSubFolders', dirname, '-Convert'
    ],
                   check=True)


def process(basename_input, dirname_output, buffer, shift, channel, fast_disk):
    # Create and make sure output directories are writable.
    def out_dir(subdir):
        dirname = dirname_output / subdir
        os.makedirs(dirname, exist_ok=True)
        return dirname

    dirname_corrected = out_dir('output')
    dirname_intermediate = out_dir('intermediate')
    dirname_results = out_dir('results')

    basename_vr = pathlib.Path(str(basename_input) + '_Cycle00001_VoltageRecording_001')

    fname_xml = basename_input.with_suffix('.xml')
    fname_vr_xml = basename_vr.with_suffix('.xml')

    metadata = get_metadata(fname_xml, fname_vr_xml)
    size = metadata['size']
    channels = metadata['channels']
    fs_param = 1. / (metadata['period'] * size['z_planes'])

    try:
        stim_channel_name, stim_channel_enabled = channels[STIM_CHANNEL_NUM]
        LOGGER.info('Found stim channel "%s", enabled=%s', stim_channel_name, stim_channel_enabled)
    except KeyError:
        stim_channel_enabled = False
        LOGGER.info('No stim channel found')

    fname_orig = dirname_intermediate / 'orig.h5'
    data = read_raw_data(basename_input, size, channel, fname_orig)

    fname_corrected = dirname_corrected / 'corrected.h5'
    if stim_channel_enabled:
        fname_vr_csv = basename_vr.with_suffix('.csv')
        df_voltage = get_voltage_recordings(fname_vr_csv)
        fname_artefacts = dirname_intermediate / 'artefact.h5'
        df_artefacts = get_artefact_bounds(df_voltage, size, stim_channel_name, fname_artefacts)
        remove_artefacts(data, df_artefacts, shift, buffer, fname_corrected)
    else:
        shutil.move(fname_orig, fname_corrected)

    fname_ops = dirname_results / 'ops.npy'
    run_suite_2p(fname_corrected, size, fs_param, fast_disk, fname_ops)


def globas_sync(local_endpoint, local_dirname, remote_endpoint, remote_dirname):
    local = f'{local_endpoint:local_dirname}'
    remote = f'{remote_endpoint:remote_dirname}'
    cmd = ['globus', local, remote]
    subprocess.run(cmd, check=True)


def get_metadata(fname_xml, fname_vr_xml):
    LOGGER.info('Extracting metadata from xml files:\n%s\n%s', fname_xml, fname_vr_xml)

    mdata_root = ElementTree.parse(fname_xml).getroot()

    def state_value(key, type_fn=str):
        element = mdata_root.find(f'.//PVStateValue[@key="{key}"]')
        value = element.attrib['value']
        return type_fn(value)

    def indexed_value(key, index, type_fn=None):
        element = mdata_root.find(f'.//PVStateValue[@key="{key}"]/IndexedValue[@index="{index}"]')
        value = element.attrib['value']
        return type_fn(value)

    num_frames = len(mdata_root.findall('Sequence'))
    num_channels = len(mdata_root.find('Sequence/Frame').findall('File'))
    num_z_planes = len(mdata_root.find('Sequence').findall('Frame'))
    num_y_px = state_value('linesPerFrame', int)
    num_x_px = state_value('pixelsPerLine', int)

    laser_power = indexed_value('laserPower', 0, float)
    laser_wavelength = indexed_value('laserWavelength', 0, int)

    frame_period = state_value('framePeriod', float)
    optical_zoom = state_value('opticalZoom', float)

    voltage_root = ElementTree.parse(fname_vr_xml).getroot()

    channels = {}
    for signal in voltage_root.findall('Experiment/SignalList/VRecSignal'):
        channel_num = int(signal.find('Channel').text)
        channel_name = signal.find('Name').text
        enabled = signal.find('Enabled').text == 'true'
        channels[channel_num] = (channel_name, enabled)

    metadata = {
        'size': {
            'frames': num_frames,
            'channels': num_channels,
            'z_planes': num_z_planes,
            'y_px': num_y_px,
            'x_px': num_x_px
        },
        'laser': {
            'power': laser_power,
            'wavelength': laser_wavelength
        },
        'period': frame_period,
        'optical_zoom': optical_zoom,
        'channels': channels,
    }
    LOGGER.info(pprint.pformat(metadata))
    return metadata


def get_voltage_recordings(fname):
    df = pd.read_csv(fname, index_col='Time(ms)', skipinitialspace=True)
    LOGGER.info('Read voltage recordings from: %s, preview:\n%s', fname, df.head())
    return df


def get_artefact_bounds(df, size, stim_channel_name, fname):
    LOGGER.info('Calculating artefact regions')

    shape = (size['frames'], size['z_planes'])
    y_px = size['y_px']

    frame = df['frame starts']
    frame_start = frame[frame.diff() > 2.5].index

    stim = df[stim_channel_name]
    stim_start = stim[stim.diff() > 2.5].index
    stim_stop = stim[stim.diff() < -2.5].index

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
    df.to_hdf(fname, 'data')
    LOGGER.info('Stored calculated artefact positions in %s, preview:\n%s', fname, df.head())
    return df


def get_loc(times, frame_start, y_px, shape):
    interp = np.interp(times, frame_start, range(len(frame_start)))
    indices = interp.astype(np.int)
    y_offset = y_px * (interp - indices)
    return np.transpose(np.unravel_index(indices, shape)), y_offset


def read_raw_data(base, size, channel, fname):
    LOGGER.info('Reading raw data')

    def read(frame, z):
        # TODO: Frame 0 has tons of OME-TIFF metadata which seems to make things slow.  Figure out how to make it faster and re-enable.
        if frame == 0:
            frame = 1
        fname = str(base) + f'_Cycle{frame+1:05d}_Ch{channel}_{z+1:06d}.ome.tif'
        return imread(fname)

    shape = (size['frames'], size['z_planes'], size['y_px'], size['x_px'])
    dtype = read(0, 0).dtype

    data = np.zeros(shape, dtype)
    for frame in range(shape[0]):
        if not frame % 500:
            LOGGER.info('Working on frame %05d of %05d', frame, shape[0])
        for z_plane in range(shape[1]):
            data[frame, z_plane] = read(frame, z_plane)

    with h5py.File(fname, 'w') as hfile:
        hfile.create_dataset('data', data=data)
    LOGGER.info('Stored data with shape %s in %s', shape, fname)
    return data


def remove_artefacts(data, df, shift, buffer, fname):
    LOGGER.info('Removing stim artefacts from data')
    for row in df.itertuples():
        y_slice = slice(int(row.y_min) + shift, int(row.y_max) + shift + buffer + 1)
        before = data[row.frame - 1, row.z_plane, y_slice]
        after = data[row.frame + 1, row.z_plane, y_slice]
        data[row.frame, row.z_plane, y_slice] = (before + after) / 2

    with h5py.File(fname, 'w') as hfile:
        hfile.create_dataset('data', data=data)
    LOGGER.info('Stored artefact-removed data in %s', fname)


def run_suite_2p(fname_h5, size, fs_param, fast_disk, fname):
    LOGGER.info('Running suite2p')
    from suite2p import run_s2p
    default_ops = run_s2p.default_ops()
    db = {
        'h5py': str(fname_h5),
        'nplanes': size['z_planes'],
        'fast_disk': str(fast_disk),
        'data_path': [],
        'fs': fs_param,
        'sav_mat': True,
        'bidi_corrected': True,
        'spatial_hp': 50,
        'sparse_mode': False,
        'threshold_scaling': 3,
    }
    ops = run_s2p.run_s2p(ops=default_ops, db=db)
    np.save(fname, ops)
    LOGGER.info('Save final suite2p ops in %s', fname)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Preprocess 2-photon raw data with suite2p')

    control_group = parser.add_argument_group('Preprocessing control flags')
    control_group.add_argument('--rip',
                               action='store_true',
                               help='Run the Prairie View Ripper to convert RAW data to TIFF')
    control_group.add_argument('--process',
                               action='store_true',
                               help='Convert the TIFF to HDF5, remove artefacts, and run Suite2p')
    control_group.add_argument('--backup', action='store_true', help='Backup all input and output data via Globus')

    group = parser.add_argument_group('Preprocessing arguments')
    group.add_argument('--data_dir', type=pathlib.Path, help='Top Level directory of data collection')
    group.add_argument('--fast_disk',
                       type=pathlib.Path,
                       help='Scratch directory for fast I/O storage')
    group.add_argument('--session_name',
                       type=str,
                       help='Top-level name of the session, usually containing date and mouse ID, e.g. YYYYMMDDmmm')
    group.add_argument('--recording_name', type=str, help='Unique name of the recording')
    group.add_argument('--recording_prefix',
                       type=str,
                       help='Prefix of the recording filenames, IF different thant --recording_name.')
    group.add_argument('--channel', type=int, default=3, help='Microscrope channel containing the two-photon data')

    group.add_argument('--ripper',
                       type=str,
                       default=R'C:\Program Files\Prairie\Prairie View\Utilities\Image-Block Ripping Utility.exe',
                       help='If specified, first rip the data from raw data to hdf5.')

    group.add_argument('--artefact_buffer', type=int, default=5, help='Rows to exclude surrounding calculated artefact')
    group.add_argument('--artefact_shift', type=int, default=3, help='Rows to shift artefact position from nominal.')

    group.add_argument('--local_endpoint', type=str, default='ce898518-5c30-11ea-960a-0afc9e7dd773', help=('Local globus endpoint id (default is B115_imaging).'))
    group.add_argument('--remote_endpoint', type=str, default='96a13ae8-1fb5-11e7-bc36-22000b9a448b', help=('Remote globus endpoint id (default is SRCC Oak).'))
    group.add_argument('--remote_dirname', type=str, default='', help=('Remote dirname to sync results to.'))

    args = parser.parse_args()

    # If recording_prefix not specified, use recording_name.
    recording_prefix = args.recording_prefix or args.recording_name

    dirname_root = args.data_dir / args.session_name
    dirname_input = dirname_root / args.recording_name
    basename_input = dirname_input / recording_prefix
    dirname_output = dirname_input.with_suffix('.preprocess')

    os.makedirs(dirname_output, exist_ok=True)  # Make directory for logging

    # Set up logging to write all INFO messages to both a file and to the stdout stream.
    LOGGER.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(name)s:%(lineno)s %(levelname)3s %(message)s')

    logger_fh = logging.FileHandler(dirname_output / 'preprocess.log')
    logger_fh.setFormatter(formatter)
    LOGGER.addHandler(logger_fh)

    logger_sh = logging.StreamHandler()
    logger_sh.setFormatter(formatter)
    LOGGER.addHandler(logger_sh)

    if args.ripper:
        rip(basename_input, args.ripper)

    if args.process:
        process(basename_input, dirname_output, args.artefact_buffer, args.artefact_shift, args.channel, args.fast_disk)

    if args.remote_dirname:
        globas_sync(args.local_endpoint, dirname_root, args.remote_endpoint, args.remote_dirname)
