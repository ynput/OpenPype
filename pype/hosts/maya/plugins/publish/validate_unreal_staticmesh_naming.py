# -*- coding: utf-8 -*-

from maya import cmds
import pyblish.api
import pype.api
import pype.hosts.maya.action
import re


class ValidateUnrealStaticmeshName(pyblish.api.InstancePlugin):
    """Validate name of Unreal Static Mesh

    Unreals naming convention states that staticMesh sould start with `SM`
    prefix - SM_[Name]_## (Eg. SM_sube_01). This plugin also validates other
    types of meshes - collision meshes:

    UBX_[RenderMeshName]_##:
                             Boxes are created with the Box objects type in
                             Max or with the Cube polygonal primitive in Maya.
                             You cannot move the vertices around or deform it
                             in any way to make it something other than a
                             rectangular prism, or else it will not work.

    UCP_[RenderMeshName]_##:
                             Capsules are created with the Capsule object type.
                             The capsule does not need to have many segments
                             (8 is a good number) at all because it is
                             converted into a true capsule for collision. Like
                             boxes, you should not move the individual
                             vertices around.

    USP_[RenderMeshName]_##:
                             Spheres are created with the Sphere object type.
                             The sphere does not need to have many segments
                             (8 is a good number) at all because it is
                             converted into a true sphere for collision. Like
                             boxes, you should not move the individual
                             vertices around.

    UCX_[RenderMeshName]_##:
                             Convex objects can be any completely closed
                             convex 3D shape. For example, a box can also be
                             a convex object

    This validator also checks if collision mesh [RenderMeshName] matches one
    of SM_[RenderMeshName].

    """
    optional = True
    order = pype.api.ValidateContentsOrder
    hosts = ["maya"]
    families = ["unrealStaticMesh"]
    label = "Unreal StaticMesh Name"
    actions = [pype.hosts.maya.action.SelectInvalidAction]
    regex_mesh = r"SM_(?P<renderName>.*)_(\d{2})"
    regex_collision = r"((UBX)|(UCP)|(USP)|(UCX))_(?P<renderName>.*)_(\d{2})"

    @classmethod
    def get_invalid(cls, instance):

        # find out if supplied transform is group or not
        def is_group(groupName):
            try:
                children = cmds.listRelatives(groupName, children=True)
                for child in children:
                    if not cmds.ls(child, transforms=True):
                        return False
                return True
            except Exception:
                return False

        invalid = []
        content_instance = instance.data.get("setMembers", None)
        if not content_instance:
            cls.log.error("Instance has no nodes!")
            return True
        pass
        descendants = cmds.listRelatives(content_instance,
                                         allDescendents=True,
                                         fullPath=True) or []

        descendants = cmds.ls(descendants, noIntermediate=True, long=True)
        trns = cmds.ls(descendants, long=False, type=('transform'))

        # filter out groups
        filter = [node for node in trns if not is_group(node)]

        # compile regex for testing names
        sm_r = re.compile(cls.regex_mesh)
        cl_r = re.compile(cls.regex_collision)

        sm_names = []
        col_names = []
        for obj in filter:
            sm_m = sm_r.match(obj)
            if sm_m is None:
                # test if it matches collision mesh
                cl_r = sm_r.match(obj)
                if cl_r is None:
                    cls.log.error("invalid mesh name on: {}".format(obj))
                    invalid.append(obj)
                else:
                    col_names.append((cl_r.group("renderName"), obj))
            else:
                sm_names.append(sm_m.group("renderName"))

        for c_mesh in col_names:
            if c_mesh[0] not in sm_names:
                cls.log.error(("collision name {} doesn't match any "
                               "static mesh names.").format(obj))
                invalid.append(c_mesh[1])

        return invalid

    def process(self, instance):

        invalid = self.get_invalid(instance)

        if invalid:
            raise RuntimeError("Model naming is invalid. See log.")
