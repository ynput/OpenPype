import os
import json
import getpass

from avalon.tvpaint import HEADLESS
from avalon.vendor import requests
import pyblish.api


class SubmitTVPaintDeadline(pyblish.api.ContextPlugin):
    """Submit instance to Deadline.

    Renders are submitted to a Deadline Web Service as
    supplied via the environment variable DEADLINE_REST_URL
    """

    label = "Submit to Deadline"
    order = pyblish.api.IntegratorOrder + 0.1
    hosts = ["tvpaint"]
    families = ["deadline"]
    optional = True

    # presets
    deadline_priority = 50
    deadline_pool = ""
    deadline_pool_secondary = ""
    deadline_group = ""
    deadline_department = ""
    deadline_limit_groups = []

    def process(self, context):
        # Skip extract if in headless mode.
        if HEADLESS:
            return

        DEADLINE_REST_URL = os.environ.get("DEADLINE_REST_URL")
        assert DEADLINE_REST_URL, "Requires DEADLINE_REST_URL"

        self.deadline_url = "{}/api/jobs".format(DEADLINE_REST_URL)
        self._deadline_user = context.data.get(
            "deadlineUser", getpass.getuser()
        )

        published_paths = {}
        for item in context:
            if "workfile" in item.data.get("families", []):
                msg = "Workfile (scene) must be published along"
                assert item.data["publish"] is True, msg

                template_data = item.data.get("anatomyData")
                for rep in item.data.get("representations"):
                    template_data["representation"] = rep["name"]
                    template_data["ext"] = rep["name"]
                    template_data["comment"] = None
                    anatomy_filled = context.data["anatomy"].format(
                        template_data
                    )
                    template_filled = anatomy_filled["publish"]["path"]

                    published_paths[rep["name"]] = os.path.normpath(
                        template_filled
                    )

                break

        self.payload_submit(
            context, published_paths["tvpp"], published_paths["json"]
        )

    def payload_submit(self, context, workfile, jsonfile):
        script_name = os.path.basename(workfile)

        app_pattern = "tvpaint_{version[major]}-{version[minor]}"
        if "pro" in context.data["hostInfo"]["type"].lower():
            app_pattern += "pro"

        app_pattern += "_attached"

        payload = {
            "JobInfo": {
                # Asset dependency to wait for at least the scene file to sync.
                "AssetDependency0": workfile,
                "AssetDependency1": jsonfile,

                # Job name, as seen in Monitor
                "Name": script_name,

                # Arbitrary username, for visualisation in Monitor
                "UserName": self._deadline_user,

                "Priority": self.deadline_priority,
                "ChunkSize": "1",
                "Department": self.deadline_department,

                "Pool": self.deadline_pool,
                "SecondaryPool": self.deadline_pool_secondary,
                "Group": self.deadline_group,

                "Plugin": "OpenPype",
                "Frames": "0",

                # limiting groups
                "LimitGroups": ",".join(self.deadline_limit_groups)

            },
            "PluginInfo": {
                "Arguments": "launch --app {}".format(
                    app_pattern.format(**context.data["hostInfo"])
                )
            },

            # Mandatory for Deadline, may be empty
            "AuxFiles": []
        }

        # Include critical environment variables with submission
        keys = [
            "AVALON_PROJECT",
            "AVALON_ASSET",
            "AVALON_TASK",
            "FTRACK_API_USER",
            "FTRACK_API_KEY",
            "FTRACK_SERVER"
        ]

        environment = {
            key: os.environ[key] for key in keys if key in os.environ
        }

        environment["PYPE_TVPAINT_PROJECT_FILE"] = workfile
        environment["PYPE_TVPAINT_JSON"] = jsonfile
        environment["AVALON_TVPAINT_HEADLESS"] = 1

        payload["JobInfo"].update(
            {
                "EnvironmentKeyValue%d" % index: "{key}={value}".format(
                    key=key,
                    value=environment[key]
                ) for index, key in enumerate(environment)
            }
        )

        plugin = payload["JobInfo"]["Plugin"]
        self.log.info("Using render plugin : {}".format(plugin))

        self.log.info("Submitting..")
        self.log.info(payload)
        self.log.info(json.dumps(payload, indent=4, sort_keys=True))

        response = requests.post(self.deadline_url, json=payload, timeout=10)

        if not response.ok:
            raise Exception(response.text)

        return response
