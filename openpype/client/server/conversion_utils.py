import os
import arrow
import collections
import json

import six

from openpype.client.operations_base import REMOVED_VALUE
from openpype.client.mongo.operations import (
    CURRENT_PROJECT_SCHEMA,
    CURRENT_ASSET_DOC_SCHEMA,
    CURRENT_SUBSET_SCHEMA,
    CURRENT_VERSION_SCHEMA,
    CURRENT_HERO_VERSION_SCHEMA,
    CURRENT_REPRESENTATION_SCHEMA,
    CURRENT_WORKFILE_INFO_SCHEMA,
)
from .constants import REPRESENTATION_FILES_FIELDS
from .utils import create_entity_id, prepare_entity_changes

# --- Project entity ---
PROJECT_FIELDS_MAPPING_V3_V4 = {
    "_id": {"name"},
    "name": {"name"},
    "data": {"data", "code"},
    "data.library_project": {"library"},
    "data.code": {"code"},
    "data.active": {"active"},
}

# TODO this should not be hardcoded but received from server!!!
# --- Folder entity ---
FOLDER_FIELDS_MAPPING_V3_V4 = {
    "_id": {"id"},
    "name": {"name"},
    "label": {"label"},
    "data": {
        "parentId", "parents", "active", "tasks", "thumbnailId"
    },
    "data.visualParent": {"parentId"},
    "data.parents": {"parents"},
    "data.active": {"active"},
    "data.thumbnail_id": {"thumbnailId"},
    "data.entityType": {"folderType"}
}

# --- Subset entity ---
SUBSET_FIELDS_MAPPING_V3_V4 = {
    "_id": {"id"},
    "name": {"name"},
    "data.active": {"active"},
    "parent": {"folderId"}
}

# --- Version entity ---
VERSION_FIELDS_MAPPING_V3_V4 = {
    "_id": {"id"},
    "name": {"version"},
    "parent": {"productId"}
}

# --- Representation entity ---
REPRESENTATION_FIELDS_MAPPING_V3_V4 = {
    "_id": {"id"},
    "name": {"name"},
    "parent": {"versionId"},
    "context": {"context"},
    "files": {"files"},
}


def project_fields_v3_to_v4(fields, con):
    """Convert project fields from v3 to v4 structure.

    Args:
        fields (Union[Iterable(str), None]): fields to be converted.

    Returns:
        Union[Set(str), None]: Converted fields to v4 fields.
    """

    # TODO config fields
    # - config.apps
    # - config.groups
    if not fields:
        return None

    project_attribs = con.get_attributes_for_type("project")
    output = set()
    for field in fields:
        # If config is needed the rest api call must be used
        if field.startswith("config"):
            return None

        if field in PROJECT_FIELDS_MAPPING_V3_V4:
            output |= PROJECT_FIELDS_MAPPING_V3_V4[field]
            if field == "data":
                output |= {
                    "attrib.{}".format(attr)
                    for attr in project_attribs
                }

        elif field.startswith("data"):
            field_parts = field.split(".")
            field_parts.pop(0)
            data_key = ".".join(field_parts)
            if data_key in project_attribs:
                output.add("attrib.{}".format(data_key))
            else:
                output.add("data")
                print("Requested specific key from data {}".format(data_key))

        else:
            raise ValueError("Unknown field mapping for {}".format(field))

    if "name" not in output:
        output.add("name")
    return output


def _get_default_template_name(templates):
    default_template = None
    for name, template in templates.items():
        if name == "default":
            return "default"

        if default_template is None:
            default_template = name

    return default_template


def _template_replacements_to_v3(template):
    return (
        template
        .replace("{product[name]}", "{subset}")
        .replace("{product[type]}", "{family}")
    )


def _convert_template_item(template):
    # Others won't have 'directory'
    if "directory" not in template:
        return
    folder = _template_replacements_to_v3(template.pop("directory"))
    template["folder"] = folder
    template["file"] = _template_replacements_to_v3(template["file"])
    template["path"] = "/".join(
        (folder, template["file"])
    )


