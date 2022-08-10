import os
from enum import Enum
from zipfile import ZipFile
from abc import abstractmethod

import attr

from openpype.lib.path_tools import sha256sum
from openpype.lib import PypeLogger

log = PypeLogger().get_logger(__name__)


class UrlType(Enum):
    HTTP = {}
    GIT = {}
    OS = {}


@attr.s
class AddonInfo(object):
    """Object matching json payload from Server"""
    name = attr.ib(default=None)
    version = attr.ib(default=None)
    addon_url = attr.ib(default=None)
    type = attr.ib(default=None)
    hash = attr.ib(default=None)


class AddonDownloader:

    def __init__(self):
        self._downloaders = {}

    def register_format(self, downloader_type, downloader):
        self._downloaders[downloader_type] = downloader

    def get_downloader(self, downloader_type):
        downloader = self._downloaders.get(downloader_type)
        if not downloader:
            raise ValueError(f"{downloader_type} not implemented")
        return downloader()

    @classmethod
    @abstractmethod
    def download(cls, addon_url, destination):
        """Returns url to downloaded addon zip file.

        Args:
            addon_url (str): http or OS or any supported protocol url to addon
                zip file
            destination (str): local folder to unzip
        Retursn:
            (str) local path to addon zip file
        """
        pass

    @classmethod
    def check_hash(cls, addon_path, addon_hash):
        """Compares 'hash' of downloaded 'addon_url' file.

        Args:
            addon_path (str): local path to addon zip file
            addon_hash (str): sha256 hash of zip file
        Raises:
            ValueError if hashes doesn't match
        """
        if addon_hash != sha256sum(addon_path):
            raise ValueError(
                "{} doesn't match expected hash".format(addon_path))

    @classmethod
    def unzip(cls, addon_path, destination):
        """Unzips local 'addon_path' to 'destination'.

        Args:
            addon_path (str): local path to addon zip file
            destination (str): local folder to unzip
        """
        addon_file_name = os.path.basename(addon_path)
        addon_base_file_name, _ = os.path.splitext(addon_file_name)
        with ZipFile(addon_path, "r") as zip_ref:
            log.debug(f"Unzipping {addon_path} to {destination}.")
            zip_ref.extractall(
                os.path.join(destination, addon_base_file_name))

    @classmethod
    def remove(cls, addon_url):
        pass


class OSAddonDownloader(AddonDownloader):

    @classmethod
    def download(cls, addon_url, destination):
        # OS doesnt need to download, unzip directly
        if not os.path.exists(addon_url):
            raise ValueError("{} is not accessible".format(addon_url))
        return addon_url


def get_addons_info():
    """Returns list of addon information from Server"""
    # TODO temp
    addon_info = AddonInfo(
        **{"name": "openpype_slack",
           "version": "1.0.0",
           "addon_url": "c:/projects/openpype_slack_1.0.0.zip",
           "type": UrlType.OS,
           "hash": "4be25eb6215e91e5894d3c5475aeb1e379d081d3f5b43b4ee15b0891cf5f5658"})  # noqa

    return [addon_info]


def update_addon_state(addon_infos, destination_folder, factory):
    """Loops through all 'addon_infos', compares local version, unzips.

    Loops through server provided list of dictionaries with information about
    available addons. Looks if each addon is already present and deployed.
    If isn't, addon zip gets downloaded and unzipped into 'destination_folder'.
    Args:
        addon_infos (list of AddonInfo)
        destination_folder (str): local path
        factory (AddonDownloader): factory to get appropriate downloader per
            addon type
    """
    for addon in addon_infos:
        full_name = "{}_{}".format(addon.name, addon.version)
        addon_url = os.path.join(destination_folder, full_name)

        if os.path.isdir(addon_url):
            log.debug(f"Addon version folder {addon_url} already exists.")
            continue

        downloader = factory.get_downloader(addon.type)
        downloader.download(addon.addon_url, destination_folder)


def cli(args):
    addon_folder = "c:/Users/petrk/AppData/Local/pypeclub/openpype/addons"

    downloader_factory = AddonDownloader()
    downloader_factory.register_format(UrlType.OS, OSAddonDownloader)

    print(update_addon_state(get_addons_info(), addon_folder,
                             downloader_factory))
    print(sha256sum("c:/projects/openpype_slack_1.0.0.zip"))


