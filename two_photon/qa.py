import matplotlib.pyplot as plt
import numpy as np


def side_by_side_comparison(uncorrected, corrected, df_artefacts, nsamples=15, random=None):
    """Makes a figure showing a sample of frames with artefacts, before and after correction."""
    if random is not None:
        df_samples = df_artefacts.sample(nsamples, random_state=random).sort_values(["t", "z"])
    else:
        indices = np.linspace(0, len(df_artefacts.index) - 1, num=nsamples)
        df_samples = df_artefacts.iloc[indices]

    ncols = 2
    figure, axes = plt.subplots(
        nsamples, ncols, figsize=(5 * ncols, 5 * nsamples), sharex=True, sharey=True, constrained_layout=True
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

    return figure
