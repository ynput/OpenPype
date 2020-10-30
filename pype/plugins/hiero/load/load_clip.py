import hiero
from pype.hosts import hiero as phiero
reload(phiero)


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

    # presets
    clip_color_last = "green"
    clip_color = "red"

    def load(self, context, name, namespace, options):

        # add additional metadata from the version to imprint Avalon knob
        add_keys = [
            "frameStart", "frameEnd", "source", "author",
            "fps", "version", "handleStart", "handleEnd"
        ]
        version = None
        data_imprint = {}
        for key in add_keys:
            if key == 'version':
                version = context["version"]['name']
                data_imprint.update({
                    key: version
                })
            else:
                data_imprint.update({
                    key: context["version"]['data'].get(key, str(None))
                })

        # load clip to timeline
        track_item = phiero.ClipLoader(self, context, **options).load()

        # set clip colour
        if version:
            track_item.source().binItem().setColor(self.clip_color_last)
        else:
            track_item.source().binItem().setColor(self.clip_color)

        namespace = track_item.name()
        data_imprint["objectName"] = namespace

        phiero.containerise(
            track_item,
            name, namespace, context,
            self.__class__.__name__,
            data_imprint)

        self.log.info("Loader done: `{}`".format(name))

    def switch(self, container, representation):
        self.update(container, representation)

    def update(self, container, representation):
        """ Updating previously loaded clips
        """
        print "____________ loader update"
        print container['namespace']
        track_item = phiero.get_track_items(
            track_item_name=container['namespace'])
        print track_item

    def remove(self, container):
        """ Removing previously loaded clips
        """
        pass
