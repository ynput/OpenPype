import attr
from enum import Enum


class UrlType(Enum):
    HTTP = "http"
    GIT = "git"
    FILESYSTEM = "filesystem"
    SERVER = "server"


@attr.s
class MultiPlatformPath(object):
    windows = attr.ib(default=None)
    linux = attr.ib(default=None)
    darwin = attr.ib(default=None)


@attr.s
class SourceInfo(object):
    type = attr.ib()


@attr.s
class LocalSourceInfo(SourceInfo):
    path = attr.ib(default=attr.Factory(MultiPlatformPath))


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


@attr.s
class VersionData(object):
    version_data = attr.ib(default=None)


@attr.s
class AddonInfo(object):
    """Object matching json payload from Server"""
    name = attr.ib()
    version = attr.ib()
    full_name = attr.ib()
    title = attr.ib(default=None)
    require_distribution = attr.ib(default=False)
    sources = attr.ib(default=attr.Factory(list))
    unknown_sources = attr.ib(default=attr.Factory(list))
    hash = attr.ib(default=None)
    description = attr.ib(default=None)
    license = attr.ib(default=None)
    authors = attr.ib(default=None)

    @classmethod
    def from_dict_by_version(cls, data, addon_version):
        """Addon info for specific version.

        Args:
            data (dict[str, Any]): Addon information from server. Should
                contain information about every version under 'versions'.
            addon_version (str): Addon version for which is info requested.

        Returns:
            Union[AddonInfo, None]: Addon info, or None if version is not
                available.
        """

        if not addon_version:
            return None

        # server payload contains info about all versions
        version_data = data.get("versions", {}).get(addon_version)
        if not version_data:
            return None

        source_info = version_data.get("clientSourceInfo")
        require_distribution = source_info is not None

        sources = []
        unknown_sources = []
        for source in (source_info or []):
            addon_source = convert_source(source)
            if addon_source is not None:
                sources.append(addon_source)
            else:
                unknown_sources.append(source)
                print(f"Unknown source {source.get('type')}")

        full_name = "{}_{}".format(data["name"], addon_version)
        return cls(
            name=data.get("name"),
            version=addon_version,
            full_name=full_name,
            require_distribution=require_distribution,
            sources=sources,
            unknown_sources=unknown_sources,
            hash=data.get("hash"),
            description=data.get("description"),
            title=data.get("title"),
            license=data.get("license"),
            authors=data.get("authors")
        )

    @classmethod
    def from_dict(cls, data, use_staging=False):
        """Get Addon information for production or staging version.

        Args:
            data (dict[str, Any]): Addon information from server. Should
                contain information about every version under 'versions'.
            use_staging (bool): Use staging version if set to 'True' instead
                of production.

        Returns:
            Union[AddonInfo, None]: Addon info, or None if version is not
                set or available.
        """

        # Active addon must have 'productionVersion' or 'stagingVersion'
        #   and matching version info.
        if use_staging:
            addon_version = data.get("stagingVersion")
        else:
            addon_version = data.get("productionVersion")
        return cls.from_dict_by_version(data, addon_version)


@attr.s
class DependencyItem(object):
    """Object matching payload from Server about single dependency package"""
    name = attr.ib()
    platform = attr.ib()
    checksum = attr.ib()
    require_distribution = attr.ib()
    sources = attr.ib(default=attr.Factory(list))
    unknown_sources = attr.ib(default=attr.Factory(list))
    addon_list = attr.ib(default=attr.Factory(list))
    python_modules = attr.ib(default=attr.Factory(dict))

    @classmethod
    def from_dict(cls, package):
        sources = []
        unknown_sources = []
        package_sources = package.get("sources")
        require_distribution = package_sources is not None
        for source in (package_sources or []):
            dependency_source = convert_source(source)
            if dependency_source is not None:
                sources.append(dependency_source)
            else:
                print(f"Unknown source {source.get('type')}")
                unknown_sources.append(source)

        addon_list = [f"{name}_{version}"
                      for name, version in
                      package.get("supportedAddons").items()]

        return cls(
            name=package.get("name"),
            platform=package.get("platform"),
            require_distribution=require_distribution,
            sources=sources,
            unknown_sources=unknown_sources,
            checksum=package.get("checksum"),
            addon_list=addon_list,
            python_modules=package.get("pythonModules")
        )
