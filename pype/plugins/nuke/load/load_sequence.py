import re
import nuke
import contextlib

from avalon import api, io
from pype.hosts.nuke import presets


@contextlib.contextmanager
def preserve_trim(node):
    """Preserve the relative trim of the Loader tool.

    This tries to preserve the loader's trim (trim in and trim out) after
    the context by reapplying the "amount" it trims on the clip's length at
    start and end.

    """
    # working script frame range
    script_start = nuke.root()["first_frame"].value()

    start_at_frame = None
    offset_frame = None
    if node['frame_mode'].value() == "start at":
        start_at_frame = node['frame'].value()
    if node['frame_mode'].value() == "offset":
        offset_frame = node['frame'].value()

    try:
        yield
    finally:
        if start_at_frame:
            node['frame_mode'].setValue("start at")
            node['frame'].setValue(str(script_start))
            print("start frame of Read was set to"
                  "{}".format(script_start))

        if offset_frame:
            node['frame_mode'].setValue("offset")
            node['frame'].setValue(str((script_start + offset_frame)))
            print("start frame of Read was set to"
                  "{}".format(script_start))


def loader_shift(node, frame, relative=True):
    """Shift global in time by i preserving duration

    This moves the loader by i frames preserving global duration. When relative
    is False it will shift the global in to the start frame.

    Args:
        loader (tool): The fusion loader tool.
        frame (int): The amount of frames to move.
        relative (bool): When True the shift is relative, else the shift will
            change the global in to frame.

    Returns:
        int: The resulting relative frame change (how much it moved)

    """
    # working script frame range
    script_start = nuke.root()["first_frame"].value()

    if relative:
        node['frame_mode'].setValue("start at")
        node['frame'].setValue(str(frame))

    return int(script_start)


class LoadSequence(api.Loader):
    """Load image sequence into Nuke"""

    families = ["render2d", "source", "plate", "render", "prerender"]
    representations = ["exr", "dpx", "jpg", "jpeg", "png"]

    label = "Load sequence"
    order = -10
    icon = "code-fork"
    color = "orange"

    def load(self, context, name, namespace, data):
        from avalon.nuke import (
            containerise,
            viewer_update_and_undo_stop
        )

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
        if "#" not in file:
            frame = repr_cont.get("frame")
            padding = len(frame)
            file = file.replace(frame, "#"*padding)

        read_name = "Read_{0}_{1}_{2}".format(
                                        repr_cont["asset"],
                                        repr_cont["subset"],
                                        repr_cont["representation"])

        # Create the Loader with the filename path set
        with viewer_update_and_undo_stop():
            # TODO: it might be universal read to img/geo/camera
            r = nuke.createNode(
                "Read",
                "name {}".format(read_name))
            r["file"].setValue(file)

            # Set colorspace defined in version data
            colorspace = context["version"]["data"].get("colorspace")
            if colorspace:
                r["colorspace"].setValue(str(colorspace))

            # load nuke presets for Read's colorspace
            read_clrs_presets = presets.get_colorspace_preset().get(
                "nuke", {}).get("read", {})

            # check if any colorspace presets for read is mathing
            preset_clrsp = next((read_clrs_presets[k]
                                 for k in read_clrs_presets
                                 if bool(re.search(k, file))),
                                None)
            if preset_clrsp is not None:
                r["colorspace"].setValue(str(preset_clrsp))

            loader_shift(r, first, relative=True)
            r["origfirst"].setValue(int(first))
            r["first"].setValue(int(first))
            r["origlast"].setValue(int(last))
            r["last"].setValue(int(last))

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

            r["tile_color"].setValue(int("0x4ecd25ff", 16))

            if version_data.get("retime", None):
                speed = version_data.get("speed", 1)
                time_warp_nodes = version_data.get("timewarps", [])
                self.make_retimes(r, speed, time_warp_nodes)

            return containerise(r,
                                name=name,
                                namespace=namespace,
                                context=context,
                                loader=self.__class__.__name__,
                                data=data_imprint)

    def make_retimes(self, node, speed, time_warp_nodes):
        ''' Create all retime and timewarping nodes with coppied animation '''
        if speed != 1:
            rtn = nuke.createNode(
                "Retime",
                "speed {}".format(speed))
            rtn["before"].setValue("continue")
            rtn["after"].setValue("continue")
            rtn["input.first_lock"].setValue(True)
            rtn["input.first"].setValue(
                self.handle_start + self.first_frame
            )

        if time_warp_nodes != []:
            for timewarp in time_warp_nodes:
                twn = nuke.createNode(timewarp["Class"],
                                      "name {}".format(timewarp["name"]))
                if isinstance(timewarp["lookup"], list):
                    # if array for animation
                    twn["lookup"].setAnimated()
                    for i, value in enumerate(timewarp["lookup"]):
                        twn["lookup"].setValueAt(
                            (self.first_frame + i) + value,
                            (self.first_frame + i))
                else:
                    # if static value `int`
                    twn["lookup"].setValue(timewarp["lookup"])

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

        node = nuke.toNode(container['objectName'])

        assert node.Class() == "Read", "Must be Read"

        repr_cont = representation["context"]

        file = api.get_representation_path(representation)

        if not file:
            repr_id = representation["_id"]
            self.log.warning(
                "Representation id `{}` is failing to load".format(repr_id))
            return

        file = file.replace("\\", "/")

        if "#" not in file:
            frame = repr_cont.get("frame")
            padding = len(frame)
            file = file.replace(frame, "#"*padding)

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
            self.log.warning("Missing start frame for updated version"
                             "assuming starts at frame 0 for: "
                             "{} ({})".format(
                                node['name'].value(), representation))
            first = 0

        first -= self.handle_start
        last += self.handle_end

        # Update the loader's path whilst preserving some values
        with preserve_trim(node):
            node["file"].setValue(file)
            self.log.info("__ node['file']: {}".format(node["file"].value()))

        # Set the global in to the start frame of the sequence
        loader_shift(node, first, relative=True)
        node["origfirst"].setValue(int(first))
        node["first"].setValue(int(first))
        node["origlast"].setValue(int(last))
        node["last"].setValue(int(last))

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

        # change color of node
        if version.get("name") not in [max_version]:
            node["tile_color"].setValue(int("0xd84f20ff", 16))
        else:
            node["tile_color"].setValue(int("0x4ecd25ff", 16))

        if version_data.get("retime", None):
            speed = version_data.get("speed", 1)
            time_warp_nodes = version_data.get("timewarps", [])
            self.make_retimes(node, speed, time_warp_nodes)

        # Update the imprinted representation
        update_container(
            node,
            updated_dict
        )
        self.log.info("udated to version: {}".format(version.get("name")))

    def remove(self, container):

        from avalon.nuke import viewer_update_and_undo_stop

        node = nuke.toNode(container['objectName'])
        assert node.Class() == "Read", "Must be Read"

        with viewer_update_and_undo_stop():
            nuke.delete(node)
