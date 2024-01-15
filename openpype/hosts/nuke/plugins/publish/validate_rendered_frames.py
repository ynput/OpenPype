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

    def repair_knob(self, context, instances, state):
        create_context = context.data["create_context"]
        for instance in instances:
            # Reset the render knob
            instance_id = instance.data.get("instance_id")
            created_instance = create_context.get_instance_by_id(
                instance_id
            )
            created_instance.creator_attributes["render_target"] = state
            self.log.info("Rendering toggled to `{}`".format(state))

        create_context.save_changes()


class RepairCollectionActionToLocal(RepairActionBase):
    label = "Repair - rerender with \"Local\""

    def process(self, context, plugin):
        instances = self.get_instance(context, plugin)
        self.repair_knob(context, instances, "local")


class RepairCollectionActionToFarm(RepairActionBase):
    label = "Repair - rerender with \"On farm\""

    def process(self, context, plugin):
        instances = self.get_instance(context, plugin)
        self.repair_knob(context, instances, "farm")


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
            self.log.debug("collections: {}".format(str(collections)))
            self.log.debug("remainder: {}".format(str(remainder)))

            collection = collections[0]

            f_start_h = instance.data["frameStartHandle"]
            f_end_h = instance.data["frameEndHandle"]

            frame_length = int(f_end_h - f_start_h + 1)

            if frame_length != 1:
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
            coll_start = min(collection.indexes)
            coll_end = max(collection.indexes)

            self.log.debug("frame_length: {}".format(frame_length))
            self.log.debug("collected_frames_len: {}".format(
                collected_frames_len))
            self.log.debug("f_start_h-f_end_h: {}-{}".format(
                f_start_h, f_end_h))
            self.log.debug(
                "coll_start-coll_end: {}-{}".format(coll_start, coll_end))

            self.log.debug(
                "len(collection.indexes): {}".format(collected_frames_len)
            )

            if ("slate" in instance.data["families"]) \
                    and (frame_length != collected_frames_len):
                collected_frames_len -= 1
                f_start_h += 1

            if (
                collected_frames_len != frame_length
                and coll_start <= f_start_h
                and coll_end >= f_end_h
            ):
                raise PublishXmlValidationError(
                    self, (
                        "{} missing frames. Use repair to "
                        "render all frames"
                    ).format(__name__), formatting_data=f_data
                )

            instance.data["collection"] = collection

            return
