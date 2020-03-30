"""Library for parsing metadata files from Bruker scope."""

import json
import logging
import pathlib
import pprint
from xml.etree import ElementTree

logger = logging.getLogger(__file__)


class MetadataError(Exception):
    """Error while extracting metadata."""


def read(basename_input, dirname_output):
    """Read in metdata from XML files."""
    fname_xml = basename_input.with_suffix('.xml')
    fname_vr_xml = pathlib.Path(str(basename_input) + '_Cycle00001_VoltageRecording_001').with_suffix('.xml')
    fname_metadata = dirname_output / 'metadata.json'

    logger.info('Extracting metadata from xml files:\n%s\n%s', fname_xml, fname_vr_xml)

    mdata_root = ElementTree.parse(fname_xml).getroot()

    def state_value(key, type_fn=str):
        element = mdata_root.find(f'.//PVStateValue[@key="{key}"]')
        value = element.attrib['value']
        return type_fn(value)

    def indexed_value(key, index, type_fn=None, required=True):
        element = mdata_root.find(f'.//PVStateValue[@key="{key}"]/IndexedValue[@index="{index}"]')
        if not element:
            if required:
                raise MetadataError('Could not find required key:index of %s:%s' % (key, index))
            return None
        value = element.attrib['value']
        return type_fn(value)

    sequences = mdata_root.findall('Sequence')
    num_sequences = len(sequences)

    # Frames/sequence should be constant, except for perhaps the last frame.
    num_frames_per_sequence = len(sequences[0].findall('Frame'))

    if num_sequences == 1:
        num_frames = num_frames_per_sequence
        num_z_planes = 1
    else:
        # If the last sequence has a different number of frames, ignore it.
        num_frames_last_sequence = sequences[-1].findall('Frame')
        if num_frames_per_sequence != num_frames_last_sequence:
            logging.warning('Skipping final stack because it was found with fewer z-planes (%d, expected: %d).',
                            num_frames_last_sequence, num_frames_per_sequence)
            num_sequences -= 1
        num_frames = num_sequences
        num_z_planes = num_frames_per_sequence

    num_channels = len(mdata_root.find('Sequence/Frame').findall('File'))
    num_y_px = state_value('linesPerFrame', int)
    num_x_px = state_value('pixelsPerLine', int)

    laser_power = indexed_value('laserPower', 0, float, required=False)
    laser_wavelength = indexed_value('laserWavelength', 0, int, required=False)

    frame_period = state_value('framePeriod', float)
    optical_zoom = state_value('opticalZoom', float)

    voltage_root = ElementTree.parse(fname_vr_xml).getroot()

    channels = {}
    for signal in voltage_root.findall('Experiment/SignalList/VRecSignal'):
        channel_num = int(signal.find('Channel').text)
        channel_name = signal.find('Name').text
        enabled = signal.find('Enabled').text == 'true'
        channels[channel_num] = {'name': channel_name, 'enabled': enabled}

    metadata = {
        'layout': {
            'sequences': num_sequences,
            'frames_per_sequence': num_frames_per_sequence,
        },
        'size': {
            'frames': num_frames,
            'channels': num_channels,
            'z_planes': num_z_planes,
            'y_px': num_y_px,
            'x_px': num_x_px
        },
        'laser': {
            'power': laser_power,
            'wavelength': laser_wavelength
        },
        'period': frame_period,
        'optical_zoom': optical_zoom,
        'channels': channels,
    }

    with open(fname_metadata, 'w') as fout:
        json.dump(metadata, fout, indent=4, sort_keys=True)

    logger.info('The following metadata is written to: %s\n%s', fname_metadata, pprint.pformat(metadata))
    return metadata
