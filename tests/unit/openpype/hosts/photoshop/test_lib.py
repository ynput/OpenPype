import pytest

from openpype.hosts.photoshop.lib import clean_subset_name

"""
Tests cleanup of unused layer placeholder ({layer}) from subset name.
Layer differentiation might be desired in subset name, but in some cases it
might be used (in `auto_image` - only single image without layer diff.,
single image instance created without toggled use of subset name etc.)
"""


def test_no_layer_placeholder():
    clean_subset = clean_subset_name("imageMain")
    assert "imageMain" == clean_subset


@pytest.mark.parametrize("subset_name",
                         ["imageMain{Layer}",
                          "imageMain_{layer}",  # trailing _
                          "image{Layer}Main",
                          "image{LAYER}Main"])
def test_not_used_layer_placeholder(subset_name):
    clean_subset = clean_subset_name(subset_name)
    assert "imageMain" == clean_subset
