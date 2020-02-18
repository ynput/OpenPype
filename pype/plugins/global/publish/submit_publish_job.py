import os
import json
import re
import logging

from avalon import api, io
from avalon.vendor import requests, clique

import pyblish.api


def _get_script():
    """Get path to the image sequence script"""
    try:
        from pype.scripts import publish_filesequence
    except Exception:
        raise RuntimeError("Expected module 'publish_deadline'"
                           "to be available")

    module_path = publish_filesequence.__file__
    if module_path.endswith(".pyc"):
        module_path = module_path[:-len(".pyc")] + ".py"

    module_path = os.path.normpath(module_path)
    mount_root = os.path.normpath(os.environ['PYPE_STUDIO_CORE_MOUNT'])
    network_root = os.path.normpath(os.environ['PYPE_STUDIO_CORE_PATH'])

    module_path = module_path.replace(mount_root, network_root)

    return module_path


# Logic to retrieve latest files concerning extendFrames
def get_latest_version(asset_name, subset_name, family):
    # Get asset
    asset_name = io.find_one(
        {
            "type": "asset",
            "name": asset_name
        },
        projection={"name": True}
    )

    subset = io.find_one(
        {
            "type": "subset",
            "name": subset_name,
            "parent": asset_name["_id"]
        },
        projection={"_id": True, "name": True}
    )

    # Check if subsets actually exists (pre-run check)
    assert subset, "No subsets found, please publish with `extendFrames` off"

    # Get version
    version_projection = {"name": True,
                          "data.startFrame": True,
                          "data.endFrame": True,
                          "parent": True}

    version = io.find_one(
        {
            "type": "version",
            "parent": subset["_id"],
            "data.families": family
        },
        projection=version_projection,
        sort=[("name", -1)]
    )

    assert version, "No version found, this is a bug"

    return version


def get_resources(version, extension=None):
    """
    Get the files from the specific version
    """
    query = {"type": "representation", "parent": version["_id"]}
    if extension:
        query["name"] = extension

    representation = io.find_one(query)
    assert representation, "This is a bug"

    directory = api.get_representation_path(representation)
    print("Source: ", directory)
    resources = sorted([os.path.normpath(os.path.join(directory, fname))
                        for fname in os.listdir(directory)])

    return resources


