"""Library for running Bruker image ripping utility."""

import logging
import pathlib
import subprocess

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
    subprocess.run(cmd, check=True)
