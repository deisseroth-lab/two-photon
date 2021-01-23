# Script for running the initial processing and backups for Bruker 2p data.
#
# python Documents\GitHub\two-photon\two-photon\process.py --input_dir E:\AD --output_dir E:\AD\output --recording 20200310M88:regL23-000 --backup_dir=X:\users\drinnenb\Data2p\ --rip
# python Documents\GitHub\two-photon\two-photon\process.py --input_dir E:\AD --output_dir E:\AD\output --recording 20200310M88:regL23-000 --backup_dir=X:\users\drinnenb\Data2p\ --preprocess
# python Documents\GitHub\two-photon\two-photon\process.py --input_dir E:\AD --output_dir E:\AD\output --recording 20200310M88:regL23-000 --backup_dir=X:\users\drinnenb\Data2p\ --run_suite2p
# python Documents\GitHub\two-photon\two-photon\process.py --input_dir E:\AD --output_dir E:\AD\output --recording 20200310M88:regL23-000 --backup_dir=X:\users\drinnenb\Data2p\ --run_suite2p --prev_recording 20200310M88:regL23-000
# python Documents\GitHub\two-photon\two-photon\process.py --input_dir E:\AD --output_dir E:\AD\output --recording 20200310M88:regL23-000 --backup_dir=X:\users\drinnenb\Data2p\ --backup_output
# python Documents\GitHub\two-photon\two-photon\process.py --input_dir E:\AD --output_dir E:\AD\output --recording 20200310M88:regL23-000 --backup_dir=X:\users\drinnenb\Data2p\ --backup_data
# python Documents\GitHub\two-photon\two-photon\process.py --input_dir E:\AD --output_dir E:\AD\output --recording 20200310M88:regL23-000 --backup_dir=X:\users\drinnenb\Data2p\ --backup_hdf5
# python Documents\GitHub\two-photon\two-photon\process.py --input_dir E:\AD --output_dir E:\AD\output --recording 20200325M89:VRmm-000 --backup_dir=X:\users\drinnenb\Data2p\ --preprocess --run_suite2p --backup_output --backup_data --zip_data
# python Documents\GitHub\two-photon\two-photon\process.py --input_dir E:\AD --output_dir E:\AD\output --recording 20200325M89:playback-000 --backup_dir=X:\users\drinnenb\Data2p\ --preprocess --run_suite2p --prev_recording 202003M89:regL23-000
# python Documents\GitHub\two-photon\two-photon\process.py --input_dir E:\AD --output_dir E:\AD\output --recording 20200325M89:playback-000 --backup_dir=X:\users\drinnenb\Data2p\ --rip --preprocess --run_suite2p --prev_recording 20200325M89:VRmm-000 --backup_output --backup_data
# python Documents\GitHub\two-photon\two-photon\process.py --input_dir E:\AD --output_dir E:\AD\output --recording 20200325M89:playback-000 --backup_dir=X:\users\drinnenb\Data2p\ --rip --preprocess --settle_time --backup_output

