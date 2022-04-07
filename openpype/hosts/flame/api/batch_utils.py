import flame


def create_batch_group(
    name,
    frame_start,
    frame_duration,
    update_batch_group=None,
    **kwargs
):
    """Create Batch Group in active project's Desktop

    Args:
        name (str): name of batch group to be created
        frame_start (int): start frame of batch
        frame_end (int): end frame of batch
        update_batch_group (PyBatch)[optional]: batch group to update

    Return:
        PyBatch: active flame batch group
    """
    # make sure some batch obj is present
    batch_group = update_batch_group or flame.batch

    schematic_reels = kwargs.get("shematic_reels") or ['LoadedReel1']
    shelf_reels = kwargs.get("shelf_reels") or ['ShelfReel1']

    handle_start = kwargs.get("handleStart") or 0
    handle_end = kwargs.get("handleEnd") or 0

    frame_start -= handle_start
    frame_duration += handle_start + handle_end

    if not update_batch_group:
        # Create batch group with name, start_frame value, duration value,
        # set of schematic reel names, set of shelf reel names
        batch_group = batch_group.create_batch_group(
            name,
            start_frame=frame_start,
            duration=frame_duration,
            reels=schematic_reels,
            shelf_reels=shelf_reels
        )
    else:
        batch_group.name = name
        batch_group.start_frame = frame_start
        batch_group.duration = frame_duration

        # add reels to batch group
        _add_reels_to_batch_group(
            batch_group, schematic_reels, shelf_reels)

        # TODO: also update write node if there is any
        # TODO: also update loaders to start from correct frameStart

    if kwargs.get("switch_batch_tab"):
        # use this command to switch to the batch tab
        batch_group.go_to()

    return batch_group


def _add_reels_to_batch_group(batch_group, reels, shelf_reels):
    # update or create defined reels
    # helper variables
    reel_names = [
        r.name.get_value()
        for r in batch_group.reels
    ]
    shelf_reel_names = [
        r.name.get_value()
        for r in batch_group.shelf_reels
    ]
    # add schematic reels
    for _r in reels:
        if _r in reel_names:
            continue
        batch_group.create_reel(_r)

    # add shelf reels
    for _sr in shelf_reels:
        if _sr in shelf_reel_names:
            continue
        batch_group.create_shelf_reel(_sr)


def create_batch_group_conent(batch_nodes, batch_links, batch_group=None):
    """Creating batch group with links

    Args:
        batch_nodes (list of dict): each dict is node definition
        batch_links (list of dict): each dict is link definition
        batch_group (PyBatch, optional): batch group. Defaults to None.
    """
    # make sure some batch obj is present
    batch_group = batch_group or flame.batch
    all_batch_nodes = {
        b.name.get_value(): b
        for b in batch_group.nodes
    }
    created_nodes = {}
    for node in batch_nodes:
        # NOTE: node_props needs to be ideally OrederDict type
        node_id, node_type, node_props = (
            node["id"], node["type"], node["properties"])

        # get node name for checking if exists
        node_name = node_props.get("name") or node_id

        if all_batch_nodes.get(node_name):
            # update existing batch node
            batch_node = all_batch_nodes[node_name]
        else:
            # create new batch node
            batch_node = batch_group.create_node(node_type)

        # set attributes found in node props
        for key, value in node_props.items():
            if not hasattr(batch_node, key):
                continue
            setattr(batch_node, key, value)

        # add created node for possible linking
        created_nodes[node_id] = batch_node

    # link nodes to each other
    for link in batch_links:
        _from_n, _to_n = link["from_node"], link["to_node"]

        # check if all linking nodes are available
        if not all([
            created_nodes.get(_from_n["id"]),
            created_nodes.get(_to_n["id"])
        ]):
            continue

        # link nodes in defined link
        batch_group.connect_nodes(
            created_nodes[_from_n["id"]], _from_n["connector"],
            created_nodes[_to_n["id"]], _to_n["connector"]
        )

    # sort batch nodes
    batch_group.organize()
