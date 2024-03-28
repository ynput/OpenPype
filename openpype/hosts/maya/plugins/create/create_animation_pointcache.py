from maya import cmds

from openpype.hosts.maya.api import lib, plugin

from openpype.lib import (
    BoolDef,
    NumberDef,
)
from openpype.pipeline import CreatedInstance


def _get_animation_attr_defs(cls):
    """Get Animation generic definitions."""
    defs = lib.collect_animation_defs()
    defs.extend(
        [
            BoolDef("farm", label="Submit to Farm"),
            NumberDef("priority", label="Farm job Priority", default=50),
            BoolDef("refresh", label="Refresh viewport during export"),
            BoolDef(
                "includeParentHierarchy", label="Include Parent Hierarchy"
            ),
            BoolDef(
                "includeUserDefinedAttributes",
                label="Include User Defined Attributes"
            ),
        ]
    )

    return defs


def extract_alembic_attributes(node_data, class_name):
    """This is a legacy transfer of creator attributes to publish attributes
    for ExtractAlembic/ExtractAnimation plugin.
    """
    publish_attributes = node_data["publish_attributes"]

    if class_name in publish_attributes:
        return node_data

    extract_alembic_flags = [
        "writeColorSets",
        "writeFaceSets",
        "writeNormals",
        "renderableOnly",
        "visibleOnly",
        "worldSpace",
        "renderableOnly"
    ]
    extract_alembic_attributes = [
        "attr",
        "attrPrefix",
        "visibleOnly"
    ]
    attributes = extract_alembic_flags + extract_alembic_attributes
    plugin_attributes = {"flags": []}
    for attr in attributes:
        if attr not in node_data["creator_attributes"].keys():
            continue
        value = node_data["creator_attributes"].pop(attr)

        if value and attr in extract_alembic_flags:
            plugin_attributes["flags"].append(attr)

        if attr in extract_alembic_attributes:
            plugin_attributes[attr] = value

    publish_attributes[class_name] = plugin_attributes

    return node_data


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
        try:
            cached_subsets = self.collection_shared_data["maya_cached_subsets"]
        except KeyError:
            self.cache_subsets(self.collection_shared_data)
            cached_subsets = self.collection_shared_data["maya_cached_subsets"]

        for node in cached_subsets.get(self.identifier, []):
            node_data = self.read_instance_node(node)

            node_data = extract_alembic_attributes(
                node_data, "ExtractAnimation"
            )

            created_instance = CreatedInstance.from_existing(node_data, self)
            self._add_instance_to_context(created_instance)

    def get_instance_attr_defs(self):
        super(CreateAnimation, self).get_instance_attr_defs()
        defs = _get_animation_attr_defs(self)
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
        try:
            cached_subsets = self.collection_shared_data["maya_cached_subsets"]
        except KeyError:
            self.cache_subsets(self.collection_shared_data)
            cached_subsets = self.collection_shared_data["maya_cached_subsets"]

        for node in cached_subsets.get(self.identifier, []):
            node_data = self.read_instance_node(node)

            node_data = extract_alembic_attributes(node_data, "ExtractAlembic")

            created_instance = CreatedInstance.from_existing(node_data, self)
            self._add_instance_to_context(created_instance)

    def get_instance_attr_defs(self):
        super(CreatePointCache, self).get_instance_attr_defs()
        defs = _get_animation_attr_defs(self)
        return defs

    def create(self, subset_name, instance_data, pre_create_data):
        instance = super(CreatePointCache, self).create(
            subset_name, instance_data, pre_create_data
        )
        instance_node = instance.get("instance_node")

        # For Arnold standin proxy
        proxy_set = cmds.sets(name=instance_node + "_proxy_SET", empty=True)
        cmds.sets(proxy_set, forceElement=instance_node)
