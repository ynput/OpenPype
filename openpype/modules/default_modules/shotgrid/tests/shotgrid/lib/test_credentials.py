import pytest
from assertpy import assert_that

import openpype.modules.default_modules.shotgrid.lib.credentials as sut


def test_missing_shotgrid_url():
    with pytest.raises(Exception) as ex:
        # arrange
        url = ""
        # act
        sut.get_shotgrid_hostname(url)
        # assert
        assert_that(ex).is_equal_to("Shotgrid url cannot be a null")


def test_full_shotgrid_url():
    # arrange
    url = "https://shotgrid.com/myinstance"
    # act
    actual = sut.get_shotgrid_hostname(url)
    # assert
    assert_that(actual).is_not_empty()
    assert_that(actual).is_equal_to("shotgrid.com")


def test_incomplete_shotgrid_url():
    # arrange
    url = "shotgrid.com/myinstance"
    # act
    actual = sut.get_shotgrid_hostname(url)
    # assert
    assert_that(actual).is_not_empty()
    assert_that(actual).is_equal_to("shotgrid.com")
