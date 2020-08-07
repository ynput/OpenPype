import re
import nuke
import contextlib

from avalon import api, io
from pype.hosts.nuke import presets
from pype.api import config


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


def add_review_presets_config():
    returning = {
        "families": list(),
        "representations": list()
    }
    review_presets = config.get_presets()["plugins"]["global"]["publish"].get(
        "ExtractReview", {})

    outputs = review_presets.get("outputs", {})
    #
    for output, properities in outputs.items():
        returning["representations"].append(output)
        returning["families"] += properities.get("families", [])

    return returning


class LoadMov(api.Loader):
    """Load mov file into Nuke"""
    presets = add_review_presets_config()
    families = [
        "source",
        "plate",
        "render",
        "prerender",
        "review"] + presets["families"]

    representations = [
        "mov",
        "preview",
        "review",
        "mp4"] + presets["representations"]

    label = "Load mov"
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

        orig_first = version_data.get("frameStart")
        orig_last = version_data.get("frameEnd")
        diff = orig_first - 1

        first = orig_first - diff
        last = orig_last - diff

        handle_start = version_data.get("handleStart", 0)
        handle_end = version_data.get("handleEnd", 0)

        colorspace = version_data.get("colorspace")
        repr_cont = context["representation"]["context"]

        self.log.debug(
            "Representation id `{}` ".format(repr_id))

        context["representation"]["_id"]
        # create handles offset (only to last, because of mov)
        last += handle_start + handle_end
        # offset should be with handles so it match orig frame range
        offset_frame = orig_first - handle_start

        # Fallback to asset name when namespace is None
        if namespace is None:
            namespace = context['asset']['name']

        file = self.fname

        if not file:
            self.log.warning(
                "Representation id `{}` is failing to load".format(repr_id))
            return

        file = file.replace("\\", "/")

        read_name = "Read_{0}_{1}_{2}".format(
            repr_cont["asset"],
            repr_cont["subset"],
            repr_cont["representation"])

        # Create the Loader with the filename path set
        with viewer_update_and_undo_stop():
            read_node = nuke.createNode(
                "Read",
                "name {}".format(read_name)
            )
            read_node["file"].setValue(file)

            loader_shift(read_node, first, relative=True)
            read_node["origfirst"].setValue(first)
            read_node["first"].setValue(first)
            read_node["origlast"].setValue(last)
            read_node["last"].setValue(last)
            read_node["frame_mode"].setValue("start at")
            read_node["frame"].setValue(str(offset_frame))

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

        node = nuke.toNode(container['objectName'])

        assert node.Class() == "Read", "Must be Read"

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
        handles = version_data.get("handles", 0)
        handle_start = version_data.get("handleStart", 0)
        handle_end = version_data.get("handleEnd", 0)
        colorspace = version_data.get("colorspace")

        if first is None:
            self.log.warning("Missing start frame for updated version"
                             "assuming starts at frame 0 for: "
                             "{} ({})".format(
                                node['name'].value(), representation))
            first = 0

        # fix handle start and end if none are available
        if not handle_start and not handle_end:
            handle_start = handles
            handle_end = handles

        # create handles offset (only to last, because of mov)
        last += handle_start + handle_end
        # offset should be with handles so it match orig frame range
        offset_frame = orig_first - handle_start

        # Update the loader's path whilst preserving some values
        with preserve_trim(node):
            node["file"].setValue(file)
            self.log.info("__ node['file']: {}".format(node["file"].value()))

        # Set the global in to the start frame of the sequence
        loader_shift(node, first, relative=True)
        node["origfirst"].setValue(first)
        node["first"].setValue(first)
        node["origlast"].setValue(last)
        node["last"].setValue(last)
        node["frame_mode"].setValue("start at")
        node["frame"].setValue(str(offset_frame))

        if colorspace:
            node["colorspace"].setValue(str(colorspace))

        # load nuke presets for Read's colorspace
        read_clrs_presets = presets.get_colorspace_preset().get(
            "nuke", {}).get("read", {})

        # check if any colorspace presets for read is mathing
        preset_clrsp = next((read_clrs_presets[k]
                             for k in read_clrs_presets
                             if bool(re.search(k, file))),
                            None)
        if preset_clrsp is not None:
            node["colorspace"].setValue(str(preset_clrsp))

        updated_dict = {}
        updated_dict.update({
            "representation": str(representation["_id"]),
            "frameStart": str(first),
            "frameEnd": str(last),
            "version": str(version.get("name")),
            "colorspace": version_data.get("colorspace"),
            "source": version_data.get("source"),
            "handleStart": str(handle_start),
            "handleEnd": str(handle_end),
            "fps": str(version_data.get("fps")),
            "author": version_data.get("author"),
            "outputDir": version_data.get("outputDir")
        })

        # change color of node
        if version.get("name") not in [max_version]:
            node["tile_color"].setValue(int("0xd84f20ff", 16))
        else:
            node["tile_color"].setValue(int("0x4ecd25ff", 16))

        # Update the imprinted representation
        update_container(
            node, updated_dict
        )
        self.log.info("udated to version: {}".format(version.get("name")))

    def remove(self, container):

        from avalon.nuke import viewer_update_and_undo_stop

        node = nuke.toNode(container['objectName'])
        assert node.Class() == "Read", "Must be Read"

        with viewer_update_and_undo_stop():
            nuke.delete(node)
