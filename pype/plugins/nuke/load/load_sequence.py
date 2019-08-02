import os
import contextlib

from avalon import api
import avalon.io as io


import nuke

from pype.api import Logger
log = Logger().get_logger(__name__, "nuke")


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
    if node['frame_mode'].value() is "offset":
        offset_frame = node['frame'].value()

    try:
        yield
    finally:
        if start_at_frame:
            node['frame_mode'].setValue("start at")
            node['frame'].setValue(str(script_start))
            log.info("start frame of Read was set to"
                     "{}".format(script_start))

        if offset_frame:
            node['frame_mode'].setValue("offset")
            node['frame'].setValue(str((script_start + offset_frame)))
            log.info("start frame of Read was set to"
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

    families = ["write", "source", "plate", "render"]
    representations = ["exr", "dpx"]

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
        log.info("version_data: {}\n".format(version_data))
        first = version_data.get("startFrame", None)
        last = version_data.get("endFrame", None)
        handles = version_data.get("handles", 0)
        handle_start = version_data.get("handleStart", 0)
        handle_end = version_data.get("handleEnd", 0)

        # fix handle start and end if none are available
        if not handle_start and not handle_end:
            handle_start = handles
            handle_end = handles

        # # create handles offset
        # first -= handle_start
        # last += handle_end

        # Fallback to asset name when namespace is None
        if namespace is None:
            namespace = context['asset']['name']

        file = self.fname.replace("\\", "/")
        log.info("file: {}\n".format(self.fname))

        read_name = "Read_" + context["representation"]["context"]["subset"]

        # Create the Loader with the filename path set
        with viewer_update_and_undo_stop():
            # TODO: it might be universal read to img/geo/camera
            r = nuke.createNode(
                "Read",
                "name {}".format(read_name))
            r["file"].setValue(file)

            # Set colorspace defined in version data
            colorspace = context["version"]["data"].get("colorspace", None)
            if colorspace is not None:
                r["colorspace"].setValue(str(colorspace))

            loader_shift(r, first, relative=True)
            r["origfirst"].setValue(int(first))
            r["first"].setValue(int(first))
            r["origlast"].setValue(int(last))
            r["last"].setValue(int(last))

            # add additional metadata from the version to imprint to Avalon knob
            add_keys = ["startFrame", "endFrame", "handles",
                        "source", "colorspace", "author", "fps", "version",
                        "handleStart", "handleEnd"]

            data_imprint = {}
            for k in add_keys:
                if k is 'version':
                    data_imprint.update({k: context["version"]['name']})
                else:
                    data_imprint.update({k: context["version"]['data'].get(k, str(None))})

            data_imprint.update({"objectName": read_name})

            r["tile_color"].setValue(int("0x4ecd25ff", 16))

            return containerise(r,
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
            ls_img_sequence,
            update_container
        )

        node = nuke.toNode(container['objectName'])
        # TODO: prepare also for other Read img/geo/camera
        assert node.Class() == "Read", "Must be Read"

        path = api.get_representation_path(representation)
        file = ls_img_sequence(path)

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

        first = version_data.get("startFrame", None)
        last = version_data.get("endFrame", None)
        handles = version_data.get("handles", 0)
        handle_start = version_data.get("handleStart", 0)
        handle_end = version_data.get("handleEnd", 0)

        if first is None:
            log.warning("Missing start frame for updated version"
                        "assuming starts at frame 0 for: "
                        "{} ({})".format(node['name'].value(), representation))
            first = 0

        # fix handle start and end if none are available
        if not handle_start and not handle_end:
            handle_start = handles
            handle_end = handles

        # create handles offset
        first -= handle_start
        last += handle_end

        # Update the loader's path whilst preserving some values
        with preserve_trim(node):
            node["file"].setValue(file["path"])
            log.info("__ node['file']: {}".format(node["file"].value()))

        # Set the global in to the start frame of the sequence
        loader_shift(node, first, relative=True)
        node["origfirst"].setValue(first)
        node["first"].setValue(first)
        node["origlast"].setValue(last)
        node["last"].setValue(last)

        updated_dict = {}
        updated_dict.update({
            "representation": str(representation["_id"]),
            "startFrame": version_data.get("startFrame"),
            "endFrame": version_data.get("endFrame"),
            "version": version.get("name"),
            "colorspace": version_data.get("colorspace"),
            "source": version_data.get("source"),
            "handles": version_data.get("handles"),
            "handleStart": version_data.get("handleStart"),
            "handleEnd": version_data.get("handleEnd"),
            "fps": version_data.get("fps"),
            "author": version_data.get("author"),
            "outputDir": version_data.get("outputDir"),
        })

        # change color of node
        if version.get("name") not in [max_version]:
            node["tile_color"].setValue(int("0xd84f20ff", 16))
        else:
            node["tile_color"].setValue(int("0x4ecd25ff", 16))

        # Update the imprinted representation
        update_container(
            node,
            updated_dict
        )
        log.info("udated to version: {}".format(version.get("name")))

    def remove(self, container):

        from avalon.nuke import viewer_update_and_undo_stop

        node = nuke.toNode(container['objectName'])
        assert node.Class() == "Read", "Must be Read"

        with viewer_update_and_undo_stop():
            nuke.delete(node)
