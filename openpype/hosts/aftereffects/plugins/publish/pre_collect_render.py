import json
import pyblish.api
from openpype.hosts.aftereffects.api import list_instances


class PreCollectRender(pyblish.api.ContextPlugin):
    """
    Checks if render instance is of old type, adds to families to both
    existing collectors work same way.

    Could be removed in the future when no one uses old publish.
    """

    label = "PreCollect Render"
    order = pyblish.api.CollectorOrder + 0.400
    hosts = ["aftereffects"]

    family_remapping = {
        "render": ("render.farm", "farm"),   # (family, label)
        "renderLocal": ("render.local", "local")
    }

    def process(self, context):
        if context.data.get("newPublishing"):
            self.log.debug("Not applicable for New Publisher, skip")
            return

        for inst in list_instances():
            if inst.get("creator_attributes"):
                raise ValueError("Instance created in New publisher, "
                                 "cannot be published in Pyblish.\n"
                                 "Please publish in New Publisher "
                                 "or recreate instances with legacy Creators")

            if inst["family"] not in self.family_remapping.keys():
                continue

            if not inst["members"]:
                raise ValueError("Couldn't find id, unable to publish. " +
                                 "Please recreate instance.")

            instance = context.create_instance(inst["subset"])
            inst["families"] = [self.family_remapping[inst["family"]][0]]
            instance.data.update(inst)

            self._debug_log(instance)

    def _debug_log(self, instance):
        def _default_json(value):
            return str(value)

        self.log.info(
            json.dumps(instance.data, indent=4, default=_default_json)
        )
