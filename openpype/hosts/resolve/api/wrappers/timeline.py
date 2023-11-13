from __future__ import annotations

import json
from pathlib import Path
import opentimelineio as otio
import DaVinciResolveScript as bmd
import openpype.hosts.resolve.api as api


TRACK_TYPES = {
    "video": otio.schema.TrackKind.Video,
    "audio": otio.schema.TrackKind.Audio,
}


class Timeline(object):
    def __init__(self, *args, **kwargs) -> object:
        self.__otio: otio.schema.Timeline
        self.__jotio: dict
        self.__root_object: object

        if args:
            self.__root_object = args[0]
            return

        # create new Timeline?

    @property
    def root(self) -> object:
        # returns BlackmagicFusion.PyRemoteObject
        return self.__root_object

    def __repr__(self) -> str:
        return f"{self.name}@{self.id}"

    def __str__(self) -> str:
        return self.name

    @property
    def id(self) -> str:
        return self.root.GetUniqueId()

    @property
    def name(self) -> str:
        return self.root.GetName()

    @property
    def video_tracks(self) -> list(api.VideoTrack):
        return [
            api.VideoTrack(self, i, self.root.GetTrackName("video", i))
            for i in range(1, self.root.GetTrackCount("video") + 1)
        ]

    @property
    def clips(self) -> list(api.TimelineItem):
        return [
            api.TimelineItem(ti, vt)
            for vt in self.video_tracks
            for ti in self.root.GetItemListInTrack("video", vt.index)
        ]

    @property
    def otio(self) -> otio.schema.Timeline:
        return self.__otio

    @otio.setter
    def otio(self, val):
        self.__otio = val

    @property
    def jotio(self) -> dict:
        return self.__jotio

    @jotio.setter
    def jotio(self, val):
        self.__jotio = val

    @property
    def otio_export_path(self) -> Path:
        return Path.home() / "bestlength_otios" / f"{self.name}.otio"

    def export_otio(self):
        # TODO: get ayon setting
        self.otio_export_path.parent.mkdir(parents=True, exist_ok=True)
        self.root.Export(
            str(self.otio_export_path),
            bmd.scriptapp("Resolve").EXPORT_OTIO,
            bmd.scriptapp("Resolve").EXPORT_NONE,
        )

    def import_bestlength_otio(self):
        self.otio = otio.adapters.read_from_file(str(self.otio_export_path))
        self.jotio = json.loads(self.otio.to_json_string())
        # return otio.adapters.read_from_file(str(self.otio_export_path))

    def log_info(self, log):
        info = {
            "id": self.id,
            "name": self.name,
            "video_tracks": self.video_tracks,
            "clips": self.clips,
            "#clips": len(self.clips),
        }

        for k, v in info.items():
            log.debug(f"{k = }: {v = }")
