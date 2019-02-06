
import pyblish.api
import pype.api
import pype.nuke.actions


class RepairWriteFamiliesAction(pyblish.api.Action):
    label = "Fix Write's render attributes"
    on = "failed"
    icon = "wrench"

    def process(self, instance, plugin):
        self.log.info("instance {}".format(instance))
        instance["render"].setValue(True)
        self.log.info("Rendering toggled ON")


@pyblish.api.log
class ValidateWriteFamilies(pyblish.api.InstancePlugin):
    """ Validates write families. """

    order = pyblish.api.ValidatorOrder
    label = "Valitade writes families"
    hosts = ["nuke"]
    families = ["write"]
    actions = [pype.nuke.actions.SelectInvalidAction, pype.api.RepairAction]

    @staticmethod
    def get_invalid(self, instance):
        if not [f for f in instance.data["families"]
                if ".frames" in f]:
            return

        if not instance.data.get('files'):
            return (instance)

    def process(self, instance):
        self.log.debug('instance.data["files"]: {}'.format(instance.data['files']))

        invalid = self.get_invalid(self, instance)

        if invalid:
            raise ValueError(str("`{}`: Switch `Render` on! "
                                 "> {}".format(__name__, invalid)))

        # if any(".frames"  in f for f in instance.data["families"]):
        #     if not instance.data["files"]:
        #         raise ValueError("instance {} is set to publish frames\
        #             but no files were collected, render the frames first or\
        #             check 'render' checkbox onthe no to 'ON'".format(instance)))
        #
        #
        # self.log.info("Checked correct writes families")

    @classmethod
    def repair(cls, instance):
        cls.log.info("instance {}".format(instance))
        instance[0]["render"].setValue(True)
        cls.log.info("Rendering toggled ON")
