import os
import re
import copy

import ayon_api
from ayon_api.operations import OperationsSession

from openpype.client import get_project
from openpype.client.operations import (
    prepare_workfile_info_update_data,
)
from openpype.pipeline.template_data import (
    get_template_data,
)
from openpype.pipeline.workfile import (
    get_workdir_with_workdir_data,
    get_workfile_template_key,
    get_last_workfile_with_version,
)
from openpype.pipeline.version_start import get_versioning_start
from openpype.tools.ayon_workfiles.abstract import WorkareaFilepathResult


def get_folder_template_data(folder):
    if not folder:
        return {}
    parts = folder["path"].split("/")
    parts.pop(-1)
    hierarchy = "/".join(parts)
    return {
        "asset": folder["name"],
        "folder": {
            "name": folder["name"],
            "type": folder["folderType"],
            "path": folder["path"],
        },
        "hierarchy": hierarchy,
    }


def get_task_template_data(task):
    if not task:
        return {}
    return {
        "task": {
            "name": task["name"],
            "type": task["taskType"]
        }
    }


class FileItem:
    def __init__(self, dirpath, filename, modified, published):
        self.filename = filename
        self.dirpath = dirpath
        self.modified = modified
        self.published = published

    @property
    def filepath(self):
        return os.path.join(self.dirpath, self.filename)

    @classmethod
    def from_dir(cls, dirpath, extensions):
        output = []
        if not dirpath or not os.path.exists(dirpath):
            return output

        for filename in os.listdir(dirpath):
            ext = os.path.splitext(filename)[-1]
            if ext.lower() not in extensions:
                continue
            output.append(cls(
                dirpath,
                filename,
                os.path.getmtime(os.path.join(dirpath, filename))
            ))

        return output


class CommentMatcher(object):
    """Use anatomy and work file data to parse comments from filenames"""
    def __init__(self, extensions, file_template, data):
        self.fname_regex = None

        if "{comment}" not in file_template:
            # Don't look for comment if template doesn't allow it
            return

        # Create a regex group for extensions
        any_extension = "(?:{})".format(
            "|".join(re.escape(ext.lstrip(".")) for ext in extensions)
        )

        # Use placeholders that will never be in the filename
        temp_data = copy.deepcopy(data)
        temp_data["comment"] = "<<comment>>"
        temp_data["version"] = "<<version>>"
        temp_data["ext"] = "<<ext>>"

        fname_pattern = file_template.format_strict(temp_data)
        fname_pattern = re.escape(fname_pattern)

        # Replace comment and version with something we can match with regex
        replacements = {
            "<<comment>>": "(.+)",
            "<<version>>": "[0-9]+",
            "<<ext>>": any_extension,
        }
        for src, dest in replacements.items():
            fname_pattern = fname_pattern.replace(re.escape(src), dest)

        # Match from beginning to end of string to be safe
        fname_pattern = "^{}$".format(fname_pattern)

        self.fname_regex = re.compile(fname_pattern)

    def parse_comment(self, filepath):
        """Parse the {comment} part from a filename"""
        if not self.fname_regex:
            return

        fname = os.path.basename(filepath)
        match = self.fname_regex.match(fname)
        if match:
            return match.group(1)


