import os
import tempfile
import itertools
import contextlib
import xml.etree.cElementTree as cET
from copy import deepcopy
import shutil
from xml.etree import ElementTree as ET

import openpype.api as openpype

import logging

log = logging.getLogger(__name__)


@contextlib.contextmanager
def maintained_temp_file_path(suffix=None):
    _suffix = suffix or ""

    try:
        # Store dumped json to temporary file
        temporary_file = tempfile.mktemp(
            suffix=_suffix, prefix="flame_maintained_")
        yield temporary_file.replace("\\", "/")

    except IOError as _error:
        raise IOError(
            "Not able to create temp json file: {}".format(_error))

    finally:
        # Remove the temporary json
        os.remove(temporary_file)


class MediaInfoFile(object):
    """Class to get media info file clip data

    Raises:
        IOError: MEDIA_SCRIPT_PATH path doesn't exists
        TypeError: Not able to generate clip xml data file
        ET.ParseError: Missing clip in xml clip data
        IOError: Not able to save xml clip data to file

    Attributes:
        str: `MEDIA_SCRIPT_PATH` path to flame binary
        logging.Logger: `log` logger

    TODO: add method for getting metadata to dict
    """
    MEDIA_SCRIPT_PATH = "/opt/Autodesk/mio/current/dl_get_media_info"

    log = log

    _clip_data = None
    _start_frame = None
    _fps = None
    _drop_mode = None

    def __init__(self, path, **kwargs):

        # replace log if any
        if kwargs.get("logger"):
            self.log = kwargs["logger"]

        # test if `dl_get_media_info` paht exists
        self._validate_media_script_path()

        # derivate other feed variables
        self.feed_basename = os.path.basename(path)
        self.feed_dir = os.path.dirname(path)
        self.feed_ext = os.path.splitext(self.feed_basename)[1][1:].lower()

        with maintained_temp_file_path(".clip") as tmp_path:
            self.log.info("Temp File: {}".format(tmp_path))
            self._generate_media_info_file(tmp_path)

            # get clip data and make them single if there is multiple
            # clips data
            xml_data = self._make_single_clip_media_info(tmp_path)
            self.log.info("xml_data: {}".format(xml_data))
            self.log.info("type: {}".format(type(xml_data)))

            # get all time related data and assign them
            self._get_time_info_from_origin(xml_data)
            self.log.info("start_frame: {}".format(self.start_frame))
            self.log.info("fps: {}".format(self.fps))
            self.log.info("drop frame: {}".format(self.drop_mode))
            self.clip_data = xml_data

    @property
    def clip_data(self):
        """Clip's xml clip data

        Returns:
            xml.etree.ElementTree: xml data
        """
        return self._clip_data

    @clip_data.setter
    def clip_data(self, data):
        self._clip_data = data

    @property
    def start_frame(self):
        """ Clip's starting frame found in timecode

        Returns:
            int: number of frames
        """
        return self._start_frame

    @start_frame.setter
    def start_frame(self, number):
        self._start_frame = int(number)

    @property
    def fps(self):
        """ Clip's frame rate

        Returns:
            float: frame rate
        """
        return self._fps

    @fps.setter
    def fps(self, fl_number):
        self._fps = float(fl_number)

    @property
    def drop_mode(self):
        """ Clip's drop frame mode

        Returns:
            str: drop frame flag
        """
        return self._drop_mode

    @drop_mode.setter
    def drop_mode(self, text):
        self._drop_mode = str(text)

    def _validate_media_script_path(self):
        if not os.path.isfile(self.MEDIA_SCRIPT_PATH):
            raise IOError("Media Scirpt does not exist: `{}`".format(
                self.MEDIA_SCRIPT_PATH))

    def _generate_media_info_file(self, fpath):
        # Create cmd arguments for gettig xml file info file
        cmd_args = [
            self.MEDIA_SCRIPT_PATH,
            "-e", self.feed_ext,
            "-o", fpath,
            self.feed_dir
        ]

        try:
            # execute creation of clip xml template data
            openpype.run_subprocess(cmd_args)
        except TypeError as error:
            raise TypeError(
                "Error creating `{}` due: {}".format(fpath, error))

    def _make_single_clip_media_info(self, fpath):
        with open(fpath) as f:
            lines = f.readlines()
            _added_root = itertools.chain(
                "<root>", deepcopy(lines)[1:], "</root>")
            new_root = ET.fromstringlist(_added_root)

        # find the clip which is matching to my input name
        xml_clips = new_root.findall("clip")
        matching_clip = None
        for xml_clip in xml_clips:
            if xml_clip.find("name").text in self.feed_basename:
                matching_clip = xml_clip

        if matching_clip is None:
            # return warning there is missing clip
            raise ET.ParseError(
                "Missing clip in `{}`. Available clips {}".format(
                    self.feed_basename, [
                        xml_clip.find("name").text
                        for xml_clip in xml_clips
                    ]
                ))

        return matching_clip

    def _get_time_info_from_origin(self, xml_data):
        try:
            for out_track in xml_data.iter('track'):
                for out_feed in out_track.iter('feed'):
                    # start frame
                    out_feed_nb_ticks_obj = out_feed.find(
                        'startTimecode/nbTicks')
                    self.start_frame = out_feed_nb_ticks_obj.text

                    # fps
                    out_feed_fps_obj = out_feed.find(
                        'startTimecode/rate')
                    self.fps = out_feed_fps_obj.text

                    # drop frame mode
                    out_feed_drop_mode_obj = out_feed.find(
                        'startTimecode/dropMode')
                    self.drop_mode = out_feed_drop_mode_obj.text
                    break
                else:
                    continue
        except Exception as msg:
            self.log.warning(msg)

    @staticmethod
    def write_clip_data_to_file(fpath, xml_data):
        log.info(">>> type of xml_data: {}".format(type(xml_data)))
        if isinstance(xml_data, ET.ElementTree):
            xml_data = xml_data.getroot()
        try:
            # save it as new file
            tree = cET.ElementTree(xml_data)
            tree.write(
                fpath, xml_declaration=True,
                method='xml', encoding='UTF-8'
            )
        except IOError as error:
            raise IOError(
                "Not able to write data to file: {}".format(error))


