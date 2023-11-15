from maya import cmds

from openpype.hosts.maya.api import lib, plugin
from openpype.hosts.maya.api.alembic import ALEMBIC_ARGS
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
        ]
    )

    return defs


def _get_animation_abc_attr_defs(cls):
    """Get definitions relating to Alembic.

    Most of the Alembic Arguments are booleans, those are stored in a
    `abc_boolean_args` attribute, the other ones are their own attriubte.

    An admin can define in settings the default arguments, which are then not
    modifiable by the person publishing, unless they are added to the Alembic
    Overrides setting, which is mapped to `abc_args_overrides`.

    We use a combination of the two above to only show a muiltiselection dropdown
    for booleans, and disabling the non-boolean arguments on the interface.

    There's also a new separator so it's clearer what belongs to common Animation
    publishes versus what is Almebic specific.
    """
    abc_defs = None
    abc_defs = [UISeparatorDef(), UILabelDef("Alembic Options")]

    # The Arguments that can be modified by the Publisher
    abc_args_overrides = getattr(cls, "abc_args_overrides", None)

    # All the Boolean Arguments that Alembic Export accepts
    abc_boolean_args = [
        arg
        for arg, arg_type in ALEMBIC_ARGS.items()
        if arg_type is bool
    ]

    # What we have set in the Settings as defaults.
    abc_settings_boolean_args = getattr(cls, "abc_boolean_args", [])

    # Default Flags set in Settings; minus the overrideable ones.
    abc_settings_boolean_arguments = [
        arg
        for arg in abc_settings_boolean_args
        if arg not in abc_args_overrides
    ]

    # We display them to the user, but disable it
    abc_defs.append(EnumDef(
        "abcDefaultExportBooleanArguments",
        abc_settings_boolean_arguments,
        default=abc_settings_boolean_arguments,
        multiselection=True,
        label="Settings Defined Arguments",
        disabled=False
    ))

    # Only display Boolan flags that the Admin defined as overrideable
    abc_boolean_overrides = [
        arg
        for arg in abc_boolean_args
        if arg in abc_args_overrides
    ]

    abc_defs.append(EnumDef(
        "abcExportBooleanArguments",
        abc_boolean_overrides if abc_boolean_overrides else [""],
        multiselection=True,
        label="Arguments Overrides",
        disabled=True if not abc_boolean_overrides else False
    ))

    abc_defs.append(
        TextDef(
            "attr",
            label="Custom Attributes",
            default=getattr(cls, "attr", None),
            placeholder="attr1; attr2; ...",
            disabled=True if "attr" not in abc_args_overrides else False,
        )
    )

    abc_defs.append(
        TextDef(
            "attrPrefix",
            label="Custom Attributes Prefix",
            default=getattr(cls, "attrPrefix", None),
            placeholder="prefix1; prefix2; ...",
            disabled=True if "attrPrefix" not in abc_args_overrides else False,
        )
    )

    abc_defs.append(
        EnumDef(
            "dataFormat",
            label="Data Format",
            default=getattr(cls, "dataFormat", None),
            items=["ogawa", "HDF"],
            disabled=True if "dataFormat" not in abc_args_overrides else False,
        )
    )

    abc_defs.append(
        NumberDef(
            "preRollStartFrame",
            label="Start frame for preroll",
            default=getattr(cls, "preRollStartFrame", None),
            tooltip=(
                "The frame to start scene evaluation at. This is used to set"
                " the starting frame for time dependent translations and can"
                " be used to evaluate run-up that isn't actually translated."
            ),
            disabled=True
            if "preRollStartFrame" not in abc_args_overrides
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

    def collect_instances(self):
        pass

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
