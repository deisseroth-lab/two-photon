import numpy as np

from two_photon import artefacts


def test_get_start_stop():
    stim_start = np.array([40.])
    stim_stop = np.array([45.])
    frame_start = np.array([0., 25., 50.])
    y_px = 200
    shape = (3, 1)
    settle_time = 0

    frame, z_plane, y_px_start, y_px_stop = artefacts.get_start_stop(stim_start, stim_stop, frame_start, y_px, shape,
                                                                     settle_time)

    np.testing.assert_equal(frame, [1])
    np.testing.assert_equal(z_plane, [0])
    np.testing.assert_equal(y_px_start, [120])
    np.testing.assert_equal(y_px_stop, [160])


def test_get_start_stop_settle():
    stim_start = np.array([40.])
    stim_stop = np.array([45.])
    frame_start = np.array([0., 25., 50.])
    y_px = 200
    shape = (3, 1)
    settle_time = 5

    frame, z_plane, y_px_start, y_px_stop = artefacts.get_start_stop(stim_start, stim_stop, frame_start, y_px, shape,
                                                                     settle_time)

    np.testing.assert_equal(frame, [1])
    np.testing.assert_equal(z_plane, [0])
    np.testing.assert_equal(y_px_start, [150])
    np.testing.assert_equal(y_px_stop, [200])


def test_get_start_stop_settle_in_settle():
    stim_start = np.array([40.])
    stim_stop = np.array([49.])
    frame_start = np.array([0., 25., 50.])
    y_px = 200
    shape = (3, 1)
    settle_time = 5

    frame, z_plane, y_px_start, y_px_stop = artefacts.get_start_stop(stim_start, stim_stop, frame_start, y_px, shape,
                                                                     settle_time)

    np.testing.assert_equal(frame, [1])
    np.testing.assert_equal(z_plane, [0])
    np.testing.assert_equal(y_px_start, [150])
    np.testing.assert_equal(y_px_stop, [200])


def test_get_start_stop_two_frame():
    stim_start = np.array([15.])
    stim_stop = np.array([45.])
    frame_start = np.array([0., 25., 50., 75.])
    y_px = 200
    shape = (2, 2)
    settle_time = 0

    frame, z_plane, y_px_start, y_px_stop = artefacts.get_start_stop(stim_start, stim_stop, frame_start, y_px, shape,
                                                                     settle_time)

    np.testing.assert_equal(frame, [0, 0])
    np.testing.assert_equal(z_plane, [0, 1])
    np.testing.assert_equal(y_px_start, [120, 0])
    np.testing.assert_equal(y_px_stop, [200, 160])


def test_get_start_stop_two_frame_settle():
    stim_start = np.array([15.])
    stim_stop = np.array([40.])
    frame_start = np.array([0., 25., 50., 75.])
    y_px = 200
    shape = (2, 2)
    settle_time = 5

    frame, z_plane, y_px_start, y_px_stop = artefacts.get_start_stop(stim_start, stim_stop, frame_start, y_px, shape,
                                                                     settle_time)

    np.testing.assert_equal(frame, [0, 0])
    np.testing.assert_equal(z_plane, [0, 1])
    np.testing.assert_equal(y_px_start, [150, 0])
    np.testing.assert_equal(y_px_stop, [200, 151])


def test_get_start_stop_two_frame_settle_no_frames():
    stim_start = np.array([47.])
    stim_stop = np.array([48.])
    frame_start = np.array([0., 25., 50., 75.])
    y_px = 200
    shape = (2, 2)
    settle_time = 5

    frame, z_plane, y_px_start, y_px_stop = artefacts.get_start_stop(stim_start, stim_stop, frame_start, y_px, shape,
                                                                     settle_time)

    np.testing.assert_equal(frame, [])
    np.testing.assert_equal(z_plane, [])
    np.testing.assert_equal(y_px_start, [])
    np.testing.assert_equal(y_px_stop, [])


def test_get_start_stop_multiple_stims():
    stim_start = np.array([40., 160.])
    stim_stop = np.array([45., 165.])
    frame_start = np.arange(0, 200, 25)
    y_px = 200
    shape = (4, 2)
    settle_time = 0

    frame, z_plane, y_px_start, y_px_stop = artefacts.get_start_stop(stim_start, stim_stop, frame_start, y_px, shape,
                                                                     settle_time)

    np.testing.assert_equal(frame, [0, 3])
    np.testing.assert_equal(z_plane, [1, 0])
    np.testing.assert_equal(y_px_start, [120, 80])
    np.testing.assert_equal(y_px_stop, [160, 120])
