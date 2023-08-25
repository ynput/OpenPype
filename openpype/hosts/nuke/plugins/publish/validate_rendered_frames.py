import os
import pyblish.api
import clique
from openpype.pipeline import PublishXmlValidationError
from openpype.pipeline.publish import get_errored_instances_from_context


class RepairActionBase(pyblish.api.Action):
    on = "failed"
    icon = "wrench"

    @staticmethod
    def get_instance(context, plugin):
        # Get the errored instances
        return get_errored_instances_from_context(context, plugin=plugin)

    def repair_knob(self, instances, state):
        for instance in instances:
            node = instance.data["transientData"]["node"]
            files_remove = [os.path.join(instance.data["outputDir"], f)
                            for r in instance.data.get("representations", [])
                            for f in r.get("files", [])
                            ]
            self.log.info("Files to be removed: {}".format(files_remove))
            for f in files_remove:
                os.remove(f)
                self.log.debug("removing file: {}".format(f))
            node["render"].setValue(state)
            self.log.info("Rendering toggled to `{}`".format(state))


class RepairCollectionActionToLocal(RepairActionBase):
    label = "Repair - rerender with \"Local\""

    def process(self, context, plugin):
        instances = self.get_instance(context, plugin)
        self.repair_knob(instances, "Local")


class RepairCollectionActionToFarm(RepairActionBase):
    label = "Repair - rerender with \"On farm\""

    def process(self, context, plugin):
        instances = self.get_instance(context, plugin)
        self.repair_knob(instances, "On farm")


class ValidateRenderedFrames(pyblish.api.InstancePlugin):
    """ Validates file output. """

    order = pyblish.api.ValidatorOrder + 0.1
    families = ["render", "prerender", "still"]

    label = "Validate rendered frame"
    hosts = ["nuke", "nukestudio"]
    actions = [RepairCollectionActionToLocal, RepairCollectionActionToFarm]

    def process(self, instance):
        node = instance.data["transientData"]["node"]

        f_data = {
            "node_name": node.name()
        }

        for repre in instance.data["representations"]:

            if not repre.get("files"):
                msg = ("no frames were collected, "
                       "you need to render them.\n"
                       "Check properties of write node (group) and"
                       "select 'Local' option in 'Publish' dropdown.")
                self.log.error(msg)
                raise PublishXmlValidationError(
                    self, msg, formatting_data=f_data)

            if isinstance(repre["files"], str):
                return

            collections, remainder = clique.assemble(repre["files"])
            self.log.info("collections: {}".format(str(collections)))
            self.log.info("remainder: {}".format(str(remainder)))

            collection = collections[0]

            frame_start_handle = instance.data["frameStartHandle"]
            frame_end_handle = instance.data["frameEndHandle"]

            asset_frames_len = int(frame_end_handle - frame_start_handle + 1)

            if asset_frames_len != 1:
                if len(collections) != 1:
                    msg = "There are multiple collections in the folder"
                    self.log.error(msg)
                    raise PublishXmlValidationError(
                        self, msg, formatting_data=f_data)

                if not collection.is_contiguous():
                    msg = "Some frames appear to be missing"
                    self.log.error(msg)
                    raise PublishXmlValidationError(
                        self, msg, formatting_data=f_data)

            collected_frames_len = len(collection.indexes)
            collection_frame_start = min(collection.indexes)
            collection_frame_end = max(collection.indexes)

            if (
                    "slate" in instance.data["families"]
                    and asset_frames_len != collected_frames_len
            ):
                frame_start_handle -= 1
                asset_frames_len += 1

            if (
                collected_frames_len != asset_frames_len
                or collection_frame_start != frame_start_handle
                or collection_frame_end != frame_end_handle
            ):
                raise PublishXmlValidationError(
                    self, (
                        "{} missing frames. Use repair to "
                        "render all frames"
                    ).format(__name__), formatting_data=f_data
                )

            instance.data["collection"] = collection

            return
