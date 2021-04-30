"""Library for running Bruker image ripping utility."""

import argparse
import atexit
import logging
import pathlib
import platform
import re
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

# Ripping process does not end cleanly, so the filesystem is polled to detect the
# processing finishing.  The following variables relate to the timing of that polling
# process.
RIP_TOTAL_WAIT_SECS = 3600  # Total time to wait for ripping before killing it.
RIP_EXTRA_WAIT_SECS = 10  # Extra time to wait after ripping is detected to be done.
RIP_POLL_SECS = 10  # Time to wait between polling the filesystem.


class RippingError(Exception):
    """Error raised if problems encountered during data conversion."""


def determine_ripper(data_dir, ripper_dir):
    """Determine which version of the Prairie View ripper to use based on reading metadata."""
    env_files = list(data_dir.glob('*.env'))
    if len(env_files) != 1:
        raise RippingError('Only expected 1 env file in %s, but found: %s' % (data_dir, env_files))

    tree = ET.parse(str(data_dir / env_files[0]))
    root = tree.getroot()
    version = root.attrib['version']

    # Prairie View versions are given in the form A.B.C.D.
    match = re.match(r'^(?P<majmin>\d+\.\d+)\.\d+\.\d+$', version)
    if not match:
        raise RippingError('Could not parse version (expected A.B.C.D): %s' % version)
    version = match.group('majmin')
    ripper = ripper_dir / f'Prairie View {version}' / 'Utilities' / 'Image-Block Ripping Utility.exe'
    logger.info('Data created with Prairie version %s, using ripper: %s', version, ripper)
    return ripper


def raw_to_tiff(in_path, out_path, ripper):
    """Convert Bruker RAW files to TIFF files using ripping utility specified with `ripper`."""
    # Bruker software appends the in_path basename to the given output directory.
    out_path_final = out_path / in_path.name
        
    def get_filelists():
        filelists = list(sorted(in_path.glob('*Filelist.txt')))
        logging.info('  Found filelists: %s', [str(f) for f in filelists])
        return filelists
    
    def get_rawdata():
        rawdata = list(sorted(in_path.glob('*RAWDATA*')))
        logging.info('  Found # rawdata files: %s', len(rawdata))
        return rawdata

    def get_tiffs():
        tiffs = set(out_path_final.glob('*.ome.tif'))
        logging.info('  Found # tiff files: %s', len(tiffs))
        return tiffs
    
    def copy_back_files():
        """Copies back metadata files that Bruker copied to output directory.
        
        This helps preserve the input directory contents.
        """
        paths_to_copy = [path for path in out_path_final.iterdir()
                         if not path.name.endswith('ome.tif')]
        logging.info('Copying back files to input directory: %s', paths_to_copy)
        for path in paths_to_copy:
            if path.is_file():
                shutil.copy(path, in_path)
            else:
                shutil.copytree(path, in_path / path.name)
        

    filelists = get_filelists()
    if not filelists:
        raise RippingError('No *Filelist.txt files present in data directory')

    rawdata = get_rawdata()
    if not rawdata:
        raise RippingError('No RAWDATA files present in %s' % in_path)

    tiffs = get_tiffs()
    if tiffs:
        raise RippingError('Cannot rip because tiffs already exist in %s (%d found)' % (in_path, len(tiffs)))

    logger.info('Ripping using:\n %s\n %s', '\n '.join([str(f) for f in filelists]),
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
        '-KeepRaw',
        '-DoNotRipToInputDirectory',
        '-IncludeSubFolders',
        '-AddRawFileWithSubFolders',
        str(in_path),
        '-SetOutputDirectory',
        str(out_path),
        '-Convert',
    ]
    
    # Run a subprocess to execute the ripping.  Note this is non-blocking because the
    # ripper never exits.  (If we blocked waiting for it, we'd wait forever.)  Instead,
    # we wait for the output files to be finished.
    process = subprocess.Popen(cmd)

    # Register a cleanup function that will kill the ripping subprocess.  This handles the cases
    # where someone hits Control-C, or the main program exits for some other reason.  Without
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

    # Wait for the tiff files to stop changing.
    remaining_sec = RIP_TOTAL_WAIT_SECS
    last_tiffs = {}
    while remaining_sec >= 0:
        logging.info('Watching for ripper to finish for %d more seconds', remaining_sec)
        remaining_sec -= RIP_POLL_SECS
        time.sleep(RIP_POLL_SECS)

        tiffs = get_tiffs()
        tiffs_changed = (last_tiffs != tiffs)
        last_tiffs = tiffs

        if not tiffs_changed:
            logging.info('Detected ripping is complete')
            time.sleep(RIP_EXTRA_WAIT_SECS)  # Wait before terminating ripper, just to be safe.
            logging.info('Killing ripper')
            process.kill()
            logging.info('Ripper has been killed')
            copy_back_files()
            return

    raise RippingError('Killing ripper because it did not finish within %s seconds' % RIP_TOTAL_WAIT_SECS)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s.%(msecs)03d %(module)s:%(lineno)s %(levelname)s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    parser = argparse.ArgumentParser(description='Preprocess 2-photon raw data into individual tiffs')
    parser.add_argument('--in_path',
                        type=pathlib.Path,
                        required=True,
                        help='Directory containing RAWDATA and Filelist.txt files for ripping')
    parser.add_argument('--out_path',
                        type=pathlib.Path,
                        required=True,
                        help='Directory for output tiff stack.')
    parser.add_argument('--rippers_path',
                        type=pathlib.Path,
                        required=True,
                        help='Directory containing versions of Bruker Image Block Ripping Utility.')
    args = parser.parse_args()
    ripper_path = determine_ripper(args.in_path, args.rippers_path)
    raw_to_tiff(args.in_path, args.out_path, ripper_path)
