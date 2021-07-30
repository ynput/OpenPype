import time
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


def run_webserver(*args, **kwargs):
    """Runs webserver in command line, adds routes."""
    from openpype.modules import ModulesManager

    manager = ModulesManager()
    webserver_module = manager.modules_by_name["webserver"]
    webserver_module.create_server_manager()

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
    while True:
        time.sleep(0.5)
