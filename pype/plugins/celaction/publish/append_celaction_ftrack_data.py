import pyblish.api
from bait.ftrack.query_runner import QueryRunner


class AppendCelactionFtrackAudio(pyblish.api.ContextPlugin):

    label = "Ftrack Audio"
    order = pyblish.api.ExtractorOrder

    def process(self, context):

        if context.data.get("audio", ''):
            self.log.info('Audio data are already collected')
            self.log.info('Audio: {}'.format(context.data.get("audio", '')))
            return

        runner = QueryRunner(context.data['ftrackSession'])

        audio_file = runner.get_audio_file_for_shot(
            context.data['ftrackData']["Shot"]["id"])

        if audio_file:
            context.data["audio"] = {
                'filename': audio_file,
                'enabled': True
            }
        else:
            self.log.warning("Couldn't find any audio file on Ftrack.")


class AppendCelactionFtrackData(pyblish.api.InstancePlugin):
    """ Appending ftrack component and asset type data """

    families = ["img.*", "mov.*"]
    # offset to piggy back from default collectors
    order = pyblish.api.CollectorOrder + 0.1

    def process(self, instance):

        # ftrack data
        if not instance.context.has_data("ftrackData"):
            return

        instance.data["ftrackComponents"] = {}
        asset_type = instance.data["family"].split(".")[0]
        instance.data["ftrackAssetType"] = asset_type
