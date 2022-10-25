import os
import sys

from maya import cmds

import pyblish.api
import tempfile

from openpype.lib import run_subprocess
from openpype.pipeline import publish
from openpype.hosts.maya.api import lib


class ExtractImportReference(publish.Extractor):
    """

        Extract the scene with imported reference.
        The temp scene with imported reference is
        published for rendering if this extractor is activated

    """

    label = "Extract Import Reference"
    order = pyblish.api.ExtractorOrder - 0.48
    hosts = ["maya"]
    families = ["renderlayer", "workfile"]
    optional = True
    tmp_format = "_tmp"

    @classmethod
    def apply_settings(cls, project_setting, system_settings): #noqa
        cls.active = project_setting["deadline"]["publish"]["MayaSubmitDeadline"]["import_reference"] # noqa

    def process(self, instance):
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
                    # set scene type to ma
                    self.scene_type = "ma"

        _scene_type = ("mayaAscii"
                       if self.scene_type == "ma"
                       else "mayaBinary")

        dir_path = self.staging_dir(instance)
        # named the file with imported reference
        if instance.name == "Main":
            return
        tmp_name = instance.name + self.tmp_format
        current_name = cmds.file(query=True, sceneName=True)
        ref_scene_name = "{0}.{1}".format(tmp_name, self.scene_type)

        reference_path = os.path.join(dir_path, ref_scene_name)
        tmp_path = os.path.dirname(current_name) + "/" + ref_scene_name

        self.log.info("Performing extraction..")

        # This generates script for mayapy to take care of reference
        # importing outside current session. It is passing current scene
        # name and destination scene name.
        script = ("""
# -*- coding: utf-8 -*-
'''Script to import references to given scene.'''
import maya.standalone
maya.standalone.initialize()
# scene names filled by caller
current_name = "{current_name}"
ref_scene_name = "{ref_scene_name}"
print(">>> Opening {{}} ...".format(current_name))
cmds.file(current_name, open=True, force=True)
reference_node = cmds.ls(type='reference')
print(">>> Processing references")
for ref in reference_node:
    ref_file = cmds.referenceQuery(ref, f=True)
    print("--- {{}}".format(ref))
    print("--> {{}}".format(ref_file))
    if ref == 'sharedReferenceNode':
        cmds.file(ref_file, removeReference=True, referenceNode=ref)
    else:
        cmds.file(ref_file, importReference=True)
print(">>> Saving scene as {{}}".format(ref_scene_name))

cmds.file(rename=ref_scene_name)
cmds.file(save=True, force=True)
print("*** Done")
        """).format(current_name=current_name, ref_scene_name=tmp_path)
        mayapy_exe = os.path.join(os.getenv("MAYA_LOCATION"), "bin", "mayapy")
        if sys.platform == "windows":
            mayapy_exe += ".exe"
            mayapy_exe = os.path.normpath(mayapy_exe)
        # can't use TemporaryNamedFile as that can't be opened in another
        # process until handles are closed by context manager.
        with tempfile.TemporaryDirectory() as tmp_dir_name:
            tmp_file_name = os.path.join(tmp_dir_name, "import_ref.py")
            tmp = open(tmp_file_name, "w+t")
            subprocess_args = [
                mayapy_exe,
                tmp_file_name
            ]
            self.log.info("Using temp file: {}".format(tmp.name))
            try:
                tmp.write(script)
                tmp.close()
                run_subprocess(subprocess_args)
            except Exception:
                self.log.error("Import reference failed", exc_info=True)
                raise

        with lib.maintained_selection():
            cmds.select(all=True, noExpand=True)
            cmds.file(reference_path,
                      force=True,
                      typ=_scene_type,
                      exportSelected=True,
                      channels=True,
                      constraints=True,
                      shader=True,
                      expressions=True,
                      constructionHistory=True)

        instance.context.data["currentFile"] = tmp_path

        if "files" not in instance.data:
            instance.data["files"] = []
        instance.data["files"].append(ref_scene_name)

        if instance.data.get("representations") is None:
            instance.data["representations"] = []

        ref_representation = {
            "name": self.scene_type,
            "ext": self.scene_type,
            "files": ref_scene_name,
            "stagingDir": os.path.dirname(current_name),
            "outputName": "imported"
        }
        self.log.info("%s" % ref_representation)

        instance.data["representations"].append(ref_representation)

        self.log.info("Extracted instance '%s' to : '%s'" % (ref_scene_name,
                                                             reference_path))
