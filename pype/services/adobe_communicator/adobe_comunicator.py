import os
import pype
from pypeapp import config, Logger
from . import PUBLISH_PATHS

log = Logger().get_logger("AdobeCommunicator")


class AdobeCommunicator:
    rest_api_obj = None

    def __init__(self):
        try:
            self.presets = config.get_presets(
            )["services"]["adobe_commuticator"]
        except Exception:
            self.presets = {"statics": {}, "rest_api": False}
            log.debug((
                "There are not set presets for AdobeCommunicator."
                " Using defaults \"{}\""
            ).format(str(self.presets)))

        # solve publish paths
        PUBLISH_PATHS.clear()
        PUBLISH_PATHS.append(os.path.sep.join(
            [pype.PLUGINS_DIR, "adobecommunicator", "publish"]
        ))

    def tray_start(self):
        return

    def process_modules(self, modules):
        rest_api_module = modules.get("RestApiServer")
        if rest_api_module:
            self.rest_api_registration(rest_api_module)

            # adding ftrack publish path
            if "FtrackModule" in modules:
                PUBLISH_PATHS.append(os.path.sep.join(
                    [pype.PLUGINS_DIR, "ftrack", "publish"]
                ))
            log.info((f"Adobe Communicator Registered PUBLISH_PATHS"
                      f"> `{PUBLISH_PATHS}`"))

    def rest_api_registration(self, module):
        for prefix, static_path in self.presets["statics"].items():
            static_path = static_path.format(
                **dict(os.environ)).replace("\\", "/")
            module.register_statics(prefix, static_path)
            log.info((f"Adobe Communicator Registering static"
                      f"> `{prefix}` at `{static_path}`"))

        if all((self.presets["rest_api"],
                not bool(self.rest_api_obj))):
            from .lib import AdobeRestApi
            self.rest_api_obj = AdobeRestApi()
