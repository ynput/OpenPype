"""Wrapper around :mod:`jsonschema`

Schemas are implicitly loaded from the /schema directory of this project.

Attributes:
    _cache: Cache of previously loaded schemas

Resources:
    http://json-schema.org/
    http://json-schema.org/latest/json-schema-core.html
    http://spacetelescope.github.io/understanding-json-schema/index.html

"""

import os
import re
import json
import logging

import jsonschema
import six

log_ = logging.getLogger(__name__)

ValidationError = jsonschema.ValidationError
SchemaError = jsonschema.SchemaError

_CACHED = False


def get_schema_version(schema_name):
    """Extract version form schema name.

    It is expected that schema name contain only major and minor version.

    Expected name should match to:
    "{name}:{type}-{major version}.{minor version}"
    - `name` - must not contain colon
    - `type` - must not contain dash
    - major and minor versions must be numbers separated by dot

    Args:
    schema_name(str): Name of schema that should be parsed.

    Returns:
    tuple: Contain two values major version as first and minor version as
    second. When schema does not match parsing regex then `(0, 0)` is
    returned.
    """
    schema_regex = re.compile(r"[^:]+:[^-]+-(\d.\d)")
    groups = schema_regex.findall(schema_name)
    if not groups:
        return 0, 0

    maj_version, min_version = groups[0].split(".")
    return int(maj_version), int(min_version)


def validate(data, schema=None):
    """Validate `data` with `schema`

    Arguments:
        data (dict): JSON-compatible data
        schema (str): DEPRECATED Name of schema. Now included in the data.

    Raises:
        ValidationError on invalid schema

    """
    if not _CACHED:
        _precache()

    root, schema = data["schema"].rsplit(":", 1)
    # assert root in (
    #     "mindbender-core",  # Backwards compatiblity
    #     "avalon-core",
    #     "pype"
    # )

    if isinstance(schema, six.string_types):
        schema = _cache[schema + ".json"]

    resolver = jsonschema.RefResolver(
        "",
        None,
        store=_cache,
        cache_remote=True
    )

    jsonschema.validate(data,
                        schema,
                        types={"array": (list, tuple)},
                        resolver=resolver)


_cache = {
    # A mock schema for docstring tests
    "_doctest.json": {
        "$schema": "http://json-schema.org/schema#",

        "title": "_doctest",
        "description": "A test schema",

        "type": "object",

        "additionalProperties": False,

        "required": ["key"],

        "properties": {
            "key": {
                "description": "A test key",
                "type": "string"
            }
        }
    }
}


def _precache():
    """Store available schemas in-memory for reduced disk access"""
    global _CACHED

    repos_root = os.environ["OPENPYPE_REPOS_ROOT"]
    schema_dir = os.path.join(repos_root, "schema")

    for schema in os.listdir(schema_dir):
        if schema.startswith(("_", ".")):
            continue
        if not schema.endswith(".json"):
            continue
        if not os.path.isfile(os.path.join(schema_dir, schema)):
            continue
        with open(os.path.join(schema_dir, schema)) as f:
            log_.debug("Installing schema '%s'.." % schema)
            _cache[schema] = json.load(f)
    _CACHED = True
