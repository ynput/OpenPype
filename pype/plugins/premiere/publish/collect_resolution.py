import pyblish.api


class CollectResolution(pyblish.api.InstancePlugin):
    """
    Collecting frameranges needed for ftrack integration

    Args:
        context (obj): pyblish context session

    """

    label = "Collect Clip Resolution"
    order = pyblish.api.CollectorOrder
    families = ['clip']

    def process(self, instance):
        # getting metadata from jsonData key
        metadata = instance.data.get('jsonData').get('metadata')

        # getting important metadata time calculation
        pixel_aspect = float(metadata['ppro.format.pixelaspect'])
        res_width = metadata['ppro.format.width']
        res_height = metadata['ppro.format.height']

        instance.data['pixelAspect'] = pixel_aspect
        instance.data['resolutionWidth'] = res_width
        instance.data['resolutionHeight'] = res_height

        self.log.info(f"Resolution was set to: `{res_width}x{res_height}`,"
                      f" and pixel aspect ration to: `{pixel_aspect}`")
