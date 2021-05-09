import logging

import click
from click_pathlib import Path

from . import convert, preprocess, raw2tiff


def check_h5(ctx, param, value):
    if value.endswith(".h5") and not value.endswith(".hdf5"):
        raise click.BadParameter("suffix should be .h5 or .hdf5 for compatibility with Suite2p")
    return value


@click.group(chain=True)
@click.pass_context
@click.option("--path", type=Path(exists=True), required=True, help="Top-level storage for local data.")
@click.option("--acquisition", required=True, help="Acquisition sub-directory to process.")
def cli(ctx, path, acquisition):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s.%(msecs)03d %(module)s:%(lineno)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    ctx.ensure_object(dict)
    ctx.obj["path"] = path
    ctx.obj["acquisition"] = acquisition


cli.add_command(raw2tiff.raw2tiff)
cli.add_command(convert.convert)
cli.add_command(preprocess.preprocess)