def _fill_template_category(templates, cat_templates, cat_key):
    default_template_name = _get_default_template_name(cat_templates)
    for template_name, cat_template in cat_templates.items():
        _convert_template_item(cat_template)
        if template_name == default_template_name:
            templates[cat_key] = cat_template
        else:
            new_name = "{}_{}".format(cat_key, template_name)
            templates["others"][new_name] = cat_template


def convert_v4_project_to_v3(project):
    """Convert Project entity data from v4 structure to v3 structure.

    Args:
        project (Dict[str, Any]): Project entity queried from v4 server.

    Returns:
        Dict[str, Any]: Project converted to v3 structure.
    """

    if not project:
        return project

    project_name = project["name"]
    output = {
        "_id": project_name,
        "name": project_name,
        "schema": CURRENT_PROJECT_SCHEMA,
        "type": "project"
    }

    data = project.get("data") or {}
    attribs = project.get("attrib") or {}
    apps_attr = attribs.pop("applications", None) or []
    applications = [
        {"name": app_name}
        for app_name in apps_attr
    ]
    data.update(attribs)
    if "tools" in data:
        data["tools_env"] = data.pop("tools")

    data["entityType"] = "Project"

    config = {}
    project_config = project.get("config")

    if project_config:
        config["apps"] = applications
        config["roots"] = project_config["roots"]

        templates = project_config["templates"]
        templates["defaults"] = templates.pop("common", None) or {}

        others_templates = templates.pop("others", None) or {}
        new_others_templates = {}
        templates["others"] = new_others_templates
        for name, template in others_templates.items():
            _convert_template_item(template)
            new_others_templates[name] = template

        for key in (
            "work",
            "publish",
            "hero"
        ):
            cat_templates = templates.pop(key)
            _fill_template_category(templates, cat_templates, key)

        delivery_templates = templates.pop("delivery", None) or {}
        new_delivery_templates = {}
        for name, delivery_template in delivery_templates.items():
            new_delivery_templates[name] = "/".join(
                (delivery_template["directory"], delivery_template["file"])
            )
        templates["delivery"] = new_delivery_templates

        config["templates"] = templates

    if "taskTypes" in project:
        task_types = project["taskTypes"]
        new_task_types = {}
        for task_type in task_types:
            name = task_type.pop("name")
            # Change 'shortName' to 'short_name'
            task_type["short_name"] = task_type.pop("shortName", None)
            new_task_types[name] = task_type

        config["tasks"] = new_task_types

    if config:
        output["config"] = config

    for data_key, key in (
        ("library_project", "library"),
        ("code", "code"),
        ("active", "active")
    ):
        if key in project:
            data[data_key] = project[key]

    if "attrib" in project:
        for key, value in project["attrib"].items():
            data[key] = value

    if data:
        output["data"] = data
    return output


def folder_fields_v3_to_v4(fields, con):
    """Convert folder fields from v3 to v4 structure.

    Args:
        fields (Union[Iterable(str), None]): fields to be converted.

    Returns:
        Union[Set(str), None]: Converted fields to v4 fields.
    """

    if not fields:
        return None

    folder_attributes = con.get_attributes_for_type("folder")
    output = set()
    for field in fields:
        if field in ("schema", "type", "parent"):
            continue

        if field in FOLDER_FIELDS_MAPPING_V3_V4:
            output |= FOLDER_FIELDS_MAPPING_V3_V4[field]
            if field == "data":
                output |= {
                    "attrib.{}".format(attr)
                    for attr in folder_attributes
                }

        elif field.startswith("data"):
            field_parts = field.split(".")
            field_parts.pop(0)
            data_key = ".".join(field_parts)
            if data_key == "label":
                output.add("name")

            elif data_key in ("icon", "color"):
                continue

            elif data_key.startswith("tasks"):
                output.add("tasks")

            elif data_key in folder_attributes:
                output.add("attrib.{}".format(data_key))

            else:
                output.add("data")
                print("Requested specific key from data {}".format(data_key))

        else:
            raise ValueError("Unknown field mapping for {}".format(field))

    if "id" not in output:
        output.add("id")
    return output


