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


@attr.s
class ServerSourceInfo(SourceInfo):
    filename = attr.ib(default=None)


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
    sources = attr.ib(default=attr.Factory(list))
    unknown_sources = attr.ib(default=attr.Factory(list))
    hash = attr.ib(default=None)
    description = attr.ib(default=None)
    license = attr.ib(default=None)
    authors = attr.ib(default=None)

    @classmethod
    def from_dict(cls, data):
        sources = []
        unknown_sources = []

        production_version = data.get("productionVersion")
        if not production_version:
            return None

        # server payload contains info about all versions
        # active addon must have 'productionVersion' and matching version info
        version_data = data.get("versions", {})[production_version]

        for source in version_data.get("clientSourceInfo", []):
            source_type = source.get("type")
            if source_type == UrlType.FILESYSTEM.value:
                source_addon = LocalSourceInfo(
                    type=source_type, path=source["path"])
            elif source_type == UrlType.HTTP.value:
                url = source["path"]
                source_addon = WebSourceInfo(
                    type=source_type,
                    url=url,
                    headers=source.get("headers")
                )
            elif source_type == UrlType.SERVER.value:
                source_addon = ServerSourceInfo(
                    type=source_type, filename=source["filename"])
            else:
                print(f"Unknown source {source_type}")
                unknown_sources.append(source)
                continue

            sources.append(source_addon)

        full_name = "{}_{}".format(data["name"], production_version)
        return cls(name=data.get("name"),
                   version=production_version,
                   full_name=full_name,
                   sources=sources,
                   unknown_sources=unknown_sources,
                   hash=data.get("hash"),
                   description=data.get("description"),
                   title=data.get("title"),
                   license=data.get("license"),
                   authors=data.get("authors"))


@attr.s
class DependencyItem(object):
    """Object matching payload from Server about single dependency package"""
    name = attr.ib()
    platform = attr.ib()
    checksum = attr.ib()
    sources = attr.ib(default=attr.Factory(list))
    unknown_sources = attr.ib(default=attr.Factory(list))
    addon_list = attr.ib(default=attr.Factory(list))
    python_modules = attr.ib(default=attr.Factory(dict))

    @classmethod
    def from_dict(cls, package):
        sources = []
        unknown_sources = []
        for source in package.get("sources", []):
            source_type = source.get("type")
            if source_type == UrlType.FILESYSTEM.value:
                source_addon = LocalSourceInfo(
                    type=source_type, path=source["path"])
            elif source_type == UrlType.HTTP.value:
                url = source["path"]
                source_addon = WebSourceInfo(
                    type=source_type,
                    url=url,
                    headers=source.get("headers")
                )
            elif source_type == UrlType.SERVER.value:
                source_addon = ServerSourceInfo(
                    type=source_type, filename=source["filename"])
            else:
                print(f"Unknown source {source_type}")
                unknown_sources.append(source)
                continue

            sources.append(source_addon)
        addon_list = [f"{name}_{version}"
                      for name, version in
                      package.get("supportedAddons").items()]

        return cls(name=package.get("name"),
                   platform=package.get("platform"),
                   sources=sources,
                   unknown_sources=unknown_sources,
                   checksum=package.get("checksum"),
                   addon_list=addon_list,
                   python_modules=package.get("pythonModules"))
