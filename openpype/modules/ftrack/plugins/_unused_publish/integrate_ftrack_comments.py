import sys
import pyblish.api
import six


class IntegrateFtrackComments(pyblish.api.InstancePlugin):
    """Create comments in Ftrack."""

    order = pyblish.api.IntegratorOrder
    label = "Integrate Comments to Ftrack"
    families = ["shot"]
    enabled = False

    def process(self, instance):
        session = instance.context.data["ftrackSession"]

        entity = session.query(
            "Shot where name is \"{}\"".format(instance.data["item"].name())
        ).one()

        notes = []
        for comment in instance.data["comments"]:
            notes.append(session.create("Note", {"content": comment}))

        entity["notes"].extend(notes)

        try:
            session.commit()
        except Exception:
            tp, value, tb = sys.exc_info()
            session.rollback()
            six.reraise(tp, value, tb)
