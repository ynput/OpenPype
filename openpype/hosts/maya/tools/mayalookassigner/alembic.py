# -*- coding: utf-8 -*-
"""Tools for loading looks to vray proxies."""
import os
from collections import defaultdict
import logging

import six

# NOTE hornet update for alembic module clash in python 2.7
# import alembic.Abc
import alembic as alembic
# END



log = logging.getLogger(__name__)


def get_alembic_paths_by_property(filename, attr, verbose=False):
    # type: (str, str, bool) -> dict
    """Return attribute value per objects in the Alembic file.

    Reads an Alembic archive hierarchy and retrieves the
    value from the `attr` properties on the objects.

    Args:
        filename (str): Full path to Alembic archive to read.
        attr (str): Id attribute.
        verbose (bool): Whether to verbosely log missing attributes.

    Returns:
        dict: Mapping of node full path with its id

    """
    # Normalize alembic path
    filename = os.path.normpath(filename)
    filename = filename.replace("\\", "/")
    filename = str(filename)  # path must be string

    try:
        archive = alembic.Abc.IArchive(filename)
    except RuntimeError:
        # invalid alembic file - probably vrmesh
        log.warning("{} is not an alembic file".format(filename))
        return {}
    root = archive.getTop()

    iterator = list(root.children)
    obj_ids = {}

    for obj in iterator:
        name = obj.getFullName()

        # include children for coming iterations
        iterator.extend(obj.children)

        props = obj.getProperties()
        if props.getNumProperties() == 0:
            # Skip those without properties, e.g. '/materials' in a gpuCache
            continue

        # THe custom attribute is under the properties' first container under
        # the ".arbGeomParams"
        prop = props.getProperty(0)  # get base property

        _property = None
        try:
            geo_params = prop.getProperty('.arbGeomParams')
            _property = geo_params.getProperty(attr)
        except KeyError:
            if verbose:
                log.debug("Missing attr on: {0}".format(name))
            continue

        if not _property.isConstant():
            log.warning("Id not constant on: {0}".format(name))

        # Get first value sample
        value = _property.getValue()[0]

        obj_ids[name] = value

    return obj_ids


def get_alembic_ids_cache(path):
    # type: (str) -> dict
    """Build a id to node mapping in Alembic file.

    Nodes without IDs are ignored.

    Returns:
        dict: Mapping of id to nodes in the Alembic.

    """
    node_ids = get_alembic_paths_by_property(path, attr="cbId")
    id_nodes = defaultdict(list)
    for node, _id in six.iteritems(node_ids):
        id_nodes[_id].append(node)

    return dict(six.iteritems(id_nodes))
