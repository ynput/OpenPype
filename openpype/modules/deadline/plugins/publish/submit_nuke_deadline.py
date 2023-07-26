import os
import re
import json
import getpass
from datetime import datetime

import requests
import pyblish.api

import nuke
from openpype.pipeline import legacy_io
from openpype.pipeline.publish import (
    OpenPypePyblishPluginMixin
)
from openpype.tests.lib import is_in_tests
from openpype.lib import (
    is_running_from_build,
    BoolDef,
    NumberDef
)


class NukeSubmitDeadline(pyblish.api.InstancePlugin,
                         OpenPypePyblishPluginMixin):
    """Submit write to Deadline

    Renders are submitted to a Deadline Web Service as
    supplied via settings key "DEADLINE_REST_URL".

    """

    label = "Submit Nuke to Deadline"
    order = pyblish.api.IntegratorOrder + 0.1
    hosts = ["nuke"]
    families = ["render", "prerender"]
    optional = True
    targets = ["local"]

    # presets
    priority = 50
    chunk_size = 1
    concurrent_tasks = 1
    group = ""
    department = ""
    limit_groups = {}
    use_gpu = False
    env_allowed_keys = []
    env_search_replace_values = {}
    # NOTE hornet updated for suspend_publish default on
    suspend_publish = True

    @classmethod
    def get_attribute_defs(cls):
        return [
            NumberDef(
                "priority",
                label="Priority",
                default=cls.priority,
                decimals=0
            ),
            NumberDef(
                "chunk",
                label="Frames Per Task",
                default=cls.chunk_size,
                decimals=0,
                minimum=1,
                maximum=1000
            ),
            NumberDef(
                "concurrency",
                label="Concurrency",
                default=cls.concurrent_tasks,
                decimals=0,
                minimum=1,
                maximum=10
            ),
            BoolDef(
                "use_gpu",
                default=cls.use_gpu,
                label="Use GPU"
            ),
            BoolDef(
                "suspend_publish",
                default=cls.suspend_publish,
                label="Suspend publish"
            )
        ]

    def process(self, instance):
        if not instance.data.get("farm"):
            self.log.info("Skipping local instance.")
            return

        instance.data["attributeValues"] = self.get_attr_values_from_data(
            instance.data)

        # add suspend_publish attributeValue to instance data
        instance.data["suspend_publish"] = instance.data["attributeValues"][
            "suspend_publish"]

        instance.data["toBeRenderedOn"] = "deadline"
        families = instance.data["families"]

        node = instance.data["transientData"]["node"]
        context = instance.context

        # get default deadline webservice url from deadline module
        deadline_url = instance.context.data["defaultDeadline"]
        # if custom one is set in instance, use that
        if instance.data.get("deadlineUrl"):
            deadline_url = instance.data.get("deadlineUrl")
        assert deadline_url, "Requires Deadline Webservice URL"

        self.deadline_url = "{}/api/jobs".format(deadline_url)
        self._comment = context.data.get("comment", "")
        self._ver = re.search(r"\d+\.\d+", context.data.get("hostVersion"))
        self._deadline_user = context.data.get(
            "deadlineUser", getpass.getuser())
        submit_frame_start = int(instance.data["frameStartHandle"])
        submit_frame_end = int(instance.data["frameEndHandle"])

        # get output path
        render_path = instance.data['path']
        script_path = context.data["currentFile"]

        for item in context:
            if "workfile" in item.data["families"]:
                msg = "Workfile (scene) must be published along"
                assert item.data["publish"] is True, msg

                template_data = item.data.get("anatomyData")
                rep = item.data.get("representations")[0].get("name")
                template_data["representation"] = rep
                template_data["ext"] = rep
                template_data["comment"] = None
                anatomy_filled = context.data["anatomy"].format(template_data)
                template_filled = anatomy_filled["publish"]["path"]
                script_path = os.path.normpath(template_filled)

                self.log.info(
                    "Using published scene for render {}".format(script_path)
                )

        response = self.payload_submit(
            instance,
            script_path,
            render_path,
            node.name(),
            submit_frame_start,
            submit_frame_end
        )
        # Store output dir for unified publisher (filesequence)
        instance.data["deadlineSubmissionJob"] = response.json()
        instance.data["outputDir"] = os.path.dirname(
            render_path).replace("\\", "/")
        instance.data["publishJobState"] = "Suspended"

        if instance.data.get("bakingNukeScripts"):
            for baking_script in instance.data["bakingNukeScripts"]:
                render_path = baking_script["bakeRenderPath"]
                script_path = baking_script["bakeScriptPath"]
                exe_node_name = baking_script["bakeWriteNodeName"]

                resp = self.payload_submit(
                    instance,
                    script_path,
                    render_path,
                    exe_node_name,
                    submit_frame_start,
                    submit_frame_end,
                    response.json()
                )

                # Store output dir for unified publisher (filesequence)
                instance.data["deadlineSubmissionJob"] = resp.json()
                instance.data["publishJobState"] = "Suspended"

                # add to list of job Id
                if not instance.data.get("bakingSubmissionJobs"):
                    instance.data["bakingSubmissionJobs"] = []

                instance.data["bakingSubmissionJobs"].append(
                    resp.json()["_id"])

        # redefinition of families
        if "render" in instance.data["family"]:
            instance.data['family'] = 'write'
            families.insert(0, "render2d")
        elif "prerender" in instance.data["family"]:
            instance.data['family'] = 'write'
            families.insert(0, "prerender")
        instance.data["families"] = families

    def payload_submit(
        self,
        instance,
        script_path,
        render_path,
        exe_node_name,
        start_frame,
        end_frame,
        response_data=None
    ):
        render_dir = os.path.normpath(os.path.dirname(render_path))
        batch_name = os.path.basename(script_path)
        jobname = "%s - %s" % (batch_name, instance.name)
        if is_in_tests():
            batch_name += datetime.now().strftime("%d%m%Y%H%M%S")


        output_filename_0 = self.preview_fname(render_path)

        if not response_data:
            response_data = {}

        try:
            # Ensure render folder exists
            os.makedirs(render_dir)
        except OSError:
            pass

        # resolve any limit groups
        limit_groups = self.get_limit_groups()
        self.log.info("Limit groups: `{}`".format(limit_groups))

        payload = {
            "JobInfo": {
                # Top-level group name
                "BatchName": batch_name,

                # Asset dependency to wait for at least the scene file to sync.
                # "AssetDependency0": script_path,

                # Job name, as seen in Monitor
                "Name": jobname,

                # Arbitrary username, for visualisation in Monitor
                "UserName": self._deadline_user,

                "Priority": instance.data["attributeValues"].get(
                    "priority", self.priority),
                "ChunkSize": instance.data["attributeValues"].get(
                    "chunk", self.chunk_size),
                "ConcurrentTasks": instance.data["attributeValues"].get(
                    "concurrency",
                    self.concurrent_tasks
                ),

                "Department": self.department,

                "Pool": instance.data.get("primaryPool"),
                "SecondaryPool": instance.data.get("secondaryPool"),
                "Group": self.group,

                "Plugin": "Nuke",
                "Frames": "{start}-{end}".format(
                    start=start_frame,
                    end=end_frame
                ),
                "Comment": self._comment,

                # Optional, enable double-click to preview rendered
                # frames from Deadline Monitor
                "OutputFilename0": output_filename_0.replace("\\", "/"),

                # limiting groups
                "LimitGroups": ",".join(limit_groups)

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

                # using GPU by default
                "UseGpu": instance.data["attributeValues"].get(
                    "use_gpu", self.use_gpu),

                # Only the specific write node is rendered.
                "WriteNode": exe_node_name
            },

            # Mandatory for Deadline, may be empty
            "AuxFiles": []
        }

        if response_data.get("_id"):
            payload["JobInfo"].update({
                "JobType": "Normal",
                "BatchName": response_data["Props"]["Batch"],
                "JobDependency0": response_data["_id"],
                "ChunkSize": 99999999
            })

        # Include critical environment variables with submission
        keys = [
            "PYTHONPATH",
            "PATH",
            "AVALON_PROJECT",
            "AVALON_ASSET",
            "AVALON_TASK",
            "AVALON_APP_NAME",
            "FTRACK_API_KEY",
            "FTRACK_API_USER",
            "FTRACK_SERVER",
            "PYBLISHPLUGINPATH",
            "NUKE_PATH",
            "TOOL_ENV",
            "FOUNDRY_LICENSE",
            "OPENPYPE_SG_USER",
        ]

        # Add OpenPype version if we are running from build.
        if is_running_from_build():
            keys.append("OPENPYPE_VERSION")

        # Add mongo url if it's enabled
        if instance.context.data.get("deadlinePassMongoUrl"):
            keys.append("OPENPYPE_MONGO")

        # add allowed keys from preset if any
        if self.env_allowed_keys:
            keys += self.env_allowed_keys

        environment = dict({key: os.environ[key] for key in keys
                            if key in os.environ}, **legacy_io.Session)

        for _path in os.environ:
            if _path.lower().startswith('openpype_'):
                environment[_path] = os.environ[_path]

        # to recognize job from PYPE for turning Event On/Off
        environment["OPENPYPE_RENDER_JOB"] = "1"

        # finally search replace in values of any key
        if self.env_search_replace_values:
            for key, value in environment.items():
                for _k, _v in self.env_search_replace_values.items():
                    environment[key] = value.replace(_k, _v)

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
        self.expected_files(
            instance,
            render_path,
            start_frame,
            end_frame
        )

        self.log.debug("__ expectedFiles: `{}`".format(
            instance.data["expectedFiles"]))
        response = requests.post(self.deadline_url, json=payload, timeout=10)

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

    def expected_files(
        self,
        instance,
        path,
        start_frame,
        end_frame
    ):
        """ Create expected files in instance data
        """
        if not instance.data.get("expectedFiles"):
            instance.data["expectedFiles"] = []

        dirname = os.path.dirname(path)
        file = os.path.basename(path)

        if "#" in file:
            pparts = file.split("#")
            padding = "%0{}d".format(len(pparts) - 1)
            file = pparts[0] + padding + pparts[-1]

        if "%" not in file:
            instance.data["expectedFiles"].append(path)
            return

        if instance.data.get("slate"):
            start_frame -= 1

        for i in range(start_frame, (end_frame + 1)):
            instance.data["expectedFiles"].append(
                os.path.join(dirname, (file % i)).replace("\\", "/"))

    def get_limit_groups(self):
        """Search for limit group nodes and return group name.
        Limit groups will be defined as pairs in Nuke deadline submitter
        presents where the key will be name of limit group and value will be
        a list of plugin's node class names. Thus, when a plugin uses more
        than one node, these will be captured and the triggered process
        will add the appropriate limit group to the payload jobinfo attributes.
        Returning:
            list: captured groups list
        """
        captured_groups = []
        for lg_name, list_node_class in self.limit_groups.items():
            for node_class in list_node_class:
                for node in nuke.allNodes(recurseGroups=True):
                    # ignore all nodes not member of defined class
                    if node.Class() not in node_class:
                        continue
                    # ignore all disabled nodes
                    if node["disable"].value():
                        continue
                    # add group name if not already added
                    if lg_name not in captured_groups:
                        captured_groups.append(lg_name)
        return captured_groups