class WorkareaModel:
    """Workfiles model looking for workfiles in workare folder.

    Workarea folder is usually task and host specific, defined by
    anatomy templates. Is looking for files with extensions defined
    by host integration.
    """

    def __init__(self, control):
        self._control = control
        self._extensions = control.get_workfile_extensions()
        self._base_data = None
        self._fill_data_by_folder_id = {}
        self._task_data_by_folder_id = {}
        self._workdir_by_context = {}

    @property
    def project_name(self):
        return self._control.get_current_project_name()

    def reset(self):
        self._base_data = None
        self._fill_data_by_folder_id = {}
        self._task_data_by_folder_id = {}

    def _get_base_data(self):
        if self._base_data is None:
            base_data = get_template_data(get_project(self.project_name))
            base_data["app"] = self._control.get_host_name()
            self._base_data = base_data
        return copy.deepcopy(self._base_data)

    def _get_folder_data(self, folder_id):
        fill_data = self._fill_data_by_folder_id.get(folder_id)
        if fill_data is None:
            folder = ayon_api.get_folder_by_id(self.project_name, folder_id)
            fill_data = get_folder_template_data(folder)
            self._fill_data_by_folder_id[folder_id] = fill_data
        return copy.deepcopy(fill_data)

    def _get_task_data(self, folder_id, task_id):
        task_data = self._task_data_by_folder_id.setdefault(folder_id, {})
        if task_id not in task_data:
            for task in ayon_api.get_tasks(
                self.project_name, task_ids=[task_id]
            ):
                task_data[task_id] = get_task_template_data(task)
        return copy.deepcopy(task_data[task_id])

    def _prepare_fill_data(self, folder_id, task_id):
        if not folder_id or not task_id:
            return {}

        base_data = self._get_base_data()
        folder_data = self._get_folder_data(folder_id)
        task_data = self._get_task_data(folder_id, task_id)

        base_data.update(folder_data)
        base_data.update(task_data)

        return base_data

    def get_workarea_dir_by_context(self, folder_id, task_id):
        if not folder_id or not task_id:
            return None
        folder_mapping = self._workdir_by_context.setdefault(folder_id, {})
        workdir = folder_mapping.get(task_id)
        if workdir is not None:
            return workdir

        # TODO use entity model to get task info
        workdir_data = self._prepare_fill_data(folder_id, task_id)

        workdir = get_workdir_with_workdir_data(
            workdir_data,
            self.project_name,
            anatomy=self._control.project_anatomy,
        )
        folder_mapping[task_id] = workdir
        return workdir

    def get_file_items(self, folder_id, task_id):
        items = []
        # TODO finish implementation
        if not folder_id or not task_id:
            return items

        workdir = self.get_workarea_dir_by_context(folder_id, task_id)
        if not os.path.exists(workdir):
            return items

        for filename in os.listdir(workdir):
            filepath = os.path.join(workdir, filename)
            if not os.path.isfile(filepath):
                continue

            ext = os.path.splitext(filename)[1].lower()
            if ext not in self._extensions:
                continue

            modified = os.path.getmtime(filepath)
            items.append(
                FileItem(workdir, filename, modified, False)
            )
        return items

    def _get_template_key(self, fill_data):
        task_type = fill_data.get("task", {}).get("type")
        # TODO cache
        return get_workfile_template_key(
            task_type,
            self._control.get_host_name(),
            project_name=self.project_name
        )

    def _get_last_workfile_version(
        self, workdir, file_template, fill_data, extensions
    ):
        version = get_last_workfile_with_version(
            workdir, str(file_template), fill_data, extensions
        )[1]

        if version is None:
            task_info = fill_data.get("task", {})
            version = get_versioning_start(
                self.project_name,
                self._control.get_host_name(),
                task_name=task_info.get("name"),
                task_type=task_info.get("type"),
                family="workfile",
                project_settings=self._control.project_settings,
            )
        else:
            version += 1
        return version

    def _get_comments_from_root(
        self,
        file_template,
        extensions,
        fill_data,
        root,
        current_filename,
    ):
        current_comment = None
        comment_hints = set()
        filenames = []
        if root and os.path.exists(root):
            for filename in os.listdir(root):
                path = os.path.join(root, filename)
                if not os.path.isfile(path):
                    continue

                ext = os.path.splitext(filename)[-1].lower()
                if ext in extensions:
                    filenames.append(filename)

        if not filenames:
            return comment_hints, current_comment

        matcher = CommentMatcher(extensions, file_template, fill_data)

        for filename in filenames:
            comment = matcher.parse_comment(filename)
            if comment:
                comment_hints.add(comment)
                if filename == current_filename:
                    current_comment = comment

        return list(comment_hints), current_comment

    def _get_workdir(self, anatomy, template_key, fill_data):
        template_info = anatomy.templates_obj[template_key]
        directory_template = template_info["folder"]
        return directory_template.format_strict(fill_data).normalized()

    def get_workarea_save_as_data(self, folder_id, task_id):
        folder = None
        task = None
        if folder_id:
            folder = ayon_api.get_folder_by_id(self.project_name, folder_id)
        if task_id:
            task = ayon_api.get_task_by_id(self.project_name, task_id)
        if not folder or not task:
            return {
                "template_key": None,
                "template_has_version": None,
                "template_has_comment": None,
                "ext": None,
                "workdir": None,
                "comment": None,
                "comment_hints": None,
                "last_version": None,
                "extensions": None,
            }

        anatomy = self._control.project_anatomy
        fill_data = self._prepare_fill_data(folder_id, task_id)
        template_key = self._get_template_key(fill_data)

        current_workfile = self._control.get_current_workfile()
        current_filename = None
        current_ext = None
        if current_workfile:
            current_filename = os.path.basename(current_workfile)
            current_ext = os.path.splitext(current_filename)[1].lower()

        extensions = self._extensions
        if not current_ext and extensions:
            current_ext = tuple(extensions)[0]

        workdir = self._get_workdir(anatomy, template_key, fill_data)

        template_info = anatomy.templates_obj[template_key]
        file_template = template_info["file"]

        comment_hints, comment = self._get_comments_from_root(
            file_template,
            extensions,
            fill_data,
            workdir,
            current_filename,
        )
        last_version = self._get_last_workfile_version(
            workdir, file_template, fill_data, extensions)
        str_file_template = str(file_template)
        template_has_version = "{version" in str_file_template
        template_has_comment = "{comment" in str_file_template

        return {
            "template_key": template_key,
            "template_has_version": template_has_version,
            "template_has_comment": template_has_comment,
            "ext": current_ext,
            "workdir": workdir,
            "comment": comment,
            "comment_hints": comment_hints,
            "last_version": last_version,
            "extensions": extensions,
        }

    def fill_workarea_filepath(
        self,
        folder_id,
        task_id,
        extension,
        use_last_version,
        version,
        comment,
    ):
        anatomy = self._control.project_anatomy
        fill_data = self._prepare_fill_data(folder_id, task_id)
        template_key = self._get_template_key(fill_data)

        workdir = self._get_workdir(anatomy, template_key, fill_data)

        template_info = anatomy.templates_obj[template_key]
        file_template = template_info["file"]

        if use_last_version:
            version = self._get_last_workfile_version(
                workdir, file_template, fill_data, self._extensions
            )
        fill_data["version"] = version
        fill_data["ext"] = extension.lstrip(".")

        filename = file_template.format(fill_data)
        if not filename.solved:
            filename = None

        exists = False
        if filename:
            filepath = os.path.join(workdir, filename)
            exists = os.path.exists(filepath)

        if comment:
            fill_data["comment"] = comment

        return WorkareaFilepathResult(
            workdir,
            filename,
            exists
        )


