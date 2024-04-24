import os
import re
import json
from collections import defaultdict

import substance_painter.project
import substance_painter.resource
import substance_painter.js
import substance_painter.export

from qtpy import QtGui, QtWidgets, QtCore


def get_export_presets():
    """Return Export Preset resource URLs for all available Export Presets.

    Returns:
        dict: {Resource url: GUI Label}

    """
    # TODO: Find more optimal way to find all export templates

    preset_resources = {}
    for shelf in substance_painter.resource.Shelves.all():
        shelf_path = os.path.normpath(shelf.path())

        presets_path = os.path.join(shelf_path, "export-presets")
        if not os.path.exists(presets_path):
            continue

        for filename in os.listdir(presets_path):
            if filename.endswith(".spexp"):
                template_name = os.path.splitext(filename)[0]

                resource = substance_painter.resource.ResourceID(
                    context=shelf.name(),
                    name=template_name
                )
                resource_url = resource.url()

                preset_resources[resource_url] = template_name

    # Sort by template name
    export_templates = dict(sorted(preset_resources.items(),
                                   key=lambda x: x[1]))

    # Add default built-ins at the start
    # TODO: find the built-ins automatically; scraped with https://gist.github.com/BigRoy/97150c7c6f0a0c916418207b9a2bc8f1  # noqa
    result = {
        "export-preset-generator://viewport2d": "2D View",  # noqa
        "export-preset-generator://doc-channel-normal-no-alpha": "Document channels + Normal + AO (No Alpha)",  # noqa
        "export-preset-generator://doc-channel-normal-with-alpha": "Document channels + Normal + AO (With Alpha)",  # noqa
        "export-preset-generator://sketchfab": "Sketchfab",  # noqa
        "export-preset-generator://adobe-standard-material": "Substance 3D Stager",  # noqa
        "export-preset-generator://usd": "USD PBR Metal Roughness",  # noqa
        "export-preset-generator://gltf": "glTF PBR Metal Roughness",  # noqa
        "export-preset-generator://gltf-displacement": "glTF PBR Metal Roughness + Displacement texture (experimental)"  # noqa
    }
    result.update(export_templates)
    return result


def _convert_stack_path_to_cmd_str(stack_path):
    """Convert stack path `str` or `[str, str]` for javascript query

    Example usage:
        >>> stack_path = _convert_stack_path_to_cmd_str(stack_path)
        >>> cmd = f"alg.mapexport.channelIdentifiers({stack_path})"
        >>> substance_painter.js.evaluate(cmd)

    Args:
        stack_path (list or str): Path to the stack, could be
            "Texture set name" or ["Texture set name", "Stack name"]

    Returns:
        str: Stack path usable as argument in javascript query.

    """
    return json.dumps(stack_path)


def get_channel_identifiers(stack_path=None):
    """Return the list of channel identifiers.

    If a context is passed (texture set/stack),
    return only used channels with resolved user channels.

    Channel identifiers are:
        basecolor, height, specular, opacity, emissive, displacement,
        glossiness, roughness, anisotropylevel, anisotropyangle, transmissive,
        scattering, reflection, ior, metallic, normal, ambientOcclusion,
        diffuse, specularlevel, blendingmask, [custom user names].

    Args:
        stack_path (list or str, Optional): Path to the stack, could be
            "Texture set name" or ["Texture set name", "Stack name"]

    Returns:
        list: List of channel identifiers.

    """
    if stack_path is None:
        stack_path = ""
    else:
        stack_path = _convert_stack_path_to_cmd_str(stack_path)
    cmd = f"alg.mapexport.channelIdentifiers({stack_path})"
    return substance_painter.js.evaluate(cmd)