def convert_v4_tasks_to_v3(tasks):
    """Convert v4 task item to v3 task.

    Args:
        tasks (List[Dict[str, Any]]): Task entites.

    Returns:
        Dict[str, Dict[str, Any]]: Tasks in v3 variant ready for v3 asset.
    """

    output = {}
    for task in tasks:
        task_name = task["name"]
        new_task = {
            "type": task["taskType"]
        }
        output[task_name] = new_task
    return output


def convert_v4_folder_to_v3(folder, project_name):
    """Convert v4 folder to v3 asset.

    Args:
        folder (Dict[str, Any]): Folder entity data.
        project_name (str): Project name from which folder was queried.

    Returns:
        Dict[str, Any]: Converted v4 folder to v3 asset.
    """

    output = {
        "_id": folder["id"],
        "parent": project_name,
        "type": "asset",
        "schema": CURRENT_ASSET_DOC_SCHEMA
    }

    output_data = folder.get("data") or {}

    if "name" in folder:
        output["name"] = folder["name"]
        output_data["label"] = folder["name"]

    if "folderType" in folder:
        output_data["entityType"] = folder["folderType"]

    for src_key, dst_key in (
        ("parentId", "visualParent"),
        ("active", "active"),
        ("thumbnailId", "thumbnail_id"),
        ("parents", "parents"),
    ):
        if src_key in folder:
            output_data[dst_key] = folder[src_key]

    if "attrib" in folder:
        output_data.update(folder["attrib"])

    if "tools" in output_data:
        output_data["tools_env"] = output_data.pop("tools")

    if "tasks" in folder:
        output_data["tasks"] = convert_v4_tasks_to_v3(folder["tasks"])

    output["data"] = output_data

    return output


def subset_fields_v3_to_v4(fields, con):
    """Convert subset fields from v3 to v4 structure.

    Args:
        fields (Union[Iterable(str), None]): fields to be converted.

    Returns:
        Union[Set(str), None]: Converted fields to v4 fields.
    """

    if not fields:
        return None

    product_attributes = con.get_attributes_for_type("product")

    output = set()
    for field in fields:
        if field in ("schema", "type"):
            continue

        if field in SUBSET_FIELDS_MAPPING_V3_V4:
            output |= SUBSET_FIELDS_MAPPING_V3_V4[field]

        elif field == "data":
            output.add("productType")
            output.add("active")
            output |= {
                "attrib.{}".format(attr)
                for attr in product_attributes
            }

        elif field.startswith("data"):
            field_parts = field.split(".")
            field_parts.pop(0)
            data_key = ".".join(field_parts)
            if data_key in ("family", "families"):
                output.add("productType")

            elif data_key in product_attributes:
                output.add("attrib.{}".format(data_key))

            else:
                output.add("data")
                print("Requested specific key from data {}".format(data_key))

        else:
            raise ValueError("Unknown field mapping for {}".format(field))

    if "id" not in output:
        output.add("id")
    return output


def convert_v4_subset_to_v3(subset):
    output = {
        "_id": subset["id"],
        "type": "subset",
        "schema": CURRENT_SUBSET_SCHEMA
    }
    if "folderId" in subset:
        output["parent"] = subset["folderId"]

    output_data = subset.get("data") or {}

    if "name" in subset:
        output["name"] = subset["name"]

    if "active" in subset:
        output_data["active"] = subset["active"]

    if "attrib" in subset:
        attrib = subset["attrib"]
        if "productGroup" in attrib:
            attrib["subsetGroup"] = attrib.pop("productGroup")
        output_data.update(attrib)

    family = subset.get("productType")
    if family:
        output_data["family"] = family
        output_data["families"] = [family]

    output["data"] = output_data

    return output


