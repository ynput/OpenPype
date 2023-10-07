from openpype.client import get_last_version_by_subset_id
from openpype.pipeline import (
    get_representation_path,
    get_representation_context,
    get_current_project_name,
)
from openpype.hosts.resolve.api import lib, plugin
from openpype.hosts.resolve.api.pipeline import (
    containerise,
    update_container,
)
from openpype.lib.transcoding import (
    VIDEO_EXTENSIONS,
    IMAGE_EXTENSIONS
)


class LoadClip(plugin.TimelineItemLoader):
    """Load a subset to timeline as clip

    Place clip to timeline on its asset origin timings collected
    during conforming to project
    """

    families = ["render2d", "source", "plate", "render", "review"]

    representations = ["*"]
    extensions = set(
        ext.lstrip(".") for ext in IMAGE_EXTENSIONS.union(VIDEO_EXTENSIONS)
    )

    label = "Load as clip"
    order = -10
    icon = "code-fork"
    color = "orange"

    # for loader multiselection
    timeline = None

    # presets
    clip_color_last = "Olive"
    clip_color = "Orange"

    def load(self, context, name, namespace, options):

        # load clip to timeline and get main variables
        path = self.filepath_from_context(context)
        timeline_item = plugin.ClipLoader(
            self, context, path, **options).load()
        namespace = namespace or timeline_item.GetName()

        # update color of clip regarding the version order
        self.set_item_color(timeline_item, version=context["version"])

        data_imprint = self.get_tag_data(context, name, namespace)
        return containerise(
            timeline_item,
            name, namespace, context,
            self.__class__.__name__,
            data_imprint)

    def switch(self, container, representation):
        self.update(container, representation)

    def update(self, container, representation):
        """ Updating previously loaded clips
        """

        context = get_representation_context(representation)
        name = container['name']
        namespace = container['namespace']
        timeline_item = container["_timeline_item"]

        media_pool_item = timeline_item.GetMediaPoolItem()

        path = get_representation_path(representation)
        loader = plugin.ClipLoader(self, context, path)
        timeline_item = loader.update(timeline_item)

        # update color of clip regarding the version order
        self.set_item_color(timeline_item, version=context["version"])

        # if original media pool item has no remaining usages left
        # remove it from the media pool
        if int(media_pool_item.GetClipProperty("Usage")) == 0:
            lib.remove_media_pool_item(media_pool_item)

        data_imprint = self.get_tag_data(context, name, namespace)
        return update_container(timeline_item, data_imprint)

    def get_tag_data(self, context, name, namespace):
        """Return data to be imprinted on the timeline item marker"""

        representation = context["representation"]
        version = context['version']
        version_data = version.get("data", {})
        version_name = version.get("name", None)
        colorspace = version_data.get("colorspace", None)
        object_name = "{}_{}".format(name, namespace)

        # add additional metadata from the version to imprint Avalon knob
        # move all version data keys to tag data
        add_version_data_keys = [
            "frameStart", "frameEnd", "source", "author",
            "fps", "handleStart", "handleEnd"
        ]
        data = {
            key: version_data.get(key, "None") for key in add_version_data_keys
        }

        # add variables related to version context
        data.update({
            "representation": str(representation["_id"]),
            "version": version_name,
            "colorspace": colorspace,
            "objectName": object_name
        })
        return data

    @classmethod
    def set_item_color(cls, timeline_item, version):
        """Color timeline item based on whether it is outdated or latest"""
        # define version name
        version_name = version.get("name", None)
        # get all versions in list
        project_name = get_current_project_name()
        last_version_doc = get_last_version_by_subset_id(
            project_name,
            version["parent"],
            fields=["name"]
        )
        if last_version_doc:
            last_version = last_version_doc["name"]
        else:
            last_version = None

        # set clip colour
        if version_name == last_version:
            timeline_item.SetClipColor(cls.clip_color_last)
        else:
            timeline_item.SetClipColor(cls.clip_color)

    def remove(self, container):
        timeline_item = container["_timeline_item"]
        media_pool_item = timeline_item.GetMediaPoolItem()
        timeline = lib.get_current_timeline()

        if timeline.DeleteClips is not None:
            timeline.DeleteClips([timeline_item])

        # if media pool item has no remaining usages left
        # remove it from the media pool
        if int(media_pool_item.GetClipProperty("Usage")) == 0:
            lib.remove_media_pool_item(media_pool_item)
