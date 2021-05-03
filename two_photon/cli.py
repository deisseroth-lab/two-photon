import logging

import click
from click_pathlib import Path

from . import raw2tiff, tiff2hdf5


def check_h5(ctx, param, value):
    if value.endswith(".h5") and not value.endswith(".hdf5"):
        raise click.BadParameter("suffix should be .h5 or .hdf5 for compatibility with Suite2p")
    return value


@click.group(chain=True)
@click.pass_context
@click.option("--directory", type=Path(exists=True), required=True, help="Top-level directory for a single acquisition")
@click.option("--raw_subdir", default="raw", show_default=True, help="Subdirectory under --directory for raw data")
@click.option("--tiff_subdir", default="tiff", show_default=True, help="Subdirectory under --directory for tiff stack")
@click.option("--h5_key", default="/data", show_default=True, help="Key within h5 file for data")
@click.option(
    "--orig_h5",
    default="orig.h5",
    callback=check_h5,
    show_default=True,
    help="Filename in --directory for original data in h5 format",
)
def cli(ctx, directory, raw_subdir, tiff_subdir, h5_key, orig_h5):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s.%(msecs)03d %(module)s:%(lineno)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    ctx.ensure_object(dict)
    ctx.obj["raw_path"] = directory / raw_subdir
    ctx.obj["tiff_path"] = directory / tiff_subdir
    ctx.obj["orig_h5_path"] = directory / orig_h5
    ctx.obj["h5_key"] = h5_key


cli.add_command(raw2tiff.raw2tiff)
cli.add_command(tiff2hdf5.tiff2hdf5)
