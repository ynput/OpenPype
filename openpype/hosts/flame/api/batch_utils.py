import flame


def create_batch(name, frame_start, frame_end, **kwargs):
    schematicReels = ['LoadedReel1']
    shelfReels = ['ShelfReel1']

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
        reels=schematicReels,
        shelf_reels=shelfReels
    )

    if kwargs.get("switch_batch_tab"):
        # use this command to switch to the batch tab
        flame.batch.go_to()

    comp = flame.batch.create_node("Comp")
    writeFile = flame.batch.create_node("Write File")

    # connect nodes
    flame.batch.connect_nodes(comp, "Result", writeFile, "Front")

    # sort batch nodes
    flame.batch.organize()
