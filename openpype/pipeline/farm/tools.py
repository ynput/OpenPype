import os


def get_published_workfile_instance(context):
    """Find workfile instance in context"""
    for i in context:
        is_workfile = (
            "workfile" in i.data.get("families", []) or
            i.data["family"] == "workfile"
        )
        if not is_workfile:
            continue

        # test if there is instance of workfile waiting
        # to be published.
        if i.data["publish"] is not True:
            continue

        return i


def from_published_scene(instance, replace_in_path=True):
    """Switch work scene for published scene.

    If rendering/exporting from published scenes is enabled, this will
    replace paths from working scene to published scene.

    Args:
        instance (pyblish.api.Instance): Instance data to process.
        replace_in_path (bool): if True, it will try to find
            old scene name in path of expected files and replace it
            with name of published scene.

    Returns:
        str: Published scene path.
        None: if no published scene is found.

    Note:
        Published scene path is actually determined from project Anatomy
        as at the time this plugin is running the scene can be still
        un-published.

    """
    workfile_instance = get_published_workfile_instance(instance.context)
    if workfile_instance is None:
        return

    # determine published path from Anatomy.
    template_data = workfile_instance.data.get("anatomyData")
    rep = workfile_instance.data["representations"][0]
    template_data["representation"] = rep.get("name")
    template_data["ext"] = rep.get("ext")
    template_data["comment"] = None

    anatomy = instance.context.data['anatomy']
    template_obj = anatomy.templates_obj["publish"]["path"]
    template_filled = template_obj.format_strict(template_data)
    file_path = os.path.normpath(template_filled)

    if not os.path.exists(file_path):
        raise

    if not replace_in_path:
        return file_path

    # now we need to switch scene in expected files
    # because <scene> token will now point to published
    # scene file and that might differ from current one
    def _clean_name(path):
        return os.path.splitext(os.path.basename(path))[0]

    new_scene = _clean_name(file_path)
    orig_scene = _clean_name(instance.context.data["currentFile"])
    expected_files = instance.data.get("expectedFiles")

    if isinstance(expected_files[0], dict):
        # we have aovs and we need to iterate over them
        new_exp = {}
        for aov, files in expected_files[0].items():
            replaced_files = []
            for f in files:
                replaced_files.append(
                    str(f).replace(orig_scene, new_scene)
                )
            new_exp[aov] = replaced_files
        # [] might be too much here, TODO
        instance.data["expectedFiles"] = [new_exp]
    else:
        new_exp = []
        for f in expected_files:
            new_exp.append(
                str(f).replace(orig_scene, new_scene)
            )
        instance.data["expectedFiles"] = new_exp

    metadata_folder = instance.data.get("publishRenderMetadataFolder")
    if metadata_folder:
        metadata_folder = metadata_folder.replace(orig_scene,
                                                  new_scene)
        instance.data["publishRenderMetadataFolder"] = metadata_folder

    return file_path


def iter_expected_files(exp):
    if isinstance(exp[0], dict):
        for _aov, files in exp[0].items():
            for file in files:
                yield file
    else:
        for file in exp:
            yield file
