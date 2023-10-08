from openpype.hosts.resolve.api import lib, plugin
from openpype.lib import BoolDef


class LoadOtioTimeline(plugin.TimelineItemLoader):
    """Load OTIO as timeline (unmanaged after import)"""

    families = ["*"]
    representations = ["*"]
    extensions = {"otio"}

    label = "Import OTIO timeline"
    order = -10
    icon = "code-fork"
    color = "orange"

    options = [
        BoolDef("importSourceClips",
                label="Import source clips",
                tooltip="Automatically import source clips into media pool",
                default=True)
    ]

    def load(self, context, name, namespace, options):

        project = lib.get_current_project()
        if not project:
            raise RuntimeError("Must have active project to load timeline")

        media_pool = project.GetMediaPool()
        path = self.filepath_from_context(context)

        # Ensure a unique name, because the timeline name must be unique
        # within the current media pool folder otherwise no import will occur
        # and no error gets raised either
        clips = media_pool.GetCurrentFolder().GetClipList()
        clip_names = {clip.GetName() for clip in clips}
        if name in clip_names:
            self.log.debug(f"Renaming to unique clip name for: {name}")
            i = 1
            while "{}{}".format(name, i) in clip_names:
                i += 1
            name = "{}{}".format(name, i)

        # It seems `importSourceClips` does not work as intended by Resolve API
        # See: https://forum.blackmagicdesign.com/viewtopic.php?f=21&t=189958
        timeline = media_pool.ImportTimelineFromFile(
            path, {
                "timelineName": name,
                "importSourceClips": options.get("importSourceClips", True)
            }
        )
        if not timeline:
            raise RuntimeError("Failed to import timeline")
