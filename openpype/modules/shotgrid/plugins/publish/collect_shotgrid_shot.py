import pyblish.api


class CollectShotgridShot(pyblish.api.InstancePlugin):
    """Collect proper shotgrid entity according to the current asset name"""

    order = pyblish.api.CollectorOrder + 0.4999
    label = "Collect Shotgrid Shot"
    hosts = ["hiero"]
    families = ["plate", "take", "reference"]

    def process(self, instance):
        context = instance.context

        anatomy_data = instance.data.get("anatomyData", {})
        sg = context.data.get("shotgridSession")

        self.log.info("Looking for shot associated with clip name")
        sg_shot = _get_shotgrid_shot(sg, anatomy_data)

        if sg_shot:
            context.data["shotgridEntity"] = sg_shot
            self.log.info(
                "Overriding entity with corresponding shot for clip: {}".format(sg_shot)
            )
        else:
            raise Exception("No Shotgrid shot found under clip name: {}".format(anatomy_data["asset"]))


def _get_shotgrid_shot(sg, anatomy):
    shot_name = anatomy["asset"]

    filters = [
        ["project.Project.sg_code", "is", anatomy["project"]["name"]],
        ["code", "is", shot_name],
    ]
    sg_shot = sg.find_one("Shot", filters, ["code"])
    # OP project name/code isn't always sg_code. This approach gives a sure fire way to match to a SG project
    if not sg_shot:
        filters = [
            ["project.Project.name", "is", anatomy["project"]["name"]],
            ["code", "is", shot_name],
        ]
        sg_shot = sg.find_one("Shot", filters, ["code"])
    if not sg_shot:
        filters = [
            ["project.Project.sg_code", "is", anatomy["project"]["code"]],
            ["code", "is", shot_name],
        ]
        sg_shot = sg.find_one("Shot", filters, ["code"])

    return sg_shot