import argparse
from datetime import datetime
import json
import logging
import os
import pathlib
import platform
import re
import subprocess
import glob

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

    def get_dirname_hdf5(sess_name, rec_name):
        return args.output_dir / sess_name / rec_name / 'hdf5'

    session_name, recording_name = recording_split(args.recording)

    # Locations for intput data to be read, output data to be written, and remote
    # data to by sync'd.
    dirname_input = args.input_dir / session_name / recording_name
    basename_input = dirname_input / recording_name  # The subdirectory and file prefix are `recording_name`

    dirname_hdf5 = get_dirname_hdf5(session_name, recording_name)

    dirname_output = args.output_dir / session_name / recording_name / 'output'
    os.makedirs(dirname_output, exist_ok=True)

    dirname_backup = args.backup_dir / session_name / recording_name

    setup_logging(dirname_output)

    fname_csv = pathlib.Path(str(basename_input) + '_Cycle00001_VoltageRecording_001').with_suffix('.csv')

    if args.rip:
        rip.raw_to_tiff(dirname_input, args.ripper)
    
    # Quick exit if our only operation is to rip
    if not (args.backup_data or args.preprocess or args.run_suite2p or args.backup_output or args.backup_hdf5):
        return

    # Quick exit if our only operation is to rip
    if not (args.backup_data or args.preprocess or args.run_suite2p or args.backup_output or args.backup_hdf5):
        return

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
        if args.zip_data:
            fname_zipped_data = archive_dir(dirname_input)
            backup(fname_zipped_data, dirname_backup)
            os.remove(fname_zipped_data)
        else:
            backup(dirname_input, dirname_backup / 'data')

    if args.preprocess or args.run_suite2p:
        fname_uncorrected_hdf5 = dirname_hdf5 / 'uncorrected' / 'uncorrected.h5'
        # This needs to be kept in sync with prev_data format below.
        # NOTE: The hdf5 file needs to be in its own directory with no other hdf5 files.  This is because
        # Suite2p uses whole directories, not filenames, when searching for data.
        fname_hdf5 = dirname_hdf5 / 'data' / 'data.h5'
        if args.preprocess:
            preprocess(basename_input, dirname_output, fname_csv, fname_uncorrected_hdf5, fname_hdf5, mdata,
                       args.artefact_buffer, args.artefact_shift, args.channel, stim_channel_name, args.settle_time)
        if args.run_suite2p:
            data_files = []
            for prev_recording in args.prev_recording:
                sn, rn = recording_split(prev_recording)
                # This needs to be kept in sync with fname_data format above.
                prev_data = get_dirname_hdf5(sn, rn) / 'data' / 'data.h5'
                data_files.append(prev_data)
            data_files.append(fname_hdf5)
            run_suite2p(data_files, dirname_output, mdata)

    if args.backup_output:
        backup(dirname_output, dirname_backup / 'output')
        # This csv file is part of the original data and backed up with --backup_data.
        # It is also backed up here so that it can be immediately available with the rest of
        # the output data, even if --backup_data is not used.
        backup(fname_csv, dirname_backup / 'output')
        if stim_channel_name:
            slm_date = datetime.strptime(session_name[:8], '%Y%m%d').strftime('%d-%b-%Y')
            slm_mouse = session_name[8:]

            slm_root = args.slm_setup_dir / slm_date
            slm_targets = slm_root / slm_mouse
            slm_trial_order_pattern = '*_' + slm_mouse + '_' + recording_name

            backup(slm_targets, dirname_backup / 'targets')
            trial_order_folder = glob.glob(os.path.join(slm_root,slm_trial_order_pattern))
            trial_order_path = pathlib.WindowsPath(trial_order_folder[0])
            backup(trial_order_path,dirname_backup / 'trial_order')
            # backup_pattern(slm_root, slm_trial_order_pattern, dirname_backup / 'trial_order')

    if args.backup_hdf5:
        backup(dirname_hdf5, dirname_backup / 'hdf5')


def preprocess(basename_input, dirname_output, fname_csv, fname_uncorrected, fname_data, mdata, buffer, shift, channel,
               stim_channel_name, settle_time):
    """Main method for running processing of TIFF files into HDF5."""
    size = mdata['size']

    df_voltage = pd.read_csv(fname_csv, index_col='Time(ms)', skipinitialspace=True)
    logger.info('Read voltage recordings from: %s, preview:\n%s', fname_csv, df_voltage.head())
    fname_frame_start = dirname_output / 'frame_start.h5'
    frame_start = artefacts.get_frame_start(df_voltage, fname_frame_start)

    if stim_channel_name:
        fname_artefacts = dirname_output / 'artefact.h5'
        df_artefacts = artefacts.get_bounds(df_voltage, frame_start, size, stim_channel_name, fname_artefacts, buffer,
                                            shift, settle_time)
    else:
        df_artefacts = None

    data = tiffdata.read(basename_input, size, mdata['layout'], channel)
    transform.convert(data, fname_data, df_artefacts, fname_uncorrected)


def backup(local_location, backup_location):
    """Sync local data to backup directory."""
    os.makedirs(backup_location.parent, exist_ok=True)
    system = platform.system()
    if system == 'Windows':
        if os.path.isdir(local_location):
            cmd = ['robocopy.exe', str(local_location), str(backup_location), '/S']
        else:
            # Single file copy done by giving source and dest directories, and specifying full filename.
            os.makedirs(backup_location, exist_ok=True)
            cmd = ['robocopy.exe', str(local_location.parent), str(backup_location), local_location.name]
        expected_returncode = 1  # robocopy.exe gives exit code 1 for a successful copy.
    elif system == 'Linux':
        if os.path.isdir(local_location):
            cmd = ['rsync', '-avh', str(local_location) + '/', str(backup_location)]
        else:
            os.makedirs(backup_location, exist_ok=True)
            cmd = ['rsync', '-avh', str(local_location), str(backup_location / local_location.name)]
        expected_returncode = 0  # Most programs give an exit code of 0 on success.
    else:
        raise BackupError('Do not recognize system: %s' % system)
    run_cmd(cmd, expected_returncode)


