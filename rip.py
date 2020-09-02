"""Library for running Bruker image ripping utility."""

import argparse
import atexit
import glob
import logging
import os
import pathlib
import platform
import subprocess
import time

logger = logging.getLogger(__name__)

# Ripping process does not end cleanly, so the filesystem is polled to detect the
# processing finishing.  The following variables relate to the timing of that polling
# process.
RIP_TOTAL_WAIT_SECS = 3600  # Total time to wait for ripping before killing it.
RIP_EXTRA_WAIT_SECS = 10  # Extra time to wait after ripping is detected to be done.
RIP_POLL_SECS = 10  # Time to wait between polling the filesystem.


class RippingError(Exception):
    """Error raised if problems encountered during data conversion."""


def raw_to_tiff(dirname, ripper):
    """Convert Bruker RAW files to TIFF files using ripping utility specified with `ripper`."""
    def get_filelists():
        return set(dirname.glob('*Filelist.txt'))

    def get_rawdata():
        return set(dirname.glob('*RAWDATA*'))

    def get_tiffs():
        return set(dirname.glob('*.ome.tif'))

    filelists = get_filelists()
    if not filelists:
        raise RippingError('No *Filelist.txt files present in %s' % dirname)

    rawdata = get_rawdata()
    if not rawdata:
        raise RippingError('No RAWDATA files present in %s' % dirname)

    tiffs = get_tiffs()
    if tiffs:
        raise RippingError('Cannot rip because tiffs already exist in %s (%d found)' % (dirname, len(tiffs)))

    logger.info('Ripping from:\n %s\n %s', '\n '.join([str(f) for f in filelists]),
                '\n '.join([str(f) for f in rawdata]))

    system = platform.system()
    if system == 'Linux':
        cmd = ['wine']
    else:
        cmd = []

    # Normally, the fname is passed to -AddRawFile.  But there is a bug in the software, so
    # we have to pop up one level and use -AddRawFileWithSubFolders.
    cmd += [
        ripper,
        '-IncludeSubFolders',
        '-AddRawFileWithSubFolders',
        str(dirname),
        '-SetOutputDirectory',
        str(dirname),
        '-Convert',
    ]

    # Run a subprocess to execute the ripping.  Note this is non-blocking because the
    # ripper never exists.  (If we blocked waiting for it, we'd wait forever.)  Instead,
    # we wait for the input files to be consumed and/or output files to be finished.
    process = subprocess.Popen(cmd)

    # Register a cleanup function that will kill the ripping subprocess.  This handles the cases
    # where someone hits Cntrl-C, or the main program exits for some other reason.  Without
    # this cleanup function, the subprocess will just continue running in the background.
    def cleanup():
        timeout_sec = 5
        p_sec = 0
        for _ in range(timeout_sec):
            if process.poll() == None:
                time.sleep(1)
                p_sec += 1
        if p_sec >= timeout_sec:
            process.kill()
        logger.info('cleaned up!')

    atexit.register(cleanup)

    # Wait for the file list and raw data to disappear
    remaining_sec = RIP_TOTAL_WAIT_SECS
    last_tiffs = {}
    while remaining_sec >= 0:
        logging.info('Waiting for ripper to finish: %d seconds remaining', remaining_sec)
        remaining_sec -= RIP_POLL_SECS
        time.sleep(RIP_POLL_SECS)

        filelists = get_filelists()
        rawdata = get_rawdata()

        tiffs = get_tiffs()
        tiffs_changed = (last_tiffs != tiffs)
        last_tiffs = tiffs

        logging.info('  Found filelist files: %s', filelists or None)
        logging.info('  Found rawdata files: %s', rawdata or None)
        logging.info('  Found this many tiff files: %s', len(tiffs))

        if not filelists and not rawdata and not tiffs_changed:
            logging.info('Detected ripping is complete')
            time.sleep(RIP_EXTRA_WAIT_SECS)  # Wait before terminating ripper, just to be safe.
            logging.info('Killing ripper')
            process.kill()
            logging.info('Ripper has been killed')
            return

    raise RippingError('Killed ripper because it did not finish within %s seconds' % RIP_TOTAL_WAIT_SECS)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s.%(msecs)03d %(module)s:%(lineno)s %(levelname)s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    parser = argparse.ArgumentParser(description='Preprocess 2-photon raw data into individual tiffs')
    parser.add_argument('--directory',
                        type=pathlib.Path,
                        required=True,
                        help='Directory containing RAWDATA and Filelist.txt files for ripping')
    parser.add_argument('--ripper',
                        default='/apps/Prairie View/Utilities/Image-Block Ripping Utility.exe',
                        help='Location of Bruker Image Block Ripping Utility.')
    args = parser.parse_args()
    raw_to_tiff(args.directory, args.ripper)
