import os
from enum import Enum
from abc import abstractmethod
import attr
import logging
import requests
import platform
import shutil
import urllib.parse as urlparse

from .file_handler import RemoteFileHandler
from .addon_info import AddonInfo, UrlType, DependencyItem
from common.openpype_common.connection.credentials import load_token


class UpdateState(Enum):
    EXISTS = "exists"
    UPDATED = "updated"
    FAILED_MISSING_SOURCE = "failed_no_download_source"
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
    def download(cls, source, destination_dir, data=None):
        """Returns url to downloaded addon zip file.

        Args:
            source (dict): {type:"http", "url":"https://} ...}
            destination_dir (str): local folder to unzip
            data (dict): dynamic values, different per downloader type
        Returns:
            (str) local path to addon zip file
        """
        pass

    @classmethod
    def check_hash(cls, addon_path, addon_hash, hash_type="sha256"):
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
                                                 hash_type=hash_type):
            raise ValueError(f"{addon_path} doesn't match expected hash.")

    @classmethod
    def unzip(cls, addon_zip_path, destination_dir):
        """Unzips local 'addon_zip_path' to 'destination'.

        Args:
            addon_zip_path (str): local path to addon zip file
            destination (str): local folder to unzip
        """
        RemoteFileHandler.unzip(addon_zip_path, destination_dir)
        os.remove(addon_zip_path)

    @classmethod
    def remove(cls, addon_url):
        pass


class OSAddonDownloader(AddonDownloader):

    @classmethod
    def download(cls, source, destination_dir, data=None):
        # OS doesnt need to download, unzip directly
        addon_url = source["path"].get(platform.system().lower())
        if not os.path.exists(addon_url):
            raise ValueError("{} is not accessible".format(addon_url))
        return addon_url


class HTTPAddonDownloader(AddonDownloader):
    CHUNK_SIZE = 100000

    @classmethod
    def download(cls, source, destination_dir, data=None):
        source_url = source["url"]
        cls.log.debug(f"Downloading {source_url} to {destination_dir}")
        file_name = os.path.basename(destination_dir)
        _, ext = os.path.splitext(file_name)
        if (ext.replace(".", '') not
                in set(RemoteFileHandler.IMPLEMENTED_ZIP_FORMATS)):
            file_name += ".zip"
        RemoteFileHandler.download_url(source_url,
                                       destination_dir,
                                       filename=file_name)

        return os.path.join(destination_dir, file_name)


class DependencyDownloader(AddonDownloader):
    """Downloads static resource file from v4 Server.

    Expects filled env var OPENPYPE_SERVER_URL.
    """
    CHUNK_SIZE = 8192

    @classmethod
    def download(cls, source, destination_dir, data=None):
        filename = source["filename"]
        cls.log.debug(f"Downloading {filename} to {destination_dir}")

        if not os.environ.get("OPENPYPE_SERVER_URL"):
            raise RuntimeError(f"Must have OPENPYPE_SERVER_URL env var!")

        file_name = os.path.basename(filename)
        _, ext = os.path.splitext(file_name)
        if (ext.replace(".", '') not
                in set(RemoteFileHandler.IMPLEMENTED_ZIP_FORMATS)):
            file_name += ".zip"

        session = requests.Session()
        session.headers.update({
            "Content-Type": "application/octet-steam",
            "Authorization": "Bearer " + data["token"]
        })
        destination_path = os.path.join(destination_dir, file_name)
        with session.get(data["server_endpoint"], stream=True) as r:
            r.raise_for_status()
            with open(destination_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=cls.CHUNK_SIZE):
                    f.write(chunk)

        return destination_path


def get_addons_info(server_endpoint):
    """Returns list of addon information from Server"""
    response = requests.get(server_endpoint)
    if not response.ok:
        raise Exception(response.text)

    addons_info = []
    addons_list = response.json()["addons"]
    for addon in addons_list:
        addon_info = AddonInfo.from_dict(addon)
        if addon_info:
            addons_info.append(AddonInfo.from_dict(addon))
    return addons_info


