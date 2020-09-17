import os
import sys
import copy
from pype.modules.rest_api import RestApi, route, abort, CallbackResult
from avalon.api import AvalonMongoDB
from pype.api import config, execute, Logger

log = Logger().get_logger("AdobeCommunicator")

CURRENT_DIR = os.path.dirname(__file__)
PUBLISH_SCRIPT_PATH = os.path.join(CURRENT_DIR, "publish.py")

PUBLISH_PATHS = []


class AdobeRestApi(RestApi):
    dbcon = AvalonMongoDB()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dbcon.install()

    @route("/available", "/adobe")
    def available(self):
        return CallbackResult()

    @route("/presets/<project_name>", "/adobe")
    def get_presets(self, request):
        project_name = request.url_data["project_name"]
        return CallbackResult(data=config.get_presets(project_name))

    @route("/publish", "/adobe", "POST")
    def publish(self, request):
        """Triggers publishing script in subprocess.

        The subprocess freeze process and during publishing is not possible to
        handle other requests and is possible that freeze main application.

        TODO: Freezing issue may be fixed with socket communication.

        Example url:
        http://localhost:8021/adobe/publish (POST)
        """
        try:
            publish_env = self._prepare_publish_environments(
                request.request_data
            )
        except Exception as exc:
            log.warning(
                "Failed to prepare environments for publishing.",
                exc_info=True
            )
            abort(400, str(exc))

        output_data_path = publish_env["AC_PUBLISH_OUTPATH"]

        log.info("Pyblish is running")
        try:
            # Trigger subprocess
            # QUESTION should we check returncode?
            returncode = execute(
                [sys.executable, PUBLISH_SCRIPT_PATH],
                env=publish_env
            )

            # Check if output file exists
            if returncode != 0 or not os.path.exists(output_data_path):
                abort(500, "Publishing failed")

            log.info("Pyblish have stopped")

            return CallbackResult(
                data={"return_data_path": output_data_path}
            )

        except Exception:
            log.warning("Publishing failed", exc_info=True)
            abort(500, "Publishing failed")

    def _prepare_publish_environments(self, data):
        """Prepares environments based on request data."""
        env = copy.deepcopy(os.environ)

        project_name = data["project"]
        asset_name = data["asset"]

        project_doc = self.dbcon[project_name].find_one({
            "type": "project"
        })
        av_asset = self.dbcon[project_name].find_one({
            "type": "asset",
            "name": asset_name
        })
        parents = av_asset["data"]["parents"]
        hierarchy = ""
        if parents:
            hierarchy = "/".join(parents)

        env["AVALON_PROJECT"] = project_name
        env["AVALON_ASSET"] = asset_name
        env["AVALON_TASK"] = data["task"]
        env["AVALON_WORKDIR"] = data["workdir"]
        env["AVALON_HIERARCHY"] = hierarchy
        env["AVALON_PROJECTCODE"] = project_doc["data"].get("code", "")
        env["AVALON_APP"] = data["AVALON_APP"]
        env["AVALON_APP_NAME"] = data["AVALON_APP_NAME"]

        env["PYBLISH_HOSTS"] = data["AVALON_APP"]

        env["PUBLISH_PATHS"] = os.pathsep.join(PUBLISH_PATHS)

        # Input and Output paths where source data and result data will be
        # stored
        env["AC_PUBLISH_INPATH"] = data["adobePublishJsonPathSend"]
        env["AC_PUBLISH_OUTPATH"] = data["adobePublishJsonPathGet"]

        return env
