import os
from enum import Enum
from abc import abstractmethod
import attr
import logging
import requests
import platform
import shutil

from .file_handler import RemoteFileHandler
from .addon_info import AddonInfo, UrlType, DependencyItem
import ayon_api


class UpdateState(Enum):
    EXISTS = "exists"
    UPDATED = "updated"
    FAILED_MISSING_SOURCE = "failed_no_download_source"
    FAILED = "failed"


DEPENDENCIES_ENDPOINT = "dependencies"
ADDON_ENDPOINT = "addons?details=1"


def get_local_dir(*subdirs):
    if not subdirs:
        raise RuntimeError("Must fill dir_name if nothing else provided!")

    local_dir = os.path.join(
        appdirs.user_data_dir("openpype", "pypeclub"),
        *subdirs
    )
    if not os.path.isdir(local_dir):
        try:
            os.makedirs(local_dir)
        except Exception:  # TODO fix exception
            raise RuntimeError(f"Cannot create {local_dir}")

    return local_dir


def get_addons_dir():
    addons_dir = os.environ.get("AYON_ADDONS_DIR")
    if not addons_dir:
        addons_dir = get_local_dir("addons")
    return addons_dir


def get_dependencies_dir():
    dependencies_dir = os.environ.get("AYON_DEPENDENCIES_DIR")
    if not dependencies_dir:
        dependencies_dir = get_local_dir("dependency_packages")
    return dependencies_dir


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
                                       filename=file_name,
                                       headers=data.get("headers"))

        return os.path.join(destination_dir, file_name)


class AyonServerDownloader(AddonDownloader):
    """Downloads static resource file from v4 Server.

    Expects filled env var AYON_SERVER_URL.
    """

    CHUNK_SIZE = 8192

    @classmethod
    def download(cls, source, destination_dir, data=None):
        filename = source["filename"]
        cls.log.debug(f"Downloading {filename} to {destination_dir}")

        if not os.environ.get("AYON_SERVER_URL"):
            raise RuntimeError(f"Must have AYON_SERVER_URL env var!")

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


def get_addons_info(server_endpoint=None):
    """Returns list of addon information from Server

    Arg:
        server_endpoint (str): addons?details=1

    Returns:
        List[AddonInfo]: List of metadata for addons sent from server,
            parsed in AddonInfo objects
    """
    if not server_endpoint:
        addons_list = get_addons_info_as_dict()
    else:
        response = ayon_api.get(server_endpoint)
        if response.status != 200:
            raise Exception(response.content)
        addons_list = response.data["addons"]

    addons_info = []
    for addon in addons_list:
        addon_info = AddonInfo.from_dict(addon)
        if addon_info:
            addons_info.append(AddonInfo.from_dict(addon))
    return addons_info


def get_addons_info_as_dict():
    response = ayon_api.get(ADDON_ENDPOINT)
    if response.status != 200:
        raise Exception(response.content)

    return response.data["addons"]


def get_dependency_info(server_endpoint=None):
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
    if not server_endpoint:
        server_endpoint = DEPENDENCIES_ENDPOINT

    response = ayon_api.get(server_endpoint)
    if response.status != 200:
        raise Exception(response.content)

    data = response.data
    dependency_list = data["packages"]
    production_package_name = data["productionPackage"]

    for dependency in dependency_list:
        dependency["productionPackage"] = production_package_name
        dependency_package = DependencyItem.from_dict(dependency)
        if (dependency_package and
                dependency_package.name == production_package_name):
            return dependency_package


def update_addon_state(addon_infos, destination_folder, factory, token,
                       log=None):
    """Loops through all 'addon_infos', compares local version, unzips.

    Loops through server provided list of dictionaries with information about
    available addons. Looks if each addon is already present and deployed.
    If isn't, addon zip gets downloaded and unzipped into 'destination_folder'.
    Args:
        addon_infos (list of AddonInfo)
        destination_folder (str): local path
            ('...AppData/Local/pypeclub/openpype/addons')
        factory (AddonDownloader): factory to get appropriate downloader per
            addon type
        token (str): authorization token
        log (logging.Logger)
    Returns:
        (dict): {"addon_full_name": UpdateState}
    """
    if not log:
        log = logging.getLogger(__name__)

    data = {"headers": {"Authorization": f"Bearer {token}"}}
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
                                                    destination_folder,
                                                    data=data)
                downloader.check_hash(zip_file_path, addon.hash)
                downloader.unzip(zip_file_path, destination_folder)
                download_states[full_name] = UpdateState.UPDATED
                break
            except Exception:
                log.warning(f"Error happened during updating {addon.name}",
                            exc_info=True)
                if os.path.isdir(addon_dest):
                    log.debug(f"Cleaning {addon_dest}")
                    shutil.rmtree(addon_dest)

    return download_states


def check_addons(server_endpoint, addon_folder, downloaders, token):
    """Main entry point to compare existing addons with those on server.

    Args:
        server_endpoint (str): url to v4 server endpoint
        addon_folder (str): local dir path for addons
        downloaders (AddonDownloader): factory of downloaders
        token (str): authentication token
    Raises:
        (RuntimeError) if any addon failed update
    """
    addons_info = get_addons_info(server_endpoint)
    result = update_addon_state(addons_info,
                                addon_folder,
                                downloaders,
                                token=token)
    failed = {}
    ok_states = [UpdateState.UPDATED, UpdateState.EXISTS]
    ok_states.append(UpdateState.FAILED_MISSING_SOURCE)  # TODO remove test only  noqa
    for addon_name, res_val in result.items():
        if res_val not in ok_states:
            failed[addon_name] = res_val.value

    if failed:
        raise RuntimeError(f"Unable to update some addons {failed}")


def check_venv(server_endpoint, local_venv_dir, downloaders, token, log=None):
    """Main entry point to compare existing addons with those on server.

    Args:
        server_endpoint (str): url to v4 server endpoint
        local_venv_dir (str): local dir path for addons
        downloaders (AddonDownloader): factory of downloaders
        token (str): authorization token

    Raises:
        (RuntimeError) if required production package failed update
    """
    if not log:
        log = logging.getLogger(__name__)

    package = get_dependency_info(server_endpoint)
    if not package:
        raise RuntimeError("Server doesn't contain dependency package!")

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

    server_endpoint = "{}/{}/{}".format(
        server_endpoint, package.name, package.platform)
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
    addon_downloader.register_format(UrlType.FILESYSTEM, OSAddonDownloader)
    addon_downloader.register_format(UrlType.HTTP, HTTPAddonDownloader)
    addon_downloader.register_format(UrlType.SERVER, AyonServerDownloader)
    return addon_downloader


def cli(*args):
    raise NotImplementedError
