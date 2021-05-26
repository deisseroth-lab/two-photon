import datetime
import logging

import click
from click_pathlib import Path

from . import analyze, backup, convert, layout, preprocess, raw2tiff


@click.group(chain=True)
@click.pass_context
@click.option("--base-path", type=Path(exists=True), required=True, help="Top-level storage for local data.")
@click.option("--acquisition", required=True, help="Acquisition sub-directory to process.")
def cli(ctx, base_path, acquisition):
    dt = datetime.datetime.now().strftime("%Y%m%d.%H%M%S")

    lo = layout.Layout(base_path, acquisition)
    ctx.obj = lo

    logs_path = lo.path("logs")
    logs_path.mkdir(parents=True, exist_ok=True)

    fname_logs = logs_path / f"{dt}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s.%(msecs)03d %(module)s:%(lineno)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(), logging.FileHandler(fname_logs)],
    )


cli.add_command(raw2tiff.raw2tiff)
cli.add_command(convert.convert)
cli.add_command(preprocess.preprocess)
cli.add_command(analyze.analyze)
cli.add_command(backup.backup)
