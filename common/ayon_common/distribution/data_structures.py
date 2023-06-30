import attr
from enum import Enum


class UrlType(Enum):
    HTTP = "http"
    GIT = "git"
    FILESYSTEM = "filesystem"
    SERVER = "server"


@attr.s
class MultiPlatformValue(object):
    windows = attr.ib(default=None)
    linux = attr.ib(default=None)
    darwin = attr.ib(default=None)


@attr.s
class SourceInfo(object):
    type = attr.ib()


@attr.s
class LocalSourceInfo(SourceInfo):
    path = attr.ib(default=attr.Factory(MultiPlatformValue))


@attr.s
class WebSourceInfo(SourceInfo):
    url = attr.ib(default=None)
    headers = attr.ib(default=None)
    filename = attr.ib(default=None)


@attr.s
class ServerSourceInfo(SourceInfo):
    filename = attr.ib(default=None)
    path = attr.ib(default=None)


def convert_source(source):
    """Create source object from data information.

    Args:
        source (Dict[str, any]): Information about source.

    Returns:
        Union[None, SourceInfo]: Object with source information if type is
            known.
    """

    source_type = source.get("type")
    if not source_type:
        return None

    if source_type == UrlType.FILESYSTEM.value:
        return LocalSourceInfo(
            type=source_type,
            path=source["path"]
        )

    if source_type == UrlType.HTTP.value:
        url = source["path"]
        return WebSourceInfo(
            type=source_type,
            url=url,
            headers=source.get("headers"),
            filename=source.get("filename")
        )

    if source_type == UrlType.SERVER.value:
        return ServerSourceInfo(
            type=source_type,
            filename=source.get("filename"),
            path=source.get("path")
        )


def prepare_sources(src_sources):
    sources = []
    unknown_sources = []
    for source in (src_sources or []):
        dependency_source = convert_source(source)
        if dependency_source is not None:
            sources.append(dependency_source)
        else:
            print(f"Unknown source {source.get('type')}")
            unknown_sources.append(source)
    return sources, unknown_sources


@attr.s
class VersionData(object):
    version_data = attr.ib(default=None)


@attr.s
class AddonVersionInfo(object):
    version = attr.ib()
    full_name = attr.ib()
    title = attr.ib(default=None)
    require_distribution = attr.ib(default=False)
    sources = attr.ib(default=attr.Factory(list))
    unknown_sources = attr.ib(default=attr.Factory(list))
    hash = attr.ib(default=None)

    @classmethod
    def from_dict(
        cls, addon_name, addon_title, addon_version, version_data
    ):
        """Addon version info.

        Args:
            addon_name (str): Name of addon.
            addon_title (str): Title of addon.
            addon_version (str): Version of addon.
            version_data (dict[str, Any]): Addon version information from
                server.

        Returns:
            AddonVersionInfo: Addon version info.
        """

        full_name = f"{addon_name}_{addon_version}"
        title = f"{addon_title} {addon_version}"

        source_info = version_data.get("clientSourceInfo")
        require_distribution = source_info is not None
        sources, unknown_sources = prepare_sources(source_info)

        return cls(
            version=addon_version,
            full_name=full_name,
            require_distribution=require_distribution,
            sources=sources,
            unknown_sources=unknown_sources,
            hash=version_data.get("hash"),
            title=title
        )


@attr.s
class AddonInfo(object):
    """Object matching json payload from Server"""
    name = attr.ib()
    versions = attr.ib(default=attr.Factory(dict))
    title = attr.ib(default=None)
    description = attr.ib(default=None)
    license = attr.ib(default=None)
    authors = attr.ib(default=None)

    @classmethod
    def from_dict(cls, data):
        """Addon info by available versions.

        Args:
            data (dict[str, Any]): Addon information from server. Should
                contain information about every version under 'versions'.

        Returns:
            AddonInfo: Addon info with available versions.
        """

        # server payload contains info about all versions
        addon_name = data["name"]
        title = data.get("title") or addon_name

        src_versions = data.get("versions") or {}
        dst_versions = {
            addon_version: AddonVersionInfo.from_dict(
                addon_name, title, addon_version, version_data
            )
            for addon_version, version_data in src_versions.items()
        }
        return cls(
            name=addon_name,
            versions=dst_versions,
            description=data.get("description"),
            title=data.get("title") or addon_name,
            license=data.get("license"),
            authors=data.get("authors")
        )


@attr.s
class DependencyItem(object):
    """Object matching payload from Server about single dependency package"""
    name = attr.ib()
    platform_name = attr.ib()
    checksum = attr.ib()
    sources = attr.ib(default=attr.Factory(list))
    unknown_sources = attr.ib(default=attr.Factory(list))
    source_addons = attr.ib(default=attr.Factory(dict))
    python_modules = attr.ib(default=attr.Factory(dict))

    @classmethod
    def from_dict(cls, package):
        sources, unknown_sources = prepare_sources(package.get("sources"))
        return cls(
            name=package["name"],
            platform_name=package["platform"],
            sources=sources,
            unknown_sources=unknown_sources,
            checksum=package["checksum"],
            source_addons=package["sourceAddons"],
            python_modules=package["pythonModules"]
        )


@attr.s
class Installer:
    version = attr.ib()
    filename = attr.ib()
    platform_name = attr.ib()
    size = attr.ib()
    checksum = attr.ib()
    python_version = attr.ib()
    python_modules = attr.ib()
    sources = attr.ib(default=attr.Factory(list))
    unknown_sources = attr.ib(default=attr.Factory(list))

    @classmethod
    def from_dict(cls, installer_info):
        sources, unknown_sources = prepare_sources(
            installer_info.get("sources"))

        return cls(
            version=installer_info["version"],
            filename=installer_info["filename"],
            platform_name=installer_info["platform"],
            size=installer_info["size"],
            sources=sources,
            unknown_sources=unknown_sources,
            checksum=installer_info["checksum"],
            python_version=installer_info["pythonVersion"],
            python_modules=installer_info["pythonModules"]
        )


@attr.s
class Bundle:
    """Class representing bundle information."""

    name = attr.ib()
    installer_version = attr.ib()
    addon_versions = attr.ib(default=attr.Factory(dict))
    dependency_packages = attr.ib(default=attr.Factory(dict))
    is_production = attr.ib(default=False)
    is_staging = attr.ib(default=False)

    @classmethod
    def from_dict(cls, data):
        return cls(
            name=data["name"],
            installer_version=data["installerVersion"],
            addon_versions=data["addons"],
            dependency_packages=data["dependencyPackages"],
            is_production=data["isProduction"],
            is_staging=data["isStaging"],
        )
