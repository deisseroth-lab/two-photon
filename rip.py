"""Library for running Bruker image ripping utility."""

import atexit
import glob
import logging
import os
import pathlib
import subprocess
import time

logger = logging.getLogger(__name__)


class RippingError(Exception):
    """Error raised if problems encountered during data conversion."""


def raw_to_tiff(base, ripper):
    """Convert Bruker RAW files to TIFF files using ripping utility specified with `ripper`."""
    fname = pathlib.Path(str(base) + '_Filelist.txt')
    if not fname.exists():
        raise RippingError('Input file list file is not present: %s' % fname)
    logger.info('Ripping using file list: %s', fname)
    dirname = fname.parent

    # Normally, the fname is passed to -AddRawFile.  But there is a bug in the software, so
    # we have to pop up one level and use -AddRawFileWithSubFolders.
    cmd = [
        ripper, '-IncludeSubFolders', '-AddRawFileWithSubFolders', dirname, '-SetOutputDirectory', dirname, '-Convert'
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
    remaining_sec = 3600
    loop_sec = 10
    last_output_tiffs = {}
    while remaining_sec >= 0:
        logging.info('Waiting for ripper to finish: %d seconds remaining', remaining_sec)
        remaining_sec -= loop_sec
        time.sleep(loop_sec)

        fname_exists = os.path.exists(fname)
        raw_exists = glob.glob(dirname / '*RAWDATA*')

        output_tiffs = set(glob.glob(base / '*.ome.tif'))
        tiffs_changed = (last_output_tiffs == output_tiffs)
        last_output_tiffs = output_tiffs

        if not fname_exists and not raw_exists and not tiffs_changed:
            logging.info('Detected ripping is complete')
            time.sleep(30)  # Wait an extra 30 seconds before terminating ripper, just to be safe.
            logging.info('Killing ripper')
            process.kill()
            break
