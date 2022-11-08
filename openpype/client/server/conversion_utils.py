import datetime
import collections

from openpype.client.operations_base import REMOVED_VALUE
from .constants import (
    DEFAULT_V3_FOLDER_FIELDS,
    FOLDER_ATTRIBS,
    FOLDER_ATTRIBS_FIELDS,

    SUBSET_ATTRIBS,

    VERSION_ATTRIBS_FIELDS,

    REPRESENTATION_ATTRIBS_FIELDS,
    REPRESENTATION_FILES_FIELDS,
)
from .utils import create_entity_id

# --- Project entity ---
PROJECT_FIELDS_MAPPING_V3_V4 = {
    "_id": {"name"},
    "name": {"name"},
    "data": {"data", "attrib", "code"},
    "data.library_project": {"library"},
    "data.code": {"code"},
    "data.active": {"active"},
}

# TODO this should not be hardcoded but received from server!!!
# --- Folder entity ---
FOLDER_FIELDS_MAPPING_V3_V4 = {
    "_id": {"id"},
    "name": {"name"},
    "label": {"name"},
    "data": {
        "parentId", "parents", "active", "tasks", "thumbnailId"
    } | FOLDER_ATTRIBS_FIELDS,
    "data.visualParent": {"parentId"},
    "data.parents": {"parents"},
    "data.active": {"active"},
    "data.thumbnail_id": {"thumbnailId"}
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
    "parent": {"subsetId"}
}

# --- Representation entity ---
REPRESENTATION_FIELDS_MAPPING_V3_V4 = {
    "_id": {"id"},
    "name": {"name"},
    "parent": {"versionId"},
    "context": {"context"},
    "files": {"files"},
}


def project_fields_v3_to_v4(fields):
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

    output = set()
    for field in fields:
        # If config is needed the rest api call must be used
        if field.startswith("config"):
            return None

        if field in PROJECT_FIELDS_MAPPING_V3_V4:
            output |= PROJECT_FIELDS_MAPPING_V3_V4[field]

        elif field.startswith("data"):
            new_field = "attrib" + field[4:]
            output.add(new_field)

        else:
            raise ValueError("Unknown field mapping for {}".format(field))

    if "name" not in output:
        output.add("name")
    return output


def _get_default_template_name(templates):
    default_template = None
    for template in templates:
        if template["name"] == "default":
            return "default"

        if default_template is None:
            default_template = template["name"]

    return default_template


def _convert_template_item(template):
    template_name = template.pop("name")
    template["folder"] = template.pop("directory")
    template["path"] = "/".join(
        (template["folder"], template["file"])
    )
    return template_name


def _fill_template_category(templates, cat_templates, cat_key):
    default_template_name = _get_default_template_name(cat_templates)
    for cat_template in cat_templates:
        template_name = _convert_template_item(cat_template)
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
        "schema": "openpype:project-3.0"
    }
    config = {}
    project_config = project.get("config")
    if project_config:
        config["apps"] = []

        roots = {}
        config["roots"] = roots
        for root in project_config["roots"]:
            name = root.pop("name")
            roots[name] = root

        templates = project_config["templates"]
        config["templates"] = templates

        others_templates = templates.pop("others")
        new_others_templates = {}
        templates["others"] = new_others_templates
        for template in others_templates:
            name = _convert_template_item(template)
            new_others_templates[name] = template

        for key in (
            "work",
            "publish",
            "hero"
        ):
            cat_templates = templates.pop(key)
            _fill_template_category(templates, cat_templates, key)

        delivery_templates = templates.pop("delivery")
        new_delivery_templates = {}
        templates["delivery"] = new_delivery_templates
        for delivery_template in delivery_templates:
            name = delivery_template["name"]
            new_delivery_templates[name] = "/".join(
                (delivery_template["directory"], delivery_template["file"])
            )

    if "taskTypes" in project:
        config["tasks"] = project["taskTypes"]

    if config:
        output["config"] = config

    data = project.get("data") or {}

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


def folder_fields_v3_to_v4(fields):
    """Convert folder fields from v3 to v4 structure.

    Args:
        fields (Union[Iterable(str), None]): fields to be converted.

    Returns:
        Union[Set(str), None]: Converted fields to v4 fields.
    """

    if not fields:
        return set(DEFAULT_V3_FOLDER_FIELDS)

    output = set()
    for field in fields:
        if field in ("schema", "type", "parent"):
            continue

        if field in FOLDER_FIELDS_MAPPING_V3_V4:
            output |= FOLDER_FIELDS_MAPPING_V3_V4[field]

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
            elif data_key in FOLDER_ATTRIBS:
                new_field = "attrib" + field[4:]
                output.add(new_field)
            else:
                print(data_key)
                raise ValueError("Can't query data for field {}".format(field))

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
        "schema": "openpype:asset-3.0"
    }

    output_data = folder.get("data") or {}

    if "name" in folder:
        output["name"] = folder["name"]
        output_data["label"] = folder["name"]

    for data_key, key in (
        ("visualParent", "parentId"),
        ("active", "active"),
        ("thumbnail_id", "thumbnailId")
    ):
        if key not in folder:
            continue

        output_data[data_key] = folder[key]

    if "attrib" in folder:
        output_data.update(folder["attrib"])

    if "tasks" in folder:
        if output_data is None:
            output_data = {}
        output_data["tasks"] = convert_v4_tasks_to_v3(folder["tasks"])

    if "parents" in folder:
        output_data["parents"] = folder["parents"]

    output["data"] = output_data

    return output


