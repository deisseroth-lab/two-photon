"""Runs Suite2p analysis over one or more acquisitions."""
import json
import logging
from xml.etree import ElementTree

import click
import h5py

logger = logging.getLogger(__name__)


@click.command()
@click.pass_obj
@click.option(
    "--extra-acquisitions",
    multiple=True,
    help="Additional acquisitions to include in analysis in addition to --acquisitions",
)
def analyze(layout, extra_acquisitions):
    """Runs suite2p on preprocessed data."""
    preprocess_path = layout.path("preprocess")
    analyze_path = layout.path("analyze")

    analyze_path.mkdir(parents=True, exist_ok=True)
    json_path = analyze_path / "data_paths.json"

    data_paths = [preprocess_path] + [layout.path("preprocess", acq) for acq in extra_acquisitions]
    data_paths = [p / "preprocess" for p in data_paths]

    xml_path = layout.raw_xml_path()
    mdata_root = ElementTree.parse(xml_path).getroot()
    element = mdata_root.find('.//PVStateValue[@key="framePeriod"]')
    period = float(element.attrib["value"])

    z_planes = 0
    for data_path in data_paths:
        with h5py.File(data_path / "preprocess.h5", "r") as h5_file:
            z_planes += h5_file["data"].shape[1]

    fs_param = 1.0 / (period * z_planes)

    # Use strings for paths: Suite2p and JSON cannot interpret Path, and logging is clearer.
    data_paths_str = [str(p) for p in data_paths]

    # Load suite2p only right before use, as it has a long load time.
    import suite2p

    default_ops = suite2p.default_ops()
    params = {
        "input_format": "h5",
        "data_path": data_paths_str,
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

    with open(json_path, "w") as fout:
        json.dump(data_paths_str, fout, indent=4)
    logger.info("Running suite2p on files:\n%s\n%s", "\n".join(data_paths_str), params)

    suite2p.run_s2p(ops=default_ops, db=params)
