import pandas as pd

from two_photon import artefact_detect


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
    df_artefacts = artefact_detect.artefact_regions(df_frames, df_stims)

    df_expected = pd.DataFrame(
        [
            [0, 0, 0.2],
            [0, 0.4, 0.6],
            [0, 0.8, 1.0],
        ],
        index=[1, 2, 3],
        columns=["frame", "frac_start", "frac_stop"],
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
    df_artefacts = artefact_detect.artefact_regions(df_frames, df_stims)

    df_expected = pd.DataFrame(
        [
            [1, 0.6, 1.0],
            [2, 0, 1.0],
            [3, 0, 0.5],
        ],
        index=[42, 42, 42],
        columns=["frame", "frac_start", "frac_stop"],
    )
    pd.testing.assert_frame_equal(df_artefacts, df_expected)
