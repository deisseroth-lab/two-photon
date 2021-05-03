""""Utility to update bad OME XML spec output by Bruker."""

from xml.etree import ElementTree as etree

import tifffile


class CorrectOmeXml(Exception):
    """TIFF file attributes not validated with Bruker OME spec correction."""


def correct_tiff(fname):
    """Update (in place) Bruker OME spec in a tiff stack master file."""
    with tifffile.TiffFile(fname, mode="r+b") as tif:
        original = tif.pages[0].tags["ImageDescription"].value
        corrected = correct_omexml(original)
        _ = tif.pages[0].tags["ImageDescription"].overwrite(tif, corrected)


def correct_omexml(omexml):
    """Update Bruker OME XML spec.

    The time dimension is incorrectly specified.  Two corrections are needed:
    - SizeT needs to indicate the number of time points present.
    - FirstT on each frame needs to be updated to indicate which time point it is
      Bruker has FirstT=0 for all files

    Uses for-loop and if-statement structure similar tifffile._series_ome.
    """
    root = etree.fromstring(omexml)
    current_timepoint = 0
    for element in root:
        if not element.tag.endswith("Image"):
            continue
        for pixels in element:
            if not pixels.tag.endswith("Pixels"):
                continue
            axes = "".join(reversed(pixels.attrib["DimensionOrder"]))
            if pixels.attrib["SizeZ"] == 1:
                # SizeZ=1 files are sometimes laid out differently -- need to check
                # this function does the right thing in those cases.
                raise CorrectOmeXml("correct_onexml is not validated with SizeZ=1")
            if axes != "TCZYX":
                # For now, punt if we get a format different than what we normally use.
                raise CorrectOmeXml(
                    "correct_onexml is not validated for axes=%s" % axes
                )
            for data in pixels:
                if data.tag.endswith("Channel"):
                    spp = int(data.attrib.get("SamplesPerPixel"))
                    if spp > 1:
                        # This could be incorporated with a little more work, but is not something
                        # typically done, so that work is deferred for now.
                        raise CorrectOmeXml(
                            "correct_onexml needs updating to handle SamplesPerPixel != 1"
                        )
                if not data.tag.endswith("TiffData"):
                    continue
                if data.attrib["FirstZ"] == "0":
                    current_timepoint += 1
                data.attrib["FirstT"] = str(current_timepoint - 1)
    for element in root:
        if not element.tag.endswith("Image"):
            continue
        for pixels in element:
            if not pixels.tag.endswith("Pixels"):
                continue
            pixels.attrib["SizeT"] = str(current_timepoint)
    return etree.tostring(root, encoding="unicode")
