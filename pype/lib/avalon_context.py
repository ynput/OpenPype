import os
import logging

from avalon import io
import avalon.api

log = logging.getLogger("AvalonContext")


def is_latest(representation):
    """Return whether the representation is from latest version

    Args:
        representation (dict): The representation document from the database.

    Returns:
        bool: Whether the representation is of latest version.

    """

    version = io.find_one({"_id": representation['parent']})
    if version["type"] == "master_version":
        return True

    # Get highest version under the parent
    highest_version = io.find_one({
        "type": "version",
        "parent": version["parent"]
    }, sort=[("name", -1)], projection={"name": True})

    if version['name'] == highest_version['name']:
        return True
    else:
        return False


def any_outdated():
    """Return whether the current scene has any outdated content"""

    checked = set()
    host = avalon.api.registered_host()
    for container in host.ls():
        representation = container['representation']
        if representation in checked:
            continue

        representation_doc = io.find_one(
            {
                "_id": io.ObjectId(representation),
                "type": "representation"
            },
            projection={"parent": True}
        )
        if representation_doc and not is_latest(representation_doc):
            return True
        elif not representation_doc:
            log.debug("Container '{objectName}' has an invalid "
                      "representation, it is missing in the "
                      "database".format(**container))

        checked.add(representation)
    return False


def switch_item(container,
                asset_name=None,
                subset_name=None,
                representation_name=None):
    """Switch container asset, subset or representation of a container by name.

    It'll always switch to the latest version - of course a different
    approach could be implemented.

    Args:
        container (dict): data of the item to switch with
        asset_name (str): name of the asset
        subset_name (str): name of the subset
        representation_name (str): name of the representation

    Returns:
        dict

    """

    if all(not x for x in [asset_name, subset_name, representation_name]):
        raise ValueError("Must have at least one change provided to switch.")

    # Collect any of current asset, subset and representation if not provided
    # so we can use the original name from those.
    if any(not x for x in [asset_name, subset_name, representation_name]):
        _id = io.ObjectId(container["representation"])
        representation = io.find_one({"type": "representation", "_id": _id})
        version, subset, asset, project = io.parenthood(representation)

        if asset_name is None:
            asset_name = asset["name"]

        if subset_name is None:
            subset_name = subset["name"]

        if representation_name is None:
            representation_name = representation["name"]

    # Find the new one
    asset = io.find_one({
        "name": asset_name,
        "type": "asset"
    })
    assert asset, ("Could not find asset in the database with the name "
                   "'%s'" % asset_name)

    subset = io.find_one({
        "name": subset_name,
        "type": "subset",
        "parent": asset["_id"]
    })
    assert subset, ("Could not find subset in the database with the name "
                    "'%s'" % subset_name)

    version = io.find_one(
        {
            "type": "version",
            "parent": subset["_id"]
        },
        sort=[('name', -1)]
    )

    assert version, "Could not find a version for {}.{}".format(
        asset_name, subset_name
    )

    representation = io.find_one({
        "name": representation_name,
        "type": "representation",
        "parent": version["_id"]}
    )

    assert representation, ("Could not find representation in the database "
                            "with the name '%s'" % representation_name)

    avalon.api.switch(container, representation)

    return representation


def get_asset(asset_name=None):
    """ Returning asset document from database """
    if not asset_name:
        asset_name = avalon.api.Session["AVALON_ASSET"]

    asset_document = io.find_one({
        "name": asset_name,
        "type": "asset"
    })

    if not asset_document:
        raise TypeError("Entity \"{}\" was not found in DB".format(asset_name))

    return asset_document


def get_hierarchy(asset_name=None):
    """
    Obtain asset hierarchy path string from mongo db

    Returns:
        string: asset hierarchy path

    """
    if not asset_name:
        asset_name = io.Session.get("AVALON_ASSET", os.environ["AVALON_ASSET"])

    asset_entity = io.find_one({
        "type": 'asset',
        "name": asset_name
    })

    not_set = "PARENTS_NOT_SET"
    entity_parents = asset_entity.get("data", {}).get("parents", not_set)

    # If entity already have parents then just return joined
    if entity_parents != not_set:
        return "/".join(entity_parents)

    # Else query parents through visualParents and store result to entity
    hierarchy_items = []
    entity = asset_entity
    while True:
        parent_id = entity.get("data", {}).get("visualParent")
        if not parent_id:
            break
        entity = io.find_one({"_id": parent_id})
        hierarchy_items.append(entity["name"])

    # Add parents to entity data for next query
    entity_data = asset_entity.get("data", {})
    entity_data["parents"] = hierarchy_items
    io.update_many(
        {"_id": asset_entity["_id"]},
        {"$set": {"data": entity_data}}
    )

    return "/".join(hierarchy_items)


