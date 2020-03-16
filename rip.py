"""Library for running Bruker image ripping utility."""

import atexit
import glob
import logging
import os
import pathlib
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
    fname = dirname / 'Cycle00001_Filelist.txt'
    if not fname.exists():
        raise RippingError('Input file list file is not present: %s' % fname)
    logger.info('Ripping using file list: %s', fname)

    # Normally, the fname is passed to -AddRawFile.  But there is a bug in the software, so
    # we have to pop up one level and use -AddRawFileWithSubFolders.
    cmd = [
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
    last_output_tiffs = {}
    while remaining_sec >= 0:
        logging.info('Waiting for ripper to finish: %d seconds remaining', remaining_sec)
        remaining_sec -= RIP_POLL_SECS
        time.sleep(RIP_POLL_SECS)

        fname_exists = os.path.exists(fname)
        raw_exists = glob.glob(str(dirname / '*RAWDATA*'))

        output_tiffs = set(glob.glob(str(dirname / '*.ome.tif')))
        tiffs_changed = (last_output_tiffs == output_tiffs)
        last_output_tiffs = output_tiffs

        if not fname_exists and not raw_exists and not tiffs_changed:
            logging.info('Detected ripping is complete')
            time.sleep(RIP_EXTRA_WAIT_SECS)  # Wait an extra 30 seconds before terminating ripper, just to be safe.
            logging.info('Killing ripper')
            process.kill()
            return

    raise RippingError('Killed ripper because it did not finish within %s seconds' % RIP_TOTAL_WAIT_SECS)