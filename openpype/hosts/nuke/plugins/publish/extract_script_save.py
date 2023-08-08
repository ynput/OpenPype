import nuke
import pyblish.api


class ExtractScriptSave(pyblish.api.Extractor):
    """
    """
    label = 'Script Save'
    order = pyblish.api.Extractor.order - 0.1
    hosts = ['nuke']

    def process(self, instance):
        # NOTE hornet update on use existing frames on farm
        render_target = instance.data.get("render_target")
        review = instance.data.get("review")
        if review == False or render_target in ['farm','local'] :
            self.log.info('saving script')
            nuke.scriptSave()
