# -*- coding: utf-8 -*-
"""Submit publishing job to farm."""

import os
import json
import re
from copy import copy, deepcopy
import requests
import clique

import pyblish.api

from openpype.client import (
    get_last_version_by_subset_name,
    get_representations,
)
from openpype.pipeline import (
    get_representation_path,
    legacy_io,
)
from openpype.tests.lib import is_in_tests
from openpype.pipeline.farm.patterning import match_aov_pattern
from openpype.lib import is_running_from_build
from openpype.pipeline.farm.pyblish import (
    create_skeleton_instance,
    create_instances_for_aov
)


def get_resource_files(resources, frame_range=None):
    """Get resource files at given path.

    If `frame_range` is specified those outside will be removed.

    Arguments:
        resources (list): List of resources
        frame_range (list): Frame range to apply override

    Returns:
        list of str: list of collected resources

    """
    res_collections, _ = clique.assemble(resources)
    assert len(res_collections) == 1, "Multiple collections found"
    res_collection = res_collections[0]

    # Remove any frames
    if frame_range is not None:
        for frame in frame_range:
            if frame not in res_collection.indexes:
                continue
            res_collection.indexes.remove(frame)

    return list(res_collection)


class ProcessSubmittedJobOnFarm(pyblish.api.InstancePlugin):
    """Process Job submitted on farm.

    These jobs are dependent on a deadline or muster job
    submission prior to this plug-in.

    - In case of Deadline, it creates dependent job on farm publishing
      rendered image sequence.

    - In case of Muster, there is no need for such thing as dependent job,
      post action will be executed and rendered sequence will be published.

    Options in instance.data:
        - deadlineSubmissionJob (dict, Required): The returned .json
          data from the job submission to deadline.

        - musterSubmissionJob (dict, Required): same as deadline.

        - outputDir (str, Required): The output directory where the metadata
            file should be generated. It's assumed that this will also be
            final folder containing the output files.

        - ext (str, Optional): The extension (including `.`) that is required
            in the output filename to be picked up for image sequence
            publishing.

        - publishJobState (str, Optional): "Active" or "Suspended"
            This defaults to "Suspended"

        - expectedFiles (list or dict): explained below

    """

    label = "Submit image sequence jobs to Deadline or Muster"
    order = pyblish.api.IntegratorOrder + 0.2
    icon = "tractor"
    deadline_plugin = "OpenPype"
    targets = ["local"]

    hosts = ["fusion", "max", "maya", "nuke",
             "celaction", "aftereffects", "harmony"]

    families = ["render.farm", "prerender.farm",
                "renderlayer", "imagesequence", "maxrender", "vrayscene"]

    aov_filter = {"maya": [r".*([Bb]eauty).*"],
                  "aftereffects": [r".*"],  # for everything from AE
                  "harmony": [r".*"],  # for everything from AE
                  "celaction": [r".*"],
                  "max": [r".*"]}

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
    ]

    # Add OpenPype version if we are running from build.
    if is_running_from_build():
        environ_keys.append("OPENPYPE_VERSION")

    # custom deadline attributes
    deadline_department = ""
    deadline_pool = ""
    deadline_pool_secondary = ""
    deadline_group = ""
    deadline_chunk_size = 1
    deadline_priority = None

    # regex for finding frame number in string
    R_FRAME_NUMBER = re.compile(r'.+\.(?P<frame>[0-9]+)\..+')

    # mapping of instance properties to be transferred to new instance
    #     for every specified family
    instance_transfer = {
        "slate": ["slateFrames", "slate"],
        "review": ["lutPath"],
        "render2d": ["bakingNukeScripts", "version"],
        "renderlayer": ["convertToScanline"]
    }

    # list of family names to transfer to new family if present
    families_transfer = ["render3d", "render2d", "ftrack", "slate"]
    plugin_pype_version = "3.0"

    # script path for publish_filesequence.py
    publishing_script = None

    # poor man exclusion
    skip_integration_repre_list = []

    def _create_metadata_path(self, instance):
        ins_data = instance.data
        # Ensure output dir exists
        output_dir = ins_data.get(
            "publishRenderMetadataFolder", ins_data["outputDir"])

        try:
            if not os.path.isdir(output_dir):
                os.makedirs(output_dir)
        except OSError:
            # directory is not available
            self.log.warning("Path is unreachable: `{}`".format(output_dir))

        metadata_filename = "{}_metadata.json".format(ins_data["subset"])

        metadata_path = os.path.join(output_dir, metadata_filename)

        # Convert output dir to `{root}/rest/of/path/...` with Anatomy
        success, rootless_mtdt_p = self.anatomy.find_root_template_from_path(
            metadata_path)
        if not success:
            # `rootless_path` is not set to `output_dir` if none of roots match
            self.log.warning((
                "Could not find root path for remapping \"{}\"."
                " This may cause issues on farm."
            ).format(output_dir))
            rootless_mtdt_p = metadata_path

        return metadata_path, rootless_mtdt_p

    def _submit_deadline_post_job(self, instance, job, instances):
        """Submit publish job to Deadline.

        Deadline specific code separated from :meth:`process` for sake of
        more universal code. Muster post job is sent directly by Muster
        submitter, so this type of code isn't necessary for it.

        Returns:
            (str): deadline_publish_job_id
        """
        data = instance.data.copy()
        subset = data["subset"]
        job_name = "Publish - {subset}".format(subset=subset)

        # instance.data.get("subset") != instances[0]["subset"]
        # 'Main' vs 'renderMain'
        override_version = None
        instance_version = instance.data.get("version")  # take this if exists
        if instance_version != 1:
            override_version = instance_version
        output_dir = self._get_publish_folder(
            instance.context.data['anatomy'],
            deepcopy(instance.data["anatomyData"]),
            instance.data.get("asset"),
            instances[0]["subset"],
            'render',
            override_version
        )

        # Transfer the environment from the original job to this dependent
        # job so they use the same environment
        metadata_path, rootless_metadata_path = \
            self._create_metadata_path(instance)

        environment = {
            "AVALON_PROJECT": legacy_io.Session["AVALON_PROJECT"],
            "AVALON_ASSET": legacy_io.Session["AVALON_ASSET"],
            "AVALON_TASK": legacy_io.Session["AVALON_TASK"],
            "OPENPYPE_USERNAME": instance.context.data["user"],
            "OPENPYPE_PUBLISH_JOB": "1",
            "OPENPYPE_RENDER_JOB": "0",
            "OPENPYPE_REMOTE_JOB": "0",
            "OPENPYPE_LOG_NO_COLORS": "1",
            "IS_TEST": str(int(is_in_tests()))
        }

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

        args = [
            "--headless",
            'publish',
            rootless_metadata_path,
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
                "Plugin": self.deadline_plugin,
                "BatchName": job["Props"]["Batch"],
                "Name": job_name,
                "UserName": job["Props"]["User"],
                "Comment": instance.context.data.get("comment", ""),

                "Department": self.deadline_department,
                "ChunkSize": self.deadline_chunk_size,
                "Priority": priority,

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

        # add assembly jobs as dependencies
        if instance.data.get("tileRendering"):
            self.log.info("Adding tile assembly jobs as dependencies...")
            job_index = 0
            for assembly_id in instance.data.get("assemblySubmissionJobs"):
                payload["JobInfo"]["JobDependency{}".format(job_index)] = assembly_id  # noqa: E501
                job_index += 1
        elif instance.data.get("bakingSubmissionJobs"):
            self.log.info("Adding baking submission jobs as dependencies...")
            job_index = 0
            for assembly_id in instance.data["bakingSubmissionJobs"]:
                payload["JobInfo"]["JobDependency{}".format(job_index)] = assembly_id  # noqa: E501
                job_index += 1
        else:
            payload["JobInfo"]["JobDependency0"] = job["_id"]

        if instance.data.get("suspend_publish"):
            payload["JobInfo"]["InitialStatus"] = "Suspended"

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

        self.log.info("Submitting Deadline job ...")

        url = "{}/api/jobs".format(self.deadline_url)
        response = requests.post(url, json=payload, timeout=10)
        if not response.ok:
            raise Exception(response.text)

        deadline_publish_job_id = response.json()["_id"]

        return deadline_publish_job_id

    def _get_representations(self, instance, exp_files):
        """Create representations for file sequences.

        This will return representations of expected files if they are not
        in hierarchy of aovs. There should be only one sequence of files for
        most cases, but if not - we create representation from each of them.

        Arguments:
            instance (dict): instance data for which we are
                             setting representations
            exp_files (list): list of expected files

        Returns:
            list of representations

        """
        representations = []
        host_name = os.environ.get("AVALON_APP", "")
        collections, remainders = clique.assemble(exp_files)

        # create representation for every collected sequence
        for collection in collections:
            ext = collection.tail.lstrip(".")
            preview = False
            # TODO 'useSequenceForReview' is temporary solution which does
            #   not work for 100% of cases. We must be able to tell what
            #   expected files contains more explicitly and from what
            #   should be review made.
            # - "review" tag is never added when is set to 'False'
            if instance["useSequenceForReview"]:
                # toggle preview on if multipart is on
                if instance.get("multipartExr", False):
                    self.log.debug(
                        "Adding preview tag because its multipartExr"
                    )
                    preview = True
                else:
                    render_file_name = list(collection)[0]
                    # if filtered aov name is found in filename, toggle it for
                    # preview video rendering
                    preview = match_aov_pattern(
                        host_name, self.aov_filter, render_file_name
                    )

            staging = os.path.dirname(list(collection)[0])
            success, rootless_staging_dir = (
                self.anatomy.find_root_template_from_path(staging)
            )
            if success:
                staging = rootless_staging_dir
            else:
                self.log.warning((
                    "Could not find root path for remapping \"{}\"."
                    " This may cause issues on farm."
                ).format(staging))

            frame_start = int(instance.get("frameStartHandle"))
            if instance.get("slate"):
                frame_start -= 1

            rep = {
                "name": ext,
                "ext": ext,
                "files": [os.path.basename(f) for f in list(collection)],
                "frameStart": frame_start,
                "frameEnd": int(instance.get("frameEndHandle")),
                # If expectedFile are absolute, we need only filenames
                "stagingDir": staging,
                "fps": instance.get("fps"),
                "tags": ["review"] if preview else [],
            }

            # poor man exclusion
            if ext in self.skip_integration_repre_list:
                rep["tags"].append("delete")

            if instance.get("multipartExr", False):
                rep["tags"].append("multipartExr")

            # support conversion from tiled to scanline
            if instance.get("convertToScanline"):
                self.log.info("Adding scanline conversion.")
                rep["tags"].append("toScanline")

            representations.append(rep)

            self._solve_families(instance, preview)

        # add remainders as representations
        for remainder in remainders:
            ext = remainder.split(".")[-1]

            staging = os.path.dirname(remainder)
            success, rootless_staging_dir = (
                self.anatomy.find_root_template_from_path(staging)
            )
            if success:
                staging = rootless_staging_dir
            else:
                self.log.warning((
                    "Could not find root path for remapping \"{}\"."
                    " This may cause issues on farm."
                ).format(staging))

            rep = {
                "name": ext,
                "ext": ext,
                "files": os.path.basename(remainder),
                "stagingDir": staging,
            }

            preview = match_aov_pattern(
                host_name, self.aov_filter, remainder
            )
            if preview:
                rep.update({
                    "fps": instance.get("fps"),
                    "tags": ["review"]
                })
            self._solve_families(instance, preview)

            already_there = False
            for repre in instance.get("representations", []):
                # might be added explicitly before by publish_on_farm
                already_there = repre.get("files") == rep["files"]
                if already_there:
                    self.log.debug("repre {} already_there".format(repre))
                    break

            if not already_there:
                representations.append(rep)

        return representations

    def _solve_families(self, instance, preview=False):
        families = instance.get("families")

        # if we have one representation with preview tag
        # flag whole instance for review and for ftrack
        if preview:
            if "ftrack" not in families:
                if os.environ.get("FTRACK_SERVER"):
                    self.log.debug(
                        "Adding \"ftrack\" to families because of preview tag."
                    )
                    families.append("ftrack")
            if "review" not in families:
                self.log.debug(
                    "Adding \"review\" to families because of preview tag."
                )
                families.append("review")
            instance["families"] = families

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
            self.log.info("Skipping local instance.")
            return

        instance_skeleton_data = create_skeleton_instance(
                                    instance,
                                    families_transfer=self.families_transfer,
                                    instance_transfer=self.instance_transfer)

        instances = None

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
            instances = create_instances_for_aov(
                instance, instance_skeleton_data)

        else:
            representations = self._get_representations(
                instance_skeleton_data,
                instance.data.get("expectedFiles")
            )

            if "representations" not in instance_skeleton_data.keys():
                instance_skeleton_data["representations"] = []

            # add representation
            instance_skeleton_data["representations"] += representations
            instances = [instance_skeleton_data]

        # if we are attaching to other subsets, create copy of existing
        # instances, change data to match its subset and replace
        # existing instances with modified data
        if instance.data.get("attachTo"):
            self.log.info("Attaching render to subset:")
            new_instances = []
            for at in instance.data.get("attachTo"):
                for i in instances:
                    new_i = copy(i)
                    new_i["version"] = at.get("version")
                    new_i["subset"] = at.get("subset")
                    new_i["family"] = at.get("family")
                    new_i["append"] = True
                    # don't set subsetGroup if we are attaching
                    new_i.pop("subsetGroup")
                    new_instances.append(new_i)
                    self.log.info("  - {} / v{}".format(
                        at.get("subset"), at.get("version")))
            instances = new_instances

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

        if instance.data.get("toBeRenderedOn") == "muster":
            render_job = instance.data.pop("musterSubmissionJob", None)
            submission_type = "muster"

        if not render_job and instance.data.get("tileRendering") is False:
            raise AssertionError(("Cannot continue without valid Deadline "
                                  "or Muster submission."))

        if not render_job:
            import getpass

            render_job = {}
            self.log.info("Faking job data ...")
            render_job["Props"] = {}
            # Render job doesn't exist because we do not have prior submission.
            # We still use data from it so lets fake it.
            #
            # Batch name reflect original scene name

            if instance.data.get("assemblySubmissionJobs"):
                render_job["Props"]["Batch"] = instance.data.get(
                    "jobBatchName")
            else:
                render_job["Props"]["Batch"] = os.path.splitext(
                    os.path.basename(instance.context.data.get("currentFile")))[0]
            # User is deadline user
            render_job["Props"]["User"] = instance.context.data.get(
                "deadlineUser", getpass.getuser())

            render_job["Props"]["Env"] = {
                "FTRACK_API_USER": os.environ.get("FTRACK_API_USER"),
                "FTRACK_API_KEY": os.environ.get("FTRACK_API_KEY"),
                "FTRACK_SERVER": os.environ.get("FTRACK_SERVER"),
            }

        if submission_type == "deadline":
            # get default deadline webservice url from deadline module
            self.deadline_url = instance.context.data["defaultDeadline"]
            # if custom one is set in instance, use that
            if instance.data.get("deadlineUrl"):
                self.deadline_url = instance.data.get("deadlineUrl")
            assert self.deadline_url, "Requires Deadline Webservice URL"

            deadline_publish_job_id = \
                self._submit_deadline_post_job(instance, render_job, instances)

        # publish job file
        publish_job = {
            "asset": instance_skeleton_data["asset"],
            "frameStart": instance_skeleton_data["frameStart"],
            "frameEnd": instance_skeleton_data["frameEnd"],
            "fps": instance_skeleton_data["fps"],
            "source": instance_skeleton_data["source"],
            "user": instance.context.data["user"],
            "version": instance.context.data["version"],  # this is workfile version
            "intent": instance.context.data.get("intent"),
            "comment": instance.context.data.get("comment"),
            "job": render_job or None,
            "session": legacy_io.Session.copy(),
            "instances": instances
        }

        if deadline_publish_job_id:
            publish_job["deadline_publish_job_id"] = deadline_publish_job_id

        # add audio to metadata file if available
        audio_file = instance.context.data.get("audioFile")
        if audio_file and os.path.isfile(audio_file):
            publish_job.update({"audio": audio_file})

        # pass Ftrack credentials in case of Muster
        if submission_type == "muster":
            ftrack = {
                "FTRACK_API_USER": os.environ.get("FTRACK_API_USER"),
                "FTRACK_API_KEY": os.environ.get("FTRACK_API_KEY"),
                "FTRACK_SERVER": os.environ.get("FTRACK_SERVER"),
            }
            publish_job.update({"ftrack": ftrack})

        metadata_path, rootless_metadata_path = self._create_metadata_path(
            instance)

        self.log.info("Writing json file: {}".format(metadata_path))
        with open(metadata_path, "w") as f:
            json.dump(publish_job, f, indent=4, sort_keys=True)

    def _extend_frames(self, asset, subset, start, end):
        """Get latest version of asset nad update frame range.

        Based on minimum and maximuma values.

        Arguments:
            asset (str): asset name
            subset (str): subset name
            start (int): start frame
            end (int): end frame

        Returns:
            (int, int): upddate frame start/end

        """
        # Frame comparison
        prev_start = None
        prev_end = None

        project_name = legacy_io.active_project()
        version = get_last_version_by_subset_name(
            project_name,
            subset,
            asset_name=asset
        )

        # Set prev start / end frames for comparison
        if not prev_start and not prev_end:
            prev_start = version["data"]["frameStart"]
            prev_end = version["data"]["frameEnd"]

        updated_start = min(start, prev_start)
        updated_end = max(end, prev_end)

        self.log.info(
            "Updating start / end frame : "
            "{} - {}".format(updated_start, updated_end)
        )

        return updated_start, updated_end

    def _get_publish_folder(self, anatomy, template_data,
                            asset, subset,
                            family='render', version=None):
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
        if not version:
            project_name = legacy_io.active_project()
            version = get_last_version_by_subset_name(
                project_name,
                subset,
                asset_name=asset
            )
            if version:
                version = int(version["name"]) + 1
            else:
                version = 1

        template_data["subset"] = subset
        template_data["family"] = "render"
        template_data["version"] = version

        render_templates = anatomy.templates_obj["render"]
        if "folder" in render_templates:
            publish_folder = render_templates["folder"].format_strict(
                template_data
            )
        else:
            # solve deprecated situation when `folder` key is not underneath
            # `publish` anatomy
            project_name = legacy_io.Session["AVALON_PROJECT"]
            self.log.warning((
                "Deprecation warning: Anatomy does not have set `folder`"
                " key underneath `publish` (in global of for project `{}`)."
            ).format(project_name))

            file_path = render_templates["path"].format_strict(template_data)
            publish_folder = os.path.dirname(file_path)

        return publish_folder
