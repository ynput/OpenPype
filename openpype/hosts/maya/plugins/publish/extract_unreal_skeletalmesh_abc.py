# -*- coding: utf-8 -*-
"""Create Unreal Skeletal Mesh data to be extracted as FBX."""
import os
from contextlib import contextmanager

from maya import cmds  # noqa

from openpype.pipeline import publish
from openpype.hosts.maya.api.lib import (
    extract_alembic,
    suspended_refresh,
    maintained_selection
)


class ExtractUnrealSkeletalMeshAbc(publish.Extractor):
    """Extract Unreal Skeletal Mesh as FBX from Maya. """

    label = "Extract Unreal Skeletal Mesh - Alembic"
    hosts = ["maya"]
    families = ["skeletalMesh"]
    optional = True

    def process(self, instance):
        self.log.debug("Extracting pointcache..")

        geo = cmds.listRelatives(
            instance.data.get("geometry"), allDescendents=True, fullPath=True)
        joints = cmds.listRelatives(
            instance.data.get("joints"), allDescendents=True, fullPath=True)

        nodes = geo + joints

        attrs = instance.data.get("attr", "").split(";")
        attrs = [value for value in attrs if value.strip()]
        attrs += ["cbId"]

        attr_prefixes = instance.data.get("attrPrefix", "").split(";")
        attr_prefixes = [value for value in attr_prefixes if value.strip()]

        # Define output path
        staging_dir = self.staging_dir(instance)
        filename = "{0}.abc".format(instance.name)
        path = os.path.join(staging_dir, filename)

        # The export requires forward slashes because we need
        # to format it into a string in a mel expression
        path = path.replace('\\', '/')

        self.log.debug("Extracting ABC to: {0}".format(path))
        self.log.debug("Members: {0}".format(nodes))
        self.log.debug("Instance: {0}".format(instance[:]))

        options = {
            "step": instance.data.get("step", 1.0),
            "attr": attrs,
            "attrPrefix": attr_prefixes,
            "writeVisibility": True,
            "writeCreases": True,
            "writeColorSets": instance.data.get("writeColorSets", False),
            "writeFaceSets": instance.data.get("writeFaceSets", False),
            "uvWrite": True,
            "selection": True,
            "worldSpace": instance.data.get("worldSpace", True)
        }

        self.log.debug("Options: {}".format(options))

        if int(cmds.about(version=True)) >= 2017:
            # Since Maya 2017 alembic supports multiple uv sets - write them.
            options["writeUVSets"] = True

        if not instance.data.get("includeParentHierarchy", True):
            # Set the root nodes if we don't want to include parents
            # The roots are to be considered the ones that are the actual
            # direct members of the set
            options["root"] = instance.data.get("setMembers")

        with suspended_refresh(suspend=instance.data.get("refresh", False)):
            with maintained_selection():
                cmds.select(nodes, noExpand=True)
                extract_alembic(file=path,
                                # startFrame=start,
                                # endFrame=end,
                                **options)

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': 'abc',
            'ext': 'abc',
            'files': filename,
            "stagingDir": staging_dir,
        }
        instance.data["representations"].append(representation)

        self.log.debug("Extract ABC successful to: {0}".format(path))
