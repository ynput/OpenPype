from maya import cmds

from pprint import pprint

from openpype.hosts.maya.api import (
    lib,
    plugin
)
from openpype.lib import (
    BoolDef,
    TextDef,
    NumberDef,
    EnumDef,
    UISeparatorDef,
    UILabelDef
)

def _get_animation_attr_defs(cls):
    """Get Animation generic ddefinitions.
    """
    defs = lib.collect_animation_defs()
    defs.extend([
        BoolDef("farm", label="Submit to Farm"),
        NumberDef("priority", label="Farm job Priority", default=50),
        BoolDef("refresh", label="Refresh viewport during export"),
        BoolDef("includeParentHierarchy", label="Include Parent Hierarchy"),
        BoolDef("writeNormals", label="Write Normals"),
        BoolDef("writeCreases", label="Write Creases")
    ])

    return defs

def _get_animation_abc_attr_defs(cls):
    """ Get definitions relating to Alembic.
    """
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
        "pythonPostJobCallback"
    ]

    abc_defs = [
        UISeparatorDef(),
        UILabelDef("Alembic Options")
    ]

    print("Processing editable Alembic attributes...")
    alembic_editable_attributes = getattr(cls, "abc_editable_flags", None)

    if not alembic_editable_attributes:
        return None

    print(alembic_editable_attributes)

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
        attrib
        for attrib in abc_boolean_defs
        if attrib in alembic_editable_attributes
    ]

    if enabled_boolean_attributes:
        abc_defs.extend([EnumDef(
            "abcExportFlags",
            enabled_boolean_attributes,
            default=abc_boolean_defaults,
            multiselection=True,
            label="Alembic Export Flags"
        )])


    abc_defs.append(TextDef(
            "attr",
            label="Alembic Custom Attributes",
            placeholder="attr1, attr2",
             disabled=True if "attr" not in alembic_editable_attributes else False
    ))

    abc_defs.append(TextDef(
            "attrPrefix",
            label="Alembic Custom Attributes Prefix",
            placeholder="prefix1, prefix2",
            disabled=True if "attrPrefix" not in alembic_editable_attributes else False
    ))

    abc_defs.append(EnumDef(
            "dataFormat",
            label="Alembic Data Format",
            items=["ogawa", "HDF"],
            disabled=True if "dataFormat" not in alembic_editable_attributes else False
    ))

    abc_defs.append(NumberDef(
            "preRollStartFrame",
            label="Start frame for preroll (Alembic)",
            tooltip=(
                "The frame to start scene evaluation at. This is used to set"
                " the starting frame for time dependent translations and can"
                " be used to evaluate run-up that isn't actually translated."
            ),
            disabled=True if "preRollStartFrame" not in alembic_editable_attributes else False
    ))

    #['__abstractmethods__', '__class__', '__delattr__', '__dict__', '__dir__', '__doc__', '__eq__', '__format__', '__ge__', '__getattribute__', '__gt__', '__hash__', '__init__', '__init_subclass__', '__le__', '__lt__', '__module__', '__ne__', '__new__', '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__', '__str__', '__subclasshook__', '__weakref__', '_abc_impl', '_add_instance_to_context', '_cached_group_label', '_default_collect_instances', '_default_remove_instances', '_default_update_instances', '_log', '_remove_instance_from_context', 'apply_settings', 'cache_subsets', 'collect_instances', 'collection_shared_data', 'create', 'create_context', 'enabled', 'family', 'get_dynamic_data', 'get_group_label', 'get_icon', 'get_instance_attr_defs', 'get_next_versions_for_instances', 'get_publish_families', 'get_subset_name', 'group_label', 'headless', 'host', 'host_name', 'icon', 'identifier', 'imprint_instance_node', 'include_parent_hierarchy', 'include_user_defined_attributes', 'instance_attr_defs', 'label', 'log', 'name', 'order', 'project_anatomy', 'project_name', 'project_settings', 'read_instance_node', 'remove_instances', 'set_instance_thumbnail_path', 'update_instances', 'write_color_sets', 'write_face_sets']
    #for
    # Collect editable state and default values.
    # resulting_defs = []
    # for definition in defs:
    #     # Include by default any attributes which has no editable state
    #     # from settings.
    #     if not hasattr(cls, definition.key + "_editable"):
    #         print("{} was not found.".format(definition.key + "_editable"))
    #         resulting_defs.append(definition)
    #         continue

    #     # Remove non-editable defs.
    #     if not getattr(cls, definition.key + "_editable"):
    #         continue

    #     # Set default values from settings.
    #     definition.default = getattr(cls, definition.key)

    #     resulting_defs.append(definition)

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
        defs = _get_animation_attr_defs(self)

        abc_defs = _get_animation_abc_attr_defs(self)

        if abc_defs:
            defs.extend(abc_defs)

        return defs

    def apply_settings(self, project_settings):
        super(CreateAnimation, self).apply_settings(project_settings)


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