def subset_fields_v3_to_v4(fields):
    """Convert subset fields from v3 to v4 structure.

    Args:
        fields (Union[Iterable(str), None]): fields to be converted.

    Returns:
        Union[Set(str), None]: Converted fields to v4 fields.
    """

    if not fields:
        return None

    output = set()
    for field in fields:
        if field in ("schema", "type"):
            continue

        if field in SUBSET_FIELDS_MAPPING_V3_V4:
            output |= SUBSET_FIELDS_MAPPING_V3_V4[field]

        elif field == "data":
            output.add("family")
            output |= SUBSET_ATTRIBS

        elif field.startswith("data"):
            field_parts = field.split(".")
            field_parts.pop(0)
            data_key = ".".join(field_parts)
            if data_key == "subsetGroup":
                output.add("attrib.subsetGroup")

            elif data_key in ("family", "families"):
                output.add("family")

            else:
                print(data_key)
                raise ValueError("Can't query data for field {}".format(field))

        else:
            raise ValueError("Unknown field mapping for {}".format(field))

    if "id" not in output:
        output.add("id")
    return output


def convert_v4_subset_to_v3(subset):
    output = {
        "_id": subset["id"],
        "type": "subset",
        "schema": "openpype:subset-3.0"
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
        output_data.update(attrib)

    family = subset.get("family")
    if family:
        output_data["family"] = family
        output_data["families"] = [family]

    output["data"] = output_data

    return output


def version_fields_v3_to_v4(fields):
    """Convert version fields from v3 to v4 structure.

    Args:
        fields (Union[Iterable(str), None]): fields to be converted.

    Returns:
        Union[Set(str), None]: Converted fields to v4 fields.
    """

    if not fields:
        return None

    output = set()
    for field in fields:
        if field in ("type", "schema", "version_id"):
            continue

        if field in VERSION_FIELDS_MAPPING_V3_V4:
            output |= VERSION_FIELDS_MAPPING_V3_V4[field]

        elif field == "data":
            output |= VERSION_ATTRIBS_FIELDS
            output |= {
                "author",
                "createdAt",
                "thumbnailId",
            }

        elif field.startswith("data"):
            field_parts = field.split(".")
            field_parts.pop(0)
            data_key = ".".join(field_parts)
            if data_key == "thumbnail_id":
                output.add("thumbnailId")

            elif data_key == "time":
                output.add("createdAt")

            elif data_key == "author":
                output.add("author")

            elif data_key in ("tags", ):
                continue

            else:
                print(data_key)
                raise ValueError("Can't query data for field {}".format(field))

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
    doc_type = "version"
    schema = "openpype:version-3.0"
    if version_num < 0:
        doc_type = "hero_version"
        schema = "openpype:hero_version-1.0"

    output = {
        "_id": version["id"],
        "type": doc_type,
        "name": version_num,
        "schema": schema
    }
    if "subsetId" in version:
        output["parent"] = version["subsetId"]

    output_data = version.get("data") or {}
    if "attrib" in version:
        output_data.update(version["attrib"])

    for key, data_key in (
        ("active", "active"),
        ("thumbnailId", "thumbnail_id"),
        ("author", "author")
    ):
        if key in version:
            output_data[data_key] = version[key]

    if "createdAt" in version:
        # TODO probably will need a conversion?
        created_at = datetime.datetime.fromtimestamp(version["createdAt"])
        output_data["time"] = created_at.strftime("%Y%m%dT%H%M%SZ")

    output["data"] = output_data

    return output


def representation_fields_v3_to_v4(fields):
    """Convert representation fields from v3 to v4 structure.

    Args:
        fields (Union[Iterable(str), None]): fields to be converted.

    Returns:
        Union[Set(str), None]: Converted fields to v4 fields.
    """

    if not fields:
        return None

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
            fields |= REPRESENTATION_ATTRIBS_FIELDS

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
        "_id": representation["id"],
        "type": "representation",
        "schema": "openpype:representation-2.0",
    }
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

        if not new_files:
            new_files.append({
                "name": "studio"
            })
        output["files"] = new_files

    output_data = representation.get("data") or {}
    if "attrib" in representation:
        output_data.update(representation["attrib"])

    for key, data_key in (
        ("active", "active"),
    ):
        if key in representation:
            output_data[data_key] = representation[key]

    output["data"] = output_data

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
    subset_attributes = con.get_attributes_for_type("subset")

    subset_data = subset["data"]
    family = subset_data.get("family")
    if not family:
        family = subset_data["families"][0]

    converted_subset = {
        "name": subset["name"],
        "family": family,
        "folderId": subset["parent"],
    }
    entity_id = subset.get("_id")
    if entity_id:
        converted_subset["id"] = entity_id

    attribs = {}
    data = {}
    for key, value in subset_data.items():
        if key not in subset_attributes:
            data[key] = value
        elif value is not None:
            attribs[key] = value

    if attribs:
        converted_subset["attrib"] = attribs

    if data:
        converted_subset["data"] = data

    return converted_subset


