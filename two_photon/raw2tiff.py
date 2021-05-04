"""Library for running Bruker image ripping utility."""

import atexit
import logging
import os
import pathlib
import platform
import re
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET

import click

logger = logging.getLogger(__name__)

# Ripping process does not end cleanly, so the filesystem is polled to detect the
# processing finishing.  The following variables relate to the timing of that polling
# process.
RIP_TOTAL_WAIT_SECS = 3600  # Total time to wait for ripping before killing it.
RIP_EXTRA_WAIT_SECS = 10  # Extra time to wait after ripping is detected to be done.
RIP_POLL_SECS = 10  # Time to wait between polling the filesystem.


class RippingError(Exception):
    """Error raised if problems encountered during data conversion."""


@click.command()
@click.pass_context
def raw2tiff(ctx):
    """Convert Bruker RAW files to TIFF files via ripper.

    Parameters
    ----------
    ctx : click's context object
        The underlying object should contain "path" an "acquisition" global flags
    """
    path = ctx.obj["path"]
    acquisition = ctx.obj["acquisition"]

    raw_path = path / "raw" / acquisition
    tiff_path = path / "processed" / acquisition / "tiff"

    # Bruker software appends the raw_path basename to the given output directory.
    tiff_path_bruker = tiff_path / raw_path.name
    os.makedirs(tiff_path_bruker, exist_ok=True)

    ripper = determine_ripper(raw_path)

    def get_filelists():
        filelists = list(sorted(raw_path.glob("*Filelist.txt")))
        logging.info("  Found filelists: %s", [str(f) for f in filelists])
        return filelists

    def get_rawdata():
        rawdata = list(sorted(raw_path.glob("*RAWDATA*")))
        logging.info("  Found # rawdata files: %s", len(rawdata))
        return rawdata

    def get_tiffs():
        tiffs = set(tiff_path_bruker.glob("*.ome.tif"))
        logging.info("  Found # tiff files: %s", len(tiffs))
        return tiffs

    def copy_back_files():
        """Copies back metadata files that Bruker copied to output directory.

        This helps preserve the input directory contents.
        """
        paths_to_copy = [path for path in tiff_path_bruker.iterdir() if not path.name.endswith("ome.tif")]
        logging.info("Copying back files to input directory: %s", paths_to_copy)
        for path in paths_to_copy:
            if path.is_file():
                shutil.copy(path, raw_path)
            else:
                shutil.copytree(path, raw_path / path.name)

    def correct_tiff_directory():
        """Move the tiff directory created by Bruker up one level."""
        for path in tiff_path_bruker.iterdir():
            path.rename(tiff_path / path.name)
        tiff_path_bruker.rmdir()

    filelists = get_filelists()
    if not filelists:
        raise RippingError("No *Filelist.txt files present in data directory")

    rawdata = get_rawdata()
    if not rawdata:
        raise RippingError("No RAWDATA files present in %s" % raw_path)

    tiffs = get_tiffs()
    if tiffs:
        raise RippingError("Cannot rip because tiffs already exist in %s (%d found)" % (raw_path, len(tiffs)))

    logger.info(
        "Ripping using:\n %s\n %s",
        "\n ".join([str(f) for f in filelists]),
        "\n ".join([str(f) for f in rawdata]),
    )

    system = platform.system()
    if system == "Linux":
        cmd = ["wine"]
    else:
        cmd = []

    # Normally, the fname is passed to -AddRawFile.  But there is a bug in the software, so
    # we have to pop up one level and use -AddRawFileWithSubFolders.
    cmd += [
        ripper,
        "-KeepRaw",
        "-DoNotRipToInputDirectory",
        "-IncludeSubFolders",
        "-AddRawFileWithSubFolders",
        str(raw_path),
        "-SetOutputDirectory",
        str(tiff_path),
        "-Convert",
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
            if process.poll() is None:
                time.sleep(1)
                p_sec += 1
        if p_sec >= timeout_sec:
            process.kill()
        logger.info("cleaned up!")

    atexit.register(cleanup)

    # Wait for the tiff files to stop changing.
    remaining_sec = RIP_TOTAL_WAIT_SECS
    last_tiffs = {}
    while remaining_sec >= 0:
        logging.info("Watching for ripper to finish for %d more seconds", remaining_sec)
        remaining_sec -= RIP_POLL_SECS
        time.sleep(RIP_POLL_SECS)

        tiffs = get_tiffs()
        tiffs_changed = last_tiffs != tiffs
        last_tiffs = tiffs

        if tiffs and not tiffs_changed:
            logging.info("Detected ripping is complete")
            time.sleep(RIP_EXTRA_WAIT_SECS)  # Wait before terminating ripper, just to be safe.
            logging.info("Killing ripper")
            process.kill()
            logging.info("Ripper has been killed")

            copy_back_files()
            correct_tiff_directory()

            logging.info("Done")
            return

    raise RippingError("Killing ripper because it did not finish within %s seconds" % RIP_TOTAL_WAIT_SECS)


def determine_ripper(raw_path):
    """Determine which version of the Prairie View ripper to use based on reading metadata."""
    env_files = list(raw_path.glob("*.env"))
    if len(env_files) != 1:
        raise RippingError("Only expected 1 env file in %s, but found: %s" % (raw_path, env_files))

    # TODO: Make this work when running from git clone, or when package is installed.
    rippers_path = pathlib.Path(__file__).parent.parent

    tree = ET.parse(str(raw_path / env_files[0]))
    root = tree.getroot()
    version = root.attrib["version"]

    # Prairie View versions are given in the form A.B.C.D.
    match = re.match(r"^(?P<majmin>\d+\.\d+)\.\d+\.\d+$", version)
    if not match:
        raise RippingError("Could not parse version (expected A.B.C.D): %s" % version)

    version = match.group("majmin")
    logger.info("Data created with Prairie version %s", version)

    ripper = rippers_path / f"Prairie View {version}" / "Utilities" / "Image-Block Ripping Utility.exe"
    if not ripper.exists():
        raise RippingError("Could not locate needed Prairie View executable:\n%s" % str(ripper))

    logger.info("Using ripper:\n%s", ripper)
    return ripper
