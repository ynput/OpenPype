from __future__ import annotations

import opentimelineio as otio
import openpype.hosts.resolve.api as api


class TimelineItem(object):
    def __init__(self, *args) -> object:
        self.__jotio: dict
        self.__index: int
        self.__root_object: object
        self.__video_track: api.VideoTrack
        self.linear_timeremap_effect: dict
        self.keyframed_timeremap_effect: dict

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
    def is_enabled(self) -> bool:
        raise NotImplementedError

    @property
    def is_offline(self) -> bool:
        raise NotImplementedError

    @property
    def is_linear_timeremap(self) -> bool:
        for e in self.jotio["effects"]:
            if e["OTIO_SCHEMA"] == "LinearTimeWarp.1":
                self.linear_timeremap_effect = e
                return True
        return False

    @property
    def is_keyframed_timeremap(self) -> bool:
        for e in self.jotio["effects"]:
            if e["OTIO_SCHEMA"] == "TimeEffect.1":
                self.keyframed_timeremap_effect = e
                return True
        return False

    @property
    def head_in(self) -> int:
        tc = self.source.properties["Start TC"]
        rt = otio.opentime.from_timecode(tc, self.source.fps)
        return int(otio.opentime.to_frames(rt))

    @property
    def tail_out(self) -> int:
        tc = self.source.properties["End TC"]
        rt = otio.opentime.from_timecode(tc, self.source.fps)
        return int(otio.opentime.to_frames(rt))

    @property
    def timeline_duration(self) -> int:
        result = int(self.root.GetDuration())
        return result

    @property
    def real_source_duration(self) -> int:
        result = self.timeline_duration

        if self.is_linear_timeremap:
            time_scalar = float(self.linear_timeremap_effect["time_scalar"])
            result *= time_scalar
        if self.is_keyframed_timeremap:
            # TODO: make sense out of the otio metadata
            pass
        return result

    @property
    def left_offset(self) -> int:
        return self.root.GetLeftOffset()

    @property
    def src_in(self) -> int:
        result = self.head_in + self.left_offset
        return result

    @property
    def src_out(self) -> int:
        result = self.src_in + self.real_source_duration
        return result

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