def convert_create_version_to_v4(version, con):
    version_attributes = con.get_attributes_for_type("version")
    converted_version = {
        "version": version["name"],
        "subsetId": version["parent"],
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


def convert_create_representation_to_v4(representation, con):
    representation_attributes = con.get_attributes_for_type("representation")

    converted_representation = {
        "name": representation["name"],
        "versionId": representation["parent"],
    }
    entity_id = representation.get("_id")
    if entity_id:
        converted_representation["id"] = entity_id

    new_files = {}
    for file_item in representation["files"]:
        new_file_item = {
            key: value
            for key, value in file_item.items()
            if key != "_id"
        }
        file_item_id = create_entity_id()
        new_files[file_item_id] = new_file_item

    attribs = {}
    data = {
        "files": new_files,
        "context": representation["context"]
    }

    representation_data = representation["data"]

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


def _from_flat_dict(data):
    output = {}
    for key, value in data.items():
        output_value = output
        for subkey in key.split("."):
            if subkey not in output_value:
                output_value[subkey] = {}
            output_value = output_value[subkey]

        output_value[subkey] = value
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


def convert_update_subset_to_v4(project_name, subset_id, update_data, con):
    new_update_data = {}

    subset_attributes = con.get_attributes_for_type("subset")
    full_update_data = _from_flat_dict(update_data)
    data = full_update_data.get("data")
    new_data = {}
    attribs = {}
    if data:
        if "family" in data:
            family = data.pop("family")
            new_update_data["family"] = family

        if "families" in data:
            families = data.pop("families")
            if "family" not in new_update_data:
                new_update_data["family"] = families[0]

        for key, value in data.items():
            if key in subset_attributes:
                if value is REMOVED_VALUE:
                    value = None
                attribs[key] = value

            elif value is not REMOVED_VALUE:
                new_data[key] = value

    if attribs:
        new_update_data["attribs"] = attribs

    if new_data:
        print("Subset has new data: {}".format(new_data))
        new_update_data["data"] = new_data

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

    return _to_flat_dict(new_update_data)


def convert_update_version_to_v4(project_name, version_id, update_data, con):
    new_update_data = {}

    version_attributes = con.get_attributes_for_type("version")
    full_update_data = _from_flat_dict(update_data)
    data = full_update_data.get("data")
    new_data = {}
    attribs = {}
    if data:
        if "author" in data:
            new_update_data["author"] = data.pop("author")

        if "thumbnail_id" in data:
            data.pop("thumbnail_id")

        for key, value in data.items():
            if key in version_attributes:
                if value is REMOVED_VALUE:
                    value = None
                attribs[key] = value

            elif value is not REMOVED_VALUE:
                new_data[key] = value

    if attribs:
        new_update_data["attribs"] = attribs

    if new_data:
        print("Version has new data: {}".format(new_data))
        new_update_data["data"] = new_data

    if "name" in update_data:
        new_update_data["version"] = update_data["name"]

    if "type" in update_data:
        new_type = update_data["type"]
        if new_type == "version":
            new_update_data["active"] = True
        elif new_type == "archived_version":
            new_update_data["active"] = False

    if "parent" in update_data:
        new_update_data["subsetId"] = update_data["parent"]

    return _to_flat_dict(new_update_data)


def convert_update_representation_to_v4(
    project_name, repre_id, update_data, con
):
    new_update_data = {}

    folder_attributes = con.get_attributes_for_type("folder")
    full_update_data = _from_flat_dict(update_data)
    data = full_update_data.get("data")

    new_data = {}
    attribs = {}
    if data:
        for key, value in data.items():
            if key in folder_attributes:
                attribs[key] = value
            else:
                new_data[key] = value

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

    if "context" in update_data or "files" in update_data:
        new_data["context"] = update_data["context"]
        new_files = update_data["files"]
        if isinstance(new_files, list):
            _new_files = {}
            for file_item in new_files:
                _file_item = {
                    key: value
                    for key, value in file_item.items()
                    if key != "_id"
                }
                file_item_id = create_entity_id()
                _new_files[file_item_id] = _file_item
            new_files = _new_files
        new_data["files"] = new_files

    if new_data:
        print("Representation has new data: {}".format(new_data))
        new_update_data["data"] = new_data

    return _to_flat_dict(new_update_data)
