from __future__ import annotations

import openpype.hosts.resolve.api as api


class Project(object):
    def __init__(self, *args, **kwargs) -> object:
        self.__root_object: object

        if len(args) > 0:
            self.__root_object = args[0]
            return
        # ? shall we implement getter/creator logic here based on ID/Name

    @property
    def root(self) -> object:
        # returns BlackmagicFusion.PyRemoteObject
        return self.__root_object

    @root.setter
    def root(self, obj):
        self.__root_object = obj

    @property
    def id(self) -> str:
        return self.root.GetUniqueId()

    @property
    def name(self) -> str:
        return self.root.GetName()

    @property
    def mediapool(self):
        return self.current_project.GetMediaPool()

    @property
    def timelines(self) -> list(api.Timeline):
        # NOTE: resolve saves Timelines with 1-based indices
        return [
            api.Timeline(self.root.GetTimelineByIndex(i))
            for i in range(1, self.root.GetTimelineCount() + 1)
        ]

    def log_info(self, log):
        info = {
            "id": self.id,
            "name": self.name,
            "timelines": self.timelines,
        }
        for k, v in info.items():
            log.debug(f"{k = }: {v = }")
