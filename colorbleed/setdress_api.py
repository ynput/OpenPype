import logging
import json
import os

import contextlib
import copy

from maya import cmds

import avalon.io as io
from avalon.maya.lib import unique_namespace

log = logging.getLogger("PackageLoader")


def matrix_equals(a, b, tolerance=1e-10):
    """Compares two matrices with an imperfection tolerance"""
    if not all(abs(x - y) < tolerance for x, y in zip(a, b)):
        return False
    return True


def to_namespace(node, namespace):
    """Return node name as if it's inside the namespace.

    Args:
        node (str): Node name
        namespace (str): Namespace

    Returns:
        str: The node in the namespace.

    """
    namespace_prefix = "|{}:".format(namespace)
    node = namespace_prefix.join(node.split("|"))
    return node


@contextlib.contextmanager
def namespaced(namespace, new=True):
    """Work inside namespace during context

    Args:
        new (bool): When enabled this will rename the namespace to a unique
            namespace if the input namespace already exists.

    Yields:
        str: The namespace that is used during the context

    """
    original = cmds.namespaceInfo(cur=True)
    if new:
        namespace = unique_namespace(namespace)
        cmds.namespace(add=namespace)

    try:
        cmds.namespace(set=namespace)
        yield namespace
    finally:
        cmds.namespace(set=original)


def load_package(filepath, name, namespace=None):
    """Load a package that was gathered elsewhere.

    A package is a group of published instances, possibly with additional data
    in a hierarchy.

    """

    from avalon.tools.cbloader import lib

    if namespace is None:
        # Define a unique namespace for the package
        namespace = os.path.basename(filepath).split(".")[0]
        unique_namespace(namespace)
    assert isinstance(namespace, basestring)

    # Load the setdress package data
    with open(filepath, "r") as fp:
        data = json.load(fp)

    # Load the setdress alembic hierarchy
    #   We import this into the namespace in which we'll load the package's
    #   instances into afterwards.
    alembic = filepath.replace(".json", ".abc")
    hierarchy = cmds.file(alembic,
                          reference=True,
                          namespace=namespace,
                          returnNewNodes=True,
                          groupReference=True,
                          groupName="{}:{}".format(namespace, name),
                          typ="Alembic")

    containers = []
    for representation_id, instances in data.items():

        # Find the compatible loaders
        loaders = list(lib.iter_loaders(representation_id))

        for instance in instances:
            container = _add(instance, representation_id, loaders, name,
                             namespace)
            containers.append(container)

    # TODO: Do we want to cripple? Or do we want to add a 'parent' parameter?
    # Cripple the original avalon containers so they don't show up in the
    # manager
    # for container in containers:
    #     cmds.setAttr("%s.id" % container,
    #                  "colorbleed.setdress.container",
    #                  type="string")

    # TODO: Lock all loaded nodes
    #   This is to ensure the hierarchy remains unaltered by the artists
    # for node in nodes:
    #      cmds.lockNode(node, lock=True)

    return containers + hierarchy


def _add(instance, representation_id, loaders, name, namespace):
    """Add an item from the package

    Args:
        instance (dict):
        representation_id (str):
        loaders (list):
        namespace (str):

    Returns:
        str: The created Avalon container.

    """

    import avalon.api as api
    from colorbleed.maya.lib import get_container_transforms

    # Process within the namespace
    with namespaced(namespace, new=False) as namespace:

        # Get the used loader
        Loader = next((x for x in loaders if
                       x.__name__ == instance['loader']),
                      None)

        if Loader is None:
            log.warning("Loader is missing: %s. Skipping %s",
                        instance['loader'], instance)
            raise RuntimeError("Loader is missing.")

        container = api.load(Loader,
                             representation_id,
                             namespace=instance['namespace'])

        # Get the root from the loaded container
        root = get_container_transforms({"objectName": container},
                                        root=True)

        # Apply matrix to root node (if any matrix edits)
        matrix = instance.get("matrix", None)
        if matrix:
            cmds.xform(root, objectSpace=True, matrix=matrix)

        # Parent into the setdress hierarchy
        # Namespace is missing from parent node(s), add namespace
        # manually
        parent_grp = instance["parent"]
        parent_grp = "{}:{}|".format(namespace, name) + to_namespace(parent_grp, namespace)

        cmds.parent(root, parent_grp, relative=True)

        return container


