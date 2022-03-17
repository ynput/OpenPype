import os
import contextlib

from avalon import io

from openpype.pipeline import (
    load,
    get_representation_path,
)
from openpype.hosts.fusion.api import (
    imprint_container,
    get_current_comp,
    comp_lock_and_undo_chunk
)

comp = get_current_comp()


@contextlib.contextmanager
def preserve_inputs(tool, inputs):
    """Preserve the tool's inputs after context"""

    comp = tool.Comp()

    values = {}
    for name in inputs:
        tool_input = getattr(tool, name)
        value = tool_input[comp.TIME_UNDEFINED]
        values[name] = value

    try:
        yield
    finally:
        for name, value in values.items():
            tool_input = getattr(tool, name)
            tool_input[comp.TIME_UNDEFINED] = value


@contextlib.contextmanager
def preserve_trim(loader, log=None):
    """Preserve the relative trim of the Loader tool.

    This tries to preserve the loader's trim (trim in and trim out) after
    the context by reapplying the "amount" it trims on the clip's length at
    start and end.

    """

    # Get original trim as amount of "trimming" from length
    time = loader.Comp().TIME_UNDEFINED
    length = loader.GetAttrs()["TOOLIT_Clip_Length"][1] - 1
    trim_from_start = loader["ClipTimeStart"][time]
    trim_from_end = length - loader["ClipTimeEnd"][time]

    try:
        yield
    finally:

        length = loader.GetAttrs()["TOOLIT_Clip_Length"][1] - 1
        if trim_from_start > length:
            trim_from_start = length
            if log:
                log.warning("Reducing trim in to %d "
                            "(because of less frames)" % trim_from_start)

        remainder = length - trim_from_start
        if trim_from_end > remainder:
            trim_from_end = remainder
            if log:
                log.warning("Reducing trim in to %d "
                            "(because of less frames)" % trim_from_end)

        loader["ClipTimeStart"][time] = trim_from_start
        loader["ClipTimeEnd"][time] = length - trim_from_end


def loader_shift(loader, frame, relative=True):
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
    comp = loader.Comp()
    time = comp.TIME_UNDEFINED

    old_in = loader["GlobalIn"][time]
    old_out = loader["GlobalOut"][time]

    if relative:
        shift = frame
    else:
        shift = frame - old_in

    # Shifting global in will try to automatically compensate for the change
    # in the "ClipTimeStart" and "HoldFirstFrame" inputs, so we preserve those
    # input values to "just shift" the clip
    with preserve_inputs(loader, inputs=["ClipTimeStart",
                                         "ClipTimeEnd",
                                         "HoldFirstFrame",
                                         "HoldLastFrame"]):

        # GlobalIn cannot be set past GlobalOut or vice versa
        # so we must apply them in the order of the shift.
        if shift > 0:
            loader["GlobalOut"][time] = old_out + shift
            loader["GlobalIn"][time] = old_in + shift
        else:
            loader["GlobalIn"][time] = old_in + shift
            loader["GlobalOut"][time] = old_out + shift

    return int(shift)


class FusionLoadSequence(load.LoaderPlugin):
    """Load image sequence into Fusion"""

    families = ["imagesequence", "review", "render"]
    representations = ["*"]

    label = "Load sequence"
    order = -10
    icon = "code-fork"
    color = "orange"

    def load(self, context, name, namespace, data):
        # Fallback to asset name when namespace is None
        if namespace is None:
            namespace = context['asset']['name']

        # Use the first file for now
        path = self._get_first_image(os.path.dirname(self.fname))

        # Create the Loader with the filename path set
        comp = get_current_comp()
        with comp_lock_and_undo_chunk(comp, "Create Loader"):

            args = (-32768, -32768)
            tool = comp.AddTool("Loader", *args)
            tool["Clip"] = path

            # Set global in point to start frame (if in version.data)
            start = context["version"]["data"].get("frameStart", None)
            if start is not None:
                loader_shift(tool, start, relative=False)

            imprint_container(tool,
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
            - ClipTimeStart: Fusion reset to 0 if duration changes
              - We keep the trim in as close as possible to the previous value.
                When there are less frames then the amount of trim we reduce
                it accordingly.

            - ClipTimeEnd: Fusion reset to 0 if duration changes
              - We keep the trim out as close as possible to the previous value
                within new amount of frames after trim in (ClipTimeStart) has
                been set.

            - GlobalIn: Fusion reset to comp's global in if duration changes
              - We change it to the "frameStart"

            - GlobalEnd: Fusion resets to globalIn + length if duration changes
              - We do the same like Fusion - allow fusion to take control.

            - HoldFirstFrame: Fusion resets this to 0
              - We preserve the value.

            - HoldLastFrame: Fusion resets this to 0
              - We preserve the value.

            - Reverse: Fusion resets to disabled if "Loop" is not enabled.
              - We preserve the value.

            - Depth: Fusion resets to "Format"
              - We preserve the value.

            - KeyCode: Fusion resets to ""
              - We preserve the value.

            - TimeCodeOffset: Fusion resets to 0
              - We preserve the value.

        """

        tool = container["_tool"]
        assert tool.ID == "Loader", "Must be Loader"
        comp = tool.Comp()

        root = os.path.dirname(get_representation_path(representation))
        path = self._get_first_image(root)

        # Get start frame from version data
        version = io.find_one({"type": "version",
                               "_id": representation["parent"]})
        start = version["data"].get("frameStart")
        if start is None:
            self.log.warning("Missing start frame for updated version"
                             "assuming starts at frame 0 for: "
                             "{} ({})".format(tool.Name, representation))
            start = 0

        with comp_lock_and_undo_chunk(comp, "Update Loader"):

            # Update the loader's path whilst preserving some values
            with preserve_trim(tool, log=self.log):
                with preserve_inputs(tool,
                                     inputs=("HoldFirstFrame",
                                             "HoldLastFrame",
                                             "Reverse",
                                             "Depth",
                                             "KeyCode",
                                             "TimeCodeOffset")):
                    tool["Clip"] = path

            # Set the global in to the start frame of the sequence
            global_in_changed = loader_shift(tool, start, relative=False)
            if global_in_changed:
                # Log this change to the user
                self.log.debug("Changed '%s' global in: %d" % (tool.Name,
                                                               start))

            # Update the imprinted representation
            tool.SetData("avalon.representation", str(representation["_id"]))

    def remove(self, container):
        tool = container["_tool"]
        assert tool.ID == "Loader", "Must be Loader"
        comp = tool.Comp()

        with comp_lock_and_undo_chunk(comp, "Remove Loader"):
            tool.Delete()

    def _get_first_image(self, root):
        """Get first file in representation root"""
        files = sorted(os.listdir(root))
        return os.path.join(root, files[0])
