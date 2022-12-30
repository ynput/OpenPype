import os

from maya import cmds

import pyblish.api

from openpype.pipeline.publish import ValidateContentsOrder


class ValidatePathForPlugin(pyblish.api.InstancePlugin):
    """
    Ensure Paths in Non-Maya Nodes(from plugins
    such as Yeti, AbcExport) are correct
    """

    order = ValidateContentsOrder
    hosts = ['maya']
    families = ["workfile"]
    label = "Non-existent Paths in Non-Maya Nodes"

    def get_invalid(self, instance):
        invalid = list()
        # check alembic node
        abc_node = cmds.ls(type="AlembicNode")
        if abc_node:
            for abc in abc_node:
                abc_fname = cmds.getAttr(abc + ".abc_File")
                if abc_fname and not os.path.exists(abc_fname):
                    invalid.append(abc)
        # check renderman node
        rman_archive = cmds.ls(type="RenderManArchive")
        if rman_archive:
            for rib in rman_archive:
                rib_fname = cmds.getAttr(rib+".filename")
                if rman_archive and not os.path.exists(rib_fname):
                    invalid.append(rib)
        # check Yeti node
        yeti_node = cmds.ls(type="pgYetiMaya")
        if yeti_node:
            for yeti in yeti_node:
                yeti_fname = cmds.getAttr(yeti+".cacheFileName")
                if yeti_fname and not os.path.exists(yeti_fname):
                    invalid.append(yeti)
        # check arnold_standin node
        arnold_standin = cmds.ls(type="aiStandIn")
        if arnold_standin:
            for standin in arnold_standin:
                standin_fname = cmds.getAttr(standin+".dso")
                if standin_fname and not os.path.exists(standin_fname):
                    invalid.append(standin)
        # check vray proxy node
        vray_proxy = cmds.ls(type="VRayProxy")
        if vray_proxy:
            for vray in vray_proxy:
                vray_fname = cmds.getAttr(vray+".fileName")
                if vray_fname and not os.path.exists(vray_fname):
                    invalid.append(vray)
        # check redshift proxy node
        redshift_proxy = cmds.ls(type="RedshiftProxyMesh")
        if redshift_proxy:
            for redshift in redshift_proxy:
                red_fname = cmds.getAttr(redshift+".fileName")
                if red_fname and not os.path.exists(red_fname):
                    invalid.append(redshift)

        return invalid

    def process(self, instance):
        """Process all directories Set as Filenames in Non-Maya Nodes"""
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Non-existent Path "
                               "found: {0}".format(invalid))
