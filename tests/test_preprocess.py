import pandas as pd

from two_photon import preprocess


def test_artefact_regions_single_frame():
    df_frames = pd.DataFrame([[25, 50]], columns=["start", "stop"])
    df_stims = pd.DataFrame(
        [
            [0, 10],  # Before first frame
            [20, 30],  # Straddles frame start
            [35, 40],  # Entirely within frame
            [45, 50],  # Straddles frame end
            [60, 70],  # After final frame
        ],
        index=[0, 1, 2, 3, 4],
        columns=["start", "stop"],
    )
    shape = (1, 1, 200, 200)
    df_artefacts = preprocess.artefact_regions(df_frames, df_stims, shape)

    df_expected = pd.DataFrame(
        [
            [0, 0, 0, 40],
            [0, 0, 80, 120],
            [0, 0, 160, 200],
        ],
        index=[1, 2, 3],
        columns=["t", "z", "pixel_start", "pixel_stop"],
    )
    pd.testing.assert_frame_equal(df_artefacts, df_expected)


def test_artefact_regions_multi_frame_stim():
    df_frames = pd.DataFrame(
        [
            [25, 50],
            [55, 80],
            [90, 110],
            [110, 130],
        ],
        columns=["start", "stop"],
    )
    df_stims = pd.DataFrame([[70, 120]], index=[42], columns=["start", "stop"])
    shape = (2, 2, 200, 200)
    df_artefacts = preprocess.artefact_regions(df_frames, df_stims, shape)

    df_expected = pd.DataFrame(
        [
            [0, 1, 120, 200],
            [1, 0, 0, 200],
            [1, 1, 0, 100],
        ],
        index=[42, 42, 42],
        columns=["t", "z", "pixel_start", "pixel_stop"],
    )
    pd.testing.assert_frame_equal(df_artefacts, df_expected)
