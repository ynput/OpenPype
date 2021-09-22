import nuke
from avalon.vendor import qargparse
from avalon import api, io
from openpype.hosts.nuke.api.lib import (
    get_imageio_input_colorspace
)


class LoadSequence(api.Loader):
    """Load image sequence into Nuke"""

    families = ["render", "source", "plate", "review"]
    representations = ["exr", "dpx"]

    label = "Load Image Sequence"
    order = -20
    icon = "file-video-o"
    color = "white"

    script_start = nuke.root()["first_frame"].value()

    # option gui
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

        self.log.info("version_data: {}\n".format(version_data))
        self.log.debug(
            "Representation id `{}` ".format(repr_id))

        self.first_frame = int(nuke.root()["first_frame"].getValue())
        self.handle_start = version_data.get("handleStart", 0)
        self.handle_end = version_data.get("handleEnd", 0)

        first = version_data.get("frameStart", None)
        last = version_data.get("frameEnd", None)

        # Fallback to asset name when namespace is None
        if namespace is None:
            namespace = context['asset']['name']

        first -= self.handle_start
        last += self.handle_end

        file = self.fname

        if not file:
            repr_id = context["representation"]["_id"]
            self.log.warning(
                "Representation id `{}` is failing to load".format(repr_id))
            return

        file = file.replace("\\", "/")

        repr_cont = context["representation"]["context"]
        assert repr_cont.get("frame"), "Representation is not sequence"

        if "#" not in file:
            frame = repr_cont.get("frame")
            if frame:
                padding = len(frame)
                file = file.replace(frame, "#" * padding)

        name_data = {
            "asset": repr_cont["asset"],
            "subset": repr_cont["subset"],
            "representation": context["representation"]["name"],
            "ext": repr_cont["representation"],
            "id": context["representation"]["_id"],
            "class_name": self.__class__.__name__
        }

        read_name = self.node_name_template.format(**name_data)

        # Create the Loader with the filename path set
        read_node = nuke.createNode(
            "Read",
            "name {}".format(read_name))

        # to avoid multiple undo steps for rest of process
        # we will switch off undo-ing
        with viewer_update_and_undo_stop():
            read_node["file"].setValue(file)

            # Set colorspace defined in version data
            colorspace = context["version"]["data"].get("colorspace")
            if colorspace:
                read_node["colorspace"].setValue(str(colorspace))

            preset_clrsp = get_imageio_input_colorspace(file)

            if preset_clrsp is not None:
                read_node["colorspace"].setValue(preset_clrsp)

            # set start frame depending on workfile or version
            self.loader_shift(read_node, start_at_workfile)
            read_node["origfirst"].setValue(int(first))
            read_node["first"].setValue(int(first))
            read_node["origlast"].setValue(int(last))
            read_node["last"].setValue(int(last))

            # add additional metadata from the version to imprint Avalon knob
            add_keys = ["frameStart", "frameEnd",
                        "source", "colorspace", "author", "fps", "version",
                        "handleStart", "handleEnd"]

            data_imprint = {}
            for k in add_keys:
                if k == 'version':
                    data_imprint.update({k: context["version"]['name']})
                else:
                    data_imprint.update(
                        {k: context["version"]['data'].get(k, str(None))})

            data_imprint.update({"objectName": read_name})

            read_node["tile_color"].setValue(int("0x4ecd25ff", 16))

            if version_data.get("retime", None):
                speed = version_data.get("speed", 1)
                time_warp_nodes = version_data.get("timewarps", [])
                self.make_retimes(speed, time_warp_nodes)

            return containerise(read_node,
                                name=name,
                                namespace=namespace,
                                context=context,
                                loader=self.__class__.__name__,
                                data=data_imprint)

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

        repr_cont = representation["context"]
        assert repr_cont.get("frame"), "Representation is not sequence"

        file = api.get_representation_path(representation)

        if not file:
            repr_id = representation["_id"]
            self.log.warning(
                "Representation id `{}` is failing to load".format(repr_id))
            return

        file = file.replace("\\", "/")

        if "#" not in file:
            frame = repr_cont.get("frame")
            if frame:
                padding = len(frame)
                file = file.replace(frame, "#" * padding)

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

        self.first_frame = int(nuke.root()["first_frame"].getValue())
        self.handle_start = version_data.get("handleStart", 0)
        self.handle_end = version_data.get("handleEnd", 0)

        first = version_data.get("frameStart")
        last = version_data.get("frameEnd")

        if first is None:
            self.log.warning(
                "Missing start frame for updated version"
                "assuming starts at frame 0 for: "
                "{} ({})".format(read_node['name'].value(), representation))
            first = 0

        first -= self.handle_start
        last += self.handle_end

        read_node["file"].setValue(file)

        # set start frame depending on workfile or version
        self.loader_shift(
            read_node,
            bool("start at" in read_node['frame_mode'].value()))

        read_node["origfirst"].setValue(int(first))
        read_node["first"].setValue(int(first))
        read_node["origlast"].setValue(int(last))
        read_node["last"].setValue(int(last))

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
            "outputDir": version_data.get("outputDir"),
        })

        # change color of read_node
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
            read_node,
            updated_dict
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

    def loader_shift(self, read_node, workfile_start=False):
        """ Set start frame of read node to a workfile start

        Args:
            read_node (nuke.Node): The nuke's read node
            workfile_start (bool): set workfile start frame if true

        """
        if workfile_start:
            read_node['frame_mode'].setValue("start at")
            read_node['frame'].setValue(str(self.script_start))
