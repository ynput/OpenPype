from openpype.pipeline.constants import AVALON_CONTAINER_ID
from pxr import Sdf

from maya import cmds


def remove_spec(spec):
    """Delete Sdf.PrimSpec or Sdf.PropertySpec

    Also see:
        https://forum.aousd.org/t/api-basics-for-designing-a-manage-edits-editor-for-usd/676/1  # noqa
        https://gist.github.com/BigRoy/4d2bf2eef6c6a83f4fda3c58db1489a5

    """
    if spec.expired:
        return

    if isinstance(spec, Sdf.PrimSpec):
        # PrimSpec
        parent = spec.nameParent
        if parent:
            view = parent.nameChildren
        else:
            # Assume PrimSpec is root prim
            view = spec.layer.rootPrims
        del view[spec.name]

    elif isinstance(spec, Sdf.PropertySpec):
        # Relationship and Attribute specs
        del spec.owner.properties[spec.name]
    else:
        raise TypeError(f"Unsupported spec type: {spec}")


def iter_ufe_usd_selection():
    for path in cmds.ls(selection=True, ufeObjects=True, long=True,
                        absoluteName=True):
        if "," not in path:
            continue

        node, ufe_path = path.split(",", 1)
        if cmds.nodeType(node) != "mayaUsdProxyShape":
            continue

        yield path


def containerise_prim(prim,
                      name,
                      namespace,
                      context,
                      loader):
    for key, value in [
        ("openpype:schema", "openpype:container-2.0"),
        ("openpype:id", AVALON_CONTAINER_ID),
        ("openpype:name", name),
        ("openpype:namespace", namespace),
        ("openpype:loader", loader),
        ("openpype:representation", context["representation"]["_id"]),
    ]:
        prim.SetCustomDataByKey(key, str(value))
