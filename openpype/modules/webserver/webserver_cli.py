import time
import os
from datetime import datetime
import requests
import json

from openpype.lib import PypeLogger

from .webpublish_routes import (
    RestApiResource,
    OpenPypeRestApiResource,
    WebpublisherBatchPublishEndpoint,
    WebpublisherTaskPublishEndpoint,
    WebpublisherHiearchyEndpoint,
    WebpublisherProjectsEndpoint,
    BatchStatusEndpoint,
    PublishesStatusEndpoint
)

from openpype.api import get_system_settings

SERVER_URL = "http://172.17.0.1:8079"  # machine is not listening on localhost

log = PypeLogger().get_logger("webserver_gui")


def run_webserver(*args, **kwargs):
    """Runs webserver in command line, adds routes."""
    from openpype.modules import ModulesManager

    manager = ModulesManager()
    webserver_module = manager.modules_by_name["webserver"]
    webserver_module.create_server_manager()

    is_webpublish_enabled = False
    webpublish_tool = get_system_settings()["modules"].\
        get("webpublish_tool")

    if webpublish_tool and webpublish_tool["enabled"]:
        is_webpublish_enabled = True

    log.debug("is_webpublish_enabled {}".format(is_webpublish_enabled))
    if is_webpublish_enabled:
        resource = RestApiResource(webserver_module.server_manager,
                                   upload_dir=kwargs["upload_dir"],
                                   executable=kwargs["executable"])
        projects_endpoint = WebpublisherProjectsEndpoint(resource)
        webserver_module.server_manager.add_route(
            "GET",
            "/api/projects",
            projects_endpoint.dispatch
        )

        hiearchy_endpoint = WebpublisherHiearchyEndpoint(resource)
        webserver_module.server_manager.add_route(
            "GET",
            "/api/hierarchy/{project_name}",
            hiearchy_endpoint.dispatch
        )

        # triggers publish
        webpublisher_task_publish_endpoint = \
            WebpublisherBatchPublishEndpoint(resource)
        webserver_module.server_manager.add_route(
            "POST",
            "/api/webpublish/batch",
            webpublisher_task_publish_endpoint.dispatch
        )

        webpublisher_batch_publish_endpoint = \
            WebpublisherTaskPublishEndpoint(resource)
        webserver_module.server_manager.add_route(
            "POST",
            "/api/webpublish/task",
            webpublisher_batch_publish_endpoint.dispatch
        )

        # reporting
        openpype_resource = OpenPypeRestApiResource()
        batch_status_endpoint = BatchStatusEndpoint(openpype_resource)
        webserver_module.server_manager.add_route(
            "GET",
            "/api/batch_status/{batch_id}",
            batch_status_endpoint.dispatch
        )

        user_status_endpoint = PublishesStatusEndpoint(openpype_resource)
        webserver_module.server_manager.add_route(
            "GET",
            "/api/publishes/{user}",
            user_status_endpoint.dispatch
        )

    webserver_module.start_server()
    last_reprocessed = time.time()
    while True:
        if is_webpublish_enabled:
            if time.time() - last_reprocessed > 20:
                reprocess_failed(kwargs["upload_dir"])
                last_reprocessed = time.time()
        time.sleep(1.0)


def reprocess_failed(upload_dir):
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
        server_url = "{}/api/webpublish/batch".format(SERVER_URL)

        with open(batch_url) as f:
            data = json.loads(f.read())

        try:
            r = requests.post(server_url, json=data)
            log.info("response{}".format(r))
        except:
            log.info("exception", exc_info=True)
