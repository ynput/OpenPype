import os
import sys
import json
import traceback
import collections
import datetime
from enum import Enum
from abc import abstractmethod
import attr
import logging
import platform
import shutil
import threading
from abc import ABCMeta

import ayon_api

from ayon_common.utils import get_ayon_appdirs
from .file_handler import RemoteFileHandler
from .addon_info import (
    AddonInfo,
    UrlType,
    DependencyItem,
)


class UpdateState(Enum):
    UNKNOWN = "unknown"
    UPDATED = "udated"
    OUTDATED = "outdated"
    UPDATE_FAILED = "failed"
    MISS_SOURCE_FILES = "miss_source_files"


def get_local_dir(*subdirs):
    """Get product directory in user's home directory.

    Each user on machine have own local directory where are downloaded updates,
    addons etc.

    Returns:
        str: Path to product local directory.
    """

    if not subdirs:
        raise ValueError("Must fill dir_name if nothing else provided!")

    local_dir = get_ayon_appdirs(*subdirs)
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


class SourceDownloader(metaclass=ABCMeta):
    log = logging.getLogger(__name__)

    @classmethod
    @abstractmethod
    def download(cls, source, destination_dir, data, transfer_progress):
        """Returns url to downloaded addon zip file.

        Tranfer progress can be ignored, in that case file transfer won't
        be shown as 0-100% but as 'running'. First step should be to set
        destination content size and then add transferred chunk sizes.

        Args:
            source (dict): {type:"http", "url":"https://} ...}
            destination_dir (str): local folder to unzip
            data (dict): More information about download content. Always have
                'type' key in.
            transfer_progress (ayon_api.TransferProgress): Progress of
                transferred (copy/download) content.

        Returns:
            (str) local path to addon zip file
        """

        pass

    @classmethod
    @abstractmethod
    def cleanup(cls, source, destination_dir, data):
        """Cleanup files when distribution finishes or crashes.

        Cleanup e.g. temporary files (downloaded zip) or other related stuff
        to downloader.
        """

        pass

    @classmethod
    def check_hash(cls, addon_path, addon_hash, hash_type="sha256"):
        """Compares 'hash' of downloaded 'addon_url' file.

        Args:
            addon_path (str): Local path to addon file.
            addon_hash (str): Hash of downloaded file.
            hash_type (str): Type of hash.

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
            destination_dir (str): local folder to unzip
        """

        RemoteFileHandler.unzip(addon_zip_path, destination_dir)
        os.remove(addon_zip_path)


class DownloadFactory:
    def __init__(self):
        self._downloaders = {}

    def register_format(self, downloader_type, downloader):
        """Register downloader for download type.

        Args:
            downloader_type (UrlType): Type of source.
            downloader (SourceDownloader): Downloader which cares about
                download, hash check and unzipping.
        """

        self._downloaders[downloader_type.value] = downloader

    def get_downloader(self, downloader_type):
        """Registered downloader for type.

        Args:
            downloader_type (UrlType): Type of source.

        Returns:
            SourceDownloader: Downloader object which should care about file
                distribution.

        Raises:
            ValueError: If type does not have registered downloader.
        """

        if downloader := self._downloaders.get(downloader_type):
            return downloader()
        raise ValueError(f"{downloader_type} not implemented")


class OSDownloader(SourceDownloader):
    @classmethod
    def download(cls, source, destination_dir, data, transfer_progress):
        # OS doesn't need to download, unzip directly
        addon_url = source["path"].get(platform.system().lower())
        if not os.path.exists(addon_url):
            raise ValueError(f"{addon_url} is not accessible")
        return addon_url

    @classmethod
    def cleanup(cls, source, destination_dir, data):
        # Nothing to do - download does not copy anything
        pass


