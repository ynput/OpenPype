"""Make all paths relative."""

import bpy


if __name__ == "__main__":
    data_blocks = set(bpy.data.collections)

    for obj in bpy.data.objects:
        data_blocks.add(obj)
        # Get reference from override library.
        if obj.override_library and obj.override_library.reference:
            data_blocks.add(obj.override_library.reference)

    bpy.data.libraries.write(
        bpy.data.filepath,
        data_blocks,
        path_remap="RELATIVE_ALL",
        compress=bpy.context.preferences.filepaths.use_file_compression,
    )
