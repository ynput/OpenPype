import os
import subprocess
import pype.api
import json


class ExtractBurnin(pype.api.Extractor):
    """
    Extractor to create video with pre-defined burnins from
    existing extracted video representation.

    It will work only on represenations having `burnin = True` or
    `tags` including `burnin`
    """

    label = "Quicktime with burnins"
    families = ["burnin"]
    optional = True

    def process(self, instance):
        if "representations" not in instance.data:
            raise RuntimeError("Burnin needs already created mov to work on.")

        # TODO: expand burnin data list to include all usefull keys
        burnin_data = {
            "username": instance.context.data['user'],
            "asset": os.environ['AVALON_ASSET'],
            "task": os.environ['AVALON_TASK'],
            "start_frame": int(instance.data['startFrame']),
            "version": "v" + str(instance.context.data['version'])
        }

        for repre in instance.data["representations"]:
            if (not repre.get("burnin", False) or
                    "burnin" not in repre.get("tags", [])):
                continue

            stagingdir = self.staging_dir(instance)
            filename = "{0}".format(repre["files"])

            movieFileBurnin = filename + "Burn" + ".mov"

            full_movie_path = os.path.join(stagingdir, repre["files"])
            full_burnin_path = os.path.join(stagingdir, movieFileBurnin)

            burnin_data = {
                "input": full_movie_path.replace("\\", "/"),
                "output": full_burnin_path.replace("\\", "/"),
                "burnin_data": burnin_data
                }

            json_data = json.dumps(burnin_data)
            scriptpath = os.path.join(os.environ['PYPE_MODULE_ROOT'],
                                      "pype",
                                      "scripts",
                                      "otio_burnin.py")

            p = subprocess.Popen(
                ['python', scriptpath, json_data]
            )
            p.wait()

            repre['files']: movieFileBurnin
