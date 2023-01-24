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
    """Get product directory in user's home directory.

    Each user on machine have own local directory where are downloaded updates,
    addons etc.

    Returns:
        str: Path to product local directory.
    """

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
    """Directory where addon packages are stored.

    Path to addons is defined using python module 'appdirs' which

    The path is stored into environment variable 'AYON_ADDONS_DIR'.
    Value of environment variable can be overriden, but we highly recommended
    to use that option only for development purposes.

    Returns:
        str: Path to directory where addons should be downloaded.
    """

    addons_dir = os.environ.get("AYON_ADDONS_DIR")
    if not addons_dir:
        addons_dir = get_local_dir("addons")
        os.environ["AYON_ADDONS_DIR"] = addons_dir
    return addons_dir


def get_dependencies_dir():
    """Directory where dependency packages are stored.

    Path to addons is defined using python module 'appdirs' which

    The path is stored into environment variable 'AYON_DEPENDENCIES_DIR'.
    Value of environment variable can be overriden, but we highly recommended
    to use that option only for development purposes.

    Returns:
        str: Path to directory where dependency packages should be downloaded.
    """

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


class DistributeTransferProgress:
    """Progress of single source item in 'DistributionItem'.

    The item is to keep track of single source item.
    """

    def __init__(self):
        self._transfer_progress = ayon_api.TransferProgress()
        self._started = False
        self._failed = False
        self._fail_reason = None
        self._unzip_started = False
        self._unzip_finished = False
        self._hash_check_started = False
        self._hash_check_finished = False

    def set_started(self):
        """Call when source distribution starts."""

        self._started = True

    def set_failed(self, reason):
        """Set source distribution as failed.

        Args:
            reason (str): Error message why the transfer failed.
        """

        self._failed = True
        self._fail_reason = reason

    def set_hash_check_started(self):
        """Call just before hash check starts."""

        self._hash_check_started = True

    def set_hash_check_finished(self):
        """Call just after hash check finishes."""

        self._hash_check_finished = True

    def set_unzip_started(self):
        """Call just before unzip starts."""

        self._unzip_started = True

    def set_unzip_finished(self):
        """Call just after unzip finishes."""

        self._unzip_finished = True

    @property
    def is_running(self):
        """Source distribution is in progress.

        Returns:
            bool: Transfer is in progress.
        """

        if (
            not self._started
            or self._failed
            or self._hash_check_finished
        ):
            return False
        return True

    @property
    def transfer_progress(self):
        """Source file 'download' progress tracker.

        Returns:
            ayon_api.TransferProgress.: Content download progress.
        """

        return self._transfer_progress

    @property
    def started(self):
        return self._started

    @property
    def hash_check_started(self):
        return self._hash_check_started

    @property
    def hash_check_finished(self):
        return self._has_check_finished

    @property
    def unzip_started(self):
        return self._unzip_started

    @property
    def unzip_finished(self):
        return self._unzip_finished

    @property
    def failed(self):
        return self._failed or self._transfer_progress.failed

    @property
    def fail_reason(self):
        return self._fail_reason or self._transfer_progress.fail_reason


