import sys
import DaVinciResolveScript
import opentimelineio as otio


self = sys.modules[__name__]
self.resolve = DaVinciResolveScript.scriptapp('Resolve')
self.fusion = DaVinciResolveScript.scriptapp('Fusion')
self.project_manager = self.resolve.GetProjectManager()
self.current_project = self.project_manager.GetCurrentProject()
self.media_pool = self.current_project.GetMediaPool()
self.track_types = {
    "video": otio.schema.TrackKind.Video,
    "audio": otio.schema.TrackKind.Audio
}
self.project_fps = None


def build_timeline(otio_timeline):
    for clip in otio_timeline.each_clip():
        print(clip.name)
        print(clip.parent().name)
        print(clip.range_in_parent())


def _build_track(otio_track):
    pass


def _build_media_pool_item(otio_media_reference):
    pass


def _build_track_item(otio_clip):
    pass


def _build_gap(otio_clip):
    pass


def _build_marker(otio_marker):
    pass


def read_from_file(otio_file):
    otio_timeline = otio.adapters.read_from_file(otio_file)
    build_timeline(otio_timeline)
