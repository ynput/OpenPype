import os
import re
import json

import substance_painter.resource
import substance_painter.js


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

    Args:
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