def get_channel_format(stack_path, channel):
    """Retrieve the channel format of a specific stack channel.

    See `alg.mapexport.channelFormat` (javascript API) for more details.

    The channel format data is:
        "label" (str): The channel format label: could be one of
            [sRGB8, L8, RGB8, L16, RGB16, L16F, RGB16F, L32F, RGB32F]
        "color" (bool): True if the format is in color, False is grayscale
        "floating" (bool): True if the format uses floating point
            representation, false otherwise
        "bitDepth" (int): Bit per color channel (could be 8, 16 or 32 bpc)

    Arguments:
        stack_path (list or str): Path to the stack, could be
            "Texture set name" or ["Texture set name", "Stack name"]
        channel (str): Identifier of the channel to export
            (see `get_channel_identifiers`)

    Returns:
        dict: The channel format data.

    """
    stack_path = _convert_stack_path_to_cmd_str(stack_path)
    cmd = f"alg.mapexport.channelFormat({stack_path}, '{channel}')"
    return substance_painter.js.evaluate(cmd)


def get_document_structure():
    """Dump the document structure.

    See `alg.mapexport.documentStructure` (javascript API) for more details.

    Returns:
        dict: Document structure or None when no project is open

    """
    return substance_painter.js.evaluate("alg.mapexport.documentStructure()")


def get_export_templates(config, format="png", strip_folder=True):
    """Return export config outputs.

    This use the Javascript API `alg.mapexport.getPathsExportDocumentMaps`
    which returns a different output than using the Python equivalent
    `substance_painter.export.list_project_textures(config)`.

    The nice thing about the Javascript API version is that it returns the
    output textures grouped by filename template.

    A downside is that it doesn't return all the UDIM tiles but per template
    always returns a single file.

    Note:
        The file format needs to be explicitly passed to the Javascript API
        but upon exporting through the Python API the file format can be based
        on the output preset. So it's likely the file extension will mismatch

    Warning:
        Even though the function appears to solely get the expected outputs
        the Javascript API will actually create the config's texture output
        folder if it does not exist yet. As such, a valid path must be set.

    Example output:
    {
        "DefaultMaterial": {
            "$textureSet_BaseColor(_$colorSpace)(.$udim)": "DefaultMaterial_BaseColor_ACES - ACEScg.1002.png",   # noqa
            "$textureSet_Emissive(_$colorSpace)(.$udim)": "DefaultMaterial_Emissive_ACES - ACEScg.1002.png",     # noqa
            "$textureSet_Height(_$colorSpace)(.$udim)": "DefaultMaterial_Height_Utility - Raw.1002.png",         # noqa
            "$textureSet_Metallic(_$colorSpace)(.$udim)": "DefaultMaterial_Metallic_Utility - Raw.1002.png",     # noqa
            "$textureSet_Normal(_$colorSpace)(.$udim)": "DefaultMaterial_Normal_Utility - Raw.1002.png",         # noqa
            "$textureSet_Roughness(_$colorSpace)(.$udim)": "DefaultMaterial_Roughness_Utility - Raw.1002.png"    # noqa
        }
    }

    Arguments:
        config (dict) Export config
        format (str, Optional): Output format to write to, defaults to 'png'
        strip_folder (bool, Optional): Whether to strip the output folder
            from the output filenames.

    Returns:
        dict: The expected output maps.

    """
    folder = config["exportPath"].replace("\\", "/")
    preset = config["defaultExportPreset"]
    cmd = f'alg.mapexport.getPathsExportDocumentMaps("{preset}", "{folder}", "{format}")'  # noqa
    result = substance_painter.js.evaluate(cmd)

    if strip_folder:
        for _stack, maps in result.items():
            for map_template, map_filepath in maps.items():
                map_filepath = map_filepath.replace("\\", "/")
                assert map_filepath.startswith(folder)
                map_filename = map_filepath[len(folder):].lstrip("/")
                maps[map_template] = map_filename

    return result


