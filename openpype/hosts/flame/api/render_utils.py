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


class OpenClip:
    media_script_path = "/opt/Autodesk/mio/current/dl_get_media_info"
    tmp_name = "_tmp.clip"
    tmp_file = None
    create_new_clip = False

    out_feed_nb_ticks = None
    out_feed_fps = None
    out_feed_drop_mode = None

    def __init__(self, name, openclip_file_path, feed_data):
        # test if media script paht exists
        self._validate_media_script_path()

        # new feed variables:
        feed_path = feed_data["path"]
        self.feed_version_name = feed_data["version"]
        self.feed_colorspace = feed_data.get("colorspace")

        # derivate other feed variables
        self.feed_basename = os.path.basename(feed_path)
        self.feed_dir = os.path.dirname(feed_path)
        self.feed_ext = os.path.splitext(self.feed_basename)[1][1:].lower()

        if not os.path.isfile(openclip_file_path):
            # openclip does not exist yet and will be created
            self.tmp_file = self.out_file = openclip_file_path
            self.create_new_clip = True

        else:
            # output a temp file
            self.out_file = openclip_file_path
            self.tmp_file = os.path.join(self.feed_dir, self.tmp_name)
            self._clear_tmp_file()

        print("Temp File: {}".format(self.tmp_file))

    def _validate_media_script_path(self):
        if not os.path.isfile(self.media_script_path):
            raise IOError("Media Scirpt does not exist: `{}`".format(
                self.media_script_path))

    def _get_media_info_args(self):
        # Create cmd arguments for gettig xml file info file
        cmd_args = [
            self.media_script_path,
            "-e", self.feed_ext,
            "-o", self.tmp_file,
            self.feed_dir
        ]

        # execute creation of clip xml template data
        try:
            openpype.lib.run_subprocess(cmd_args)
        except TypeError:
            print("Error createing self.tmp_file")
            six.reraise(*sys.exc_info())

    def _clear_tmp_file(self):
        if os.path.isfile(self.tmp_file):
            os.remove(self.tmp_file)

    def _clear_handler(self, xml_object):
        for handler in xml_object.findall("./handler"):
            print("Handler found")
            xml_object.remove(handler)

    def _create_new_open_clip(self):
        print("Building new openClip")

        tmp_xml = ET.parse(self.tmp_file)

        tmp_xml_feeds = tmp_xml.find('tracks/track/feeds')
        tmp_xml_feeds.set('currentVersion', self.feed_version_name)
        for tmp_feed in tmp_xml_feeds:
            tmp_feed.set('vuid', self.feed_version_name)

            # add colorspace if any is set
            if self.feed_colorspace:
                self._add_colorspace(tmp_feed, self.feed_colorspace)

            self._clear_handler(tmp_feed)

        tmp_xml_versions_obj = tmp_xml.find('versions')
        tmp_xml_versions_obj.set('currentVersion', self.feed_version_name)
        for xml_new_version in tmp_xml_versions_obj:
            xml_new_version.set('uid', self.feed_version_name)
            xml_new_version.set('type', 'version')

        xml_data = self._fix_xml_data(tmp_xml)
        print("Adding feed version: {}".format(self.feed_basename))

        self._write_result_xml_to_file(xml_data)

        print("openClip Updated: %s" % self.tmp_file)

    def _update_open_clip(self):
        print("Updating openClip ..")

        out_xml = ET.parse(self.out_file)
        tmp_xml = ET.parse(self.tmp_file)

        print(">> out_xml: {}".format(out_xml))
        print(">> tmp_xml: {}".format(tmp_xml))

        # Get new feed from tmp file
        tmp_xml_feed = tmp_xml.find('tracks/track/feeds/feed')

        self._clear_handler(tmp_xml_feed)
        self._get_time_info_from_origin(out_xml)

        if self.out_feed_fps:
            tmp_feed_fps_obj = tmp_xml_feed.find(
                "startTimecode/rate")
            tmp_feed_fps_obj.text = self.out_feed_fps
        if self.out_feed_nb_ticks:
            tmp_feed_nb_ticks_obj = tmp_xml_feed.find(
                "startTimecode/nbTicks")
            tmp_feed_nb_ticks_obj.text = self.out_feed_nb_ticks
        if self.out_feed_drop_mode:
            tmp_feed_drop_mode_obj = tmp_xml_feed.find(
                "startTimecode/dropMode")
            tmp_feed_drop_mode_obj.text = self.out_feed_drop_mode

        new_path_obj = tmp_xml_feed.find(
            "spans/span/path")
        new_path = new_path_obj.text

        feed_added = False
        if not self._feed_exists(out_xml, new_path):
            tmp_xml_feed.set('vuid', self.feed_version_name)
            # Append new temp file feed to .clip source out xml
            out_track = out_xml.find("tracks/track")
            # add colorspace if any is set
            if self.feed_colorspace:
                self._add_colorspace(tmp_xml_feed, self.feed_colorspace)

            out_feeds = out_track.find('feeds')
            out_feeds.set('currentVersion', self.feed_version_name)
            out_feeds.append(tmp_xml_feed)

            print(
                "Appending new feed: {}".format(
                    self.feed_version_name))
            feed_added = True

        if feed_added:
            # Append vUID to versions
            out_xml_versions_obj = out_xml.find('versions')
            out_xml_versions_obj.set(
                'currentVersion', self.feed_version_name)
            new_version_obj = ET.Element(
                "version", {"type": "version", "uid": self.feed_version_name})
            out_xml_versions_obj.insert(0, new_version_obj)

            xml_data = self._fix_xml_data(out_xml)

            # fist create backup
            self._create_openclip_backup_file(self.out_file)

            print("Adding feed version: {}".format(self.feed_version_name))

            self._write_result_xml_to_file(xml_data)

            print("openClip Updated: {}".format(self.out_file))

        self._clear_tmp_file()

    def _get_time_info_from_origin(self, xml_data):
        try:
            for out_track in xml_data.iter('track'):
                for out_feed in out_track.iter('feed'):
                    out_feed_nb_ticks_obj = out_feed.find(
                        'startTimecode/nbTicks')
                    self.out_feed_nb_ticks = out_feed_nb_ticks_obj.text
                    out_feed_fps_obj = out_feed.find(
                        'startTimecode/rate')
                    self.out_feed_fps = out_feed_fps_obj.text
                    out_feed_drop_mode_obj = out_feed.find(
                        'startTimecode/dropMode')
                    self.out_feed_drop_mode = out_feed_drop_mode_obj.text
                    break
                else:
                    continue
        except Exception as msg:
            print(msg)

    def _feed_exists(self, xml_data, path):
        # loop all available feed paths and check if
        # the path is not already in file
        for src_path in xml_data.iter('path'):
            if path == src_path.text:
                print("Not appending file as it already is in .clip file")
                return True

    def _fix_xml_data(self, xml_data):
        xml_root = xml_data.getroot()
        self._clear_handler(xml_root)
        return ET.tostring(xml_root).decode('utf-8')

    def maintain_clip(self):
        self._get_media_info_args()

        if self.create_new_clip:
            # New openClip
            self._create_new_open_clip()
        else:
            self._update_open_clip()

    def _write_result_xml_to_file(self, xml_data):
        with open(self.out_file, "w") as f:
            f.write(xml_data)

    def _create_openclip_backup_file(self, file):
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

    def _add_colorspace(self, feed_obj, profile_name):
        feed_storage_obj = feed_obj.find("storageFormat")
        feed_clr_obj = feed_storage_obj.find("colourSpace")
        if not feed_clr_obj:
            feed_clr_obj = ET.Element(
                "colourSpace", {"type": "string"})
            feed_storage_obj.append(feed_clr_obj)

        feed_clr_obj.text = profile_name