def version_fields_v3_to_v4(fields, con):
    """Convert version fields from v3 to v4 structure.

    Args:
        fields (Union[Iterable(str), None]): fields to be converted.

    Returns:
        Union[Set(str), None]: Converted fields to v4 fields.
    """

    if not fields:
        return None

    version_attributes = con.get_attributes_for_type("version")

    output = set()
    for field in fields:
        if field in ("type", "schema", "version_id"):
            continue

        if field in VERSION_FIELDS_MAPPING_V3_V4:
            output |= VERSION_FIELDS_MAPPING_V3_V4[field]

        elif field == "data":
            output |= {
                "attrib.{}".format(attr)
                for attr in version_attributes
            }
            output |= {
                "author",
                "createdAt",
                "thumbnailId",
            }

        elif field.startswith("data"):
            field_parts = field.split(".")
            field_parts.pop(0)
            data_key = ".".join(field_parts)
            if data_key in version_attributes:
                output.add("attrib.{}".format(data_key))

            elif data_key == "thumbnail_id":
                output.add("thumbnailId")

            elif data_key == "time":
                output.add("createdAt")

            elif data_key == "author":
                output.add("author")

            elif data_key in ("tags", ):
                continue

            else:
                output.add("data")
                print("Requested specific key from data {}".format(data_key))

        else:
            raise ValueError("Unknown field mapping for {}".format(field))

    if "id" not in output:
        output.add("id")
    return output


def convert_v4_version_to_v3(version):
    """Convert v4 version entity to v4 version.

    Args:
        version (Dict[str, Any]): Queried v4 version entity.

    Returns:
        Dict[str, Any]: Conveted version entity to v3 structure.
    """

    version_num = version["version"]
    if version_num < 0:
        output = {
            "_id": version["id"],
            "type": "hero_version",
            "schema": CURRENT_HERO_VERSION_SCHEMA,
        }
        if "productId" in version:
            output["parent"] = version["productId"]

        if "data" in version:
            output["data"] = version["data"]
        return output

    output = {
        "_id": version["id"],
        "type": "version",
        "name": version_num,
        "schema": CURRENT_VERSION_SCHEMA
    }
    if "productId" in version:
        output["parent"] = version["productId"]

    output_data = version.get("data") or {}
    if "attrib" in version:
        output_data.update(version["attrib"])

    for src_key, dst_key in (
        ("active", "active"),
        ("thumbnailId", "thumbnail_id"),
        ("author", "author")
    ):
        if src_key in version:
            output_data[dst_key] = version[src_key]

    if "createdAt" in version:
        created_at = arrow.get(version["createdAt"])
        output_data["time"] = created_at.strftime("%Y%m%dT%H%M%SZ")

    output["data"] = output_data

    return output


def representation_fields_v3_to_v4(fields, con):
    """Convert representation fields from v3 to v4 structure.

    Args:
        fields (Union[Iterable(str), None]): fields to be converted.

    Returns:
        Union[Set(str), None]: Converted fields to v4 fields.
    """

    if not fields:
        return None

    representation_attributes = con.get_attributes_for_type("representation")

    output = set()
    for field in fields:
        if field in ("type", "schema"):
            continue

        if field in REPRESENTATION_FIELDS_MAPPING_V3_V4:
            output |= REPRESENTATION_FIELDS_MAPPING_V3_V4[field]

        elif field.startswith("context"):
            output.add("context")

        # TODO: 'files' can have specific attributes but the keys in v3 and v4
        #   are not the same (content is not the same)
        elif field.startswith("files"):
            output |= REPRESENTATION_FILES_FIELDS

        elif field.startswith("data"):
            output |= {
                "attrib.{}".format(attr)
                for attr in representation_attributes
            }

        else:
            raise ValueError("Unknown field mapping for {}".format(field))

    if "id" not in output:
        output.add("id")
    return output


