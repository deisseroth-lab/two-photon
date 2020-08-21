import artefacts
import numpy as np


def test_get_start_stop():
    stim_start = np.array([40.])
    stim_stop = np.array([45.])
    frame_start = np.array([0., 25., 50.])
    y_px = 200
    shape = (3, 1)
    settle_time = 0
    
    frame, z_plane, y_px_start, y_px_stop = artefacts.get_start_stop(stim_start, stim_stop, frame_start, y_px, shape, settle_time)
    
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
    
    frame, z_plane, y_px_start, y_px_stop = artefacts.get_start_stop(stim_start, stim_stop, frame_start, y_px, shape, settle_time)
    
    np.testing.assert_equal(frame, [1])
    np.testing.assert_equal(z_plane, [0])
    np.testing.assert_equal(y_px_start, [100])
    np.testing.assert_equal(y_px_stop, [150])
    
    
def test_get_start_stop_two_frame():
    stim_start = np.array([15.])
    stim_stop = np.array([45.])
    frame_start = np.array([0., 25., 50., 75.])
    y_px = 200
    shape = (2, 2)
    settle_time = 0
    
    frame, z_plane, y_px_start, y_px_stop = artefacts.get_start_stop(stim_start, stim_stop, frame_start, y_px, shape, settle_time)
    
    np.testing.assert_equal(frame, [0, 0])
    np.testing.assert_equal(z_plane, [0, 1])
    np.testing.assert_equal(y_px_start, [120, 0])
    np.testing.assert_equal(y_px_stop, [200, 160])

def test_get_start_stop_two_frame_settle():
    stim_start = np.array([15.])
    stim_stop = np.array([45.])
    frame_start = np.array([0., 25., 50., 75.])
    y_px = 200
    shape = (2, 2)
    settle_time = 5
    
    frame, z_plane, y_px_start, y_px_stop = artefacts.get_start_stop(stim_start, stim_stop, frame_start, y_px, shape, settle_time)
    
    np.testing.assert_equal(frame, [0, 0])
    np.testing.assert_equal(z_plane, [0, 1])
    np.testing.assert_equal(y_px_start, [100, 0])
    np.testing.assert_equal(y_px_stop, [200, 150])


def test_get_start_stop_two_frame_settle_no_second_frame():
    stim_start = np.array([15.])
    stim_stop = np.array([27.])
    frame_start = np.array([0., 25., 50., 75.])
    y_px = 200
    shape = (2, 2)
    settle_time = 5
    
    frame, z_plane, y_px_start, y_px_stop = artefacts.get_start_stop(stim_start, stim_stop, frame_start, y_px, shape, settle_time)
    
    np.testing.assert_equal(frame, [0])
    np.testing.assert_equal(z_plane, [0])
    np.testing.assert_equal(y_px_start, [100])
    np.testing.assert_equal(y_px_stop, [200])

def test_get_start_stop_two_frame_settle_no_frames():
    stim_start = np.array([50.])
    stim_stop = np.array([53.])
    frame_start = np.array([0., 25., 50., 75.])
    y_px = 200
    shape = (2, 2)
    settle_time = 5
    
    frame, z_plane, y_px_start, y_px_stop = artefacts.get_start_stop(stim_start, stim_stop, frame_start, y_px, shape, settle_time)
    
    np.testing.assert_equal(frame, [])
    np.testing.assert_equal(z_plane, [])
    np.testing.assert_equal(y_px_start, [])
    np.testing.assert_equal(y_px_stop, [])
    