import os
import json
import getpass

from avalon import api
from avalon.vendor import requests
import re
import pyblish.api


class ExtractCelactionDeadline(pyblish.api.InstancePlugin):
    """Submit CelAction2D scene to Deadline

    Renders are submitted to a Deadline Web Service as
    supplied via the environment variable DEADLINE_REST_URL

    """

    label = "Submit CelAction to Deadline"
    order = pyblish.api.IntegratorOrder + 0.1
    hosts = ["celaction"]
    families = ["render.farm"]

    deadline_department = ""
    deadline_priority = 50
    deadline_pool = ""
    deadline_pool_secondary = ""
    deadline_group = ""
    deadline_chunk_size = 1

    def process(self, instance):
        families = instance.data["families"]

        context = instance.context

        DEADLINE_REST_URL = os.environ.get("DEADLINE_REST_URL",
                                           "http://localhost:8082")
        assert DEADLINE_REST_URL, "Requires DEADLINE_REST_URL"

        self.deadline_url = "{}/api/jobs".format(DEADLINE_REST_URL)
        self._comment = context.data.get("comment", "")
        self._ver = re.search(r"\d+\.\d+", context.data.get("hostVersion"))
        self._deadline_user = context.data.get(
            "deadlineUser", getpass.getuser())
        self._frame_start = int(instance.data["frameStartHandle"])
        self._frame_end = int(instance.data["frameEndHandle"])

        # get output path
        render_path = instance.data['path']
        script_path = context.data["currentFile"]

        response = self.payload_submit(instance,
                                       script_path,
                                       render_path
                                       )
        # Store output dir for unified publisher (filesequence)
        instance.data["deadlineSubmissionJob"] = response.json()

        instance.data["outputDir"] = os.path.dirname(
            render_path).replace("\\", "/")

        instance.data["publishJobState"] = "Suspended"

        # adding 2d render specific family for version identification in Loader
        instance.data["families"] = families.insert(0, "render2d")

    def payload_submit(self,
                       instance,
                       script_path,
                       render_path,
                       responce_data=None
                       ):
        render_dir = os.path.normpath(os.path.dirname(render_path))
        script_name = os.path.basename(script_path)
        jobname = "%s - %s" % (script_name, instance.name)

        output_filename_0 = self.preview_fname(render_path)

        if not responce_data:
            responce_data = {}

        try:
            # Ensure render folder exists
            os.makedirs(render_dir)
        except OSError:
            pass

        # define chunk and priority
        chunk_size = instance.context.data.get("chunk")
        if chunk_size == 0:
            chunk_size = self.deadline_chunk_size

        payload = {
            "JobInfo": {
                # Top-level group name
                "BatchName": script_name,

                # Job name, as seen in Monitor
                "Name": jobname,

                # Arbitrary username, for visualisation in Monitor
                "UserName": self._deadline_user,

                "Department": self.deadline_department,
                "Priority": self.deadline_priority,
                "ChunkSize": chunk_size,

                "Group": self.deadline_group,
                "Pool": self.deadline_pool,
                "SecondaryPool": self.deadline_pool_secondary,

                "Plugin": "CelAction",
                "Frames": "{start}-{end}".format(
                    start=self._frame_start,
                    end=self._frame_end
                ),
                "Comment": self._comment,

                # Optional, enable double-click to preview rendered
                # frames from Deadline Monitor
                "OutputFilename0": output_filename_0.replace("\\", "/")

            },
            "PluginInfo": {
                # Input
                "SceneFile": script_path,

                # Output directory and filename
                "OutputFilePath": render_dir.replace("\\", "/"),

                # Mandatory for Deadline
                "Version": self._ver.group(),

                # Resolve relative references
                "ProjectPath": script_path,
                "AWSAssetFile0": render_path,
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
            "PYBLISHPLUGINPATH",
            "TOOL_ENV"
        ]
        environment = dict({key: os.environ[key] for key in keys
                            if key in os.environ}, **api.Session)

        for path in os.environ:
            if path.lower().startswith('pype_'):
                environment[path] = os.environ[path]

        environment["PATH"] = os.environ["PATH"]
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

        # adding expectied files to instance.data
        self.expected_files(instance, render_path)
        self.log.debug("__ expectedFiles: `{}`".format(
            instance.data["expectedFiles"]))
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

    def preview_fname(self, path):
        """Return output file path with #### for padding.

        Deadline requires the path to be formatted with # in place of numbers.
        For example `/path/to/render.####.png`

        Args:
            path (str): path to rendered images

        Returns:
            str

        """
        self.log.debug("_ path: `{}`".format(path))
        if "%" in path:
            search_results = re.search(r"(%0)(\d)(d.)", path).groups()
            self.log.debug("_ search_results: `{}`".format(search_results))
            return int(search_results[1])
        if "#" in path:
            self.log.debug("_ path: `{}`".format(path))
            return path
        else:
            return path

    def expected_files(self,
                       instance,
                       path):
        """ Create expected files in instance data
        """
        if not instance.data.get("expectedFiles"):
            instance.data["expectedFiles"] = list()

        dir = os.path.dirname(path)
        file = os.path.basename(path)

        if "#" in file:
            pparts = file.split("#")
            padding = "%0{}d".format(len(pparts) - 1)
            file = pparts[0] + padding + pparts[-1]

        if "%" not in file:
            instance.data["expectedFiles"].append(path)
            return

        for i in range(self._frame_start, (self._frame_end + 1)):
            instance.data["expectedFiles"].append(
                os.path.join(dir, (file % i)).replace("\\", "/"))
