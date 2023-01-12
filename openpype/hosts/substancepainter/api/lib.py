import os
import re
import substance_painter.resource


def load_shelf(path, name=None):
    """Add shelf to substance painter (for current application session)

    This will dynamically add a Shelf for the current session. It's good
    to note however that these will *not* persist on restart of the host.

    Note:
        Consider the loaded shelf a static library of resources.

        The shelf will *not* be visible in application preferences in
        Edit > Settings > Libraries.

        The shelf will *not* show in the Assets browser if it has no existing
        assets

        The shelf will *not* be a selectable option for selecting it as a
        destination to import resources too.

    """

    # Ensure expanded path with forward slashes
    path = os.path.expandvars(path)
    path = os.path.abspath(path)
    path = path.replace("\\", "/")

    # Path must exist
    if not os.path.isdir(path):
        raise ValueError(f"Path is not an existing folder: {path}")

    # This name must be unique and must only contain lowercase letters,
    # numbers, underscores or hyphens.
    if name is None:
        name = os.path.basename(path)

    name = name.lower()
    name = re.sub(r"[^a-z0-9_\-]", "_", name)   # sanitize to underscores

    if substance_painter.resource.Shelves.exists(name):
        shelf = next(
            shelf for shelf in substance_painter.resource.Shelves.all()
            if shelf.name() == name
        )
        if os.path.normpath(shelf.path()) != os.path.normpath(path):
            raise ValueError(f"Shelf with name '{name}' already exists "
                             f"for a different path: '{shelf.path()}")

        return

    print(f"Adding Shelf '{name}' to path: {path}")
    substance_painter.resource.Shelves.add(name, path)

    return name
