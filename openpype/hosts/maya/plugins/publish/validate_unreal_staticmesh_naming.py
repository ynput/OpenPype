# -*- coding: utf-8 -*-
"""Validator for correct naming of Static Meshes."""
import re

import pyblish.api

import openpype.hosts.maya.api.action
from openpype.pipeline import legacy_io
from openpype.settings import get_project_settings
from openpype.pipeline.publish import (
    ValidateContentsOrder,
    OptionalPyblishPluginMixin,
    PublishValidationError
)


class ValidateUnrealStaticMeshName(pyblish.api.InstancePlugin,
                                   OptionalPyblishPluginMixin):
    """Validate name of Unreal Static Mesh

    Unreals naming convention states that staticMesh should start with `SM`
    prefix - SM_[Name]_## (Eg. SM_sube_01).These prefixes can be configured
    in Settings UI. This plugin also validates other types of
    meshes - collision meshes:

    UBX_[RenderMeshName]*:
                             Boxes are created with the Box objects type in
                             Max or with the Cube polygonal primitive in Maya.
                             You cannot move the vertices around or deform it
                             in any way to make it something other than a
                             rectangular prism, or else it will not work.

    UCP_[RenderMeshName]*:
                             Capsules are created with the Capsule object type.
                             The capsule does not need to have many segments
                             (8 is a good number) at all because it is
                             converted into a true capsule for collision. Like
                             boxes, you should not move the individual
                             vertices around.

    USP_[RenderMeshName]*:
                             Spheres are created with the Sphere object type.
                             The sphere does not need to have many segments
                             (8 is a good number) at all because it is
                             converted into a true sphere for collision. Like
                             boxes, you should not move the individual
                             vertices around.

    UCX_[RenderMeshName]*:
                             Convex objects can be any completely closed
                             convex 3D shape. For example, a box can also be
                             a convex object

    This validator also checks if collision mesh [RenderMeshName] matches one
    of SM_[RenderMeshName].

    """
    optional = True
    order = ValidateContentsOrder
    hosts = ["maya"]
    families = ["staticMesh"]
    label = "Unreal Static Mesh Name"
    actions = [openpype.hosts.maya.api.action.SelectInvalidAction]
    regex_mesh = r"(?P<renderName>.*))"
    regex_collision = r"(?P<renderName>.*)"

    @classmethod
    def get_invalid(cls, instance):

        invalid = []

        collision_prefixes = (
            instance.context.data["project_settings"]
            ["maya"]
            ["create"]
            ["CreateUnrealStaticMesh"]
            ["collision_prefixes"]
        )

        if cls.validate_mesh:
            # compile regex for testing names
            regex_mesh = "{}{}".format(
                ("_" + cls.static_mesh_prefix) or "", cls.regex_mesh
            )
            sm_r = re.compile(regex_mesh)
            if not sm_r.match(instance.data.get("subset")):
                cls.log.error("Mesh doesn't comply with name validation.")
                return True

        if cls.validate_collision:
            collision_set = instance.data.get("collisionMembers", None)
            # soft-fail is there are no collision objects
            if not collision_set:
                cls.log.warning("No collision objects to validate.")
                return False

            regex_collision = "{}{}_(\\d+)".format(
                "(?P<prefix>({}))_".format(
                    "|".join("{0}".format(p) for p in collision_prefixes)
                ) or "", cls.regex_collision
            )

            cl_r = re.compile(regex_collision)

            asset_name = instance.data["assetEntity"]["name"]
            mesh_name = "{}{}".format(asset_name,
                                      instance.data.get("variant", []))

            for obj in collision_set:
                cl_m = cl_r.match(obj)
                if not cl_m:
                    cls.log.error("{} is invalid".format(obj))
                    invalid.append(obj)
                else:
                    expected_collision = "{}_{}".format(
                        cl_m.group("prefix"),
                        mesh_name
                    )

                    if not obj.startswith(expected_collision):

                        cls.log.error(
                            "Collision object name doesn't match "
                            "static mesh name"
                        )
                        cls.log.error("{}_{} != {}_{}*".format(
                            cl_m.group("prefix"),
                            cl_m.group("renderName"),
                            cl_m.group("prefix"),
                            mesh_name,
                        ))
                        invalid.append(obj)

        return invalid

    def process(self, instance):
        if not self.is_active(instance.data):
            return

        if not self.validate_mesh and not self.validate_collision:
            self.log.debug("Validation of both mesh and collision names"
                           "is disabled.")
            return

        if not instance.data.get("collisionMembers", None):
            self.log.debug("There are no collision objects to validate")
            return

        invalid = self.get_invalid(instance)

        if invalid:
            raise PublishValidationError("Model naming is invalid. See log.")
