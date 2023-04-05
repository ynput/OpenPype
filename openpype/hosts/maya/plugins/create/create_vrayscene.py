# -*- coding: utf-8 -*-
"""Create instance of vrayscene."""

from maya import cmds
import maya.app.renderSetup.model.renderSetup as renderSetup

from openpype.hosts.maya.api import (
    lib,
    lib_rendersettings,
    plugin
)
from openpype.pipeline import (
    CreatorError,
    legacy_io,
    Creator,
    CreatedInstance
)
from openpype.lib import (
    BoolDef,
    NumberDef
)


def ensure_namespace(namespace):
    """Make sure the namespace exists.

    Args:
        namespace (str): The preferred namespace name.

    Returns:
        str: The generated or existing namespace

    """
    exists = cmds.namespace(exists=namespace)
    if exists:
        return namespace
    else:
        return cmds.namespace(add=namespace)


class CreateVRayScene(Creator, plugin.MayaCreatorBase):
    """Create Vray Scene."""

    identifier = "io.openpype.creators.maya.vrayscene"

    family = "vrayscene"
    label = "VRay Scene"
    icon = "cubes"

    render_settings = {}
    singleton_node_name = "vraysceneMain"

    def _get_singleton_node(self, return_all=False):
        nodes = lib.lsattr("pre_creator_identifier", self.identifier)
        if nodes:
            return nodes if return_all else nodes[0]

    @classmethod
    def apply_settings(cls, project_settings, system_settings):
        cls.render_settings = project_settings["maya"]["RenderSettings"]

    def create(self, subset_name, instance_data, pre_create_data):
        # A Renderlayer is never explicitly created using the create method.
        # Instead, renderlayers from the scene are collected. Thus "create"
        # would only ever be called to say, 'hey, please refresh collect'

        # Only allow a single render instance to exist
        if self._get_singleton_node():
            raise CreatorError("A Render instance already exists - only "
                               "one can be configured.")

        # Apply default project render settings on create
        if self.render_settings.get("apply_render_settings"):
            lib_rendersettings.RenderSettings().set_default_renderer_settings()

        # if no render layers are present, create default one with
        # asterisk selector
        rs = renderSetup.instance()
        if not rs.getRenderLayers():
            render_layer = rs.createRenderLayer('Main')
            collection = render_layer.createCollection("defaultCollection")
            collection.getSelector().setPattern('*')

        with lib.undo_chunk():
            node = cmds.sets(empty=True, name=self.singleton_node_name)
            lib.imprint(node, data={
                "pre_creator_identifier": self.identifier
            })

            # By RenderLayerCreator.create we make it so that the renderlayer
            # instances directly appear even though it just collects scene
            # renderlayers. This doesn't actually 'create' any scene contents.
            self.collect_instances()

    def collect_instances(self):

        # We only collect if the global render instance exists
        if not self._get_singleton_node():
            return

        rs = renderSetup.instance()
        layers = rs.getRenderLayers()
        for layer in layers:
            layer_instance_node = self.find_layer_instance_node(layer)
            if layer_instance_node:
                data = self.read_instance_node(layer_instance_node)
                instance = CreatedInstance.from_existing(data, creator=self)
            else:
                # No existing scene instance node for this layer. Note that
                # this instance will not have the `instance_node` data yet
                # until it's been saved/persisted at least once.
                # TODO: Correctly define the subset name using templates
                subset_name = "{}{}".format(self.family, layer.name())
                instance_data = {
                    "asset": legacy_io.Session["AVALON_ASSET"],
                    "task": legacy_io.Session["AVALON_TASK"],
                    "variant": layer.name(),
                }
                instance = CreatedInstance(
                    family=self.family,
                    subset_name=subset_name,
                    data=instance_data,
                    creator=self
                )

            instance.transient_data["layer"] = layer
            self._add_instance_to_context(instance)

    def find_layer_instance_node(self, layer):
        connected_sets = cmds.listConnections(
            "{}.message".format(layer.name()),
            source=False,
            destination=True,
            type="objectSet"
        ) or []

        for node in connected_sets:
            if not cmds.attributeQuery("creator_identifier",
                                       node=node,
                                       exists=True):
                continue

            creator_identifier = cmds.getAttr(node + ".creator_identifier")
            if creator_identifier == self.identifier:
                self.log.info(f"Found node: {node}")
                return node

    def _create_layer_instance_node(self, layer):

        # We only collect if a CreateRender instance exists
        create_render_set = self._get_singleton_node()
        if not create_render_set:
            raise CreatorError("Creating a renderlayer instance node is not "
                               "allowed if no 'CreateVRayScene' instance "
                               "exists")

        namespace = "_{}".format(self.singleton_node_name)
        namespace = ensure_namespace(namespace)

        name = "{}:{}".format(namespace, layer.name())
        render_set = cmds.sets(name=name, empty=True)

        # Keep an active link with the renderlayer so we can retrieve it
        # later by a physical maya connection instead of relying on the layer
        # name
        cmds.addAttr(render_set, longName="renderlayer", at="message")
        cmds.connectAttr("{}.message".format(layer.name()),
                         "{}.renderlayer".format(render_set), force=True)

        # Add the set to the 'CreateRender' set.
        cmds.sets(render_set, forceElement=create_render_set)

        return render_set

    def update_instances(self, update_list):
        # We only generate the persisting layer data into the scene once
        # we save with the UI on e.g. validate or publish
        for instance, _changes in update_list:
            instance_node = instance.data.get("instance_node")

            # Ensure a node exists to persist the data to
            if not instance_node:
                layer = instance.transient_data["layer"]
                instance_node = self._create_layer_instance_node(layer)
                instance.data["instance_node"] = instance_node
            else:
                # TODO: Keep name in sync with the actual renderlayer?
                self.log.warning("No instance node found for to be updated "
                                 "instance: {}".format(instance))
                continue

            self.imprint_instance_node(instance_node,
                                       data=instance.data_to_store())

    def imprint_instance_node(self, node, data):
        # Do not ever try to update the `renderlayer` since it'll try
        # to remove the attribute and recreate it but fail to keep it a
        # message attribute link. We only ever imprint that on the initial
        # node creation.
        # TODO: Improve how this is handled
        data.pop("renderlayer", None)
        data.get("creator_attributes", {}).pop("renderlayer", None)

        return super(CreateVRayScene, self).imprint_instance_node(node,
                                                                  data=data)

    def remove_instances(self, instances):
        """Remove specified instances from the scene.

        This is only removing `id` parameter so instance is no longer
        instance, because it might contain valuable data for artist.

        """
        # Instead of removing the single instance or renderlayers we instead
        # remove the CreateRender node this creator relies on to decide whether
        # it should collect anything at all.
        nodes = self._get_singleton_node(return_all=True)
        if nodes:
            cmds.delete(nodes)

        # Remove ALL the instances even if only one gets deleted
        for instance in list(self.create_context.instances):
            if instance.get("creator_identifier") == self.identifier:
                self._remove_instance_from_context(instance)

                # Remove the stored settings per renderlayer too
                node = instance.data.get("instance_node")
                if node and cmds.objExists(node):
                    cmds.delete(node)

    def get_instance_attr_defs(self):
        """Create instance settings."""

        return [
            BoolDef("vraySceneMultipleFiles",
                    label="V-Ray Scene Multiple Files",
                    default=False),
            BoolDef("exportOnFarm",
                    label="Export on farm",
                    default=False)
        ]
