import bpy


if __name__ == "__main__":
    bpy.ops.file.make_paths_relative()

    bpy.ops.wm.save_mainfile()
