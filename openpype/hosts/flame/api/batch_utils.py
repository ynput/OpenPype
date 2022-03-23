import flame


def create_batch(name, frame_start, frame_end, **kwargs):
    """Create Batch Group in active project's Desktop

    Args:
        name (str): name of batch group to be created
        frame_start (int): start frame of batch
        frame_end (int): end frame of batch
    """
    schematic_reels = kwargs.get("shematic_reels") or ['LoadedReel1']
    shelf_reels = kwargs.get("shelf_reels") or ['ShelfReel1']

    write_pref = kwargs["write_pref"]
    handle_start = kwargs.get("handleStart")
    handle_end = kwargs.get("handleEnd")

    if handle_start:
        frame_start -= handle_start
    if handle_end:
        frame_end += handle_end

    # Create batch group with name, start_frame value, duration value,
    # set of schematic reel names, set of shelf reel names
    flame.batch.create_batch_group(
        name,
        start_frame=frame_start,
        duration=frame_end,
        reels=schematic_reels,
        shelf_reels=shelf_reels
    )

    if kwargs.get("switch_batch_tab"):
        # use this command to switch to the batch tab
        flame.batch.go_to()

    comp_node = flame.batch.create_node("Comp")

    # TODO: convert this to iterational processing,
    #       so it could be driven from `imageio` settigns
    # create write node
    write_node = flame.batch.create_node('Write File')
    # assign attrs
    write_node.name = write_pref["name"]
    write_node.media_path = write_pref["media_path"]
    write_node.media_path_pattern = write_pref["media_path_pattern"]
    write_node.create_clip = write_pref["create_clip"]
    write_node.include_setup = write_pref["include_setup"]
    write_node.create_clip_path = write_pref["create_clip_path"]
    write_node.include_setup_path = write_pref["include_setup_path"]
    write_node.file_type = write_pref["file_type"]
    write_node.format_extension = write_pref["format_extension"]
    write_node.bit_depth = write_pref["bit_depth"]
    write_node.compress = write_pref["compress"]
    write_node.compress_mode = write_pref["compress_mode"]
    write_node.frame_index_mode = write_pref["frame_index_mode"]
    write_node.frame_padding = write_pref["frame_padding"]
    write_node.version_mode = write_pref["version_mode"]
    write_node.version_name = write_pref["version_name"]

    flame.batch.connect_nodes(comp_node, "Result", write_node, "Front")

    # sort batch nodes
    flame.batch.organize()
