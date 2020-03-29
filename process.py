# Script for running the initial processing and backups for Bruker 2p data.
#
# python Documents\GitHub\two-photon\process.py --input_dir E:\AD --output_dir E:\AD\output --recording 20200310M88:regL23-000 --backup_dir=X:\users\drinnenb\Data2p\ --rip
# python Documents\GitHub\two-photon\process.py --input_dir E:\AD --output_dir E:\AD\output --recording 20200310M88:regL23-000 --backup_dir=X:\users\drinnenb\Data2p\ --preprocess
# python Documents\GitHub\two-photon\process.py --input_dir E:\AD --output_dir E:\AD\output --recording 20200310M88:regL23-000 --backup_dir=X:\users\drinnenb\Data2p\ --run_suite2p
# python Documents\GitHub\two-photon\process.py --input_dir E:\AD --output_dir E:\AD\output --recording 20200310M88:regL23-000 --backup_dir=X:\users\drinnenb\Data2p\ --run_suite2p --prev_recording 20200310M88:regL23-000
# python Documents\GitHub\two-photon\process.py --input_dir E:\AD --output_dir E:\AD\output --recording 20200310M88:regL23-000 --backup_dir=X:\users\drinnenb\Data2p\ --backup_output
# python Documents\GitHub\two-photon\process.py --input_dir E:\AD --output_dir E:\AD\output --recording 20200310M88:regL23-000 --backup_dir=X:\users\drinnenb\Data2p\ --backup_data
# python Documents\GitHub\two-photon\process.py --input_dir E:\AD --output_dir E:\AD\output --recording 20200325M89:VRmm-000 --backup_dir=X:\users\drinnenb\Data2p\ --preprocess --run_suite2p --backup_output --backup_data
# python Documents\GitHub\two-photon\process.py --input_dir E:\AD --output_dir E:\AD\output --recording 20200325M89:playback-000 --backup_dir=X:\users\drinnenb\Data2p\ --preprocess --run_suite2p --prev_recording 202003M89:regL23-000
# python Documents\GitHub\two-photon\process.py --input_dir E:\AD --output_dir E:\AD\output --recording 20200325M89:playback-000 --backup_dir=X:\users\drinnenb\Data2p\ --rip --preprocess --run_suite2p --prev_recording 20200325M89:VRmm-000 --backup_output --backup_data

import argparse
from datetime import datetime
import logging
import os
import pathlib
import platform
import re
import subprocess

import numpy as np
import pandas as pd

import artefacts
import metadata
import rip
import tiffdata
import transform

STIM_CHANNEL_NUM = 7

logger = logging.getLogger(__file__)


class BackupError(Exception):
    pass


def main():
    """Deiver method to run processing from the command line."""
    args = parse_args()

    def recording_split(recording):
        pieces = recording.split(':')
        if len(pieces) != 2:
            raise ValueError('Recording should be SESSION:RECORDING.  Got %s' % recording)
        return pieces

    session_name, recording_name = recording_split(args.recording)

    # Locations for intput data to be read, output data to be written, and remote
    # data to by sync'd.
    dirname_input = args.input_dir / session_name
    basename_input = dirname_input / recording_name / recording_name  # The subdirectory and file prefix are `recording_name`

    dirname_output = args.output_dir / session_name / recording_name
    os.makedirs(dirname_output, exist_ok=True)

    dirname_backup = args.backup_dir / session_name / recording_name

    setup_logging(dirname_output)

    if args.rip:
        rip.raw_to_tiff(dirname_input / recording_name, args.ripper)

    mdata = metadata.read(basename_input, dirname_output)
    stim_channel = mdata['channels'][STIM_CHANNEL_NUM]

    try:
        stim_channel_name = stim_channel['name']
        stim_channel_enabled = stim_channel['enabled']
        logger.info('Found stim channel "%s", enabled=%s', stim_channel_name, stim_channel_enabled)
        if not stim_channel_enabled:
            stim_channel_name = None
    except KeyError:
        stim_channel_name = None
        logger.info('No stim channel found')

    if args.backup_data:
        backup(dirname_input, dirname_backup / 'data')

        if stim_channel_name:
            slm_date = datetime.strptime(session_name[:8], '%Y%m%d').strftime('%d-%b-%Y')
            slm_mouse = session_name[8:]

            slm_root = args.slm_setup_dir / slm_date
            slm_targets = slm_root / slm_mouse
            slm_trial_order = slm_root / ('*_' + slm_mouse + '_' + recording_name)

            backup(slm_targets, dirname_backup / 'targets')
            backup(slm_trial_order, dirname_backup / 'trial_order')

    if args.preprocess or args.run_suite2p:
        # This needs to be kept in sync with prev_data format below.
        fname_data = dirname_output / 'data' / 'data.h5'
        if args.preprocess:
            os.makedirs(fname_data.parent, exist_ok=True)
            preprocess(basename_input, dirname_output, fname_data, mdata, args.artefact_buffer, args.artefact_shift,
                       args.channel, stim_channel_name)
        if args.run_suite2p:
            data_files = []
            for prev_recording in args.prev_recording:
                sn, rn = recording_split(prev_recording)
                # This needs to be kept in sync with fname_data format above.
                prev_data = args.output_dir / sn / rn / 'data' / 'data.h5'
                data_files.append(prev_data)
            data_files.append(fname_data)

            run_suite2p(data_files, dirname_output, mdata)

    if args.backup_output:
        backup(dirname_output, dirname_backup / 'processed')


