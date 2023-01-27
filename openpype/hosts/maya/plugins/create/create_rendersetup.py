from openpype.hosts.maya.api import plugin
from openpype.pipeline import CreatorError


class CreateRenderSetup(plugin.MayaCreator):
    """Create rendersetup template json data"""

    identifier = "io.openpype.creators.maya.rendersetup"
    label = "Render Setup Preset"
    family = "rendersetup"
    icon = "tablet"

    def get_pre_create_attr_defs(self):
        # Do not show the "use_selection" setting from parent class
        return []

    def create(self, subset_name, instance_data, pre_create_data):

        existing_instance = None
        for instance in self.create_context.instances:
            if instance.family == self.family:
                existing_instance = instance
                break

        if existing_instance:
            raise CreatorError("A RenderSetup instance already exists - only "
                               "one can be configured.")

        super(CreateRenderSetup, self).create(subset_name,
                                              instance_data,
                                              pre_create_data)