def convert_v4_representation_to_v3(representation):
    """Convert v4 representation to v3 representation.

    Args:
        representation (Dict[str, Any]): Queried representation from v4 server.

    Returns:
        Dict[str, Any]: Converted representation to v3 structure.
    """

    output = {
        "type": "representation",
        "schema": CURRENT_REPRESENTATION_SCHEMA,
    }
    if "id" in representation:
        output["_id"] = representation["id"]

    for v3_key, v4_key in (
        ("name", "name"),
        ("parent", "versionId")
    ):
        if v4_key in representation:
            output[v3_key] = representation[v4_key]

    if "context" in representation:
        context = representation["context"]
        if isinstance(context, six.string_types):
            context = json.loads(context)

        if "asset" not in context and "folder" in context:
            _c_folder = context["folder"]
            context["asset"] = _c_folder["name"]

        elif "asset" in context and "folder" not in context:
            context["folder"] = {"name": context["asset"]}

        if "product" in context:
            _c_product = context.pop("product")
            context["family"] = _c_product["type"]
            context["subset"] = _c_product["name"]

        output["context"] = context

    if "files" in representation:
        files = representation["files"]
        new_files = []
        # From GraphQl is list
        if isinstance(files, list):
            for file_info in files:
                file_info["_id"] = file_info["id"]
                new_files.append(file_info)

        # From RestPoint is dictionary
        elif isinstance(files, dict):
            for file_id, file_info in files:
                file_info["_id"] = file_id
                new_files.append(file_info)

        for file_info in new_files:
            if not file_info.get("sites"):
                file_info["sites"] = [{
                    "name": "studio"
                }]

        output["files"] = new_files

    if representation.get("active") is False:
        output["type"] = "archived_representation"
        output["old_id"] = output["_id"]

    output_data = representation.get("data") or {}
    if "attrib" in representation:
        output_data.update(representation["attrib"])

    for key, data_key in (
        ("active", "active"),
    ):
        if key in representation:
            output_data[data_key] = representation[key]

    if "template" in output_data:
        output_data["template"] = (
            output_data["template"]
            .replace("{product[name]}", "{subset}")
            .replace("{product[type]}", "{family}")
        )

    output["data"] = output_data

    return output


def workfile_info_fields_v3_to_v4(fields):
    if not fields:
        return None

    new_fields = set()
    fields = set(fields)
    for v3_key, v4_key in (
        ("_id", "id"),
        ("files", "path"),
        ("filename", "name"),
        ("data", "data"),
    ):
        if v3_key in fields:
            new_fields.add(v4_key)

    if "parent" in fields or "task_name" in fields:
        new_fields.add("taskId")

    return new_fields


def convert_v4_workfile_info_to_v3(workfile_info, task):
    output = {
        "type": "workfile",
        "schema": CURRENT_WORKFILE_INFO_SCHEMA,
    }
    if "id" in workfile_info:
        output["_id"] = workfile_info["id"]

    if "path" in workfile_info:
        output["files"] = [workfile_info["path"]]

    if "name" in workfile_info:
        output["filename"] = workfile_info["name"]

    if "taskId" in workfile_info:
        output["task_name"] = task["name"]
        output["parent"] = task["folderId"]

    return output


def convert_create_asset_to_v4(asset, project, con):
    folder_attributes = con.get_attributes_for_type("folder")

    asset_data = asset["data"]
    parent_id = asset_data["visualParent"]

    folder = {
        "name": asset["name"],
        "parentId": parent_id,
    }
    entity_id = asset.get("_id")
    if entity_id:
        folder["id"] = entity_id

    attribs = {}
    data = {}
    for key, value in asset_data.items():
        if key in (
            "visualParent",
            "thumbnail_id",
            "parents",
            "inputLinks",
            "avalon_mongo_id",
        ):
            continue

        if key not in folder_attributes:
            data[key] = value
        elif value is not None:
            attribs[key] = value

    if attribs:
        folder["attrib"] = attribs

    if data:
        folder["data"] = data
    return folder


def convert_create_task_to_v4(task, project, con):
    if not project["taskTypes"]:
        raise ValueError(
            "Project \"{}\" does not have any task types".format(
                project["name"]))

    task_type = task["type"]
    if task_type not in project["taskTypes"]:
        task_type = tuple(project["taskTypes"].keys())[0]

    return {
        "name": task["name"],
        "taskType": task_type,
        "folderId": task["folderId"]
    }


