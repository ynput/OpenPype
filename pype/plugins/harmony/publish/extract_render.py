import os
import tempfile
import subprocess

import pyblish.api
from avalon import harmony

import clique


class ExtractRender(pyblish.api.InstancePlugin):
    """Produce a flattened image file from instance.
    This plug-in only takes into account the nodes connected to the composite.
    """

    label = "Extract Render"
    order = pyblish.api.ExtractorOrder
    hosts = ["harmony"]
    families = ["render"]

    def process(self, instance):
        # Collect scene data.
        func = """function func(write_node)
        {
            return [
                about.getApplicationPath(),
                scene.currentProjectPath(),
                scene.currentScene(),
                scene.getFrameRate(),
                scene.getStartFrame(),
                scene.getStopFrame(),
                sound.getSoundtrackAll().path()
            ]
        }
        func
        """
        result = harmony.send(
            {"function": func, "args": [instance[0]]}
        )["result"]
        application_path = result[0]
        scene_path = os.path.join(result[1], result[2] + ".xstage")
        frame_rate = result[3]
        frame_start = result[4]
        frame_end = result[5]
        audio_path = result[6]

        # Set output path to temp folder.
        path = tempfile.mkdtemp()
        func = """function func(args)
        {
            node.setTextAttr(args[0], "DRAWING_NAME", 1, args[1]);
        }
        func
        """
        result = harmony.send(
            {
                "function": func,
                "args": [instance[0], path + "/" + instance.data["name"]]
            }
        )
        harmony.save_scene()

        # Execute rendering. Ignoring error cause Harmony returns error code
        # always.
        proc = subprocess.Popen(
            [application_path, "-batch", scene_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE
        )
        output, error = proc.communicate()
        self.log.info(output.decode("utf-8"))

        # Collect rendered files.
        self.log.debug(path)
        files = os.listdir(path)
        self.log.debug(files)
        collections, remainder = clique.assemble(files, minimum_items=1)
        assert not remainder, (
            "There should not be a remainder for {0}: {1}".format(
                instance[0], remainder
            )
        )
        self.log.debug(collections)
        if len(collections) > 1:
            for col in collections:
                if len(list(col)) > 1:
                     collection = col
        else:
            # assert len(collections) == 1, (
            #     "There should only be one image sequence in {}. Found: {}".format(
            #         path, len(collections)
            #     )
            # )
            collection = collections[0]

        # Generate thumbnail.
        thumbnail_path = os.path.join(path, "thumbnail.png")
        args = [
            "ffmpeg", "-y",
            "-i", os.path.join(path, list(collections[0])[0]),
            "-vf", "scale=300:-1",
            "-vframes", "1",
            thumbnail_path
        ]
        process = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE
        )

        output = process.communicate()[0]

        if process.returncode != 0:
            raise ValueError(output.decode("utf-8"))

        self.log.debug(output.decode("utf-8"))

        # Generate mov.
        mov_path = os.path.join(path, instance.data["name"] + ".mov")
        if os.path.isfile(audio_path):
            args = [
                "ffmpeg", "-y",
                "-i", audio_path,
                "-i",
                os.path.join(path, collection.head + "%04d" + collection.tail),
                mov_path
            ]
        else:
            args = [
                "ffmpeg", "-y",
                "-i",
                os.path.join(path, collection.head + "%04d" + collection.tail),
                mov_path
            ]

        process = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE
        )

        output = process.communicate()[0]

        if process.returncode != 0:
            raise ValueError(output.decode("utf-8"))

        self.log.debug(output.decode("utf-8"))

        # Generate representations.
        extension = collection.tail[1:]
        representation = {
            "name": extension,
            "ext": extension,
            "files": list(collection),
            "stagingDir": path
        }
        movie = {
            "name": "mov",
            "ext": "mov",
            "files": os.path.basename(mov_path),
            "stagingDir": path,
            "frameStart": frame_start,
            "frameEnd": frame_end,
            "fps": frame_rate,
            "preview": True,
            "tags": ["review", "ftrackreview"]
        }
        thumbnail = {
            "name": "thumbnail",
            "ext": "png",
            "files": os.path.basename(thumbnail_path),
            "stagingDir": path,
            "tags": ["thumbnail"]
        }
        instance.data["representations"] = [representation, movie, thumbnail]

        # Required for extract_review plugin (L222 onwards).
        instance.data["frameStart"] = frame_start
        instance.data["frameEnd"] = frame_end
        instance.data["fps"] = frame_rate

        self.log.info(f"Extracted {instance} to {path}")
