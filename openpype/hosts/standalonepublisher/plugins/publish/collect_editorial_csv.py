from copy import copy, deepcopy
import re
import os
import csv
from pprint import pformat
import pyblish.api
from openpype.lib.transcoding import (
    VIDEO_EXTENSIONS, IMAGE_EXTENSIONS
)
from openpype.client import get_asset_by_name
from openpype.pipeline.create import get_subset_name
from openpype.pipeline import (
    publish
)
import clique


class CollectEditorialCSV(
    pyblish.api.InstancePlugin,
    publish.ColormanagedPyblishPluginMixin
):
    """Collect Editorial CSV"""

    order = pyblish.api.CollectorOrder + 0.002
    label = ">>>> Collect Editorial CSV"
    hosts = ["standalonepublisher"]
    families = ["editorialcsv"]

    # variables
    csv_delimiter = ","
    tags_delimiter = ";"
    default_tags = ["review"]

    # configs
    columns_config = None
    representation_config = None

    def process(self, instance):
        context = instance.context

        passing_instance_data = {
            _key: _value for _key, _value in instance.data.items()
            if _key in [
                "asset", "family", "subset", "label", "publish", "source"
            ]
        }
        # get representation with editorial file
        for representation in instance.data["representations"]:
            # make editorial sequence file path
            staging_dir = representation["stagingDir"]
            csv_file_path = os.path.join(
                staging_dir, str(representation["files"])
            )
            _, extension = os.path.splitext(
                os.path.basename(csv_file_path)
            )
            if extension != ".csv":
                raise TypeError(
                    "Editorial CSV file must have .csv extension."
                )

            # create new instance from the csv editorial file via self function
            self._create_new_instance(
                context,
                csv_file_path,
                passing_instance_data
            )

            # from special function get all data from csv file and convert them to new instances
            csv_data_for_instances = self._get_data_from_csv(
                context,
                csv_file_path,
            )

            # create instances from csv data via self function
            self._create_instances_from_csv_data(
                context, csv_data_for_instances,
                passing_instance_data, staging_dir
            )

        # remove incoming instance from the context
        context.remove(instance)

    def _create_instances_from_csv_data(
        self,
        context,
        csv_data_for_instances,
        passing_instance_data,
        staging_dir
    ):
        """Create instances from csv data"""

        for asset_name, _data in csv_data_for_instances.items():
            asset_doc = _data["asset_doc"]
            vendor_name = _data["vendor_name"]
            products = _data["products"]

            for instance_name, product_data in products.items():
                # get important instance variables
                task_name = product_data["task_name"]
                variant_name = product_data["variant_name"]
                product_type = product_data["product_type"]
                version = product_data["version"]

                # create subset/product name
                product_name = get_subset_name(
                    product_type,
                    variant_name,
                    task_name,
                    asset_doc,
                )

                # make sure frame start/end is inherited from csv columns
                # if they exists or inherit them from asset doc for case where
                # columns are missing because only mov or mp4 files needs to be
                # published
                frame_start = None
                frame_end = None
                comment = None
                intent = None
                for filepath, repre_data in product_data["representations"].items():
                    if not comment and repre_data["notes"]:
                        comment = repre_data["notes"]
                    if not intent and repre_data["intent"]:
                        intent = repre_data["intent"]
                        if intent:
                            comment = f"{intent}: {comment}"

                    extension = os.path.splitext(filepath)[-1]
                    if extension in [".mp4"]:
                        continue
                    if not frame_start and repre_data["frameStart"]:
                        frame_start = repre_data["frameStart"]
                    if not frame_end and repre_data["frameEnd"]:
                        frame_end = repre_data["frameEnd"]

                if not frame_start:
                    frame_start = asset_doc["data"]["frameStart"]
                if not frame_end:
                    frame_end = asset_doc["data"]["frameEnd"]

                # get representations from product data
                representations = product_data["representations"]
                label = f"{asset_name}_{product_name}_v{version:>03}"

                # make product data
                product_data = {
                    "asset": asset_name,
                    "subset": product_name,
                    "family": product_type,
                    "families": ["csv", "ftrack"],
                    "assetEntity": asset_doc,
                    "label": label,
                    "publish": True,
                    "task": task_name,
                    "variant": variant_name,
                    "source": passing_instance_data["source"],
                    "user": vendor_name,
                    "representations": [],
                    "frameStart": frame_start,
                    "frameEnd": frame_end,
                    "version": version,
                    "comment": comment,
                }

                # create new instance
                new_instance = context.create_instance(
                    instance_name, family=product_type,
                )
                # pass data from original instance to the new one
                new_instance.data.update(product_data)

                for filepath, repre_data in representations.items():
                    # get representation data
                    representation_data = self._get_representation_data(
                        context, filepath, repre_data, staging_dir
                    )
                    # add representation to the new instance
                    new_instance.data["representations"].append(
                        representation_data)

                # update instance data frame Start and End with representation
                # this is for case when Start and End columns are missing
                # since sequence representation will have frameStart and frameEnd
                # we can override asset_doc frameStart and frameEnd
                repre_frame_start = None
                repre_frame_end = None
                for repre in new_instance.data["representations"]:
                    if repre.get("frameStart") and repre.get("frameEnd"):
                        repre_frame_start = repre["frameStart"]
                        repre_frame_end = repre["frameEnd"]
                        break

                if repre_frame_start and repre_frame_end:
                    new_instance.data["frameStart"] = repre_frame_start
                    new_instance.data["frameEnd"] = repre_frame_end

                    # for thumbnail creation
                    thumb_index = 0
                    if "slate" in repre_data and repre_data["slate"]:
                        thumb_index += 1
                    thumbnail_source = os.path.join(
                        repre["stagingDir"], repre["files"][thumb_index]
                    )
                else:
                    thumbnail_source = os.path.join(
                        repre["stagingDir"], repre["files"]
                    )

                new_instance.data["thumbnailSource"] = thumbnail_source

                self.log.debug(
                    f"__ new_instance.data: `{pformat(new_instance.data)}`")

    def _get_representation_data(
        self, context, filepath, repre_data, staging_dir
    ):
        """Get representation data"""
        context = deepcopy(context)
        # change hostName to Traypublisher for colorspace validation
        context.data["hostName"] = "traypublisher"

        # get extension of file
        basename = os.path.basename(filepath)
        _, extension = os.path.splitext(filepath)

        # validate filepath is having correct extension based on output
        config_repre_data = self.config_representation_data()
        output = repre_data["output"]
        if output not in config_repre_data:
            raise KeyError(
                f"Output '{output}' not found in config representation data."
            )
        validate_extensions = config_repre_data[output]["extensions"]
        if extension not in validate_extensions:
            raise TypeError(
                f"File extension '{extension}' not valid for "
                f"output '{validate_extensions}'."
            )

        is_sequence = (extension in IMAGE_EXTENSIONS)
        # convert ### string in file name to %03d
        # this is for correct frame range validation
        # example: file.###.exr -> file.%03d.exr
        if "#" in basename:
            padding = len(basename.split("#")) - 1
            basename = basename.replace("#"*padding, f"%0{padding}d")
            is_sequence = True

        # make absolute path to file
        absfilepath = os.path.normpath(os.path.join(staging_dir, filepath))
        dirname = os.path.dirname(absfilepath)

        # check if dirname exists
        if not os.path.isdir(dirname):
            raise NotADirectoryError(
                f"Directory '{dirname}' does not exist."
            )

        # collect all data from dirname
        paths_for_collection = []
        for file in os.listdir(dirname):
            filepath = os.path.join(dirname, file)
            paths_for_collection.append(filepath)

        collections, _ = clique.assemble(paths_for_collection)

        if collections:
            collections = collections[0]
        else:
            if is_sequence:
                raise ValueError(
                    f"No collections found in directory '{dirname}'."
                )

        frame_start = None
        frame_end = None
        if is_sequence:
            files = [os.path.basename(file) for file in collections]
            frame_start = list(collections.indexes)[0]
            frame_end = list(collections.indexes)[-1]
        else:
            files = basename

        tags = deepcopy(repre_data["tags"])
        # if slate in repre_data is True then remove one frame from start
        if repre_data["slate"]:
            tags.append("has_slate")

        # get representation data
        representation_data = {
            "name": output,
            "ext": extension[1:],
            "files": files,
            "stagingDir": dirname,
            "stagingDir_persistent": True,
            "tags": tags,
        }
        if extension in VIDEO_EXTENSIONS:
            representation_data.update({
                "fps": 25,
                "outputName": output,
            })

        if frame_start:
            representation_data["frameStart"] = frame_start
        if frame_end:
            representation_data["frameEnd"] = frame_end

        self.set_representation_colorspace(
            representation_data,
            context=context,
            colorspace=repre_data["color"]
        )

        return representation_data

    def _get_data_from_csv(
        self, context, csv_file_path
    ):
        """Generate instances from the csv editorial file"""
        # get current project name and code from context.data
        project_doc = context.data["projectEntity"]
        project_name = project_doc["name"]

        # package name from csv file path
        package_folder = os.path.basename(os.path.dirname(csv_file_path))
        self.log.debug(f"__ package_folder: `{package_folder}`")

        # make sure csv file contains columns from following list
        column_config = self.config_columns_data()
        required_columns = [
            name for name, value in column_config.items()
            if value["required"]
        ]
        # get data from csv file
        with open(csv_file_path, "r") as csv_file:
            csv_reader = csv.DictReader(csv_file, delimiter=self.csv_delimiter)

            # fix fieldnames
            # sometimes someone can keep extra space at the start or end of
            # the column name
            all_columns = [" ".join(column.rsplit()) for column in csv_reader.fieldnames]
            # return back fixed fieldnames
            csv_reader.fieldnames = all_columns

            # check if csv file contains all required columns
            if any(column not in all_columns for column in required_columns):
                raise KeyError(
                    f"Missing required columns: {required_columns}"
                )

            csv_data = {}
            # get data from csv file
            for row in csv_reader:
                # get project from row or get default current project
                row_project_name = self._get_row_value_with_validation(
                    "Project", row, column_config,
                    default_value=project_name
                )

                # raise if row project name is not equal to current project name
                if row_project_name != project_name:
                    raise ValueError(
                        f"Project name in csv file '{row_project_name}' "
                        "must be equal to current project name: "
                        f"{project_name}"
                    )
                # get Package row value
                package = self._get_row_value_with_validation(
                    "Package", row, column_config, default_value=package_folder)

                if (package and package != package_folder):
                    raise ValueError(
                        f"Package name in csv file '{package}' "
                        "must be equal to package folder name: "
                        f"{package_folder}"
                    )

                row_vendor_name = self._get_row_value_with_validation(
                    "Vendor", row, column_config,
                    default_value=context.data["user"]
                )

                # get related shot asset
                context_asset_name = self._get_row_value_with_validation(
                    "Context", row, column_config)

                # get Task row value
                task_name = self._get_row_value_with_validation(
                    "Task", row, column_config)

                # get Variant row value
                variant_name = self._get_row_value_with_validation(
                    "Variant", row, column_config)

                # get Family row value
                product_type = self._get_row_value_with_validation(
                    "Family", row, column_config)

                # get Version row value
                version = self._get_row_value_with_validation(
                    "Version", row, column_config)

                pre_product_name = (
                    f"{task_name}{variant_name}{product_type}"
                    f"{version}".replace(" ", "").lower()
                )

                # get representation data
                filename, representation_data = \
                    self._get_representation_row_data(
                        row, column_config)

                # get all csv data into one dict and make sure there are no duplicates
                # data are already validated and sorted under correct existing asset
                # also check if asset exists and if task name is valid task in asset doc
                # and representations are distributed under products following variants
                if context_asset_name not in csv_data:
                    asset_doc = get_asset_by_name(project_name, context_asset_name)
                    # make sure asset exists
                    if not asset_doc:
                        raise ValueError(
                            f"Asset '{context_asset_name}' not found."
                        )
                    # check if task name is valid task in asset doc
                    if task_name not in asset_doc["data"]["tasks"]:
                        raise ValueError(
                            f"Task '{task_name}' not found in asset doc."
                        )

                    csv_data[context_asset_name] = {
                        "asset_doc": asset_doc,
                        "vendor_name": row_vendor_name,
                        "products": {
                            pre_product_name: {
                                "task_name": task_name,
                                "variant_name": variant_name,
                                "product_type": product_type,
                                "version": version,
                                "representations": {
                                    filename: representation_data,
                                },
                            }
                        }
                    }
                else:
                    asset_doc = csv_data[context_asset_name]["asset_doc"]
                    csv_products = csv_data[context_asset_name]["products"]
                    if pre_product_name not in csv_products:
                        csv_products[pre_product_name] = {
                            "task_name": task_name,
                            "variant_name": variant_name,
                            "product_type": product_type,
                            "version": version,
                            "representations": {
                                filename: representation_data,
                            },
                        }
                    else:
                        csv_representations = \
                            csv_products[pre_product_name]["representations"]
                        if filename in csv_representations:
                            raise ValueError(
                                f"Duplicate filename '{filename}' in csv file."
                            )
                        csv_representations[filename] = representation_data

        return csv_data

    def _get_representation_row_data(self, row_data, column_config):
        # get Filename row value
        filename = self._get_row_value_with_validation(
            "Filename", row_data, column_config)
        # get Version row value
        version = self._get_row_value_with_validation(
            "Version", row_data, column_config)
        # get Color row value
        color = self._get_row_value_with_validation(
            "Color", row_data, column_config)
        # get Notes row value
        notes = self._get_row_value_with_validation(
            "Notes", row_data, column_config)
        # get Intent row value
        intent = self._get_row_value_with_validation(
            "Intent", row_data, column_config)
        # get Output row value
        output = self._get_row_value_with_validation(
            "Output", row_data, column_config)
        # get Slate row value
        slate = self._get_row_value_with_validation(
            "Slate", row_data, column_config)
        # get Tag row value
        tags = self._get_row_value_with_validation(
            "Tags", row_data, column_config)

        # convert tags value to list
        tags_list = copy(self.default_tags)
        if tags:
            # strip spaces from tags
            if self.tags_delimiter in tags:
                tags = tags.split(self.tags_delimiter)
                for _tag in tags:
                    tags_list.append(("".join(_tag.strip())).lower())
            else:
                tags_list.append(("".join(tags.strip())).lower())

        # get Start row value
        frame_start = self._get_row_value_with_validation(
            "Start", row_data, column_config)
        # get End row value
        frame_end = self._get_row_value_with_validation(
            "End", row_data, column_config)

        frame_length = self._get_row_value_with_validation(
            "Length", row_data, column_config)

        representation_data = {
            "version": int(version),
            "color": color,
            "notes": notes,
            "intent": intent,
            "output": output,
            "slate": slate,
            "tags": tags_list,
            "frameStart": int(frame_start) if frame_start else None,
            "frameEnd": int(frame_end) if frame_end else None,
            "frameLength": int(frame_length) if frame_length else None,
        }
        return filename, representation_data

    def _get_row_value_with_validation(
        self, column_name, row_data, column_config, default_value=None
    ):
        """Get row value with validation"""
        # get column data from column config
        column_data = column_config.get(column_name)
        if not column_data:
            raise KeyError(
                f"Column '{column_name}' not found in column config."
            )

        # get column value from row
        column_value = row_data.get(column_name)
        # get column type
        column_type = column_data["type"]
        # get column validation regex
        column_validation = column_data["validate"]
        # get column default value
        column_default = default_value or column_data["default"]

        if column_type == "number" and column_default == 0:
            column_default = None

        # check if column value is not empty string
        if column_value == "":
            # set default value if column value is empty string
            column_value = column_default

        # set column value to correct type following column type
        if column_type == "number" and column_value != None:
            column_value = int(column_value)
        elif column_type == "bool":
            column_value = column_value in ["true", "True"]

        # check if column value matches validation regex
        if (
            column_value != None and
            not re.match(str(column_validation), str(column_value))
        ):
            raise ValueError(
                f"Column '{column_name}' value '{column_value}' "
                f"does not match validation regex '{column_validation}' \n"
                f"Row data: {row_data} \n"
                f"Column data: {column_data}"
            )

        return column_value

    def _create_new_instance(
        self, context, csv_file_path, passing_instance_data
    ):
        """Create new instance from the csv editorial file"""
        dirname, filename = os.path.split(csv_file_path)
        basename, _ = os.path.splitext(filename)

        representation = {
            "name": "csv",
            "ext": "csv",
            "files": filename,
            "stagingDir": dirname,
        }

        # create new instance from the csv editorial file
        new_instance = context.create_instance(
            basename, family="editorial_csv",
        )
        # pass data from original instance to the new one
        new_instance.data.update(passing_instance_data)

        new_instance.data.update({
            "label": f"CSV: {filename}",
            "subset": (
                passing_instance_data["subset"] + basename.replace("_", "")),
            "representations": [representation],
            "stagingDir": dirname,
            "stagingDir_persistent": True,
        })

    def config_columns_data(self):
        if self.columns_config:
            return self.columns_config
        return {
            "Project": {
                "type": "text",
                "default": "",
                "required": False,
                "validate": "^(.*)$"
            },
            "Vendor": {
                "type": "text",
                "default": "",
                "required": False,
                "validate": "^(.*)$"
            },
            "Package": {
                "type": "text",
                "default": "",
                "required": False,
                "validate": "^(.*)$"
            },
            "Filename": {
                "type": "text",
                "default": "",
                "required": False,
                "validate": "^(.*)$"
            },
            "Context": {
                "type": "text",
                "default": "",
                "required": False,
                "validate": "^(.*)$"
            },
            "Task": {
                "type": "text",
                "default": "",
                "required": False,
                "validate": "^(.*)$"
            },
            "Version": {
                "type": "number",
                "default": 1,
                "required": True,
                "validate": "^(\\d{1,3})$"
            },
            "Color": {
                "type": "text",
                "default": "",
                "required": False,
                "validate": "^(.*)$"
            },
            "Notes": {
                "type": "text",
                "default": "",
                "required": False,
                "validate": "^(.*)$"
            },
            "Intent": {
                "type": "text",
                "default": "",
                "required": False,
                "validate": "^(.*)$"
            },
            "Output": {
                "type": "text",
                "default": "",
                "required": False,
                "validate": "^(.*)$"
            },
            "Family": {
                "type": "text",
                "default": "",
                "required": False,
                "validate": "^(.*)$"
            },
            "Slate": {
                "type": "bool",
                "default": True,
                "required": False,
                "validate": "(true|false)"
            },
            "Tags": {
                "type": "text",
                "default": "",
                "required": False,
                "validate": "^(.*)$"
            },
            "Variant": {
                "type": "text",
                "default": "",
                "required": False,
                "validate": "^(.*)$"
            },
            "Start": {
                "type": "number",
                "default": 0,
                "required": False,
                "validate": "^(\\d{1,8})$|None"
            },
            "End": {
                "type": "number",
                "default": 0,
                "required": False,
                "validate": "^(\\d{1,8})$|None"
            },
            "Length": {
                "type": "number",
                "default": 0,
                "required": False,
                "validate": "^(\\d{1,8})$|None"
            }
        }

    def config_representation_data(self):
        if self.representation_config:
            return self.representation_config
        return {
            "preview": {
                "extensions": [".mp4", ".mov"]
            },
            "exr": {
                "extensions": [".exr"]
            },
            "edit": {
                "extensions": [".mov"]
            },
            "review": {
                "extensions": [".mov"]
            },
            "nuke": {
                "extensions": [".nk"]
            }
        }
