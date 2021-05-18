import logging

import click
from click_pathlib import Path

from . import analyze, backup, convert, layout, preprocess, raw2tiff


@click.group(chain=True)
@click.pass_context
@click.option("--base-path", type=Path(exists=True), required=True, help="Top-level storage for local data.")
@click.option("--acquisition", required=True, help="Acquisition sub-directory to process.")
def cli(ctx, base_path, acquisition):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s.%(msecs)03d %(module)s:%(lineno)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    ctx.obj = layout.Layout(base_path, acquisition)


cli.add_command(raw2tiff.raw2tiff)
cli.add_command(convert.convert)
cli.add_command(preprocess.preprocess)
cli.add_command(analyze.analyze)
cli.add_command(backup.backup)