def _templates_to_regex(templates,
                        texture_set,
                        colorspaces,
                        project,
                        mesh):
    """Return regex based on a Substance Painter expot filename template.

    This converts Substance Painter export filename templates like
    `$mesh_$textureSet_BaseColor(_$colorSpace)(.$udim)` into a regex
    which can be used to query an output filename to help retrieve:

        - Which template filename the file belongs to.
        - Which color space the file is written with.
        - Which udim tile it is exactly.

    This is used by `get_parsed_export_maps` which tries to as explicitly
    as possible match the filename pattern against the known possible outputs.
    That's why Texture Set name, Color spaces, Project path and mesh path must
    be provided. By doing so we get the best shot at correctly matching the
    right template because otherwise $texture_set could basically be any string
    and thus match even that of a color space or mesh.

    Arguments:
        templates (list): List of templates to convert to regex.
        texture_set (str): The texture set to match against.
        colorspaces (list): The colorspaces defined in the current project.
        project (str): Filepath of current substance project.
        mesh (str): Path to mesh file used in current project.

    Returns:
        dict: Template: Template regex pattern

    """
    def _filename_no_ext(path):
        return os.path.splitext(os.path.basename(path))[0]

    if colorspaces and any(colorspaces):
        colorspace_match = "|".join(re.escape(c) for c in set(colorspaces))
        colorspace_match = f"({colorspace_match})"
    else:
        # No colorspace support enabled
        colorspace_match = ""

    # Key to regex valid search values
    key_matches = {
        "$project": re.escape(_filename_no_ext(project)),
        "$mesh": re.escape(_filename_no_ext(mesh)),
        "$textureSet": re.escape(texture_set),
        "$colorSpace": colorspace_match,
        "$udim": "([0-9]{4})"
    }

    # Turn the templates into regexes
    regexes = {}
    for template in templates:

        # We need to tweak a temp
        search_regex = re.escape(template)

        # Let's assume that any ( and ) character in the file template was
        # intended as an optional template key and do a simple `str.replace`
        # Note: we are matching against re.escape(template) so will need to
        #       search for the escaped brackets.
        search_regex = search_regex.replace(re.escape("("), "(")
        search_regex = search_regex.replace(re.escape(")"), ")?")

        # Substitute each key into a named group
        for key, key_expected_regex in key_matches.items():

            # We want to use the template as a regex basis in the end so will
            # escape the whole thing first. Note that thus we'll need to
            # search for the escaped versions of the keys too.
            escaped_key = re.escape(key)
            key_label = key[1:]  # key without $ prefix

            key_expected_grp_regex = f"(?P<{key_label}>{key_expected_regex})"
            search_regex = search_regex.replace(escaped_key,
                                                key_expected_grp_regex)

        # The filename templates don't include the extension so we add it
        # to be able to match the out filename beginning to end
        ext_regex = r"(?P<ext>\.[A-Za-z][A-Za-z0-9-]*)"
        search_regex = rf"^{search_regex}{ext_regex}$"

        regexes[template] = search_regex

    return regexes


def strip_template(template, strip="._ "):
    """Return static characters in a substance painter filename template.

    >>> strip_template("$textureSet_HELLO(.$udim)")
    # HELLO
    >>> strip_template("$mesh_$textureSet_HELLO_WORLD_$colorSpace(.$udim)")
    # HELLO_WORLD
    >>> strip_template("$textureSet_HELLO(.$udim)", strip=None)
    # _HELLO
    >>> strip_template("$mesh_$textureSet_$colorSpace(.$udim)", strip=None)
    # _HELLO_
    >>> strip_template("$textureSet_HELLO(.$udim)")
    # _HELLO

    Arguments:
        template (str): Filename template to strip.
        strip (str, optional): Characters to strip from beginning and end
            of the static string in template. Defaults to: `._ `.

    Returns:
        str: The static string in filename template.

    """
    # Return only characters that were part of the template that were static.
    # Remove all keys
    keys = ["$project", "$mesh", "$textureSet", "$udim", "$colorSpace"]
    stripped_template = template
    for key in keys:
        stripped_template = stripped_template.replace(key, "")

    # Everything inside an optional bracket space is excluded since it's not
    # static. We keep a counter to track whether we are currently iterating
    # over parts of the template that are inside an 'optional' group or not.
    counter = 0
    result = ""
    for char in stripped_template:
        if char == "(":
            counter += 1
        elif char == ")":
            counter -= 1
            if counter < 0:
                counter = 0
        else:
            if counter == 0:
                result += char

    if strip:
        # Strip of any trailing start/end characters. Technically these are
        # static but usually start and end separators like space or underscore
        # aren't wanted.
        result = result.strip(strip)

    return result


