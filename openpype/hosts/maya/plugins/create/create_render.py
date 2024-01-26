# -*- coding: utf-8 -*-
"""Create ``Render`` instance in Maya."""

from openpype.settings import (
    get_system_settings,
    get_project_settings
)
from openpype.hosts.maya.api import (
    lib_rendersettings,
    plugin
)
from openpype.pipeline import CreatorError
from openpype.pipeline.context_tools import (
    get_current_task_name,
    get_current_project_name
)
from openpype.lib import (
    BoolDef,
    NumberDef,
    EnumDef,
    filter_profiles
)
from openpype.pipeline.context_tools import _get_modules_manager


class CreateRenderlayer(plugin.RenderlayerCreator):
    """Create and manages renderlayer subset per renderLayer in workfile.

    This generates a single node in the scene which tells the Creator to if
    it exists collect Maya rendersetup renderlayers as individual instances.
    As such, triggering create doesn't actually create the instance node per
    layer but only the node which tells the Creator it may now collect
    the renderlayers.

    """

    identifier = "io.openpype.creators.maya.renderlayer"
    family = "renderlayer"
    label = "Render"
    icon = "eye"

    layer_instance_prefix = "render"
    singleton_node_name = "renderingMain"

    render_settings = {}

    @classmethod
    def apply_settings(cls, project_settings):
        cls.render_settings = project_settings["maya"]["RenderSettings"]

    def create(self, subset_name, instance_data, pre_create_data):
        # Only allow a single render instance to exist
        if self._get_singleton_node():
            raise CreatorError("A Render instance already exists - only "
                               "one can be configured.")

        # Apply default project render settings on create
        if self.render_settings.get("apply_render_settings"):
            lib_rendersettings.RenderSettings().set_default_renderer_settings()

        super(CreateRenderlayer, self).create(subset_name,
                                              instance_data,
                                              pre_create_data)

    def get_instance_attr_defs(self):
        """Create instance settings."""
        default_limit_groups = []
        default_machine_limit = 0
        modules_system_settings = get_system_settings()["modules"]
        deadline_enabled = modules_system_settings["deadline"]["enabled"]
        deadline_url = modules_system_settings["deadline"]["deadline_urls"].get("default")

        limit_groups = self._get_limit_groups(
            deadline_enabled, deadline_url
        )

        profile = self.get_profile()
        if profile:
            default_machine_limit = profile.get("limit_machines", 0)
            default_limit_groups = profile.get("limit_plugins", [])

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
                    tooltip="Override existing rendered frames "
                            "(if they exist).",
                    default=True),
            NumberDef("machineLimit",
                      label="Machine Limit",
                      default=default_machine_limit,
                      minimum=0,
                      decimals=0),
            EnumDef("limits",
                    label="Limit Groups",
                    items=limit_groups,
                    default=default_limit_groups,
                    multiselection=True),

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

    def get_profile(self):
        task = get_current_task_name()
        project_name = get_current_project_name()
        project_settings = get_project_settings(project_name)
        settings = project_settings["deadline"]["DefaultJobSettings"]
        profile = None

        filtering_criteria = {
            "hosts": "maya",
            "task_type": task
        }
        if settings.get("profiles"):
            profile = filter_profiles(
                settings["profiles"],
                filtering_criteria,
                logger=self.log
            )

        return profile

    def _get_default_machine_limit(self, deadline_enabled):
        default_machine_limit = 0

        if deadline_enabled:
            default_machine_limit = \
                self.project_settings.get("deadline").get("publish").get(
                    "MayaSubmitDeadline").get("jobInfo").get("machineLimit", 0)

        return default_machine_limit

    def _get_limit_groups(self, deadline_enabled, deadline_url):
        manager = _get_modules_manager()
        deadline_module = manager.modules_by_name["deadline"]

        limit_groups = []
        if deadline_enabled:
            requested_arguments = {"NamesOnly": True}
            limit_groups = deadline_module.get_deadline_data(
                deadline_url,
                "limitgroups",
                log=self.log,
                **requested_arguments
            )

        return limit_groups
