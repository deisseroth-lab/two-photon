"""Runs Suite2p analysis over one or more acquisitions."""
import json
import logging
from xml.etree import ElementTree

import click
import h5py

logger = logging.getLogger(__name__)


@click.command()
@click.pass_context
@click.option("--extra_acquisitions", multiple=True, help="Additional paths to include in analysis after --path")
def analyze(ctx, extra_paths):
    path = ctx.obj["path"]
    acquisition = ctx.obj["acquisition"]

    analyze_path = path / "analyze" / acquisition

    data_paths = [p / "processed" / acquisition for p in [path] + extra_paths]

    xml_prefix = acquisition.split("/")[-1]
    fname_xml = path / "raw" / acquisition / xml_prefix + ".xml"

    mdata_root = ElementTree.parse(fname_xml).getroot()
    element = mdata_root.find('.//PVStateValue[@key="framePeriod"]')
    period = float(element.attrib["value"])

    z_planes = 0
    for data_path in data_paths:
        for h5_fname in data_path.glob("*.h5"):
            with h5py.File(h5_fname, "r") as h5_file:
                z_planes += h5_file["data"].shape[1]

    fs_param = 1.0 / (period * z_planes)

    # Load suite2p only right before use, as it has a long load time.
    from suite2p import run_s2p

    default_ops = run_s2p.default_ops()
    params = {
        "input_format": "h5",
        "data_path": data_paths,
        "save_path0": str(analyze_path),
        "nplanes": z_planes,
        "fs": fs_param,
        "save_mat": True,
        "bidi_corrected": True,
        "spatial_hp": 50,
        "sparse_mode": False,
        "threshold_scaling": 3,
        "diameter": 6,
    }

    # Use strings for paths: JSON cannot interpret Path, and logging is clearer with strings.
    data_paths_str = [str(p) for p in data_paths]
    with open(analyze_path / "data_paths.json", "w") as fout:
        json.dump(data_paths_str, fout, indent=4)
    logger.info("Running suite2p on files:\n%s\n%s", "\n".join(data_paths_str), params)

    run_s2p.run_s2p(ops=default_ops, db=params)