class HTTPDownloader(SourceDownloader):
    CHUNK_SIZE = 100000

    @staticmethod
    def get_filename(source):
        source_url = source["url"]
        filename = source.get("filename")
        if not filename:
            filename = os.path.basename(source_url)
            basename, ext = os.path.splitext(filename)
            allowed_exts = set(RemoteFileHandler.IMPLEMENTED_ZIP_FORMATS)
            if ext.replace(".", "") not in allowed_exts:
                filename = f"{basename}.zip"
        return filename

    @classmethod
    def download(cls, source, destination_dir, data, transfer_progress):
        source_url = source["url"]
        cls.log.debug(f"Downloading {source_url} to {destination_dir}")
        headers = source.get("headers")
        filename = cls.get_filename(source)

        # TODO use transfer progress
        RemoteFileHandler.download_url(
            source_url,
            destination_dir,
            filename,
            headers=headers
        )

        return os.path.join(destination_dir, filename)

    @classmethod
    def cleanup(cls, source, destination_dir, data):
        # Nothing to do - download does not copy anything
        filename = cls.get_filename(source)
        filepath = os.path.join(destination_dir, filename)
        if os.path.exists(filepath) and os.path.isfile(filepath):
            os.remove(filepath)


class AyonServerDownloader(SourceDownloader):
    """Downloads static resource file from v4 Server.

    Expects filled env var AYON_SERVER_URL.
    """

    CHUNK_SIZE = 8192

    @classmethod
    def download(cls, source, destination_dir, data, transfer_progress):
        path = source["path"]
        filename = source["filename"]
        if path and not filename:
            filename = path.split("/")[-1]

        cls.log.debug(f"Downloading {filename} to {destination_dir}")

        _, ext = os.path.splitext(filename)
        clear_ext = ext.lower().replace(".", "")
        valid_exts = set(RemoteFileHandler.IMPLEMENTED_ZIP_FORMATS)
        if clear_ext not in valid_exts:
            raise ValueError(
                "Invalid file extension \"{}\". Expected {}".format(
                    clear_ext, ", ".join(valid_exts)
                ))

        if path:
            filepath = os.path.join(destination_dir, filename)
            return ayon_api.download_file(
                path,
                filepath,
                chunk_size=cls.CHUNK_SIZE,
                progress=transfer_progress
            )

        # dst_filepath = os.path.join(destination_dir, filename)
        if data["type"] == "dependency_package":
            return ayon_api.download_dependency_package(
                data["name"],
                destination_dir,
                filename,
                platform_name=data["platform"],
                chunk_size=cls.CHUNK_SIZE,
                progress=transfer_progress
            )

        if data["type"] == "addon":
            return ayon_api.download_addon_private_file(
                data["name"],
                data["version"],
                filename,
                destination_dir,
                chunk_size=cls.CHUNK_SIZE,
                progress=transfer_progress
            )

        raise ValueError(f"Unknown type to download \"{data['type']}\"")

    @classmethod
    def cleanup(cls, source, destination_dir, data):
        # Nothing to do - download does not copy anything
        filename = source["filename"]
        filepath = os.path.join(destination_dir, filename)
        if os.path.exists(filepath) and os.path.isfile(filepath):
            os.remove(filepath)


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

        return bool(
            self._started
            and not self._failed
            and not self._hash_check_finished
        )

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
        factory (DownloadFactory): Downloaders factory object.
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

    @property
    def error_message(self):
        """Reason why distribution item failed.

        Returns:
            Union[str, None]: Error message.
        """

        return self._error_msg

    @property
    def error_detail(self):
        """Detailed reason why distribution item failed.

        Returns:
            Union[str, None]: Detailed information (maybe traceback).
        """

        return self._error_detail

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


