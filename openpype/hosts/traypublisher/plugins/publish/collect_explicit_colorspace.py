import pyblish.api
from openpype.pipeline import registered_host
from openpype.pipeline import publish
from openpype.lib import EnumDef
from openpype.pipeline import colorspace


class CollectColorspace(pyblish.api.InstancePlugin,
                        publish.OpenPypePyblishPluginMixin,
                        publish.ColormanagedPyblishPluginMixin):
    """Collect explicit user defined representation colorspaces"""

    label = "Choose representation colorspace"
    order = pyblish.api.CollectorOrder + 0.49
    hosts = ["traypublisher"]
    families = ["render", "plate", "reference", "image", "online"]

    colorspace_items = [
        (None, "Don't override")
    ]
    colorspace_attr_show = False

    def process(self, instance):
        values = self.get_attr_values_from_data(instance.data)
        colorspace = values.get("colorspace", None)
        if colorspace is None:
            return

        self.log.debug("Explicit colorspace set to: {}".format(colorspace))

        context = instance.context
        for repre in instance.data.get("representations", {}):
            self.set_representation_colorspace(
                representation=repre,
                context=context,
                colorspace=colorspace
            )

    @classmethod
    def apply_settings(cls, project_settings):
        host = registered_host()
        host_name = host.name
        project_name = host.get_current_project_name()
        config_data = colorspace.get_imageio_config(
            project_name, host_name,
            project_settings=project_settings
        )

        if config_data:
            filepath = config_data["path"]
            config_items = colorspace.get_ocio_config_colorspaces(filepath)
            cls.colorspace_items.extend((
                (name, name) for name in config_items.keys()
            ))
            cls.colorspace_attr_show = True

    @classmethod
    def get_attribute_defs(cls):
        return [
            EnumDef(
                "colorspace",
                cls.colorspace_items,
                default="Don't override",
                label="Override Colorspace",
                hidden=not cls.colorspace_attr_show
            )
        ]
