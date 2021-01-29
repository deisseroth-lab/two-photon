# Script for copying raw data for Bruker 2p data.
#
# python Documents\GitHub\two-photon\two-photon\backup_session.py --input_dir E:\AD --backup_dir E:\AD\output --recording 20200310M88:regL23-000

import argparse
import logging
import pathlib

import common_lib

logger = logging.getLogger(__file__)

class BackupSessionError(Exception):
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

    dirname_input = args.input_dir / session_name / recording_name
    dirname_backup = args.backup_dir / 'rawdata'/ session_name / recording_name
    common_lib.setup_logging(dirname_backup)

    filelists = dirname_input.glob('*Filelist.txt')
    if not filelists:
        raise BackupSessionError('Did not find any *Filelist.txt files')

    rawdata = dirname_input.glob('*RAWDATA*')
    if not rawdata:
        raise BackupSessionError('Did not find any *RAWDATA* files')


    common_lib.backup(dirname_input, dirname_backup)


def parse_args():
    """Gather command line arguments."""
    parser = argparse.ArgumentParser(description='Copy 2-photon session raw data')

    parser.add_argument('--input_dir',
                       type=pathlib.Path,
                       help='Top level directory of data collection (where microscope writes files)',
                       required=True)
    parser.add_argument('--backup_dir',
                        type=pathlib.Path,
                        help='Remote dirname to sync results to.',
                        required=True)
    parser.add_argument('--recording',
                        type=str,
                        help=('Name of a recording, given as a slash separated id of SESSION/RECORDING/OPTIONAL_PREFIX '
                              'e.g. 20200202M79/stimL23-000 or 20200124M74/stimL23-000/stim3dL23withBeam-001'))

    return parser.parse_args()




if __name__ == '__main__':
    main()
