import xmldiff.main

from two_photon import correct_omexml


def test_correct_omexml(testdata):
    original = (testdata / "correct_onexml.original.xml").read_text()
    corrected = correct_omexml.correct_omexml(original)
    expected = (testdata / "correct_onexml.expected.xml").read_text()

    diff = xmldiff.main.diff_texts(corrected, expected)
    assert not diff
