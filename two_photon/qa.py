import matplotlib.pyplot as plt


def side_by_side_comparison(uncorrected, corrected, df_artefacts, nsamples=15):
    """Makes a figure showing a sample of frames with artefacts, before and after correction."""
    samples = df_artefacts.sample(nsamples).reset_index().sort_values(["frame", "z_plane"])

    ncols = 2
    figure, axes = plt.subplots(
        nsamples, ncols, figsize=(5 * ncols, 5 * nsamples), sharex=True, sharey=True, constrained_layout=True
    )

    axes[0][0].set_title("Uncorrected")
    axes[0][1].set_title("Corrected")

    for row, s in enumerate(samples.itertuples()):
        axes[row][0].set_ylabel(f"Frame {s.frame}, Plane {s.zplane}")

        vmin = corrected[s.frame, s.z_plane].min()
        vmax = corrected[s.frame, s.z_plane].max()

        axes[row][0].imshow(uncorrected[s.frame, s.z_plane], vmin=vmin, vmax=vmax)
        axes[row][0].axhline(s.y_min, c="r", lw=2)
        axes[row][0].axhline(s.y_max, c="r", lw=2)

        axes[row][1].imshow(corrected[s.frame, s.z_plane], vmin=vmin, vmax=vmax)
        axes[row][1].axhline(s.y_min, c="r", lw=2)
        axes[row][1].axhline(s.y_max, c="r", lw=2)

    return figure
