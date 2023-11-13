from __future__ import annotations

import openpype.hosts.resolve.api as api


class MediapoolItem(object):
    def __init__(self, *args) -> object:
        self.__root_object: object

        if args:
            self.__root_object = args[0]

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"{self.name}@{self.id}"

    @property
    def root(self) -> object:
        return self.__root_object

    @property
    def id(self) -> str:
        return self.root.GetUniqueId()

    @property
    def name(self) -> str:
        return self.root.GetName()

    @property
    def properties(self) -> dict:
        result = self.root.GetMetadata()
        result.update(self.root.GetClipProperty())
        return result

    @property
    def fps(self) -> float:
        return float(self.properties["FPS"])