def convert_create_subset_to_v4(subset, con):
    product_attributes = con.get_attributes_for_type("product")

    subset_data = subset["data"]
    product_type = subset_data.get("family")
    if not product_type:
        product_type = subset_data["families"][0]

    converted_product = {
        "name": subset["name"],
        "productType": product_type,
        "folderId": subset["parent"],
    }
    entity_id = subset.get("_id")
    if entity_id:
        converted_product["id"] = entity_id

    attribs = {}
    data = {}
    if "subsetGroup" in subset_data:
        subset_data["productGroup"] = subset_data.pop("subsetGroup")
    for key, value in subset_data.items():
        if key not in product_attributes:
            data[key] = value
        elif value is not None:
            attribs[key] = value

    if attribs:
        converted_product["attrib"] = attribs

    if data:
        converted_product["data"] = data

    return converted_product


def convert_create_version_to_v4(version, con):
    version_attributes = con.get_attributes_for_type("version")
    converted_version = {
        "version": version["name"],
        "productId": version["parent"],
    }
    entity_id = version.get("_id")
    if entity_id:
        converted_version["id"] = entity_id

    version_data = version["data"]
    attribs = {}
    data = {}
    for key, value in version_data.items():
        if key not in version_attributes:
            data[key] = value
        elif value is not None:
            attribs[key] = value

    if attribs:
        converted_version["attrib"] = attribs

    if data:
        converted_version["data"] = attribs

    return converted_version


def convert_create_hero_version_to_v4(hero_version, project_name, con):
    if "version_id" in hero_version:
        version_id = hero_version["version_id"]
        version = con.get_version_by_id(project_name, version_id)
        version["version"] = - version["version"]

        for auto_key in (
            "name",
            "createdAt",
            "updatedAt",
            "author",
        ):
            version.pop(auto_key, None)

        return version

    version_attributes = con.get_attributes_for_type("version")
    converted_version = {
        "version": hero_version["version"],
        "productId": hero_version["parent"],
    }
    entity_id = hero_version.get("_id")
    if entity_id:
        converted_version["id"] = entity_id

    version_data = hero_version["data"]
    attribs = {}
    data = {}
    for key, value in version_data.items():
        if key not in version_attributes:
            data[key] = value
        elif value is not None:
            attribs[key] = value

    if attribs:
        converted_version["attrib"] = attribs

    if data:
        converted_version["data"] = attribs

    return converted_version


def convert_create_representation_to_v4(representation, con):
    representation_attributes = con.get_attributes_for_type("representation")

    converted_representation = {
        "name": representation["name"],
        "versionId": representation["parent"],
    }
    entity_id = representation.get("_id")
    if entity_id:
        converted_representation["id"] = entity_id

    if representation.get("type") == "archived_representation":
        converted_representation["active"] = False

    new_files = []
    for file_item in representation["files"]:
        new_file_item = {
            key: value
            for key, value in file_item.items()
            if key in ("hash", "path", "size")
        }
        new_file_item.update({
            "id": create_entity_id(),
            "hash_type": "op3",
            "name": os.path.basename(new_file_item["path"])
        })
        new_files.append(new_file_item)

    converted_representation["files"] = new_files

    context = representation["context"]
    if "folder" not in context:
        context["folder"] = {
            "name": context.get("asset")
        }

    context["product"] = {
        "type": context.pop("family", None),
        "name": context.pop("subset", None),
    }

    attribs = {}
    data = {
        "context": context,
    }

    representation_data = representation["data"]
    representation_data["template"] = (
        representation_data["template"]
        .replace("{subset}", "{product[name]}")
        .replace("{family}", "{product[type]}")
    )

    for key, value in representation_data.items():
        if key not in representation_attributes:
            data[key] = value
        elif value is not None:
            attribs[key] = value

    if attribs:
        converted_representation["attrib"] = attribs

    if data:
        converted_representation["data"] = data

    return converted_representation


def convert_create_workfile_info_to_v4(data, project_name, con):
    folder_id = data["parent"]
    task_name = data["task_name"]
    task = con.get_task_by_name(project_name, folder_id, task_name)
    if not task:
        return None

    workfile_attributes = con.get_attributes_for_type("workfile")
    filename = data["filename"]
    possible_attribs = {
        "extension": os.path.splitext(filename)[-1]
    }
    attribs = {}
    for attr in workfile_attributes:
        if attr in possible_attribs:
            attribs[attr] = possible_attribs[attr]

    output = {
        "path": data["files"][0],
        "name": filename,
        "taskId": task["id"]
    }
    if "_id" in data:
        output["id"] = data["_id"]

    if attribs:
        output["attrib"] = attribs

    output_data = data.get("data")
    if output_data:
        output["data"] = output_data
    return output


