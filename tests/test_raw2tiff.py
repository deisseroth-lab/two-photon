from pathlib import Path

import pytest

from two_photon import raw2tiff


def test_determine_ripper_54(tmp_path):
    xml = tmp_path / "blah.env"
    xml.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<Environment version="5.4.64.700" date="6/16/2020 1:07:05 AM">
</Environment>
"""
    )

    actual = raw2tiff.determine_ripper(tmp_path, Path("/toplevel"))
    expected = Path("/toplevel/Prairie View 5.4/Utilities/Image-Block Ripping Utility.exe")
    assert actual == expected


def test_determine_ripper_55(tmp_path):
    xml = tmp_path / "blah.env"
    xml.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<Environment version="5.5.64.200" date="8/19/2020 1:54:33 PM">
</Environment>
"""
    )

    actual = raw2tiff.determine_ripper(tmp_path, Path("/toplevel"))
    expected = Path("/toplevel/Prairie View 5.5/Utilities/Image-Block Ripping Utility.exe")
    assert actual == expected


def test_determine_ripper_bad_path():
    with pytest.raises(raw2tiff.RippingError):
        raw2tiff.determine_ripper(Path("/nonexistant"), Path("/toplevel"))


def test_determine_ripper_missing_metadata(tmp_path):
    with pytest.raises(raw2tiff.RippingError):
        raw2tiff.determine_ripper(tmp_path, Path("/toplevel"))


def test_determine_ripper_multiple_metadata(tmp_path):
    xml = tmp_path / "blah.env"
    xml.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<Environment version="5.4.64.700" date="6/16/2020 1:07:05 AM">
</Environment>
"""
    )
    xml = tmp_path / "blah2.env"
    xml.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<Environment version="5.4.64.700" date="6/16/2020 1:07:05 AM">
</Environment>
"""
    )
    with pytest.raises(raw2tiff.RippingError):
        raw2tiff.determine_ripper(tmp_path, Path("/toplevel"))


def test_determine_ripper_bad_version(tmp_path):
    xml = tmp_path / "blah.env"
    xml.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<Environment version="5.64.200" date="8/19/2020 1:54:33 PM">
</Environment>
"""
    )
    with pytest.raises(raw2tiff.RippingError):
        raw2tiff.determine_ripper(tmp_path, Path("/toplevel"))
