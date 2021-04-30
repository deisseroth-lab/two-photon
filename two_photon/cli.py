import logging

import click
import click_pathlib

from . import raw2tiff
from . import tiff2hdf5

def validate_hdf5(ctx, param, value):
    if value.endswith('.h5') and not value.endswith('.hdf5'):
        raise click.BadParameter('suffix should be .h5 or .hdf5 for compatibility with Suite2p')
    return value

@click.group(chain=True)
@click.pass_context
@click.option('--directory', type=click_pathlib.Path(exists=True), required=True,
              help='Top-level directory for a single acquisition')
@click.option('--raw_subdir', default='raw', show_default=True,
              help='Subdirectory under --directory for raw data')
@click.option('--tiff_subdir', default='tiff', show_default=True,
              help='Subdirectory under --directory for tiff stack')
@click.option('--orig_hdf5', default='orig.hdf5', show_default=True,
              callback=validate_hdf5, 
              help='Filename under --directory for original data in hdf5 format')
@click.option('--hdf5_key', default='/data', show_default=True, 
              help='Key within hdf5 file for data')
def cli(ctx, directory, raw_subdir, tiff_subdir, orig_hdf5, hdf5_key):
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s.%(msecs)03d %(module)s:%(lineno)s %(levelname)s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    ctx.ensure_object(dict)
    ctx.obj['raw_path'] = directory / raw_subdir
    ctx.obj['tiff_path'] = directory / tiff_subdir
    ctx.obj['orig_hdf5_path'] = directory / orig_hdf5
    ctx.obj['hdf5_key'] = hdf5_key

cli.add_command(raw2tiff.raw2tiff)
cli.add_command(tiff2hdf5.tiff2hdf5)
