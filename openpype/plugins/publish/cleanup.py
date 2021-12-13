# -*- coding: utf-8 -*-
"""Cleanup leftover files from publish."""
import os
import shutil
import pyblish.api
import re


class CleanUp(pyblish.api.InstancePlugin):
    """Cleans up the staging directory after a successful publish.

    This will also clean published renders and delete their parent directories.

    """

    order = pyblish.api.IntegratorOrder + 10
    label = "Clean Up"
    hosts = [
        "aftereffects",
        "blender",
        "celaction",
        "flame",
        "fusion",
        "harmony",
        "hiero",
        "houdini",
        "maya",
        "nuke",
        "photoshop",
        "resolve",
        "tvpaint",
        "unreal",
        "standalonepublisher",
        "webpublisher",
        "shell"
    ]
    exclude_families = ["clip"]
    optional = True
    active = True

    # Presets
    paterns = None  # list of regex paterns
    remove_temp_renders = True

    def process(self, instance):
        """Plugin entry point."""
        # Get the errored instances
        failed = []
        for result in instance.context.data["results"]:
            if (result["error"] is not None and result["instance"] is not None
               and result["instance"] not in failed):
                failed.append(result["instance"])
        assert instance not in failed, (
            "Result of '{}' instance were not success".format(
                instance.data["name"]
            )
        )

        _skip_cleanup_filepaths = instance.context.data.get(
            "skipCleanupFilepaths"
        ) or []
        skip_cleanup_filepaths = set()
        for path in _skip_cleanup_filepaths:
            skip_cleanup_filepaths.add(os.path.normpath(path))

        if self.remove_temp_renders:
            self.log.info("Cleaning renders new...")
            self.clean_renders(instance, skip_cleanup_filepaths)

        if [ef for ef in self.exclude_families
                if instance.data["family"] in ef]:
            return
        import tempfile

        temp_root = tempfile.gettempdir()
        staging_dir = instance.data.get("stagingDir", None)

        if not staging_dir:
            self.log.info("Staging dir not set.")
            return

        if not os.path.normpath(staging_dir).startswith(temp_root):
            self.log.info("Skipping cleanup. Staging directory is not in the "
                          "temp folder: %s" % staging_dir)
            return

        if not os.path.exists(staging_dir):
            self.log.info("No staging directory found: %s" % staging_dir)
            return

        self.log.info("Removing staging directory {}".format(staging_dir))
        shutil.rmtree(staging_dir)

    def clean_renders(self, instance, skip_cleanup_filepaths):
        transfers = instance.data.get("transfers", list())

        current_families = instance.data.get("families", list())
        instance_family = instance.data.get("family", None)
        dirnames = []
        transfers_dirs = []

        for src, dest in transfers:
            # fix path inconsistency
            src = os.path.normpath(src)
            dest = os.path.normpath(dest)

            # add src dir into clearing dir paths (regex paterns)
            transfers_dirs.append(os.path.dirname(src))

            # add dest dir into clearing dir paths (regex paterns)
            transfers_dirs.append(os.path.dirname(dest))

            if src in skip_cleanup_filepaths:
                self.log.debug((
                    "Source file is marked to be skipped in cleanup. {}"
                ).format(src))
                continue

            if os.path.normpath(src) != os.path.normpath(dest):
                if instance_family == 'render' or 'render' in current_families:
                    self.log.info("Removing src: `{}`...".format(src))
                    try:
                        os.remove(src)
                    except PermissionError:
                        self.log.warning("Insufficient permission to delete {}".format(src))
                        continue

                    # add dir for cleanup
                    dirnames.append(os.path.dirname(src))

        # clean by regex paterns
        # make unique set
        transfers_dirs = set(transfers_dirs)

        self.log.debug("__ transfers_dirs: `{}`".format(transfers_dirs))
        self.log.debug("__ self.paterns: `{}`".format(self.paterns))
        if self.paterns:
            files = list()
            # get list of all available content of dirs
            for _dir in transfers_dirs:
                if not os.path.exists(_dir):
                    continue
                files.extend([
                    os.path.join(_dir, f)
                    for f in os.listdir(_dir)])

            self.log.debug("__ files: `{}`".format(files))

            # remove all files which match regex patern
            for f in files:
                if os.path.normpath(f) in skip_cleanup_filepaths:
                    continue

                for p in self.paterns:
                    patern = re.compile(p)
                    if not patern.findall(f):
                        continue
                    if not os.path.exists(f):
                        continue

                    self.log.info("Removing file by regex: `{}`".format(f))
                    os.remove(f)

                    # add dir for cleanup
                    dirnames.append(os.path.dirname(f))

        # make unique set
        cleanup_dirs = set(dirnames)

        # clean dirs which are empty
        for dir in cleanup_dirs:
            try:
                os.rmdir(dir)
            except OSError:
                # directory is not empty, skipping
                continue
