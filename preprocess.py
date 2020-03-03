import argparse
import logging
import os
import subprocess
from xml.etree import ElementTree

import h5py
import numpy as np
import pandas as pd
import skimage.io
from suite2p import run_s2p


def main(basename_input, dirname_output, buffer, shift, channel, ripper,
         fast_disk, local_endpoint, remote_endpoint, remote_dirname):

    dirname_corrected = os.path.join(dirname_output, 'output')
    dirname_results = os.path.join(dirname_output, 'intermediates')

    os.makedirs(dirname_corrected, exist_ok=True)
    os.makedirs(dirname_results, exist_ok=True)

    if ripper:
        rip(basename_input, ripper)

    metadata_dct = get_metadata(basename_input)
    size = metadata_dct['size']

    df_voltage = get_voltage_recordings(basename_input)
    df_artefacts = get_artefact_bounds(df_voltage, size)

    fname_artefact = os.path.join(dirname_results, 'artefact.h5')
    df_artefacts.to_hdf(fname_artefact, 'data')

    data = read_raw_data(basename_input, size, channel)
    fname_orig = os.path.join(dirname_results, 'orig.h5')
    with h5py.File(fname_orig, 'w') as f_orig:
        f_orig.create_dataset('data', data=data)

    remove_artefacts(data, df_artefacts, shift, buffer)

    fname_corrected = os.path.join(dirname_corrected, 'corrected.h5')
    with h5py.File(fname_corrected, 'w') as f_corr:
        f_corr.create_dataset('data', data=data)

    ops = run_suite_2p(fname_corrected, size, fast_disk)
    np.save(os.path.join(dirname_results, 'ops.npy'), ops)

    if remote_dirname:
        oak_sync(local_endpoint, dirname_output, remote_endpoint,
                 remote_dirname)


def oak_sync(local_endpoint, local_dirname, remote_endpoint, remote_dirname):
    local = f'{local_endpoint:local_dirname}'
    remote = f'{remote_endpoint:remote_dirname}'
    cmd = ['globus', local, remote]
    subprocess.run(cmd, check=True)


def rip(base, ripper):
    logging.info('Ripping')

    fname = base + '_Filelist.txt'
    dirname = os.path.dirname(fname)

    # Normally, the fname is passed to -AddRawFile.  But there is a bug in the software, so
    # we have to pop up one level and use -AddRawFileWithSubFolders.
    subprocess.run([
        ripper, '-SetOutputDirectory', dirname, '-AddRawFileWithSubFolders',
        dirname, '-Convert'
    ])


