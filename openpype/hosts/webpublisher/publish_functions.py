import os
import time
import pyblish.api
import pyblish.util

from openpype.lib import Logger
from openpype.lib.applications import (
    ApplicationManager,
    LaunchTypes,
)
from openpype.pipeline import install_host
from openpype.hosts.webpublisher.api import WebpublisherHost

from .lib import (
    get_batch_asset_task_info,
    get_webpublish_conn,
    start_webpublish_log,
    publish_and_log,
    fail_batch,
    find_variant_key,
    get_task_data,
    get_timeout,
    IN_PROGRESS_STATUS
)


def cli_publish(project_name, batch_path, user_email, targets):
    """Start headless publishing.

    Used to publish rendered assets, workfiles etc via Webpublisher.
    Eventually should be yanked out to Webpublisher cli.

    Publish use json from passed paths argument.

    Args:
        project_name (str): project to publish (only single context is
            expected per call of 'publish')
        batch_path (str): Path batch folder. Contains subfolders with
            resources (workfile, another subfolder 'renders' etc.)
        user_email (string): email address for webpublisher - used to
            find Ftrack user with same email
        targets (list): Pyblish targets
            (to choose validator for example)

    Raises:
        RuntimeError: When there is no path to process.
    """

    if not batch_path:
        raise RuntimeError("No publish paths specified")

    log = Logger.get_logger("Webpublish")
    log.info("Webpublish command")

    # Register target and host
    webpublisher_host = WebpublisherHost()

    os.environ["OPENPYPE_PUBLISH_DATA"] = batch_path
    os.environ["AVALON_PROJECT"] = project_name
    os.environ["AVALON_APP"] = webpublisher_host.name
    os.environ["USER_EMAIL"] = user_email
    os.environ["HEADLESS_PUBLISH"] = 'true'  # to use in app lib

    if targets:
        if isinstance(targets, str):
            targets = [targets]
        for target in targets:
            pyblish.api.register_target(target)

    install_host(webpublisher_host)

    log.info("Running publish ...")

    _, batch_id = os.path.split(batch_path)
    dbcon = get_webpublish_conn()
    _id = start_webpublish_log(dbcon, batch_id, user_email)

    task_data = get_task_data(batch_path)
    if not task_data["context"]:
        msg = "Batch manifest must contain context data"
        msg += "Create new batch and set context properly."
        fail_batch(_id, dbcon, msg)

    publish_and_log(dbcon, _id, log, batch_id=batch_id)

    log.info("Publish finished.")


def cli_publish_from_app(
    project_name, batch_path, host_name, user_email, targets
):
    """Opens installed variant of 'host' and run remote publish there.

    Eventually should be yanked out to Webpublisher cli.

    Currently implemented and tested for Photoshop where customer
    wants to process uploaded .psd file and publish collected layers
    from there. Triggered by Webpublisher.

    Checks if no other batches are running (status =='in_progress). If
    so, it sleeps for SLEEP (this is separate process),
    waits for WAIT_FOR seconds altogether.

    Requires installed host application on the machine.

    Runs publish process as user would, in automatic fashion.

    Args:
        project_name (str): project to publish (only single context is
            expected per call of publish
        batch_path (str): Path batch folder. Contains subfolders with
            resources (workfile, another subfolder 'renders' etc.)
        host_name (str): 'photoshop'
        user_email (string): email address for webpublisher - used to
            find Ftrack user with same email
        targets (list): Pyblish targets
            (to choose validator for example)
    """

    log = Logger.get_logger("PublishFromApp")

    log.info("Webpublish photoshop command")

    task_data = get_task_data(batch_path)

    workfile_path = os.path.join(batch_path,
                                 task_data["task"],
                                 task_data["files"][0])

    print("workfile_path {}".format(workfile_path))

    batch_id = task_data["batch"]
    dbcon = get_webpublish_conn()
    # safer to start logging here, launch might be broken altogether
    _id = start_webpublish_log(dbcon, batch_id, user_email)

    batches_in_progress = list(dbcon.find({"status": IN_PROGRESS_STATUS}))
    if len(batches_in_progress) > 1:
        running_batches = [str(batch["_id"])
                           for batch in batches_in_progress
                           if batch["_id"] != _id]
        msg = "There are still running batches {}\n". \
            format("\n".join(running_batches))
        msg += "Ask admin to check them and reprocess current batch"
        fail_batch(_id, dbcon, msg)

    if not task_data["context"]:
        msg = "Batch manifest must contain context data"
        msg += "Create new batch and set context properly."
        fail_batch(_id, dbcon, msg)

    asset_name, task_name, task_type = get_batch_asset_task_info(
        task_data["context"])

    application_manager = ApplicationManager()
    found_variant_key = find_variant_key(application_manager, host_name)
    app_name = "{}/{}".format(host_name, found_variant_key)

    data = {
        "last_workfile_path": workfile_path,
        "start_last_workfile": True,
        "project_name": project_name,
        "asset_name": asset_name,
        "task_name": task_name,
        "launch_type": LaunchTypes.automated,
    }
    launch_context = application_manager.create_launch_context(
        app_name, **data)
    launch_context.run_prelaunch_hooks()

    # must have for proper launch of app
    env = launch_context.env
    print("env:: {}".format(env))
    env["OPENPYPE_PUBLISH_DATA"] = batch_path
    # must pass identifier to update log lines for a batch
    env["BATCH_LOG_ID"] = str(_id)
    env["HEADLESS_PUBLISH"] = 'true'  # to use in app lib
    env["USER_EMAIL"] = user_email

    os.environ.update(env)

    # Why is this here? Registered host in this process does not affect
    #   regitered host in launched process.
    pyblish.api.register_host(host_name)
    if targets:
        if isinstance(targets, str):
            targets = [targets]
        current_targets = os.environ.get("PYBLISH_TARGETS", "").split(
            os.pathsep)
        for target in targets:
            current_targets.append(target)

        os.environ["PYBLISH_TARGETS"] = os.pathsep.join(
            set(current_targets))

    launched_app = application_manager.launch_with_context(launch_context)

    timeout = get_timeout(project_name, host_name, task_type)

    time_start = time.time()
    while launched_app.poll() is None:
        time.sleep(0.5)
        if time.time() - time_start > timeout:
            launched_app.terminate()
            msg = "Timeout reached"
            fail_batch(_id, dbcon, msg)
