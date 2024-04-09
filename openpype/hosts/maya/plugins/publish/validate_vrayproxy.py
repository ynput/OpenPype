import pyblish.api

from openpype.pipeline import KnownPublishError
from openpype.pipeline.publish import OptionalPyblishPluginMixin


class ValidateVrayProxy(pyblish.api.InstancePlugin,
                        OptionalPyblishPluginMixin):

    order = pyblish.api.ValidatorOrder
    label = "VRay Proxy Settings"
    hosts = ["maya"]
    families = ["vrayproxy"]
    optional = False

    def process(self, instance):
        data = instance.data
        if not self.is_active(data):
            return
        if not data["setMembers"]:
            raise KnownPublishError(
                "'%s' is empty! This is a bug" % instance.name
            )

        if data["animation"]:
            if data["frameEnd"] < data["frameStart"]:
                raise KnownPublishError(
                    "End frame is smaller than start frame"
                )

        if not data["vrmesh"] and not data["alembic"]:
            raise KnownPublishError(
                "Both vrmesh and alembic are off. Needs at least one to"
                " publish."
            )
