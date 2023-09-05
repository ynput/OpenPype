from collections import defaultdict

try:
    from pxr import Usd
    is_usd_lib_supported = True
except ImportError:
    is_usd_lib_supported = False


def get_usd_ids_cache(path):
    # type: (str) -> dict
    """Build a id to node mapping in a USD file.

    Nodes without IDs are ignored.

    Returns:
        dict: Mapping of id to nodes in the USD file.

    """
    if not is_usd_lib_supported:
        raise RuntimeError("No pxr.Usd python library available.")

    stage = Usd.Stage.Open(path)
    ids = {}
    for prim in stage.Traverse():
        attr = prim.GetAttribute("userProperties:cbId")
        if not attr.IsValid():
            continue
        path = str(prim.GetPath())
        value = attr.Get()
        if not value:
            continue
        ids[path] = value

    cache = defaultdict(list)
    for path, value in ids.items():
        cache[value].append(path)
    return dict(cache)
