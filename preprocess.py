"""Script for running the initial processing and backups for Bruker 2p data."""

import argparse
import logging
import os
import pathlib
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


def main():
    """Deiver method to run processing from the command line."""
    args = parse_args()

    # Locations for intput data to be read, output data to be written, and remote
    # data to by sync'd.
    dirname_input = args.input_dir / args.session_name / args.recording_name
    basename_input = dirname_input / args.recording_prefix

    dirname_output = args.output_dir / args.session_name / args.recording_prefix
    os.makedirs(dirname_output, exist_ok=True)

    dirname_remote = args.remote_dirname / args.session_name / args.recording_prefix

    setup_logging(dirname_output)

    if args.rip:
        rip.raw_to_tiff(basename_input, args.ripper)

    if args.backup_data:
        globus_sync(args.local_endpoint, dirname_input, args.remote_endpoint, dirname_remote / 'data')

    if args.process:
        mdata = metadata.read(basename_input, dirname_output)
        fname_data = process(basename_input, dirname_output, mdata, args.artefact_buffer, args.artefact_shift,
                             args.channel)
        fast_disk = args.fast_disk / args.session_name / args.recording_name / args.recording_prefix
        run_suite_2p(fname_data, dirname_output, mdata, fast_disk)

    if args.backup_processing:
        globus_sync(args.local_endpoint, dirname_output, args.remote_endpoint, dirname_remote / 'processing')


def process(basename_input, dirname_output, mdata, buffer, shift, channel):
    """Main method for running processing of TIFF files into HDF5."""

    dirname_corrected = dirname_output / 'data'
    os.makedirs(dirname_corrected, exist_ok=True)

    size = mdata['size']
    stim_channel = mdata['channels'][STIM_CHANNEL_NUM]

    try:
        stim_channel_name = stim_channel['name']
        stim_channel_enabled = stim_channel['enabled']
        logger.info('Found stim channel "%s", enabled=%s', stim_channel_name, stim_channel_enabled)
    except KeyError:
        stim_channel_enabled = False
        logger.info('No stim channel found')

    if stim_channel_enabled:
        fname_csv = pathlib.Path(str(basename_input) + '_Cycle00001_VoltageRecording_001').with_suffix('.csv')
        df_voltage = pd.read_csv(fname_csv, index_col='Time(ms)', skipinitialspace=True)
        logger.info('Read voltage recordings from: %s, preview:\n%s', fname_csv, df_voltage.head())

        fname_artefacts = dirname_output / 'artefact.h5'
        df_artefacts = artefacts.get_bounds(df_voltage, size, stim_channel_name, fname_artefacts)
    else:
        df_artefacts = None

    data = tiffdata.read(basename_input, size, channel)
    fname_uncorrected = dirname_output / 'uncorrected.h5'
    fname_data = dirname_corrected / 'data.h5'
    transform.convert(data, fname_data, df_artefacts, fname_uncorrected, shift, buffer)
    return fname_data


def globus_sync(local_endpoint, local_dirname, remote_endpoint, remote_dirname):
    """Start a Globus sync operation."""
    local = f'{local_endpoint}:{local_dirname}'
    remote = f'{remote_endpoint}:{remote_dirname}'
    cmd = ['globus', local, remote]
    subprocess.run(cmd, check=True)


def run_suite_2p(fname_h5, dirname_output, mdata, fast_disk):
    logger.info('Running suite2p')

    z_planes = mdata['size']['z_planes']
    fs_param = 1. / (mdata['period'] * z_planes)

    # Load suite2p only right before use, as it has a long load time.
    from suite2p import run_s2p
    default_ops = run_s2p.default_ops()
    params = {
        'h5py': str(fname_h5),
        'nplanes': z_planes,
        'fast_disk': str(fast_disk),
        'data_path': [],
        'fs': fs_param,
        'sav_mat': True,
        'bidi_corrected': True,
        'spatial_hp': 50,
        'sparse_mode': False,
        'threshold_scaling': 3,
    }
    ops = run_s2p.run_s2p(ops=default_ops, db=params)

    fname_ops = dirname_output / 'ops.npy'
    np.save(fname_ops, ops)
    logger.info('Save final suite2p ops in %s', fname_ops)


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

    group.add_argument('--process',
                       action='store_true',
                       help='Convert the TIFF to HDF5, remove artefacts, and run Suite2p')
    group.add_argument('--input_dir',
                       type=pathlib.Path,
                       help='Top Level directory of data collection (where microscope writes files)')
    group.add_argument('--output_dir', type=pathlib.Path, help='Top Level directory of data processing')

    group.add_argument('--fast_disk', type=pathlib.Path, help='Scratch directory for fast I/O storage')
    group.add_argument('--session_name',
                       type=str,
                       help='Top-level name of the session, usually containing date and mouse ID, e.g. YYYYMMDDmmm')
    group.add_argument('--recording_name', type=str, help='Unique name of the recording')
    group.add_argument('--recording_prefix',
                       type=str,
                       help='Prefix of the recording filenames, IF different thant --recording_name.')
    group.add_argument('--channel', type=int, default=3, help='Microscrope channel containing the two-photon data')
    group.add_argument('--artefact_buffer',
                       type=int,
                       default=14,
                       help='Rows to exclude surrounding calculated artefact')
    group.add_argument('--artefact_shift', type=int, default=2, help='Rows to shift artefact position from nominal.')

    group.add_argument('--backup_data', action='store_true', help='Backup all input data (post-ripping) via Globus')
    group.add_argument('--backup_processing', action='store_true', help='Backup all output processing via Globus')
    group.add_argument('--local_endpoint',
                       type=str,
                       default='ce898518-5c30-11ea-960a-0afc9e7dd773',
                       help='Local globus endpoint id (default is B115_imaging).')
    group.add_argument('--remote_endpoint',
                       type=str,
                       default='96a13ae8-1fb5-11e7-bc36-22000b9a448b',
                       help='Remote globus endpoint id (default is SRCC Oak).')
    group.add_argument('--remote_dirname', type=pathlib.Path, default='', help='Remote dirname to sync results to.')

    args = parser.parse_args()

    # If recording_prefix not specified, use recording_name.
    args.recording_prefix = args.recording_prefix or args.recording_name

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
