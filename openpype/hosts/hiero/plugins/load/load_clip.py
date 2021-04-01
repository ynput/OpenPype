from avalon import io, api
import openpype.hosts.hiero.api as phiero
# from openpype.hosts.hiero.api import plugin, lib
# reload(lib)
# reload(plugin)
# reload(phiero)


class LoadClip(phiero.SequenceLoader):
    """Load a subset to timeline as clip

    Place clip to timeline on its asset origin timings collected
    during conforming to project
    """

    families = ["render2d", "source", "plate", "render", "review"]
    representations = ["exr", "dpx", "jpg", "jpeg", "png", "h264"]

    label = "Load as clip"
    order = -10
    icon = "code-fork"
    color = "orange"

    # for loader multiselection
    sequence = None
    track = None

    # presets
    clip_color_last = "green"
    clip_color = "red"

    def load(self, context, name, namespace, options):

        # in case loader uses multiselection
        if self.track and self.sequence:
            options.update({
                "sequence": self.sequence,
                "track": self.track
            })

        # load clip to timeline and get main variables
        track_item = phiero.ClipLoader(self, context, **options).load()
        namespace = namespace or track_item.name()
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
        self.set_item_color(track_item, version)

        # deal with multiselection
        self.multiselection(track_item)

        self.log.info("Loader done: `{}`".format(name))

        return phiero.containerise(
            track_item,
            name, namespace, context,
            self.__class__.__name__,
            data_imprint)

    def switch(self, container, representation):
        self.update(container, representation)

    def update(self, container, representation):
        """ Updating previously loaded clips
        """

        # load clip to timeline and get main variables
        name = container['name']
        namespace = container['namespace']
        track_item = phiero.get_track_items(
            track_item_name=namespace)
        version = io.find_one({
            "type": "version",
            "_id": representation["parent"]
        })
        version_data = version.get("data", {})
        version_name = version.get("name", None)
        colorspace = version_data.get("colorspace", None)
        object_name = "{}_{}".format(name, namespace)
        file = api.get_representation_path(representation).replace("\\", "/")

        # reconnect media to new path
        track_item.source().reconnectMedia(file)

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
        self.set_item_color(track_item, version)

        return phiero.update_container(track_item, data_imprint)

    def remove(self, container):
        """ Removing previously loaded clips
        """
        # load clip to timeline and get main variables
        namespace = container['namespace']
        track_item = phiero.get_track_items(
            track_item_name=namespace)
        track = track_item.parent()

        # remove track item from track
        track.removeItem(track_item)

    @classmethod
    def multiselection(cls, track_item):
        if not cls.track:
            cls.track = track_item.parent()
            cls.sequence = cls.track.parent()

    @classmethod
    def set_item_color(cls, track_item, version):

        # define version name
        version_name = version.get("name", None)
        # get all versions in list
        versions = io.find({
            "type": "version",
            "parent": version["parent"]
        }).distinct('name')

        max_version = max(versions)

        # set clip colour
        if version_name == max_version:
            track_item.source().binItem().setColor(cls.clip_color_last)
        else:
            track_item.source().binItem().setColor(cls.clip_color)
