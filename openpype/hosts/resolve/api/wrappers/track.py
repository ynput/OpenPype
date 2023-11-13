from __future__ import annotations

import opentimelineio as otio
import openpype.hosts.resolve.api as api


class VideoTrack(object):
    def __init__(self, *args) -> None:
        self.name: object
        self.index: int
        self.timeline: api.Timeline
        self.__otio: otio.schema.Track

        if args:
            self.timeline = args[0]
            self.name = args[2]
            self.index = args[1]

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
    def otio(self):
        return self.__otio

    @otio.setter
    def otio(self, val):
        self.__otio = val

    def log_info(self, log):
        info = {
            "timeline": self.timeline,
            "name": self.name,
            "index": self.index,
            "clips": self.clips,
        }
        for k, v in info.items():
            log.debug(f"{k = }: {v = }")
