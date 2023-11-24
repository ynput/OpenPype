# -*- coding: utf-8 -*-
import os

from maya import cmds  # noqa
import pyblish.api

from openpype.pipeline import publish
from openpype.hosts.maya.api import fbx
from openpype.hosts.maya.api.lib import (
    namespaced, get_namespace, strip_namespace
)


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
        out_members = instance.data.get("animated_skeleton", [])
        # Export
        instance.data["constraints"] = True
        instance.data["skeletonDefinitions"] = True
        instance.data["referencedAssetsContent"] = True
        fbx_exporter.set_options_from_instance(instance)
        # Export from the rig's namespace so that the exported
        # FBX does not include the namespace but preserves the node
        # names as existing in the rig workfile
        if not out_members:
            skeleton_set = [
                i for i in instance
                if i.endswith("skeletonAnim_SET")
            ]
            self.log.debug(
                "Top group of animated skeleton not found in "
                "{}.\nSkipping fbx animation extraction.".format(skeleton_set))
            return

        namespace = get_namespace(out_members[0])
        relative_out_members = [
            strip_namespace(node, namespace) for node in out_members
        ]
        with namespaced(
            ":" + namespace,
            new=False,
            relative_names=True
        ) as namespace:
            fbx_exporter.export(relative_out_members, path)

        representations = instance.data.setdefault("representations", [])
        representations.append({
            'name': 'fbx',
            'ext': 'fbx',
            'files': filename,
            "stagingDir": staging_dir
        })

        self.log.debug(
            "Extracted FBX animation to: {0}".format(path))
