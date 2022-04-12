import pyblish.api

from openpype.pipeline import (
    PublishXmlValidationError,
    OptionalPyblishPluginMixin
)
from openpype.modules.deadline.deadline_module import DeadlineModule


class ValidateDeadlinePools(OptionalPyblishPluginMixin,
                            pyblish.api.InstancePlugin):
    """Validate primaryPool and secondaryPool on instance.

    Values are on instance based on value insertion when Creating instance or
    by Settings in CollectDeadlinePools.
    """

    label = "Validate Deadline Pools"
    order = pyblish.api.ValidatorOrder
    families = ["rendering", "render.farm", "renderFarm", "renderlayer"]
    optional = True

    def process(self, instance):
        # get default deadline webservice url from deadline module
        deadline_url = instance.context.data["defaultDeadline"]
        self.log.info("deadline_url::{}".format(deadline_url))
        pools = DeadlineModule.get_deadline_pools(deadline_url, log=self.log)
        self.log.info("pools::{}".format(pools))

        formatting_data = {
            "pools_str": ",".join(pools)
        }

        primary_pool = instance.data.get("primaryPool")
        if primary_pool and primary_pool not in pools:
            msg = "Configured primary '{}' not present on Deadline".format(
                    instance.data["primaryPool"])
            formatting_data["invalid_value_str"] = msg
            raise PublishXmlValidationError(self, msg,
                                            formatting_data=formatting_data)

        secondary_pool = instance.data.get("secondaryPool")
        if secondary_pool and secondary_pool not in pools:
            msg = "Configured secondary '{}' not present on Deadline".format(
                    instance.data["secondaryPool"])
            formatting_data["invalid_value_str"] = msg
            raise PublishXmlValidationError(self, msg,
                                            formatting_data=formatting_data)
