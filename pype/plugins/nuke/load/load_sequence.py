import nuke
import os
import contextlib

from avalon import api
import avalon.io as io

from pype.api import Logger
log = Logger.getLogger(__name__, "nuke")


class LoadSequence(api.Loader):
    """Load image sequence into Nuke"""

    families = ["write"]
    representations = ["*"]

    label = "Load sequence"
    order = -10
    icon = "code-fork"
    color = "orange"

    def load(self, context, name, namespace, data):

        log.info("context: {}\n".format(context["representation"]))
        log.info("name: {}\n".format(name))
        log.info("namespace: {}\n".format(namespace))
        log.info("data: {}\n".format(data))
        return
    #     # Fallback to asset name when namespace is None
    #     if namespace is None:
    #         namespace = context['asset']['name']
    #
    #     # Use the first file for now
    #     # TODO: fix path fname
    #     file = ls_img_sequence(os.path.dirname(self.fname), one=True)
    #
    #     # Create the Loader with the filename path set
    #     with viewer_update_and_undo_stop():
    #         # TODO: it might be universal read to img/geo/camera
    #         r = nuke.createNode(
    #             "Read",
    #             "name {}".format(self.name))  # TODO: does self.name exist?
    #         r["file"].setValue(file['path'])
    #         if len(file['frames']) is 1:
    #             first = file['frames'][0][0]
    #             last = file['frames'][0][1]
    #             r["originfirst"].setValue(first)
    #             r["first"].setValue(first)
    #             r["originlast"].setValue(last)
    #             r["last"].setValue(last)
    #         else:
    #             first = file['frames'][0][0]
    #             last = file['frames'][:-1][1]
    #             r["originfirst"].setValue(first)
    #             r["first"].setValue(first)
    #             r["originlast"].setValue(last)
    #             r["last"].setValue(last)
    #             log.warning("Missing frames in image sequence")
    #
    #         # Set global in point to start frame (if in version.data)
    #         start = context["version"]["data"].get("startFrame", None)
    #         if start is not None:
    #             loader_shift(r, start, relative=False)
    #
    #         containerise(r,
    #                      name=name,
    #                      namespace=namespace,
    #                      context=context,
    #                      loader=self.__class__.__name__)
    #
    # def switch(self, container, representation):
    #     self.update(container, representation)
    #
    # def update(self, container, representation):
    #     """Update the Loader's path
    #
    #     Fusion automatically tries to reset some variables when changing
    #     the loader's path to a new file. These automatic changes are to its
    #     inputs:
    #
    #     """
    #
    #     from avalon.nuke import (
    #         viewer_update_and_undo_stop,
    #         ls_img_sequence,
    #         update_container
    #     )
    #     log.info("this i can see")
    #     node = container["_tool"]
    #     # TODO: prepare also for other readers img/geo/camera
    #     assert node.Class() == "Reader", "Must be Reader"
    #
    #     root = api.get_representation_path(representation)
    #     file = ls_img_sequence(os.path.dirname(root), one=True)
    #
    #     # Get start frame from version data
    #     version = io.find_one({"type": "version",
    #                            "_id": representation["parent"]})
    #     start = version["data"].get("startFrame")
    #     if start is None:
    #         log.warning("Missing start frame for updated version"
    #                     "assuming starts at frame 0 for: "
    #                     "{} ({})".format(node['name'].value(), representation))
    #         start = 0
    #
    #     with viewer_update_and_undo_stop():
    #
    #         # Update the loader's path whilst preserving some values
    #         with preserve_trim(node):
    #             with preserve_inputs(node,
    #                                  knobs=["file",
    #                                         "first",
    #                                         "last",
    #                                         "originfirst",
    #                                         "originlast",
    #                                         "frame_mode",
    #                                         "frame"]):
    #                 node["file"] = file["path"]
    #
    #         # Set the global in to the start frame of the sequence
    #         global_in_changed = loader_shift(node, start, relative=False)
    #         if global_in_changed:
    #             # Log this change to the user
    #             log.debug("Changed '{}' global in:"
    #                       " {:d}".format(node['name'].value(), start))
    #
    #         # Update the imprinted representation
    #         update_container(
    #             node,
    #             {"representation": str(representation["_id"])}
    #         )
    #
    # def remove(self, container):
    #
    #     from avalon.nuke import viewer_update_and_undo_stop
    #
    #     node = container["_tool"]
    #     assert node.Class() == "Reader", "Must be Reader"
    #
    #     with viewer_update_and_undo_stop():
    #         nuke.delete(node)
