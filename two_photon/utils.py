"""Methods useful to multiple stages of the pipeline."""
from xml.etree import ElementTree


def frame_period(layout):
    xml_path = layout.raw_xml_path()
    mdata_root = ElementTree.parse(xml_path).getroot()
    element = mdata_root.find('.//PVStateValue[@key="framePeriod"]')
    return float(element.attrib["value"])
