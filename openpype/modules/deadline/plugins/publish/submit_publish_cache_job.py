# -*- coding: utf-8 -*-
"""Submit publishing job to farm."""
import os
import json
import re
from copy import deepcopy
import requests

import pyblish.api

from openpype import AYON_SERVER_ENABLED
from openpype.client import (
    get_last_version_by_subset_name,
)
from openpype.pipeline import publish, legacy_io
from openpype.lib import EnumDef, is_running_from_build
from openpype.tests.lib import is_in_tests
from openpype.pipeline.version_start import get_versioning_start

from openpype.pipeline.farm.pyblish_functions import (
    create_skeleton_instance_cache,
    create_instances_for_cache,
    attach_instances_to_subset,
    prepare_cache_representations,
    create_metadata_path
)


class ProcessSubmittedCacheJobOnFarm(pyblish.api.InstancePlugin,
                                     publish.OpenPypePyblishPluginMixin,
                                     publish.ColormanagedPyblishPluginMixin):
    """Process Cache Job submitted on farm
    This is replicated version of submit publish job
    specifically for cache(s).

    These jobs are dependent on a deadline job
    submission prior to this plug-in.

    - In case of Deadline, it creates dependent job on farm publishing
      rendered image sequence.

    Options in instance.data:
        - deadlineSubmissionJob (dict, Required): The returned .json
          data from the job submission to deadline.

        - outputDir (str, Required): The output directory where the metadata
            file should be generated. It's assumed that this will also be
            final folder containing the output files.

        - ext (str, Optional): The extension (including `.`) that is required
            in the output filename to be picked up for image sequence
            publishing.

        - expectedFiles (list or dict): explained below

    """

    label = "Submit cache jobs to Deadline"
    order = pyblish.api.IntegratorOrder + 0.2
    icon = "tractor"

    targets = ["local"]

    hosts = ["houdini"]

    families = ["publish.hou"]

    environ_job_filter = [
        "OPENPYPE_METADATA_FILE"
    ]

    environ_keys = [
        "FTRACK_API_USER",
        "FTRACK_API_KEY",
        "FTRACK_SERVER",
        "AVALON_APP_NAME",
        "OPENPYPE_USERNAME",
        "OPENPYPE_SG_USER",
        "KITSU_LOGIN",
        "KITSU_PWD"
    ]

    # custom deadline attributes
    deadline_department = ""
    deadline_pool = ""
    deadline_pool_secondary = ""
    deadline_group = ""
    deadline_chunk_size = 1
    deadline_priority = None

    # regex for finding frame number in string
    R_FRAME_NUMBER = re.compile(r'.+\.(?P<frame>[0-9]+)\..+')

    plugin_pype_version = "3.0"

    # script path for publish_filesequence.py
    publishing_script = None

    def _submit_deadline_post_job(self, instance, job):
        """Submit publish job to Deadline.

        Returns:
            (str): deadline_publish_job_id
        """
        data = instance.data.copy()
        subset = data["subset"]
        job_name = "Publish - {subset}".format(subset=subset)

        anatomy = instance.context.data['anatomy']

        # instance.data.get("subset") != instances[0]["subset"]
        # 'Main' vs 'renderMain'
        override_version = None
        instance_version = instance.data.get("version")  # take this if exists
        if instance_version != 1:
            override_version = instance_version

        output_dir = self._get_publish_folder(
            anatomy,
            deepcopy(instance.data["anatomyData"]),
            instance.data.get("asset"),
            instance.data["subset"],
            instance.context,
            instance.data["family"],
            override_version
        )

        # Transfer the environment from the original job to this dependent
        # job so they use the same environment
        metadata_path, rootless_metadata_path = \
            create_metadata_path(instance, anatomy)

        environment = {
            "AVALON_PROJECT": instance.context.data["projectName"],
            "AVALON_ASSET": instance.context.data["asset"],
            "AVALON_TASK": instance.context.data["task"],
            "OPENPYPE_USERNAME": instance.context.data["user"],
            "OPENPYPE_LOG_NO_COLORS": "1",
            "IS_TEST": str(int(is_in_tests()))
        }

        if AYON_SERVER_ENABLED:
            environment["AYON_PUBLISH_JOB"] = "1"
            environment["AYON_RENDER_JOB"] = "0"
            environment["AYON_REMOTE_PUBLISH"] = "0"
            environment["AYON_BUNDLE_NAME"] = os.environ["AYON_BUNDLE_NAME"]
            deadline_plugin = "Ayon"
        else:
            environment["OPENPYPE_PUBLISH_JOB"] = "1"
            environment["OPENPYPE_RENDER_JOB"] = "0"
            environment["OPENPYPE_REMOTE_PUBLISH"] = "0"
            deadline_plugin = "OpenPype"
            # Add OpenPype version if we are running from build.
            if is_running_from_build():
                self.environ_keys.append("OPENPYPE_VERSION")

        # add environments from self.environ_keys
        for env_key in self.environ_keys:
            if os.getenv(env_key):
                environment[env_key] = os.environ[env_key]

        # pass environment keys from self.environ_job_filter
        job_environ = job["Props"].get("Env", {})
        for env_j_key in self.environ_job_filter:
            if job_environ.get(env_j_key):
                environment[env_j_key] = job_environ[env_j_key]

        # Add mongo url if it's enabled
        if instance.context.data.get("deadlinePassMongoUrl"):
            mongo_url = os.environ.get("OPENPYPE_MONGO")
            if mongo_url:
                environment["OPENPYPE_MONGO"] = mongo_url

        priority = self.deadline_priority or instance.data.get("priority", 50)

        instance_settings = self.get_attr_values_from_data(instance.data)
        initial_status = instance_settings.get("publishJobState", "Active")
        # TODO: Remove this backwards compatibility of `suspend_publish`
        if instance.data.get("suspend_publish"):
            initial_status = "Suspended"

        args = [
            "--headless",
            'publish',
            '"{}"'.format(rootless_metadata_path),
            "--targets", "deadline",
            "--targets", "farm"
        ]

        if is_in_tests():
            args.append("--automatic-tests")

        # Generate the payload for Deadline submission
        secondary_pool = (
            self.deadline_pool_secondary or instance.data.get("secondaryPool")
        )
        payload = {
            "JobInfo": {
                "Plugin": deadline_plugin,
                "BatchName": job["Props"]["Batch"],
                "Name": job_name,
                "UserName": job["Props"]["User"],
                "Comment": instance.context.data.get("comment", ""),

                "Department": self.deadline_department,
                "ChunkSize": self.deadline_chunk_size,
                "Priority": priority,
                "InitialStatus": initial_status,

                "Group": self.deadline_group,
                "Pool": self.deadline_pool or instance.data.get("primaryPool"),
                "SecondaryPool": secondary_pool,
                # ensure the outputdirectory with correct slashes
                "OutputDirectory0": output_dir.replace("\\", "/")
            },
            "PluginInfo": {
                "Version": self.plugin_pype_version,
                "Arguments": " ".join(args),
                "SingleFrameOnly": "True",
            },
            # Mandatory for Deadline, may be empty
            "AuxFiles": [],
        }

        if job.get("_id"):
            payload["JobInfo"]["JobDependency0"] = job["_id"]

        for index, (key_, value_) in enumerate(environment.items()):
            payload["JobInfo"].update(
                {
                    "EnvironmentKeyValue%d"
                    % index: "{key}={value}".format(
                        key=key_, value=value_
                    )
                }
            )
        # remove secondary pool
        payload["JobInfo"].pop("SecondaryPool", None)

        self.log.debug("Submitting Deadline publish job ...")

        url = "{}/api/jobs".format(self.deadline_url)
        response = requests.post(url, json=payload, timeout=10)
        if not response.ok:
            raise Exception(response.text)

        deadline_publish_job_id = response.json()["_id"]

        return deadline_publish_job_id

    def process(self, instance):
        # type: (pyblish.api.Instance) -> None
        """Process plugin.

        Detect type of render farm submission and create and post dependent
        job in case of Deadline. It creates json file with metadata needed for
        publishing in directory of render.

        Args:
            instance (pyblish.api.Instance): Instance data.

        """
        if not instance.data.get("farm"):
            self.log.debug("Skipping local instance.")
            return

        anatomy = instance.context.data["anatomy"]

        instance_skeleton_data = create_skeleton_instance_cache(instance)
        """
        if content of `expectedFiles` list are dictionaries, we will handle
        it as list of AOVs, creating instance for every one of them.

        Example:
        --------

        expectedFiles = [
            {
                "beauty": [
                    "foo_v01.0001.exr",
                    "foo_v01.0002.exr"
                ],

                "Z": [
                    "boo_v01.0001.exr",
                    "boo_v01.0002.exr"
                ]
            }
        ]

        This will create instances for `beauty` and `Z` subset
        adding those files to their respective representations.

        If we have only list of files, we collect all file sequences.
        More then one doesn't probably make sense, but we'll handle it
        like creating one instance with multiple representations.

        Example:
        --------

        expectedFiles = [
            "foo_v01.0001.exr",
            "foo_v01.0002.exr",
            "xxx_v01.0001.exr",
            "xxx_v01.0002.exr"
        ]

        This will result in one instance with two representations:
        `foo` and `xxx`
        """

        if isinstance(instance.data.get("expectedFiles")[0], dict):
            instances = create_instances_for_cache(
                instance, instance_skeleton_data)
        else:
            representations = prepare_cache_representations(
                instance_skeleton_data,
                instance.data.get("expectedFiles"),
                anatomy
            )

            if "representations" not in instance_skeleton_data.keys():
                instance_skeleton_data["representations"] = []

            # add representation
            instance_skeleton_data["representations"] += representations
            instances = [instance_skeleton_data]

        # attach instances to subset
        if instance.data.get("attachTo"):
            instances = attach_instances_to_subset(
                instance.data.get("attachTo"), instances
            )

        r''' SUBMiT PUBLiSH JOB 2 D34DLiN3
          ____
        '     '            .---.  .---. .--. .---. .--..--..--..--. .---.
        |     |   --= \   |  .  \/   _|/    \|  .  \  ||  ||   \  |/   _|
        | JOB |   --= /   |  |  ||  __|  ..  |  |  |  |;_ ||  \   ||  __|
        |     |           |____./ \.__|._||_.|___./|_____|||__|\__|\.___|
        ._____.

        '''

        render_job = None
        submission_type = ""
        if instance.data.get("toBeRenderedOn") == "deadline":
            render_job = instance.data.pop("deadlineSubmissionJob", None)
            submission_type = "deadline"

        if not render_job:
            import getpass

            render_job = {}
            self.log.debug("Faking job data ...")
            render_job["Props"] = {}
            # Render job doesn't exist because we do not have prior submission.
            # We still use data from it so lets fake it.
            #
            # Batch name reflect original scene name

            if instance.data.get("assemblySubmissionJobs"):
                render_job["Props"]["Batch"] = instance.data.get(
                    "jobBatchName")
            else:
                batch = os.path.splitext(os.path.basename(
                    instance.context.data.get("currentFile")))[0]
                render_job["Props"]["Batch"] = batch
            # User is deadline user
            render_job["Props"]["User"] = instance.context.data.get(
                "deadlineUser", getpass.getuser())

        deadline_publish_job_id = None
        if submission_type == "deadline":
            # get default deadline webservice url from deadline module
            self.deadline_url = instance.context.data["defaultDeadline"]
            # if custom one is set in instance, use that
            if instance.data.get("deadlineUrl"):
                self.deadline_url = instance.data.get("deadlineUrl")
            assert self.deadline_url, "Requires Deadline Webservice URL"

            deadline_publish_job_id = \
                self._submit_deadline_post_job(instance, render_job)

            # Inject deadline url to instances.
            for inst in instances:
                inst["deadlineUrl"] = self.deadline_url

        # publish job file
        publish_job = {
            "asset": instance_skeleton_data["asset"],
            "frameStart": instance_skeleton_data["frameStart"],
            "frameEnd": instance_skeleton_data["frameEnd"],
            "fps": instance_skeleton_data["fps"],
            "source": instance_skeleton_data["source"],
            "user": instance.context.data["user"],
            "version": instance.context.data["version"],  # workfile version
            "intent": instance.context.data.get("intent"),
            "comment": instance.context.data.get("comment"),
            "job": render_job or None,
            "session": legacy_io.Session.copy(),
            "instances": instances
        }

        if deadline_publish_job_id:
            publish_job["deadline_publish_job_id"] = deadline_publish_job_id

        metadata_path, rootless_metadata_path = \
            create_metadata_path(instance, anatomy)

        with open(metadata_path, "w") as f:
            json.dump(publish_job, f, indent=4, sort_keys=True)

    def _get_publish_folder(self, anatomy, template_data,
                            asset, subset, context,
                            family, version=None):
        """
            Extracted logic to pre-calculate real publish folder, which is
            calculated in IntegrateNew inside of Deadline process.
            This should match logic in:
                'collect_anatomy_instance_data' - to
                    get correct anatomy, family, version for subset and
                'collect_resources_path'
                    get publish_path

        Args:
            anatomy (openpype.pipeline.anatomy.Anatomy):
            template_data (dict): pre-calculated collected data for process
            asset (string): asset name
            subset (string): subset name (actually group name of subset)
            family (string): for current deadline process it's always 'render'
                TODO - for generic use family needs to be dynamically
                    calculated like IntegrateNew does
            version (int): override version from instance if exists

        Returns:
            (string): publish folder where rendered and published files will
                be stored
                based on 'publish' template
        """

        project_name = context.data["projectName"]
        if not version:
            version = get_last_version_by_subset_name(
                project_name,
                subset,
                asset_name=asset
            )
            if version:
                version = int(version["name"]) + 1
            else:
                version = get_versioning_start(
                    project_name,
                    template_data["app"],
                    task_name=template_data["task"]["name"],
                    task_type=template_data["task"]["type"],
                    family="render",
                    subset=subset,
                    project_settings=context.data["project_settings"]
                )

        host_name = context.data["hostName"]
        task_info = template_data.get("task") or {}

        template_name = publish.get_publish_template_name(
            project_name,
            host_name,
            family,
            task_info.get("name"),
            task_info.get("type"),
        )

        template_data["subset"] = subset
        template_data["family"] = family
        template_data["version"] = version

        render_templates = anatomy.templates_obj[template_name]
        if "folder" in render_templates:
            publish_folder = render_templates["folder"].format_strict(
                template_data
            )
        else:
            # solve deprecated situation when `folder` key is not underneath
            # `publish` anatomy
            self.log.warning((
                "Deprecation warning: Anatomy does not have set `folder`"
                " key underneath `publish` (in global of for project `{}`)."
            ).format(project_name))

            file_path = render_templates["path"].format_strict(template_data)
            publish_folder = os.path.dirname(file_path)

        return publish_folder

    @classmethod
    def get_attribute_defs(cls):
        return [
            EnumDef("publishJobState",
                    label="Publish Job State",
                    items=["Active", "Suspended"],
                    default="Active")
        ]
