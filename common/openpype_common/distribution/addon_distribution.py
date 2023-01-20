import os
from enum import Enum
from abc import abstractmethod
import attr
import logging
import platform
import shutil

import appdirs
import ayon_api

from .file_handler import RemoteFileHandler
from .addon_info import (
    AddonInfo,
    UrlType,
    DependencyItem,
    ServerResourceSource,
)


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
        os.environ["AYON_ADDONS_DIR"] = addons_dir
    return addons_dir


def get_dependencies_dir():
    dependencies_dir = os.environ.get("AYON_DEPENDENCIES_DIR")
    if not dependencies_dir:
        dependencies_dir = get_local_dir("dependency_packages")
        os.environ["AYON_DEPENDENCIES_DIR"] = dependencies_dir
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
    def download(cls, source, destination_dir, data):
        """Returns url to downloaded addon zip file.

        Args:
            source (dict): {type:"http", "url":"https://} ...}
            destination_dir (str): local folder to unzip
            data (dict): More information about download content. Always have
                'type' key in.

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
    def download(cls, source, destination_dir, data):
        # OS doesnt need to download, unzip directly
        addon_url = source["path"].get(platform.system().lower())
        if not os.path.exists(addon_url):
            raise ValueError("{} is not accessible".format(addon_url))
        return addon_url


class HTTPAddonDownloader(AddonDownloader):
    CHUNK_SIZE = 100000

    @classmethod
    def download(cls, source, destination_dir, data):
        source_url = source["url"]
        cls.log.debug(f"Downloading {source_url} to {destination_dir}")
        filename = source.get("filename")
        headers = source.get("headers")
        if not filename:
            filename = os.path.basename(source_url)
            basename, ext = os.path.splitext(filename)
            allowed_exts = set(RemoteFileHandler.IMPLEMENTED_ZIP_FORMATS)
            if ext.replace(".", "") not in allowed_exts:
                filename = basename + ".zip"

        RemoteFileHandler.download_url(
            source_url,
            destination_dir,
            filename,
            headers=headers
        )

        return os.path.join(destination_dir, filename)


class AyonServerDownloader(AddonDownloader):
    """Downloads static resource file from v4 Server.

    Expects filled env var AYON_SERVER_URL.
    """

    CHUNK_SIZE = 8192

    @classmethod
    def download(cls, source, destination_dir, data):
        filename = source["filename"]

        cls.log.debug(f"Downloading {filename} to {destination_dir}")

        _, ext = os.path.splitext(filename)
        clear_ext = ext.lower().replace(".", "")
        valid_exts = set(RemoteFileHandler.IMPLEMENTED_ZIP_FORMATS)
        if clear_ext not in valid_exts:
            raise ValueError(
                "Invalid file extension \"{}\". Expected {}".format(
                    clear_ext, ", ".join(valid_exts)
                ))

        # dst_filepath = os.path.join(destination_dir, filename)
        if data["type"] == "dependency_package":
            # TODO replace with 'download_dependency_package'
            #   when available/fixed in 'ayon_api'
            return ayon_api.download_dependency_package(
                data["name"],
                destination_dir,
                filename,
                platform_name=data["platform"],
                chunk_size=cls.CHUNK_SIZE
            )

        if data["type"] == "addon":
            # TODO replace with 'download_addon_private_file'
            #   when available/fixed in 'ayon_api'
            return ayon_api.download_addon_private_file(
                data["name"],
                data["version"],
                filename,
                destination_dir,
                chunk_size=cls.CHUNK_SIZE
            )

        raise ValueError(f"Unknown type to download \"{data['type']}\"")


def get_addons_info():
    """Returns list of addon information from Server

    Returns:
        List[AddonInfo]: List of metadata for addons sent from server,
            parsed in AddonInfo objects
    """

    addons_info = []
    for addon in ayon_api.get_addons_info(details=True)["addons"]:
        addon_info = AddonInfo.from_dict(addon)
        if addon_info is not None:
            addons_info.append(addon_info)
    return addons_info


def get_dependency_package(package_name=None):
    """Returns info about currently used dependency package.

    Dependency package means .venv created from all activated addons from the
    server (plus libraries for core Tray app TODO confirm).
    This package needs to be downloaded, unpacked and added to sys.path for
    Tray app to work.

    Args:
        package_name (str): Name of package. Production package name is used
            if not entered.

    Returns:
        Union[DependencyItem, None]: Item or None if package with the name was
            not found.
    """

    dependencies_info = ayon_api.get_dependencies_info()

    dependency_list = dependencies_info["packages"]
    # Use production package if package is not specified
    if package_name is None:
        package_name = dependencies_info["productionPackage"]

    for dependency in dependency_list:
        dependency_package = DependencyItem.from_dict(dependency)
        if dependency_package.name == package_name:
            return dependency_package


def _try_convert_to_server_source(addon, source):
    ayon_base_url = ayon_api.get_base_url()
    urls = [source.url]
    if "https://" in source.url:
        urls.append(source.url.replace("https://", "http://"))
    elif "http://" in source.url:
        urls.append(source.url.replace("http://", "https://"))

    addon_url = f"{ayon_base_url}/addons/{addon.name}/{addon.version}/private/"
    filename = None
    for url in urls:
        if url.startswith(addon_url):
            filename = url.replace(addon_url, "")
            break

    if not filename:
        return source

    return ServerResourceSource(
        type=UrlType.SERVER.value, filename=filename
    )


def update_addon_state(
    addon_infos,
    destination_folder,
    factory,
    log=None
):
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
        log (logging.Logger)

    Returns:
        (dict): {"addon_full_name": UpdateState}
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

        data = {
            "type": "addon",
            "name": addon.name,
            "version": addon.version
        }

        for source in addon.sources:
            download_states[full_name] = UpdateState.FAILED

            # Convert 'WebAddonSource' to 'ServerResourceSource' if possible
            if source.type == UrlType.HTTP.value:
                source = _try_convert_to_server_source(addon, source)

            try:
                downloader = factory.get_downloader(source.type)
                zip_file_path = downloader.download(
                    attr.asdict(source),
                    addon_dest,
                    data
                )
                downloader.check_hash(zip_file_path, addon.hash)
                downloader.unzip(zip_file_path, addon_dest)
                download_states[full_name] = UpdateState.UPDATED
                break
            except Exception:
                log.warning(
                    f"Error happened during updating {addon.name}",
                    exc_info=True)

                if os.path.isdir(addon_dest):
                    log.debug(f"Cleaning {addon_dest}")
                    shutil.rmtree(addon_dest)

    return download_states


def make_sure_addons_are_updated(downloaders=None, addon_folder=None):
    """Main entry point to compare existing addons with those on server.

    Args:
        downloaders (AddonDownloader): factory of downloaders
        addon_folder (str): local dir path for addons

    Raises:
        (RuntimeError) if any addon failed update
    """

    if downloaders is None:
        downloaders = get_default_addon_downloader()

    if addon_folder is None:
        addon_folder = get_addons_dir()

    addons_info = get_addons_info()
    result = update_addon_state(addons_info, addon_folder, downloaders)
    failed = {}
    ok_states = [UpdateState.UPDATED, UpdateState.EXISTS]
    ok_states.append(UpdateState.FAILED_MISSING_SOURCE)  # TODO remove test only  noqa
    for addon_name, res_val in result.items():
        if res_val not in ok_states:
            failed[addon_name] = res_val.value

    if failed:
        raise RuntimeError(f"Unable to update some addons {failed}")


def make_sure_venv_is_updated(downloaders=None, local_venv_dir=None, log=None):
    """Main entry point to compare existing addons with those on server.

    Args:
        downloaders (AddonDownloader): factory of downloaders
        local_venv_dir (str): local dir path for addons

    Raises:
        (RuntimeError) if required production package failed update
    """

    if downloaders is None:
        downloaders = get_default_addon_downloader()

    if local_venv_dir is None:
        local_venv_dir = get_dependencies_dir()

    if log is None:
        log = logging.getLogger(__name__)

    package = get_dependency_package()
    if not package:
        log.info("Server does not contain dependency package")
        return

    venv_dest_dir = os.path.join(local_venv_dir, package.name)
    log.debug(f"Checking {package.name} in {local_venv_dir}")

    if os.path.isdir(venv_dest_dir):
        log.debug(f"Venv folder {venv_dest_dir} already exists.")
        return

    os.makedirs(venv_dest_dir)

    if not package.sources:
        msg = (
            f"Package {package.name} doesn't have any "
            "sources to download from."
        )
        raise RuntimeError(msg)

    data = {
        "type": "dependency_package",
        "name": package.name,
        "platform": package.platform
    }
    for source in package.sources:
        try:
            downloader = downloaders.get_downloader(source.type)
            zip_file_path = downloader.download(
                attr.asdict(source),
                venv_dest_dir,
                data
            )
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


def get_default_addon_downloader():
    addon_downloader = AddonDownloader()
    addon_downloader.register_format(UrlType.FILESYSTEM, OSAddonDownloader)
    addon_downloader.register_format(UrlType.HTTP, HTTPAddonDownloader)
    addon_downloader.register_format(UrlType.SERVER, AyonServerDownloader)
    return addon_downloader


def cli(*args):
    raise NotImplementedError
