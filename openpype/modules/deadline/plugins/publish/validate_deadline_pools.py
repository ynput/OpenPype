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
    families = ["rendering",
                "render.farm",
                "render.frames_farm",
                "renderFarm",
                "renderlayer",
                "maxrender"]
    optional = True

    # cache
    pools_per_url = {}

    def process(self, instance):
        if not self.is_active(instance.data):
            return

        if not instance.data.get("farm"):
            self.log.debug("Skipping local instance.")
            return

        deadline_url = instance.context.data["defaultDeadline"]
        pools = self.get_pools(deadline_url)

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

    def get_pools(self, deadline_url):
        if deadline_url not in self.pools_per_url:
            self.log.debug(
                "Querying available pools for Deadline url: {}".format(
                    deadline_url)
            )
            pools = DeadlineModule.get_deadline_pools(deadline_url,
                                                      log=self.log)
            self.log.info("Available pools: {}".format(pools))
            self.pools_per_url[deadline_url] = pools

        return self.pools_per_url[deadline_url]
