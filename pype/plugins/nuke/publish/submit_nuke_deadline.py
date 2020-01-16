import os
import json
import getpass

from avalon import api
from avalon.vendor import requests
import re

import pyblish.api


class NukeSubmitDeadline(pyblish.api.InstancePlugin):
    """Submit write to Deadline

    Renders are submitted to a Deadline Web Service as
    supplied via the environment variable DEADLINE_REST_URL

    """

    label = "Submit to Deadline"
    order = pyblish.api.IntegratorOrder + 0.1
    hosts = ["nuke", "nukestudio"]
    families = ["render.farm"]
    optional = True

    def process(self, instance):

        node = instance[0]
        context = instance.context

        DEADLINE_REST_URL = os.environ.get("DEADLINE_REST_URL",
                                           "http://localhost:8082")
        assert DEADLINE_REST_URL, "Requires DEADLINE_REST_URL"

        self.deadline_url = "{}/api/jobs".format(DEADLINE_REST_URL)
        self._comment = context.data.get("comment", "")
        self._ver = re.search(r"\d+\.\d+", context.data.get("hostVersion"))
        self._deadline_user = context.data.get(
            "deadlineUser", getpass.getuser())
        self._frame_start = int(instance.data["frameStart"])
        self._frame_end = int(instance.data["frameEnd"])

        # get output path
        render_path = instance.data['path']
        script_path = context.data["currentFile"]

        # exception for slate workflow
        if "slate" in instance.data["families"]:
            self._frame_start -= 1

        response = self.payload_submit(instance,
                                       script_path,
                                       render_path,
                                       node.name()
                                       )
        # Store output dir for unified publisher (filesequence)
        instance.data["deadlineSubmissionJob"] = response.json()
        instance.data["publishJobState"] = "Active"

        if instance.data.get("bakeScriptPath"):
            render_path = instance.data.get("bakeRenderPath")
            script_path = instance.data.get("bakeScriptPath")
            exe_node_name = instance.data.get("bakeWriteNodeName")

            # exception for slate workflow
            if "slate" in instance.data["families"]:
                self._frame_start += 1

            resp = self.payload_submit(instance,
                                       script_path,
                                       render_path,
                                       exe_node_name,
                                       response.json()
                                       )
            # Store output dir for unified publisher (filesequence)
            instance.data["deadlineSubmissionJob"] = resp.json()
            instance.data["publishJobState"] = "Suspended"

    def payload_submit(self,
                       instance,
                       script_path,
                       render_path,
                       exe_node_name,
                       responce_data=None
                       ):
        render_dir = os.path.normpath(os.path.dirname(render_path))
        script_name = os.path.basename(script_path)
        jobname = "%s - %s" % (script_name, instance.name)

        if not responce_data:
            responce_data = {}

        try:
            # Ensure render folder exists
            os.makedirs(render_dir)
        except OSError:
            pass

        payload = {
            "JobInfo": {
                # Top-level group name
                "BatchName": script_name,

                # Job name, as seen in Monitor
                "Name": jobname,

                # Arbitrary username, for visualisation in Monitor
                "UserName": self._deadline_user,

                "Priority": instance.data["deadlinePriority"],

                "Pool": "2d",
                "SecondaryPool": "2d",

                "Plugin": "Nuke",
                "Frames": "{start}-{end}".format(
                    start=self._frame_start,
                    end=self._frame_end
                ),
                "Comment": self._comment,

            },
            "PluginInfo": {
                # Input
                "SceneFile": script_path,

                # Output directory and filename
                "OutputFilePath": render_dir.replace("\\", "/"),
                # "OutputFilePrefix": render_variables["filename_prefix"],

                # Mandatory for Deadline
                "Version": self._ver.group(),

                # Resolve relative references
                "ProjectPath": script_path,
                "AWSAssetFile0": render_path,
                # Only the specific write node is rendered.
                "WriteNode": exe_node_name
            },

            # Mandatory for Deadline, may be empty
            "AuxFiles": []
        }

        if responce_data.get("_id"):
            payload["JobInfo"].update({
                "JobType": "Normal",
                "BatchName": responce_data["Props"]["Batch"],
                "JobDependency0": responce_data["_id"],
                "ChunkSize": 99999999
                })

        # Include critical environment variables with submission
        keys = [
            "PYTHONPATH",
            "PATH",
            "AVALON_SCHEMA",
            "FTRACK_API_KEY",
            "FTRACK_API_USER",
            "FTRACK_SERVER",
            "PYBLISHPLUGINPATH",
            "NUKE_PATH",
            "TOOL_ENV"
        ]
        environment = dict({key: os.environ[key] for key in keys
                            if key in os.environ}, **api.Session)
        # self.log.debug("enviro: {}".format(pprint(environment)))
        for path in os.environ:
            if path.lower().startswith('pype_'):
                environment[path] = os.environ[path]

        environment["PATH"] = os.environ["PATH"]
        # self.log.debug("enviro: {}".format(environment['PYPE_SCRIPTS']))
        clean_environment = {}
        for key in environment:
            clean_path = ""
            self.log.debug("key: {}".format(key))
            to_process = environment[key]
            if key == "PYPE_STUDIO_CORE_MOUNT":
                clean_path = environment[key]
            elif "://" in environment[key]:
                clean_path = environment[key]
            elif os.pathsep not in to_process:
                try:
                    path = environment[key]
                    path.decode('UTF-8', 'strict')
                    clean_path = os.path.normpath(path)
                except UnicodeDecodeError:
                    print('path contains non UTF characters')
            else:
                for path in environment[key].split(os.pathsep):
                    try:
                        path.decode('UTF-8', 'strict')
                        clean_path += os.path.normpath(path) + os.pathsep
                    except UnicodeDecodeError:
                        print('path contains non UTF characters')

            if key == "PYTHONPATH":
                clean_path = clean_path.replace('python2', 'python3')

            clean_path = clean_path.replace(
                                    os.path.normpath(
                                        environment['PYPE_STUDIO_CORE_MOUNT']),  # noqa
                                    os.path.normpath(
                                        environment['PYPE_STUDIO_CORE_PATH']))   # noqa
            clean_environment[key] = clean_path

        environment = clean_environment

        payload["JobInfo"].update({
            "EnvironmentKeyValue%d" % index: "{key}={value}".format(
                key=key,
                value=environment[key]
            ) for index, key in enumerate(environment)
        })

        plugin = payload["JobInfo"]["Plugin"]
        self.log.info("using render plugin : {}".format(plugin))

        self.log.info("Submitting..")
        self.log.info(json.dumps(payload, indent=4, sort_keys=True))

        response = requests.post(self.deadline_url, json=payload)

        if not response.ok:
            raise Exception(response.text)

        return response

    def preflight_check(self, instance):
        """Ensure the startFrame, endFrame and byFrameStep are integers"""

        for key in ("frameStart", "frameEnd"):
            value = instance.data[key]

            if int(value) == value:
                continue

            self.log.warning(
                "%f=%d was rounded off to nearest integer"
                % (value, int(value))
            )
