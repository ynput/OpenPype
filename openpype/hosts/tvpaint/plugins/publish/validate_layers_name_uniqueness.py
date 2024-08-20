import pyblish.api
from openpype.pipeline import (
    PublishXmlValidationError,
    OptionalPyblishPluginMixin,
)
from openpype.hosts.tvpaint.api.pipeline import (
    list_instances,
    write_instances,
)
from openpype.hosts.tvpaint.api.lib import execute_george


class ValidateLayersNameUniquenessTvPaintSelect(pyblish.api.Action):
    """Select the layers in fault.
    """

    label = "Select Layers"
    icon = "briefcase"
    on = "failed"

    def process(self, context, plugin):
        """Select the layers that haven't a unique name"""

        for layer in context.data['transientData'][ValidateLayersNameUniquenessTvPaint.__name__]:
            self.log.debug(execute_george(f'tv_layerselection {layer["layer_id"]} "true"'))
        return True


class ValidateLayersNameUniquenessTvPaint(
    OptionalPyblishPluginMixin,
    pyblish.api.ContextPlugin
):
    """Validate if all the layers have unique names"""

    label = "Validate Layers Name Uniqueness"
    order = pyblish.api.ValidatorOrder
    hosts = ["tvpaint"]
    actions = [ValidateLayersNameUniquenessTvPaintSelect]
    optional = True
    active = True

    def process(self, context):

        return_list = list()
        msg = ""
        for instance in context:
            layers = instance.data.get("layers")

            if not layers:
                continue

            layer_list = [layer["name"] for layer in layers]
            duplicates = set()

            for layer in layers:
                if layer["name"] in duplicates or layer_list.count(layer["name"]) == 1:
                    continue

                return_list.append(layer)
                duplicates.add(layer["name"])
                msg = "{}\nThe name {} is not unique.".format(msg, layer["name"])

        if return_list:
            if not context.data.get('transientData'):
                context.data['transientData'] = dict()

            context.data['transientData'][self.__class__.__name__] = return_list
            raise PublishXmlValidationError(self, msg)
