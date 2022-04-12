from pprint import pprint
from openpype.lib import import_filepath
import flame


clip_path = "/Users/pype.club/pype_club_root/OP02_VFX_demo/shots/a/a0000001/publish/plate/plateMain/v007/op02vfx_a0000001_plateMain_v007_exr16fpdwaaCl.0997.exr"
clips = flame.import_clips(clip_path)

clip = clips.pop()
preset_path = "/opt/Autodesk/shared/export/presets/file_sequence/OpenEXR (16-bit fp DWAA)_custom.xml"
extension = "exr"
export_data = {
    "in_mark": 10,
    "out_mark": 15
}

util_mod = import_filepath(
    "/Users/pype.club/code/openpype/openpype/hosts/flame/api/render_utils_wip.py")

transcoder = util_mod.BackburnerTranscoder(
    clip, preset_path, extension, **export_data
)
data_out = transcoder.export()

pprint(data_out)