class WorkfileEntitiesModel:
    """Workfile entities model.

    Args:
        control (AbstractWorkfileController): Controller object.
    """

    def __init__(self, control):
        self._control = control
        self._cache = {}

    def _get_workfile_info_identifier(
        self, folder_id, task_id, rootless_path):
        return "_".join([folder_id, task_id, rootless_path])

    def _get_rootless_path(self, filepath):
        anatomy = self._control.project_anatomy

        workdir, filename = os.path.split(filepath)
        success, rootless_dir = anatomy.find_root_template_from_path(workdir)
        return "/".join([
            os.path.normpath(rootless_dir).replace("\\", "/"),
            filename
        ])

    def get_workfile_info(
        self, folder_id, task_id, filepath, rootless_path=None
    ):
        if not folder_id or not task_id or not filepath:
            return None

        if rootless_path is None:
            rootless_path = self._get_rootless_path(filepath)

        # TODO add threadable way to get workfile info
        identifier = self._get_workfile_info_identifier(
            folder_id, task_id, rootless_path)
        info = self._cache.get(identifier)
        if not info:
            for workfile_info in ayon_api.get_workfiles_info(
                self._control.get_current_project_name(),
                task_ids=[task_id],
                fields=["id", "path", "attrib"],
            ):
                workfile_identifier = self._get_workfile_info_identifier(
                    folder_id, task_id, workfile_info["path"]
                )
                self._cache[workfile_identifier] = workfile_info

        return self._cache.get(identifier)

    def save_workfile_info(self, folder_id, task_id, filepath, note):
        rootless_path = self._get_rootless_path(filepath)
        identifier = self._get_workfile_info_identifier(
            folder_id, task_id, rootless_path
        )
        workfile_info = self.get_workfile_info(
            folder_id, task_id, filepath, rootless_path
        )
        if not workfile_info:
            workfile_info = self._create_workfile_doc(
                task_id, rootless_path, note)
            self._cache[identifier] = workfile_info
            return workfile_info

        new_workfile_info = copy.deepcopy(workfile_info)
        attrib = new_workfile_info.setdefault("attrib", {})
        attrib["description"] = note
        update_data = prepare_workfile_info_update_data(
            workfile_info, new_workfile_info
        )
        self._cache[identifier] = new_workfile_info
        if not update_data:
            return

        project_name = self._control.get_current_project_name()

        session = OperationsSession()
        session.update_entity(
            project_name, "workfile", workfile_info["id"], update_data
        )
        session.commit()

    def _create_workfile_doc(self, task_id, rootless_path, note):
        extension = os.path.splitext(rootless_path)[1]

        project_name = self._control.get_current_project_name()

        workfile_info = {
            "path": rootless_path,
            "taskId": task_id,
            "attrib": {
                "extension": extension,
                "description": note
            }
        }

        session = OperationsSession()
        session.create_entity(project_name, "workfile", workfile_info)
        session.commit()
        return workfile_info