class DistributionItem:
    """Distribution item with sources and target directories.

    Distribution item can be an addon or dependency package. Distribution item
    can be already distributed and don't need any progression. The item keeps
    track of the progress. The reason is to be able to use the distribution
    items as source data for UI without implementing the same logic.

    Distribution is "state" based. Distribution can be 'UPDATED' or 'OUTDATED'
    at the initialization. If item is 'UPDATED' the distribution is skipped
    and 'OUTDATED' will trigger the distribution process.

    Because the distribution may have multiple sources each source has own
    progress item.

    Args:
        state (UpdateState): Initial state (UpdateState.UPDATED or
            UpdateState.OUTDATED).
        unzip_dirpath (str): Path to directory where zip is downloaded.
        download_dirpath (str): Path to directory where file is unzipped.
        file_hash (str): Hash of file for validation.
        factory (AddonDownloader): Downloaders factory object.
        sources (List[SourceInfo]): Possible sources to receive the
            distribution item.
        downloader_data (Dict[str, Any]): More information for downloaders.
        item_label (str): Label used in log outputs (and in UI).
        logger (logging.Logger): Logger object.
    """

    def __init__(
        self,
        state,
        unzip_dirpath,
        download_dirpath,
        file_hash,
        factory,
        sources,
        downloader_data,
        item_label,
        logger=None,
    ):
        if logger is None:
            logger = logging.getLogger(self.__class__.__name__)
        self.log = logger
        self.state = state
        self.unzip_dirpath = unzip_dirpath
        self.download_dirpath = download_dirpath
        self.file_hash = file_hash
        self.factory = factory
        self.sources = [
            (source, DistributeTransferProgress())
            for source in sources
        ]
        self.downloader_data = downloader_data
        self.item_label = item_label

        self._need_distribution = state != UpdateState.UPDATED
        self._current_source_progress = None
        self._used_source_progress = None
        self._used_source = None
        self._dist_started = False
        self._dist_finished = False

        self._error_msg = None
        self._error_detail = None

    @property
    def need_distribution(self):
        """Need distribution based on initial state.

        Returns:
            bool: Need distribution.
        """

        return self._need_distribution

    @property
    def current_source_progress(self):
        """Currently processed source progress object.

        Returns:
            Union[DistributeTransferProgress, None]: Transfer progress or None.
        """

        return self._current_source_progress

    @property
    def used_source_progress(self):
        """Transfer progress that successfully distributed the item.

        Returns:
            Union[DistributeTransferProgress, None]: Transfer progress or None.
        """

        return self._used_source_progress

    @property
    def used_source(self):
        """Data of source item.

        Returns:
            Union[Dict[str, Any], None]: SourceInfo data or None.
        """

        return self._used_source

    def _distribute(self):
        if not self.sources:
            message = (
                f"{self.item_label}: Don't have"
                " any sources to download from."
            )
            self.log.error(message)
            self._error_msg = message
            self.state = UpdateState.MISS_SOURCE_FILES
            return

        download_dirpath = self.download_dirpath
        unzip_dirpath = self.unzip_dirpath
        for source, source_progress in self.sources:
            self._current_source_progress = source_progress
            source_progress.set_started()

            # Remove directory if exists
            if os.path.isdir(unzip_dirpath):
                self.log.debug(f"Cleaning {unzip_dirpath}")
                shutil.rmtree(unzip_dirpath)

            # Create directory
            os.makedirs(unzip_dirpath)
            if not os.path.isdir(download_dirpath):
                os.makedirs(download_dirpath)

            try:
                downloader = self.factory.get_downloader(source.type)
            except Exception:
                source_progress.set_failed(f"Unknown downloader {source.type}")
                self.log.warning(message, exc_info=True)
                continue

            source_data = attr.asdict(source)
            cleanup_args = (
                source_data,
                download_dirpath,
                self.downloader_data
            )

            try:
                zip_filepath = downloader.download(
                source_data,
                download_dirpath,
                self.downloader_data,
                source_progress.transfer_progress,
            )
            except Exception:
                message = "Failed to download source"
                source_progress.set_failed(message)
                self.log.warning(
                    f"{self.item_label}: {message}",
                    exc_info=True
                )
                downloader.cleanup(*cleanup_args)
                continue

            source_progress.set_hash_check_started()
            try:
                downloader.check_hash(zip_filepath, self.file_hash)
            except Exception:
                message = "File hash does not match"
                source_progress.set_failed(message)
                self.log.warning(
                    f"{self.item_label}: {message}",
                    exc_info=True
                )
                downloader.cleanup(*cleanup_args)
                continue

            source_progress.set_hash_check_finished()
            source_progress.set_unzip_started()
            try:
                downloader.unzip(zip_filepath, unzip_dirpath)
            except Exception:
                message = "Couldn't unzip source file"
                source_progress.set_failed(message)
                self.log.warning(
                    f"{self.item_label}: {message}",
                    exc_info=True
                )
                downloader.cleanup(*cleanup_args)
                continue

            source_progress.set_unzip_finished()
            downloader.cleanup(*cleanup_args)
            self.state = UpdateState.UPDATED
            self._used_source = source_data
            break

        last_progress = self._current_source_progress
        self._current_source_progress = None
        if self.state == UpdateState.UPDATED:
            self._used_source_progress = last_progress
            self.log.info(f"{self.item_label}: Distributed")
            return

        self.log.error(f"{self.item_label}: Failed to distribute")
        self._error_msg = "Failed to receive or install source files"

    def distribute(self):
        """Execute distribution logic."""

        if not self.need_distribution or self._dist_started:
            return

        self._dist_started = True
        try:
            if self.state == UpdateState.OUTDATED:
                self._distribute()

        except Exception as exc:
            self.state = UpdateState.UPDATE_FAILED
            self._error_msg = str(exc)
            self._error_detail = "".join(
                traceback.format_exception(*sys.exc_info())
            )
            self.log.error(
                f"{self.item_label}: Distibution filed",
                exc_info=True
            )

        finally:
            self._dist_finished = True
            if self.state == UpdateState.OUTDATED:
                self.state = UpdateState.UPDATE_FAILED
                self._error_msg = "Distribution failed"

            if (
                self.state != UpdateState.UPDATED
                and self.unzip_dirpath
                and os.path.isdir(self.unzip_dirpath)
            ):
                self.log.debug(f"Cleaning {self.unzip_dirpath}")
                shutil.rmtree(self.unzip_dirpath)


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
