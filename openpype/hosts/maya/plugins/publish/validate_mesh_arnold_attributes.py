from maya import cmds
import pyblish.api

import openpype.hosts.maya.api.action
from openpype.hosts.maya.api.lib import (
    maintained_selection,
    delete_after,
    undo_chunk,
    get_attribute,
    set_attribute
)
from openpype.pipeline.publish import (
    OptionalPyblishPluginMixin,
    RepairAction,
    ValidateMeshOrder,
    PublishValidationError
)


class ValidateMeshArnoldAttributes(pyblish.api.InstancePlugin,
                                   OptionalPyblishPluginMixin):
    """Validate the mesh has default Arnold attributes.

    It compares all Arnold attributes from a default mesh. This is to ensure
    later published looks can discover non-default Arnold attributes.
    """

    order = ValidateMeshOrder
    hosts = ["maya"]
    families = ["model"]
    label = "Mesh Arnold Attributes"
    actions = [
        openpype.hosts.maya.api.action.SelectInvalidAction,
        RepairAction
    ]

    optional = True

    @classmethod
    def apply_settings(cls, project_settings, system_settings):
        # todo: this should not be done this way
        attr = "defaultRenderGlobals.currentRenderer"
        cls.active = cmds.getAttr(attr).lower() == "arnold"

    @classmethod
    def get_default_attributes(cls):
        # Get default arnold attribute values for mesh type.
        defaults = {}
        with delete_after() as tmp:
            transform = cmds.createNode("transform")
            tmp.append(transform)

            mesh = cmds.createNode("mesh", parent=transform)
            arnold_attributes = cmds.listAttr(mesh,
                                              string="ai*",
                                              fromPlugin=True) or []
            for attr in arnold_attributes:
                plug = "{}.{}".format(mesh, attr)
                try:
                    defaults[attr] = get_attribute(plug)
                except PublishValidationError:
                    cls.log.debug("Ignoring arnold attribute: {}".format(attr))

        return defaults

    @classmethod
    def get_invalid_attributes(cls, instance, compute=False):
        invalid = []

        if compute:

            meshes = cmds.ls(instance, type="mesh", long=True)
            if not meshes:
                return []

            # Compare the values against the defaults
            defaults = cls.get_default_attributes()
            for mesh in meshes:
                for attr_name, default_value in defaults.items():
                    plug = "{}.{}".format(mesh, attr_name)
                    if get_attribute(plug) != default_value:
                        invalid.append(plug)

            instance.data["nondefault_arnold_attributes"] = invalid

        return instance.data.get("nondefault_arnold_attributes", [])

    @classmethod
    def get_invalid(cls, instance):
        invalid_attrs = cls.get_invalid_attributes(instance, compute=False)
        invalid_nodes = set(attr.split(".", 1)[0] for attr in invalid_attrs)
        return sorted(invalid_nodes)

    @classmethod
    def repair(cls, instance):
        with maintained_selection():
            with undo_chunk():
                defaults = cls.get_default_attributes()
                attributes = cls.get_invalid_attributes(
                    instance, compute=False
                )
                for attr in attributes:
                    node, attr_name = attr.split(".", 1)
                    value = defaults[attr_name]
                    set_attribute(
                        node=node,
                        attribute=attr_name,
                        value=value
                    )

    def process(self, instance):
        if not self.is_active(instance.data):
            return

        if not cmds.pluginInfo("mtoa", query=True, loaded=True):
            # Arnold attributes only exist if plug-in is loaded
            return

        invalid = self.get_invalid_attributes(instance, compute=True)
        if invalid:
            raise PublishValidationError(
                "Non-default Arnold attributes found in instance:"
                " {0}".format(invalid)
            )
