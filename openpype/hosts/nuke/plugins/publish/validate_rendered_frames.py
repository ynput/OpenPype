import os
import pyblish.api
from openpype.api import ValidationException
import clique


@pyblish.api.log
class RepairActionBase(pyblish.api.Action):
    on = "failed"
    icon = "wrench"

    @staticmethod
    def get_instance(context, plugin):
        # Get the errored instances
        failed = []
        for result in context.data["results"]:
            if (result["error"] is not None and result["instance"] is not None
               and result["instance"] not in failed):
                failed.append(result["instance"])

        # Apply pyblish.logic to get the instances for the plug-in
        return pyblish.api.instances_by_plugin(failed, plugin)

    def repair_knob(self, instances, state):
        for instance in instances:
            files_remove = [os.path.join(instance.data["outputDir"], f)
                            for r in instance.data.get("representations", [])
                            for f in r.get("files", [])
                            ]
            self.log.info("Files to be removed: {}".format(files_remove))
            for f in files_remove:
                os.remove(f)
                self.log.debug("removing file: {}".format(f))
            instance[0]["render"].setValue(state)
            self.log.info("Rendering toggled to `{}`".format(state))


class RepairCollectionActionToLocal(RepairActionBase):
    label = "Repair > rerender with `Local` machine"

    def process(self, context, plugin):
        instances = self.get_instance(context, plugin)
        self.repair_knob(instances, "Local")


class RepairCollectionActionToFarm(RepairActionBase):
    label = "Repair > rerender `On farm` with remote machines"

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

        for repre in instance.data["representations"]:

            if not repre.get("files"):
                msg = ("no frames were collected, "
                       "you need to render them.\n"
                       "Check properties of write node (group) and"
                       "select 'Local' option in 'Publish' dropdown.")
                self.log.error(msg)
                raise ValidationException(msg)

            if isinstance(repre["files"], str):
                return

            collections, remainder = clique.assemble(repre["files"])
            self.log.info("collections: {}".format(str(collections)))
            self.log.info("remainder: {}".format(str(remainder)))

            collection = collections[0]

            fstartH = instance.data["frameStartHandle"]
            fendH = instance.data["frameEndHandle"]

            frame_length = int(fendH - fstartH + 1)

            if frame_length != 1:
                if len(collections) != 1:
                    msg = "There are multiple collections in the folder"
                    self.log.error(msg)
                    raise ValidationException(msg)

                if not collection.is_contiguous():
                    msg = "Some frames appear to be missing"
                    self.log.error(msg)
                    raise ValidationException(msg)

            collected_frames_len = int(len(collection.indexes))
            coll_start = min(collection.indexes)
            coll_end = max(collection.indexes)

            self.log.info("frame_length: {}".format(frame_length))
            self.log.info("collected_frames_len: {}".format(
                collected_frames_len))
            self.log.info("fstartH-fendH: {}-{}".format(fstartH, fendH))
            self.log.info(
                "coll_start-coll_end: {}-{}".format(coll_start, coll_end))

            self.log.info(
                "len(collection.indexes): {}".format(collected_frames_len)
            )

            if ("slate" in instance.data["families"]) \
                    and (frame_length != collected_frames_len):
                collected_frames_len -= 1
                fstartH += 1

            assert ((collected_frames_len >= frame_length)
                    and (coll_start <= fstartH)
                    and (coll_end >= fendH)), (
                "{} missing frames. Use repair to render all frames"
            ).format(__name__)

            instance.data["collection"] = collection

            return
