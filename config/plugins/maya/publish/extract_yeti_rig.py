import os
import json
import contextlib

from maya import cmds

import avalon.maya.lib as lib
import config.api
import config.maya.lib as maya


@contextlib.contextmanager
def disconnected_attributes(settings, members):

    members = cmds.ls(members, long=True)
    original_connections = []
    try:
        for input in settings["inputs"]:

            # Get source shapes
            source_nodes = lib.lsattr("cbId", input["sourceID"])
            sources = [i for i in source_nodes if
                       not cmds.referenceQuery(i, isNodeReferenced=True)
                       and i in members]
            try:
                source = sources[0]
            except IndexError:
                print("source_id:", input["sourceID"])
                continue

            # Get destination shapes (the shapes used as hook up)
            destination_nodes = lib.lsattr("cbId", input["destinationID"])
            destinations = [i for i in destination_nodes if i not in members
                            and i not in sources]
            destination = destinations[0]

            # Break connection
            connections = input["connections"]
            src_attribute = "%s.%s" % (source, connections[0])
            dst_attribute = "%s.%s" % (destination, connections[1])

            # store connection pair
            if not cmds.isConnected(src_attribute, dst_attribute):
                continue

            cmds.disconnectAttr(src_attribute, dst_attribute)
            original_connections.append([src_attribute, dst_attribute])
        yield
    finally:
        # restore connections
        for connection in original_connections:
            try:
                cmds.connectAttr(connection[0], connection[1])
            except Exception as e:
                print(e)
                continue


class ExtractYetiRig(config.api.Extractor):
    """Produce an alembic of just point positions and normals.

    Positions and normals are preserved, but nothing more,
    for plain and predictable point caches.

    """

    label = "Extract Yeti Rig"
    hosts = ["maya"]
    families = ["studio.yetiRig"]

    def process(self, instance):

        yeti_nodes = cmds.ls(instance, type="pgYetiMaya")
        if not yeti_nodes:
            raise RuntimeError("No pgYetiMaya nodes found in the instance")

        # Define extract output file path
        dirname = self.staging_dir(instance)
        settings_path = os.path.join(dirname, "yeti.rigsettings")

        # Yeti related staging dirs
        maya_path = os.path.join(dirname, "yeti_rig.ma")

        self.log.info("Writing metadata file")

        image_search_path = ""
        settings = instance.data.get("rigsettings", None)
        if settings is not None:

            # Create assumed destination folder for imageSearchPath
            assumed_temp_data = instance.data["assumedTemplateData"]
            template = instance.data["template"]
            template_formatted = template.format(**assumed_temp_data)

            destination_folder = os.path.dirname(template_formatted)
            image_search_path = os.path.join(destination_folder, "resources")
            image_search_path = os.path.normpath(image_search_path)

            settings["imageSearchPath"] = image_search_path
            with open(settings_path, "w") as fp:
                json.dump(settings, fp, ensure_ascii=False)

        attr_value = {"%s.imageSearchPath" % n: str(image_search_path) for
                      n in yeti_nodes}

        # Get input_SET members
        input_set = [i for i in instance if i == "input_SET"]
        # Get all items
        set_members = cmds.sets(input_set[0], query=True)
        members = cmds.listRelatives(set_members, ad=True, fullPath=True) or []
        members += cmds.ls(set_members, long=True)

        nodes = instance.data["setMembers"]
        with disconnected_attributes(settings, members):
            with maya.attribute_values(attr_value):
                cmds.select(nodes, noExpand=True)
                cmds.file(maya_path,
                          force=True,
                          exportSelected=True,
                          typ="mayaAscii",
                          preserveReferences=False,
                          constructionHistory=True,
                          shader=False)

        # Ensure files can be stored
        if "files" not in instance.data:
            instance.data["files"] = list()

        instance.data["files"].extend(["yeti_rig.ma", "yeti.rigsettings"])

        self.log.info("Extracted {} to {}".format(instance, dirname))

        cmds.select(clear=True)
