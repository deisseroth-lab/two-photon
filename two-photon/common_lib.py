"""Utilities common to multiple scripts."""

import logging
import os
import platform
import subprocess

logger = logging.getLogger(__file__)


class BackupError(Exception):
    pass


def setup_logging(dirname_output):
    """Set up logging to write all INFO messages to both the stdout stram and a file."""
    fname_logs = dirname_output / 'backup_session.log'
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s.%(msecs)03d %(module)s:%(lineno)s %(levelname)s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        handlers=[logging.StreamHandler(), logging.FileHandler(fname_logs)])


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


def run_cmd(cmd, expected_returncode, shell=False):
    """Run a shell command via a subprocess."""
    logger.info('Running command in subprocess:\n%s', cmd)
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=shell)  # pylint: disable=subprocess-run-check
    if result.returncode != expected_returncode:
        raise BackupError('Command failed!\n%s' % result.stdout.decode('utf-8'))
    logger.info('Output:\n%s', result.stdout.decode('utf-8'))
