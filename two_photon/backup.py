import logging
import os
import platform
import subprocess

import click
from click_pathlib import Path

logger = logging.getLogger(__name__)


class BackupError(Exception):
    pass


# TODO: integrate the following, possibly by copying the data into the appropriate directory
#       in the convert stage?
# This csv file is part of the original data and backed up with --backup_data.
# It is also backed up here so that it can be immediately available with the rest of
# the output data, even if --backup_data is not used.
# backup(fname_csv, dirname_backup / "output")
# if stim_channel_name:
#     slm_date = datetime.strptime(session_name[:8], "%Y%m%d").strftime("%d-%b-%Y")
#     slm_mouse = session_name[8:]

#     slm_root = args.slm_setup_dir / slm_date
#     slm_targets = slm_root / slm_mouse
#     slm_trial_order_pattern = "*_" + slm_mouse + "_" + recording_name

#     backup(slm_targets, dirname_backup / "targets")
#     trial_order_folder = glob.glob(os.path.join(slm_root, slm_trial_order_pattern))
#     trial_order_path = pathlib.WindowsPath(trial_order_folder[0])
#     backup(trial_order_path, dirname_backup / "trial_order")
#     # backup_pattern(slm_root, slm_trial_order_pattern, dirname_backup / 'trial_order')


@click.command()
@click.pass_obj
@click.option(
    "--backup_path", type=Path(exists=True), required=True, help="Top-level directory where backup data resides"
)
@click.option(
    "--backup_stage",
    type=click.Choice(["raw", "convert", "preprocess", "analyze"]),
    multiple=True,
    help="Names of stages to backup",
)
def backup(layout, backup_path, backup_stage):
    """Backs up data from one or more pipeline stages.

    Parameters
    ----------
    layout: Layout object
        Object used to determine path naming
    backup_path: pathlib.Path
        Top-level directory where backup data resides
    backup_stages: list of str
        Names of stages to backup
    """
    for stage in backup_stage:
        local_path = layout.path(stage)
        remote_path = layout.backup_path(backup_path, stage)

        if stage == "tiff":  # TIFF stacks need to be archived first.
            archive = archive_path(local_path)
            backup_path(archive, remote_path / archive.name)
        else:
            backup_path(local_path, remote_path)


def backup_path(local_path, backup_path):
    """Sync local data to backup directory."""
    os.makedirs(backup_path.parent, exist_ok=True)
    system = platform.system()
    if system == "Windows":
        if os.path.isdir(local_path):
            cmd = ["robocopy.exe", str(local_path), str(backup_path), "/S"]
        else:
            # Single file copy done by giving source and dest directories, and specifying full filename.
            os.makedirs(backup_path, exist_ok=True)
            cmd = [
                "robocopy.exe",
                str(local_path.parent),
                str(backup_path),
                local_path.name,
            ]
        expected_returncode = 1  # robocopy.exe gives exit code 1 for a successful copy.
    elif system == "Linux":
        if os.path.isdir(local_path):
            cmd = ["rsync", "-avh", str(local_path) + "/", str(backup_path)]
        else:
            os.makedirs(backup_path, exist_ok=True)
            cmd = [
                "rsync",
                "-avh",
                str(local_path),
                str(backup_path / local_path.name),
            ]
        expected_returncode = 0  # Most programs give an exit code of 0 on success.
    else:
        raise BackupError("Do not recognize system: %s" % system)
    run_cmd(cmd, expected_returncode)


def archive_path(path):
    """Use tar+gzip (7z on Windows) to zip directory contents into single, compressed file."""
    archive = path.with_suffix(".tgz")
    system = platform.system()
    if system == "Linux":
        # (c)reate archive as a (f)ile, use (z)ip compression
        cmd = ["tar", "cfz", str(archive), str(path)]
        run_cmd(cmd, expected_returncode=0)
    elif system == "Windows":
        # Using 7z to mimic 'tar cfz' as per this post:
        # https://superuser.com/questions/244703/how-can-i-run-the-tar-czf-command-in-windows
        cmd = f"7z -ttar a dummy {path}\* -so | 7z -si -tgzip a {archive}"
        run_cmd(cmd, expected_returncode=0, shell=True)
    else:
        raise BackupError("Do not recognize system: %s" % system)
    return archive


def backup_pattern(local_dir, local_pattern, backup_dir):
    """Backup a filepattern to another directory.

    Need special treatment, as robocopy.exe on Windows has a different command line than typicaly linux utilities.
    """
    system = platform.system()
    if system == "Linux":
        backup(local_dir / local_pattern, backup_dir)
    elif system == "Windows":
        os.makedirs(backup_dir, exist_ok=True)
        cmd = ["robocopy.exe", str(local_dir), str(backup_dir), local_pattern, "/S"]
        expected_returncode = 1  # robocopy.exe gives exit code 1 for a successful copy.
        run_cmd(cmd, expected_returncode)
    else:
        raise BackupError("Do not recognize system: %s" % system)


def run_cmd(cmd, expected_returncode, shell=False):
    """Run a shell command via a subprocess."""
    logger.info("Running command in subprocess:\n%s", cmd)
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=shell)
    if result.returncode != expected_returncode:
        raise BackupError("Command failed!\n%s" % result.stdout.decode("utf-8"))
    logger.info("Output:\n%s", result.stdout.decode("utf-8"))