def get_dependency_info(server_endpoint):
    """Returns info about currently used dependency package.

    Dependency package means .venv created from all activated addons from the
    server (plus libraries for core Tray app TODO confirm).
    This package needs to be downloaded, unpacked and added to sys.path for
    Tray app to work.
    Args:
        server_endpoint (str): url to server
    Returns:
        (DependencyItem) or None if no production_package_name found
    """
    response = requests.get(server_endpoint)
    if not response.ok:
        raise Exception(response.text)

    response_json = response.json()
    dependency_list = response_json["packages"]
    production_package_name = response_json["productionPackage"]
    for dependency in dependency_list:
        dependency["productionPackage"] = production_package_name
        dependency_package = DependencyItem.from_dict(dependency)
        if (dependency_package and
                dependency_package.name == production_package_name):
            return dependency_package


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
        log.debug(f"Checking {full_name} in {addon_dest}")

        if os.path.isdir(addon_dest):
            log.debug(f"Addon version folder {addon_dest} already exists.")
            download_states[full_name] = UpdateState.EXISTS
            continue

        if not addon.sources:
            log.debug(f"Addon doesn't have any sources to download from.")
            failed_state = UpdateState.FAILED_MISSING_SOURCE
            download_states[full_name] = failed_state
            continue

        for source in addon.sources:
            download_states[full_name] = UpdateState.FAILED
            try:
                downloader = factory.get_downloader(source.type)
                zip_file_path = downloader.download(attr.asdict(source),
                                                    addon_dest)
                downloader.check_hash(zip_file_path, addon.hash)
                downloader.unzip(zip_file_path)
                download_states[full_name] = UpdateState.UPDATED
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
    failed = {}
    ok_states = [UpdateState.UPDATED, UpdateState.EXISTS]
    ok_states.append(UpdateState.FAILED_MISSING_SOURCE)  # TODO remove test only  noqa
    for addon_name, res_val in result.items():
        if res_val not in ok_states:
            failed[addon_name] = res_val.value

    if failed:
        raise RuntimeError(f"Unable to update some addons {failed}")


def check_venv(server_endpoint, local_venv_dir, downloaders, log=None):
    """Main entry point to compare existing addons with those on server.

    Args:
        server_endpoint (str): url to v4 server endpoint
        local_venv_dir (str): local dir path for addons
        downloaders (AddonDownloader): factory of downloaders

    Raises:
        (RuntimeError) if required production package failed update
    """
    if not log:
        log = logging.getLogger(__name__)

    package = get_dependency_info(server_endpoint)
    venv_dest_dir = os.path.join(local_venv_dir, package.name)
    log.debug(f"Checking {package.name} in {local_venv_dir}")

    if os.path.isdir(venv_dest_dir):
        log.debug(f"Venv folder {venv_dest_dir} already exists.")
        return

    os.makedirs(venv_dest_dir)

    if not package.sources:
        msg = f"Package {package.name} doesn't have any "\
               "sources to download from."
        raise RuntimeError(msg)

    parsed_uri = urlparse.urlparse(server_endpoint)
    server_url = '{uri.scheme}://{uri.netloc}'.format(uri=parsed_uri)
    token = load_token(server_url)
    server_endpoint = "{}/api/dependencies/{}/{}".format(
        server_url, package.name, package.platform)
    data = {"server_endpoint": server_endpoint,
            "token": token}

    for source in package.sources:
        try:
            downloader = downloaders.get_downloader(source.type)
            zip_file_path = downloader.download(attr.asdict(source),
                                                venv_dest_dir,
                                                data)
            downloader.check_hash(zip_file_path, package.checksum, "md5")
            downloader.unzip(zip_file_path, venv_dest_dir)
            break
        except Exception:
            log.warning(f"Error happened during updating {package.name}",
                        exc_info=True)
            if os.path.isdir(venv_dest_dir):
                log.debug(f"Cleaning {venv_dest_dir}")
                shutil.rmtree(venv_dest_dir)
            raise RuntimeError(f"Unable to download {package.name}")


def default_addon_downloader():
    addon_downloader = AddonDownloader()
    addon_downloader.register_format(UrlType.FILESYSTEM,
                                     OSAddonDownloader)
    addon_downloader.register_format(UrlType.HTTP,
                                     HTTPAddonDownloader)
    addon_downloader.register_format(UrlType.SERVER,
                                     DependencyDownloader)

    return addon_downloader


def cli(*args):
    raise NotImplementedError