# Store root nodes based on representation and namespace
def _instances_by_namespace(data):
    """Rebuild instance data so we can look it up by namespace.

    Note that the `representation` is added into the instance's
    data with a `representation` key.

    Args:
        data (dict): scene build data

    Returns:
        dict

    """
    result = {}
    # Add new assets
    for representation_id, instances in data.items():

        # Ensure we leave the source data unaltered
        instances = copy.deepcopy(instances)
        for instance in instances:
            instance['representation'] = representation_id
            result[instance['namespace']] = instance

    return result


def get_contained_containers(container):
    """Get the Avalon containers in this container
    
    Args:
        container (dict): The container dict.
        
    Returns:
        list: A list of member container dictionaries.
        
    """

    import avalon.schema
    from avalon.maya.pipeline import parse_container

    # Get avalon containers in this package setdress container
    containers = []
    members = cmds.sets(container['objectName'], query=True)
    for node in cmds.ls(members, type="objectSet"):
        try:
            member_container = parse_container(node)
            containers.append(member_container)
        except avalon.schema.ValidationError:
            pass

    return containers


def update_package_version(container, version):
    """Update package by version number"""

    # Versioning (from `core.maya.pipeline`)
    current_representation = io.find_one({
        "_id": io.ObjectId(container["representation"])
    })

    assert current_representation is not None, "This is a bug"

    version_, subset, asset, project = io.parenthood(current_representation)

    if version == -1:
        new_version = io.find_one({
            "type": "version",
            "parent": subset["_id"]
        }, sort=[("name", -1)])
    else:
        new_version = io.find_one({
            "type": "version",
            "parent": subset["_id"],
            "name": version,
        })

    assert new_version is not None, "This is a bug"

    # Get the new representation (new file)
    new_representation = io.find_one({
        "type": "representation",
        "parent": new_version["_id"],
        "name": current_representation["name"]
    })

    update_package(container, new_representation)


def update_package(set_container, representation):
    """Update any matrix changes in the scene based on the new data

    Args:
        set_container (dict): container data from `ls()`
        version (int): version number of the subset

    """

    import avalon.api

    # Load the original package data
    current_representation = io.find_one({
        "_id": io.ObjectId(set_container['representation']),
        "type": "representation"
    })

    current_file = avalon.api.get_representation_path(current_representation)
    assert current_file.endswith(".json")
    with open(current_file, "r") as fp:
        current_data = json.load(fp)

    # Load the new package data
    new_file = avalon.api.get_representation_path(representation)
    assert new_file.endswith(".json")
    with open(new_file, "r") as fp:
        new_data = json.load(fp)

    # Update scene content
    containers = get_contained_containers(set_container)
    update_scene(set_container, containers, current_data, new_data, new_file)

    # TODO: This should be handled by the pipeline itself
    cmds.setAttr(set_container['objectName'] + ".representation",
                 str(representation['_id']), type="string")


