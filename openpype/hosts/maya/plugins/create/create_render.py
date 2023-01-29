# -*- coding: utf-8 -*-
"""Create ``Render`` instance in Maya."""
from maya import cmds
from maya.app.renderSetup.model import renderSetup

from openpype.hosts.maya.api import (
    lib,
    lib_rendersettings,
    plugin
)
from openpype.lib import (
    BoolDef,
    NumberDef
)

from openpype.pipeline import legacy_io
from openpype.pipeline.create import (
    CreatorError,
    HiddenCreator,
    CreatedInstance
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


class CreateRender(plugin.MayaCreator):
    """Create *render* instance.

    Render instances are not actually published, they hold options for
    collecting of render data. It render instance is present, it will trigger
    collection of render layers, AOVs, cameras for either direct submission
    to render farm or export as various standalone formats (like V-Rays
    ``vrscenes`` or Arnolds ``ass`` files) and then submitting them to render
    farm.

    Instance has following attributes::
        extendFrames (bool): Use already existing frames from previous version
            to extend current render.
        overrideExistingFrame (bool): Overwrite already existing frames.
        vrscene (bool): Submit as ``vrscene`` file for standalone V-Ray
            renderer.
        ass (bool): Submit as ``ass`` file for standalone Arnold renderer.
        tileRendering (bool): Instance is set to tile rendering mode. We
            won't submit actual render, but we'll make publish job to wait
            for Tile Assembly job done and then publish.

    See Also:
        https://pype.club/docs/artist_hosts_maya#creating-basic-render-setup

    """

    identifier = "io.openpype.creators.maya.render"
    label = "Render"
    family = "rendering"
    icon = "eye"

    render_settings = {}

    @classmethod
    def apply_settings(cls, project_settings, system_settings):
        cls.render_settings = project_settings["maya"]["RenderSettings"]

    def create(self, subset_name, instance_data, pre_create_data):

        # Only allow a single render instance to exist
        nodes = lib.lsattr("creator_identifier", self.identifier)
        if nodes:
            raise CreatorError("A Render instance already exists - only "
                               "one can be configured.")

        # Apply default project render settings on create
        if self.render_settings.get("apply_render_settings"):
            lib_rendersettings.RenderSettings().set_default_renderer_settings()

        with lib.undo_chunk():
            instance = super(CreateRender, self).create(subset_name,
                                                        instance_data,
                                                        pre_create_data)
            # We never want to SHOW the instance in the UI since the parent
            # class already adds it after creation let's directly remove it.
            self._remove_instance_from_context(instance)

            # TODO: Now make it so that RenderLayerCreator 'collect'
            #       automatically gets triggered to directly see renderlayers

        return instance

    def collect_instances(self):
        # We never show this instance in the publish UI
        return

    def get_pre_create_attr_defs(self):
        # Do not show the "use_selection" setting from parent class
        return []


class RenderlayerCreator(HiddenCreator, plugin.MayaCreatorBase):
    """Create and manges renderlayer subset per renderLayer in workfile.

    This does no do ANYTHING until a CreateRender subset exists in the
    scene, created by the CreateRender creator.

    """

    identifier = "io.openpype.creators.maya.renderlayer"
    family = "renderlayer"
    label = "Renderlayer"

    render_settings = {}

    @classmethod
    def apply_settings(cls, project_settings, system_settings):
        cls.render_settings = project_settings["maya"]["RenderSettings"]

    def create(self, instance_data, source_data):
        # Make sure an instance exists per renderlayer in the scene

        # # create namespace with instance
        # namespace_name = "_{}".format(subset_name)
        # namespace = ensure_namespace(namespace_name)
        #
        # # Pre-process any existing layers
        # # TODO: Document why we're processing the layers explicitly?
        #
        # self.log.info("Processing existing layers")
        # sets = []
        # for layer in layers:
        #     set_name = "{}:{}".format(namespace, layer.name())
        #     self.log.info("  - creating set for {}".format(set_name))
        #     render_set = cmds.sets(name=set_name, empty=True)
        #     sets.append(render_set)
        #
        # cmds.sets(sets, forceElement=instance_node)
        #
        # # if no render layers are present, create default one with
        # # asterisk selector
        # if not layers:
        #     render_layer = rs.createRenderLayer('Main')
        #     collection = render_layer.createCollection("defaultCollection")
        #     collection.getSelector().setPattern('*')
        return

    def collect_instances(self):

        # We only collect if a CreateRender instance exists
        create_render_exists = any(
            self.iter_subset_nodes(identifier=CreateRender.identifier)
        )
        if not create_render_exists:
            return

        rs = renderSetup.instance()
        layers = rs.getRenderLayers()
        for layer in layers:
            subset_name = "render" + layer.name()

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
            self._add_instance_to_context(instance)

    def update_instances(self, update_list):
        # We only generate the persisting layer data into the scene once
        # we save with the UI on e.g. validate or publish
        # TODO: Implement this behavior for data persistence

        # for instance, changes in update_list.items():
        #     instance_node = instance.data.get("instance_node")
        #     if not instance_node:
        #         layer = instance.data.get("layer")
        #         instance_node = self._create_layer_instance_node(layer)
        #
        #     self.imprint_instance_node(instance_node,
        #                                data=instance.data_to_store())
        pass

    def remove_instances(self, instances):
        """Remove specified instance from the scene.

        This is only removing `id` parameter so instance is no longer
        instance, because it might contain valuable data for artist.

        """
        for instance in instances:
            node = instance.data.get("instance_node")
            if node:
                cmds.delete(node)

            self._remove_instance_from_context(instance)

    def get_instance_attr_defs(self):
        """Create instance settings."""

        return [
            BoolDef("review",
                    label="Review",
                    tooltip="Mark as reviewable",
                    default=True),
            BoolDef("extendFrames",
                    label="Extend Frames",
                    tooltip="Extends the frames on top of the previous "
                            "publish.\nIf the previous was 1001-1050 and you "
                            "would now submit 1020-1070 only the new frames "
                            "1051-1070 would be rendered and published "
                            "together with the previously rendered frames.\n"
                            "If 'overrideExistingFrame' is enabled it *will* "
                            "render any existing frames.",
                    default=False),
            BoolDef("overrideExistingFrame",
                    label="Override Existing Frame",
                    tooltip="Mark as reviewable",
                    default=True),

            # TODO: Should these move to submit_maya_deadline plugin?
            # Tile rendering
            BoolDef("tileRendering",
                    label="Enable tiled rendering",
                    default=False),
            NumberDef("tilesX",
                      label="Tiles X",
                      default=2,
                      minimum=1,
                      decimals=0),
            NumberDef("tilesY",
                      label="Tiles Y",
                      default=2,
                      minimum=1,
                      decimals=0),

            # Additional settings
            BoolDef("convertToScanline",
                    label="Convert to Scanline",
                    tooltip="Convert the output images to scanline images",
                    default=False),
            BoolDef("useReferencedAovs",
                    label="Use Referenced AOVs",
                    tooltip="Consider the AOVs from referenced scenes as well",
                    default=False),

            BoolDef("renderSetupIncludeLights",
                    label="Render Setup Include Lights",
                    default=self.render_settings.get("enable_all_lights",
                                                     False))
        ]
