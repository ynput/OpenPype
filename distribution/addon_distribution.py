import os
from enum import Enum
from abc import abstractmethod
import attr
import logging
import requests

from distribution.file_handler import RemoteFileHandler


class UrlType(Enum):
    HTTP = "http"
    GIT = "git"
    FILESYSTEM = "filesystem"


@attr.s
class AddonInfo(object):
    """Object matching json payload from Server"""
    name = attr.ib(default=None)
    version = attr.ib(default=None)
    addon_url = attr.ib(default=None)
    type = attr.ib(default=None)
    hash = attr.ib(default=None)
    description = attr.ib(default=None)
    license = attr.ib(default=None)
    authors = attr.ib(default=None)


class AddonDownloader:
    log = logging.getLogger(__name__)

    def __init__(self):
        self._downloaders = {}

    def register_format(self, downloader_type, downloader):
        self._downloaders[downloader_type.value] = downloader

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
        if not os.path.exists(addon_path):
            raise ValueError(f"{addon_path} doesn't exist.")
        if addon_hash != RemoteFileHandler.calculate_md5(addon_path):
            raise ValueError(f"{addon_path} doesn't match expected hash.")

    @classmethod
    def unzip(cls, addon_zip_path, destination):
        """Unzips local 'addon_zip_path' to 'destination'.

        Args:
            addon_zip_path (str): local path to addon zip file
            destination (str): local folder to unzip
        """
        RemoteFileHandler.unzip(addon_zip_path, destination)
        os.remove(addon_zip_path)

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


class HTTPAddonDownloader(AddonDownloader):
    CHUNK_SIZE = 100000

    @classmethod
    def download(cls, addon_url, destination):
        cls.log.debug(f"Downloading {addon_url} to {destination}")
        file_name = os.path.basename(destination)
        _, ext = os.path.splitext(file_name)
        if (ext.replace(".", '') not
                in set(RemoteFileHandler.IMPLEMENTED_ZIP_FORMATS)):
            file_name += ".zip"
        RemoteFileHandler.download_url(addon_url,
                                       destination,
                                       filename=file_name)

        return os.path.join(destination, file_name)


def get_addons_info(server_endpoint):
    """Returns list of addon information from Server"""
    # TODO temp
    # addon_info = AddonInfo(
    #     **{"name": "openpype_slack",
    #        "version": "1.0.0",
    #        "addon_url": "c:/projects/openpype_slack_1.0.0.zip",
    #        "type": UrlType.FILESYSTEM,
    #        "hash": "4f6b8568eb9dd6f510fd7c4dcb676788"})  # noqa
    #
    # http_addon = AddonInfo(
    #     **{"name": "openpype_slack",
    #        "version": "1.0.0",
    #        "addon_url": "https://drive.google.com/file/d/1TcuV8c2OV8CcbPeWi7lxOdqWsEqQNPYy/view?usp=sharing",  # noqa
    #        "type": UrlType.HTTP,
    #        "hash": "4f6b8568eb9dd6f510fd7c4dcb676788"})  # noqa

    response = requests.get(server_endpoint)
    if not response.ok:
        raise Exception(response.text)

    addons_info = []
    for addon in response.json():
        addons_info.append(AddonInfo(**addon))
    return addons_info


def update_addon_state(addon_infos, destination_folder, factory,
                       log=None):
    """Loops through all 'addon_infos', compares local version, unzips.

    Loops through server provided list of dictionaries with information about
    available addons. Looks if each addon is already present and deployed.
    If isn't, addon zip gets downloaded and unzipped into 'destination_folder'.
    Args:
        addon_infos (list of AddonInfo)
        destination_folder (str): local path
        factory (AddonDownloader): factory to get appropriate downloader per
            addon type
        log (logging.Logger)
    """
    if not log:
        log = logging.getLogger(__name__)

    for addon in addon_infos:
        full_name = "{}_{}".format(addon.name, addon.version)
        addon_dest = os.path.join(destination_folder, full_name)

        if os.path.isdir(addon_dest):
            log.debug(f"Addon version folder {addon_dest} already exists.")
            continue

        try:
            downloader = factory.get_downloader(addon.type)
            zip_file_path = downloader.download(addon.addon_url, addon_dest)
            downloader.check_hash(zip_file_path, addon.hash)
            downloader.unzip(zip_file_path, addon_dest)
        except Exception:
            log.warning(f"Error happened during updating {addon.name}",
                        exc_info=True)


def check_addons(server_endpoint, addon_folder, downloaders):
    """Main entry point to compare existing addons with those on server."""
    addons_info = get_addons_info(server_endpoint)
    update_addon_state(addons_info,
                       addon_folder,
                       downloaders)


def cli(args):
    addon_folder = "c:/projects/testing_addons/pypeclub/openpype/addons"

    downloader_factory = AddonDownloader()
    downloader_factory.register_format(UrlType.FILESYSTEM, OSAddonDownloader)
    downloader_factory.register_format(UrlType.HTTP, HTTPAddonDownloader)

    test_endpoint = "https://34e99f0f-f987-4715-95e6-d2d88caa7586.mock.pstmn.io/get_addons_info"  # noqa
    if os.environ.get("OPENPYPE_SERVER"):  # TODO or from keychain
        server_endpoint = os.environ.get("OPENPYPE_SERVER") + "get_addons_info"
    else:
        server_endpoint = test_endpoint

    check_addons(server_endpoint, addon_folder, downloader_factory)