def update_scene(set_container, containers, current_data, new_data, new_file):
    """Updates the hierarchy, assets and their matrix

    Updates the following withing the scene:
        * Setdress hierarchy alembic
        * Matrix
        * Parenting
        * Representations

    It removes any assets which are not present in the new build data

    Args:
        set_container (dict): the setdress container of the scene
        containers (list): the list of containers under the setdress container
        current_data (dict): the current build data of the setdress
        new_data (dict): the new build data of the setdres

    Returns:
        processed_containers (list): all new and updated containers
    """

    from colorbleed.maya.lib import DEFAULT_MATRIX, get_container_transforms
    from avalon.tools.cbloader import lib
    from avalon import api

    set_namespace = set_container['namespace']

    # Update the setdress hierarchy alembic
    set_root = get_container_transforms(set_container, root=True)
    set_hierarchy_root = cmds.listRelatives(set_root, fullPath=True)[0]
    set_hierarchy_reference = cmds.referenceQuery(set_hierarchy_root,
                                                  referenceNode=True)
    new_alembic = new_file.replace(".json", ".abc")
    assert os.path.exists(new_alembic), "%s does not exist." % new_alembic
    cmds.file(new_alembic,
              loadReference=set_hierarchy_reference,
              type="Alembic")

    identity = DEFAULT_MATRIX[:]

    processed_namespaces = set()
    processed_containers = list()

    new_lookup = _instances_by_namespace(new_data)
    old_lookup = _instances_by_namespace(current_data)
    for container in containers:
        container_ns = container['namespace']

        if container_ns in new_lookup:
            root = get_container_transforms(container, root=True)
            if not root:
                log.error("Can't find root for %s", container['objectName'])
                continue

            old_instance = old_lookup.get(container_ns, {})
            new_instance = new_lookup[container_ns]

            # Update the matrix
            # check matrix against old_data matrix to find local overrides
            current_matrix = cmds.xform(root,
                                        query=True,
                                        matrix=True,
                                        objectSpace=True)

            original_matrix = old_instance.get("matrix", identity)
            has_matrix_override = not matrix_equals(current_matrix,
                                                    original_matrix)

            if has_matrix_override:
                log.warning("Matrix override preserved on %s", container_ns)

            else:
                new_matrix = new_instance.get("matrix", identity)
                cmds.xform(root, matrix=new_matrix, objectSpace=True)

            # Update the parenting
            if old_instance.get("parent", None) != new_instance["parent"]:

                parent = to_namespace(new_instance['parent'], set_namespace)
                if not cmds.objExists(parent):
                    log.error("Can't find parent %s", parent)
                    continue

                # Set the new parent
                cmds.lockNode(root, lock=False)
                root = cmds.parent(root, parent, relative=True)
                cmds.lockNode(root, lock=True)

            # TODO: Update the representation with the new loader
            if new_instance['loader'] != old_instance['loader']:
                log.error("Switching loader between updates is not supported.")
                continue

            # TODO: Update the representation with the new loader
            representation_new = new_instance['representation']
            representation_old = old_instance['representation']
            if representation_new != representation_old:

                print "namespace :", container_ns

                new = io.find_one({"_id": io.ObjectId(representation_new)})
                old = io.find_one({"_id": io.ObjectId(representation_old)})

                is_valid = compare_representations(old=old, new=new)
                if not is_valid:
                    continue

                new_version = new["context"]["version"]

                api.update(container, version=new_version)

        else:
            # Remove this container because it's not in the new data
            log.warning("Removing content: %s", container_ns)
            api.remove(container)

        processed_namespaces.add(container_ns)
        processed_containers.append(container['objectName'])

    # Add new assets
    for representation_id, instances in new_data.items():

        # Find the compatible loaders
        loaders = list(lib.iter_loaders(representation_id))

        for instance in instances:

            # Already processed in update functionality
            if instance['namespace'] in processed_namespaces:
                continue

            container = _add(instance,
                             representation_id,
                             loaders,
                             set_container['name'],
                             set_container['namespace'])

            # Add to the setdress container
            cmds.sets(container,
                      addElement=set_container['objectName'])

            processed_containers.append(container)

    return processed_containers


def compare_representations(old, new):
    """Check if the old representation given can be updated

    Due to limitations of the `api.update` function we cannot allow
    differences in the following data:

    * Representation name (extension)
    * Asset name
    * Subset name (variation)

    If any of those data values differs, the function will raise an
    RuntimeError

    Args:
        old(dict): representation data from the database
        new(dict): representation data from the database

    Returns:
        bool: False if the representation is not invalid else True
    """

    if new["name"] != old["name"]:
        log.error("Cannot switch extensions")
        return False

    new_context = new["context"]
    old_context = old["context"]

    if new_context["asset"] != old_context["asset"]:
        log.error("Changing assets between updates is "
                  "not supported.")
        return False

    if new_context["subset"] != old_context["subset"]:
        log.error("Changing subsets between updates is "
                  "not supported.")
        return False

    return True
