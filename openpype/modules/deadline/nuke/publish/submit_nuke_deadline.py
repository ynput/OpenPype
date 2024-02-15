import os
import re
import json
import getpass
from datetime import datetime

import requests
import pyblish.api

from openpype import AYON_SERVER_ENABLED
from openpype.pipeline import legacy_io
from openpype.pipeline.publish import (
    OpenPypePyblishPluginMixin
)
from openpype.pipeline.context_tools import _get_modules_manager
from openpype.modules.deadline.utils import (
    set_custom_deadline_name,
    get_deadline_job_profile,
    DeadlineDefaultJobAttrs
)
from openpype.tests.lib import is_in_tests
from openpype.lib import (
    is_running_from_build,
    BoolDef,
    NumberDef,
    EnumDef
)

try:
    import nuke
except ImportError:
    # Ignoring, we don't want misleading error logs on jobs log on deadline.
    # Because the farm publish function imports every publish file before filtering.
    pass


class NukeSubmitDeadline(pyblish.api.InstancePlugin,
                         OpenPypePyblishPluginMixin,
                         DeadlineDefaultJobAttrs):
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

    chunk_size = 1
    concurrent_tasks = 1
    group = ""
    department = ""
    use_gpu = False
    env_allowed_keys = []
    env_search_replace_values = {}

    @classmethod
    def apply_settings(cls, project_settings, system_settings):
        profile = get_deadline_job_profile(project_settings, cls.hosts[0])
        cls.priority = profile.get("priority", cls.priority)
        cls.pool = profile.get("pool", cls.pool)
        cls.pool_secondary = profile.get("pool_secondary", cls.pool_secondary)

    @classmethod
    def get_attribute_defs(cls):
        defs = super(NukeSubmitDeadline, cls).get_attribute_defs()
        manager = _get_modules_manager()
        deadline_module = manager.modules_by_name["deadline"]
        deadline_url = deadline_module.deadline_urls["default"]
        pools = deadline_module.get_deadline_pools(deadline_url, cls.log)

        defs.extend([
            EnumDef("primary_pool",
                    label="Primary Pool",
                    items=pools,
                    default=cls.pool),
            EnumDef("secondary_pool",
                    label="Secondary Pool",
                    items=pools,
                    default=cls.pool_secondary),
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
                default=False,
                label="Suspend publish"
            )
        ])
        return defs

    def process(self, instance):
        if not instance.data.get("farm"):
            self.log.debug("Skipping local instance.")
            return
        instance.data["attributeValues"] = self.get_attr_values_from_data(
            instance.data)

        # add suspend_publish attributeValue to instance data
        instance.data["suspend_publish"] = instance.data["attributeValues"][
            "suspend_publish"]

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

        for item_ in context:
            if "workfile" in item_.data["family"]:
                template_data = item_.data.get("anatomyData")
                rep = item_.data.get("representations")[0].get("name")
                template_data["representation"] = rep
                template_data["ext"] = rep
                template_data["comment"] = None
                anatomy_filled = context.data["anatomy"].format(template_data)
                template_filled = anatomy_filled["publish"]["path"]
                script_path = os.path.normpath(template_filled)

                self.log.info(
                    "Using published scene for render {}".format(script_path)
                )

        # only add main rendering job if target is not frames_farm
        r_job_response_json = None
        if instance.data["render_target"] != "frames_farm":
            r_job_response = self.payload_submit(
                instance,
                script_path,
                render_path,
                node.name(),
                submit_frame_start,
                submit_frame_end
            )
            r_job_response_json = r_job_response.json()
            instance.data["deadlineSubmissionJob"] = r_job_response_json

            # Store output dir for unified publisher (filesequence)
            instance.data["outputDir"] = os.path.dirname(
                render_path).replace("\\", "/")
            instance.data["publishJobState"] = "Suspended"

        if instance.data.get("bakingNukeScripts"):
            for baking_script in instance.data["bakingNukeScripts"]:
                render_path = baking_script["bakeRenderPath"]
                script_path = baking_script["bakeScriptPath"]
                exe_node_name = baking_script["bakeWriteNodeName"]

                b_job_response = self.payload_submit(
                    instance,
                    script_path,
                    render_path,
                    exe_node_name,
                    submit_frame_start,
                    submit_frame_end,
                    r_job_response_json,
                    baking_submission=True
                )

                # Store output dir for unified publisher (filesequence)
                instance.data["deadlineSubmissionJob"] = b_job_response.json()

                instance.data["publishJobState"] = "Suspended"

                # add to list of job Id
                if not instance.data.get("bakingSubmissionJobs"):
                    instance.data["bakingSubmissionJobs"] = []

                instance.data["bakingSubmissionJobs"].append(
                    b_job_response.json()["_id"])

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
        response_data=None,
        baking_submission=False,
    ):
        """Submit payload to Deadline

        Args:
            instance (pyblish.api.Instance): pyblish instance
            script_path (str): path to nuke script
            render_path (str): path to rendered images
            exe_node_name (str): name of the node to render
            start_frame (int): start frame
            end_frame (int): end frame
            response_data Optional[dict]: response data from
                                          previous submission
            baking_submission Optional[bool]: if it's baking submission

        Returns:
            requests.Response
        """
        render_dir = os.path.normpath(os.path.dirname(render_path))

        # batch name
        src_filepath = instance.context.data["currentFile"]
        filename = os.path.basename(src_filepath)

        job_name = set_custom_deadline_name(
            instance,
            filename,
            "deadline_job_name"
        )
        batch_name = set_custom_deadline_name(
            instance,
            filename,
            "deadline_batch_name"
        )

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
        limits = ",".join(
            instance.data["creator_attributes"].get('limits', self.limits_plugin)
        )

        payload = {
            "JobInfo": {
                # Top-level group name
                "BatchName": "Group: " + batch_name,

                # Job name, as seen in Monitor
                "Name": job_name,

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

                "Pool": instance.data["attributeValues"].get(
                    "primary_pool", self.pool),
                "SecondaryPool": instance.data["attributeValues"].get(
                    "secondary_pool", self.pool_secondary),
                "MachineLimit": instance.data["creator_attributes"].get(
                    "machineLimit", self.limit_machine),
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
                "LimitGroups": limits

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

        # TODO: rewrite for baking with sequences
        if baking_submission:
            payload["JobInfo"].update({
                "JobType": "Normal",
                "ChunkSize": 99999999
            })

        if response_data.get("_id"):
            payload["JobInfo"].update({
                "BatchName": response_data["Props"]["Batch"],
                "JobDependency0": response_data["_id"],
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

        # add all gizmos and plugin paths to the NUKE_PATH for the render farm
        nuke_path = os.environ.get("NUKE_PATH", "")
        nuke_paths = [path for path in nuke_path.split(os.pathsep) if path]
        for nuke_plugin_path in nuke.pluginPath():
            if nuke_plugin_path not in nuke_paths:
                nuke_paths.append(nuke_plugin_path)
        os.environ["NUKE_PATH"] = os.pathsep.join(nuke_paths)

        environment = dict({key: os.environ[key] for key in keys
                            if key in os.environ}, **legacy_io.Session)

        for _path in os.environ:
            if _path.lower().startswith('openpype_'):
                environment[_path] = os.environ[_path]

        # to recognize render jobs
        if AYON_SERVER_ENABLED:
            environment["AYON_BUNDLE_NAME"] = os.environ["AYON_BUNDLE_NAME"]
            render_job_label = "AYON_RENDER_JOB"
        else:
            render_job_label = "OPENPYPE_RENDER_JOB"

        environment[render_job_label] = "1"

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
        self.log.debug("using render plugin : {}".format(plugin))

        self.log.debug("Submitting..")
        self.log.debug(json.dumps(payload, indent=4, sort_keys=True))

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
