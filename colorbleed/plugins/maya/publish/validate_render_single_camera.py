import pyblish.api
import colorbleed.api
import colorbleed.maya.action


class ValidateRenderSingleCamera(pyblish.api.InstancePlugin):
    """Only one camera may be renderable in a layer.

    Currently the pipeline supports only a single camera per layer.
    This is because when multiple cameras are rendered the output files
    automatically get different names because the <Camera> render token
    is not in the output path. As such the output files conflict with how
    our pipeline expects the output.

    """

    order = colorbleed.api.ValidateContentsOrder
    label = "Render Single Camera"
    hosts = ['maya']
    families = ['colorbleed.renderlayer',
                "colorbleed.vrayscene"]

    def process(self, instance):
        """Process all the cameras in the instance"""

    @classmethod
    def get_invalid(cls, instance):
        cameras = instance.data.get("cameras", [])
        if len(cameras) != 1:
            cls.log.error("Multiple renderable cameras" "found: %s " %
                          instance.data["setMembers"])

            return [instance.data["setMembers"]]
