import pytest
import attr
import tempfile

from distribution.addon_distribution import (
    AddonDownloader,
    UrlType,
    OSAddonDownloader,
    HTTPAddonDownloader,
    AddonInfo,
    update_addon_state,
    UpdateState
)


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
        "name": "openpype_slack",
        "version": "1.0.0",
        "sources": [
            {
                "type": "http",
                "url": "https://drive.google.com/file/d/1TcuV8c2OV8CcbPeWi7lxOdqWsEqQNPYy/view?usp=sharing"  # noqa
            },
            {
                "type": "filesystem",
                "path": {
                    "windows": ["P:/sources/some_file.zip", "W:/sources/some_file.zip"],  # noqa
                    "linux": ["/mnt/srv/sources/some_file.zip"],
                    "darwin": ["/Volumes/srv/sources/some_file.zip"]
                }
            }
        ],
        "hash": "4be25eb6215e91e5894d3c5475aeb1e379d081d3f5b43b4ee15b0891cf5f5658"
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
    valid_minimum = {"name": "openpype_slack", "version": "1.0.0"}

    assert AddonInfo(**valid_minimum), "Missing required fields"
    assert AddonInfo(name=valid_minimum["name"],
                     version=valid_minimum["version"]), \
        "Missing required fields"

    with pytest.raises(TypeError):
        # TODO should be probably implemented
        assert AddonInfo(valid_minimum), "Wrong argument format"

    addon = AddonInfo(**sample_addon_info)
    assert addon, "Should be created"
    assert addon.name == "openpype_slack", "Incorrect name"
    assert addon.version == "1.0.0", "Incorrect version"

    with pytest.raises(TypeError):
        assert addon["name"], "Dict approach not implemented"

    addon_as_dict = attr.asdict(addon)
    assert addon_as_dict["name"], "Dict approach should work"

    with pytest.raises(AttributeError):
        # TODO should be probably implemented as . not dict
        first_source = addon.sources[0]
        assert first_source.type == "http", "Not implemented"


def test_update_addon_state(printer, sample_addon_info,
                            temp_folder, addon_downloader):
    addon_info = AddonInfo(**sample_addon_info)
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
