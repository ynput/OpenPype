import os
import sys
import copy
import tempfile


import attr
import pytest

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, "..", "..", "..", ".."))
sys.path.append(root_dir)

from common.ayon_common.distribution.downloaders import (
    DownloadFactory,
    OSDownloader,
    HTTPDownloader,
)
from common.ayon_common.distribution.control import (
    AyonDistribution,
    UpdateState,
)
from common.ayon_common.distribution.data_structures import (
    AddonInfo,
    UrlType,
)


@pytest.fixture
def download_factory():
    addon_downloader = DownloadFactory()
    addon_downloader.register_format(UrlType.FILESYSTEM, OSDownloader)
    addon_downloader.register_format(UrlType.HTTP, HTTPDownloader)

    yield addon_downloader


@pytest.fixture
def http_downloader(download_factory):
    yield download_factory.get_downloader(UrlType.HTTP.value)


@pytest.fixture
def temp_folder():
    yield tempfile.mkdtemp(prefix="ayon_test_")


@pytest.fixture
def sample_bundles():
    yield {
        "bundles": [
            {
                "name": "TestBundle",
                "createdAt": "2023-06-29T00:00:00.0+00:00",
                "installerVersion": None,
                "addons": {
                    "slack": "1.0.0"
                },
                "dependencyPackages": {},
                "isProduction": True,
                "isStaging": False
            }
        ],
        "productionBundle": "TestBundle",
        "stagingBundle": None
    }


@pytest.fixture
def sample_addon_info():
    yield {
        "name": "slack",
        "title": "Slack addon",
        "versions": {
            "1.0.0": {
                "hasSettings": True,
                "hasSiteSettings": False,
                "frontendScopes": {},
                "clientSourceInfo": [
                    {
                        "type": "server",
                        "filename": "client.zip"
                    }
                ],
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
                "clientSourceInfo": [
                    {
                        "type": "http",
                        "path": "https://drive.google.com/file/d/1TcuV8c2OV8CcbPeWi7lxOdqWsEqQNPYy/view?usp=sharing",  # noqa
                        "filename": "dummy.zip"
                    },
                    {
                        "type": "filesystem",
                        "path": {
                            "windows": "P:/sources/some_file.zip",
                            "linux": "/mnt/srv/sources/some_file.zip",
                            "darwin": "/Volumes/srv/sources/some_file.zip"
                        }
                    }
                ],
                "frontendScopes": {
                    "project": {
                        "sidebar": "hierarchy",
                    }
                },
                "hash": "4be25eb6215e91e5894d3c5475aeb1e379d081d3f5b43b4ee15b0891cf5f5658"  # noqa
            }
        },
        "description": ""
    }


def test_register(printer):
    download_factory = DownloadFactory()

    assert len(download_factory._downloaders) == 0, "Contains registered"

    download_factory.register_format(UrlType.FILESYSTEM, OSDownloader)
    assert len(download_factory._downloaders) == 1, "Should contain one"


def test_get_downloader(printer, download_factory):
    assert download_factory.get_downloader(UrlType.FILESYSTEM.value), "Should find"  # noqa

    with pytest.raises(ValueError):
        download_factory.get_downloader("unknown"), "Shouldn't find"


def test_addon_info(printer, sample_addon_info):
    """Tests parsing of expected payload from v4 server into AadonInfo."""
    valid_minimum = {
        "name": "slack",
        "versions": {
            "1.0.0": {
                "clientSourceInfo": [
                    {
                        "type": "filesystem",
                        "path": {
                            "windows": "P:/sources/some_file.zip",
                            "linux": "/mnt/srv/sources/some_file.zip",
                            "darwin": "/Volumes/srv/sources/some_file.zip"
                         }
                     }
                 ]
             }
         }
    }

    assert AddonInfo.from_dict(valid_minimum), "Missing required fields"

    addon = AddonInfo.from_dict(sample_addon_info)
    assert addon, "Should be created"
    assert addon.name == "slack", "Incorrect name"
    assert "1.0.0" in addon.versions, "Version is not in versions"

    with pytest.raises(TypeError):
        assert addon["name"], "Dict approach not implemented"

    addon_as_dict = attr.asdict(addon)
    assert addon_as_dict["name"], "Dict approach should work"


def _get_dist_item(dist_items, name, version):
    final_dist_info = next(
        (
            dist_info
            for dist_info in dist_items
            if (
                dist_info["addon_name"] == name
                and dist_info["addon_version"] == version
            )
        ),
        {}
    )
    return final_dist_info["dist_item"]


def test_update_addon_state(
    printer, sample_addon_info, temp_folder, download_factory, sample_bundles
):
    """Tests possible cases of addon update."""

    addon_version = list(sample_addon_info["versions"])[0]
    broken_addon_info = copy.deepcopy(sample_addon_info)

    # Cause crash because of invalid hash
    broken_addon_info["versions"][addon_version]["hash"] = "brokenhash"
    distribution = AyonDistribution(
        addon_dirpath=temp_folder,
        dependency_dirpath=temp_folder,
        dist_factory=download_factory,
        addons_info=[broken_addon_info],
        dependency_packages_info=[],
        bundles_info=sample_bundles
    )
    distribution.distribute()
    dist_items = distribution.get_addon_dist_items()
    slack_dist_item = _get_dist_item(
        dist_items,
        sample_addon_info["name"],
        addon_version
    )
    slack_state = slack_dist_item.state
    assert slack_state == UpdateState.UPDATE_FAILED, (
        "Update should have failed because of wrong hash")

    # Fix cache and validate if was updated
    distribution = AyonDistribution(
        addon_dirpath=temp_folder,
        dependency_dirpath=temp_folder,
        dist_factory=download_factory,
        addons_info=[sample_addon_info],
        dependency_packages_info=[],
        bundles_info=sample_bundles
    )
    distribution.distribute()
    dist_items = distribution.get_addon_dist_items()
    slack_dist_item = _get_dist_item(
        dist_items,
        sample_addon_info["name"],
        addon_version
    )
    assert slack_dist_item.state == UpdateState.UPDATED, (
        "Addon should have been updated")

    # Is UPDATED without calling distribute
    distribution = AyonDistribution(
        addon_dirpath=temp_folder,
        dependency_dirpath=temp_folder,
        dist_factory=download_factory,
        addons_info=[sample_addon_info],
        dependency_packages_info=[],
        bundles_info=sample_bundles
    )
    dist_items = distribution.get_addon_dist_items()
    slack_dist_item = _get_dist_item(
        dist_items,
        sample_addon_info["name"],
        addon_version
    )
    assert slack_dist_item.state == UpdateState.UPDATED, (
        "Addon should already exist")
