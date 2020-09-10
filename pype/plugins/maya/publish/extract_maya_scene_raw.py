# -*- coding: utf-8 -*-
"""Extract data as Maya scene (raw)."""
import os

from maya import cmds

import avalon.maya
import pype.api


class ExtractMayaSceneRaw(pype.api.Extractor):
    """Extract as Maya Scene (raw).

    This will preserve all references, construction history, etc.
    """

    label = "Maya Scene (Raw)"
    hosts = ["maya"]
    families = ["mayaAscii",
                "setdress",
                "layout"]
    scene_type = "ma"

    def process(self, instance):
        """Plugin entry point."""
        ext_mapping = instance.context.data["presets"]["maya"].get("ext_mapping")  # noqa: E501
        if ext_mapping:
            self.log.info("Looking in presets for scene type ...")
            # use extension mapping for first family found
            for family in self.families:
                try:
                    self.scene_type = ext_mapping[family]
                    self.log.info(
                        "Using {} as scene type".format(self.scene_type))
                    break
                except AttributeError:
                    # no preset found
                    pass
        # Define extract output file path
        dir_path = self.staging_dir(instance)
        filename = "{0}.{1}".format(instance.name, self.scene_type)
        path = os.path.join(dir_path, filename)

        # Whether to include all nodes in the instance (including those from
        # history) or only use the exact set members
        members_only = instance.data.get("exactSetMembersOnly", False)
        if members_only:
            members = instance.data.get("setMembers", list())
            if not members:
                raise RuntimeError("Can't export 'exact set members only' "
                                   "when set is empty.")
        else:
            members = instance[:]

        # Perform extraction
        self.log.info("Performing extraction ...")
        with avalon.maya.maintained_selection():
            cmds.select(members, noExpand=True)
            cmds.file(path,
                      force=True,
                      typ="mayaAscii" if self.scene_type == "ma" else "mayaBinary",  # noqa: E501
                      exportSelected=True,
                      preserveReferences=True,
                      constructionHistory=True,
                      shader=True,
                      constraints=True,
                      expressions=True)

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': self.scene_type,
            'ext': self.scene_type,
            'files': filename,
            "stagingDir": dir_path
        }
        instance.data["representations"].append(representation)

        self.log.info("Extracted instance '%s' to: %s" % (instance.name, path))
