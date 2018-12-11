import os
import pyblish.api
import clique


@pyblish.api.log
class RepairWriteFamiliesAction(pyblish.api.Action):
    label = "Fix Write's render attributes"
    on = "failed"
    icon = "wrench"

    def process(self, context, plugin):
        context[0][0]["render"].setValue(True)
        self.log.info("Rendering toggled ON")


class ValidateWriteFamilies(pyblish.api.InstancePlugin):
    """ Validates write families. """

    order = pyblish.api.ValidatorOrder
    label = "Check correct writes families"
    hosts = ["nuke"]
    families = ["write"]
    actions = [RepairWriteFamiliesAction]

    def process(self, instance):
        self.log.debug('instance.data["files"]: {}'.format(instance.data['files']))

        if not [f for f in instance.data["families"]
                if ".frames" in f]:
            return

        assert instance.data["files"], self.log.info(
            "`{}`: Swith `Render` on! \n"
            "No available frames to add to database. \n"
            "Use repair to render all frames".format(__name__))

        self.log.info("Checked correct writes families")
