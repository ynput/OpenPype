import gazu

from pymongo import DeleteOne, UpdateOne

from avalon.api import AvalonMongoDB
from openpype.lib import create_project


def sync_project(project: dict, dbcon: AvalonMongoDB) -> UpdateOne:
    """Sync project with database.
    Create project if doesn't exist.

    :param project: Gazu project
    :param dbcon: DB to create project in
    :return: Update instance for the project
    """
    project_name = project["name"]
    project_doc = dbcon.find_one({"type": "project"})
    if not project_doc:
        print(f"Creating project '{project_name}'")
        project_doc = create_project(project_name, project_name, dbcon=dbcon)

    print(f"Synchronizing {project_name}...")

    # Project data and tasks
    if not project["data"]:  # Sentinel
        project["data"] = {}

    return UpdateOne(
        {"_id": project_doc["_id"]},
        {
            "$set": {
                "config.tasks": {
                    t["name"]: {"short_name": t.get("short_name", t["name"])}
                    for t in gazu.task.all_task_types_for_project(project)
                },
                "data": project["data"].update(
                    {
                        "code": project["code"],
                        "fps": project["fps"],
                        "resolutionWidth": project["resolution"].split("x")[0],
                        "resolutionHeight": project["resolution"].split("x")[1],
                    }
                ),
            }
        },
    )
