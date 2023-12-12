from maya import cmds

from openpype.hosts.maya.api import lib, plugin
from openpype.lib import (
    BoolDef,
    TextDef,
    NumberDef,
    EnumDef,
    UISeparatorDef,
    UILabelDef,
)
from openpype.pipeline import CreatedInstance


def _get_animation_attr_defs(cls):
    """Get Animation generic definitions.

    The line is blurry between what's "Animation" generic and "Alembic" is
    blurry, but the rule of thumb is that whatever "AlembicExport -h" accepts
    is "Alembic" and the other ones are "Animation".
    """
    defs = lib.collect_animation_defs()
    defs.extend(
        [
            BoolDef("farm", label="Submit to Farm"),
            NumberDef("priority", label="Farm job Priority", default=50),
            BoolDef("refresh", label="Refresh viewport during export"),
            BoolDef(
                "includeParentHierarchy", label="Include Parent Hierarchy"
            ),
            BoolDef("writeNormals", label="Write Normals"),
        ]
    )

    return defs


def _get_alembic_boolean_arguments(cls):
    """Get two lists with the Alembic flags.

    Alembic flags are treted as booleans, so here we get all the possible
    options, and work out a list with all the ones that can be toggled and the
    list of defaults (un-toggleable.)
    """

    # The Arguments that can be modified by the Publisher
    abc_args_overrides = set(getattr(cls, "abc_args_overrides", []))

    # What we have set in the Settings as defaults.
    abc_settings_boolean_args = set(getattr(cls, "abc_boolean_args", []))

    abc_defaults = {
        arg
        for arg in abc_settings_boolean_args
        if arg not in abc_args_overrides
    }

    abc_overrideable = {
        arg for arg in abc_settings_boolean_args if arg in abc_args_overrides
    }

    return abc_defaults, abc_overrideable


def _get_animation_abc_attr_defs(cls):
    """Get definitions relating to Alembic.

    An admin can define in settings the default arguments, which are then not
    modifiable by the person publishing, unless they are added to the Alembic
    Overrides setting, which is mapped to `abc_args_overrides`.

    Most of the Alembic Arguments are flags, treated as booleans, and there are
    two possible lists: the defaults (from settings) and the the toggleable by
    the user, these two define an EnumDef respectively.

    We use a combination of the two above to only show a muiltiselection
    dropdown for booleans, and disabling the non-boolean arguments on the
    interface.

    There's also a new separator so it's clearer what belongs to common
    Animation publishes versus what is Almebic specific, the line is blurry,
    but the rule of thumb is that whatever "AlembicExport -h" accepts is
    "Alembic" and the other ones are "Animation".
    """
    abc_defs = None
    abc_defs = [
        UISeparatorDef("sep_alembic_options"),
        UILabelDef("Alembic Options"),
    ]

    # The Arguments that can be modified by the Publisher
    abc_args_overrides = getattr(cls, "abc_args_overrides", None)

    (
        abc_boolean_defaults,
        abc_boolean_overrides,
    ) = _get_alembic_boolean_arguments(cls)

    abc_defs.append(
        EnumDef(
            "abcDefaultExportBooleanArguments",
            abc_boolean_defaults,
            default=abc_boolean_defaults,
            multiselection=True,
            label="Settings Defined Arguments",
            disabled=True,
            hidden=True
        )
    )

    # Only display Boolan flags that the Admin defined as overrideable
    abc_defs.append(
        EnumDef(
            "abcExportBooleanArguments",
            abc_boolean_overrides if abc_boolean_overrides else [""],
            multiselection=True,
            label="Arguments Overrides",
            disabled=True if not abc_boolean_overrides else False,
        )
    )

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


def _ensure_defaults(cls, instance_data):
    """Ensure we get default values when an attribute is not overrideable.

    In instances where an attribute used to be modifiable, and then was locked
    again, we want to make sure that we pass the default (what's on the
    settings) instead of any value that might have been stored in the scene
    when the attribute was modifiable.
    """
    abc_args_overrides = getattr(cls, "abc_args_overrides", [])
    creator_attr = instance_data["creator_attributes"]
    attr_default = getattr(cls, "attr", "")

    if "attr" not in abc_args_overrides:
        creator_attr["attr"] = attr_default

    if "attrPrefix" not in abc_args_overrides:
        creator_attr["attrPrefix"] = getattr(cls, "attrPrefix", "")

    if "dataFormat" not in abc_args_overrides:
        creator_attr["dataFormat"] = getattr(cls, "dataFormat", "")

    if "preRollStartFrame" not in abc_args_overrides:
        creator_attr["preRollStartFrame"] = getattr(
            cls, "preRollStartFrame", ""
        )

    (
        abc_boolean_defaults,
        abc_boolean_overrides,
    ) = _get_alembic_boolean_arguments(cls)

    creator_attr["abcDefaultExportBooleanArguments"] = abc_boolean_defaults

    creator_attr["abcExportBooleanArguments"] = [
        arg for arg in creator_attr["abcExportBooleanArguments"]
        if arg not in abc_boolean_overrides
    ]

    return instance_data


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
        cached_subsets = self.collection_shared_data["maya_cached_subsets"]
        for node in cached_subsets.get(self.identifier, []):
            node_data = self.read_instance_node(node)
            _ensure_defaults(self, node_data)

            created_instance = CreatedInstance.from_existing(node_data, self)
            self._add_instance_to_context(created_instance)

    def get_instance_attr_defs(self):
        super(CreateAnimation, self).get_instance_attr_defs()
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

    def collect_instances(self):
        cached_subsets = self.collection_shared_data["maya_cached_subsets"]
        for node in cached_subsets.get(self.identifier, []):
            node_data = self.read_instance_node(node)
            _ensure_defaults(self, node_data)

            created_instance = CreatedInstance.from_existing(node_data, self)
            self._add_instance_to_context(created_instance)

    def get_instance_attr_defs(self):
        super(CreatePointCache, self).get_instance_attr_defs()
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
