import pandas as pd
from two_photon import preprocess


def test_artefact_regions():
    df_frames = pd.DataFrame(
        [
            [25, 50],
            [50, 75],
            [75, 100],
            [105, 130],  # Gap from previous frame
        ],
        columns=["start", "stop"],
    )
    df_stims = pd.DataFrame(
        [
            [20, 30],  # Straddles first frame start
            [60, 70],  # Entirely within frame
            [90, 102],  # Ends within frame gap
            [103, 110],  # Starts within frame gap
            [125, 140],  # Straddles last frame end
        ],
        columns=["start", "stop"],
    )
    # df_stims = pd.DataFrame([[5, 10], [20, 30], [60, 70], [90, 110]], columns=["start", "stop"])
    shape = (2, 2, 200, 200)
    df_artefacts = preprocess.artefact_regions(df_frames, df_stims, shape)

    df_expected = pd.DataFrame(
        [
            [0, 0, 0, 0, 0, 40],
            [0, 1, 80, 0, 1, 160],
            [1, 0, 120, 1, 0, 200],
            [1, 1, 0, 1, 1, 40],
            [1, 1, 160, 1, 1, 200],
        ],
        columns=["t_start", "z_start", "pixel_start", "t_stop", "z_stop", "pixel_stop"],
    )
    pd.testing.assert_frame_equal(df_artefacts, df_expected)