def _from_flat_dict(data):
    output = {}
    for key, value in data.items():
        output_value = output
        subkeys = key.split(".")
        last_key = subkeys.pop(-1)
        for subkey in subkeys:
            if subkey not in output_value:
                output_value[subkey] = {}
            output_value = output_value[subkey]

        output_value[last_key] = value
    return output


def _to_flat_dict(data):
    output = {}
    flat_queue = collections.deque()
    flat_queue.append(([], data))
    while flat_queue:
        item = flat_queue.popleft()
        parent_keys, data = item
        for key, value in data.items():
            keys = list(parent_keys)
            keys.append(key)
            if isinstance(value, dict):
                flat_queue.append((keys, value))
            else:
                full_key = ".".join(keys)
                output[full_key] = value

    return output


def convert_update_folder_to_v4(project_name, asset_id, update_data, con):
    new_update_data = {}

    folder_attributes = con.get_attributes_for_type("folder")
    full_update_data = _from_flat_dict(update_data)
    data = full_update_data.get("data")

    has_new_parent = False
    has_task_changes = False
    parent_id = None
    tasks = None
    new_data = {}
    attribs = full_update_data.pop("attrib", {})
    if "type" in update_data:
        new_update_data["active"] = update_data["type"] == "asset"

    if data:
        if "thumbnail_id" in data:
            new_update_data["thumbnailId"] = data.pop("thumbnail_id")

        if "tasks" in data:
            tasks = data.pop("tasks")
            has_task_changes = True

        if "visualParent" in data:
            has_new_parent = True
            parent_id = data.pop("visualParent")

        for key, value in data.items():
            if key in folder_attributes:
                attribs[key] = value
            else:
                new_data[key] = value

    if "name" in update_data:
        new_update_data["name"] = update_data["name"]

    if "type" in update_data:
        new_type = update_data["type"]
        if new_type == "asset":
            new_update_data["active"] = True
        elif new_type == "archived_asset":
            new_update_data["active"] = False

    if has_new_parent:
        new_update_data["parentId"] = parent_id

    if new_data:
        print("Folder has new data: {}".format(new_data))
        new_update_data["data"] = new_data

    if attribs:
        new_update_data["attrib"] = attribs

    if has_task_changes:
        raise ValueError("Task changes of folder are not implemented")

    return _to_flat_dict(new_update_data)


def convert_update_subset_to_v4(project_name, subset_id, update_data, con):
    new_update_data = {}

    product_attributes = con.get_attributes_for_type("product")
    full_update_data = _from_flat_dict(update_data)
    data = full_update_data.get("data")
    new_data = {}
    attribs = full_update_data.pop("attrib", {})
    if data:
        if "family" in data:
            family = data.pop("family")
            new_update_data["productType"] = family

        if "families" in data:
            families = data.pop("families")
            if "productType" not in new_update_data:
                new_update_data["productType"] = families[0]

        if "subsetGroup" in data:
            data["productGroup"] = data.pop("subsetGroup")
        for key, value in data.items():
            if key in product_attributes:
                if value is REMOVED_VALUE:
                    value = None
                attribs[key] = value

            elif value is not REMOVED_VALUE:
                new_data[key] = value

    if "name" in update_data:
        new_update_data["name"] = update_data["name"]

    if "type" in update_data:
        new_type = update_data["type"]
        if new_type == "subset":
            new_update_data["active"] = True
        elif new_type == "archived_subset":
            new_update_data["active"] = False

    if "parent" in update_data:
        new_update_data["folderId"] = update_data["parent"]

    flat_data = _to_flat_dict(new_update_data)
    if attribs:
        flat_data["attrib"] = attribs

    if new_data:
        print("Subset has new data: {}".format(new_data))
        flat_data["data"] = new_data

    return flat_data


