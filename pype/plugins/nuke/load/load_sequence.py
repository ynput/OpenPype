import os
import re
import nuke

from avalon.vendor import qargparse
from avalon import api, io
from pype.hosts.nuke import presets


class LoadSequence(api.Loader):
    """Load image sequence into Nuke"""

    families = ["render2d", "source", "plate", "render", "prerender", "review"]
    representations = ["exr", "dpx", "jpg", "jpeg", "png"]

    label = "Load Image Sequence"
    order = -20
    icon = "file-video-o"
    color = "white"

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

    # presets
    name_expression = "{class_name}_{ext}"

    @staticmethod
    def fix_hashes_in_path(file, repr_cont):
        if "#" not in file:
            dirname, basename = os.path.split(file)
            frame = repr_cont.get("frame")
            if frame:
                max = len(basename.split(frame)) - 2
                new_basename = ""
                for index, split in enumerate(basename.split(frame)):
                    new_basename += split
                    if max == index:
                        new_basename += "#" * len(frame)
                    if index < max:
                        new_basename += frame
                file = os.path.join(dirname, new_basename).replace("\\", "/")
        return file

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

        repr_cont = context["representation"]["context"]

        file = self.fix_hashes_in_path(file, repr_cont).replace("\\", "/")

        name_data = {
            "asset": repr_cont["asset"],
            "subset": repr_cont["subset"],
            "representation": context["representation"]["name"],
            "ext": repr_cont["representation"],
            "id": context["representation"]["_id"],
            "class_name": self.__class__.__name__
        }

        read_name = self.name_expression.format(**name_data)

        read_node = nuke.createNode(
            "Read",
            "name {}".format(read_name))

        # Create the Loader with the filename path set
        with viewer_update_and_undo_stop():
            read_node["file"].setValue(file)

            # Set colorspace defined in version data
            colorspace = context["version"]["data"].get("colorspace")
            if colorspace:
                read_node["colorspace"].setValue(str(colorspace))

            # load nuke presets for Read's colorspace
            read_clrs_presets = presets.get_colorspace_preset().get(
                "nuke", {}).get("read", {})

            # check if any colorspace presets for read is mathing
            preset_clrsp = next((read_clrs_presets[k]
                                 for k in read_clrs_presets
                                 if bool(re.search(k, file))),
                                None)
            if preset_clrsp is not None:
                read_node["colorspace"].setValue(str(preset_clrsp))

            loader_shift(read_node, start_at_workfile)
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
                self.make_retimes(read_node, speed, time_warp_nodes)

            return containerise(read_node,
                                name=name,
                                namespace=namespace,
                                context=context,
                                loader=self.__class__.__name__,
                                data=data_imprint)

    def update(self, container, representation):
        """ Update the Loader's path

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

        file = api.get_representation_path(representation)

        if not file:
            repr_id = representation["_id"]
            self.log.warning(
                "Representation id `{}` is failing to load".format(repr_id))
            return

        file = self.fix_hashes_in_path(file, repr_cont).replace("\\", "/")

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
        self.log.info(
            "__ read_node['file']: {}".format(read_node["file"].value()))

        # Set the global in to the start frame of the sequence

        loader_shift(
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
            self.make_retimes(read_node, speed, time_warp_nodes)

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

    def switch(self, container, representation):
        self.update(container, representation)

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


def loader_shift(read_node, workfile_start=False):
    """ Set start frame of read node to a workfile start

    Args:
        read_node (nuke.Node): The nuke's read node
        workfile_start (bool): set workfile start frame if true

    """
    # working script frame range
    script_start = nuke.root()["first_frame"].value()

    if workfile_start:
        read_node['frame_mode'].setValue("start at")
        read_node['frame'].setValue(str(script_start))
