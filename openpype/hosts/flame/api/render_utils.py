import os

SHARED_PRESET_PATH = '/opt/Autodesk/shared/export/presets'


def export_clip(export_path, clip, export_preset, **kwargs):
    """Flame exported wrapper

    Args:
        export_path (str): exporting directory path
        clip (PyClip): flame api object
        export_preset (str): name of exporting preset xml file

    Kwargs:
        export_type (str)[optional]: name of export type folder
        thumb_frame_number (int)[optional]: source frame number
        in_mark (int)[optional]: cut in mark
        out_mark (int)[optional]: cut out mark

    Raises:
        KeyError: Missing input kwarg `thumb_frame_number`
                  in case `thumbnail` in `export_preset`
        KeyError: Missing input kwarg `export_type`
                  in case of other `export_preset` then `thumbnail`
        FileExistsError: Missing export preset in shared folder
    """
    import flame

    in_mark = out_mark = None

    # Set exporter
    exporter = flame.PyExporter()
    exporter.foreground = True
    exporter.export_between_marks = True

    # Duplicate the clip to avoid modifying the original clip
    duplicate_clip = flame.duplicate(clip)

    if export_preset == 'thumbnail':
        thumb_frame_number = kwargs.get("thumb_frame_number")
        # make sure it exists in kwargs
        if not thumb_frame_number:
            raise KeyError(
                "Missing key `thumb_frame_number` in input kwargs")

        in_mark = int(thumb_frame_number)
        out_mark = int(thumb_frame_number) + 1

        # In case Thumbnail is needed
        preset_dir = flame.PyExporter.get_presets_dir(
            flame.PyExporter.PresetVisibility.Autodesk,
            flame.PyExporter.PresetType.Image_Sequence)
        export_preset_path = os.path.join(
            preset_dir, "Jpeg", "Jpeg (8-bit).xml")

    else:
        # In case other output is needed
        # get compulsory kwargs
        export_type = kwargs.get("export_type")
        # make sure it exists in kwargs
        if not export_type:
            raise KeyError(
                "Missing key `export_type` in input kwargs")

        # create full shared preset path
        shared_preset_dir = os.path.join(
            SHARED_PRESET_PATH, export_type
        )

        # check if export preset is available in shared presets
        shared_presets = [
            preset[:-4] for preset in os.listdir(shared_preset_dir)]
        if export_preset not in shared_presets:
            raise FileExistsError(
                "Missing preset file `{}` in `{}`".format(
                    export_preset,
                    shared_preset_dir
                ))

        export_preset_path = os.path.join(
            shared_preset_dir, export_preset + '.xml')

        # check if mark in/out is set in kwargs
        if kwargs.get("in_mark") and kwargs.get("out_mark"):
            in_mark = int(kwargs["in_mark"])
            out_mark = int(kwargs["out_mark"])
        else:
            exporter.export_between_marks = False

    try:
        # set in and out marks if they are available
        if in_mark and out_mark:
            duplicate_clip.in_mark = in_mark
            duplicate_clip.out_mark = out_mark

        # export with exporter
        exporter.export(duplicate_clip, export_preset_path, export_path)
    finally:
        print('Exported: {} at {}-{}'.format(
            clip.name.get_value(),
            duplicate_clip.in_mark,
            duplicate_clip.out_mark
        ))

        # delete duplicated clip it is not needed anymore
        flame.delete(duplicate_clip)
