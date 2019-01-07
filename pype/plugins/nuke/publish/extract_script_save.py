import nuke
import pyblish.api


class ExtractScriptSave(pyblish.api.Extractor):
    """
    """
    label = 'Script Save'
    order = pyblish.api.Extractor.order - 0.1
    hosts = ['nuke']

    def process(self, instance):

        self.log.info('saving script')
        nuke.scriptSave()