class AyonDistribution:
    """Distribution control.

    Receive information from server what addons and dependency packages
    should be available locally and prepare/validate their distribution.

    Arguments are available for testing of the class.

    Args:
        addon_dirpath (Optional[str]): Where addons will be stored.
        dependency_dirpath (Optional[str]): Where dependencies will be stored.
        dist_factory (Optional[DownloadFactory]): Factory which cares about
            downloading of items based on source type.
        addons_info (Optional[List[AddonInfo]]): List of prepared addons' info.
        dependency_package_info (Optional[Union[Dict[str, Any], None]]): Info
            about package from server. Defaults to '-1'.
        use_staging (Optional[bool]): Use staging versions of an addon.
            If not passed, an environment variable 'OPENPYPE_USE_STAGING' is
            checked for value '1'.
    """

    def __init__(
        self,
        addon_dirpath=None,
        dependency_dirpath=None,
        dist_factory=None,
        addons_info=None,
        dependency_package_info=-1,
        use_staging=None
    ):
        self._addons_dirpath = addon_dirpath or get_addons_dir()
        self._dependency_dirpath = dependency_dirpath or get_dependencies_dir()
        self._dist_factory = (
            dist_factory or get_default_download_factory()
        )

        if isinstance(addons_info, list):
            addons_info = {item.full_name: item for item in addons_info}
        self._dist_started = False
        self._dist_finished = False
        self._log = None
        self._addons_info = addons_info
        self._addons_dist_items = None
        self._dependency_package = dependency_package_info
        self._dependency_dist_item = -1
        self._use_staging = use_staging

    @property
    def use_staging(self):
        if self._use_staging is None:
            self._use_staging = os.getenv("OPENPYPE_USE_STAGING") == "1"
        return self._use_staging

    @property
    def log(self):
        if self._log is None:
            self._log = logging.getLogger(self.__class__.__name__)
        return self._log

    @property
    def addons_info(self):
        """Information about available addons on server.

        Addons may require distribution of files. For those addons will be
        created 'DistributionItem' handling distribution itself.

        Todos:
            Add support for staging versions. Right now is supported only
                production version.

        Returns:
            Dict[str, AddonInfo]: Addon info by full name.
        """

        if self._addons_info is None:
            addons_info = {}
            server_addons_info = ayon_api.get_addons_info(details=True)
            for addon in server_addons_info["addons"]:
                addon_info = AddonInfo.from_dict(addon, self.use_staging)
                if addon_info is None:
                    continue
                addons_info[addon_info.full_name] = addon_info

            self._addons_info = addons_info
        return self._addons_info

    @property
    def dependency_package(self):
        """Information about dependency package from server.

        Receive and cache dependency package information from server.

        Notes:
            For testing purposes it is possible to pass dependency package
                information to '__init__'.

        Returns:
            Union[None, Dict[str, Any]]: None if server does not have specified
                dependency package.
        """

        if self._dependency_package == -1:
            self._dependency_package = get_dependency_package()
        return self._dependency_package

    def _prepare_current_addons_dist_items(self):
        addons_metadata = self.get_addons_metadata()
        output = {}
        for full_name, addon_info in self.addons_info.items():
            if not addon_info.require_distribution:
                continue
            addon_dest = os.path.join(self._addons_dirpath, full_name)
            self.log.debug(f"Checking {full_name} in {addon_dest}")
            addon_in_metadata = (
                addon_info.name in addons_metadata
                and addon_info.version in addons_metadata[addon_info.name]
            )
            if addon_in_metadata and os.path.isdir(addon_dest):
                self.log.debug(
                    f"Addon version folder {addon_dest} already exists."
                )
                state = UpdateState.UPDATED

            else:
                state = UpdateState.OUTDATED

            downloader_data = {
                "type": "addon",
                "name": addon_info.name,
                "version": addon_info.version
            }

            output[full_name] = DistributionItem(
                state,
                addon_dest,
                addon_dest,
                addon_info.hash,
                self._dist_factory,
                list(addon_info.sources),
                downloader_data,
                full_name,
                self.log
            )
        return output

    def _prepare_dependency_progress(self):
        package = self.dependency_package
        if package is None or not package.require_distribution:
            return None

        metadata = self.get_dependency_metadata()
        downloader_data = {
            "type": "dependency_package",
            "name": package.name,
            "platform": package.platform
        }
        zip_dir = package_dir = os.path.join(
            self._dependency_dirpath, package.name
        )
        self.log.debug(f"Checking {package.name} in {package_dir}")

        if not os.path.isdir(package_dir) or package.name not in metadata:
            state = UpdateState.OUTDATED
        else:
            state = UpdateState.UPDATED

        return DistributionItem(
            state,
            zip_dir,
            package_dir,
            package.checksum,
            self._dist_factory,
            package.sources,
            downloader_data,
            package.name,
            self.log,
        )

    def get_addons_dist_items(self):
        """Addon distribution items.

        These items describe source files required by addon to be available on
        machine. Each item may have 0-n source information from where can be
        obtained. If file is already available it's state will be 'UPDATED'.

        Returns:
             Dict[str, DistributionItem]: Distribution items by addon fullname.
        """

        if self._addons_dist_items is None:
            self._addons_dist_items = self._prepare_current_addons_dist_items()
        return self._addons_dist_items

    def get_dependency_dist_item(self):
        """Dependency package distribution item.

        Item describe source files required by server to be available on
        machine. Item may have 0-n source information from where can be
        obtained. If file is already available it's state will be 'UPDATED'.

        'None' is returned if server does not have defined any dependency
        package.

        Returns:
            Union[None, DistributionItem]: Dependency item or None if server
                does not have specified any dependency package.
        """

        if self._dependency_dist_item == -1:
            self._dependency_dist_item = self._prepare_dependency_progress()
        return self._dependency_dist_item

    def get_dependency_metadata_filepath(self):
        """Path to distribution metadata file.

        Metadata contain information about distributed packages, used source,
        expected file hash and time when file was distributed.

        Returns:
            str: Path to a file where dependency package metadata are stored.
        """

        return os.path.join(self._dependency_dirpath, "dependency.json")

    def get_addons_metadata_filepath(self):
        """Path to addons metadata file.

        Metadata contain information about distributed addons, used sources,
        expected file hashes and time when files were distributed.

        Returns:
            str: Path to a file where addons metadata are stored.
        """

        return os.path.join(self._addons_dirpath, "addons.json")

    def read_metadata_file(self, filepath, default_value=None):
        """Read json file from path.

        Method creates the file when does not exist with default value.

        Args:
            filepath (str): Path to json file.
            default_value (Union[Dict[str, Any], List[Any], None]): Default
                value if the file is not available (or valid).

        Returns:
            Union[Dict[str, Any], List[Any]]: Value from file.
        """

        if default_value is None:
            default_value = {}

        if not os.path.exists(filepath):
            return default_value

        try:
            with open(filepath, "r") as stream:
                data = json.load(stream)
        except ValueError:
            data = default_value
        return data

    def save_metadata_file(self, filepath, data):
        """Store data to json file.

        Method creates the file when does not exist.

        Args:
            filepath (str): Path to json file.
            data (Union[Dict[str, Any], List[Any]]): Data to store into file.
        """

        if not os.path.exists(filepath):
            dirpath = os.path.dirname(filepath)
            if not os.path.exists(dirpath):
                os.makedirs(dirpath)
        with open(filepath, "w") as stream:
            json.dump(data, stream, indent=4)

    def get_dependency_metadata(self):
        filepath = self.get_dependency_metadata_filepath()
        return self.read_metadata_file(filepath, {})

    def update_dependency_metadata(self, package_name, data):
        dependency_metadata = self.get_dependency_metadata()
        dependency_metadata[package_name] = data
        filepath = self.get_dependency_metadata_filepath()
        self.save_metadata_file(filepath, dependency_metadata)

    def get_addons_metadata(self):
        filepath = self.get_addons_metadata_filepath()
        return self.read_metadata_file(filepath, {})

    def update_addons_metadata(self, addons_information):
        if not addons_information:
            return
        addons_metadata = self.get_addons_metadata()
        for addon_name, version_value in addons_information.items():
            if addon_name not in addons_metadata:
                addons_metadata[addon_name] = {}
            for addon_version, version_data in version_value.items():
                addons_metadata[addon_name][addon_version] = version_data

        filepath = self.get_addons_metadata_filepath()
        self.save_metadata_file(filepath, addons_metadata)

    def finish_distribution(self):
        """Store metadata about distributed items."""

        self._dist_finished = True
        stored_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        dependency_dist_item = self.get_dependency_dist_item()
        if (
            dependency_dist_item is not None
            and dependency_dist_item.need_distribution
            and dependency_dist_item.state == UpdateState.UPDATED
        ):
            package = self.dependency_package
            source = dependency_dist_item.used_source
            if source is not None:
                data = {
                    "source": source,
                    "file_hash": dependency_dist_item.file_hash,
                    "distributed_dt": stored_time
                }
                self.update_dependency_metadata(package.name, data)

        addons_info = {}
        for full_name, dist_item in self.get_addons_dist_items().items():
            if (
                not dist_item.need_distribution
                or dist_item.state != UpdateState.UPDATED
            ):
                continue

            source_data = dist_item.used_source
            if not source_data:
                continue
            addon_info = self.addons_info[full_name]
            if addon_info.name not in addons_info:
                addons_info[addon_info.name] = {}
            addons_info[addon_info.name][addon_info.version] = {
                "source": source_data,
                "file_hash": dist_item.file_hash,
                "distributed_dt": stored_time
            }

        self.update_addons_metadata(addons_info)

    def get_all_distribution_items(self):
        """Distribution items required by server.

        Items contain dependency package item and all addons that are enabled
        and have distribution requirements.

        Items can be already available on machine.

        Returns:
            List[DistributionItem]: Distribution items required by server.
        """

        output = []
        dependency_dist_item = self.get_dependency_dist_item()
        if dependency_dist_item is not None:
            output.append(dependency_dist_item)
        for dist_item in self.get_addons_dist_items().values():
            output.append(dist_item)
        return output

    def distribute(self, threaded=False):
        """Distribute all missing items.

        Method will try to distribute all items that are required by server.

        This method does not handle failed items. To validate the result call
        'validate_distribution' when this method finishes.

        Args:
            threaded (bool): Distribute items in threads.
        """

        if self._dist_started:
            raise RuntimeError("Distribution already started")
        self._dist_started = True
        threads = collections.deque()
        for item in self.get_all_distribution_items():
            if threaded:
                threads.append(threading.Thread(target=item.distribute))
            else:
                item.distribute()

        while threads:
            thread = threads.popleft()
            if thread.is_alive():
                threads.append(thread)
            else:
                thread.join()

        self.finish_distribution()

    def validate_distribution(self):
        """Check if all required distribution items are distributed.

        Raises:
            RuntimeError: Any of items is not available.
        """

        invalid = []
        dependency_package = self.get_dependency_dist_item()
        if (
            dependency_package is not None
            and dependency_package.state != UpdateState.UPDATED
        ):
            invalid.append("Dependency package")

        for addon_name, dist_item in self.get_addons_dist_items().items():
            if dist_item.state != UpdateState.UPDATED:
                invalid.append(addon_name)

        if not invalid:
            return

        raise RuntimeError("Failed to distribute {}".format(
            ", ".join([f'"{item}"' for item in invalid])
        ))

    def get_sys_paths(self):
        """Get all paths to python packages that should be added to python.

        These paths lead to addon directories and python dependencies in
        dependency package.

        Todos:
            Add dependency package directory to output. ATM is not structure of
                dependency package 100% defined.

        Returns:
            List[str]: Paths that should be added to 'sys.path' and
                'PYTHONPATH'.
        """

        output = []
        for item in self.get_all_distribution_items():
            if item.state != UpdateState.UPDATED:
                continue
            unzip_dirpath = item.unzip_dirpath
            if unzip_dirpath and os.path.exists(unzip_dirpath):
                output.append(unzip_dirpath)
        return output


def get_default_download_factory():
    download_factory = DownloadFactory()
    download_factory.register_format(UrlType.FILESYSTEM, OSDownloader)
    download_factory.register_format(UrlType.HTTP, HTTPDownloader)
    download_factory.register_format(UrlType.SERVER, AyonServerDownloader)
    return download_factory


def cli(*args):
    raise NotImplementedError