class OpenClipSolver(MediaInfoFile):
    create_new_clip = False

    log = log

    def __init__(self, openclip_file_path, feed_data):
        self.out_file = openclip_file_path

        # new feed variables:
        feed_path = feed_data.pop("path")

        # initialize parent class
        super(OpenClipSolver, self).__init__(
            feed_path,
            **feed_data
        )

        # get other metadata
        self.feed_version_name = feed_data["version"]
        self.feed_colorspace = feed_data.get("colorspace")
        self.log.info("feed_version_name: {}".format(self.feed_version_name))

        # derivate other feed variables
        self.feed_basename = os.path.basename(feed_path)
        self.feed_dir = os.path.dirname(feed_path)
        self.feed_ext = os.path.splitext(self.feed_basename)[1][1:].lower()
        self.log.info("feed_ext: {}".format(self.feed_ext))
        self.log.info("out_file: {}".format(self.out_file))
        if not self._is_valid_tmp_file(self.out_file):
            self.create_new_clip = True

    def _is_valid_tmp_file(self, file):
        # check if file exists
        if os.path.isfile(file):
            # test also if file is not empty
            with open(file) as f:
                lines = f.readlines()
                if len(lines) > 2:
                    return True

                # file is probably corrupted
                os.remove(file)
                return False

    def make(self):

        if self.create_new_clip:
            # New openClip
            self._create_new_open_clip()
        else:
            self._update_open_clip()

    def _clear_handler(self, xml_object):
        for handler in xml_object.findall("./handler"):
            self.log.info("Handler found")
            xml_object.remove(handler)

    def _create_new_open_clip(self):
        self.log.info("Building new openClip")
        self.log.info(">> self.clip_data: {}".format(self.clip_data))

        # clip data comming from MediaInfoFile
        tmp_xml_feeds = self.clip_data.find('tracks/track/feeds')
        tmp_xml_feeds.set('currentVersion', self.feed_version_name)
        for tmp_feed in tmp_xml_feeds:
            tmp_feed.set('vuid', self.feed_version_name)

            # add colorspace if any is set
            if self.feed_colorspace:
                self._add_colorspace(tmp_feed, self.feed_colorspace)

            self._clear_handler(tmp_feed)

        tmp_xml_versions_obj = self.clip_data.find('versions')
        tmp_xml_versions_obj.set('currentVersion', self.feed_version_name)
        for xml_new_version in tmp_xml_versions_obj:
            xml_new_version.set('uid', self.feed_version_name)
            xml_new_version.set('type', 'version')

        self._clear_handler(self.clip_data)
        self.log.info("Adding feed version: {}".format(self.feed_basename))

        self.write_clip_data_to_file(self.out_file, self.clip_data)

    def _update_open_clip(self):
        self.log.info("Updating openClip ..")

        out_xml = ET.parse(self.out_file)

        self.log.info(">> out_xml: {}".format(out_xml))
        self.log.info(">> self.clip_data: {}".format(self.clip_data))

        # Get new feed from tmp file
        tmp_xml_feed = self.clip_data.find('tracks/track/feeds/feed')

        self._clear_handler(tmp_xml_feed)

        # update fps from MediaInfoFile class
        if self.fps:
            tmp_feed_fps_obj = tmp_xml_feed.find(
                "startTimecode/rate")
            tmp_feed_fps_obj.text = str(self.fps)

        # update start_frame from MediaInfoFile class
        if self.start_frame:
            tmp_feed_nb_ticks_obj = tmp_xml_feed.find(
                "startTimecode/nbTicks")
            tmp_feed_nb_ticks_obj.text = str(self.start_frame)

        # update drop_mode from MediaInfoFile class
        if self.drop_mode:
            tmp_feed_drop_mode_obj = tmp_xml_feed.find(
                "startTimecode/dropMode")
            tmp_feed_drop_mode_obj.text = str(self.drop_mode)

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

            self.log.info(
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

            self._clear_handler(out_xml)

            # fist create backup
            self._create_openclip_backup_file(self.out_file)

            self.log.info("Adding feed version: {}".format(
                self.feed_version_name))

            self.write_clip_data_to_file(self.out_file, out_xml)

            self.log.info("openClip Updated: {}".format(self.out_file))

    def _feed_exists(self, xml_data, path):
        # loop all available feed paths and check if
        # the path is not already in file
        for src_path in xml_data.iter('path'):
            if path == src_path.text:
                self.log.warning(
                    "Not appending file as it already is in .clip file")
                return True

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
        if feed_clr_obj is not None:
            feed_clr_obj = ET.Element(
                "colourSpace", {"type": "string"})
            feed_storage_obj.append(feed_clr_obj)

        feed_clr_obj.text = profile_name
