# -*- coding: utf-8 -*-
"""Submit publishing job to farm."""

import os
import json
import re
from copy import copy

from avalon import api, io
from avalon.vendor import requests, clique

import pyblish.api


def _get_script():
    """Get path to the image sequence script."""
    try:
        from pype.scripts import publish_filesequence
    except Exception:
        assert False, "Expected module 'publish_deadline'to be available"

    module_path = publish_filesequence.__file__
    if module_path.endswith(".pyc"):
        module_path = module_path[: -len(".pyc")] + ".py"

    return os.path.normpath(module_path)


def get_latest_version(asset_name, subset_name, family):
    """Retrieve latest files concerning extendFrame feature."""
    # Get asset
    asset_name = io.find_one(
        {"type": "asset", "name": asset_name}, projection={"name": True}
    )

    subset = io.find_one(
        {"type": "subset", "name": subset_name, "parent": asset_name["_id"]},
        projection={"_id": True, "name": True},
    )

    # Check if subsets actually exists (pre-run check)
    assert subset, "No subsets found, please publish with `extendFrames` off"

    # Get version
    version_projection = {
        "name": True,
        "data.startFrame": True,
        "data.endFrame": True,
        "parent": True,
    }

    version = io.find_one(
        {"type": "version", "parent": subset["_id"], "data.families": family},
        projection=version_projection,
        sort=[("name", -1)],
    )

    assert version, "No version found, this is a bug"

    return version


