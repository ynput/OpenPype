import os
import getpass
import json

from openpype.lib import Logger
from openpype.pipeline import legacy_io

from openpype.hosts.batchpublisher import deadline
from openpype.hosts.batchpublisher import utils


logger = Logger.get_logger(__name__)


REVIEW_FAMILIES = {
    "render"
}

PUBLISH_TO_SG_FAMILIES = {
    "render"
}


def publish_version_pyblish(
        project_name,
        asset_name,
        task_name,
        family_name,
        subset_name,
        expected_representations,
        publish_data):

    # Hack required for environment to pick up in the farm
    legacy_io.Session["AVALON_PROJECT"] = project_name
    legacy_io.Session["AVALON_APP"] = "traypublisher"

    os.environ['AVALON_PROJECT'] = project_name

    representation_name = list(expected_representations.keys())[0]
    file_path = list(expected_representations.values())[0]

    from openpype.lib import FileDefItem

    from openpype.hosts.traypublisher.api import TrayPublisherHost
    from openpype.pipeline import install_host
    from openpype.pipeline.create import CreateContext
    import pyblish.api
    import logging

    host = TrayPublisherHost()
    install_host(host)

    create_context = CreateContext(host)
    pyblish_context = pyblish.api.Context()
    pyblish_context.data["create_context"] = create_context
    pyblish_plugins = create_context.publish_plugins

    instance = pyblish_context.create_instance(name=subset_name, family=family_name)
    instance.data.update(
        {
            "family": family_name,
            "asset": asset_name,
            "task": task_name,
            "subset": subset_name,
            "publish": True,
            "active": True,
            "source": file_path,
            "version": publish_data.get("version"),
            "comment": publish_data.get("comment"),
        })

    directory = os.path.dirname(file_path)
    file_name = os.path.basename(file_path)
    extension = os.path.splitext(file_name)[1].lstrip(".")

    representation = {
        "name": representation_name,
        "ext": extension,
        "preview": True,
        "tags": [],
        "files": file_name,
        "stagingDir": directory,
    }
    instance.data.setdefault("representations", [])
    instance.data["representations"].append(representation)

    error_format = ("Failed {plugin.__name__}: {error} -- {error.traceback}")

    for result in pyblish.util.publish_iter(context=pyblish_context, plugins=pyblish_plugins):
        for record in result["records"]:
            logging.info("{}: {}".format(result["plugin"].label, record.msg))
        if result["error"]:
            error_message = error_format.format(**result)
            logging.error(error_message)


def publish_version(
    project_name,
    asset_name,
    task_name,
    family_name,
    subset_name,
    expected_representations,
    publish_data,
):

    # Hack required for environment to pick up in the farm
    legacy_io.Session["AVALON_PROJECT"] = project_name
    legacy_io.Session["AVALON_APP"] = "traypublisher"

    # # Hack required for environment to pick up in the farm
    # legacy_io.Session["AVALON_PROJECT"] = project_name
    # legacy_io.Session["AVALON_APP"] = "traypublisher"

    # TODO: write some logic that finds the main path from the list of
    # representations
    source_path = list(expected_representations.values())[0]

    instance_data = {
        "project": project_name,
        "family": family_name,
        "subset": subset_name,
        "families": publish_data.get("families", []),
        "asset": asset_name,
        "task": task_name,
        "comment": publish_data.get("comment", ""),
        "source": source_path,
        "overrideExistingFrame": False,
        "useSequenceForReview": True,
        "colorspace": publish_data.get("colorspace"),
        "version": publish_data.get("version"),
        "outputDir": os.path.dirname(source_path),
    }

    representations = utils.get_representations(
        instance_data,
        expected_representations,
        add_review=family_name in REVIEW_FAMILIES,
        publish_to_sg=family_name in PUBLISH_TO_SG_FAMILIES,
    )
    if not representations:
        logger.error(
            "No representations could be found on expected dictionary: %s",
            expected_representations
        )
        return {}

    if family_name in REVIEW_FAMILIES:
        # inject colorspace data if we are generating a review
        for rep in representations:
            source_colorspace = publish_data.get("colorspace")
            source_colorspace = source_colorspace or "scene_linear"
            logger.debug(
                "Setting colorspace '%s' to representation", source_colorspace
            )
            utils.set_representation_colorspace(
                rep, project_name, colorspace=source_colorspace
            )

    instance_data["frameStartHandle"] = representations[0]["frameStart"]
    instance_data["frameEndHandle"] = representations[0]["frameEnd"]

    # add representation
    instance_data["representations"] = representations
    instances = [instance_data]

    # Create farm job to run OP publish
    metadata_path = utils.create_metadata_path(instance_data)
    logger.info("Metadata path: %s", metadata_path)

    publish_args = [
        "--headless",
        "publish",
        '"{}"'.format(metadata_path),
        "--targets",
        "deadline",
        "--targets",
        "farm",
    ]

    # Create dictionary of data specific to OP plugin for payload submit
    plugin_data = {
        "Arguments": " ".join(publish_args),
        "Version": os.getenv("OPENPYPE_VERSION"),
        "SingleFrameOnly": "True",
    }

    username = getpass.getuser()

    # Submit job to Deadline
    extra_env = {
        "AVALON_PROJECT": project_name,
        "AVALON_ASSET": asset_name,
        "AVALON_TASK": task_name,
        "OPENPYPE_USERNAME": username,
        "AVALON_WORKDIR": os.path.dirname(source_path),
        "OPENPYPE_PUBLISH_JOB": "1",
        "OPENPYPE_RENDER_JOB": "0",
        "OPENPYPE_REMOTE_JOB": "0",
        "OPENPYPE_LOG_NO_COLORS": "1",
        "OPENPYPE_SG_USER": username,
    }

    deadline_task_name = "Publish {} - {} - {} - {} - {}".format(
        family_name,
        subset_name,
        task_name,
        asset_name,
        project_name
    )

    response = deadline.payload_submit(
        project_name,
        plugin="OpenPype",
        plugin_data=plugin_data,
        batch_name=publish_data.get("jobBatchName") or deadline_task_name,
        task_name=deadline_task_name,
        # group=dl_constants.OP_GROUP,
        extra_env=extra_env,
    )

    # Set session environment variables as a few OP plugins
    # rely on these
    legacy_io.Session["AVALON_PROJECT"] = project_name
    legacy_io.Session["AVALON_ASSET"] = asset_name
    legacy_io.Session["AVALON_TASK"] = task_name
    legacy_io.Session["AVALON_WORKDIR"] = extra_env["AVALON_WORKDIR"]

    # publish job file
    publish_job = {
        "asset": instance_data["asset"],
        "frameStart": instance_data["frameStartHandle"],
        "frameEnd": instance_data["frameEndHandle"],
        "source": instance_data["source"],
        "user": getpass.getuser(),
        "version": None,  # this is workfile version
        "comment": instance_data["comment"],
        "job": {},
        "session": legacy_io.Session.copy(),
        "instances": instances,
        "deadline_publish_job_id": response.get("_id")
    }

    logger.info("Writing json file: {}".format(metadata_path))
    with open(metadata_path, "w") as f:
        json.dump(publish_job, f, indent=4, sort_keys=True)

    return response