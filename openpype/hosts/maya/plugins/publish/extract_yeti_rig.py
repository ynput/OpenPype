# -*- coding: utf-8 -*-
"""Extract Yeti rig."""

import os
import json
import contextlib

from maya import cmds

import openpype.api
from openpype.hosts.maya.api import lib


@contextlib.contextmanager
def disconnect_plugs(settings, members):
    """Disconnect and store attribute connections."""
    members = cmds.ls(members, long=True)
    original_connections = []
    try:
        for input in settings["inputs"]:

            # Get source shapes
            source_nodes = lib.lsattr("cbId", input["sourceID"])
            if not source_nodes:
                continue

            source = next(s for s in source_nodes if s not in members)

            # Get destination shapes (the shapes used as hook up)
            destination_nodes = lib.lsattr("cbId", input["destinationID"])
            destination = next(i for i in destination_nodes if i in members)

            # Create full connection
            connections = input["connections"]
            src_attribute = "%s.%s" % (source, connections[0])
            dst_attribute = "%s.%s" % (destination, connections[1])

            # Check if there is an actual connection
            if not cmds.isConnected(src_attribute, dst_attribute):
                print("No connection between %s and %s" % (
                    src_attribute, dst_attribute))
                continue

            # Break and store connection
            cmds.disconnectAttr(src_attribute, dst_attribute)
            original_connections.append([src_attribute, dst_attribute])
        yield
    finally:
        # Restore previous connections
        for connection in original_connections:
            try:
                cmds.connectAttr(connection[0], connection[1])
            except Exception as e:
                print(e)
                continue


@contextlib.contextmanager
def yetigraph_attribute_values(assumed_destination, resources):
    """Get values from Yeti attributes in graph."""
    try:
        for resource in resources:
            if "graphnode" not in resource:
                continue

            fname = os.path.basename(resource["source"])
            new_fpath = os.path.join(assumed_destination, fname)
            new_fpath = new_fpath.replace("\\", "/")

            try:
                cmds.pgYetiGraph(resource["node"],
                                 node=resource["graphnode"],
                                 param=resource["param"],
                                 setParamValueString=new_fpath)
            except Exception as exc:
                print(">>> Exception:", exc)
        yield

    finally:
        for resource in resources:
            if "graphnode" not in resources:
                continue

            try:
                cmds.pgYetiGraph(resource["node"],
                                 node=resource["graphnode"],
                                 param=resource["param"],
                                 setParamValue=resource["source"])
            except RuntimeError:
                pass


class ExtractYetiRig(openpype.api.Extractor):
    """Extract the Yeti rig to a Maya Scene and write the Yeti rig data."""

    label = "Extract Yeti Rig"
    hosts = ["maya"]
    families = ["yetiRig"]
    scene_type = "ma"

    def process(self, instance):
        """Plugin entry point."""
        ext_mapping = (
            instance.context.data["project_settings"]["maya"]["ext_mapping"]
        )
        if ext_mapping:
            self.log.info("Looking in settings for scene type ...")
            # use extension mapping for first family found
            for family in self.families:
                try:
                    self.scene_type = ext_mapping[family]
                    self.log.info(
                        "Using {} as scene type".format(self.scene_type))
                    break
                except KeyError:
                    # no preset found
                    pass
        yeti_nodes = cmds.ls(instance, type="pgYetiMaya")
        if not yeti_nodes:
            raise RuntimeError("No pgYetiMaya nodes found in the instance")

        # Define extract output file path
        dirname = self.staging_dir(instance)
        settings_path = os.path.join(dirname, "yeti.rigsettings")

        # Yeti related staging dirs
        maya_path = os.path.join(dirname,
                                 "yeti_rig.{}".format(self.scene_type))

        self.log.info("Writing metadata file")

        image_search_path = resources_dir = instance.data["resourcesDir"]

        settings = instance.data.get("rigsettings", None)
        assert settings, "Yeti rig settings were not collected."
        settings["imageSearchPath"] = image_search_path
        with open(settings_path, "w") as fp:
            json.dump(settings, fp, ensure_ascii=False)

        # add textures to transfers
        if 'transfers' not in instance.data:
            instance.data['transfers'] = []

        for resource in instance.data.get('resources', []):
            for file in resource['files']:
                src = file
                dst = os.path.join(image_search_path, os.path.basename(file))
                instance.data['transfers'].append([src, dst])

                self.log.info("adding transfer {} -> {}". format(src, dst))

        # Ensure the imageSearchPath is being remapped to the publish folder
        attr_value = {"%s.imageSearchPath" % n: str(image_search_path) for
                      n in yeti_nodes}

        # Get input_SET members
        input_set = next(i for i in instance if i == "input_SET")

        # Get all items
        set_members = cmds.sets(input_set, query=True) or []
        set_members += cmds.listRelatives(set_members,
                                          allDescendents=True,
                                          fullPath=True) or []
        members = cmds.ls(set_members, long=True)

        nodes = instance.data["setMembers"]
        resources = instance.data.get("resources", {})
        with disconnect_plugs(settings, members):
            with yetigraph_attribute_values(resources_dir, resources):
                with lib.attribute_values(attr_value):
                    cmds.select(nodes, noExpand=True)
                    cmds.file(maya_path,
                              force=True,
                              exportSelected=True,
                              typ="mayaAscii" if self.scene_type == "ma" else "mayaBinary",  # noqa: E501
                              preserveReferences=False,
                              constructionHistory=True,
                              shader=False)

        # Ensure files can be stored
        # build representations
        if "representations" not in instance.data:
            instance.data["representations"] = []

        self.log.info("rig file: {}".format(maya_path))
        instance.data["representations"].append(
            {
                'name': self.scene_type,
                'ext': self.scene_type,
                'files': os.path.basename(maya_path),
                'stagingDir': dirname
            }
        )
        self.log.info("settings file: {}".format(settings_path))
        instance.data["representations"].append(
            {
                'name': 'rigsettings',
                'ext': 'rigsettings',
                'files': os.path.basename(settings_path),
                'stagingDir': dirname
            }
        )

        self.log.info("Extracted {} to {}".format(instance, dirname))

        cmds.select(clear=True)