def get_metadata(base):
    logging.info('Extracting metadata')

    mdata_root = ElementTree.fromstring(open(base + '.xml').read())

    def state_value(key, type_fn=str):
        element = mdata_root.find(f'.//PVStateValue[@key="{key}"]')
        value = element.attrib['value']
        return type_fn(value)

    def indexed_value(key, index, type_fn=None):
        element = mdata_root.find(
            f'.//PVStateValue[@key="{key}"]/IndexedValue[@index="{index}"]')
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

    fname_voltage_xml = base + '_Cycle00001_VoltageRecording_001.xml'
    voltage_root = ElementTree.fromstring(open(fname_voltage_xml).read())

    channels = {}
    for signal in voltage_root.findall('Experiment/SignalList/VRecSignal'):
        channel = int(signal.find('Channel').text)
        name = signal.find('Name').text
        channels[name] = channel

    return {
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


def get_voltage_recordings(base):
    logging.info('Reading voltage recordings')

    fname_voltage_csv = base + '_Cycle00001_VoltageRecording_001.csv'
    return pd.read_csv(fname_voltage_csv,
                       index_col='Time(ms)',
                       skipinitialspace=True)


def get_artefact_bounds(df, size):
    logging.info('Calculating artefact regions')

    shape = (size['frames'], size['z_planes'])
    y_px = size['y_px']

    frame = df['frame starts']
    frame_start = frame[frame.diff() > 2.5].index

    stim = df['FieldStimulator']
    stim_start = stim[stim.diff() > 2.5].index
    stim_stop = stim[stim.diff() < -2.5].index

    ix_start, y_off_start = get_loc(stim_start, frame_start, y_px, shape)
    ix_stop, y_off_stop = get_loc(stim_stop, frame_start, y_px, shape)

    frame = []
    z_plane = []
    y_px_start = []
    y_px_stop = []
    for (ix_start_cyc,
         ix_start_z), (ix_stop_cyc,
                       ix_stop_z), y_min, y_max in zip(ix_start, ix_stop,
                                                       y_off_start,
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

    return pd.DataFrame({
        'frame': frame,
        'z_plane': z_plane,
        'y_min': y_px_start,
        'y_max': y_px_stop
    })


def get_loc(times, frame_start, y_px, shape):
    interp = np.interp(times, frame_start, range(len(frame_start)))
    indices = interp.astype(np.int)
    y_offset = y_px * (interp - indices)
    return np.transpose(np.unravel_index(indices, shape)), y_offset


def read_raw_data(base, size, channel):
    logging.info('Reading raw data')

    def read(frame, z):
        fname = base + f'_Cycle{frame+1:05d}_Ch{channel}_{z+1:06d}.ome.tif'
        return skimage.io.imread(fname)

    shape = (size['frames'], size['z_planes'], size['y_px'], size['x_px'])
    dtype = read(0, 0).dtype

    data = np.zeros(shape, dtype)
    for frame in range(size['frames']):
        for z_plane in range(size['z_planes']):
            data[frame, z_plane] = read(frame, z_plane)
    return data


def remove_artefacts(data, df, shift, buffer):
    logging.info('Removing stim artefacts from data')

    for row in df.itertuples():
        y_slice = slice(
            int(row.y_min) + shift,
            int(row.y_max) + shift + buffer + 1)
        before = data[row.frame - 1, row.z_plane, y_slice]
        after = data[row.frame + 1, row.z_plane, y_slice]
        data[row.frame, row.z_plane, y_slice] = (before + after) / 2


def run_suite_2p(fname_h5, size, fast_disk):
    logging.info('Running suite2p')

    default_ops = run_s2p.default_ops()
    db = {
        'h5py': fname_h5,
        'nplanes': size['z_planes'],
        'fast_disk': fast_disk,
        'data_path': [],
        'fs': 7.45,  # From frame rate and number of planes
        'sav_mat': True,
        'bidi_corrected': True,
        'spatial_hp': 50,
        'sparse_mode': False,
        'threshold_scaling': 3,
        # 'xrange': [1, 510],
        # 'yrange': [1, 510],
    }

    return run_s2p.run_s2p(ops=default_ops, db=db)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(
        description='Preprocess 2-photon raw data with suite2p')

    group = parser.add_argument_group('Two-photon preprocessing arguments')

    group.add_argument('--data_dir',
                       type=str,
                       required=True,
                       help='Top Level directory of data collection')

    group.add_argument('--fast_disk',
                       type=str,
                       required=True,
                       help='Top Level directory of data collection')

    group.add_argument(
        '--session_name',
        type=str,
        required=True,
        help=
        'Top-level name of the session, usually containing date and mouse ID: YYYYMMDDmmm'
    )

    group.add_argument('--recording_name',
                       type=str,
                       required=True,
                       help='Unique name of the recording')

    group.add_argument(
        '--recording_prefix',
        type=str,
        help=
        ('Prefix of the recording filenames, IF different thant --recording_name.  '
         '(If unspecified, will be --recording_name)'))

    group.add_argument(
        '--channel',
        type=int,
        default=3,
        help='Microscrope channel containing the two-photon data')

    group.add_argument(
        '--ripper',
        type=str,
        help=('If specified, first rip the data from raw data to hdf5.  '
              'If unset, assume ripping has already completed'))
    #R'C:\Program Files\Prairie\Prairie View\Utilities\Image-Block Ripping Utility.exe'

    group.add_argument(
        '--artefact_buffer',
        type=int,
        default=5,
        help=
        'Number of rows to exclude surrounding calculated artefact position')
    group.add_argument(
        '--artefact_shift',
        type=int,
        default=3,
        help=
        'Number of rows to shift artefact position from calculated position')
    group.add_argument('--local_endpoint',
                       type=str,
                       default='',
                       help=('Local globus endpoint id.'))
    group.add_argument('--remote_endpoint',
                       type=str,
                       default='',
                       help=('Remote globus endpoint id.'))
    group.add_argument('--remote_dirname',
                       type=str,
                       default='',
                       help=('Remote dirname to sync results to.'))

    args = parser.parse_args()

    # If recording_prefix not specified, use recording_name.
    recording_prefix = args.recording_prefix or args.recording_name

    basename_input = os.path.join(args.data_dir, args.session_name,
                                  args.recording_name, recording_prefix)
    dirname_output = os.path.join(args.data_dir, args.session_name,
                                  args.recording_name + '.preprocess')

    main(basename_input, dirname_output, args.artefact_buffer,
         args.artefact_shift, args.channel, args.ripper, args.fast_disk,
         args.local_endpoint, args.remote_endpoint, args.remote_dirname)
