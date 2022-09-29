import attr
from enum import Enum


class UrlType(Enum):
    HTTP = "http"
    GIT = "git"
    FILESYSTEM = "filesystem"


@attr.s
class MultiPlatformPath(object):
    windows = attr.ib(default=None)
    linux = attr.ib(default=None)
    darwin = attr.ib(default=None)


@attr.s
class AddonSource(object):
    type = attr.ib()


@attr.s
class LocalAddonSource(AddonSource):
    path = attr.ib(default=attr.Factory(MultiPlatformPath))


@attr.s
class WebAddonSource(AddonSource):
    url = attr.ib(default=None)


@attr.s
class VersionData(object):
    version_data = attr.ib(default=None)


@attr.s
class AddonInfo(object):
    """Object matching json payload from Server"""
    name = attr.ib()
    version = attr.ib()
    title = attr.ib(default=None)
    sources = attr.ib(default=attr.Factory(dict))
    hash = attr.ib(default=None)
    description = attr.ib(default=None)
    license = attr.ib(default=None)
    authors = attr.ib(default=None)

    @classmethod
    def from_dict(cls, data):
        sources = []

        production_version = data.get("productionVersion")
        if not production_version:
            return

        # server payload contains info about all versions
        # active addon must have 'productionVersion' and matching version info
        version_data = data.get("versions", {})[production_version]

        for source in version_data.get("clientSourceInfo", []):
            if source.get("type") == UrlType.FILESYSTEM.value:
                source_addon = LocalAddonSource(type=source["type"],
                                                path=source["path"])
            if source.get("type") == UrlType.HTTP.value:
                source_addon = WebAddonSource(type=source["type"],
                                              url=source["url"])

            sources.append(source_addon)

        return cls(name=data.get("name"),
                   version=production_version,
                   sources=sources,
                   hash=data.get("hash"),
                   description=data.get("description"),
                   title=data.get("title"),
                   license=data.get("license"),
                   authors=data.get("authors"))

