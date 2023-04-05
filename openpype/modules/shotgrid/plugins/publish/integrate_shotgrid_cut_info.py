import os
import pyblish.api


from openpype.pipeline import publish
from openpype.hosts.hiero import api as phiero
from openpype.pipeline.publish import ValidateContentsOrder
def openpype_publish_tag(track_item):
    """Get tag that was used to publish track item"""
    for item_tag in track_item.tags():
        # print(instance_tag, 'instance_tag')
        tag_metadata = dict(item_tag.metadata())
        tag_family = tag_metadata.get("tag.family", "")
        if tag_family == "reference":
            return dict(item_tag.metadata())

    return {}


def get_tag_handles(track_item):
    tag = openpype_publish_tag(track_item)
    print(tag, 'tag')
    try:
        handle_start = int(tag.get("tag.handleStart", "0"))
        handle_end = int(tag.get("tag.handleEnd", "0"))
    except ValueError:
        raise Exception("Handle field should only contain numbers")

    return handle_start, handle_end




                    # class ValidateShotgridUser(pyblish.api.ContextPlugin):
                    #     """
                    #     Check if user is valid and have access to the project.
                    #     """
                    #
                    #     label = "Validate Shotgrid User"
                    #     order = ValidateContentsOrder
class IntegrateShotgridCutInfo(pyblish.api.InstancePlugin):
# class IntegrateShotgridCutInfo(publish.Extractor):

    order = pyblish.api.IntegratorOrder + 0.4999
    # order = ValidateContentsOrder
    # order = pyblish.api.ExtractorOrder - .5
    label = "Integrate Shotgrid Cut Info"
    hosts = ["hiero"]
    families = ["reference"]

    optional = True

    def process(self, instance):
        context = instance.context
        self.sg = context.data.get("shotgridSession")
        shotgrid_version = instance.data.get("shotgridVersion")

        # print(self.tag_data, 'self.tag_data')
        # If cut already added to shotgrid shot then don't update cut?
        if not shotgrid_version:
            self.log.warning("No Shotgrid version collect. Cut Info could not be integrated into shot")
            return
        # self.log.info("Cut In and Cut Out already in Shotgrid")


        # first_frame = instance.data["frameStart"]
        # end_frame = instance.data["frameEnd"] + handle_end

        # need the cut item to calculate the cut info keys

        track_item = instance.data["item"]
        openpype_tag = phiero.get_track_item_tags(track_item)

        # handleStart and handleEnd are overriden to reflect media range and not absolute handles
        # Solution is to take the handle values directly from the tag instead of instance data
        handle_start, handle_end = get_tag_handles(track_item)
        cut_in = instance.data["frameStart"]
        cut_out = instance.data["frameEnd"]
        head_in = cut_in - handle_start
        tail_out = cut_out + handle_end

        shot_data = {
            "sg_cut_in": cut_in,
            "sg_cut_out": cut_out,
            "sg_head_in": head_in,
            "sg_tail_out": tail_out
        }
        self.log.info("Setting cut info on shot '{0}' - {1}".format(
            shotgrid_version["entity"]["name"],
            shot_data
            )
        )

        result = self.sg.update("Shot",
                       shotgrid_version["entity"]["id"],
                       shot_data,
                       )
        if not result:
            self.log.warning('Failed to update shot cut information. Most likely SG connection was severed')
