import json

from openpype.client import (
    get_version_by_id,
    get_last_version_by_subset_id,
)
from openpype.pipeline import (
    LoaderPlugin,
    get_representation_path
)
from openpype.pipeline.context_tools import get_current_project_name
from openpype.hosts.resolve.api import lib
from openpype.hosts.resolve.api.pipeline import AVALON_CONTAINER_ID
from openpype.lib.transcoding import (
    VIDEO_EXTENSIONS,
    IMAGE_EXTENSIONS
)


class LoadMedia(LoaderPlugin):
    """Load a subset as media pool item."""

    families = ["render2d", "source", "plate", "render", "review"]

    representations = ["*"]
    extensions = set(
        ext.lstrip(".") for ext in IMAGE_EXTENSIONS.union(VIDEO_EXTENSIONS)
    )

    label = "Load media"
    order = -10
    icon = "code-fork"
    color = "orange"

    # for loader multiselection
    timeline = None

    # presets
    clip_color_last = "Olive"
    clip_color = "Orange"

    bin_path = "Loader/{representation[context][hierarchy]}/{asset[name]}"

    def load(self, context, name, namespace, options):

        # For loading multiselection, we store timeline before first load
        # because the current timeline can change with the imported media.
        if self.timeline is None:
            self.timeline = lib.get_current_timeline()

        representation = context["representation"]

        project = lib.get_current_project()
        media_pool = project.GetMediaPool()

        # Create or set the bin folder, we add it in there
        # If bin path is not set we just add into the current active bin
        if self.bin_path:
            bin_path = self.bin_path.format(**context)
            lib.create_bin(
                name=bin_path,
                root=media_pool.GetRootFolder()
            )

        # TODO: Correctly set the media path for image sequences
        # frames = [
        #     "path/to/frame.1001.exr",
        #     "path/to/frame.1002.exr"
        # ]
        path = get_representation_path(representation)
        items = media_pool.ImportMedia(path)
        assert len(items) == 1, "Must import only one media item"

        item = items[0]
        color = self.get_item_color(representation)
        item.SetClipColor(color)

        data = self._get_container_data(representation)

        # Add containerise data only needed on first load
        data.update({
            "schema": "openpype:container-2.0",
            "id": AVALON_CONTAINER_ID,
            "name": str(name),
            "namespace": str(namespace),
            "loader": str(self.__class__.__name__),
        })

        item.SetMetadata(lib.pype_tag_name, json.dumps(data))

        timeline = options.get("timeline", self.timeline)
        if timeline:
            # Add media to active timeline
            lib.create_timeline_item(
                media_pool_item=item,
                timeline=timeline
            )

    def switch(self, container, representation):
        self.update(container, representation)

    def update(self, container, representation):
        # Update MediaPoolItem filepath and metadata
        item = container["_item"]

        # Get the existing metadata before we update because the
        # metadata gets removed
        data = json.loads(item.GetMetadata(lib.pype_tag_name))

        # Update path
        path = get_representation_path(representation)
        item.ReplaceClip(path)

        # Update the metadata
        update_data = self._get_container_data(representation)
        data.update(update_data)
        item.SetMetadata(lib.pype_tag_name, json.dumps(data))

        # Update the clip color
        color = self.get_item_color(representation)
        item.SetClipColor(color)

    def remove(self, container):
        # Remove MediaPoolItem entry
        project = lib.get_current_project()
        media_pool = project.GetMediaPool()
        item = container["_item"]
        media_pool.DeleteClips([item])

    def _get_container_data(self, representation):
        """Return metadata related to the representation and version."""

        # load clip to timeline and get main variables
        project_name = get_current_project_name()
        version = get_version_by_id(project_name, representation["parent"])
        version_data = version.get("data", {})
        version_name = version.get("name", None)
        colorspace = version_data.get("colorspace", None)

        # add additional metadata from the version to imprint Avalon knob
        add_keys = [
            "frameStart", "frameEnd", "source", "author",
            "fps", "handleStart", "handleEnd"
        ]
        data = {
            key: version_data.get(key, str(None)) for key in add_keys
        }

        # add variables related to version context
        data.update({
            "representation": str(representation["_id"]),
            "version": version_name,
            "colorspace": colorspace,
        })

        return data

    @classmethod
    def get_item_color(cls, representation):
        # Compare version with last version
        project_name = get_current_project_name()
        version = get_version_by_id(
            project_name,
            representation["parent"],
            fields=["name", "parent"]
        )
        last_version = get_last_version_by_subset_id(
            project_name,
            version["parent"],
            fields=["name"]
        ) or {}

        # set clip colour
        if version.get("name") == last_version.get("name"):
            return cls.clip_color_last
        else:
            return cls.clip_color
