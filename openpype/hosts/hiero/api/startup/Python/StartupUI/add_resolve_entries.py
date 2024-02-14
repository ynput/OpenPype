# coding: utf-8

"""
Add user resolve entries
==============================

"""

# Import depandencies
import hiero.core  # noqa


def global_add_resolve_entries(self, resolver):

    # Get resolution
    def get_resolution(task):
        if hasattr(task._item, 'source'):
            width = task._item.source().mediaSource().width()
            height = task._item.source().mediaSource().height()
        else:
            current = task._sequence if task._sequence else task._clip
            width = current.format().width()
            height = current.format().height()
        return str(width), str(height)

    # Add resolver for width
    resolver.addResolver(
        "{width}",
        "Returns the width of the source plate",
        lambda keyword, task: get_resolution(task)[0]
    )

    # Add resolver for height
    resolver.addResolver(
        "{height}",
        "Returns the height of the source plate",
        lambda keyword, task: get_resolution(task)[1]
    )


# This token can be applied to ANY export so add it to the base class
hiero.core.TaskPresetBase.addUserResolveEntries = global_add_resolve_entries