def convert_update_version_to_v4(project_name, version_id, update_data, con):
    new_update_data = {}

    version_attributes = con.get_attributes_for_type("version")
    full_update_data = _from_flat_dict(update_data)
    data = full_update_data.get("data")
    new_data = {}
    attribs = full_update_data.pop("attrib", {})
    if data:
        if "author" in data:
            new_update_data["author"] = data.pop("author")

        if "thumbnail_id" in data:
            new_update_data["thumbnailId"] = data.pop("thumbnail_id")

        for key, value in data.items():
            if key in version_attributes:
                if value is REMOVED_VALUE:
                    value = None
                attribs[key] = value

            elif value is not REMOVED_VALUE:
                new_data[key] = value

    if "name" in update_data:
        new_update_data["version"] = update_data["name"]

    if "type" in update_data:
        new_type = update_data["type"]
        if new_type == "version":
            new_update_data["active"] = True
        elif new_type == "archived_version":
            new_update_data["active"] = False

    if "parent" in update_data:
        new_update_data["productId"] = update_data["parent"]

    flat_data = _to_flat_dict(new_update_data)
    if attribs:
        flat_data["attrib"] = attribs

    if new_data:
        print("Version has new data: {}".format(new_data))
        flat_data["data"] = new_data
    return flat_data


def convert_update_hero_version_to_v4(
    project_name, hero_version_id, update_data, con
):
    if "version_id" not in update_data:
        return None

    version_id = update_data["version_id"]
    hero_version = con.get_hero_version_by_id(project_name, hero_version_id)
    version = con.get_version_by_id(project_name, version_id)
    version["version"] = - version["version"]
    version["id"] = hero_version_id

    for auto_key in (
        "name",
        "createdAt",
        "updatedAt",
        "author",
    ):
        version.pop(auto_key, None)

    return prepare_entity_changes(hero_version, version)


def convert_update_representation_to_v4(
    project_name, repre_id, update_data, con
):
    new_update_data = {}

    folder_attributes = con.get_attributes_for_type("folder")
    full_update_data = _from_flat_dict(update_data)
    data = full_update_data.get("data")

    new_data = {}
    attribs = full_update_data.pop("attrib", {})
    if data:
        for key, value in data.items():
            if key in folder_attributes:
                attribs[key] = value
            else:
                new_data[key] = value

    if "template" in attribs:
        attribs["template"] = (
            attribs["template"]
            .replace("{family}", "{product[type]}")
            .replace("{subset}", "{product[name]}")
        )

    if "name" in update_data:
        new_update_data["name"] = update_data["name"]

    if "type" in update_data:
        new_type = update_data["type"]
        if new_type == "representation":
            new_update_data["active"] = True
        elif new_type == "archived_representation":
            new_update_data["active"] = False

    if "parent" in update_data:
        new_update_data["versionId"] = update_data["parent"]

    if "context" in update_data:
        context = update_data["context"]
        if "folder" not in context and "asset" in context:
            context["folder"] = {"name": context.pop("asset")}

        if "family" in context or "subset" in context:
            context["product"] = {
                "name": context.pop("subset"),
                "type": context.pop("family"),
            }
        new_data["context"] = context

    if "files" in update_data:
        new_files = update_data["files"]
        if isinstance(new_files, dict):
            new_files = list(new_files.values())

        for item in new_files:
            for key in tuple(item.keys()):
                if key not in ("hash", "path", "size"):
                    item.pop(key)
            item.update({
                "id": create_entity_id(),
                "name": os.path.basename(item["path"]),
                "hash_type": "op3",
            })
        new_update_data["files"] = new_files

    flat_data = _to_flat_dict(new_update_data)
    if attribs:
        flat_data["attrib"] = attribs

    if new_data:
        print("Representation has new data: {}".format(new_data))
        flat_data["data"] = new_data

    return flat_data


def convert_update_workfile_info_to_v4(
    project_name, workfile_id, update_data, con
):
    return {
        key: value
        for key, value in update_data.items()
        if key.startswith("data")
    }
