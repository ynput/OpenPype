import os
import re
import sys
import six
import tempfile
from xml.etree import ElementTree as ET
import flame


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


class Transcoder(object):
    exporter = flame.PyExporter()

    def __init__(
            self,
            clip,
            preset_path,
            ext,
            output_dir=None,
            **kwargs
    ):
        self._input_clip = clip
        self._output_ext = ext
        self._preset_path = preset_path
        self._output_dir = output_dir or self._get_temp_dir()

        # create arbitrari job name
        self._clip_name = clip.name.get_value()
        self._preset_name = os.path.splitext(
            os.path.basename(preset_path)
        )[0]

        # set in and out markers
        self._define_in_out(kwargs)

    def _define_in_out(self, data):
        in_mark = out_mark = None

        # Set exporter
        self.exporter.export_between_marks = True

        if data.get("thumb_frame_number"):
            thumb_frame_number = data["thumb_frame_number"]
            # make sure it exists in kwargs
            if not thumb_frame_number:
                raise KeyError(
                    "Missing key `thumb_frame_number` in input kwargs")

            in_mark = int(thumb_frame_number)
            out_mark = int(thumb_frame_number) + 1

        elif data.get("in_mark") and data.get("out_mark"):
            in_mark = int(data["in_mark"])
            out_mark = int(data["out_mark"])
        else:
            self.exporter.export_between_marks = False

        # set in and out marks if they are available
        if in_mark and out_mark:
            self._input_clip.in_mark = in_mark
            self._input_clip.out_mark = out_mark

    def _get_temp_dir(self):
        return tempfile.mkdtemp()

    def export(self):
        self.exporter.foreground_export = True

        try:
            self.exporter.export(
                self._input_clip,
                self._preset_path,
                self._output_dir
            )
        except Exception:
            tp, value, tb = sys.exc_info()
            six.reraise(tp, value, tb)

        finally:
            print("Exported: `{}` [{}-{}] to `{}`".format(
                self._clip_name,
                self._input_clip.in_mark,
                self._input_clip.out_mark,
                self._output_dir
            ))


class BackburnerTranscoder(Transcoder):
    RETURNING_JOB_KEY = "transcoding_job"
    JOB_NAME_LENGTH = 92
    COMPLETION = {
        "delete": {"delay": 10},
        "leaveInQueue": {"delay": None},
        "archive": {"delay": 0}
    }

    def __init__(
            self,
            clip,
            preset_path,
            ext,
            job_name=None,
            job_completion=None,
            **kwargs
    ):
        super(BackburnerTranscoder, self).__init__(
            clip, preset_path, ext, **kwargs)

        self._job_name = job_name or "_".join([
            self._clip_name,
            self._preset_name
        ])

        self._job_completion = job_completion

    def export(self):
        self.exporter.foreground_export = False
        hooks_user_data = {}

        output_dir, output_file = self._create_temp_paths()

        try:
            self.exporter.export(
                sources=self._input_clip,
                preset_path=self._preset_path,
                output_directory=output_dir,
                background_job_settings=self._create_background_job_settings(),
                hooks=self.job_hook(self.RETURNING_JOB_KEY),
                hooks_user_data=hooks_user_data,
            )
        except Exception:
            tp, value, tb = sys.exc_info()
            six.reraise(tp, value, tb)

        return {
            "job_temp_dir": output_dir,
            "job_temp_files": output_file,
            "job_hooks_data": hooks_user_data.get(
                self.RETURNING_JOB_KEY)
        }

    def _create_temp_paths(self):

        tmp_d, fpath = tempfile.mkstemp(
            suffix=self._output_ext, dir=self.get_backburner_tmp()
        )
        os.close(tmp_d)
        self._input_clip.name = os.path.splitext(
            os.path.basename(fpath))[0]

        return tmp_d, fpath

    def get_backburner_tmp(self):
        return (
            os.environ.get("SHOTGUN_FLAME_BACKBURNER_SHARED_TMP")
            or tempfile.gettempdir()
        )

    def _create_background_job_settings(self):
        """ Creating Backbruner job settings

        Returns:
            _type_: _description_
        """
        bgr_job_settings = flame.PyExporter.BackgroundJobSettings()
        bgr_job_settings.name = self._get_job_name()
        bgr_job_settings.description = (
            "Generating files `{}` - {} -> {}"
        ).format(
            self._job_name,
            self._clip_name,
            self._out_dir_path,
        )

        if self._job_completion:
            compl_handling = self.COMPLETION.get(self._job_completion)

            if not compl_handling:
                raise AttributeError(
                    "Wrong comletion name: {}. Correct: {}".format(
                        self._job_completion, self.COMPLETION
                    )
                )
            bgr_job_settings.completion_handling = self._job_completion
            if compl_handling["delay"] is not None:
                bgr_job_settings.completion_handling_delay = (
                    compl_handling["delay"]
                )
        return bgr_job_settings

    def _get_job_name(self):
        """ Sanitase job name so Backbruner accept it

        Args:
            name (str): input name

        Returns:
            str: fixed name
        """
        name_correct_length = self._job_name[: self.JOB_NAME_LENGTH]
        return re.sub(r"[^0-9a-zA-Z_\-,\. %]+", "_", name_correct_length)

    def submit(self):
        pass

    @classmethod
    def job_hook(klass, job_key_user_data):
        class PythonHookOverride(object):
            def __init__(self, job_key_user_data):
                self._job_key_user_data = job_key_user_data

            def preExport(self, info, userData, *args, **kwargs):
                pass

            def postExport(self, info, userData, *args, **kwargs):
                pass

            def preExportSequence(self, info, userData, *args, **kwargs):
                pass

            def postExportSequence(self, info, userData, *args, **kwargs):
                pass

            def preExportAsset(self, info, userData, *args, **kwargs):
                pass

            def postExportAsset(self, info, userData, *args, **kwargs):
                del args, kwargs  # Unused necessary parameters
                userData[self._job_key_user_data] = {
                    info["backgroundJobId"]: info
                }

            def exportOverwriteFile(self, path, *args, **kwargs):
                del path, args, kwargs  # Unused necessary parameters
                return "overwrite"

        return PythonHookOverride(job_key_user_data)
