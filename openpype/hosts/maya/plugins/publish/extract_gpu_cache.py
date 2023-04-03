import json

from maya import cmds

from openpype.pipeline import publish


class ExtractGPUCache(publish.Extractor):
    """Extract the content of the instance to a GPU cache file."""

    label = "GPU Cache"
    hosts = ["maya"]
    families = ["model", "animation", "pointcache"]
    step = 1.0
    stepSave = 1
    optimize = True
    optimizationThreshold = 40000
    optimizeAnimationsForMotionBlur = True
    writeMaterials = True
    useBaseTessellation = True

    def process(self, instance):
        cmds.loadPlugin("gpuCache", quiet=True)

        staging_dir = self.staging_dir(instance)
        filename = "{}_gpu_cache".format(instance.name)

        # Write out GPU cache file.
        kwargs = {
            "directory": staging_dir,
            "fileName": filename,
            "saveMultipleFiles": False,
            "simulationRate": self.step,
            "sampleMultiplier": self.stepSave,
            "optimize": self.optimize,
            "optimizationThreshold": self.optimizationThreshold,
            "optimizeAnimationsForMotionBlur": (
                self.optimizeAnimationsForMotionBlur
            ),
            "writeMaterials": self.writeMaterials,
            "useBaseTessellation": self.useBaseTessellation
        }
        self.log.debug(
            "Extract {} with:\n{}".format(
                instance[:], json.dumps(kwargs, indent=4, sort_keys=True)
            )
        )
        cmds.gpuCache(instance[:], **kwargs)

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            "name": "gpu_cache",
            "ext": "abc",
            "files": filename + ".abc",
            "stagingDir": staging_dir,
            "outputName": "gpu_cache"
        }

        instance.data["representations"].append(representation)

        self.log.info(
            "Extracted instance {} to: {}".format(instance.name, staging_dir)
        )