def get_parsed_export_maps(config):
    """Return Export Config's expected output textures with parsed data.

    This tries to parse the texture outputs using a Python API export config.

    Parses template keys: $project, $mesh, $textureSet, $colorSpace, $udim

    Example:
    {("DefaultMaterial", ""): {
        "$mesh_$textureSet_BaseColor(_$colorSpace)(.$udim)": [
                {
                    // OUTPUT DATA FOR FILE #1 OF THE TEMPLATE
                },
                {
                    // OUTPUT DATA FOR FILE #2 OF THE TEMPLATE
                },
            ]
        },
    }}

    File output data (all outputs are `str`).
    1) Parsed tokens: These are parsed tokens from the template, they will
        only exist if found in the filename template and output filename.

        project: Workfile filename without extension
        mesh: Filename of the loaded mesh without extension
        textureSet: The texture set, e.g. "DefaultMaterial",
        colorSpace: The color space, e.g. "ACES - ACEScg",
        udim: The udim tile, e.g. "1001"

    2) Template output and filepath

        filepath: Full path to the resulting texture map, e.g.
            "/path/to/mesh_DefaultMaterial_BaseColor_ACES - ACEScg.1002.png",
        output: "mesh_DefaultMaterial_BaseColor_ACES - ACEScg.1002.png"
            Note: if template had slashes (folders) then `output` will too.
                  So `output` might include a folder.

    Returns:
        dict: [texture_set, stack]: {template: [file1_data, file2_data]}

    """
    # Import is here to avoid recursive lib <-> colorspace imports
    from .colorspace import get_project_channel_data

    outputs = substance_painter.export.list_project_textures(config)
    templates = get_export_templates(config, strip_folder=False)

    # Get all color spaces set for the current project
    project_colorspaces = set(
        data["colorSpace"] for data in get_project_channel_data().values()
    )

    # Get current project mesh path and project path to explicitly match
    # the $mesh and $project tokens
    project_mesh_path = substance_painter.project.last_imported_mesh_path()
    project_path = substance_painter.project.file_path()

    # Get the current export path to strip this of the beginning of filepath
    # results, since filename templates don't have these we'll match without
    # that part of the filename.
    export_path = config["exportPath"]
    export_path = export_path.replace("\\", "/")
    if not export_path.endswith("/"):
        export_path += "/"

    # Parse the outputs
    result = {}
    for key, filepaths in outputs.items():
        texture_set, stack = key

        if stack:
            stack_path = f"{texture_set}/{stack}"
        else:
            stack_path = texture_set

        stack_templates = list(templates[stack_path].keys())

        template_regex = _templates_to_regex(stack_templates,
                                             texture_set=texture_set,
                                             colorspaces=project_colorspaces,
                                             mesh=project_mesh_path,
                                             project=project_path)

        # Let's precompile the regexes
        for template, regex in template_regex.items():
            template_regex[template] = re.compile(regex)

        stack_results = defaultdict(list)
        for filepath in sorted(filepaths):
            # We strip explicitly using the full parent export path instead of
            # using `os.path.basename` because export template is allowed to
            # have subfolders in its template which we want to match against
            filepath = filepath.replace("\\", "/")
            assert filepath.startswith(export_path), (
                f"Filepath {filepath} must start with folder {export_path}"
            )
            filename = filepath[len(export_path):]

            for template, regex in template_regex.items():
                match = regex.match(filename)
                if match:
                    parsed = match.groupdict(default={})

                    # Include some special outputs for convenience
                    parsed["filepath"] = filepath
                    parsed["output"] = filename

                    stack_results[template].append(parsed)
                    break
            else:
                raise ValueError(f"Unable to match {filename} against any "
                                 f"template in: {list(template_regex.keys())}")

        result[key] = dict(stack_results)

    return result


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


