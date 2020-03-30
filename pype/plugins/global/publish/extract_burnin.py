import os
import json
import copy

import pype.api
import pyblish


class ExtractBurnin(pype.api.Extractor):
    """
    Extractor to create video with pre-defined burnins from
    existing extracted video representation.

    It will work only on represenations having `burnin = True` or
    `tags` including `burnin`
    """

    label = "Extract burnins"
    order = pyblish.api.ExtractorOrder + 0.03
    families = ["review", "burnin"]
    hosts = ["nuke", "maya", "shell"]
    optional = True

    def process(self, instance):
        if "representations" not in instance.data:
            raise RuntimeError("Burnin needs already created mov to work on.")

        context_data = instance.context.data

        version = instance.data.get(
            'version', instance.context.data.get('version'))
        frame_start = int(instance.data.get("frameStart") or 0)
        frame_end = int(instance.data.get("frameEnd") or 1)
        handle_start = instance.data.get("handleStart",
                                         context_data.get("handleStart"))
        handle_end = instance.data.get("handleEnd",
                                       context_data.get("handleEnd"))

        frame_start_handle = frame_start - handle_start
        frame_end_handle = frame_end + handle_end
        duration = frame_end_handle - frame_start_handle + 1

        prep_data = copy.deepcopy(instance.data["anatomyData"])

        if "slate.farm" in instance.data["families"]:
            frame_start_handle += 1
            duration -= 1

        prep_data.update({
            "frame_start": frame_start_handle,
            "frame_end": frame_end_handle,
            "duration": duration,
            "version": int(version),
            "comment": instance.context.data.get("comment", "")
        })

        intent_label = instance.context.data.get("intent")
        if intent_label and isinstance(intent_label, dict):
            intent_label = intent_label.get("label")

        if intent_label:
            prep_data["intent"] = intent_label

        # get anatomy project
        anatomy = instance.context.data['anatomy']

        self.log.debug("__ prep_data: {}".format(prep_data))
        for i, repre in enumerate(instance.data["representations"]):
            self.log.debug("__ i: `{}`, repre: `{}`".format(i, repre))

            if "multipartExr" in repre.get("tags", []):
                # ffmpeg doesn't support multipart exrs
                continue

            if "burnin" not in repre.get("tags", []):
                continue

            is_sequence = "sequence" in repre.get("tags", [])

            # no handles switch from profile tags
            no_handles = "no-handles" in repre.get("tags", [])

            stagingdir = repre["stagingDir"]
            filename = "{0}".format(repre["files"])

            if is_sequence:
                filename = repre["sequence_file"]

            name = "_burnin"
            ext = os.path.splitext(filename)[1]
            movieFileBurnin = filename.replace(ext, "") + name + ext

            if is_sequence:
                fn_splt = filename.split(".")
                movieFileBurnin = ".".join(
                    ((fn_splt[0] + name), fn_splt[-2], fn_splt[-1]))

            self.log.debug("__ movieFileBurnin: `{}`".format(movieFileBurnin))

            full_movie_path = os.path.join(
                os.path.normpath(stagingdir), filename)
            full_burnin_path = os.path.join(
                os.path.normpath(stagingdir), movieFileBurnin)

            self.log.debug("__ full_movie_path: {}".format(full_movie_path))
            self.log.debug("__ full_burnin_path: {}".format(full_burnin_path))

            # create copy of prep_data for anatomy formatting
            _prep_data = copy.deepcopy(prep_data)
            _prep_data["representation"] = repre["name"]
            filled_anatomy = anatomy.format_all(_prep_data)
            _prep_data["anatomy"] = filled_anatomy.get_solved()

            # copy frame range variables
            frame_start_cp = frame_start_handle
            frame_end_cp = frame_end_handle
            duration_cp = duration

            if no_handles:
                frame_start_cp = frame_start
                frame_end_cp = frame_end
                duration_cp = frame_end_cp - frame_start_cp + 1
                _prep_data.update({
                    "frame_start": frame_start_cp,
                    "frame_end": frame_end_cp,
                    "duration": duration_cp,
                })

            # dealing with slates
            slate_frame_start = frame_start_cp
            slate_frame_end = frame_end_cp
            slate_duration = duration_cp

            # exception for slate workflow
            if ("slate" in instance.data["families"]):
                if "slate-frame" in repre.get("tags", []):
                    slate_frame_start = frame_start_cp - 1
                    slate_frame_end = frame_end_cp
                    slate_duration = duration_cp + 1

            self.log.debug("__1 slate_frame_start: {}".format(slate_frame_start))

            _prep_data.update({
                "slate_frame_start": slate_frame_start,
                "slate_frame_end": slate_frame_end,
                "slate_duration": slate_duration
            })

            burnin_data = {
                "input": full_movie_path.replace("\\", "/"),
                "codec": repre.get("codec", []),
                "output": full_burnin_path.replace("\\", "/"),
                "burnin_data": _prep_data
            }

            self.log.debug("__ burnin_data2: {}".format(burnin_data))

            json_data = json.dumps(burnin_data)

            # Get script path.
            module_path = os.environ['PYPE_MODULE_ROOT']

            # There can be multiple paths in PYPE_MODULE_ROOT, in which case
            # we just take first one.
            if os.pathsep in module_path:
                module_path = module_path.split(os.pathsep)[0]

            scriptpath = os.path.normpath(
                os.path.join(
                    module_path,
                    "pype",
                    "scripts",
                    "otio_burnin.py"
                )
            )

            self.log.debug("__ scriptpath: {}".format(scriptpath))

            # Get executable.
            executable = os.getenv("PYPE_PYTHON_EXE")

            # There can be multiple paths in PYPE_PYTHON_EXE, in which case
            # we just take first one.
            if os.pathsep in executable:
                executable = executable.split(os.pathsep)[0]

            self.log.debug("__ EXE: {}".format(executable))

            args = [executable, scriptpath, json_data]
            self.log.debug("Executing: {}".format(args))
            output = pype.api.subprocess(args)
            self.log.debug("Output: {}".format(output))

            repre_update = {
                "anatomy_template": "render",
                "files": movieFileBurnin,
                "name": repre["name"],
                "tags": [x for x in repre["tags"] if x != "delete"]
            }

            if is_sequence:
                burnin_seq_files = list()
                for frame_index in range(_prep_data["duration"] + 1):
                    if frame_index == 0:
                        continue
                    burnin_seq_files.append(movieFileBurnin % frame_index)
                repre_update.update({
                    "files": burnin_seq_files
                })

            instance.data["representations"][i].update(repre_update)

            # removing the source mov file
            if is_sequence:
                for frame_index in range(_prep_data["duration"] + 1):
                    if frame_index == 0:
                        continue
                    rm_file = full_movie_path % frame_index
                    os.remove(rm_file)
                    self.log.debug("Removed: `{}`".format(rm_file))
            else:
                os.remove(full_movie_path)
                self.log.debug("Removed: `{}`".format(full_movie_path))

        # Remove any representations tagged for deletion.
        for repre in instance.data["representations"]:
            if "delete" in repre.get("tags", []):
                self.log.debug("Removing representation: {}".format(repre))
                instance.data["representations"].remove(repre)

        self.log.debug(instance.data["representations"])