def get_resource_files(resources, frame_range, override=True):

    res_collections, _ = clique.assemble(resources)
    assert len(res_collections) == 1, "Multiple collections found"
    res_collection = res_collections[0]

    # Remove any frames
    if override:
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

    This requires a "frameStart" and "frameEnd" to be present in instance.data
    or in context.data.

    """

    label = "Submit image sequence jobs to Deadline or Muster"
    order = pyblish.api.IntegratorOrder + 0.2
    icon = "tractor"

    hosts = ["fusion", "maya", "nuke"]

    families = [
        "render.farm",
        "renderlayer",
        "imagesequence"
    ]

    enviro_filter = [
                     "PATH",
                     "PYTHONPATH",
                     "FTRACK_API_USER",
                     "FTRACK_API_KEY",
                     "FTRACK_SERVER",
                     "PYPE_ROOT",
                     "PYPE_METADATA_FILE",
                     "PYPE_STUDIO_PROJECTS_PATH",
                     "PYPE_STUDIO_PROJECTS_MOUNT"
                     ]
                     
    deadline_pool = ""

    def _submit_deadline_post_job(self, instance, job):
        """
        Deadline specific code separated from :meth:`process` for sake of
        more universal code. Muster post job is sent directly by Muster
        submitter, so this type of code isn't necessary for it.
        """
        data = instance.data.copy()
        subset = data["subset"]
        job_name = "{batch} - {subset} [publish image sequence]".format(
            batch=job["Props"]["Name"],
            subset=subset
        )

        metadata_filename = "{}_metadata.json".format(subset)
        output_dir = instance.data["outputDir"]
        metadata_path = os.path.join(output_dir, metadata_filename)

        metadata_path = os.path.normpath(metadata_path)
        mount_root = os.path.normpath(os.environ['PYPE_STUDIO_PROJECTS_MOUNT'])
        network_root = os.path.normpath(
            os.environ['PYPE_STUDIO_PROJECTS_PATH'])

        metadata_path = metadata_path.replace(mount_root, network_root)

        # Generate the payload for Deadline submission
        payload = {
            "JobInfo": {
                "Plugin": "Python",
                "BatchName": job["Props"]["Batch"],
                "Name": job_name,
                "JobType": "Normal",
                "JobDependency0": job["_id"],
                "UserName": job["Props"]["User"],
                "Comment": instance.context.data.get("comment", ""),
                "Priority": job["Props"]["Pri"],
                "Pool": self.deadline_pool
            },
            "PluginInfo": {
                "Version": "3.6",
                "ScriptFile": _get_script(),
                "Arguments": "",
                "SingleFrameOnly": "True"
            },

            # Mandatory for Deadline, may be empty
            "AuxFiles": []
        }

        # Transfer the environment from the original job to this dependent
        # job so they use the same environment

        environment = job["Props"].get("Env", {})
        environment["PYPE_METADATA_FILE"] = metadata_path
        i = 0
        for index, key in enumerate(environment):
            self.log.info("KEY: {}".format(key))
            self.log.info("FILTER: {}".format(self.enviro_filter))

            if key.upper() in self.enviro_filter:
                payload["JobInfo"].update({
                    "EnvironmentKeyValue%d" % i: "{key}={value}".format(
                        key=key,
                        value=environment[key]
                    )
                })
                i += 1

        # Avoid copied pools and remove secondary pool
        payload["JobInfo"]["Pool"] = "none"
        payload["JobInfo"].pop("SecondaryPool", None)

        self.log.info("Submitting..")
        self.log.info(json.dumps(payload, indent=4, sort_keys=True))

        url = "{}/api/jobs".format(self.DEADLINE_REST_URL)
        response = requests.post(url, json=payload)
        if not response.ok:
            raise Exception(response.text)

    def process(self, instance):
        """
        Detect type of renderfarm submission and create and post dependend job
        in case of Deadline. It creates json file with metadata needed for
        publishing in directory of render.

        :param instance: Instance data
        :type instance: dict
        """
        # Get a submission job
        data = instance.data.copy()
        if hasattr(instance, "_log"):
            data['_log'] = instance._log
        render_job = data.pop("deadlineSubmissionJob", None)
        submission_type = "deadline"

        if not render_job:
            # No deadline job. Try Muster: musterSubmissionJob
            render_job = data.pop("musterSubmissionJob", None)
            submission_type = "muster"
            if not render_job:
                raise RuntimeError("Can't continue without valid Deadline "
                                   "or Muster submission prior to this "
                                   "plug-in.")

        if submission_type == "deadline":
            self.DEADLINE_REST_URL = os.environ.get("DEADLINE_REST_URL",
                                                    "http://localhost:8082")
            assert self.DEADLINE_REST_URL, "Requires DEADLINE_REST_URL"

            self._submit_deadline_post_job(instance, render_job)

        asset = data.get("asset") or api.Session["AVALON_ASSET"]
        subset = data["subset"]

        # Get start/end frame from instance, if not available get from context
        context = instance.context
        start = instance.data.get("frameStart")
        if start is None:
            start = context.data["frameStart"]
        end = instance.data.get("frameEnd")
        if end is None:
            end = context.data["frameEnd"]

        # Add in regex for sequence filename
        # This assumes the output files start with subset name and ends with
        # a file extension. The "ext" key includes the dot with the extension.
        if "ext" in instance.data:
            ext = r"\." + re.escape(instance.data["ext"])
        else:
            ext = r"\.\D+"

        regex = r"^{subset}.*\d+{ext}$".format(subset=re.escape(subset),
                                               ext=ext)

        try:
            source = data['source']
        except KeyError:
            source = context.data["currentFile"]

        source = source.replace(os.getenv("PYPE_STUDIO_PROJECTS_MOUNT"),
                                api.registered_root())

        relative_path = os.path.relpath(source, api.registered_root())
        source = os.path.join("{root}", relative_path).replace("\\", "/")

        # find subsets and version to attach render to
        attach_to = instance.data.get("attachTo")
        attach_subset_versions = []
        if attach_to:
            for subset in attach_to:
                for instance in context:
                    if instance.data["subset"] != subset["subset"]:
                        continue
                    attach_subset_versions.append(
                        {"version": instance.data["version"],
                         "subset": subset["subset"],
                         "family": subset["family"]})

        # Write metadata for publish job
        metadata = {
            "asset": asset,
            "regex": regex,
            "frameStart": start,
            "frameEnd": end,
            "fps": context.data.get("fps", None),
            "families": ["render"],
            "source": source,
            "user": context.data["user"],
            "version": context.data["version"],
            "intent": context.data.get("intent"),
            "comment": context.data.get("comment"),
            # Optional metadata (for debugging)
            "metadata": {
                "instance": data,
                "job": render_job,
                "session": api.Session.copy()
            }
        }

        if api.Session["AVALON_APP"] == "nuke":
            metadata['subset'] = subset

        if submission_type == "muster":
            ftrack = {
                "FTRACK_API_USER": os.environ.get("FTRACK_API_USER"),
                "FTRACK_API_KEY": os.environ.get("FTRACK_API_KEY"),
                "FTRACK_SERVER": os.environ.get("FTRACK_SERVER")
            }
            metadata.update({"ftrack": ftrack})

        # Ensure output dir exists
        output_dir = instance.data["outputDir"]
        if not os.path.isdir(output_dir):
            os.makedirs(output_dir)

        if data.get("extendFrames", False):

            family = "render"
            override = data["overrideExistingFrame"]

            # override = data.get("overrideExistingFrame", False)
            out_file = render_job.get("OutFile")
            if not out_file:
                raise RuntimeError("OutFile not found in render job!")

            extension = os.path.splitext(out_file[0])[1]
            _ext = extension[1:]

            # Frame comparison
            prev_start = None
            prev_end = None
            resource_range = range(int(start), int(end)+1)

            # Gather all the subset files (one subset per render pass!)
            subset_names = [data["subset"]]
            subset_names.extend(data.get("renderPasses", []))
            resources = []
            for subset_name in subset_names:
                version = get_latest_version(asset_name=data["asset"],
                                             subset_name=subset_name,
                                             family=family)

                # Set prev start / end frames for comparison
                if not prev_start and not prev_end:
                    prev_start = version["data"]["frameStart"]
                    prev_end = version["data"]["frameEnd"]

                subset_resources = get_resources(version, _ext)
                resource_files = get_resource_files(subset_resources,
                                                    resource_range,
                                                    override)

                resources.extend(resource_files)

            updated_start = min(start, prev_start)
            updated_end = max(end, prev_end)

            # Update metadata and instance start / end frame
            self.log.info("Updating start / end frame : "
                          "{} - {}".format(updated_start, updated_end))

            # TODO : Improve logic to get new frame range for the
            # publish job (publish_filesequence.py)
            # The current approach is not following Pyblish logic
            # which is based
            # on Collect / Validate / Extract.

            # ---- Collect Plugins  ---
            # Collect Extend Frames - Only run if extendFrames is toggled
            # # # Store in instance:
            # # # Previous rendered files per subset based on frames
            # # # --> Add to instance.data[resources]
            # # # Update publish frame range

            # ---- Validate Plugins ---
            # Validate Extend Frames
            # # # Check if instance has the requirements to extend frames
            # There might have been some things which can be added to the list
            # Please do so when fixing this.

            # Start frame
            metadata["frameStart"] = updated_start
            metadata["metadata"]["instance"]["frameStart"] = updated_start

            # End frame
            metadata["frameEnd"] = updated_end
            metadata["metadata"]["instance"]["frameEnd"] = updated_end

        metadata_filename = "{}_metadata.json".format(subset)

        metadata_path = os.path.join(output_dir, metadata_filename)
        # convert log messages if they are `LogRecord` to their
        # string format to allow serializing as JSON later on.
        rendered_logs = []
        for log in metadata["metadata"]["instance"].get("_log", []):
            if isinstance(log, logging.LogRecord):
                rendered_logs.append(log.getMessage())
            else:
                rendered_logs.append(log)

        metadata["metadata"]["instance"]["_log"] = rendered_logs
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=4, sort_keys=True)

        # Copy files from previous render if extendFrame is True
        if data.get("extendFrames", False):

            self.log.info("Preparing to copy ..")
            import shutil

            dest_path = data["outputDir"]
            for source in resources:
                src_file = os.path.basename(source)
                dest = os.path.join(dest_path, src_file)
                shutil.copy(source, dest)

            self.log.info("Finished copying %i files" % len(resources))
