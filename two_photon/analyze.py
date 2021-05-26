"""Runs Suite2p analysis over one or more acquisitions."""
import json
import logging

import click
import h5py

from two_photon import utils

logger = logging.getLogger(__name__)


@click.command()
@click.pass_obj
@click.option(
    "--extra-acquisitions",
    multiple=True,
    help="Additional acquisitions to include in analysis in addition to --acquisitions",
)
@click.option("--suite2p-params-file", help="Optional Suite2p ops file (json format) to specify non-default options.")
def analyze(layout, extra_acquisitions, suite2p_params_file):
    """Runs suite2p on preprocessed data."""
    preprocess_path = layout.path("preprocess")
    analyze_path = layout.path("analyze")

    analyze_path.mkdir(parents=True, exist_ok=True)
    json_path = analyze_path / "data_paths.json"

    data_paths = [preprocess_path] + [layout.path("preprocess", acq) for acq in extra_acquisitions]
    data_paths = [p / "preprocess" for p in data_paths]

    # Use first file to determine the sampling rate.
    with h5py.File(data_paths[0] / "preprocess.h5", "r") as h5_file:
        z_planes = h5_file["data"].shape[1]
    period = utils.frame_period(layout)
    fs_param = 1.0 / (period * z_planes)

    # Use strings for paths: Suite2p and JSON cannot interpret Path, and logging is clearer.
    data_paths_str = [str(p) for p in data_paths]

    params_internal = {
        "input_format": "h5",
        "data_path": data_paths_str,
        "save_path0": str(analyze_path),
        "fs": fs_param,
    }
    params_external = json.load(open(suite2p_params_file, "r")) if suite2p_params_file else {}
    params = {**params_internal, **params_external}

    with open(json_path, "w") as fout:
        json.dump(data_paths_str, fout, indent=4)
    logger.info("Running suite2p on files:\n%s\n%s", "\n".join(data_paths_str), params)

    # Load suite2p only right before use, as it has a long load time.
    import suite2p

    suite2p.run_s2p(params)
