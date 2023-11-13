from __future__ import annotations

import openpype.hosts.resolve.api as api


class TimelineItem(object):
    def __init__(self, *args) -> object:
        self.__root_object: object
        self.__video_track: api.VideoTrack

        if args:
            self.__root_object = args[0]
            self.__video_track = args[1]

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
    def video_track(self) -> api.VideoTrack:
        return self.__video_track

    def log_info(self, log):
        info = {
            "id": self.id,
            "name": self.name,
            "video_track": self.video_track,
        }
        for k, v in info.items():
            log.debug(f"{k = }: {v = }")
