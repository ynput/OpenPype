from avalon import io, api
import openpype.hosts.flame.api as opfapi


class LoadClip(opfapi.ClipLoader):
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

    clip_name_template = "{asset}_{subset}_{representation}"

    def load(self, context, name, namespace, options):

        # load clip to timeline and get main variables
        namespace = namespace
        version = context['version']
        version_data = version.get("data", {})
        version_name = version.get("name", None)
        colorspace = version_data.get("colorspace", None)
        clip_name = self.clip_name_template.format(
            **context["representation"]["context"])

        # todo: settings in imageio
        # convert colorspace with ocio to flame mapping
        # in imageio flame section
        colorspace = colorspace

        # create new workfile version in conform task for _v###.clip
        # every new version is also the *_latest.clip
        openclip_name = clip_name

        # prepare Reel group in actual desktop
        reel_object = "prepared reel object"

        # prepare clip data from context ad send it to openClipLoader
        loading_context = {
            "path": self.fname.replace("\\", "/"),
            "colorspace": colorspace,
            "clip_name": openclip_name,
            "reel_object": reel_object

        }

        # with maintained openclip as opc
        opc = "loaded open pype clip "
        # opc set in and out marks if handles

        # opc refresh versions

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
            "objectName": clip_name
        })

        # unwrap segment from clip
        open_clip_segment = self._get_segment_from_clip(opc)

        return opfapi.containerise(
            open_clip_segment,
            name, namespace, context,
            self.__class__.__name__,
            data_imprint)

    def _get_segment_from_clip(self, clip):
        # unwrapping segment from input clip
        pass

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
        clip = track_item.source()

        # reconnect media to new path
        clip.reconnectMedia(file)

        # set colorspace
        if colorspace:
            clip.setSourceMediaColourTransform(colorspace)

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

        clip = track_item.source()
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
            clip.binItem().setColor(cls.clip_color_last)
        else:
            clip.binItem().setColor(cls.clip_color)