def get_resources(version, extension=None):
    """Get the files from the specific version."""
    query = {"type": "representation", "parent": version["_id"]}
    if extension:
        query["name"] = extension

    representation = io.find_one(query)
    assert representation, "This is a bug"

    directory = api.get_representation_path(representation)
    print("Source: ", directory)
    resources = sorted(
        [
            os.path.normpath(os.path.join(directory, fname))
            for fname in os.listdir(directory)
        ]
    )

    return resources


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

    - In case of Deadline, it creates dependend job on farm publishing
      rendered image sequence.

    - In case of Muster, there is no need for such thing as dependend job,
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

        - expectedFiles (list or dict): explained bellow

    """

    label = "Submit image sequence jobs to Deadline or Muster"
    order = pyblish.api.IntegratorOrder + 0.2
    icon = "tractor"

    hosts = ["fusion", "maya", "nuke"]

    families = ["render.farm", "prerener", "renderlayer", "imagesequence"]

    aov_filter = {"maya": ["beauty"]}

    enviro_filter = [
        "FTRACK_API_USER",
        "FTRACK_API_KEY",
        "FTRACK_SERVER",
        "PYPE_METADATA_FILE",
        "AVALON_PROJECT",
        "PYPE_LOG_NO_COLORS"
    ]

    # pool used to do the publishing job
    deadline_pool = ""

    # regex for finding frame number in string
    R_FRAME_NUMBER = re.compile(r'.+\.(?P<frame>[0-9]+)\..+')

    # mapping of instance properties to be transfered to new instance for every
    # specified family
    instance_transfer = {
        "slate": ["slateFrame"],
        "review": ["lutPath"],
        "render2d": ["bakeScriptPath", "bakeRenderPath",
                     "bakeWriteNodeName", "version"]
    }

    # list of family names to transfer to new family if present
    families_transfer = ["render3d", "render2d", "ftrack", "slate"]

    def _submit_deadline_post_job(self, instance, job):
        """Submit publish job to Deadline.

        Deadline specific code separated from :meth:`process` for sake of
        more universal code. Muster post job is sent directly by Muster
        submitter, so this type of code isn't necessary for it.

        """
        data = instance.data.copy()
        subset = data["subset"]
        job_name = "{batch} - {subset} [publish image sequence]".format(
            batch=job["Props"]["Name"], subset=subset
        )

        output_dir = instance.data["outputDir"]
        # Convert output dir to `{root}/rest/of/path/...` with Anatomy
        success, rootless_path = (
            self.anatomy.find_root_template_from_path(output_dir)
        )
        if not success:
            # `rootless_path` is not set to `output_dir` if none of roots match
            self.log.warning((
                "Could not find root path for remapping \"{}\"."
                " This may cause issues on farm."
            ).format(output_dir))
            rootless_path = output_dir

        # Generate the payload for Deadline submission
        payload = {
            "JobInfo": {
                "Plugin": "Python",
                "BatchName": job["Props"]["Batch"],
                "Name": job_name,
                "JobDependency0": job["_id"],
                "UserName": job["Props"]["User"],
                "Comment": instance.context.data.get("comment", ""),
                "Priority": job["Props"]["Pri"],
                "Pool": self.deadline_pool,
                "OutputDirectory0": output_dir
            },
            "PluginInfo": {
                "Version": "3.6",
                "ScriptFile": _get_script(),
                "Arguments": "",
                "SingleFrameOnly": "True",
            },
            # Mandatory for Deadline, may be empty
            "AuxFiles": [],
        }

        # Transfer the environment from the original job to this dependent
        # job so they use the same environment
        metadata_filename = "{}_metadata.json".format(subset)
        metadata_path = os.path.join(rootless_path, metadata_filename)

        environment = job["Props"].get("Env", {})
        environment["PYPE_METADATA_FILE"] = metadata_path
        environment["AVALON_PROJECT"] = io.Session["AVALON_PROJECT"]
        environment["PYPE_LOG_NO_COLORS"] = "1"
        try:
            environment["PYPE_PYTHON_EXE"] = os.environ["PYPE_PYTHON_EXE"]
        except KeyError:
            # PYPE_PYTHON_EXE not set
            pass
        i = 0
        for index, key in enumerate(environment):
            if key.upper() in self.enviro_filter:
                payload["JobInfo"].update(
                    {
                        "EnvironmentKeyValue%d"
                        % i: "{key}={value}".format(
                            key=key, value=environment[key]
                        )
                    }
                )
                i += 1

        # remove secondary pool
        payload["JobInfo"].pop("SecondaryPool", None)

        self.log.info("Submitting Deadline job ...")
        # self.log.info(json.dumps(payload, indent=4, sort_keys=True))

        url = "{}/api/jobs".format(self.DEADLINE_REST_URL)
        response = requests.post(url, json=payload, timeout=10)
        if not response.ok:
            raise Exception(response.text)

    def _copy_extend_frames(self, instance, representation):
        """Copy existing frames from latest version.

        This will copy all existing frames from subset's latest version back
        to render directory and rename them to what renderer is expecting.

        Arguments:
            instance (pyblish.plugin.Instance): instance to get required
                data from
            representation (dict): presentation to operate on

        """
        import speedcopy

        self.log.info("Preparing to copy ...")
        start = instance.data.get("startFrame")
        end = instance.data.get("endFrame")

        # get latest version of subset
        # this will stop if subset wasn't published yet
        version = get_latest_version(
            instance.data.get("asset"),
            instance.data.get("subset"), "render")
        # get its files based on extension
        subset_resources = get_resources(version, representation.get("ext"))
        r_col, _ = clique.assemble(subset_resources)

        # if override remove all frames we are expecting to be rendered
        # so we'll copy only those missing from current render
        if instance.data.get("overrideExistingFrame"):
            for frame in range(start, end + 1):
                if frame not in r_col.indexes:
                    continue
                r_col.indexes.remove(frame)

        # now we need to translate published names from represenation
        # back. This is tricky, right now we'll just use same naming
        # and only switch frame numbers
        resource_files = []
        r_filename = os.path.basename(
            representation.get("files")[0])  # first file
        op = re.search(self.R_FRAME_NUMBER, r_filename)
        pre = r_filename[:op.start("frame")]
        post = r_filename[op.end("frame"):]
        assert op is not None, "padding string wasn't found"
        for frame in list(r_col):
            fn = re.search(self.R_FRAME_NUMBER, frame)
            # silencing linter as we need to compare to True, not to
            # type
            assert fn is not None, "padding string wasn't found"
            # list of tuples (source, destination)
            staging = representation.get("stagingDir")
            staging = self.anatomy.fill_roots(staging)
            resource_files.append(
                (frame,
                 os.path.join(staging,
                              "{}{}{}".format(pre,
                                              fn.group("frame"),
                                              post)))
            )

        # test if destination dir exists and create it if not
        output_dir = os.path.dirname(representation.get("files")[0])
        if not os.path.isdir(output_dir):
            os.makedirs(output_dir)

        # copy files
        for source in resource_files:
            speedcopy.copy(source[0], source[1])
            self.log.info("  > {}".format(source[1]))

        self.log.info(
            "Finished copying %i files" % len(resource_files))

    def _create_instances_for_aov(self, instance_data, exp_files):
        """Create instance for each AOV found.

        This will create new instance for every aov it can detect in expected
        files list.

        Arguments:
            instance_data (pyblish.plugin.Instance): skeleton data for instance
                (those needed) later by collector
            exp_files (list): list of expected files divided by aovs

        Returns:
            list of instances

        """
        task = os.environ["AVALON_TASK"]
        subset = instance_data["subset"]
        instances = []
        # go through aovs in expected files
        for aov, files in exp_files[0].items():
            cols, rem = clique.assemble(files)
            # we shouldn't have any reminders
            if rem:
                self.log.warning(
                    "skipping unexpected files found "
                    "in sequence: {}".format(rem))

            # but we really expect only one collection, nothing else make sense
            assert len(cols) == 1, "only one image sequence type is expected"

            # create subset name `familyTaskSubset_AOV`
            group_name = 'render{}{}{}{}'.format(
                task[0].upper(), task[1:],
                subset[0].upper(), subset[1:])

            subset_name = '{}_{}'.format(group_name, aov)

            staging = os.path.dirname(list(cols[0])[0])
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

            self.log.info("Creating data for: {}".format(subset_name))

            app = os.environ.get("AVALON_APP", "")

            preview = False
            if app in self.aov_filter.keys():
                if aov in self.aov_filter[app]:
                    preview = True

            new_instance = copy(instance_data)
            new_instance["subset"] = subset_name
            new_instance["subsetGroup"] = group_name

            ext = cols[0].tail.lstrip(".")

            # create represenation
            rep = {
                "name": ext,
                "ext": ext,
                "files": [os.path.basename(f) for f in list(cols[0])],
                "frameStart": int(instance_data.get("frameStartHandle")),
                "frameEnd": int(instance_data.get("frameEndHandle")),
                # If expectedFile are absolute, we need only filenames
                "stagingDir": staging,
                "fps": new_instance.get("fps"),
                "tags": ["review"] if preview else []
            }

            self._solve_families(new_instance, preview)

            new_instance["representations"] = [rep]

            # if extending frames from existing version, copy files from there
            # into our destination directory
            if new_instance.get("extendFrames", False):
                self._copy_extend_frames(new_instance, rep)
            instances.append(new_instance)

        return instances

    def _get_representations(self, instance, exp_files):
        """Create representations for file sequences.

        This will return representations of expected files if they are not
        in hierarchy of aovs. There should be only one sequence of files for
        most cases, but if not - we create representation from each of them.

        Arguments:
            instance (pyblish.plugin.Instance): instance for which we are
                                                setting representations
            exp_files (list): list of expected files

        Returns:
            list of representations

        """
        representations = []
        collections, remainders = clique.assemble(exp_files)
        bake_render_path = instance.get("bakeRenderPath")

        # create representation for every collected sequence
        for collection in collections:
            ext = collection.tail.lstrip(".")
            preview = False
            # if filtered aov name is found in filename, toggle it for
            # preview video rendering
            for app in self.aov_filter:
                if os.environ.get("AVALON_APP", "") == app:
                    for aov in self.aov_filter[app]:
                        if re.match(
                            r".+(?:\.|_)({})(?:\.|_).*".format(aov),
                            list(collection)[0]
                        ):
                            preview = True
                            break
                break

            if bake_render_path:
                preview = False

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

            rep = {
                "name": ext,
                "ext": ext,
                "files": [os.path.basename(f) for f in list(collection)],
                "frameStart": int(instance.get("frameStartHandle")),
                "frameEnd": int(instance.get("frameEndHandle")),
                # If expectedFile are absolute, we need only filenames
                "stagingDir": staging,
                "fps": instance.get("fps"),
                "tags": ["review", "preview"] if preview else [],
            }

            if instance.get("multipartExr", False):
                rep["tags"].append["multipartExr"]

            representations.append(rep)

            self._solve_families(instance, preview)

        # add reminders as representations
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
                "stagingDir": os.path.dirname(remainder),
            }
            if remainder in bake_render_path:
                rep.update({
                    "fps": instance.get("fps"),
                    "tags": ["review", "delete"]
                })
                # solve families with `preview` attributes
                self._solve_families(instance, True)
            representations.append(rep)

        return representations

    def _solve_families(self, instance, preview=False):
        families = instance.get("families")
        # if we have one representation with preview tag
        # flag whole instance for review and for ftrack
        if preview:
            if "ftrack" not in families:
                if os.environ.get("FTRACK_SERVER"):
                    families.append("ftrack")
            if "review" not in families:
                families.append("review")
            instance["families"] = families

    def process(self, instance):
        """Process plugin.

        Detect type of renderfarm submission and create and post dependend job
        in case of Deadline. It creates json file with metadata needed for
        publishing in directory of render.

        :param instance: Instance data
        :type instance: dict
        """
        data = instance.data.copy()
        context = instance.context
        self.context = context
        self.anatomy = instance.context.data["anatomy"]

        if hasattr(instance, "_log"):
            data['_log'] = instance._log
        render_job = data.pop("deadlineSubmissionJob", None)
        submission_type = "deadline"
        if not render_job:
            # No deadline job. Try Muster: musterSubmissionJob
            render_job = data.pop("musterSubmissionJob", None)
            submission_type = "muster"
            assert render_job, (
                "Can't continue without valid Deadline "
                "or Muster submission prior to this "
                "plug-in."
            )

        if submission_type == "deadline":
            self.DEADLINE_REST_URL = os.environ.get(
                "DEADLINE_REST_URL", "http://localhost:8082"
            )
            assert self.DEADLINE_REST_URL, "Requires DEADLINE_REST_URL"

            self._submit_deadline_post_job(instance, render_job)

        asset = data.get("asset") or api.Session["AVALON_ASSET"]
        subset = data.get("subset")

        start = instance.data.get("frameStart")
        if start is None:
            start = context.data["frameStart"]

        end = instance.data.get("frameEnd")
        if end is None:
            end = context.data["frameEnd"]

        handle_start = instance.data.get("handleStart")
        if handle_start is None:
            handle_start = context.data["handleStart"]

        handle_end = instance.data.get("handleEnd")
        if handle_end is None:
            handle_end = context.data["handleEnd"]

        fps = instance.data.get("fps")
        if fps is None:
            fps = context.data["fps"]

        if data.get("extendFrames", False):
            start, end = self._extend_frames(
                asset,
                subset,
                start,
                end,
                data["overrideExistingFrame"])

        try:
            source = data["source"]
        except KeyError:
            source = context.data["currentFile"]

        success, rootless_path = (
            self.anatomy.find_root_template_from_path(source)
        )
        if success:
            source = rootless_path

        else:
            # `rootless_path` is not set to `source` if none of roots match
            self.log.warning((
                "Could not find root path for remapping \"{}\"."
                " This may cause issues."
            ).format(source))

        families = ["render"]

        instance_skeleton_data = {
            "family": "render",
            "subset": subset,
            "families": families,
            "asset": asset,
            "frameStart": start,
            "frameEnd": end,
            "handleStart": handle_start,
            "handleEnd": handle_end,
            "frameStartHandle": start - handle_start,
            "frameEndHandle": end + handle_end,
            "fps": fps,
            "source": source,
            "extendFrames": data.get("extendFrames"),
            "overrideExistingFrame": data.get("overrideExistingFrame"),
            "pixelAspect": data.get("pixelAspect", 1),
            "resolutionWidth": data.get("resolutionWidth", 1920),
            "resolutionHeight": data.get("resolutionHeight", 1080),
            "multipartExr": data.get("multipartExr", False)
        }

        if "prerender" in instance.data["families"]:
            instance_skeleton_data.update({
                "family": "prerender",
                "families": []})

        # transfer specific families from original instance to new render
        for item in self.families_transfer:
            if item in instance.data.get("families", []):
                instance_skeleton_data["families"] += [item]

        if "render.farm" in instance.data["families"]:
            instance_skeleton_data.update({
                "family": "render2d",
                "families": ["render"] + [f for f in instance.data["families"]
                                          if "render.farm" not in f]
            })

        # transfer specific properties from original instance based on
        # mapping dictionary `instance_transfer`
        for key, values in self.instance_transfer.items():
            if key in instance.data.get("families", []):
                for v in values:
                    instance_skeleton_data[v] = instance.data.get(v)

        # look into instance data if representations are not having any
        # which are having tag `publish_on_farm` and include them
        for repre in instance.data.get("representations", []):
            staging_dir = repre.get("stagingDir")
            if staging_dir:
                success, rootless_staging_dir = (
                    self.anatomy.find_root_template_from_path(
                        staging_dir
                    )
                )
                if success:
                    repre["stagingDir"] = rootless_staging_dir
                else:
                    self.log.warning((
                        "Could not find root path for remapping \"{}\"."
                        " This may cause issues on farm."
                    ).format(staging_dir))
                    repre["stagingDir"] = staging_dir

            if "publish_on_farm" in repre.get("tags"):
                # create representations attribute of not there
                if "representations" not in instance_skeleton_data.keys():
                    instance_skeleton_data["representations"] = []

                instance_skeleton_data["representations"].append(repre)

        instances = None
        assert data.get("expectedFiles"), ("Submission from old Pype version"
                                           " - missing expectedFiles")

        """
        if content of `expectedFiles` are dictionaries, we will handle
        it as list of AOVs, creating instance from every one of them.

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

        If we've got only list of files, we collect all filesequences.
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

        self.log.info(data.get("expectedFiles"))

        if isinstance(data.get("expectedFiles")[0], dict):
            # we cannot attach AOVs to other subsets as we consider every
            # AOV subset of its own.

            if len(data.get("attachTo")) > 0:
                assert len(data.get("expectedFiles")[0].keys()) == 1, (
                    "attaching multiple AOVs or renderable cameras to "
                    "subset is not supported")

            # create instances for every AOV we found in expected files.
            # note: this is done for every AOV and every render camere (if
            #       there are multiple renderable cameras in scene)
            instances = self._create_instances_for_aov(
                instance_skeleton_data,
                data.get("expectedFiles"))
            self.log.info("got {} instance{}".format(
                len(instances),
                "s" if len(instances) > 1 else ""))

        else:
            representations = self._get_representations(
                instance_skeleton_data,
                data.get("expectedFiles")
            )

            if "representations" not in instance_skeleton_data.keys():
                instance_skeleton_data["representations"] = []

            # add representation
            instance_skeleton_data["representations"] += representations
            instances = [instance_skeleton_data]

        # if we are attaching to other subsets, create copy of existing
        # instances, change data to match thats subset and replace
        # existing instances with modified data
        if instance.data.get("attachTo"):
            self.log.info("Attaching render to subset:")
            new_instances = []
            for at in instance.data.get("attachTo"):
                for i in instances:
                    new_i = copy(i)
                    new_i["version"] = at.get("version")
                    new_i["subset"] = at.get("subset")
                    new_i["append"] = True
                    new_i["families"].append(at.get("family"))
                    new_instances.append(new_i)
                    self.log.info("  - {} / v{}".format(
                        at.get("subset"), at.get("version")))
            instances = new_instances

        # publish job file
        publish_job = {
            "asset": asset,
            "frameStart": start,
            "frameEnd": end,
            "fps": context.data.get("fps", None),
            "source": source,
            "user": context.data["user"],
            "version": context.data["version"],  # this is workfile version
            "intent": context.data.get("intent"),
            "comment": context.data.get("comment"),
            "job": render_job,
            "session": api.Session.copy(),
            "instances": instances
        }

        # pass Ftrack credentials in case of Muster
        if submission_type == "muster":
            ftrack = {
                "FTRACK_API_USER": os.environ.get("FTRACK_API_USER"),
                "FTRACK_API_KEY": os.environ.get("FTRACK_API_KEY"),
                "FTRACK_SERVER": os.environ.get("FTRACK_SERVER"),
            }
            publish_job.update({"ftrack": ftrack})

        # Ensure output dir exists
        output_dir = instance.data["outputDir"]
        if not os.path.isdir(output_dir):
            os.makedirs(output_dir)

        metadata_filename = "{}_metadata.json".format(subset)

        metadata_path = os.path.join(output_dir, metadata_filename)
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

        version = get_latest_version(
            asset_name=asset,
            subset_name=subset,
            family='render'
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
