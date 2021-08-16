import nuke
from avalon.vendor import qargparse
from avalon import api, io
from openpype.api import get_current_project_settings
from openpype.hosts.nuke.api.lib import (
    get_imageio_input_colorspace
)


def add_review_presets_config():
    returning = {
        "families": list(),
        "representations": list()
    }
    settings = get_current_project_settings()
    review_profiles = (
        settings["global"]
                ["publish"]
                ["ExtractReview"]
                ["profiles"]
    )

    outputs = {}
    for profile in review_profiles:
        outputs.update(profile.get("outputs", {}))

    for output, properities in outputs.items():
        returning["representations"].append(output)
        returning["families"] += properities.get("families", [])

    return returning


class LoadMov(api.Loader):
    """Load mov file into Nuke"""
    families = ["render", "source", "plate", "review"]
    representations = ["mov", "review", "mp4"]

    label = "Load mov"
    order = -10
    icon = "code-fork"
    color = "orange"

    first_frame = nuke.root()["first_frame"].value()

    # options gui
    defaults = {
        "start_at_workfile": True
    }

    options = [
        qargparse.Boolean(
            "start_at_workfile",
            help="Load at workfile start frame",
            default=True
        )
    ]

    node_name_template = "{class_name}_{ext}"

    def load(self, context, name, namespace, options):
        from avalon.nuke import (
            containerise,
            viewer_update_and_undo_stop
        )

        start_at_workfile = options.get(
            "start_at_workfile", self.defaults["start_at_workfile"])

        version = context['version']
        version_data = version.get("data", {})
        repr_id = context["representation"]["_id"]

        self.handle_start = version_data.get("handleStart", 0)
        self.handle_end = version_data.get("handleEnd", 0)

        orig_first = version_data.get("frameStart")
        orig_last = version_data.get("frameEnd")
        diff = orig_first - 1

        first = orig_first - diff
        last = orig_last - diff

        colorspace = version_data.get("colorspace")
        repr_cont = context["representation"]["context"]

        self.log.debug(
            "Representation id `{}` ".format(repr_id))

        context["representation"]["_id"]
        # create handles offset (only to last, because of mov)
        last += self.handle_start + self.handle_end

        # Fallback to asset name when namespace is None
        if namespace is None:
            namespace = context['asset']['name']

        file = self.fname

        if not file:
            self.log.warning(
                "Representation id `{}` is failing to load".format(repr_id))
            return

        file = file.replace("\\", "/")

        name_data = {
            "asset": repr_cont["asset"],
            "subset": repr_cont["subset"],
            "representation": context["representation"]["name"],
            "ext": repr_cont["representation"],
            "id": context["representation"]["_id"],
            "class_name": self.__class__.__name__
        }

        read_name = self.node_name_template.format(**name_data)

        read_node = nuke.createNode(
            "Read",
            "name {}".format(read_name)
        )

        # to avoid multiple undo steps for rest of process
        # we will switch off undo-ing
        with viewer_update_and_undo_stop():
            read_node["file"].setValue(file)

            read_node["origfirst"].setValue(first)
            read_node["first"].setValue(first)
            read_node["origlast"].setValue(last)
            read_node["last"].setValue(last)
            read_node['frame_mode'].setValue("start at")

            if start_at_workfile:
                # start at workfile start
                read_node['frame'].setValue(str(self.first_frame))
            else:
                # start at version frame start
                read_node['frame'].setValue(
                    str(orig_first - self.handle_start))

            if colorspace:
                read_node["colorspace"].setValue(str(colorspace))

            preset_clrsp = get_imageio_input_colorspace(file)

            if preset_clrsp is not None:
                read_node["colorspace"].setValue(preset_clrsp)

            # add additional metadata from the version to imprint Avalon knob
            add_keys = [
                "frameStart", "frameEnd", "handles", "source", "author",
                "fps", "version", "handleStart", "handleEnd"
            ]

            data_imprint = {}
            for key in add_keys:
                if key == 'version':
                    data_imprint.update({
                        key: context["version"]['name']
                    })
                else:
                    data_imprint.update({
                        key: context["version"]['data'].get(key, str(None))
                    })

            data_imprint.update({"objectName": read_name})

            read_node["tile_color"].setValue(int("0x4ecd25ff", 16))

            if version_data.get("retime", None):
                speed = version_data.get("speed", 1)
                time_warp_nodes = version_data.get("timewarps", [])
                self.make_retimes(speed, time_warp_nodes)

            return containerise(
                read_node,
                name=name,
                namespace=namespace,
                context=context,
                loader=self.__class__.__name__,
                data=data_imprint
            )

    def switch(self, container, representation):
        self.update(container, representation)

    def update(self, container, representation):
        """Update the Loader's path

        Nuke automatically tries to reset some variables when changing
        the loader's path to a new file. These automatic changes are to its
        inputs:

        """

        from avalon.nuke import (
            update_container
        )

        read_node = nuke.toNode(container['objectName'])

        assert read_node.Class() == "Read", "Must be Read"

        file = self.fname

        if not file:
            repr_id = representation["_id"]
            self.log.warning(
                "Representation id `{}` is failing to load".format(repr_id))
            return

        file = file.replace("\\", "/")

        # Get start frame from version data
        version = io.find_one({
            "type": "version",
            "_id": representation["parent"]
        })

        # get all versions in list
        versions = io.find({
            "type": "version",
            "parent": version["parent"]
        }).distinct('name')

        max_version = max(versions)

        version_data = version.get("data", {})

        orig_first = version_data.get("frameStart")
        orig_last = version_data.get("frameEnd")
        diff = orig_first - 1

        # set first to 1
        first = orig_first - diff
        last = orig_last - diff
        self.handle_start = version_data.get("handleStart", 0)
        self.handle_end = version_data.get("handleEnd", 0)
        colorspace = version_data.get("colorspace")

        if first is None:
            self.log.warning((
                "Missing start frame for updated version"
                "assuming starts at frame 0 for: "
                "{} ({})").format(
                    read_node['name'].value(), representation))
            first = 0

        # create handles offset (only to last, because of mov)
        last += self.handle_start + self.handle_end

        read_node["file"].setValue(file)

        # Set the global in to the start frame of the sequence
        read_node["origfirst"].setValue(first)
        read_node["first"].setValue(first)
        read_node["origlast"].setValue(last)
        read_node["last"].setValue(last)
        read_node['frame_mode'].setValue("start at")

        if int(float(self.first_frame)) == int(
                float(read_node['frame'].value())):
            # start at workfile start
            read_node['frame'].setValue(str(self.first_frame))
        else:
            # start at version frame start
            read_node['frame'].setValue(str(orig_first - self.handle_start))

        if colorspace:
            read_node["colorspace"].setValue(str(colorspace))

        preset_clrsp = get_imageio_input_colorspace(file)

        if preset_clrsp is not None:
            read_node["colorspace"].setValue(preset_clrsp)

        updated_dict = {}
        updated_dict.update({
            "representation": str(representation["_id"]),
            "frameStart": str(first),
            "frameEnd": str(last),
            "version": str(version.get("name")),
            "colorspace": version_data.get("colorspace"),
            "source": version_data.get("source"),
            "handleStart": str(self.handle_start),
            "handleEnd": str(self.handle_end),
            "fps": str(version_data.get("fps")),
            "author": version_data.get("author"),
            "outputDir": version_data.get("outputDir")
        })

        # change color of node
        if version.get("name") not in [max_version]:
            read_node["tile_color"].setValue(int("0xd84f20ff", 16))
        else:
            read_node["tile_color"].setValue(int("0x4ecd25ff", 16))

        if version_data.get("retime", None):
            speed = version_data.get("speed", 1)
            time_warp_nodes = version_data.get("timewarps", [])
            self.make_retimes(speed, time_warp_nodes)

        # Update the imprinted representation
        update_container(
            read_node, updated_dict
        )
        self.log.info("udated to version: {}".format(version.get("name")))

    def remove(self, container):

        from avalon.nuke import viewer_update_and_undo_stop

        read_node = nuke.toNode(container['objectName'])
        assert read_node.Class() == "Read", "Must be Read"

        with viewer_update_and_undo_stop():
            nuke.delete(read_node)

    def make_retimes(self, speed, time_warp_nodes):
        ''' Create all retime and timewarping nodes with coppied animation '''
        if speed != 1:
            rtn = nuke.createNode(
                "Retime",
                "speed {}".format(speed))
            rtn["before"].setValue("continue")
            rtn["after"].setValue("continue")
            rtn["input.first_lock"].setValue(True)
            rtn["input.first"].setValue(
                self.first_frame
            )

        if time_warp_nodes != []:
            start_anim = self.first_frame + (self.handle_start / speed)
            for timewarp in time_warp_nodes:
                twn = nuke.createNode(timewarp["Class"],
                                      "name {}".format(timewarp["name"]))
                if isinstance(timewarp["lookup"], list):
                    # if array for animation
                    twn["lookup"].setAnimated()
                    for i, value in enumerate(timewarp["lookup"]):
                        twn["lookup"].setValueAt(
                            (start_anim + i) + value,
                            (start_anim + i))
                else:
                    # if static value `int`
                    twn["lookup"].setValue(timewarp["lookup"])
