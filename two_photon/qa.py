import logging

import click
import h5py
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@click.command()
@click.pass_obj
@click.option("--num_frames", default=15, help="Number of frames to make QA plots for")
@click.option(
    "--random_state",
    type=int,
    help="Random seed for sampling frames for QA (if unset, frames are evenly spaced through dataset)",
)
def qa(layout, num_frames, random_state):
    convert_path = layout.path("convert")
    orig_h5_path = convert_path / "orig.h5"

    preprocess_path = layout.path("preprocess")
    preprocess_h5_path = preprocess_path / "preprocess" / "preprocess.h5"
    artefacts_path = preprocess_path / "artefacts" / "artefacts.h5"

    qa_path = layout.path("qa")
    qa_plot_path = qa_path / "qa.png"

    with h5py.File(orig_h5_path, "r") as h5file:
        data = h5file["data"][()]

    with h5py.File(preprocess_h5_path, "r") as h5file:
        data_processed = h5file["data"][()]

    df_artefacts = pd.read_hdf(artefacts_path, "artefacts")

    qa_plot = side_by_side_comparison(data, data_processed, df_artefacts, num_frames, random_state)

    qa_plot_path.parent.mkdir(parents=True, exist_ok=True)
    qa_plot.savefig(qa_plot_path)
    logger.info("Stored QA plot in %s", qa_plot_path)

    logger.info("Done")


def side_by_side_comparison(uncorrected, corrected, df_artefacts, num_frames=15, random_state=None):
    """Makes a figure showing a sample of frames with artefacts, before and after correction."""
    if random_state is not None:
        df_samples = df_artefacts.sample(num_frames, random_state=random_state).sort_values(["t", "z"])
    else:
        indices = np.linspace(0, len(df_artefacts.index) - 1, num=num_frames)
        df_samples = df_artefacts.iloc[indices]

    ncols = 2
    figure, axes = plt.subplots(
        num_frames, ncols, figsize=(5 * ncols, 5 * num_frames), sharex=True, sharey=True, constrained_layout=True
    )

    axes[0][0].set_title("Uncorrected")
    axes[0][1].set_title("Corrected")

    for idx, sample in enumerate(df_samples.itertuples()):
        axes[idx][0].set_ylabel(f"Artefact {sample.Index}, Timepoint {sample.t}, Plane {sample.z}")

        vmin = corrected[sample.t, sample.z].min()
        vmax = corrected[sample.t, sample.z].max()

        axes[idx][0].imshow(uncorrected[sample.t, sample.z], vmin=vmin, vmax=vmax)
        axes[idx][0].axhline(sample.pixel_start, c="r", lw=2)
        axes[idx][0].axhline(sample.pixel_stop, c="r", lw=2)

        axes[idx][1].imshow(corrected[sample.t, sample.z], vmin=vmin, vmax=vmax)
        axes[idx][1].axhline(sample.pixel_start, c="r", lw=2)
        axes[idx][1].axhline(sample.pixel_stop, c="r", lw=2)

        print(sample.pixel_start, sample.pixel_stop)

    return figure
