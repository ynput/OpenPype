from maya import cmds

from pprint import pprint

from openpype.hosts.maya.api import lib, plugin
from openpype.lib import (
    BoolDef,
    TextDef,
    NumberDef,
    EnumDef,
    UISeparatorDef,
    UILabelDef,
)


def _get_animation_attr_defs(cls):
    """Get Animation generic ddefinitions."""
    defs = lib.collect_animation_defs()
    defs.extend(
        [
            BoolDef("farm", label="Submit to Farm"),
            NumberDef("priority", label="Farm job Priority", default=50),
            BoolDef("refresh", label="Refresh viewport during export"),
            BoolDef("includeParentHierarchy", label="Include Parent Hierarchy"),
            BoolDef("writeNormals", label="Write Normals"),
            BoolDef("writeCreases", label="Write Creases"),
        ]
    )

    return defs


def _get_animation_abc_attr_defs(cls):
    """Get definitions relating to Alembic."""
    # List of arguments extracted from AbcExport -h
    # Them being here doesn't imply we support them or that we need them at this
    # point, it's a convininece list to populate the UI defaults.
    alembic_attributes = [
        "preRollStartFrame",
        "dontSkipUnwrittenFrames",
        "verbose",
        "attr",
        "autoSubd",
        "attrPrefix",
        "dataFormat",
        "eulerFilter",
        "frameRange",
        "frameRelativeSample",
        "noNormals",
        "preRoll",
        "renderableOnly",
        "root",
        "step",
        "selection",
        "stripNamespaces",
        "userAttr",
        "userAttrPrefix",
        "uvWrite",
        "uvsOnly",
        "writeColorSets",
        "writeFaceSets",
        "wholeFrameGeo",
        "worldSpace",
        "writeVisibility",
        "writeUVSets",
        "melPerFrameCallback",
        "melPostJobCallback",
        "pythonPerFrameCallback",
        "pythonPostJobCallback",
    ]

    abc_defs = [UISeparatorDef(), UILabelDef("Alembic Options")]

    alembic_editable_attributes = getattr(cls, "abc_editable_flags", None)

    if not alembic_editable_attributes:
        print("No Almbic attributes found in settings.")
        return None

    print("Processing editable Alembic attributes...")

    abc_boolean_defs = [
        "writeColorSets",
        "writeFaceSets",
        "renderableOnly",
        "visibleOnly",
        "worldSpace",
        "noNormals",
        "includeUserDefinedAttributes",
        "eulerFilter",
        "preRoll",
        "stripNamespaces",
        "uvWrite",
        "verbose",
        "wholeFrameGeo",
        "writeUVSets",
        "writeVisibility",
    ]

    abc_boolean_defaults = [
        "uvWrite",
        "worldSpace",
        "writeVisibility",
    ]

    enabled_boolean_attributes = [
        attrib for attrib in abc_boolean_defs if attrib in alembic_editable_attributes
    ]

    if enabled_boolean_attributes:
        abc_defs.extend(
            [
                EnumDef(
                    "abcExportFlags",
                    enabled_boolean_attributes,
                    default=abc_boolean_defaults,
                    multiselection=True,
                    label="Alembic Export Flags",
                )
            ]
        )

    abc_defs.append(
        TextDef(
            "attr",
            label="Alembic Custom Attributes",
            placeholder="attr1, attr2",
            disabled=True if "attr" not in alembic_editable_attributes else False,
        )
    )

    abc_defs.append(
        TextDef(
            "attrPrefix",
            label="Alembic Custom Attributes Prefix",
            placeholder="prefix1, prefix2",
            disabled=True if "attrPrefix" not in alembic_editable_attributes else False,
        )
    )

    abc_defs.append(
        EnumDef(
            "dataFormat",
            label="Alembic Data Format",
            items=["ogawa", "HDF"],
            disabled=True if "dataFormat" not in alembic_editable_attributes else False,
        )
    )

    abc_defs.append(
        NumberDef(
            "preRollStartFrame",
            label="Start frame for preroll (Alembic)",
            tooltip=(
                "The frame to start scene evaluation at. This is used to set"
                " the starting frame for time dependent translations and can"
                " be used to evaluate run-up that isn't actually translated."
            ),
            disabled=True
            if "preRollStartFrame" not in alembic_editable_attributes
            else False,
        )
    )

    return abc_defs


class CreateAnimation(plugin.MayaHiddenCreator):
    """Animation output for character rigs

    We hide the animation creator from the UI since the creation of it is
    automated upon loading a rig. There's an inventory action to recreate it
    for loaded rigs if by chance someone deleted the animation instance.
    """

    identifier = "io.openpype.creators.maya.animation"
    name = "animationDefault"
    label = "Animation"
    family = "animation"
    icon = "male"

    write_color_sets = False
    write_face_sets = False
    include_parent_hierarchy = False
    include_user_defined_attributes = False

    def get_instance_attr_defs(self):
        super(CreateAnimation, self).get_instance_attr_defs()
        # adding project settings, since MayaHiddenCreator does not
        # handle this for us (yet?)
        settings = (
            getattr(self, "project_settings", {})
            .get("maya", {})
            .get("create", {})
            .get("CreateAnimation")
        )

        for key, value in settings.items():
            setattr(self, key, value)

        defs = _get_animation_attr_defs(self)

        abc_defs = _get_animation_abc_attr_defs(self)

        if abc_defs:
            defs.extend(abc_defs)

        return defs


class CreatePointCache(plugin.MayaCreator):
    """Alembic pointcache for animated data"""

    identifier = "io.openpype.creators.maya.pointcache"
    label = "Pointcache"
    family = "pointcache"
    icon = "gears"
    write_color_sets = False
    write_face_sets = False
    include_user_defined_attributes = False

    def get_instance_attr_defs(self):
        super(CreatePointCache, self).get_instance_attr_defs()
        # defs = self.get_instance_attr_defs()
        print(self.instance_attr_defs)
        defs = _get_animation_attr_defs(self)

        abc_defs = _get_animation_abc_attr_defs(self)

        if abc_defs:
            defs.extend(abc_defs)

        return defs

    def create(self, subset_name, instance_data, pre_create_data):
        instance = super(CreatePointCache, self).create(
            subset_name, instance_data, pre_create_data
        )
        instance_node = instance.get("instance_node")

        # For Arnold standin proxy
        proxy_set = cmds.sets(name=instance_node + "_proxy_SET", empty=True)
        cmds.sets(proxy_set, forceElement=instance_node)

    def apply_settings(self, project_settings):
        super(CreatePointCache, self).apply_settings(project_settings)