def get_subsets(asset_name,
                regex_filter=None,
                version=None,
                representations=["exr", "dpx"]):
    """
    Query subsets with filter on name.

    The method will return all found subsets and its defined version
    and subsets. Version could be specified with number. Representation
    can be filtered.

    Arguments:
        asset_name (str): asset (shot) name
        regex_filter (raw): raw string with filter pattern
        version (str or int): `last` or number of version
        representations (list): list for all representations

    Returns:
        dict: subsets with version and representaions in keys
    """

    # query asset from db
    asset_io = io.find_one({"type": "asset", "name": asset_name})

    # check if anything returned
    assert asset_io, (
        "Asset not existing. Check correct name: `{}`").format(asset_name)

    # create subsets query filter
    filter_query = {"type": "subset", "parent": asset_io["_id"]}

    # add reggex filter string into query filter
    if regex_filter:
        filter_query.update({"name": {"$regex": r"{}".format(regex_filter)}})
    else:
        filter_query.update({"name": {"$regex": r'.*'}})

    # query all assets
    subsets = [s for s in io.find(filter_query)]

    assert subsets, ("No subsets found. Check correct filter. "
                     "Try this for start `r'.*'`: "
                     "asset: `{}`").format(asset_name)

    output_dict = {}
    # Process subsets
    for subset in subsets:
        if not version:
            version_sel = io.find_one(
                {
                    "type": "version",
                    "parent": subset["_id"]
                },
                sort=[("name", -1)]
            )
        else:
            assert isinstance(version, int), "version needs to be `int` type"
            version_sel = io.find_one({
                "type": "version",
                "parent": subset["_id"],
                "name": int(version)
            })

        find_dict = {"type": "representation",
                     "parent": version_sel["_id"]}

        filter_repr = {"name": {"$in": representations}}

        find_dict.update(filter_repr)
        repres_out = [i for i in io.find(find_dict)]

        if len(repres_out) > 0:
            output_dict[subset["name"]] = {"version": version_sel,
                                           "representations": repres_out}

    return output_dict


def get_linked_assets(asset_entity):
    """Return linked assets for `asset_entity`."""
    inputs = asset_entity["data"].get("inputs", [])
    inputs = [io.find_one({"_id": x}) for x in inputs]
    return inputs


def get_latest_version(asset_name, subset_name, dbcon=None, project_name=None):
    """Retrieve latest version from `asset_name`, and `subset_name`.

    Do not use if you want to query more than 5 latest versions as this method
    query 3 times to mongo for each call. For those cases is better to use
    more efficient way, e.g. with help of aggregations.

    Args:
        asset_name (str): Name of asset.
        subset_name (str): Name of subset.
        dbcon (avalon.mongodb.AvalonMongoDB, optional): Avalon Mongo connection
            with Session.
        project_name (str, optional): Find latest version in specific project.

    Returns:
        None: If asset, subset or version were not found.
        dict: Last version document for entered .
    """

    if not dbcon:
        log.debug("Using `avalon.io` for query.")
        dbcon = io
        # Make sure is installed
        io.install()

    if project_name and project_name != dbcon.Session.get("AVALON_PROJECT"):
        # `avalon.io` has only `_database` attribute
        # but `AvalonMongoDB` has `database`
        database = getattr(dbcon, "database", dbcon._database)
        collection = database[project_name]
    else:
        project_name = dbcon.Session.get("AVALON_PROJECT")
        collection = dbcon

    log.debug((
        "Getting latest version for Project: \"{}\" Asset: \"{}\""
        " and Subset: \"{}\""
    ).format(project_name, asset_name, subset_name))

    # Query asset document id by asset name
    asset_doc = collection.find_one(
        {"type": "asset", "name": asset_name},
        {"_id": True}
    )
    if not asset_doc:
        log.info(
            "Asset \"{}\" was not found in Database.".format(asset_name)
        )
        return None

    subset_doc = collection.find_one(
        {"type": "subset", "name": subset_name, "parent": asset_doc["_id"]},
        {"_id": True}
    )
    if not subset_doc:
        log.info(
            "Subset \"{}\" was not found in Database.".format(subset_name)
        )
        return None

    version_doc = collection.find_one(
        {"type": "version", "parent": subset_doc["_id"]},
        sort=[("name", -1)],
    )
    if not version_doc:
        log.info(
            "Subset \"{}\" does not have any version yet.".format(subset_name)
        )
        return None
    return version_doc
