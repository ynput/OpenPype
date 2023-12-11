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
                "maxrender",
                "publish.hou"]
    optional = True

    # cache
    pools_per_url = {}

    def process(self, instance):
        if not self.is_active(instance.data):
            return

        if not instance.data.get("farm"):
            self.log.debug("Skipping local instance.")
            return

        deadline_url = self.get_deadline_url(instance)
        pools = self.get_pools(deadline_url)

        invalid_pools = {}
        primary_pool = instance.data.get("primaryPool")
        if primary_pool and primary_pool not in pools:
            invalid_pools["primary"] = primary_pool

        secondary_pool = instance.data.get("secondaryPool")
        if secondary_pool and secondary_pool not in pools:
            invalid_pools["secondary"] = secondary_pool

        if invalid_pools:
            message = "\n".join(
                "{} pool '{}' not available on Deadline".format(key.title(),
                                                                pool)
                for key, pool in invalid_pools.items()
            )
            raise PublishXmlValidationError(
                plugin=self,
                message=message,
                formatting_data={"pools_str": ", ".join(pools)}
            )

    def get_deadline_url(self, instance):
        # get default deadline webservice url from deadline module
        deadline_url = instance.context.data["defaultDeadline"]
        if instance.data.get("deadlineUrl"):
            # if custom one is set in instance, use that
            deadline_url = instance.data.get("deadlineUrl")
        return deadline_url

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
