# Workfiles App

The Workfiles app facilitates easy saving, creation and launching of work files.

The current supported hosts are:

- Maya
- Houdini
- Fusion

The app is available inside hosts via. the ```Avalon > Work Files``` menu.

## Enabling Workfiles on launch

By default the Workfiles app will not launch on startup, so it has to be explicitly enabled in a config.

```python
workfiles.show()
```

## Naming Files

Workfiles app enables user to easily save and create new work files.

The user is presented with a two parameters; ```version``` and ```comment```. The name of the work file is determined from a template.

### ```Next Available Version```

Will search for the next version number that is not in use.

## Templates

The default template for work files is ```{task[name]}_v{version:0>4}<_{comment}>```. Launching Maya on an animation task and creating a version 1 will result in ```animation_v0001.ma```. Adding "blocking" to the optional comment input will result in ```animation_v0001_blocking.ma```.

This template can be customized per project with the ```workfile``` template.

There are other variables to customize the template with:

```python
{
    "project": project,  # The project data from the database.
    "asset": asset, # The asset data from the database.
    "task": {
        "label": label,  # Label of task chosen.
        "name": name  # Sanitize version of the label.
    },
    "user": user,  # Name of the user on the machine.
    "version": version,  # Chosen version of the user.
    "comment": comment,  # Chosen comment of the user.
}
```

### Optional template groups

The default template contains an optional template group ```<_{comment}>```. If any template group (```{comment}```) within angle bracket ```<>``` does not exist, the whole optional group is discarded.


## Implementing a new host integration for Work Files

For the Work Files tool to work with a new host integration the host must
implement the following functions:

- `file_extensions()`: The files the host should allow to open and show in the Work Files view.
- `open_file(filepath)`: Open a file.
- `save_file(filepath)`: Save the current file. This should return None if it failed to save, and return the path if it succeeded
- `has_unsaved_changes()`: Return whether the current scene has unsaved changes.
- `current_file()`: The path to the current file. None if not saved.
- `work_root()`: The path to where the work files for this app should be saved.

Here's an example code layout:

```python
def file_extensions():
    """Return the filename extension formats that should be shown.

    Note:
        The first entry in the list will be used as the default file
        format to save to when the current scene is not saved yet.

    Returns:
        list: A list of the file extensions supported by Work Files.

    """
    return list()


def has_unsaved_changes():
    """Return whether current file has unsaved modifications."""


def save_file(filepath):
    """Save to filepath.
    
    This should return None if it failed to save, and return the path if it 
    succeeded.
    """
    pass


def open_file(filepath):
    """Open file"""
    pass


def current_file():
    """Return path to currently open file or None if not saved.

    Returns:
        str or None: The full path to current file or None when not saved.

    """
    pass


def work_root():
    """Return the default root for the Host to browse in for Work Files

    Returns:
        str: The path to look in.

    """
    pass
```

#### Work Files Scenes root (AVALON_SCENEDIR)

Whenever the host application has no built-in implementation that defines
where scene files should be saved to then the Work Files API for that host
should fall back to the `AVALON_SCENEDIR` variable in `api.Session`.

When `AVALON_SCENEDIR` is set the  directory is the relative folder inside the 
`AVALON_WORKDIR`. Otherwise, when it is not set or empty it should fall back
to the Work Directory's root, `AVALON_WORKDIR` 

```python
AVALON_WORKDIR="/path/to/work"
AVALON_SCENEDIR="scenes"
# Result: /path/to/work/scenes

AVALON_WORKDIR="/path/to/work"
AVALON_SCENEDIR=None
# Result: /path/to/work
```