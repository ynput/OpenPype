import os
import contextlib

from avalon import api
import avalon.io as io

from avalon.nuke import log
import nuke


@contextlib.contextmanager
def preserve_inputs(node, knobs):
    """Preserve the node's inputs after context"""

    values = {}
    for name in knobs:
        try:
            knob_value = node[name].vaule()
            values[name] = knob_value
        except ValueError:
            log.warning("missing knob {} in node {}"
                        "{}".format(name, node['name'].value()))

    try:
        yield
    finally:
        for name, value in values.items():
            node[name].setValue(value)


@contextlib.contextmanager
def preserve_trim(node):
    """Preserve the relative trim of the Loader tool.

    This tries to preserve the loader's trim (trim in and trim out) after
    the context by reapplying the "amount" it trims on the clip's length at
    start and end.

    """
    # working script frame range
    script_start = nuke.root()["start_frame"].value()

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
            log.info("start frame of reader was set to"
                     "{}".format(script_start))

        if offset_frame:
            node['frame_mode'].setValue("offset")
            node['frame'].setValue(str((script_start + offset_frame)))
            log.info("start frame of reader was set to"
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
    script_start = nuke.root()["start_frame"].value()

    if node['frame_mode'].value() == "start at":
        start_at_frame = node['frame'].value()
    if node['frame_mode'].value() is "offset":
        offset_frame = node['frame'].value()

    if relative:
        shift = frame
    else:
        if start_at_frame:
            shift = frame
        if offset_frame:
            shift = frame + offset_frame

    # Shifting global in will try to automatically compensate for the change
    # in the "ClipTimeStart" and "HoldFirstFrame" inputs, so we preserve those
    # input values to "just shift" the clip
    with preserve_inputs(node, knobs=["file",
                                      "first",
                                      "last",
                                      "originfirst",
                                      "originlast",
                                      "frame_mode",
                                      "frame"]):

        # GlobalIn cannot be set past GlobalOut or vice versa
        # so we must apply them in the order of the shift.
        if start_at_frame:
            node['frame_mode'].setValue("start at")
            node['frame'].setValue(str(script_start + shift))
        if offset_frame:
            node['frame_mode'].setValue("offset")
            node['frame'].setValue(str(shift))

    return int(shift)


class LoadSequence(api.Loader):
    """Load image sequence into Nuke"""

    families = ["write"]
    representations = ["*"]

    label = "Load sequence"
    order = -10
    icon = "code-fork"
    color = "orange"

    def load(self, context, name, namespace, data):

        from avalon.nuke import (
            containerise,
            ls_img_sequence,
            viewer_update_and_undo_stop
        )
        log.info("here i am")
        # Fallback to asset name when namespace is None
        if namespace is None:
            namespace = context['asset']['name']

        # Use the first file for now
        # TODO: fix path fname
        file = ls_img_sequence(os.path.dirname(self.fname), one=True)

        # Create the Loader with the filename path set
        with viewer_update_and_undo_stop():
            # TODO: it might be universal read to img/geo/camera
            r = nuke.createNode(
                "Read",
                "name {}".format(self.name))  # TODO: does self.name exist?
            r["file"].setValue(file['path'])
            if len(file['frames']) is 1:
                first = file['frames'][0][0]
                last = file['frames'][0][1]
                r["originfirst"].setValue(first)
                r["first"].setValue(first)
                r["originlast"].setValue(last)
                r["last"].setValue(last)
            else:
                first = file['frames'][0][0]
                last = file['frames'][:-1][1]
                r["originfirst"].setValue(first)
                r["first"].setValue(first)
                r["originlast"].setValue(last)
                r["last"].setValue(last)
                log.warning("Missing frames in image sequence")

            # Set global in point to start frame (if in version.data)
            start = context["version"]["data"].get("startFrame", None)
            if start is not None:
                loader_shift(r, start, relative=False)

            containerise(r,
                         name=name,
                         namespace=namespace,
                         context=context,
                         loader=self.__class__.__name__)

    def switch(self, container, representation):
        self.update(container, representation)

    def update(self, container, representation):
        """Update the Loader's path

        Fusion automatically tries to reset some variables when changing
        the loader's path to a new file. These automatic changes are to its
        inputs:

        """

        from avalon.nuke import (
            viewer_update_and_undo_stop,
            ls_img_sequence,
            update_container
        )

        node = container["_node"]
        # TODO: prepare also for other readers img/geo/camera
        assert node.Class() == "Reader", "Must be Reader"

        root = api.get_representation_path(representation)
        file = ls_img_sequence(os.path.dirname(root), one=True)

        # Get start frame from version data
        version = io.find_one({"type": "version",
                               "_id": representation["parent"]})
        start = version["data"].get("startFrame")
        if start is None:
            log.warning("Missing start frame for updated version"
                        "assuming starts at frame 0 for: "
                        "{} ({})".format(node['name'].value(), representation))
            start = 0

        with viewer_update_and_undo_stop():

            # Update the loader's path whilst preserving some values
            with preserve_trim(node):
                with preserve_inputs(node,
                                     knobs=["file",
                                            "first",
                                            "last",
                                            "originfirst",
                                            "originlast",
                                            "frame_mode",
                                            "frame"]):
                    node["file"] = file["path"]

            # Set the global in to the start frame of the sequence
            global_in_changed = loader_shift(node, start, relative=False)
            if global_in_changed:
                # Log this change to the user
                log.debug("Changed '{}' global in:"
                          " {:d}".format(node['name'].value(), start))

            # Update the imprinted representation
            update_container(
                node,
                {"representation": str(representation["_id"])}
            )

    def remove(self, container):

        from avalon.nuke import viewer_update_and_undo_stop

        node = container["_node"]
        assert node.Class() == "Reader", "Must be Reader"

        with viewer_update_and_undo_stop():
            nuke.delete(node)
