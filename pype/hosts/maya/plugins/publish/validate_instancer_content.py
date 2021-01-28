import maya.cmds as cmds

import pyblish.api
from pype.hosts.maya import lib


class ValidateInstancerContent(pyblish.api.InstancePlugin):
    """Validates that all meshes in the instance have object IDs.

    This skips a check on intermediate objects because we consider them
    not important.
    """
    order = pyblish.api.ValidatorOrder
    label = 'Instancer Content'
    families = ['instancer']

    def process(self, instance):

        error = False
        members = instance.data['setMembers']
        export_members = instance.data['exactExportMembers']

        self.log.info("Contents {0}".format(members))

        if not len(members) == len(cmds.ls(members, type="instancer")):
            self.log.error("Instancer can only contain instancers")
            error = True

        # TODO: Implement better check for particles are cached
        if not cmds.ls(export_members, type="nucleus"):
            self.log.error("Instancer must have a connected nucleus")
            error = True

        if not cmds.ls(export_members, type="cacheFile"):
            self.log.error("Instancer must be cached")
            error = True

        hidden = self.check_geometry_hidden(export_members)
        if not hidden:
            error = True
            self.log.error("Instancer input geometry must be hidden "
                           "the scene. Invalid: {0}".format(hidden))

        # Ensure all in one group
        parents = cmds.listRelatives(members,
                                     allParents=True,
                                     fullPath=True) or []
        roots = list(set(cmds.ls(parents, assemblies=True, long=True)))
        if len(roots) > 1:
            self.log.error("Instancer should all be contained in a single "
                           "group. Current roots: {0}".format(roots))
            error = True

        if error:
            raise RuntimeError("Instancer Content is invalid. See log.")

    def check_geometry_hidden(self, export_members):

        # Ensure all instanced geometry is hidden
        shapes = cmds.ls(export_members,
                         dag=True,
                         shapes=True,
                         noIntermediate=True)
        meshes = cmds.ls(shapes, type="mesh")

        visible = [node for node in meshes
                   if lib.is_visible(node,
                                     displayLayer=False,
                                     intermediateObject=False)]
        if visible:
            return False

        return True
