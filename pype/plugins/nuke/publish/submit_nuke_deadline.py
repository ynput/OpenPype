import os
import json
import getpass

import nuke

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

        node = None
        for x in instance:
            if x.Class() == "Write":
                node = x

        if node is None:
            return

        DEADLINE_REST_URL = os.environ.get("DEADLINE_REST_URL",
                                           "http://localhost:8082")
        assert DEADLINE_REST_URL, "Requires DEADLINE_REST_URL"

        context = instance.context
        workspace = os.path.dirname(context.data["currentFile"])
        filepath = None

        # get path
        path = nuke.filename(node)
        output_dir = instance.data['outputDir']

        filepath = context.data["currentFile"]

        self.log.debug(filepath)

        filename = os.path.basename(filepath)
        comment = context.data.get("comment", "")
        dirname = os.path.join(workspace, "renders")
        deadline_user = context.data.get("deadlineUser", getpass.getuser())
        jobname = "%s - %s" % (filename, instance.name)
        ver = re.search(r"\d+\.\d+", context.data.get("hostVersion"))

        try:
            # Ensure render folder exists
            os.makedirs(dirname)
        except OSError:
            pass

        # Documentation for keys available at:
        # https://docs.thinkboxsoftware.com
        #    /products/deadline/8.0/1_User%20Manual/manual
        #    /manual-submission.html#job-info-file-options
        payload = {
            "JobInfo": {
                # Top-level group name
                "BatchName": filename,

                # Job name, as seen in Monitor
                "Name": jobname,

                # Arbitrary username, for visualisation in Monitor
                "UserName": deadline_user,

                "Plugin": "Nuke",
                "Frames": "{start}-{end}".format(
                    start=int(instance.data["frameStart"]),
                    end=int(instance.data["frameEnd"])
                ),
                "ChunkSize": instance.data["deadlineChunkSize"],
                "Priority": instance.data["deadlinePriority"],

                "Comment": comment,

                # Optional, enable double-click to preview rendered
                # frames from Deadline Monitor
                # "OutputFilename0": output_filename_0.replace("\\", "/"),
            },
            "PluginInfo": {
                # Input
                "SceneFile": filepath,

                # Output directory and filename
                "OutputFilePath": dirname.replace("\\", "/"),
                # "OutputFilePrefix": render_variables["filename_prefix"],

                # Mandatory for Deadline
                "Version": ver.group(),

                # Resolve relative references
                "ProjectPath": workspace,

                # Only the specific write node is rendered.
                "WriteNode": instance[0].name()
            },

            # Mandatory for Deadline, may be empty
            "AuxFiles": []
        }

        # Include critical environment variables with submission
        keys = [
            # This will trigger `userSetup.py` on the slave
            # such that proper initialisation happens the same
            # way as it does on a local machine.
            # TODO(marcus): This won't work if the slaves don't
            # have accesss to these paths, such as if slaves are
            # running Linux and the submitter is on Windows.
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

        self.preflight_check(instance)

        self.log.info("Submitting..")
        self.log.info(json.dumps(payload, indent=4, sort_keys=True))

        # E.g. http://192.168.0.1:8082/api/jobs
        url = "{}/api/jobs".format(DEADLINE_REST_URL)
        response = requests.post(url, json=payload)
        if not response.ok:
            raise Exception(response.text)

        # Store output dir for unified publisher (filesequence)
        instance.data["deadlineSubmissionJob"] = response.json()
        instance.data["publishJobState"] = "Active"

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
