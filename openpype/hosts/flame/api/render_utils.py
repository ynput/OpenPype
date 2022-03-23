import os
from xml.etree import ElementTree as ET


def export_clip(export_path, clip, preset_path, **kwargs):
    """Flame exported wrapper

    Args:
        export_path (str): exporting directory path
        clip (PyClip): flame api object
        preset_path (str): full export path to xml file

    Kwargs:
        thumb_frame_number (int)[optional]: source frame number
        in_mark (int)[optional]: cut in mark
        out_mark (int)[optional]: cut out mark

    Raises:
        KeyError: Missing input kwarg `thumb_frame_number`
                  in case `thumbnail` in `export_preset`
        FileExistsError: Missing export preset in shared folder
    """
    import flame

    in_mark = out_mark = None

    # Set exporter
    exporter = flame.PyExporter()
    exporter.foreground = True
    exporter.export_between_marks = True

    if kwargs.get("thumb_frame_number"):
        thumb_frame_number = kwargs["thumb_frame_number"]
        # make sure it exists in kwargs
        if not thumb_frame_number:
            raise KeyError(
                "Missing key `thumb_frame_number` in input kwargs")

        in_mark = int(thumb_frame_number)
        out_mark = int(thumb_frame_number) + 1

    elif kwargs.get("in_mark") and kwargs.get("out_mark"):
        in_mark = int(kwargs["in_mark"])
        out_mark = int(kwargs["out_mark"])
    else:
        exporter.export_between_marks = False

    try:
        # set in and out marks if they are available
        if in_mark and out_mark:
            clip.in_mark = in_mark
            clip.out_mark = out_mark

        # export with exporter
        exporter.export(clip, preset_path, export_path)
    finally:
        print('Exported: {} at {}-{}'.format(
            clip.name.get_value(),
            clip.in_mark,
            clip.out_mark
        ))


def get_preset_path_by_xml_name(xml_preset_name):
    def _search_path(root):
        output = []
        for root, _dirs, files in os.walk(root):
            for f in files:
                if f != xml_preset_name:
                    continue
                file_path = os.path.join(root, f)
                output.append(file_path)
        return output

    def _validate_results(results):
        if results and len(results) == 1:
            return results.pop()
        elif results and len(results) > 1:
            print((
                "More matching presets for `{}`: /n"
                "{}").format(xml_preset_name, results))
            return results.pop()
        else:
            return None

    from .utils import (
        get_flame_install_root,
        get_flame_version
    )

    # get actual flame version and install path
    _version = get_flame_version()["full"]
    _install_root = get_flame_install_root()

    # search path templates
    shared_search_root = "{install_root}/shared/export/presets"
    install_search_root = (
        "{install_root}/presets/{version}/export/presets/flame")

    # fill templates
    shared_search_root = shared_search_root.format(
        install_root=_install_root
    )
    install_search_root = install_search_root.format(
        install_root=_install_root,
        version=_version
    )

    # get search results
    shared_results = _search_path(shared_search_root)
    installed_results = _search_path(install_search_root)

    # first try to return shared results
    shared_preset_path = _validate_results(shared_results)

    if shared_preset_path:
        return os.path.dirname(shared_preset_path)

    # then try installed results
    installed_preset_path = _validate_results(installed_results)

    if installed_preset_path:
        return os.path.dirname(installed_preset_path)

    # if nothing found then return False
    return False


def modify_preset_file(xml_path, staging_dir, data):
    """Modify xml preset with input data

    Args:
        xml_path (str ): path for input xml preset
        staging_dir (str): staging dir path
        data (dict): data where key is xmlTag and value as string

    Returns:
        str: _description_
    """
    # create temp path
    dirname, basename = os.path.split(xml_path)
    temp_path = os.path.join(staging_dir, basename)

    # change xml following data keys
    with open(xml_path, "r") as datafile:
        tree = ET.parse(datafile)
        for key, value in data.items():
            for element in tree.findall(".//{}".format(key)):
                element.text = str(value)
        tree.write(temp_path)

    return temp_path
