import os
import contextlib

import maya.cmds as cmds

import pyblish_maya
import colorbleed.api

import cb.utils.maya.context as context


def _set_cache_file_path(node, path):
    """Forces a cacheFile.cachePath attribute to be set to path.

    When the given path does not exist Maya will raise an error
    when using `maya.cmds.setAttr` to set the "cachePath" attribute.

    Arguments:
        node (str): Name of cacheFile node.
        path (str): Path value to set.

    """

    path = str(path)

    # Temporary unique attribute name
    attr = "__tmp_path"
    while cmds.attributeQuery(attr, node=node, exists=True):
        attr += "_"

    # Create the temporary attribute, set its value and connect
    # it to the `.cachePath` attribute to force the value to be
    # set and applied without errors.
    cmds.addAttr(node, longName=attr, dataType="string")
    plug = "{0}.{1}".format(node, attr)
    try:
        cmds.setAttr(plug, path, type="string")
        cmds.connectAttr(plug,
                         "{0}.cachePath".format(node),
                         force=True)
    finally:
        # Ensure the temporary attribute is deleted
        cmds.deleteAttr(plug)


@contextlib.contextmanager
def cache_file_paths(mapping):
    """Set the cacheFile paths during context.

    This is a workaround context manager that allows
    to set the .cachePath attribute to a folder that
    doesn't actually exist since using regular
    `maya.cmds.setAttr` results in an error.

    Arguments:
        mapping (dict): node -> path mapping

    """

    # Store the original values
    original = dict()
    for node in mapping:
        original[node] = cmds.getAttr("{}.cachePath".format(node))

    try:
        for node, path in mapping.items():
            _set_cache_file_path(node, path)
        yield
    finally:
        for node, path in original.items():
            _set_cache_file_path(node, path)


def is_cache_resource(resource):
    """Return whether resource is a cacheFile resource"""
    start_tags = ["maya", "node", "cacheFile"]
    required = set(start_tags)
    tags = resource.get("tags", [])
    return required.issubset(tags)


class ExtractInstancerMayaAscii(colorbleed.api.Extractor):
    """Extract as Maya Ascii"""

    label = "Instancer (Maya Ascii)"
    hosts = ["maya"]
    families = ["colorbleed.instancer"]

    # TODO: Find other solution than expanding vars to fix lack of support
    # TODO: of cacheFile

    def process(self, instance):

        export = instance.data("exactExportMembers")

        # Set up cacheFile path remapping.
        resources = instance.data.get("resources", [])
        attr_remap, cache_remap = self.process_resources(resources)

        # Define extract output file path
        dir_path = self.staging_dir(instance)
        filename = "{0}.ma".format(instance.name)
        path = os.path.join(dir_path, filename)

        # Perform extraction
        self.log.info("Performing extraction..")
        with pyblish_maya.maintained_selection():
            with cache_file_paths(cache_remap):
                with context.attribute_values(attr_remap):
                    cmds.select(export, noExpand=True)
                    cmds.file(path,
                              force=True,
                              typ="mayaAscii",
                              exportSelected=True,
                              preserveReferences=False,
                              constructionHistory=False,
                              channels=True,  # allow animation
                              constraints=False,
                              shader=False,
                              expressions=False)

        self.log.info("Extracted instance '{0}' to: {1}".format(
            instance.name, path))

    def process_resources(self, resources):

        attr_remap = dict()
        cache_remap = dict()
        for resource in resources:
            if not is_cache_resource(resource):
                continue

            node = resource['node']
            destination = resource['destination']

            folder = os.path.dirname(destination)
            fname = os.path.basename(destination)
            if fname.endswith(".xml"):
                fname = fname[:-4]

            # Ensure the folder path ends with a slash
            if not folder.endswith("\\") and not folder.endswith("/"):
                folder += "/"

            # Set path and name
            attr_remap["{0}.cacheName".format(node)] = os.path.expandvars(
                fname)
            cache_remap[node] = os.path.expandvars(folder)

            self.log.info("Mapping {0} to {1}".format(node, destination))

        return attr_remap, cache_remap
