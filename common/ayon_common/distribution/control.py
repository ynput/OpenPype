import os
import sys
import json
import traceback
import collections
import datetime
import logging
import shutil
import threading
import platform
import attr
from enum import Enum

import ayon_api

from .utils import (
    get_addons_dir,
    get_dependencies_dir,
)
from .downloaders import get_default_download_factory
from .data_structures import (
    AddonInfo,
    DependencyItem,
    Bundle,
)

NOT_SET = type("UNKNOWN", (), {"__bool__": lambda: False})()


class BundleNotFoundError(Exception):
    """Bundle name is defined but is not available on server.

    Args:
        bundle_name (str): Name of bundle that was not found.
    """

    def __init__(self, bundle_name):
        self.bundle_name = bundle_name
        super().__init__(
            f"Bundle '{bundle_name}' is not available on server"
        )


class UpdateState(Enum):
    UNKNOWN = "unknown"
    UPDATED = "udated"
    OUTDATED = "outdated"
    UPDATE_FAILED = "failed"
    MISS_SOURCE_FILES = "miss_source_files"


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
        addons_info (Optional[list[dict[str, Any]]): List of prepared
            addons' info.
        dependency_packages_info (Optional[list[dict[str, Any]]): Info
            about packages from server.
        bundles_info (Optional[Dict[str, Any]]): Info about
            bundles.
        bundle_name (Optional[str]): Name of bundle to use. If not passed
            an environment variable 'AYON_BUNDLE_NAME' is checked for value.
            When both are not available the bundle is defined by 'use_staging'
            value.
        use_staging (Optional[bool]): Use staging versions of an addon.
            If not passed, an environment variable 'OPENPYPE_USE_STAGING' is
            checked for value '1'.
    """

    def __init__(
        self,
        addon_dirpath=None,
        dependency_dirpath=None,
        dist_factory=None,
        addons_info=NOT_SET,
        dependency_packages_info=NOT_SET,
        bundles_info=NOT_SET,
        bundle_name=NOT_SET,
        use_staging=None
    ):
        self._log = None

        self._dist_started = False
        self._dist_finished = False

        self._addons_dirpath = addon_dirpath or get_addons_dir()
        self._dependency_dirpath = dependency_dirpath or get_dependencies_dir()
        self._dist_factory = (
            dist_factory or get_default_download_factory()
        )

        if isinstance(addons_info, list):
            addons_info = {item.full_name: item for item in addons_info}

        if bundle_name is NOT_SET:
            bundle_name = os.environ.get("AYON_BUNDLE_NAME", NOT_SET)

        # Raw addons data from server
        self._addons_info = addons_info
        # Prepared data as Addon objects
        self._addon_items = NOT_SET
        # Distrubtion items of addons
        #   - only those addons and versions that should be distributed
        self._addon_dist_items = NOT_SET

        # Raw dependency packages data from server
        self._dependency_packages_info = dependency_packages_info
        # Prepared dependency packages as objects
        self._dependency_packages_items = NOT_SET
        # Dependency package item that should be used
        self._dependency_package_item = NOT_SET
        # Distribution item of dependency package
        self._dependency_dist_item = NOT_SET

        # Raw bundles data from server
        self._bundles_info = bundles_info
        # Bundles as objects
        self._bundle_items = NOT_SET

        # Bundle that should be used in production
        self._production_bundle = NOT_SET
        # Bundle that should be used in staging
        self._staging_bundle = NOT_SET
        # Boolean that defines if staging bundle should be used
        self._use_staging = use_staging

        # Specific bundle name should be used
        self._bundle_name = bundle_name
        # Final bundle that will be used
        self._bundle = NOT_SET

    @property
    def use_staging(self):
        """Staging version of a bundle should be used.

        This value is completely ignored if specific bundle name should
            be used.

        Returns:
            bool: True if staging version should be used.
        """

        if self._use_staging is None:
            self._use_staging = os.getenv("OPENPYPE_USE_STAGING") == "1"
        return self._use_staging

    @property
    def log(self):
        """Helper to access logger.

        Returns:
             logging.Logger: Logger instance.
        """
        if self._log is None:
            self._log = logging.getLogger(self.__class__.__name__)
        return self._log

    @property
    def bundles_info(self):
        """

        Returns:
            dict[str, dict[str, Any]]: Bundles information from server.
        """

        if self._bundles_info is NOT_SET:
            self._bundles_info = ayon_api.get_bundles()
        return self._bundles_info

    @property
    def bundle_items(self):
        """

        Returns:
            list[Bundle]: List of bundles info.
        """

        if self._bundle_items is NOT_SET:
            self._bundle_items = [
                Bundle.from_dict(info)
                for info in self.bundles_info["bundles"]
            ]
        return self._bundle_items

    def _prepare_production_staging_bundles(self):
        production_bundle = None
        staging_bundle = None
        for bundle in self.bundle_items:
            if bundle.is_production:
                production_bundle = bundle
            if bundle.is_staging:
                staging_bundle = bundle
        self._production_bundle = production_bundle
        self._staging_bundle = staging_bundle

    @property
    def production_bundle(self):
        """
        Returns:
            Union[Bundle, None]: Bundle that should be used in production.
        """

        if self._production_bundle is NOT_SET:
            self._prepare_production_staging_bundles()
        return self._production_bundle

    @property
    def staging_bundle(self):
        """
        Returns:
            Union[Bundle, None]: Bundle that should be used in staging.
        """

        if self._staging_bundle is NOT_SET:
            self._prepare_production_staging_bundles()
        return self._staging_bundle

    @property
    def bundle_to_use(self):
        """Bundle that will be used for distribution.

        Bundle that should be used can be affected by 'bundle_name'
            or 'use_staging'.

        Returns:
            Union[Bundle, None]: Bundle that will be used for distribution
                or None.

        Raises:
            BundleNotFoundError: When bundle name to use is defined
                but is not available on server.
        """

        if self._bundle is NOT_SET:
            if self._bundle_name is not NOT_SET:
                bundle = next(
                    (
                        bundle
                        for bundle in self.bundle_items
                        if bundle.name == self._bundle_name
                    ),
                    None
                )
                if bundle is None:
                    raise BundleNotFoundError(self._bundle_name)

                self._bundle = bundle
            elif self.use_staging:
                self._bundle = self.staging_bundle
            else:
                self._bundle = self.production_bundle
        return self._bundle

    @property
    def bundle_name_to_use(self):
        bundle = self.bundle_to_use
        return None if bundle is None else bundle.name

    @property
    def addons_info(self):
        """Server information about available addons.

        Returns:
            Dict[str, dict[str, Any]: Addon info by addon name.
        """

        if self._addons_info is NOT_SET:
            self._addons_info = ayon_api.get_addons_info(details=True)
        return self._addons_info

    @property
    def addon_items(self):
        """Information about available addons on server.

        Addons may require distribution of files. For those addons will be
        created 'DistributionItem' handling distribution itself.

        Returns:
            Dict[str, AddonInfo]: Addon info object by addon name.
        """

        if self._addon_items is NOT_SET:
            addons_info = {}
            for addon in self.addons_info["addons"]:
                addon_info = AddonInfo.from_dict(addon)
                addons_info[addon_info.name] = addon_info
            self._addon_items = addons_info
        return self._addon_items

    @property
    def dependency_packages_info(self):
        """Server information about available dependency packages.

        Notes:
            For testing purposes it is possible to pass dependency packages
                information to '__init__'.

        Returns:
            list[dict[str, Any]]: Dependency packages information.
        """

        if self._dependency_packages_info is NOT_SET:
            self._dependency_packages_info = (
                ayon_api.get_dependency_packages())
        return self._dependency_packages_info

    @property
    def dependency_packages_items(self):
        """Dependency packages as objects.

        Returns:
            dict[str, DependencyItem]: Dependency packages as objects by name.
        """

        if self._dependency_packages_items is NOT_SET:
            dependenc_package_items = {}
            for item in self.dependency_packages_info["packages"]:
                item = DependencyItem.from_dict(item)
                dependenc_package_items[item.name] = item
            self._dependency_packages_items = dependenc_package_items
        return self._dependency_packages_items

    @property
    def dependency_package_item(self):
        """Dependency package item that should be used by bundle.

        Returns:
            Union[None, Dict[str, Any]]: None if bundle does not have
                specified dependency package.
        """

        if self._dependency_package_item is NOT_SET:
            dependency_package_item = None
            bundle = self.bundle_to_use
            if bundle is not None:
                package_name = bundle.dependency_packages.get(
                    platform.system().lower()
                )
                dependency_package_item = self.dependency_packages_items.get(
                    package_name)
            self._dependency_package_item = dependency_package_item
        return self._dependency_package_item

    def _prepare_current_addon_dist_items(self):
        addons_metadata = self.get_addons_metadata()
        output = []
        addon_versions = {}
        bundle = self.bundle_to_use
        if bundle is not None:
            addon_versions = bundle.addon_versions
        for addon_name, addon_item in self.addons_info.items():
            addon_version = addon_versions.get(addon_name)
            # Addon is not in bundle -> Skip
            if addon_version is None:
                continue

            addon_version_item = addon_item.versions.get(addon_version)
            # Addon version is not available in addons info
            # - TODO handle this case (raise error, skip, store, report, ...)
            if addon_version_item is None:
                print(
                    f"Version '{addon_version}' of addon '{addon_name}'"
                    " is not available on server."
                )
                continue

            if not addon_version_item.require_distribution:
                continue
            full_name = addon_version_item.full_name
            addon_dest = os.path.join(self._addons_dirpath, full_name)
            self.log.debug(f"Checking {full_name} in {addon_dest}")
            addon_in_metadata = (
                addon_name in addons_metadata
                and addon_version_item.version in addons_metadata[addon_name]
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
                "name": addon_name,
                "version": addon_version
            }

            dist_item = DistributionItem(
                state,
                addon_dest,
                addon_dest,
                addon_version_item.hash,
                self._dist_factory,
                list(addon_version_item.sources),
                downloader_data,
                full_name,
                self.log
            )
            output.append({
                "dist_item": dist_item,
                "addon_name": addon_name,
                "addon_version": addon_version,
                "addon_item": addon_item,
                "addon_version_item": addon_version_item,
            })
        return output

    def _prepare_dependency_progress(self):
        package = self.dependency_package_item
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

    def get_addon_dist_items(self):
        """Addon distribution items.

        These items describe source files required by addon to be available on
        machine. Each item may have 0-n source information from where can be
        obtained. If file is already available it's state will be 'UPDATED'.

        Example output:
            [
                {
                    "dist_item": DistributionItem,
                    "addon_name": str,
                    "addon_version": str,
                    "addon_item": AddonInfo,
                    "addon_version_item": AddonVersionInfo
                }, {
                    ...
                }
            ]

        Returns:
             list[dict[str, Any]]: Distribution items with addon version item.
        """

        if self._addon_dist_items is NOT_SET:
            self._addon_dist_items = (
                self._prepare_current_addon_dist_items())
        return self._addon_dist_items

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

        if self._dependency_dist_item is NOT_SET:
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
        for item in self.get_addon_dist_items():
            dist_item = item["dist_item"]
            if (
                not dist_item.need_distribution
                or dist_item.state != UpdateState.UPDATED
            ):
                continue

            source_data = dist_item.used_source
            if not source_data:
                continue

            addon_name = item["addon_name"]
            addon_version = item["addon_version"]
            addons_info.setdefault(addon_name, {})
            addons_info[addon_name][addon_version] = {
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

        output = [
            item["dist_item"]
            for item in self.get_addon_dist_items()
        ]
        dependency_dist_item = self.get_dependency_dist_item()
        if dependency_dist_item is not None:
            output.insert(0, dependency_dist_item)

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

        for item in self.get_addon_dist_items():
            dist_item = item["dist_item"]
            if dist_item.state != UpdateState.UPDATED:
                invalid.append(item["addon_name"])

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


def cli(*args):
    raise NotImplementedError
