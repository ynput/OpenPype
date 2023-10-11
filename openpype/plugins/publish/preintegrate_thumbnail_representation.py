""" Marks thumbnail representation for integrate to DB or not.

    Some hosts produce thumbnail representation, most of them do not create
    them explicitly, but they created during extract phase.

    In some cases it might be useful to override implicit setting for host/task

    This plugin needs to run after extract phase, but before integrate.py as
    thumbnail is part of review family and integrated there.

    It should be better to control integration of thumbnail in one place than
    configure it in multiple places on host implementations.
"""
import pyblish.api

from openpype.lib.profiles_filtering import filter_profiles


class PreIntegrateThumbnails(pyblish.api.InstancePlugin):
    """Marks thumbnail representation for integrate to DB or not."""

    label = "Override Integrate Thumbnail Representations"
    order = pyblish.api.IntegratorOrder - 0.1

    integrate_profiles = []

    def process(self, instance):
        repres = instance.data.get("representations")
        if not repres:
            return

        thumbnail_repres = []
        for repre in repres:
            if "thumbnail" in repre.get("tags", []):
                thumbnail_repres.append(repre)

        if not thumbnail_repres:
            return

        family = instance.data["family"]
        subset_name = instance.data["subset"]
        host_name = instance.context.data["hostName"]

        anatomy_data = instance.data["anatomyData"]
        task = anatomy_data.get("task", {})

        found_profile = filter_profiles(
            self.integrate_profiles,
            {
                "hosts": host_name,
                "task_names": task.get("name"),
                "task_types": task.get("type"),
                "families": family,
                "subsets": subset_name,
            },
            logger=self.log
        )

        if not found_profile:
            return

        for thumbnail_repre in thumbnail_repres:
            thumbnail_repre.setdefault("tags", [])

            if not found_profile["integrate_thumbnail"]:
                if "delete" not in thumbnail_repre["tags"]:
                    thumbnail_repre["tags"].append("delete")
            else:
                if "delete" in thumbnail_repre["tags"]:
                    thumbnail_repre["tags"].remove("delete")

            self.log.debug(
                "Thumbnail repre tags {}".format(thumbnail_repre["tags"]))
