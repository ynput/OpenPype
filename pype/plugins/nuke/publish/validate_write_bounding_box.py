import nuke

import pyblish.api


class RepairNukeBoundingBoxAction(pyblish.api.Action):

    label = "Repair"
    icon = "wrench"
    on = "failed"

    def process(self, context, plugin):

        # Get the errored instances
        failed = []
        for result in context.data["results"]:
            if (result["error"] is not None and result["instance"] is not None
               and result["instance"] not in failed):
                failed.append(result["instance"])

        # Apply pyblish.logic to get the instances for the plug-in
        instances = pyblish.api.instances_by_plugin(failed, plugin)

        for instance in instances:
            crop = instance[0].dependencies()[0]
            if crop.Class() != "Crop":
                crop = nuke.nodes.Crop(inputs=[instance[0].input(0)])

                xpos = instance[0].xpos()
                ypos = instance[0].ypos() - 26

                dependent_ypos = instance[0].dependencies()[0].ypos()
                if (instance[0].ypos() - dependent_ypos) <= 51:
                    xpos += 110

                crop.setXYpos(xpos, ypos)

                instance[0].setInput(0, crop)

            crop["box"].setValue(
                (
                    0.0,
                    0.0,
                    instance[0].input(0).width(),
                    instance[0].input(0).height()
                )
            )


class ValidateNukeWriteBoundingBox(pyblish.api.InstancePlugin):
    """Validates write bounding box.

    Ffmpeg does not support bounding boxes outside of the image
    resolution a crop is needed. This needs to validate all frames, as each
    rendered exr can break the ffmpeg transcode.
    """

    order = pyblish.api.ValidatorOrder
    optional = True
    families = ["render", "render.local", "render.farm"]
    label = "Write Bounding Box"
    hosts = ["nuke"]
    actions = [RepairNukeBoundingBoxAction]

    def process(self, instance):

        # Skip bounding box check if a crop node exists.
        if instance[0].dependencies()[0].Class() == "Crop":
            return

        msg = "Bounding box is outside the format."
        assert self.check_bounding_box(instance), msg

    def check_bounding_box(self, instance):
        node = instance[0]

        first_frame = instance.data["frameStart"]
        last_frame = instance.data["frameEnd"]

        format_width = node.format().width()
        format_height = node.format().height()

        # The trick is that we need to execute() some node every time we go to
        # a next frame, to update the context.
        # So we create a CurveTool that we can execute() on every frame.
        temporary_node = nuke.nodes.CurveTool()
        bbox_check = True
        for frame in range(first_frame, last_frame + 1):
            # Workaround to update the tree
            nuke.execute(temporary_node, frame, frame)

            x = node.bbox().x()
            y = node.bbox().y()
            w = node.bbox().w()
            h = node.bbox().h()

            if x < 0 or (x + w) > format_width:
                bbox_check = False
                break

            if y < 0 or (y + h) > format_height:
                bbox_check = False
                break

        nuke.delete(temporary_node)
        return bbox_check
