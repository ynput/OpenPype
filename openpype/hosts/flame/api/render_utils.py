import os

SHARED_PRESET_PATH = '/opt/Autodesk/shared/export/presets/file_sequence'
SHARED_PRESETS = ['Default Jpeg'] + [
    preset[:-4] for preset in os.listdir(SHARED_PRESET_PATH)]


def export_clip(export_path, clip, export_preset, **kwargs):
    import flame

    # Set exporter
    exporter = flame.PyExporter()
    exporter.foreground = True
    exporter.export_between_marks = True

    if "in_mark" not in kwargs.keys():
        exporter.export_between_marks = False

    # Duplicate the clip to avoid modifying the original clip
    duplicate_clip = flame.duplicate(clip)

    # Set export preset path
    if export_preset == 'Default Jpeg':
        # Get default export preset path
        preset_dir = flame.PyExporter.get_presets_dir(
            flame.PyExporter.PresetVisibility.Autodesk,
            flame.PyExporter.PresetType.Image_Sequence)
        export_preset_path = os.path.join(
            preset_dir, "Jpeg", "Jpeg (8-bit).xml")
    else:
        export_preset_path = os.path.join(
            SHARED_PRESET_PATH, export_preset + '.xml')

    try:
        if kwargs.get("in_mark") and kwargs.get("out_mark"):
            duplicate_clip.in_mark = int(kwargs["in_mark"])
            duplicate_clip.in_mark = int(kwargs["out_mark"])

        exporter.export(duplicate_clip, export_preset_path, export_path)
    finally:
        print('Exported: {} at {}-{}'.format(
            clip.name.get_value(),
            duplicate_clip.in_mark,
            duplicate_clip.out_mark
        ))
        flame.delete(duplicate_clip)