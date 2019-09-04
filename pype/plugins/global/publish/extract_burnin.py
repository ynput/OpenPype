import os
import json

import pype.api
import pyblish


class ExtractBurnin(pype.api.Extractor):
    """
    Extractor to create video with pre-defined burnins from
    existing extracted video representation.

    It will work only on represenations having `burnin = True` or
    `tags` including `burnin`
    """

    label = "Quicktime with burnins"
    order = pyblish.api.ExtractorOrder + 0.03
    families = ["review", "burnin"]
    hosts = ["nuke", "maya", "shell"]
    optional = True

    def process(self, instance):
        if "representations" not in instance.data:
            raise RuntimeError("Burnin needs already created mov to work on.")

        # TODO: expand burnin data list to include all usefull keys
        version = ''
        if instance.context.data.get('version'):
            version = "v" + str(instance.context.data['version'])

        prep_data = {
            "username": instance.context.data['user'],
            "asset": os.environ['AVALON_ASSET'],
            "task": os.environ['AVALON_TASK'],
            "start_frame": int(instance.data["frameStart"]),
            "version": version
        }
        self.log.debug("__ prep_data: {}".format(prep_data))
        for i, repre in enumerate(instance.data["representations"]):
            self.log.debug("__ i: `{}`, repre: `{}`".format(i, repre))

            if "burnin" not in repre.get("tags", []):
                continue

            stagingdir = repre["stagingDir"]
            filename = "{0}".format(repre["files"])

            name = "_burnin"
            movieFileBurnin = filename.replace(".mov", "") + name + ".mov"

            full_movie_path = os.path.join(os.path.normpath(stagingdir), repre["files"])
            full_burnin_path = os.path.join(os.path.normpath(stagingdir), movieFileBurnin)
            self.log.debug("__ full_burnin_path: {}".format(full_burnin_path))

            burnin_data = {
                "input": full_movie_path.replace("\\", "/"),
                "output": full_burnin_path.replace("\\", "/"),
                "burnin_data": prep_data
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
                "files": movieFileBurnin,
                "name": repre["name"],
                "tags": [x for x in repre["tags"] if x != "delete"]
            }
            instance.data["representations"][i].update(repre_update)

            # removing the source mov file
            os.remove(full_movie_path)
            self.log.debug("Removed: `{}`".format(full_movie_path))

        # Remove any representations tagged for deletion.
        for repre in instance.data["representations"]:
            if "delete" in repre.get("tags", []):
                self.log.debug("Removing representation: {}".format(repre))
                instance.data["representations"].remove(repre)

        self.log.debug(instance.data["representations"])
