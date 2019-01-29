import pyblish.api
import pype.api
import pype.maya.action


class ValidateRenderSingleCamera(pyblish.api.InstancePlugin):
    """Only one camera may be renderable in a layer.

    Currently the pipeline supports only a single camera per layer.
    This is because when multiple cameras are rendered the output files
    automatically get different names because the <Camera> render token
    is not in the output path. As such the output files conflict with how
    our pipeline expects the output.

    """

    order = pype.api.ValidateContentsOrder
    label = "Render Single Camera"
    hosts = ['maya']
    families = ["renderlayer",
                "vrayscene"]
    actions = [pype.maya.action.SelectInvalidAction]

    def process(self, instance):
        """Process all the cameras in the instance"""
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Invalid cameras for render.")

    @classmethod
    def get_invalid(cls, instance):

        cameras = instance.data.get("cameras", [])

        if len(cameras) > 1:
            cls.log.error("Multiple renderable cameras found for %s: %s " %
                          (instance.data["setMembers"], cameras))
            return [instance.data["setMembers"]] + cameras

        elif len(cameras) < 1:
            cls.log.error("No renderable cameras found for %s " %
                          instance.data["setMembers"])
            return [instance.data["setMembers"]]
