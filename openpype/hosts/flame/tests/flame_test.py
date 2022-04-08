from openpype.lib import import_filepath

plugin = import_filepath(
    "/Users/pype.club/code/openpype/openpype/hosts/flame/api/test_plugin.py")

openclip_file_path = "/Users/pype.club/FLAME_STORAGE/test_shot_fps_float/test.clip"
# feed_datas = [
#     {
#         "path": "/Users/pype.club/pype_club_root/OP02_VFX_demo/shots/a/a0000001/publish/plate/plateMain/v007/op02vfx_a0000001_plateMain_v007_exr16fpdwaaCl.0997.exr",
#         "version": "v007"
#     },
#     {
#         "path": "/Users/pype.club/pype_club_root/OP02_VFX_demo/shots/a/a0000001/publish/plate/plateMain/v008/op02vfx_a0000001_plateMain_v008_exr16fpdwaaCl.0997.exr",
#         "version": "v008"
#     }
# ]

feed_datas = [
    {
        "path": "/Users/pype.club/FLAME_STORAGE/test_shot_fps_float/v001/file_name_v001.1001.exr",
        "version": "v001"
    },
    {
        "path": "/Users/pype.club/FLAME_STORAGE/test_shot_fps_float/v002/file_name_v002.1001.exr",
        "version": "v002"
    }
]
for feed_data in feed_datas:
    oclip = plugin.OpenClipSolver(openclip_file_path, feed_data)
    oclip.make()
