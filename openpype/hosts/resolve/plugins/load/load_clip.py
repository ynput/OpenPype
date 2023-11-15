from copy import deepcopy

from openpype.client import (
    get_version_by_id,
    get_last_version_by_subset_id,
)
# from openpype.hosts import resolve
from openpype.pipeline import (
    get_representation_path,
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

        # in case loader uses multiselection
        if self.timeline:
            options.update({
                "timeline": self.timeline,
            })

        # load clip to timeline and get main variables
        path = self.filepath_from_context(context)
        timeline_item = plugin.ClipLoader(
            self, context, path, **options).load()
        namespace = namespace or timeline_item.GetName()
        version = context['version']
        version_data = version.get("data", {})
        version_name = version.get("name", None)
        colorspace = version_data.get("colorspace", None)
        object_name = "{}_{}".format(name, namespace)

        # add additional metadata from the version to imprint Avalon knob
        add_keys = [
            "frameStart", "frameEnd", "source", "author",
            "fps", "handleStart", "handleEnd"
        ]

        # move all version data keys to tag data
        data_imprint = {}
        for key in add_keys:
            data_imprint.update({
                key: version_data.get(key, str(None))
            })

        # add variables related to version context
        data_imprint.update({
            "version": version_name,
            "colorspace": colorspace,
            "objectName": object_name
        })

        # update color of clip regarding the version order
        self.set_item_color(timeline_item, version)

        self.log.info("Loader done: `{}`".format(name))

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

        # load clip to timeline and get main variables
        context = deepcopy(representation["context"])
        context.update({"representation": representation})
        name = container['name']
        namespace = container['namespace']
        timeline_item_data = lib.get_pype_timeline_item_by_name(namespace)
        timeline_item = timeline_item_data["clip"]["item"]
        project_name = get_current_project_name()
        version = get_version_by_id(project_name, representation["parent"])
        version_data = version.get("data", {})
        version_name = version.get("name", None)
        colorspace = version_data.get("colorspace", None)
        object_name = "{}_{}".format(name, namespace)
        path = get_representation_path(representation)
        context["version"] = {"data": version_data}

        loader = plugin.ClipLoader(self, context, path)
        timeline_item = loader.update(timeline_item)

        # add additional metadata from the version to imprint Avalon knob
        add_keys = [
            "frameStart", "frameEnd", "source", "author",
            "fps", "handleStart", "handleEnd"
        ]

        # move all version data keys to tag data
        data_imprint = {}
        for key in add_keys:
            data_imprint.update({
                key: version_data.get(key, str(None))
            })

        # add variables related to version context
        data_imprint.update({
            "representation": str(representation["_id"]),
            "version": version_name,
            "colorspace": colorspace,
            "objectName": object_name
        })

        # update color of clip regarding the version order
        self.set_item_color(timeline_item, version)

        return update_container(timeline_item, data_imprint)

    @classmethod
    def set_item_color(cls, timeline_item, version):
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
