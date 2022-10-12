import os
import sys

from maya import cmds

import pyblish.api

from openpype.lib import run_subprocess
from openpype.pipeline import publish, legacy_io
from openpype.settings import get_project_settings
from openpype.hosts.maya.api import lib


def _import_reference():
    project_name = legacy_io.active_project()
    project_setting = get_project_settings(project_name)
    import_reference = (
        project_setting["deadline"]["publish"]["MayaSubmitDeadline"]["import_reference"] # noqa
    )
    return import_reference


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
    active = True
    optional = True
    tmp_format = "_tmp"

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
        ref_scene_name  = "{0}.{1}".format(tmp_name, self.scene_type)

        reference_path = os.path.join(dir_path, ref_scene_name)

        self.log.info("Performing extraction..")
        script = f"""
        import maya.standalone
        maya.standalone.initialize()
        cmds.file('{current_name}', open=True, force=True)
        reference_node = cmds.ls(type='reference')
        for ref in reference_node:
            ref_file = cmds.referenceQuery(ref, f=True)
            if ref == 'sharedReferenceNode':
                cmds.file(ref_file, removeReference=True, referenceNode=ref)
            else:
                cmds.file(ref_file, importReference=True)
        try:
            cmds.file(rename='{ref_scene_name}')
        except SyntaxError:
            cmds.file(rename='{ref_scene_name}')

        cmds.file(save=True, force=True)
        """

        mayapy_exe = os.path.join(os.getenv("MAYA_LOCATION"), "bin", "mayapy")
        if sys.platform == "windows":
            mayapy_exe = mayapy_exe + ".exe"

        subprocess_args = [
            mayapy_exe,
            "-c",
        script.replace("\n", ";")
        ]
        try:
            out = run_subprocess(subprocess_args)
        except Exception:
            self.log.error("Import reference failed", exc_info=True)
            raise

        instance.context.data["currentFile"] = ref_scene_name
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

        if "files" not in instance.data:
            instance.data["files"] = []
        instance.data["files"].append(ref_scene_name)

        if instance.data.get("representations") is None:
            instance.data["representations"] = []

        ref_representation = {
            "name": self.scene_type,
            "ext": self.scene_type,
            "files": ref_scene_name,
            "stagingDir": os.path.dirname(current_name)
        }

        instance.data["representations"].append(ref_representation)

        self.log.info("Extracted instance '%s' to : '%s'" % (ref_scene_name,
                                                             reference_path))
