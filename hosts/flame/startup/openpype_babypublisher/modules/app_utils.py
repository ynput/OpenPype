import os
import io
import ConfigParser as CP
from xml.etree import ElementTree as ET
from contextlib import contextmanager

PLUGIN_DIR = os.path.dirname(os.path.dirname(__file__))
EXPORT_PRESETS_DIR = os.path.join(PLUGIN_DIR, "export_preset")

CONFIG_DIR = os.path.join(os.path.expanduser(
    "~/.openpype"), "openpype_babypublisher")


@contextmanager
def make_temp_dir():
    import tempfile

    try:
        dirpath = tempfile.mkdtemp()

        yield dirpath

    except IOError as _error:
        raise IOError("Not able to create temp dir file: {}".format(_error))

    finally:
        pass


@contextmanager
def get_config(section=None):
    cfg_file_path = os.path.join(CONFIG_DIR, "settings.ini")

    # create config dir
    if not os.path.exists(CONFIG_DIR):
        print("making dirs at: `{}`".format(CONFIG_DIR))
        os.makedirs(CONFIG_DIR, mode=0o777)

    # write default data to settings.ini
    if not os.path.exists(cfg_file_path):
        default_cfg = cfg_default()
        config = CP.RawConfigParser()
        config.readfp(io.BytesIO(default_cfg))
        with open(cfg_file_path, 'wb') as cfg_file:
            config.write(cfg_file)

    try:
        config = CP.RawConfigParser()
        config.read(cfg_file_path)
        if section:
            _cfg_data = {
                k: v
                for s in config.sections()
                for k, v in config.items(s)
                if s == section
            }
        else:
            _cfg_data = {s: dict(config.items(s)) for s in config.sections()}

        yield _cfg_data

    except IOError as _error:
        raise IOError('Not able to read settings.ini file: {}'.format(_error))

    finally:
        pass


def set_config(cfg_data, section=None):
    cfg_file_path = os.path.join(CONFIG_DIR, "settings.ini")

    config = CP.RawConfigParser()
    config.read(cfg_file_path)

    try:
        if not section:
            for section in cfg_data:
                for key, value in cfg_data[section].items():
                    config.set(section, key, value)
        else:
            for key, value in cfg_data.items():
                config.set(section, key, value)

        with open(cfg_file_path, 'wb') as cfg_file:
            config.write(cfg_file)

    except IOError as _error:
        raise IOError('Not able to write settings.ini file: {}'.format(_error))


def cfg_default():
    return """
[main]
workfile_start_frame = 1001
shot_handles = 0
shot_name_template = {sequence}_{shot}
hierarchy_template = shots[Folder]/{sequence}[Sequence]
create_task_type = Compositing
"""


def configure_preset(file_path, data):
    split_fp = os.path.splitext(file_path)
    new_file_path = split_fp[0] + "_tmp" + split_fp[-1]
    with open(file_path, "r") as datafile:
        tree = ET.parse(datafile)
        for key, value in data.items():
            for element in tree.findall(".//{}".format(key)):
                print(element)
                element.text = str(value)
        tree.write(new_file_path)

    return new_file_path


def export_thumbnail(sequence, tempdir_path, data):
    import flame
    export_preset = os.path.join(
        EXPORT_PRESETS_DIR,
        "openpype_seg_thumbnails_jpg.xml"
    )
    new_path = configure_preset(export_preset, data)
    poster_frame_exporter = flame.PyExporter()
    poster_frame_exporter.foreground = True
    poster_frame_exporter.export(sequence, new_path, tempdir_path)


def export_video(sequence, tempdir_path, data):
    import flame
    export_preset = os.path.join(
        EXPORT_PRESETS_DIR,
        "openpype_seg_video_h264.xml"
    )
    new_path = configure_preset(export_preset, data)
    poster_frame_exporter = flame.PyExporter()
    poster_frame_exporter.foreground = True
    poster_frame_exporter.export(sequence, new_path, tempdir_path)


def timecode_to_frames(timecode, framerate):
    def _seconds(value):
        if isinstance(value, str):
            _zip_ft = zip((3600, 60, 1, 1 / framerate), value.split(':'))
            return sum(f * float(t) for f, t in _zip_ft)
        elif isinstance(value, (int, float)):
            return value / framerate
        return 0

    def _frames(seconds):
        return seconds * framerate

    def tc_to_frames(_timecode, start=None):
        return _frames(_seconds(_timecode) - _seconds(start))

    if '+' in timecode:
        timecode = timecode.replace('+', ':')
    elif '#' in timecode:
        timecode = timecode.replace('#', ':')

    frames = int(round(tc_to_frames(timecode, start='00:00:00:00')))

    return frames
