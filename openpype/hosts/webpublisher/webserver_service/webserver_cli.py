import collections
import time
import os
from datetime import datetime
import requests
import json
import subprocess

from openpype.lib import PypeLogger

from .webpublish_routes import (
    RestApiResource,
    OpenPypeRestApiResource,
    WebpublisherBatchPublishEndpoint,
    WebpublisherTaskPublishEndpoint,
    WebpublisherHiearchyEndpoint,
    WebpublisherProjectsEndpoint,
    BatchStatusEndpoint,
    PublishesStatusEndpoint,
    ConfiguredExtensionsEndpoint
)


log = PypeLogger().get_logger("webserver_gui")


def run_webserver(*args, **kwargs):
    """Runs webserver in command line, adds routes."""
    from openpype.modules import ModulesManager

    manager = ModulesManager()
    webserver_module = manager.modules_by_name["webserver"]
    host = kwargs.get("host") or "localhost"
    port = kwargs.get("port") or 8079
    server_manager = webserver_module.create_new_server_manager(port, host)
    webserver_url = server_manager.url
    # queue for remotepublishfromapp tasks
    studio_task_queue = collections.deque()

    resource = RestApiResource(server_manager,
                               upload_dir=kwargs["upload_dir"],
                               executable=kwargs["executable"],
                               studio_task_queue=studio_task_queue)
    projects_endpoint = WebpublisherProjectsEndpoint(resource)
    server_manager.add_route(
        "GET",
        "/api/projects",
        projects_endpoint.dispatch
    )

    hiearchy_endpoint = WebpublisherHiearchyEndpoint(resource)
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
    webpublisher_task_publish_endpoint = \
        WebpublisherBatchPublishEndpoint(resource)
    server_manager.add_route(
        "POST",
        "/api/webpublish/batch",
        webpublisher_task_publish_endpoint.dispatch
    )

    webpublisher_batch_publish_endpoint = \
        WebpublisherTaskPublishEndpoint(resource)
    server_manager.add_route(
        "POST",
        "/api/webpublish/task",
        webpublisher_batch_publish_endpoint.dispatch
    )

    # reporting
    openpype_resource = OpenPypeRestApiResource()
    batch_status_endpoint = BatchStatusEndpoint(openpype_resource)
    server_manager.add_route(
        "GET",
        "/api/batch_status/{batch_id}",
        batch_status_endpoint.dispatch
    )

    user_status_endpoint = PublishesStatusEndpoint(openpype_resource)
    server_manager.add_route(
        "GET",
        "/api/publishes/{user}",
        user_status_endpoint.dispatch
    )

    server_manager.start_server()
    last_reprocessed = time.time()
    while True:
        if time.time() - last_reprocessed > 20:
            reprocess_failed(kwargs["upload_dir"], webserver_url)
            last_reprocessed = time.time()
        if studio_task_queue:
            args = studio_task_queue.popleft()
            subprocess.call(args)  # blocking call

        time.sleep(1.0)


def reprocess_failed(upload_dir, webserver_url):
    # log.info("check_reprocesable_records")
    from openpype.lib import OpenPypeMongoConnection

    mongo_client = OpenPypeMongoConnection.get_mongo_client()
    database_name = os.environ["OPENPYPE_DATABASE_NAME"]
    dbcon = mongo_client[database_name]["webpublishes"]

    results = dbcon.find({"status": "reprocess"})
    for batch in results:
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
                        "status": "error",
                        "progress": 1,
                        "log": batch.get("log") + msg
                    }}
            )
            continue
        server_url = "{}/api/webpublish/batch".format(webserver_url)

        with open(batch_url) as f:
            data = json.loads(f.read())

        try:
            r = requests.post(server_url, json=data)
            log.info("response{}".format(r))
        except Exception:
            log.info("exception", exc_info=True)

        dbcon.update_one(
            {"_id": batch["_id"]},
            {"$set":
                {
                    "finish_date": datetime.now(),
                    "status": "sent_for_reprocessing",
                    "progress": 1
                }}
        )
