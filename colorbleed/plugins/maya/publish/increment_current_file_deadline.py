import pyblish.api


class IncrementCurrentFileDeadline(pyblish.api.ContextPlugin):
    """Submit available render layers to Deadline

    Renders are submitted to a Deadline Web Service as
    supplied via the environment variable AVALON_DEADLINE

    """

    label = "Increment current file"
    order = pyblish.api.IntegratorOrder + 9.0
    hosts = ["maya"]
    families = ["colorbleed.renderlayer"]

    def process(self, context):

        from maya import cmds

        from colorbleed.action import get_errored_plugins_from_data

        plugins = get_errored_plugins_from_data(context)

        if any(plugin.__name__ == "MindbenderSubmitDeadline"
                for plugin in plugins):
            raise RuntimeError("Skipping incrementing current file because"
                               "submission to deadline failed.")

        new_filename = self.version_up(context.data["currentFile"])

        cmds.file(rename=new_filename)
        cmds.file(save=True, force=True, type="mayaAscii")

    def version_up(self, filepath):

        import os
        import re

        dirname = os.path.dirname(filepath)
        basename, ext = os.path.splitext(os.path.basename(filepath))

        regex = "[/_.]" + "v" + "\d+"
        matches = re.findall(regex, str(basename), re.IGNORECASE)
        if not len(matches):
            self.log.info("Creating version ...")
            version_str = "_v{number:03d}".format(number=1)
        else:
            version_label = matches[-1:][0]
            basename = basename.strip(version_label)

            current_version = re.search("\d+", version_label).group()
            padding = len(current_version)
            prefix = version_label.split(current_version)[0]

            version_int = int(current_version) + 1
            version_str = '{prefix}{number:0{padding}d}'.format(
                                                        prefix=prefix,
                                                        padding=padding,
                                                        number=version_int)
        # Create new basename
        self.log.info("New version %s" % version_str)
        new_basename = "{}{}{}".format(basename, version_str, ext)

        new_filename = os.path.join(dirname, new_basename)
        new_filename = os.path.normpath(new_filename)

        if new_filename == filepath:
            raise RuntimeError("Created path is the same as current file,"
                               "please let someone no")

        if os.path.exists(new_filename):
            new_filename = self.version_up(new_filename)

        return new_filename
