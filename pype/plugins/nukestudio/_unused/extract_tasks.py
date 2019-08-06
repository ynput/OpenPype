from pyblish import api


class ExtractTasks(api.InstancePlugin):
    """Extract tasks."""

    order = api.ExtractorOrder
    label = "Tasks"
    hosts = ["nukestudio"]
    families = ["clip"]
    optional = True

    def filelink(self, src, dst):
        import filecmp
        import os
        import shutil

        import filelink

        # Compare files to check whether they are the same.
        if os.path.exists(dst) and filecmp.cmp(src, dst):
            return

        # Remove existing destination file.
        if os.path.exists(dst):
            os.remove(dst)

        try:
            filelink.create(src, dst, filelink.HARDLINK)
            self.log.debug("Linking: \"{0}\" to \"{1}\"".format(src, dst))
        except WindowsError as e:
            if e.winerror == 17:
                self.log.warning(
                    "File linking failed due to: \"{0}\". "
                    "Resorting to copying instead.".format(e)
                )
                shutil.copy(src, dst)
            else:
                raise e

    def process(self, instance):
        import time
        import os

        import hiero.core.nuke as nuke
        import hiero.exporters as he
        import clique

        task = instance.data["task"]

        hiero_cls = he.FnSymLinkExporter.SymLinkExporter
        if isinstance(task, hiero_cls):
            src = os.path.join(
                task.filepath(),
                task.fileName()
            )
            # Filelink each image file
            if "img" in instance.data["families"]:
                collection = clique.parse(src + " []")
                for f in os.listdir(os.path.dirname(src)):
                    f = os.path.join(os.path.dirname(src), f)

                frame_offset = task.outputRange()[0] - task.inputRange()[0]
                input_range = (
                    int(task.inputRange()[0]), int(task.inputRange()[1]) + 1
                )
                for index in range(*input_range):
                    dst = task.resolvedExportPath() % (index + frame_offset)
                    self.filelink(src % index, dst)
            # Filelink movie file
            if "mov" in instance.data["families"]:
                dst = task.resolvedExportPath()
                self.filelink(src, dst)

        hiero_cls = he.FnTranscodeExporter.TranscodeExporter
        if isinstance(task, hiero_cls):
            task.startTask()
            while task.taskStep():
                time.sleep(1)

            script_path = task._scriptfile
            log_path = script_path.replace(".nk", ".log")
            log_file = open(log_path, "w")
            process = nuke.executeNukeScript(script_path, log_file, True)

            self.poll(process)

            log_file.close()

            if not task._preset.properties()["keepNukeScript"]:
                os.remove(script_path)
                os.remove(log_path)

        hiero_cls = he.FnNukeShotExporter.NukeShotExporter
        if isinstance(task, hiero_cls):
            task.startTask()
            while task.taskStep():
                time.sleep(1)

        hiero_cls = he.FnAudioExportTask.AudioExportTask
        if isinstance(task, hiero_cls):
            task.startTask()
            while task.taskStep():
                time.sleep(1)

        # Fill collection with output
        if "img" in instance.data["families"]:
            collection = instance.data["collection"]
            path = os.path.dirname(collection.format())
            for f in os.listdir(path):
                file_path = os.path.join(path, f).replace("\\", "/")
                if collection.match(file_path):
                    collection.add(file_path)

    def poll(self, process):
        import time

        returnCode = process.poll()

        # if the return code hasn't been set, Nuke is still running
        if returnCode is None:
            time.sleep(1)

            self.poll(process)
