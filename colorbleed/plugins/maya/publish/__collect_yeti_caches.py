import os
import re
import pyseq
import glob

import pyblish.api

from maya import cmds


class SeletYetiCachesAction(pyblish.api.Action):
    """Select the nodes related to the collected file textures"""

    label = "Select yeti nodes"
    on = "succeeded"  # This action is only available on a failed plug-in
    icon = "search"  # Icon from Awesome Icon

    def process(self, context, plugin):

        self.log.info("Finding textures..")

        # Get the errored instances
        instances = []
        for result in context.data["results"]:
            instance = result["instance"]
            if instance is None:
                continue

            instances.append(instance)

        # Apply pyblish.logic to get the instances for the plug-in
        instances = pyblish.api.instances_by_plugin(instances, plugin)

        # Get the texture nodes from the instances
        nodes = []
        for instance in instances:
            texture_nodes = instance.data['yetiCaches'].keys()
            nodes.extend(texture_nodes)

        # Ensure unique
        nodes = list(set(nodes))

        if nodes:
            self.log.info("Selecting nodes: %s" % ", ".join(nodes))
            cmds.select(nodes, r=True, noExpand=True)
        else:
            self.log.info("No nodes found.")
            cmds.select(deselect=True)


def get_sequence(filename, pattern="%04d"):
    """Get pyseq sequence from filename

    Supports negative frame ranges like (-001, 0000, 0001 and -0001, 0000, 0001).

    Arguments:
        filename (str): The full path to filename containing the given pattern.
        pattern (str): The pattern to swap with the variable frame number.

    Returns:
        pyseq.Sequence: file sequence.

    """

    glob_pattern = filename.replace(pattern, "*")

    escaped = re.escape(filename)
    re_pattern = escaped.replace(pattern, "-?[0-9]+")

    files = glob.glob(glob_pattern)
    files = [str(f) for f in files if re.match(re_pattern, f)]

    return pyseq.get_sequences(files)


class CollectYetiCaches(pyblish.api.InstancePlugin):
    """Collect used yeti caches.

    Collects the file sequences from pgYetiMaya.cacheFileName

    """

    order = pyblish.api.CollectorOrder + 0.495
    label = 'Yeti Caches'
    families = ["colorbleed.groom"]
    actions = [SeletYetiCachesAction]

    TYPES = {"pgYetiMaya": "cacheFileName"}

    def process(self, instance):

        # Get textures from sets
        members = instance.data("setMembers")
        members = cmds.ls(members, dag=True, shapes=True, type="pgYetiMaya",
                          noIntermediate=True, long=True)
        if not members:
            raise RuntimeError("Instance appears to be empty (no members)")

        # Collect only those cache frames that are required
        # If handles are required it is assumed to already be included
        # in the start frame and end frames.
        # (e.g. using frame handle collector)
        start_frame = instance.data("startFrame")
        end_frame = instance.data("endFrame")
        required = set(range(int(start_frame), int(end_frame) + 1))

        history = cmds.listHistory(members) or []

        resources = instance.data.get("resources", [])
        yeti_caches = dict()

        for node_type, attr in self.TYPES.iteritems():
            for node in cmds.ls(history, type=node_type, long=True):

                attribute = "{0}.{1}".format(node, attr)

                # Source
                source = cmds.getAttr(attribute)
                if not source:
                    self.log.error("Node does not have a file set: "
                                   "{0}".format(node))

                # Collect the source as expanded path because that's also
                # how the attribute must be 'set' for yeti nodes.
                source = os.path.realpath(cmds.workspace(expandName=source))

                # Collect the frames we need from the sequence
                sequences = get_sequence(source)
                files = list()
                for sequence in sequences:
                    for index, frame in enumerate(sequence.frames()):
                        if frame not in required:
                            continue

                        item = sequence[index]
                        files.append(item.path)

                # Define the resource
                resource = {"tags": ["maya", "yeti", "attribute"],
                            "node": node,
                            "attribute": attribute,
                            "source": source,        # required for resources
                            "files": files,          # required for resources
                            "subfolder": "caches"    # optional for resources
                            }

                resources.append(resource)

                # For validations
                yeti_caches[node] = {"attribute": attribute,
                                     "source": source,
                                     "sequences": sequences}

        # Store data on instance
        instance.data['yetiCaches'] = yeti_caches
        instance.data['resources'] = resources
