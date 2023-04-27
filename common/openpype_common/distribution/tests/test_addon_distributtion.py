import pytest
import attr
import tempfile

from common.openpype_common.distribution.addon_distribution import (
    AddonDownloader,
    OSAddonDownloader,
    HTTPAddonDownloader,
    AddonInfo,
    update_addon_state,
    UpdateState
)
from common.openpype_common.distribution.addon_info import UrlType


@pytest.fixture
def addon_downloader():
    addon_downloader = AddonDownloader()
    addon_downloader.register_format(UrlType.FILESYSTEM, OSAddonDownloader)
    addon_downloader.register_format(UrlType.HTTP, HTTPAddonDownloader)

    yield addon_downloader


@pytest.fixture
def http_downloader(addon_downloader):
    yield addon_downloader.get_downloader(UrlType.HTTP.value)


@pytest.fixture
def temp_folder():
    yield tempfile.mkdtemp()


@pytest.fixture
def sample_addon_info():
    addon_info = {
       "versions": {
            "1.0.0": {
                 "clientPyproject": {
                      "tool": {
                           "poetry": {
                            "dependencies": {
                             "nxtools": "^1.6",
                             "orjson": "^3.6.7",
                             "typer": "^0.4.1",
                             "email-validator": "^1.1.3",
                             "python": "^3.10",
                             "fastapi": "^0.73.0"
                            }
                       }
                  }
                 },
                 "hasSettings": True,
                 "clientSourceInfo": [
                     {
                         "type": "http",
                         "url": "https://drive.google.com/file/d/1TcuV8c2OV8CcbPeWi7lxOdqWsEqQNPYy/view?usp=sharing"  # noqa
                     },
                     {
                         "type": "filesystem",
                         "path": {
                             "windows": ["P:/sources/some_file.zip",
                                         "W:/sources/some_file.zip"],  # noqa
                             "linux": ["/mnt/srv/sources/some_file.zip"],
                             "darwin": ["/Volumes/srv/sources/some_file.zip"]
                         }
                     }
                 ],
                 "frontendScopes": {
                      "project": {
                       "sidebar": "hierarchy"
                      }
                 }
            }
       },
       "description": "",
       "title": "Slack addon",
       "name": "openpype_slack",
       "productionVersion": "1.0.0",
       "hash": "4be25eb6215e91e5894d3c5475aeb1e379d081d3f5b43b4ee15b0891cf5f5658"  # noqa
    }
    yield addon_info


def test_register(printer):
    addon_downloader = AddonDownloader()

    assert len(addon_downloader._downloaders) == 0, "Contains registered"

    addon_downloader.register_format(UrlType.FILESYSTEM, OSAddonDownloader)
    assert len(addon_downloader._downloaders) == 1, "Should contain one"


def test_get_downloader(printer, addon_downloader):
    assert addon_downloader.get_downloader(UrlType.FILESYSTEM.value), "Should find"  # noqa

    with pytest.raises(ValueError):
        addon_downloader.get_downloader("unknown"), "Shouldn't find"


def test_addon_info(printer, sample_addon_info):
    """Tests parsing of expected payload from v4 server into AadonInfo."""
    valid_minimum = {
        "name": "openpype_slack",
         "productionVersion": "1.0.0",
         "versions": {
             "1.0.0": {
                 "clientSourceInfo": [
                     {
                         "type": "filesystem",
                         "path": {
                             "windows": [
                                 "P:/sources/some_file.zip",
                                 "W:/sources/some_file.zip"],
                             "linux": [
                                 "/mnt/srv/sources/some_file.zip"],
                             "darwin": [
                                 "/Volumes/srv/sources/some_file.zip"]  # noqa
                         }
                     }
                 ]
             }
         }
    }

    assert AddonInfo.from_dict(valid_minimum), "Missing required fields"

    valid_minimum["versions"].pop("1.0.0")
    with pytest.raises(KeyError):
        assert not AddonInfo.from_dict(valid_minimum), "Must fail without version data"  # noqa

    valid_minimum.pop("productionVersion")
    assert not AddonInfo.from_dict(
        valid_minimum), "none if not productionVersion"  # noqa

    addon = AddonInfo.from_dict(sample_addon_info)
    assert addon, "Should be created"
    assert addon.name == "openpype_slack", "Incorrect name"
    assert addon.version == "1.0.0", "Incorrect version"

    with pytest.raises(TypeError):
        assert addon["name"], "Dict approach not implemented"

    addon_as_dict = attr.asdict(addon)
    assert addon_as_dict["name"], "Dict approach should work"


def test_update_addon_state(printer, sample_addon_info,
                            temp_folder, addon_downloader):
    """Tests possible cases of addon update."""
    addon_info = AddonInfo.from_dict(sample_addon_info)
    orig_hash = addon_info.hash

    addon_info.hash = "brokenhash"
    result = update_addon_state([addon_info], temp_folder, addon_downloader)
    assert result["openpype_slack_1.0.0"] == UpdateState.FAILED.value, \
        "Update should failed because of wrong hash"

    addon_info.hash = orig_hash
    result = update_addon_state([addon_info], temp_folder, addon_downloader)
    assert result["openpype_slack_1.0.0"] == UpdateState.UPDATED.value, \
        "Addon should have been updated"

    result = update_addon_state([addon_info], temp_folder, addon_downloader)
    assert result["openpype_slack_1.0.0"] == UpdateState.EXISTS.value, \
        "Addon should already exist"