def archive_dir(dirname):
    """Use tar+gzip to zip directory contents into single, compressed file."""
    fname_archive = dirname.with_suffix('.tgz')
    system = platform.system()
    if system == 'Linux':
        # (c)reate archive as a (f)ile, use (z)ip compression
        cmd = ['tar', 'cfz', str(fname_archive), str(dirname)]
        run_cmd(cmd, expected_returncode=0)
    elif system == 'Windows':
        # Using 7z to mimic 'tar cfz' as per this post:
        # https://superuser.com/questions/244703/how-can-i-run-the-tar-czf-command-in-windows
        cmd = f'7z -ttar a dummy {dirname}\* -so | 7z -si -tgzip a {fname_archive}'
        run_cmd(cmd, expected_returncode=0, shell=True)
    else:
        raise BackupError('Do not recognize system: %s' % system)
    return fname_archive


def backup_pattern(local_dir, local_pattern, backup_dir):
    """Backup a filepattern to another directory.

    Need special treatment, as robocopy.exe on Windows has a different command line than typicaly linux utilities.
    """
    system = platform.system()
    if system == 'Linux':
        backup(local_dir / local_pattern, backup_dir)
    elif system == 'Windows':
        os.makedirs(backup_dir, exist_ok=True)
        cmd = ['robocopy.exe', str(local_dir), str(backup_dir), local_pattern, '/S']
        expected_returncode = 1  # robocopy.exe gives exit code 1 for a successful copy.
        run_cmd(cmd, expected_returncode)
    else:
        raise BackupError('Do not recognize system: %s' % system)


def run_cmd(cmd, expected_returncode, shell=False):
    """Run a shell command via a subprocess."""
    logger.info('Running command in subprocess:\n%s', cmd)
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=shell)  # pylint: disable=subprocess-run-check
    if result.returncode != expected_returncode:
        raise BackupError('Command failed!\n%s' % result.stdout.decode('utf-8'))
    logger.info('Output:\n%s', result.stdout.decode('utf-8'))


def run_suite2p(hdf5_list, dirname_output, mdata):
    z_planes = mdata['size']['z_planes']
    fs_param = 1. / (mdata['period'] * z_planes)

    # Load suite2p only right before use, as it has a long load time.
    from suite2p import run_s2p
    default_ops = run_s2p.default_ops()
    params = {
        'input_format': 'h5',
        'data_path': [str(f.parent) for f in hdf5_list],
        'save_path0': str(dirname_output),
        'nplanes': z_planes,
        'fs': fs_param,
        'save_mat': True,
        'bidi_corrected': True,
        'spatial_hp': 50,
        'sparse_mode': False,
        'threshold_scaling': 3,
        'diameter': 6,
    }
    logger.info('Running suite2p on files:\n%s\n%s', '\n'.join(str(f) for f in hdf5_list), params)
    with open(dirname_output / 'recording_order.json', 'w') as fout:
        json.dump([str(e) for e in hdf5_list], fout, indent=4)
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
                       default='Z:/mSLM/SetupFiles/Experiment',
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
    group.add_argument(
        '--settle_time',
        type=float,
        default=0,
        help='Amount of time at the beginning of an aquisition window to ignore while the hardware is settling.')
    group.add_argument('--artefact_buffer', type=float, default=0, help='Time to exclude following calculated artefact')
    group.add_argument('--artefact_shift', type=float, default=0, help='Time to shift artefact position from nominal.')

    group.add_argument('--backup_data', action='store_true', help='Backup all input data (post-ripping)')
    group.add_argument('--backup_hdf5',
                       action='store_true',
                       help='Backup hdf5 formatted data (with and without artefact removal)')
    group.add_argument('--backup_output', action='store_true', help='Backup all output processing')
    group.add_argument('--backup_dir', type=pathlib.Path, default='', help='Remote dirname to sync results to.')

    # Temporary argument for testing.  If it works, leave it on by default and remove flag.
    group.add_argument('--zip_data',
                       action='store_true',
                       help='Compress data directory (mostly TIFF files) into a single file for backup')

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