class WorkfilesModel:
    """Workfiles model."""

    def __init__(self, control):
        self._control = control
        self._cache = {}

        self._entities_model = WorkfileEntitiesModel(control)
        self._workarea_model = WorkareaModel(control)

    def get_workfile_info(self, folder_id, task_id, filepath):
        return self._entities_model.get_workfile_info(
            folder_id, task_id, filepath
        )

    def save_workfile_info(self, folder_id, task_id, filepath, note):
        return self._entities_model.save_workfile_info(
            folder_id, task_id, filepath, note
        )

    def get_workarea_dir_by_context(self, folder_id, task_id):
        """Workarea dir for passed context.

        The directory path is based on project anatomy templates.

        Args:
            folder_id (str): Folder id.
            task_id (str): Task id.

        Returns:
            Union[str, None]: Workarea dir path or None for invalid context.
        """

        return self._workarea_model.get_workarea_dir_by_context(
            folder_id, task_id)

    def get_workarea_file_items(self, folder_id, task_id):
        """Workfile items for passed context from workarea.

        Args:
            folder_id (Union[str, None]): Folder id.
            task_id (Union[str, None]): Task id.

        Returns:
            list[FileItem]: List of file items matching workarea of passed
                context.
        """

        return self._workarea_model.get_file_items(folder_id, task_id)

    def get_workarea_save_as_data(self, folder_id, task_id):
        return self._workarea_model.get_workarea_save_as_data(
            folder_id, task_id)

    def fill_workarea_filepath(self, *args, **kwargs):
        return self._workarea_model.fill_workarea_filepath(
            *args, **kwargs
        )

    def get_published_file_items(self, folder_id):
        """Published workfiles for passed context.

        Args:
            folder_id (str): Folder id.

        Returns:
            list[FileItem]: List of files for published workfiles.
        """

        # TODO implement
        return []
