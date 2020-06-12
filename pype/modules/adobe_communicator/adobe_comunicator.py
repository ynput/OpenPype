import os
import pype
from pype.api import Logger
from .lib import AdobeRestApi, PUBLISH_PATHS

log = Logger().get_logger("AdobeCommunicator")


class AdobeCommunicator:
    rest_api_obj = None

    def __init__(self):
        self.rest_api_obj = None

        # Add "adobecommunicator" publish paths
        PUBLISH_PATHS.append(os.path.sep.join(
            [pype.PLUGINS_DIR, "adobecommunicator", "publish"]
        ))

    def tray_start(self):
        return

    def process_modules(self, modules):
        # Module requires RestApiServer
        rest_api_module = modules.get("RestApiServer")
        if not rest_api_module:
            log.warning(
                "AdobeCommunicator won't work without RestApiServer."
            )
            return

        # Register statics url
        pype_module_root = os.environ["PYPE_MODULE_ROOT"].replace("\\", "/")
        static_path = "{}/pype/hosts/premiere/ppro".format(pype_module_root)
        rest_api_module.register_statics("/ppro", static_path)

        # Register rest api object for communication
        self.rest_api_obj = AdobeRestApi()

        # Add Ftrack publish path if registered Ftrack mdule
        if "FtrackModule" in modules:
            PUBLISH_PATHS.append(os.path.sep.join(
                [pype.PLUGINS_DIR, "ftrack", "publish"]
            ))

        log.debug((
            f"Adobe Communicator Registered PUBLISH_PATHS"
            f"> `{PUBLISH_PATHS}`"
        ))
