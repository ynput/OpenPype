import os

from maya import cmds

import pyblish.api

from openpype.pipeline import publish, legacy_io
from openpype.settings import get_project_settings
from openpype.hosts.maya.api import lib


def _get_project_setting():
    project_name = legacy_io.active_project()
    project_setting = get_project_settings(project_name)
    maya_enabled = (
        project_setting["maya"]["publish"]["ImportReference"]["enabled"]
    )
    use_published = (
        project_setting["deadline"]["publish"]["MayaSubmitDeadline"]["use_published"] # noqa
    )
    if maya_enabled != use_published:
        return False
    else:
        return use_published


class ImportReference(publish.Extractor):
    """

        Extract the scene with imported reference.
        The temp scene with imported reference is
        published for rendering if this extractor is activated

    """

    label = "Import Reference"
    order = pyblish.api.ExtractorOrder - 0.48
    hosts = ["maya"]
    families = ["renderlayer", "workfile"]
    active = _get_project_setting()
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
                    # no preset found
                    pass

        _scene_type = ("mayaAscii"
                       if self.scene_type == "ma"
                       else "mayaBinary")

        dir_path = self.staging_dir(instance)
        # named the file with imported reference
        tmp_name = instance.name + self.tmp_format
        m_ref_fname = "{0}.{1}".format(tmp_name, self.scene_type)

        m_ref_path = os.path.join(dir_path, m_ref_fname)

        self.log.info("Performing extraction..")
        current = cmds.file(query=True, sceneName=True)
        cmds.file(save=True, force=True)

        self.log.info("Performing extraction..")

        # create temp scene with imported
        # reference for rendering
        reference_node = cmds.ls(type="reference")
        for r in reference_node:
            rFile = cmds.referenceQuery(r, f=True)
            if r == "sharedReferenceNode":
                cmds.file(rFile, removeReference=True, referenceNode=r)
            cmds.file(rFile, importReference=True)

        if current.endswith(self.scene_type):
            current_path = os.path.dirname(current)
            tmp_path_name = os.path.join(current_path, tmp_name)
            cmds.file(rename=tmp_path_name)
            cmds.file(save=True, force=True)

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
                      constructionHistory=True
            )

        if "files" not in instance.data:
            instance.data["files"] = []

        instance.data["files"].append(m_ref_path)

        if instance.data.get("representations") is None:
            instance.data["representations"] = []

        ref_representation = {
            "name": self.scene_type,
            "ext": self.scene_type,
            "files": os.path.basename(m_ref_fname),
            "stagingDir": dir_path
        }
        instance.data["representations"].append(ref_representation)

        self.log.info("Extracted instance '%s' to : '%s'" % (tmp_name,
                                                             m_ref_path))

        cmds.file(current, open=True)
