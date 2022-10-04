import os

from maya import cmds

import pyblish.api

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
    active = _import_reference()
    optional= True
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
        m_ref_fname = "{0}.{1}".format(tmp_name, self.scene_type)

        m_ref_path = os.path.join(dir_path, m_ref_fname)

        self.log.info("Performing extraction..")
        current = cmds.file(query=True, sceneName=True)
        cmds.file(save=True, force=True)
        # create temp scene with imported
        # reference for rendering
        reference_node = cmds.ls(type="reference")
        for r in reference_node:
            ref_file = cmds.referenceQuery(r, f=True)
            if r == "sharedReferenceNode":
                cmds.file(ref_file, removeReference=True, referenceNode=r)
                return
            cmds.file(ref_file, importReference=True)

        cmds.file(rename=m_ref_fname)
        cmds.file(save=True, force=True)
        tmp_filepath = cmds.file(query=True, sceneName=True)
        instance.context.data["currentFile"] = tmp_filepath

        with lib.maintained_selection():
            cmds.select(all=True, noExpand=True)
            cmds.file(m_ref_path,
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
        instance.data["files"].append(m_ref_fname)

        if instance.data.get("representations") is None:
            instance.data["representations"] = []

        ref_representation = {
            "name": self.scene_type,
            "ext": self.scene_type,
            "files": m_ref_fname,
            "stagingDir": os.path.dirname(tmp_filepath)
        }

        instance.data["representations"].append(ref_representation)

        self.log.info("Extracted instance '%s' to : '%s'" % (m_ref_fname,
                                                             m_ref_path))

        # re-open the previous scene
        cmds.file(current, open=True)
