import os
import json
import pprint
import re

from avalon import api, io
from avalon.vendor import requests, clique

import pyblish.api


def _get_script():
    """Get path to the image sequence script"""
    try:
        from pype.scripts import publish_filesequence
    except Exception as e:
        raise RuntimeError("Expected module 'publish_imagesequence'"
                           "to be available")

    module_path = publish_filesequence.__file__
    if module_path.endswith(".pyc"):
        module_path = module_path[:-len(".pyc")] + ".py"

    return module_path


# Logic to retrieve latest files concerning extendFrames
def get_latest_version(asset_name, subset_name, family):
    # Get asset
    asset_name = io.find_one({"type": "asset",
                              "name": asset_name},
                             projection={"name": True})

    subset = io.find_one({"type": "subset",
                          "name": subset_name,
                          "parent": asset_name["_id"]},
                         projection={"_id": True, "name": True})

    # Check if subsets actually exists (pre-run check)
    assert subset, "No subsets found, please publish with `extendFrames` off"

    # Get version
    version_projection = {"name": True,
                          "data.startFrame": True,
                          "data.endFrame": True,
                          "parent": True}

    version = io.find_one({"type": "version",
                           "parent": subset["_id"],
                           "data.families": family},
                          projection=version_projection,
                          sort=[("name", -1)])

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


class SubmitDependentImageSequenceJobDeadline(pyblish.api.InstancePlugin):
    """Submit image sequence publish jobs to Deadline.

    These jobs are dependent on a deadline job submission prior to this
    plug-in.

    Renders are submitted to a Deadline Web Service as
    supplied via the environment variable AVALON_DEADLINE

    Options in instance.data:
        - deadlineSubmission (dict, Required): The returned .json
            data from the job submission to deadline.

        - outputDir (str, Required): The output directory where the metadata
            file should be generated. It's assumed that this will also be
            final folder containing the output files.

        - ext (str, Optional): The extension (including `.`) that is required
            in the output filename to be picked up for image sequence
            publishing.

        - publishJobState (str, Optional): "Active" or "Suspended"
            This defaults to "Suspended"

    This requires a "startFrame" and "endFrame" to be present in instance.data
    or in context.data.

    """

    label = "Submit image sequence jobs to Deadline"
    order = pyblish.api.IntegratorOrder + 0.2

    hosts = ["fusion", "maya", "nuke"]

    families = [
        "render.deadline",
        "renderlayer",
        "imagesequence"
    ]

    def process(self, instance):

        # AVALON_DEADLINE = api.Session.get("AVALON_DEADLINE",
        #                                   "http://localhost:8082")
        # assert AVALON_DEADLINE, "Requires AVALON_DEADLINE"

        try:
            deadline_url = os.environ["DEADLINE_REST_URL"]
        except KeyError:
            self.log.error("Deadline REST API url not found.")

        # Get a submission job
        job = instance.data.get("deadlineSubmissionJob")
        if not job:
            raise RuntimeError("Can't continue without valid deadline "
                               "submission prior to this plug-in.")

        data = instance.data.copy()
        asset = data.get("asset") or api.Session["AVALON_ASSET"]
        subset = data["subset"]
        state = data.get("publishJobState", "Suspended")
        job_name = "{batch} - {subset} [publish image sequence]".format(
            batch=job["Props"]["Name"],
            subset=subset
        )

        # Get start/end frame from instance, if not available get from context
        context = instance.context
        start = instance.data.get("startFrame")
        if start is None:
            start = context.data["startFrame"]
        end = instance.data.get("endFrame")
        if end is None:
            end = context.data["endFrame"]

        # Add in regex for sequence filename
        # This assumes the output files start with subset name and ends with
        # a file extension. The "ext" key includes the dot with the extension.
        if "ext" in instance.data:
            ext = re.escape(instance.data["ext"])
        else:
            ext = "\.\D+"

        regex = "^{subset}.*\d+{ext}$".format(subset=re.escape(subset),
                                              ext=ext)

        try:
            source = data['source']
        except KeyError:
            source = context.data["currentFile"]

        relative_path = os.path.relpath(source, api.registered_root())
        source = os.path.join("{root}", relative_path).replace("\\", "/")

        # Write metadata for publish job
        render_job = data.pop("deadlineSubmissionJob")
        metadata = {
            "asset": asset,
            "regex": regex,
            "startFrame": start,
            "endFrame": end,
            "families": ["render"],
            "source": source,
            "user": context.data["user"],

            # Optional metadata (for debugging)
            "metadata": {
                "instance": data,
                "job": job,
                "session": api.Session.copy()
            }
        }

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

            for subset_name in subset_names:
                version = get_latest_version(asset_name=data["asset"],
                                             subset_name=subset_name,
                                             family=family)

                # Set prev start / end frames for comparison
                if not prev_start and not prev_end:
                    prev_start = version["data"]["startFrame"]
                    prev_end = version["data"]["endFrame"]

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
            # The current approach is not following Pyblish logic which is based
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
            metadata["startFrame"] = updated_start
            metadata["metadata"]["instance"]["startFrame"] = updated_start

            # End frame
            metadata["endFrame"] = updated_end
            metadata["metadata"]["instance"]["endFrame"] = updated_end

        metadata_filename = "{}_metadata.json".format(subset)
        metadata_path = os.path.join(output_dir, metadata_filename)
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=4, sort_keys=True)

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
                "InitialStatus": state
            },
            "PluginInfo": {
                "Version": "3.6",
                "ScriptFile": _get_script(),
                "Arguments": '--path "{}"'.format(metadata_path),
                "SingleFrameOnly": "True"
            },

            # Mandatory for Deadline, may be empty
            "AuxFiles": []
        }

        # Transfer the environment from the original job to this dependent
        # job so they use the same environment
        environment = job["Props"].get("Env", {})
        payload["JobInfo"].update({
            "EnvironmentKeyValue%d" % index: "{key}={value}".format(
                key=key,
                value=environment[key]
            ) for index, key in enumerate(environment)
        })

        # Avoid copied pools and remove secondary pool
        payload["JobInfo"]["Pool"] = "none"
        payload["JobInfo"].pop("SecondaryPool", None)

        self.log.info("Submitting..")
        self.log.info(json.dumps(payload, indent=4, sort_keys=True))

        url = "{}/api/jobs".format(deadline_url)
        response = requests.post(url, json=payload)
        if not response.ok:
            raise Exception(response.text)

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
