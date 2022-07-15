from pprint import pformat
import pyblish.api


class CollectClipInstance(pyblish.api.InstancePlugin):
    """Collect clip instances and resolve its parent"""

    label = "Collect Clip Instances"
    order = pyblish.api.CollectorOrder

    hosts = ["traypublisher"]
    families = ["plate", "review", "audio"]

    def process(self, instance):
        creator_identifier = instance.data["creator_identifier"]
        if "editorial" not in creator_identifier:
            return

        instance.data["families"].append("clip")

        parent_instance_id = instance.data["parent_instance_id"]
        edit_shared_data = instance.context.data["editorialSharedData"]
        instance.data.update(
            edit_shared_data[parent_instance_id]
        )

        if "editorialSourcePath" in instance.context.data.keys():
            instance.data["editorialSourcePath"] = (
                instance.context.data["editorialSourcePath"])
            instance.data["families"].append("trimming")

        self.log.debug(pformat(instance.data))