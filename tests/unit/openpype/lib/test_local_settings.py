import pytest
from openpype.lib.local_settings import parse_set_url, parse_get_url


def test_parse_set_url_none():
    assert (None, None, None, None) == parse_set_url(None)
    assert (None, None, None, None) == parse_get_url(None)


def test_parse_set_url_no_location_no_location():
    with pytest.raises(ValueError):
        parse_set_url("foo/bar=111")
        parse_get_url("foo/bar=111")


def test_parse_set_url_not_implemented_location():
    with pytest.raises(ValueError):
        parse_set_url("not_implemented:/file/environment/foo/bar=111")
        parse_get_url("not_implemented:/file/environment/foo/bar=111")


def test_parse_set_url_no_key():
    with pytest.raises(ValueError):
        parse_set_url("keyring://=111")
        parse_get_url("keyring://foo/")


def test_parse_set_url_no_path():
    assert ("keyring", "", "bar", "111") == parse_set_url("keyring://bar=111")
    assert ("keyring", "", "bar", None) == parse_get_url("keyring://bar")


def test_parse_set_url_proper():
    assert ("keyring", "file/environment", "bar", "111") == parse_set_url("keyring://file/environment/bar=111")  # noqa
    assert ("keyring", "file/environment", "bar", None) == parse_get_url("keyring://file/environment/bar")  # noqa
