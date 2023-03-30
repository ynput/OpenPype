import ast

import unreal


def get_params(params, *args):
    params = ast.literal_eval(params)
    if len(args) == 1:
        return params.get(args[0])
    else:
        return tuple(params.get(arg) for arg in args)


def format_string(input_str):
    string = input_str.replace('\\', '/')
    string = string.replace('"', '\\"')
    string = string.replace("'", "\\'")
    return f'"{string}"'


def cast_map_to_str_dict(umap) -> dict:
    """Cast Unreal Map to dict.

    Helper function to cast Unreal Map object to plain old python
    dict. This will also cast values and keys to str. Useful for
    metadata dicts.

    Args:
        umap: Unreal Map object

    Returns:
        dict

    """
    return {str(key): str(value) for (key, value) in umap.items()}


def get_asset(path):
    """
    Args:
        path (str): path to the asset
    """
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    return ar.get_asset_by_object_path(path).get_asset()


def get_subsequences(sequence: unreal.LevelSequence):
    """Get list of subsequences from sequence.

    Args:
        sequence (unreal.LevelSequence): Sequence

    Returns:
        list(unreal.LevelSequence): List of subsequences

    """
    tracks = sequence.get_master_tracks()
    subscene_track = next(
        (
            t
            for t in tracks
            if t.get_class() == unreal.MovieSceneSubTrack.static_class()
        ),
        None,
    )
    if subscene_track is not None and subscene_track.get_sections():
        return subscene_track.get_sections()
    return []
