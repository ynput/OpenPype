import os
import sys
import json
from subprocess import Popen
try:
    import ftrack_api_old as ftrack_api
except Exception:
    import ftrack_api
from pype.api import config
from pype import lib as pypelib
from avalon.vendor.Qt import QtWidgets, QtCore
from avalon import io, api, style, schema
from avalon.tools import lib as parentlib
from . import widget, model

module = sys.modules[__name__]
module.window = None


class Window(QtWidgets.QDialog):
    """Asset creator interface

    """

    def __init__(self, parent=None, context=None):
        super(Window, self).__init__(parent)
        self.context = context
        project_name = io.active_project()
        self.setWindowTitle("Asset creator ({0})".format(project_name))
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        # Validators
        self.valid_parent = False

        self.session = None

        # assets widget
        assets_widget = QtWidgets.QWidget()
        assets_widget.setContentsMargins(0, 0, 0, 0)
        assets_layout = QtWidgets.QVBoxLayout(assets_widget)
        assets = widget.AssetWidget()
        assets.view.setSelectionMode(assets.view.ExtendedSelection)
        assets_layout.addWidget(assets)

        # Outlink
        label_outlink = QtWidgets.QLabel("Outlink:")
        input_outlink = QtWidgets.QLineEdit()
        input_outlink.setReadOnly(True)
        input_outlink.setStyleSheet("background-color: #333333;")
        checkbox_outlink = QtWidgets.QCheckBox("Use outlink")
        # Parent
        label_parent = QtWidgets.QLabel("*Parent:")
        input_parent = QtWidgets.QLineEdit()
        input_parent.setReadOnly(True)
        input_parent.setStyleSheet("background-color: #333333;")

        # Name
        label_name = QtWidgets.QLabel("*Name:")
        input_name = QtWidgets.QLineEdit()
        input_name.setPlaceholderText("<asset name>")

        # Asset Build
        label_assetbuild = QtWidgets.QLabel("Asset Build:")
        combo_assetbuilt = QtWidgets.QComboBox()

        # Task template
        label_task_template = QtWidgets.QLabel("Task template:")
        combo_task_template = QtWidgets.QComboBox()

        # Info widget
        info_widget = QtWidgets.QWidget()
        info_widget.setContentsMargins(10, 10, 10, 10)
        info_layout = QtWidgets.QVBoxLayout(info_widget)

        # Inputs widget
        inputs_widget = QtWidgets.QWidget()
        inputs_widget.setContentsMargins(0, 0, 0, 0)

        inputs_layout = QtWidgets.QFormLayout(inputs_widget)
        inputs_layout.addRow(label_outlink, input_outlink)
        inputs_layout.addRow(None, checkbox_outlink)
        inputs_layout.addRow(label_parent, input_parent)
        inputs_layout.addRow(label_name, input_name)
        inputs_layout.addRow(label_assetbuild, combo_assetbuilt)
        inputs_layout.addRow(label_task_template, combo_task_template)

        # Add button
        btns_widget = QtWidgets.QWidget()
        btns_widget.setContentsMargins(0, 0, 0, 0)
        btn_layout = QtWidgets.QHBoxLayout(btns_widget)
        btn_create_asset = QtWidgets.QPushButton("Create asset")
        btn_create_asset.setToolTip(
            "Creates all neccessary components for asset"
        )
        checkbox_app = None
        if self.context is not None:
            checkbox_app = QtWidgets.QCheckBox("Open {}".format(
                self.context.capitalize())
            )
            btn_layout.addWidget(checkbox_app)
        btn_layout.addWidget(btn_create_asset)

        task_view = QtWidgets.QTreeView()
        task_view.setIndentation(0)
        task_model = model.TasksModel()
        task_view.setModel(task_model)

        info_layout.addWidget(inputs_widget)
        info_layout.addWidget(task_view)
        info_layout.addWidget(btns_widget)

        # Body
        body = QtWidgets.QSplitter()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                           QtWidgets.QSizePolicy.Expanding)
        body.setOrientation(QtCore.Qt.Horizontal)
        body.addWidget(assets_widget)
        body.addWidget(info_widget)
        body.setStretchFactor(0, 100)
        body.setStretchFactor(1, 150)

        # statusbar
        message = QtWidgets.QLabel()
        message.setFixedHeight(20)

        statusbar = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(statusbar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(message)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(body)
        layout.addWidget(statusbar)

        self.data = {
            "label": {
                "message": message,
            },
            "view": {
                "tasks": task_view
            },
            "model": {
                "assets": assets,
                "tasks": task_model
            },
            "inputs": {
                "outlink": input_outlink,
                "outlink_cb": checkbox_outlink,
                "parent": input_parent,
                "name": input_name,
                "assetbuild": combo_assetbuilt,
                "tasktemplate": combo_task_template,
                "open_app": checkbox_app
            },
            "buttons": {
                "create_asset": btn_create_asset
            }
        }

        # signals
        btn_create_asset.clicked.connect(self.create_asset)
        assets.selection_changed.connect(self.on_asset_changed)
        input_name.textChanged.connect(self.on_asset_name_change)
        checkbox_outlink.toggled.connect(self.on_outlink_checkbox_change)
        combo_task_template.currentTextChanged.connect(
            self.on_task_template_changed
        )
        if self.context is not None:
            checkbox_app.toggled.connect(self.on_app_checkbox_change)
        # on start
        self.on_start()

        self.resize(600, 500)

        self.echo("Connected to project: {0}".format(project_name))

    def open_app(self):
        if self.context == 'maya':
            Popen("maya")
        else:
            message = QtWidgets.QMessageBox(self)
            message.setWindowTitle("App is not set")
            message.setIcon(QtWidgets.QMessageBox.Critical)
            message.show()

    def on_start(self):
        project_name = io.Session['AVALON_PROJECT']
        project_query = 'Project where full_name is "{}"'.format(project_name)
        if self.session is None:
            session = ftrack_api.Session()
            self.session = session
        else:
            session = self.session
        ft_project = session.query(project_query).one()
        schema_name = ft_project['project_schema']['name']
        # Load config
        schemas_items = config.get_presets().get('ftrack', {}).get(
            'project_schemas', {}
        )
        # Get info if it is silo project
        self.silos = io.distinct("silo")
        if self.silos and None in self.silos:
            self.silos = None

        key = "default"
        if schema_name in schemas_items:
            key = schema_name

        self.config_data = schemas_items[key]

        # set outlink
        input_outlink = self.data['inputs']['outlink']
        checkbox_outlink = self.data['inputs']['outlink_cb']
        outlink_text = io.Session.get('AVALON_ASSET', '')
        checkbox_outlink.setChecked(True)
        if outlink_text == '':
            outlink_text = '< No context >'
            checkbox_outlink.setChecked(False)
            checkbox_outlink.hide()
        input_outlink.setText(outlink_text)

        # load asset build types
        self.load_assetbuild_types()

        # Load task templates
        self.load_task_templates()
        self.data["model"]["assets"].refresh()
        self.on_asset_changed()

    def create_asset(self):
        name_input = self.data['inputs']['name']
        name = name_input.text()
        test_name = name.replace(' ', '')
        error_message = None
        message = QtWidgets.QMessageBox(self)
        message.setWindowTitle("Some errors has occured")
        message.setIcon(QtWidgets.QMessageBox.Critical)
        # TODO: show error messages on any error
        if self.valid_parent is not True and test_name == '':
            error_message = "Name is not set and Parent is not selected"
        elif self.valid_parent is not True:
            error_message = "Parent is not selected"
        elif test_name == '':
            error_message = "Name is not set"

        if error_message is not None:
            message.setText(error_message)
            message.show()
            return

        test_name_exists = io.find({
            'type': 'asset',
            'name': name
        })
        existing_assets = [x for x in test_name_exists]
        if len(existing_assets) > 0:
            message.setText("Entered Asset name is occupied")
            message.show()
            return

        checkbox_app = self.data['inputs']['open_app']
        if checkbox_app is not None and checkbox_app.isChecked() is True:
            task_view = self.data["view"]["tasks"]
            task_model = self.data["model"]["tasks"]
            try:
                index = task_view.selectedIndexes()[0]
                task_name = task_model.itemData(index)[0]
            except Exception:
                message.setText("Please select task")
                message.show()
                return

        # Get ftrack session
        if self.session is None:
            session = ftrack_api.Session()
            self.session = session
        else:
            session = self.session

        # Get Ftrack project entity
        project_name = io.Session['AVALON_PROJECT']
        project_query = 'Project where full_name is "{}"'.format(project_name)
        try:
            ft_project = session.query(project_query).one()
        except Exception:
            message.setText("Ftrack project was not found")
            message.show()
            return

        # Get Ftrack entity of parent
        ft_parent = None
        assets_model = self.data["model"]["assets"]
        selected = assets_model.get_selected_assets()
        parent = io.find_one({"_id": selected[0], "type": "asset"})
        asset_id = parent.get('data', {}).get('ftrackId', None)
        asset_entity_type = parent.get('data', {}).get('entityType', None)
        asset_query = '{} where id is "{}"'
        if asset_id is not None and asset_entity_type is not None:
            try:
                ft_parent = session.query(asset_query.format(
                    asset_entity_type, asset_id)
                ).one()
            except Exception:
                ft_parent = None

        if ft_parent is None:
            ft_parent = self.get_ftrack_asset(parent, ft_project)

        if ft_parent is None:
            message.setText("Parent's Ftrack entity was not found")
            message.show()
            return

        asset_build_combo = self.data['inputs']['assetbuild']
        asset_type_name = asset_build_combo.currentText()
        asset_type_query = 'Type where name is "{}"'.format(asset_type_name)
        try:
            asset_type = session.query(asset_type_query).one()
        except Exception:
            message.setText("Selected Asset Build type does not exists")
            message.show()
            return

        for children in ft_parent['children']:
            if children['name'] == name:
                message.setText("Entered Asset name is occupied")
                message.show()
                return

        task_template_combo = self.data['inputs']['tasktemplate']
        task_template = task_template_combo.currentText()
        tasks = []
        for template in self.config_data['task_templates']:
            if template['name'] == task_template:
                tasks = template['task_types']
                break

        available_task_types = []
        task_types = ft_project['project_schema']['_task_type_schema']
        for task_type in task_types['types']:
            available_task_types.append(task_type['name'])

        not_possible_tasks = []
        for task in tasks:
            if task not in available_task_types:
                not_possible_tasks.append(task)

        if len(not_possible_tasks) != 0:
            message.setText((
                "These Task types weren't found"
                " in Ftrack project schema:\n{}").format(
                ', '.join(not_possible_tasks))
            )
            message.show()
            return

        # Create asset build
        asset_build_data = {
            'name': name,
            'project_id': ft_project['id'],
            'parent_id': ft_parent['id'],
            'type': asset_type
        }

        new_entity = session.create('AssetBuild', asset_build_data)

        task_data = {
            'project_id': ft_project['id'],
            'parent_id': new_entity['id']
        }

        for task in tasks:
            type = session.query('Type where name is "{}"'.format(task)).one()

            task_data['type_id'] = type['id']
            task_data['name'] = task
            session.create('Task', task_data)

        av_project = io.find_one({'type': 'project'})

        hiearchy_items = []
        hiearchy_items.extend(self.get_avalon_parent(parent))
        hiearchy_items.append(parent['name'])

        hierarchy = os.path.sep.join(hiearchy_items)
        new_asset_data = {
            'ftrackId': new_entity['id'],
            'entityType': new_entity.entity_type,
            'visualParent': parent['_id'],
            'tasks': tasks,
            'parents': hiearchy_items,
            'hierarchy': hierarchy
        }
        new_asset_info = {
            'parent': av_project['_id'],
            'name': name,
            'schema': "avalon-core:asset-3.0",
            'type': 'asset',
            'data': new_asset_data
        }

        # Backwards compatibility (add silo from parent if is silo project)
        if self.silos:
            new_asset_info["silo"] = parent["silo"]

        try:
            schema.validate(new_asset_info)
        except Exception:
            message.setText((
                'Asset information are not valid'
                ' to create asset in avalon database'
            ))
            message.show()
            session.rollback()
            return
        io.insert_one(new_asset_info)
        session.commit()

        outlink_cb = self.data['inputs']['outlink_cb']
        if outlink_cb.isChecked() is True:
            outlink_input = self.data['inputs']['outlink']
            outlink_name = outlink_input.text()
            outlink_asset = io.find_one({
                'type': 'asset',
                'name': outlink_name
            })
            outlink_ft_id = outlink_asset.get('data', {}).get('ftrackId', None)
            outlink_entity_type = outlink_asset.get(
                'data', {}
            ).get('entityType', None)
            if outlink_ft_id is not None and outlink_entity_type is not None:
                try:
                    outlink_entity = session.query(asset_query.format()).one()
                except Exception:
                    outlink_entity = None

            if outlink_entity is None:
                outlink_entity = self.get_ftrack_asset(
                    outlink_asset, ft_project
                )

            if outlink_entity is None:
                message.setText("Outlink's Ftrack entity was not found")
                message.show()
                return

            link_data = {
                'from_id': new_entity['id'],
                'to_id': outlink_entity['id']
            }
            session.create('TypedContextLink', link_data)
            session.commit()

        if checkbox_app is not None and checkbox_app.isChecked() is True:
            origin_asset = api.Session.get('AVALON_ASSET', None)
            origin_task = api.Session.get('AVALON_TASK', None)
            asset_name = name
            task_view = self.data["view"]["tasks"]
            task_model = self.data["model"]["tasks"]
            try:
                index = task_view.selectedIndexes()[0]
            except Exception:
                message.setText("No task is selected. App won't be launched")
                message.show()
                return
            task_name = task_model.itemData(index)[0]
            try:
                api.update_current_task(task=task_name, asset=asset_name)
                self.open_app()

            finally:
                if origin_task is not None and origin_asset is not None:
                    api.update_current_task(
                        task=origin_task, asset=origin_asset
                    )

        message.setWindowTitle("Asset Created")
        message.setText("Asset Created successfully")
        message.setIcon(QtWidgets.QMessageBox.Information)
        message.show()

    def get_ftrack_asset(self, asset, ft_project):
        parenthood = []
        parenthood.extend(self.get_avalon_parent(asset))
        parenthood.append(asset['name'])
        parenthood = list(reversed(parenthood))
        output_entity = None
        ft_entity = ft_project
        index = len(parenthood) - 1
        while True:
            name = parenthood[index]
            found = False
            for children in ft_entity['children']:
                if children['name'] == name:
                    ft_entity = children
                    found = True
                    break
            if found is False:
                return None
            if index == 0:
                output_entity = ft_entity
                break
            index -= 1

        return output_entity

    def get_avalon_parent(self, entity):
        parent_id = entity['data']['visualParent']
        parents = []
        if parent_id is not None:
            parent = io.find_one({'_id': parent_id})
            parents.extend(self.get_avalon_parent(parent))
            parents.append(parent['name'])
        return parents

    def echo(self, message):
        widget = self.data["label"]["message"]
        widget.setText(str(message))

        QtCore.QTimer.singleShot(5000, lambda: widget.setText(""))

        print(message)

    def load_task_templates(self):
        templates = self.config_data.get('task_templates', [])
        all_names = []
        for template in templates:
            all_names.append(template['name'])

        tt_combobox = self.data['inputs']['tasktemplate']
        tt_combobox.clear()
        tt_combobox.addItems(all_names)

    def load_assetbuild_types(self):
        types = []
        schemas = self.config_data.get('schemas', [])
        for _schema in schemas:
            if _schema['object_type'] == 'Asset Build':
                types = _schema['task_types']
                break
        ab_combobox = self.data['inputs']['assetbuild']
        ab_combobox.clear()
        ab_combobox.addItems(types)

    def on_app_checkbox_change(self):
        task_model = self.data['model']['tasks']
        app_checkbox = self.data['inputs']['open_app']
        if app_checkbox.isChecked() is True:
            task_model.selectable = True
        else:
            task_model.selectable = False

    def on_outlink_checkbox_change(self):
        checkbox_outlink = self.data['inputs']['outlink_cb']
        outlink_input = self.data['inputs']['outlink']
        if checkbox_outlink.isChecked() is True:
            outlink_text = io.Session['AVALON_ASSET']
        else:
            outlink_text = '< Outlinks won\'t be set >'

        outlink_input.setText(outlink_text)

    def on_task_template_changed(self):
        combobox = self.data['inputs']['tasktemplate']
        task_model = self.data['model']['tasks']
        name = combobox.currentText()
        tasks = []
        for template in self.config_data['task_templates']:
            if template['name'] == name:
                tasks = template['task_types']
                break
        task_model.set_tasks(tasks)

    def on_asset_changed(self):
        """Callback on asset selection changed

        This updates the task view.

        """
        assets_model = self.data["model"]["assets"]
        parent_input = self.data['inputs']['parent']
        selected = assets_model.get_selected_assets()

        self.valid_parent = False
        if len(selected) > 1:
            parent_input.setText('< Please select only one asset! >')
        elif len(selected) == 1:
            if isinstance(selected[0], io.ObjectId):
                self.valid_parent = True
                asset = io.find_one({"_id": selected[0], "type": "asset"})
                parent_input.setText(asset['name'])
            else:
                parent_input.setText('< Selected invalid parent(silo) >')
        else:
            parent_input.setText('< Nothing is selected >')

        self.creatability_check()

    def on_asset_name_change(self):
        self.creatability_check()

    def creatability_check(self):
        name_input = self.data['inputs']['name']
        name = str(name_input.text()).strip()
        creatable = False
        if name and self.valid_parent:
            creatable = True

        self.data["buttons"]["create_asset"].setEnabled(creatable)



def show(parent=None, debug=False, context=None):
    """Display Loader GUI

    Arguments:
        debug (bool, optional): Run loader in debug-mode,
            defaults to False

    """

    try:
        module.window.close()
        del module.window
    except (RuntimeError, AttributeError):
        pass

    if debug is True:
        io.install()

    with parentlib.application():
        window = Window(parent, context)
        window.setStyleSheet(style.load_stylesheet())
        window.show()

        module.window = window


def cli(args):
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("project")
    parser.add_argument("asset")

    args = parser.parse_args(args)
    project = args.project
    asset = args.asset
    io.install()

    api.Session["AVALON_PROJECT"] = project
    if asset != '':
        api.Session["AVALON_ASSET"] = asset

    show()
