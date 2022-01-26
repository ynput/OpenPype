import os
import sys
import traceback
from xml.etree import ElementTree as ET
import shutil
import openpype.lib
import six


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


def get_open_clip(
        name,  openclip_file_path, feed_data):

    # establish media script path and test it
    media_script_path = "/opt/Autodesk/mio/current/dl_get_media_info"
    if not os.path.isfile(media_script_path):
        raise IOError("Media Scirpt does not exist: `{}`".format(
            media_script_path))

    # openclip will be updated via temp.clip file
    tmp_name = "_tmp.clip"

    # new feed variables:
    feed_path = feed_data["path"]
    feed_version_name = feed_data["version"]
    feed_colorspace = feed_data.get("colorspace")

    # derivate other feed variables
    feed_basename = os.path.basename(feed_path)
    feed_dir = os.path.dirname(feed_path)

    clip_uploaded = False
    create_new_clip = False

    feed_ext = os.path.splitext(feed_basename)[1][1:].lower()

    if not os.path.isfile(openclip_file_path):
        # openclip does not exist yet and will be created
        feed_path = os.path.abspath(feed_path)
        tmp_file = openclip_file_path
        create_new_clip = True
        clip_uploaded = True
    else:
        # output a temp file
        tmp_file = os.path.join(feed_dir, tmp_name)
        if os.path.isfile(tmp_file):
            os.remove(tmp_file)

    print("Temp File: {}".format(tmp_file))

    # Create cmd arguments for gettig xml file info file
    cmd_args = [
        media_script_path,
        "-e", feed_ext,
        "-o", tmp_file,
        feed_dir
    ]

    # execute creation of clip xml template data
    try:
        openpype.lib.run_subprocess(cmd_args)
    except TypeError:
        print("Error createing tmp_file")
        six.reraise(*sys.exc_info())

    # Check media type for valid extension
    try:
        tmp_xml = ET.parse(tmp_file)
        print(tmp_xml)
    except:
        print("XML is probably empty.")
        print('{}'.format(traceback.print_exc()))
        if os.path.isfile(tmp_file):
            os.remove(tmp_file)
        return False

    for newTrack in tmp_xml.iter('track'):
        new_path_obj = newTrack.find("feeds/feed/spans/span/path")
        new_path = new_path_obj.text
        print("tmp_xml new_path: {}".format(new_path))

    if create_new_clip:
        # New openClip
        print("Building new openClip")

        new_xml = ET.parse(tmp_file)

        for new_feed in new_xml.iter('feeds'):
            feed = new_feed.find('feed')
            feed.set('vuid', feed_basename)

            # add colorspace if any is set
            if feed_colorspace:
                _add_colorspace(feed, feed_colorspace)

            feedHandler = feed.find("./handler")
            feed.remove(feedHandler)

        for newVersion in new_xml.iter('versions'):
            newVersion.set('currentVersion', feed_basename)
            version = newVersion.find('version')
            version.set('uid', feed_basename)
            version.set('type', 'version')

        xmlRoot = new_xml.getroot()

        # Clean tmp_file - brute force remove errant <root/handler>
        print("Removing Handler")
        for handler in xmlRoot.findall("./handler"):
            print("Handler found")
            xmlRoot.remove(handler)

        resultXML = ET.tostring(xmlRoot).decode('utf-8')

        print("Adding feed version: {}".format(feed_basename))

        with open(tmp_file, "w") as f:
            f.write(resultXML)

        print("openClip Updated: %s" % tmp_file)

        clip_uploaded = True

    else:
        print("Updating openClip ..")

        source_xml = ET.parse(openclip_file_path)
        new_xml = ET.parse(tmp_file)

        print(">> source_xml: {}".format(source_xml))
        print(">> new_xml: {}".format(new_xml))

        feed_exists = False
        feed_added = 0

        feed_src_nb_ticks = None
        feed_src_fps = None
        feed_src_drop_mode = None

        try:
            for src_track in source_xml.iter('track'):
                for srcFeed in src_track.iter('feed'):
                    feed_src_nb_ticksObj = srcFeed.find(
                        'startTimecode/nbTicks')
                    feed_src_nb_ticks = feed_src_nb_ticksObj.text
                    feed_src_fpsObj = srcFeed.find(
                        'startTimecode/rate')
                    feed_src_fps = feed_src_fpsObj.text
                    feed_src_drop_modeObj = srcFeed.find(
                        'startTimecode/dropMode')
                    feed_src_drop_mode = feed_src_drop_modeObj.text
                    break
                else:
                    continue
                break
        except Exception as msg:
            print(msg)

        print("Source startTimecode/nbTicks: %s" % feed_src_nb_ticks)
        print("Source startTimecode/rate: %s" % feed_src_fps)
        print("Source startTimecode/dropMode: %s" % feed_src_drop_mode)

        # Get new feed from file
        for newTrack in new_xml.iter('track'):
            uid = newTrack.get('uid')
            new_feed = newTrack.find('feeds/feed')

            feedHandler = new_feed.find("./handler")
            new_feed.remove(feedHandler)

            if feed_src_fps:
                new_rateObject = newTrack.find(
                    "feeds/feed/startTimecode/rate")
                new_rateObject.text = feed_src_fps
            if feed_src_nb_ticks:
                new_nbTicksObject = newTrack.find(
                    "feeds/feed/startTimecode/nbTicks")
                new_nbTicksObject.text = feed_src_nb_ticks
            if feed_src_drop_mode:
                new_dropModeObj = newTrack.find(
                    "feeds/feed/startTimecode/dropMode")
                new_dropModeObj.text = feed_src_drop_mode

            new_path_obj = newTrack.find(
                "feeds/feed/spans/span/path")
            new_path = new_path_obj.text

            # loop all available feed paths and check if
            # the path is not already in file
            for src_path in source_xml.iter('path'):
                if new_path == src_path.text:
                    print("Not appending file as it already is in .clip file")
                    feed_exists = True

            if not feed_exists:
                # Append new temp file feed to .clip source xml tree
                for src_track in source_xml.iter('track'):
                    new_feed.set('vuid', feed_version_name)

                    # add colorspace if any is set
                    if feed_colorspace:
                        _add_colorspace(new_feed, feed_colorspace)

                    src_track.find('feeds').append(new_feed)
                    print(
                        "Appending new feed: {}".format(feed_version_name))
                    feed_added += 1

        if feed_added > 0:
            # Append vUID to versions
            newVersion = source_xml.find('versions')
            newVersionElement = ET.Element(
                "version", {"type": "version", "uid": feed_version_name})
            newVersion.insert(0, newVersionElement)
            xmlRoot = source_xml.getroot()

            # Clean tmp_file - brute force remove errant <root/handler>
            print("Removing Handler")
            for handler in xmlRoot.findall("./handler"):
                print("Handler found")
                xmlRoot.remove(handler)

            resultXML = ET.tostring(xmlRoot).decode('utf-8')

            # fist create backup
            create_openclip_backup_file(openclip_file_path)

            out_file = openclip_file_path

            print("Adding feed version: {}".format(feed_version_name))

            with open(out_file, "w") as f:
                f.write(resultXML)

            print("openClip Updated: {}".format(out_file))

            clip_uploaded = True

        if os.path.isfile(tmp_file):
            os.remove(tmp_file)

    return clip_uploaded


def create_openclip_backup_file(file):
    bck_file = "{}.bak".format(file)
    # if backup does not exist
    if not os.path.isfile(bck_file):
        shutil.copy2(file, bck_file)
    else:
        # in case it exists and is already multiplied
        created = False
        for _i in range(1, 99):
            bck_file = "{name}.bak.{idx:0>2}".format(
                name=file,
                idx=_i)
            # create numbered backup file
            if not os.path.isfile(bck_file):
                shutil.copy2(file, bck_file)
                created = True
                break
        # in case numbered does not exists
        if not created:
            bck_file = "{}.bak.last".format(file)
            shutil.copy2(file, bck_file)


def _add_colorspace(feed_obj, profile_name):
    feed_storage_obj = feed_obj.find("storageFormat")
    feed_clr_obj = feed_storage_obj.find("colourSpace")
    if not feed_clr_obj:
        feed_clr_obj = ET.Element(
            "colourSpace", {"type": "string"})
        feed_storage_obj.append(feed_clr_obj)

    feed_clr_obj.text = profile_name
