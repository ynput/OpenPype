# -*- coding: utf-8 -*-
import os

from maya import cmds  # noqa
import maya.mel as mel  # noqa
import pyblish.api

from openpype.pipeline import publish
from openpype.hosts.maya.api.lib import maintained_selection
from openpype.hosts.maya.api import fbx


class ExtractRigFBX(publish.Extractor):
    """Extract Rig in FBX format from Maya.

    This extracts the rig in fbx with the constraints
    and referenced asset content included.
    This also optionally extract animated rig in fbx with
    geometries included.

    """
    order = pyblish.api.ExtractorOrder
    label = "Extract Rig (FBX)"
    families = ["rig"]

    def process(self, instance):
        if not instance.data.get("fbx_enabled"):
            self.log.debug("fbx extractor has been disable.."
                           "Skipping the action...")
            return

        # Define output path
        staging_dir = self.staging_dir(instance)
        filename = "{0}.fbx".format(instance.name)
        path = os.path.join(staging_dir, filename)

        # The export requires forward slashes because we need
        # to format it into a string in a mel expression
        path = path.replace('\\', '/')

        self.log.debug("Extracting FBX to: {0}".format(path))

        control_rigs = instance.data.get("control_rigs",[])
        skeletal_mesh = instance.data.get("skeleton_mesh", [])
        members = control_rigs + skeletal_mesh
        self._to_extract(instance, path, members)


        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': 'fbx',
            'ext': 'fbx',
            'files': filename,
            "stagingDir": staging_dir,
        }
        instance.data["representations"].append(representation)

        self.log.debug("Extract FBX successful to: {0}".format(path))
        if skeletal_mesh:
            self._to_extract(instance, path, skeletal_mesh)
            representation = {
                'name': 'fbxanim',
                'ext': 'fbx',
                'files': filename,
                "stagingDir": staging_dir,
                "outputName": "fbxanim"
            }
            instance.data["representations"].append(representation)
            self.log.debug("Extract animated FBX successful to: {0}".format(path))

    def _to_extract(self, instance, path, members):
        fbx_exporter = fbx.FBXExtractor(log=self.log)
        control_rigs = instance.data.get("control_rigs",[])
        skeletal_mesh = instance.data.get("skeleton_mesh", [])
        static_sets = control_rigs + skeletal_mesh
        if members == static_sets:
            instance.data["constraints"] = True
            instance.data["referencedAssetsContent"] = True
        if members == skeletal_mesh:
            instance.data["constraints"] = True
            instance.data["referencedAssetsContent"] = True
            instance.data["animationOnly"] = True

        fbx_exporter.set_options_from_instance(instance)

        # Export
        with maintained_selection():
            fbx_exporter.export(members, path)
            cmds.select(members, r=1, noExpand=True)
            mel.eval('FBXExport -f "{}" -s'.format(path))
