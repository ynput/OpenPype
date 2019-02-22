"""Utility script for updating database with configuration files

Until assets are created entirely in the database, this script
provides a bridge between the file-based project inventory and configuration.

- Migrating an old project:
    $ python -m avalon.inventory --extract --silo-parent=f02_prod
    $ python -m avalon.inventory --upload

- Managing an existing project:
    1. Run `python -m avalon.inventory --load`
    2. Update the .inventory.toml or .config.toml
    3. Run `python -m avalon.inventory --save`

"""


from avalon import schema, io


def create_asset(data):
    """Create asset

    Requires:
        {"name": "uniquecode",
         "silo": "assets"}

     Optional:
        {"data": {}}
    """

    data = data.copy()

    project = io.find_one({"type": "project"})
    if project is None:
        raise RuntimeError("Project must exist prior to creating assets")

    asset = {
        "schema": "avalon-core:asset-2.0",
        "parent": project['_id'],
        "name": data.pop("name"),
        "silo": data.pop("silo"),
        "type": "asset",
        "data": data
    }

    # Asset *must* have a name and silo
    assert asset['name'], "Asset has no name"
    assert asset['silo'], "Asset has no silo"

    # Ensure it has a unique name
    asset_doc = io.find_one({
        "name": asset['name'],
        "type": "asset",
    })
    if asset_doc is not None:
        raise RuntimeError("Asset '{}' already exists.".format(asset['name']))

    schema.validate(asset)
    io.insert_one(asset)


def list_project_tasks():
    """List the project task types available in the current project"""
    project = io.find_one({"type": "project"})
    return [task['name'] for task in project['config']['tasks']]
