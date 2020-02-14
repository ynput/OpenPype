from bson.objectid import ObjectId

from .avalon_sync import CustAttrIdKey
import avalon.io


def get_project_from_entity(entity):
    # TODO add more entities
    ent_type_lowered = entity.entity_type.lower()
    if ent_type_lowered == "project":
        return entity

    elif ent_type_lowered == "assetversion":
        return entity["asset"]["parent"]["project"]

    elif "project" in entity:
        return entity["project"]

    return None


def get_avalon_entities_for_assetversion(asset_version, db_con=None):
    output = {
        "success": True,
        "message": None,
        "project": None,
        "project_name": None,
        "asset": None,
        "asset_name": None,
        "asset_path": None,
        "subset": None,
        "subset_name": None,
        "version": None,
        "version_name": None,
        "representations": None
    }

    if db_con is None:
        db_con = avalon.io
    db_con.install()

    ft_asset = asset_version["asset"]
    subset_name = ft_asset["name"]
    version = asset_version["version"]
    parent = ft_asset["parent"]
    ent_path = "/".join(
        [ent["name"] for ent in parent["link"]]
    )
    project = get_project_from_entity(asset_version)
    project_name = project["full_name"]

    output["project_name"] = project_name
    output["asset_name"] = parent["name"]
    output["asset_path"] = ent_path
    output["subset_name"] = subset_name
    output["version_name"] = version

    db_con.Session["AVALON_PROJECT"] = project_name

    avalon_project = db_con.find_one({"type": "project"})
    output["project"] = avalon_project

    if not avalon_project:
        output["success"] = False
        output["message"] = "Project not synchronized to avalon `{}`".format(
            project_name
        )
        return output

    asset_ent = None
    asset_mongo_id = parent["custom_attributes"].get(CustAttrIdKey)
    if asset_mongo_id:
        try:
            asset_mongo_id = ObjectId(asset_mongo_id)
            asset_ent = db_con.find_one({
                "type": "asset",
                "_id": asset_mongo_id
            })
        except Exception:
            pass

    if not asset_ent:
        asset_ent = db_con.find_one({
            "type": "asset",
            "data.ftrackId": parent["id"]
        })

    output["asset"] = asset_ent

    if not asset_ent:
        output["success"] = False
        output["message"] = "Not synchronized entity to avalon `{}`".format(
            ent_path
        )
        return output

    asset_mongo_id = asset_ent["_id"]

    subset_ent = db_con.find_one({
        "type": "subset",
        "parent": asset_mongo_id,
        "name": subset_name
    })

    output["subset"] = subset_ent

    if not subset_ent:
        output["success"] = False
        output["message"] = (
            "Subset `{}` does not exist under Asset `{}`"
        ).format(subset_name, ent_path)
        return output

    version_ent = db_con.find_one({
        "type": "version",
        "name": version,
        "parent": subset_ent["_id"]
    })

    output["version"] = version_ent

    if not version_ent:
        output["success"] = False
        output["message"] = (
            "Version `{}` does not exist under Subset `{}` | Asset `{}`"
        ).format(version, subset_name, ent_path)
        return output

    repre_ents = list(db_con.find({
        "type": "representation",
        "parent": version_ent["_id"]
    }))

    output["representations"] = repre_ents
    return output
