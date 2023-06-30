import os
import logging
import platform
from abc import ABCMeta, abstractmethod

import ayon_api

from .file_handler import RemoteFileHandler
from .data_structures import UrlType


class SourceDownloader(metaclass=ABCMeta):
    """Abstract class for source downloader."""

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
        if not RemoteFileHandler.check_integrity(
            addon_path, addon_hash, hash_type=hash_type
        ):
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


class OSDownloader(SourceDownloader):
    """Downloader using files from file drive."""

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
    """Downloader using http or https protocol."""

    CHUNK_SIZE = 100000

    @staticmethod
    def get_filename(source):
        source_url = source["url"]
        filename = source.get("filename")
        if not filename:
            filename = os.path.basename(source_url)
            basename, ext = os.path.splitext(filename)
            allowed_exts = set(RemoteFileHandler.IMPLEMENTED_ZIP_FORMATS)
            if ext.lower().lstrip(".") not in allowed_exts:
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
        filename = cls.get_filename(source)
        filepath = os.path.join(destination_dir, filename)
        if os.path.exists(filepath) and os.path.isfile(filepath):
            os.remove(filepath)


class AyonServerDownloader(SourceDownloader):
    """Downloads static resource file from AYON Server.

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
        ext = ext.lower().lstrip(".")
        valid_exts = set(RemoteFileHandler.IMPLEMENTED_ZIP_FORMATS)
        if ext not in valid_exts:
            raise ValueError((
                f"Invalid file extension \"{ext}\"."
                f" Expected {', '.join(valid_exts)}"
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
        filename = source["filename"]
        filepath = os.path.join(destination_dir, filename)
        if os.path.exists(filepath) and os.path.isfile(filepath):
            os.remove(filepath)


class DownloadFactory:
    """Factory for downloaders."""

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


def get_default_download_factory():
    download_factory = DownloadFactory()
    download_factory.register_format(UrlType.FILESYSTEM, OSDownloader)
    download_factory.register_format(UrlType.HTTP, HTTPDownloader)
    download_factory.register_format(UrlType.SERVER, AyonServerDownloader)
    return download_factory
