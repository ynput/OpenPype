# -*- coding: utf-8 -*-

from maya import cmds  # noqa
import pyblish.api
import openpype.api
import openpype.hosts.maya.api.action
import re


class ValidateUnrealStaticMeshName(pyblish.api.InstancePlugin):
    """Validate name of Unreal Static Mesh

    Unreals naming convention states that staticMesh should start with `SM`
    prefix - SM_[Name]_## (Eg. SM_sube_01).These prefixes can be configured
    in Settings UI. This plugin also validates other types of
    meshes - collision meshes:

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
    order = openpype.api.ValidateContentsOrder
    hosts = ["maya"]
    families = ["unrealStaticMesh"]
    label = "Unreal StaticMesh Name"
    actions = [openpype.hosts.maya.api.action.SelectInvalidAction]
    regex_mesh = r"(?P<renderName>.*)_(\d{2})"
    regex_collision = r"_(?P<renderName>.*)_(\d{2})"

    @classmethod
    def get_invalid(cls, instance):

        invalid = []

        combined_geometry_name = instance.data.get(
            "staticMeshCombinedName", None)
        if cls.validate_mesh:
            # compile regex for testing names
            regex_mesh = "{}{}".format(
                ("_" + cls.static_mesh_prefix) or "", cls.regex_mesh
            )
            sm_r = re.compile(regex_mesh)
            if not sm_r.match(combined_geometry_name):
                cls.log.error("Mesh doesn't comply with name validation.")
                return True

        if cls.validate_collision:
            collision_set = instance.data.get("collisionMembers", None)
            # soft-fail is there are no collision objects
            if not collision_set:
                cls.log.warning("No collision objects to validate.")
                return False

            regex_collision = "{}{}".format(
                "({})_".format(
                    "|".join("(0}".format(p) for p in cls.collision_prefixes)
                ) or "", cls.regex_collision
            )
            cl_r = re.compile(regex_collision)

            for obj in collision_set:
                cl_m = cl_r.match(obj)
                if not cl_m:
                    cls.log.error("{} is invalid".format(obj))
                    invalid.append(obj)
                elif cl_m.group("renderName") != combined_geometry_name:
                    cls.log.error(
                        "Collision object name doesn't match"
                        "static mesh name: {} != {}".format(
                            cl_m.group("renderName"),
                            combined_geometry_name)
                    )
                    invalid.append(obj)

        return invalid

    def process(self, instance):
        # todo: load prefixes from creator settings.

        if not self.validate_mesh and not self.validate_collision:
            self.log.info("Validation of both mesh and collision names"
                          "is disabled.")
            return

        if not instance.data.get("collisionMembers", None):
            self.log.info("There are no collision objects to validate")
            return

        invalid = self.get_invalid(instance)

        if invalid:
            raise RuntimeError("Model naming is invalid. See log.")