def _get_new_project_action():
    """Return QAction which triggers Substance Painter's new project dialog"""

    main_window = substance_painter.ui.get_main_window()

    # Find the file menu's New file action
    menubar = main_window.menuBar()
    new_action = None
    for action in menubar.actions():
        menu = action.menu()
        if not menu:
            continue

        if menu.objectName() != "file":
            continue

        # Find the action with the CTRL+N key sequence
        new_action = next(action for action in menu.actions()
                          if action.shortcut() == QtGui.QKeySequence.New)
        break

    return new_action


def prompt_new_file_with_mesh(mesh_filepath):
    """Prompts the user for a new file using Substance Painter's own dialog.

    This will set the mesh path to load to the given mesh and disables the
    dialog box to disallow the user to change the path. This way we can allow
    user configuration of a project but set the mesh path ourselves.

    Warning:
        This is very hacky and experimental.

    Note:
       If a project is currently open using the same mesh filepath it can't
       accurately detect whether the user had actually accepted the new project
       dialog or whether the project afterwards is still the original project,
       for example when the user might have cancelled the operation.

    """

    app = QtWidgets.QApplication.instance()
    assert os.path.isfile(mesh_filepath), \
        f"Mesh filepath does not exist: {mesh_filepath}"

    def _setup_file_dialog():
        """Set filepath in QFileDialog and trigger accept result"""
        file_dialog = app.activeModalWidget()
        assert isinstance(file_dialog, QtWidgets.QFileDialog)

        # Quickly hide the dialog
        file_dialog.hide()
        app.processEvents(QtCore.QEventLoop.ExcludeUserInputEvents, 1000)

        file_dialog.setDirectory(os.path.dirname(mesh_filepath))
        url = QtCore.QUrl.fromLocalFile(os.path.basename(mesh_filepath))
        file_dialog.selectUrl(url)
        # TODO: find a way to improve the process event to
        # load more complicated mesh
        app.processEvents(QtCore.QEventLoop.ExcludeUserInputEvents, 3000)

        file_dialog.done(file_dialog.Accepted)
        app.processEvents(QtCore.QEventLoop.AllEvents)

    def _setup_prompt():
        app.processEvents(QtCore.QEventLoop.ExcludeUserInputEvents)
        dialog = app.activeModalWidget()
        assert dialog.objectName() == "NewProjectDialog"

        # Set the window title
        mesh = os.path.basename(mesh_filepath)
        dialog.setWindowTitle(f"New Project with mesh: {mesh}")

        # Get the select mesh file button
        mesh_select = dialog.findChild(QtWidgets.QPushButton, "meshSelect")

        # Hide the select mesh button to the user to block changing of mesh
        mesh_select.setVisible(False)

        # Ensure UI is visually up-to-date
        app.processEvents(QtCore.QEventLoop.ExcludeUserInputEvents, 8000)

        # Trigger the 'select file' dialog to set the path and have the
        # new file dialog to use the path.
        QtCore.QTimer.singleShot(10, _setup_file_dialog)
        mesh_select.click()

        app.processEvents(QtCore.QEventLoop.AllEvents, 5000)

        mesh_filename = dialog.findChild(QtWidgets.QFrame, "meshFileName")
        mesh_filename_label = mesh_filename.findChild(QtWidgets.QLabel)
        if not mesh_filename_label.text():
            dialog.close()
            substance_painter.logging.warning(
                "Failed to set mesh path with the prompt dialog:"
                f"{mesh_filepath}\n\n"
                "Creating new project directly with the mesh path instead.")

    new_action = _get_new_project_action()
    if not new_action:
        raise RuntimeError("Unable to detect new file action..")

    QtCore.QTimer.singleShot(0, _setup_prompt)
    new_action.trigger()
    app.processEvents(QtCore.QEventLoop.AllEvents, 5000)

    if not substance_painter.project.is_open():
        return

    # Confirm mesh was set as expected
    project_mesh = substance_painter.project.last_imported_mesh_path()
    if os.path.normpath(project_mesh) != os.path.normpath(mesh_filepath):
        return

    return project_mesh
