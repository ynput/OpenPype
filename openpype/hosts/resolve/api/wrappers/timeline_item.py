from __future__ import annotations

import openpype.hosts.resolve.api as api


class TimelineItem(object):
    def __init__(self, *args) -> object:
        self.__jotio: dict
        self.__index: int
        self.__root_object: object
        self.__video_track: api.VideoTrack

        if args:
            self.__root_object = args[0]
            self.__video_track = args[1]
            self.__index = args[2]

        # initialize jotio
        items = []
        for i in self.video_track.jotio["children"]:
            if i["OTIO_SCHEMA"] not in ["Clip.1", "Clip.2"]:
                continue
            items.append(i)
        self.jotio = items[self.__index]

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
    def index(self) -> int:
        return self.__index

    @property
    def color(self) -> str:
        return self.root.GetClipColor()

    @property
    def source(self) -> api.MediaPoolItem:
        result = api.MediapoolItem(self.root.GetMediaPoolItem())
        return result

    @property
    def video_track(self) -> api.VideoTrack:
        return self.__video_track

    @property
    def is_retimed(self) -> bool:
        for e in self.jotio["effects"]:
            if e["OTIO_SCHEMA"] in ["LinearTimeWarp.1", "TimeEffect.1"]:
                return True
        return False
    @property
    def jotio(self) -> dict:
        return self.__jotio

    @jotio.setter
    def jotio(self, val):
        self.__jotio = val

    def log_info(self, log):
        info = {
            "id": self.id,
            "name": self.name,
            "video_track": self.video_track,
        }
        for k, v in info.items():
            log.debug(f"{k = }: {v = }")
