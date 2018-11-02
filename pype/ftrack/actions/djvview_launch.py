import os
import logging
import json

import ftrack
import ftrack_api
import clique
import ftrack_template

log = logging.getLogger(__name__)


def modify_launch(session, event):
    """Modify the application launch command with potential files to open"""

    # Collect published paths
    data = {}
    for item in event["data"].get("selection", []):

        versions = []

        if entity.entity_type == "Assetversion":
            version = ftrack.AssetVersion(item["entityId"])
            if version.getAsset().getType().getShort() in ["img", "mov"]:
                versions.append(version)

        # Add latest version of "img" and "mov" type from tasks.
        if item["entityType"] == "task":
            task = ftrack.Task(item["entityId"])
            for asset in task.getAssets(assetTypes=["img", "mov"]):
                versions.append(asset.getVersions()[-1])

        for version in versions:
            for component in version.getComponents():
                component_list = data.get(component.getName(), [])
                component_list.append(component)
                data[component.getName()] = component_list

                label = "v{0} - {1} - {2}"
                label = label.format(
                    str(version.getVersion()).zfill(3),
                    version.getAsset().getType().getName(),
                    component.getName()
                )

                file_path = component.getFilesystemPath()
                if component.isSequence():
                    if component.getMembers():
                        frame = int(component.getMembers()[0].getName())
                        file_path = file_path % frame

                event["data"]["items"].append(
                    {"label": label, "value": file_path}
                )

    # Collect workspace paths
    session = ftrack_api.Session()
    for item in event["data"].get("selection", []):
        if item["entityType"] == "task":
            templates = ftrack_template.discover_templates()
            task_area, template = ftrack_template.format(
                {}, templates, entity=session.get("Task", item["entityId"])
            )

            # Traverse directory and collect collections from json files.
            instances = []
            for root, dirs, files in os.walk(task_area):
                for f in files:
                    if f.endswith(".json"):
                        with open(os.path.join(root, f)) as json_data:
                            for data in json.load(json_data):
                                instances.append(data)

            check_values = []
            for data in instances:
                if "collection" in data:

                    # Check all files in the collection
                    collection = clique.parse(data["collection"])
                    for f in list(collection):
                        if not os.path.exists(f):
                            collection.remove(f)

                    if list(collection):
                        value = list(collection)[0]

                        # Check if value already exists
                        if value in check_values:
                            continue
                        else:
                            check_values.append(value)

                        # Add workspace items
                        event["data"]["items"].append(
                            {
                                "label": "{0} - {1}".format(
                                    data["name"],
                                    os.path.basename(collection.format())
                                ),
                                "value": value
                            }
                        )

    return event


def register(session, **kw):
    # Validate session
    if not isinstance(session, ftrack_api.session.Session):
        return

    session.event_hub.subscribe(
        'topic=djvview.launch',
        modify_launch(session)
    )
