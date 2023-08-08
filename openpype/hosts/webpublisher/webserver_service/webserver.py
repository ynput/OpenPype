import collections
import time
import os
from datetime import datetime
import requests
import json
import subprocess

from openpype.client import OpenPypeMongoConnection
from openpype.modules import ModulesManager
from openpype.lib import Logger

from openpype_modules.webpublisher.lib import (
    ERROR_STATUS,
    REPROCESS_STATUS,
    SENT_REPROCESSING_STATUS
)

from .webpublish_routes import (
    RestApiResource,
    WebpublishRestApiResource,
    HiearchyEndpoint,
    ProjectsEndpoint,
    ConfiguredExtensionsEndpoint,
    BatchPublishEndpoint,
    BatchReprocessEndpoint,
    BatchStatusEndpoint,
    TaskPublishEndpoint,
    UserReportEndpoint
)

log = Logger.get_logger("webserver_gui")


def run_webserver(executable, upload_dir, host=None, port=None):
    """Runs webserver in command line, adds routes."""

    if not host:
        host = "localhost"
    if not port:
        port = 8079

    manager = ModulesManager()
    webserver_module = manager.modules_by_name["webserver"]

    server_manager = webserver_module.create_new_server_manager(port, host)
    webserver_url = server_manager.url
    # queue for publishfromapp tasks
    studio_task_queue = collections.deque()

    resource = RestApiResource(server_manager,
                               upload_dir=upload_dir,
                               executable=executable,
                               studio_task_queue=studio_task_queue)
    projects_endpoint = ProjectsEndpoint(resource)
    server_manager.add_route(
        "GET",
        "/api/projects",
        projects_endpoint.dispatch
    )

    hiearchy_endpoint = HiearchyEndpoint(resource)
    server_manager.add_route(
        "GET",
        "/api/hierarchy/{project_name}",
        hiearchy_endpoint.dispatch
    )

    configured_ext_endpoint = ConfiguredExtensionsEndpoint(resource)
    server_manager.add_route(
        "GET",
        "/api/webpublish/configured_ext/{project_name}",
        configured_ext_endpoint.dispatch
    )

    # triggers publish
    webpublisher_task_publish_endpoint = BatchPublishEndpoint(resource)
    server_manager.add_route(
        "POST",
        "/api/webpublish/batch",
        webpublisher_task_publish_endpoint.dispatch
    )

    webpublisher_batch_publish_endpoint = TaskPublishEndpoint(resource)
    server_manager.add_route(
        "POST",
        "/api/webpublish/task",
        webpublisher_batch_publish_endpoint.dispatch
    )

    # reporting
    webpublish_resource = WebpublishRestApiResource()
    batch_status_endpoint = BatchStatusEndpoint(webpublish_resource)
    server_manager.add_route(
        "GET",
        "/api/batch_status/{batch_id}",
        batch_status_endpoint.dispatch
    )

    user_status_endpoint = UserReportEndpoint(webpublish_resource)
    server_manager.add_route(
        "GET",
        "/api/publishes/{user}",
        user_status_endpoint.dispatch
    )

    batch_reprocess_endpoint = BatchReprocessEndpoint(webpublish_resource)
    server_manager.add_route(
        "POST",
        "/api/webpublish/reprocess/{batch_id}",
        batch_reprocess_endpoint.dispatch
    )

    server_manager.start_server()
    last_reprocessed = time.time()
    while True:
        if time.time() - last_reprocessed > 20:
            reprocess_failed(upload_dir, webserver_url)
            last_reprocessed = time.time()
        if studio_task_queue:
            args = studio_task_queue.popleft()
            subprocess.call(args)  # blocking call

        time.sleep(1.0)


def reprocess_failed(upload_dir, webserver_url):
    # log.info("check_reprocesable_records")
    mongo_client = OpenPypeMongoConnection.get_mongo_client()
    database_name = os.environ["OPENPYPE_DATABASE_NAME"]
    dbcon = mongo_client[database_name]["webpublishes"]

    results = dbcon.find({"status": REPROCESS_STATUS})
    reprocessed_batches = set()
    for batch in results:
        if batch["batch_id"] in reprocessed_batches:
            continue

        batch_url = os.path.join(upload_dir,
                                 batch["batch_id"],
                                 "manifest.json")
        log.info("batch:: {} {}".format(os.path.exists(batch_url), batch_url))
        if not os.path.exists(batch_url):
            msg = "Manifest {} not found".format(batch_url)
            print(msg)
            dbcon.update_one(
                {"_id": batch["_id"]},
                {"$set":
                    {
                        "finish_date": datetime.now(),
                        "status": ERROR_STATUS,
                        "progress": 100,
                        "log": batch.get("log") + msg
                    }}
            )
            continue
        server_url = "{}/api/webpublish/batch".format(webserver_url)

        with open(batch_url) as f:
            data = json.loads(f.read())

        dbcon.update_many(
            {
                "batch_id": batch["batch_id"],
                "status": {"$in": [ERROR_STATUS, REPROCESS_STATUS]}
            },
            {
                "$set": {
                    "finish_date": datetime.now(),
                    "status": SENT_REPROCESSING_STATUS,
                    "progress": 100
                }
            }
        )

        try:
            r = requests.post(server_url, json=data)
            log.info("response{}".format(r))
        except Exception:
            log.info("exception", exc_info=True)

        reprocessed_batches.add(batch["batch_id"])
