import os
import subprocess
import pype.api
import json


class ExtractBurnin(pype.api.Extractor):

    label = "Quicktime with burnins"
    families = ["burnin"]
    optional = True

    def process(self, instance):
        version = instance.context.data['version']
        stagingdir = self.staging_dir(instance)
        filename = "{0}".format(instance.name)

        movieFile = filename + ".mov"
        movieFileBurnin = filename + "Burn" + ".mov"

        full_movie_path = os.path.join(stagingdir, movieFile)
        full_burnin_path = os.path.join(stagingdir, movieFileBurnin)

        burnin_data = {
            "input": full_movie_path.replace("\\", "/"),
            "output": full_burnin_path.replace("\\", "/"),
            "burnin_data": {
                            "username": instance.context.data['user'],
                            "asset": os.environ['AVALON_ASSET'],
                            "task": os.environ['AVALON_TASK'],
                            "start_frame": int(instance.data['startFrame']),
                            "version": "v" + str(version)
                            }
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

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': 'mov',
            'ext': 'mov',
            'files': movieFileBurnin,
            "stagingDir": stagingdir,
            'preview': True
        }
        instance.data["representations"].append(representation)
