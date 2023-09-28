# -*- coding: utf-8 -*-
import os

from maya import cmds  # noqa
import pyblish.api

from openpype.pipeline import publish
from openpype.hosts.maya.api import fbx
from openpype.hosts.maya.api.lib import namespaced


class ExtractFBXAnimation(publish.Extractor):
    """Extract Rig in FBX format from Maya.

    This extracts the rig in fbx with the constraints
    and referenced asset content included.
    This also optionally extract animated rig in fbx with
    geometries included.

    """
    order = pyblish.api.ExtractorOrder
    label = "Extract Animation (FBX)"
    hosts = ["maya"]
    families = ["animation.fbx"]

    def process(self, instance):
        # Define output path
        staging_dir = self.staging_dir(instance)
        filename = "{0}.fbx".format(instance.name)
        path = os.path.join(staging_dir, filename)
        path = path.replace("\\", "/")

        fbx_exporter = fbx.FBXExtractor(log=self.log)
        out_set = instance.data.get("animated_skeleton", [])
        # Export
        instance.data["constraints"] = True
        instance.data["skeletonDefinitions"] = True
        instance.data["referencedAssetsContent"] = True

        fbx_exporter.set_options_from_instance(instance)

        out_set_name = next(out for out in out_set)
        # temporarily disable namespace
        namespace = out_set_name.split(":")[0]
        new_out_set = out_set_name.replace(
            f"{namespace}:", "")
        cmds.namespace(set=':' + namespace)
        cmds.namespace(relativeNames=True)
        with namespaced(":" + namespace, new=False) as namespace:
            fbx_exporter.export(
                new_out_set, path.replace("\\", "/"))

        representations = instance.data.setdefault("representations", [])
        representations.append({
            'name': 'fbx',
            'ext': 'fbx',
            'files': filename,
            "stagingDir": staging_dir
        })

        self.log.debug(
            "Extracted Fbx animation successful to: {0}".format(path))
