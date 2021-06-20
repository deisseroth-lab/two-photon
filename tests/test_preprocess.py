import pytest

import pandas as pd

from two_photon import preprocess


@pytest.mark.parametrize(
    "settle_ms,piezo_period_frames,piezo_skip_frames,expected_fname",
    [
        (0, None, None, "frame_start.tsv"),
        (5, None, None, "frame_start_settle.tsv"),
        (0, 7, 3, "frame_start_piezo.tsv"),
    ],
)
def test_extract_frames(testdata, settle_ms, piezo_period_frames, piezo_skip_frames, expected_fname):
    df_voltage = pd.read_hdf(testdata / "voltage_recording.h5", "voltages")
    frame_signal = df_voltage["StartFrameResonant"]

    df_frames = preprocess.extract_frames(frame_signal, settle_ms, piezo_period_frames, piezo_skip_frames)

    # To rewrite testdata, uncomment the following:
    # df_frames.to_csv(testdata / expected_fname, sep="\t")

    df_frames_expected = pd.read_csv(testdata / expected_fname, sep="\t", index_col="frame")
    pd.testing.assert_frame_equal(df_frames, df_frames_expected)


@pytest.mark.parametrize(
    "shift_ms,buffer_ms,expected_fname",
    [
        (0, 0, "stim.tsv"),
        (1, 0, "stim_1_0.tsv"),
        (1, 2, "stim_1_2.tsv"),
    ],
)
def test_extract_stims(testdata, shift_ms, buffer_ms, expected_fname):
    df_voltage = pd.read_hdf(testdata / "voltage_recording.h5", "voltages")
    stim_signal = df_voltage["StartFrameResonant"]

    df_stims = preprocess.extract_stims(stim_signal, shift_ms, buffer_ms)

    # To rewrite testdata, uncomment the following:
    # df_stims.to_csv(testdata / expected_fname, sep="\t")

    df_stims_expected = pd.read_csv(testdata / expected_fname, sep="\t", index_col="stim")
    pd.testing.assert_frame_equal(df_stims, df_stims_expected)
