import os
from enum import Enum
from abc import abstractmethod
import attr
import logging
import requests
import platform
import shutil

from .file_handler import RemoteFileHandler
from .addon_info import AddonInfo


class UpdateState(Enum):
    EXISTS = "exists"
    UPDATED = "updated"
    FAILED = "failed"


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
    def download(cls, source, destination):
        """Returns url to downloaded addon zip file.

        Args:
            source (dict): {type:"http", "url":"https://} ...}
            destination (str): local folder to unzip
        Returns:
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
        if not RemoteFileHandler.check_integrity(addon_path,
                                                 addon_hash,
                                                 hash_type="sha256"):
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
    def download(cls, source, destination):
        # OS doesnt need to download, unzip directly
        addon_url = source["path"].get(platform.system().lower())
        if not os.path.exists(addon_url):
            raise ValueError("{} is not accessible".format(addon_url))
        return addon_url


class HTTPAddonDownloader(AddonDownloader):
    CHUNK_SIZE = 100000

    @classmethod
    def download(cls, source, destination):
        source_url = source["url"]
        cls.log.debug(f"Downloading {source_url} to {destination}")
        file_name = os.path.basename(destination)
        _, ext = os.path.splitext(file_name)
        if (ext.replace(".", '') not
                in set(RemoteFileHandler.IMPLEMENTED_ZIP_FORMATS)):
            file_name += ".zip"
        RemoteFileHandler.download_url(source_url,
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
    #        "hash": "4be25eb6215e91e5894d3c5475aeb1e379d081d3f5b43b4ee15b0891cf5f5658"})  # noqa
    #
    # http_addon = AddonInfo(
    #     **{"name": "openpype_slack",
    #        "version": "1.0.0",
    #        "addon_url": "https://drive.google.com/file/d/1TcuV8c2OV8CcbPeWi7lxOdqWsEqQNPYy/view?usp=sharing",  # noqa
    #        "type": UrlType.HTTP,
    #        "hash": "4be25eb6215e91e5894d3c5475aeb1e379d081d3f5b43b4ee15b0891cf5f5658"})  # noqa

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
    Returns:
        (dict): {"addon_full_name": UpdateState.value
            (eg. "exists"|"updated"|"failed")
    """
    if not log:
        log = logging.getLogger(__name__)

    download_states = {}
    for addon in addon_infos:
        full_name = "{}_{}".format(addon.name, addon.version)
        addon_dest = os.path.join(destination_folder, full_name)

        if os.path.isdir(addon_dest):
            log.debug(f"Addon version folder {addon_dest} already exists.")
            download_states[full_name] = UpdateState.EXISTS.value
            continue

        for source in addon.sources:
            download_states[full_name] = UpdateState.FAILED.value
            try:
                downloader = factory.get_downloader(source.type)
                zip_file_path = downloader.download(attr.asdict(source),
                                                    addon_dest)
                downloader.check_hash(zip_file_path, addon.hash)
                downloader.unzip(zip_file_path, addon_dest)
                download_states[full_name] = UpdateState.UPDATED.value
                break
            except Exception:
                log.warning(f"Error happened during updating {addon.name}",
                            exc_info=True)
                if os.path.isdir(addon_dest):
                    log.debug(f"Cleaning {addon_dest}")
                    shutil.rmtree(addon_dest)

    return download_states


def check_addons(server_endpoint, addon_folder, downloaders):
    """Main entry point to compare existing addons with those on server.

    Args:
        server_endpoint (str): url to v4 server endpoint
        addon_folder (str): local dir path for addons
        downloaders (AddonDownloader): factory of downloaders

    Raises:
        (RuntimeError) if any addon failed update
    """
    addons_info = get_addons_info(server_endpoint)
    result = update_addon_state(addons_info,
                                addon_folder,
                                downloaders)
    if UpdateState.FAILED.value in result.values():
        raise RuntimeError(f"Unable to update some addons {result}")


def cli(*args):
    raise NotImplementedError