def preprocess(basename_input, dirname_output, fname_data, mdata, buffer, shift, channel, stim_channel_name):
    """Main method for running processing of TIFF files into HDF5."""
    size = mdata['size']

    fname_csv = pathlib.Path(str(basename_input) + '_Cycle00001_VoltageRecording_001').with_suffix('.csv')
    df_voltage = pd.read_csv(fname_csv, index_col='Time(ms)', skipinitialspace=True)
    logger.info('Read voltage recordings from: %s, preview:\n%s', fname_csv, df_voltage.head())
    fname_frame_start = dirname_output / 'frame_start.h5'
    frame_start = artefacts.get_frame_start(df_voltage, fname_frame_start)

    if stim_channel_name:
        fname_artefacts = dirname_output / 'artefact.h5'
        df_artefacts = artefacts.get_bounds(df_voltage, frame_start, size, stim_channel_name, fname_artefacts)
    else:
        df_artefacts = None

    data = tiffdata.read(basename_input, size, mdata['layout'], channel)
    fname_uncorrected = dirname_output / 'uncorrected.h5'

    transform.convert(data, fname_data, df_artefacts, fname_uncorrected, shift, buffer)


def backup(local_dirname, backup_dirname):
    """Sync local data to backup directory."""
    if os.path.exists(backup_dirname):
        raise BackupError('Cannot back up to already existing directory: %s' % backup_dirname)
    system = platform.system()
    if system == 'Windows':
        cmd = ['robocopy.exe', str(local_dirname), str(backup_dirname), '/S']  # '/S' means copy subfolders
        expected_returncode = 1
    elif system == 'Linux':
        os.makedirs(backup_dirname.parent, exist_ok=True)
        cmd = ['rsync', '-avh', str(local_dirname) + '/', str(backup_dirname)]
        expected_returncode = 0
    else:
        raise BackupError('Do not recognize system: %s' % system)

    logger.info('Running backup from %s to %s', local_dirname, backup_dirname)
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    logger.info('Output from backup:\n%s', result.stdout.decode('utf-8'))
    if result.returncode != expected_returncode:
        raise BackupError('Backup failed for %s -> %s' % (local_dirname, backup_dirname))


def run_suite2p(h5_list, dirname_output, mdata):
    z_planes = mdata['size']['z_planes']
    fs_param = 1. / (mdata['period'] * z_planes)

    # Load suite2p only right before use, as it has a long load time.
    from suite2p import run_s2p
    default_ops = run_s2p.default_ops()
    params = {
        'input_format': 'h5',
        'data_path': [str(f.parent) for f in h5_list],
        'save_path0': str(dirname_output),
        'nplanes': z_planes,
        'fs': fs_param,
        'save_mat': True,
        'bidi_corrected': True,
        'spatial_hp': 50,
        'sparse_mode': False,
        'threshold_scaling': 3,
    }
    logger.info('Running suite2p on files:\n%s\n%s', '\n'.join(str(f) for f in h5_list), params)
    run_s2p.run_s2p(ops=default_ops, db=params)


def parse_args():
    """Gather command line arguments."""
    parser = argparse.ArgumentParser(description='Preprocess 2-photon raw data with suite2p')

    group = parser.add_argument_group('Preprocessing arguments')

    group = parser.add_argument_group('Preprocessing control flags')

    group.add_argument('--rip', action='store_true', help='Run the Prairie View Ripper to convert RAW data to TIFF')
    group.add_argument('--ripper',
                       type=str,
                       default=R'C:\Program Files\Prairie\Prairie View\Utilities\Image-Block Ripping Utility.exe',
                       help='If specified, first rip the data from raw data to hdf5.')

    group.add_argument('--preprocess',
                       action='store_true',
                       help='Convert the TIFF to HDF5 and, if needed, remove artefacts')
    group.add_argument('--run_suite2p', action='store_true', help='Run Suite2p')

    group.add_argument('--input_dir',
                       type=pathlib.Path,
                       help='Top level directory of data collection (where microscope writes files)')
    group.add_argument('--slm_setup_dir',
                       type=pathlib.Path,
                       default='Z:/mSLM_B115/SetupFiles/Experiment',
                       help='Top level directory for SLM setup data')
    group.add_argument('--output_dir', type=pathlib.Path, help='Top level directory of data processing')

    group.add_argument('--recording',
                       type=str,
                       help=('Name of a recording, given as a slash separated id of SESSION/RECORDING/OPTIONAL_PREFIX '
                             'e.g. 20200202M79/stimL23-000 or 20200124M74/stimL23-000/stim3dL23withBeam-001'))
    group.add_argument('--prev_recording',
                       type=str,
                       nargs='+',
                       default=[],
                       help=('Name of one or more already preprocessed recordings to merge during suite2p.  '
                             'See --recording for format.'))

    group.add_argument('--channel', type=int, default=3, help='Microscrope channel containing the two-photon data')
    group.add_argument('--artefact_buffer',
                       type=int,
                       default=18,
                       help='Rows to exclude surrounding calculated artefact')
    group.add_argument('--artefact_shift', type=int, default=2, help='Rows to shift artefact position from nominal.')

    group.add_argument('--backup_data', action='store_true', help='Backup all input data (post-ripping) via Globus')
    group.add_argument('--backup_output', action='store_true', help='Backup all output processing via Globus')
    group.add_argument('--backup_dir', type=pathlib.Path, default='', help='Remote dirname to sync results to.')

    args = parser.parse_args()

    return args


def setup_logging(dirname_output):
    """Set up logging to write all INFO messages to both the stdout stram and a file."""
    fname_logs = dirname_output / 'preprocess.log'
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s.%(msecs)03d %(module)s:%(lineno)s %(levelname)s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        handlers=[logging.StreamHandler(), logging.FileHandler(fname_logs)])

    # Turn of verbose WARN messages from the tifffile library.
    logging.getLogger('tifffile').setLevel(logging.ERROR)


if __name__ == '__main__':
    main()
