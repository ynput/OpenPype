import nuke
import pyblish.api


class ExtractScriptSave(pyblish.api.InstancePlugin):
    """ Saves the script before extraction. """

    order = pyblish.api.ExtractorOrder - 0.49
    label = "Script Save"
    hosts = ["nuke"]
    families = ["saver"]

    def process(self, instance):

        nuke.scriptSave()
