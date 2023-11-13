from __future__ import annotations

import opentimelineio as otio
import openpype.hosts.resolve.api as api


class VideoTrack(object):
    def __init__(self, *args) -> None:
        self.name: object
        self.index: int
        self.timeline: api.Timeline
        self.__jotio: dict

        if args:
            self.timeline = args[0]
            self.index = args[1]
            self.name = args[2]

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"{self.name}@i={self.index}"

    @property
    def clips(self) -> list(api.TimelineItem):
        return [
            api.TimelineItem(vti, self)
            for vti in self.timeline.root.GetItemListInTrack("video", self.index)
        ]

    @property
    def jotio(self):
        return self.__jotio

    @jotio.setter
    def jotio(self, val):
        self.__jotio = val

    def log_info(self, log):
        info = {
            "timeline": self.timeline,
            "name": self.name,
            "index": self.index,
            "clips": self.clips,
        }
        for k, v in info.items():
            log.debug(f"{k = }: {v = }")
