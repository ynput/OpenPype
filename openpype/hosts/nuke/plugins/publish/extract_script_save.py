import nuke
import pyblish.api


class ExtractScriptSave(pyblish.api.Extractor):
    """Save current Nuke workfile script"""
    label = 'Script Save'
    order = pyblish.api.Extractor.order - 0.1
    hosts = ['nuke']

    def process(self, instance):

        self.log.debug('Saving current script')
        nuke.scriptSave()
