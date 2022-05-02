import os
import getpass
import platform

from Qt import QtCore, QtGui, QtWidgets

from openpype import style
import ftrack_api


class Project_name_getUI(QtWidgets.QWidget):
    '''
    Project setting ui: here all the neceserry ui widgets are created
    they are going to be used i later proces for dynamic linking of project
    in list to project's attributes
    '''

    def __init__(self, parent=None):
        super(Project_name_getUI, self).__init__(parent)

        self.platform = platform.system()
        self.new_index = 0
        # get projects from ftrack
        self.session = ftrack_api.Session()
        self.projects_from_ft = self.session.query(
            'Project where status is active')
        self.disks_from_ft = self.session.query('Disk')
        self.schemas_from_ft = self.session.query('ProjectSchema')
        self.projects = self._get_projects_ftrack()

        # define window geometry
        self.setWindowTitle('Set project attributes')
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.resize(550, 340)
        self.setStyleSheet(style.load_stylesheet())

        # define disk combobox  widget
        self.disks = self._get_all_disks()
        self.disk_combobox_label = QtWidgets.QLabel('Destination storage:')
        self.disk_combobox = QtWidgets.QComboBox()

        # define schema combobox  widget
        self.schemas = self._get_all_schemas()
        self.schema_combobox_label = QtWidgets.QLabel('Project schema:')
        self.schema_combobox = QtWidgets.QComboBox()

        # define fps widget
        self.fps_label = QtWidgets.QLabel('Fps:')
        self.fps_label.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.fps = QtWidgets.QLineEdit()

        # define project dir widget
        self.project_dir_label = QtWidgets.QLabel('Project dir:')
        self.project_dir_label.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.project_dir = QtWidgets.QLineEdit()

        self.project_path_label = QtWidgets.QLabel(
            'Project_path (if not then created):')
        self.project_path_label.setAlignment(
            QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
        project_path_font = QtGui.QFont(
            "Helvetica [Cronyx]", 12, QtGui.QFont.Bold)
        self.project_path = QtWidgets.QLabel()
        self.project_path.setObjectName('nom_plan_label')
        self.project_path.setStyleSheet(
            'QtWidgets.QLabel#nom_plan_label {color: red}')
        self.project_path.setAlignment(
            QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
        self.project_path.setFont(project_path_font)

        # define handles widget
        self.handles_label = QtWidgets.QLabel('Handles:')
        self.handles_label.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.handles = QtWidgets.QLineEdit()

        # define resolution widget
        self.resolution_w_label = QtWidgets.QLabel('W:')
        self.resolution_w = QtWidgets.QLineEdit()
        self.resolution_h_label = QtWidgets.QLabel('H:')
        self.resolution_h = QtWidgets.QLineEdit()

        devider = QtWidgets.QFrame()
        # devider.Shape(QFrame.HLine)
        devider.setFrameShape(QtWidgets.QFrame.HLine)
        devider.setFrameShadow(QtWidgets.QFrame.Sunken)

        self.generate_lines()

        # define push buttons
        self.set_pushbutton = QtWidgets.QPushButton('Set project')
        self.cancel_pushbutton = QtWidgets.QPushButton('Cancel')

        # definition of layouts
        ############################################
        action_layout = QtWidgets.QHBoxLayout()
        action_layout.addWidget(self.set_pushbutton)
        action_layout.addWidget(self.cancel_pushbutton)

        # schema property
        schema_layout = QtWidgets.QGridLayout()
        schema_layout.addWidget(self.schema_combobox, 0, 1)
        schema_layout.addWidget(self.schema_combobox_label, 0, 0)

        # storage property
        storage_layout = QtWidgets.QGridLayout()
        storage_layout.addWidget(self.disk_combobox, 0, 1)
        storage_layout.addWidget(self.disk_combobox_label, 0, 0)

        # fps property
        fps_layout = QtWidgets.QGridLayout()
        fps_layout.addWidget(self.fps, 1, 1)
        fps_layout.addWidget(self.fps_label, 1, 0)

        # project dir property
        project_dir_layout = QtWidgets.QGridLayout()
        project_dir_layout.addWidget(self.project_dir, 1, 1)
        project_dir_layout.addWidget(self.project_dir_label, 1, 0)

        # project path property
        project_path_layout = QtWidgets.QGridLayout()
        spacer_1_item = QtWidgets.QSpacerItem(10, 10)
        project_path_layout.addItem(spacer_1_item, 0, 1)
        project_path_layout.addWidget(self.project_path_label, 1, 1)
        project_path_layout.addWidget(self.project_path, 2, 1)
        spacer_2_item = QtWidgets.QSpacerItem(20, 20)
        project_path_layout.addItem(spacer_2_item, 3, 1)

        # handles property
        handles_layout = QtWidgets.QGridLayout()
        handles_layout.addWidget(self.handles, 1, 1)
        handles_layout.addWidget(self.handles_label, 1, 0)

        # resolution property
        resolution_layout = QtWidgets.QGridLayout()
        resolution_layout.addWidget(self.resolution_w_label, 1, 1)
        resolution_layout.addWidget(self.resolution_w, 2, 1)
        resolution_layout.addWidget(self.resolution_h_label, 1, 2)
        resolution_layout.addWidget(self.resolution_h, 2, 2)

        # form project property layout
        p_layout = QtWidgets.QGridLayout()
        p_layout.addLayout(storage_layout, 1, 0)
        p_layout.addLayout(schema_layout, 2, 0)
        p_layout.addLayout(project_dir_layout, 3, 0)
        p_layout.addLayout(fps_layout, 4, 0)
        p_layout.addLayout(handles_layout, 5, 0)
        p_layout.addLayout(resolution_layout, 6, 0)
        p_layout.addWidget(devider, 7, 0)
        spacer_item = QtWidgets.QSpacerItem(
            150,
            40,
            QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Expanding
        )
        p_layout.addItem(spacer_item, 8, 0)

        # form with list to one layout with project property
        list_layout = QtWidgets.QGridLayout()
        list_layout.addLayout(p_layout, 1, 0)
        list_layout.addWidget(self.listWidget, 1, 1)

        root_layout = QtWidgets.QVBoxLayout()
        root_layout.addLayout(project_path_layout)
        root_layout.addWidget(devider)
        root_layout.addLayout(list_layout)
        root_layout.addLayout(action_layout)

        self.setLayout(root_layout)

    def generate_lines(self):
        '''
        Will generate lines of project list
        '''

        self.listWidget = QtWidgets.QListWidget()
        for self.index, p in enumerate(self.projects):
            item = QtWidgets.QListWidgetItem("{full_name}".format(**p))
            # item.setSelected(False)
            self.listWidget.addItem(item)
        print(self.listWidget.indexFromItem(item))
        # self.listWidget.setCurrentItem(self.listWidget.itemFromIndex(1))

        # add options to schemas widget
        self.schema_combobox.addItems(self.schemas)

        # add options to disk widget
        self.disk_combobox.addItems(self.disks)

        # populate content of project info widgets
        self.projects[1] = self._fill_project_attributes_widgets(p, None)

    def _fill_project_attributes_widgets(self, p=None, index=None):
        '''
        will generate actual informations wich are saved on ftrack
        '''

        if index is None:
            self.new_index = 1

        if not p:
            pass
        # change schema selection
        for i, schema in enumerate(self.schemas):
            if p['project_schema']['name'] in schema:
                break
        self.schema_combobox.setCurrentIndex(i)

        disk_name, disk_path = self._build_disk_path()
        for i, disk in enumerate(self.disks):
            if disk_name in disk:
                break
        # change disk selection
        self.disk_combobox.setCurrentIndex(i)

        # change project_dir selection
        if "{root}".format(**p):
            self.project_dir.setPlaceholderText("{root}".format(**p))
        else:
            print("not root so it was replaced with name")
            self.project_dir.setPlaceholderText("{name}".format(**p))
            p['root'] = p['name']

        # set project path to show where it will be created
        self.project_path.setText(
            os.path.join(self.disks[i].split(' ')[-1],
                         self.project_dir.text()))

        # change fps selection
        self.fps.setPlaceholderText("{custom_attributes[fps]}".format(**p))

        # change handles selection
        self.handles.setPlaceholderText(
            "{custom_attributes[handles]}".format(**p))

        # change resolution selection
        self.resolution_w.setPlaceholderText(
            "{custom_attributes[resolution_width]}".format(**p))
        self.resolution_h.setPlaceholderText(
            "{custom_attributes[resolution_height]}".format(**p))

        self.update_disk()

        return p

    def fix_project_path_literals(self, dir):
        return dir.replace(' ', '_').lower()

    def update_disk(self):
        disk = self.disk_combobox.currentText().split(' ')[-1]

        dir = self.project_dir.text()
        if not dir:
            dir = "{root}".format(**self.projects[self.new_index])
            self.projects[self.new_index]['project_path'] = os.path.normpath(
                self.fix_project_path_literals(os.path.join(disk, dir)))
        else:
            self.projects[self.new_index]['project_path'] = os.path.normpath(
                self.fix_project_path_literals(os.path.join(disk, dir)))

        self.projects[self.new_index]['disk'] = self.disks_from_ft[
            self.disk_combobox.currentIndex()]
        self.projects[self.new_index]['disk_id'] = self.projects[
            self.new_index]['disk']['id']

        # set project path to show where it will be created
        self.project_path.setText(
            self.projects[self.new_index]['project_path'])

    def update_resolution(self):
        # update all values in resolution
        if self.resolution_w.text():
            self.projects[self.new_index]['custom_attributes'][
                "resolutionWidth"] = int(self.resolution_w.text())
        if self.resolution_h.text():
            self.projects[self.new_index]['custom_attributes'][
                "resolutionHeight"] = int(self.resolution_h.text())

    def _update_attributes_by_list_selection(self):
        # generate actual selection index
        self.new_index = self.listWidget.currentRow()
        self.project_dir.setText('')
        self.fps.setText('')
        self.handles.setText('')
        self.resolution_w.setText('')
        self.resolution_h.setText('')

        # update project properities widgets and write changes
        # into project dictionaries
        self.projects[self.new_index] = self._fill_project_attributes_widgets(
            self.projects[self.new_index], self.new_index)

        self.update_disk()

    def _build_disk_path(self):
        if self.platform == "Windows":
            print(self.projects[self.index].keys())
            print(self.projects[self.new_index]['disk'])
            return self.projects[self.new_index]['disk'][
                'name'], self.projects[self.new_index]['disk']['windows']
        else:
            return self.projects[self.new_index]['disk'][
                'name'], self.projects[self.new_index]['disk']['unix']

    def _get_all_schemas(self):
        schemas_list = []

        for s in self.schemas_from_ft:
            # print d.keys()
            # if 'Pokus' in s['name']:
            #     continue
            schemas_list.append('{}'.format(s['name']))
        print("\nschemas in ftrack: {}\n".format(schemas_list))
        return schemas_list

    def _get_all_disks(self):
        disks_list = []
        for d in self.disks_from_ft:
            # print d.keys()
            if self.platform == "Windows":
                if 'Local drive' in d['name']:
                    d['windows'] = os.path.join(d['windows'],
                                                os.getenv('USERNAME')
                                                or os.getenv('USER')
                                                or os.getenv('LOGNAME'))
                disks_list.append('"{}" at {}'.format(d['name'], d['windows']))
            else:
                if 'Local drive' in d['name']:
                    d['unix'] = os.path.join(d['unix'], getpass.getuser())
                disks_list.append('"{}" at {}'.format(d['name'], d['unix']))
        return disks_list

    def _get_projects_ftrack(self):

        projects_lst = []
        for project in self.projects_from_ft:
            # print project.keys()
            projects_dict = {}

            for k in project.keys():
                ''' # TODO: delete this in production version '''

                # if 'test' not in project['name']:
                #     continue

                # print '{}: {}\n'.format(k, project[k])

                if '_link' == k:
                    # print project[k]
                    content = project[k]
                    for kc in content[0].keys():
                        if content[0]['name']:
                            content[0][kc] = content[0][kc].encode(
                                'ascii', 'ignore').decode('ascii')
                            print('{}: {}\n'.format(kc, content[0][kc]))
                    projects_dict[k] = content
                    print(project[k])
                    print(projects_dict[k])
                elif 'root' == k:
                    print('{}: {}\n'.format(k, project[k]))
                    projects_dict[k] = project[k]
                elif 'disk' == k:
                    print('{}: {}\n'.format(k, project[k]))
                    projects_dict[k] = project[k]
                elif 'name' == k:
                    print('{}: {}\n'.format(k, project[k]))
                    projects_dict[k] = project[k].encode(
                        'ascii', 'ignore').decode('ascii')
                elif 'disk_id' == k:
                    print('{}: {}\n'.format(k, project[k]))
                    projects_dict[k] = project[k]
                elif 'id' == k:
                    print('{}: {}\n'.format(k, project[k]))
                    projects_dict[k] = project[k]
                elif 'full_name' == k:
                    print('{}: {}\n'.format(k, project[k]))
                    projects_dict[k] = project[k].encode(
                        'ascii', 'ignore').decode('ascii')
                elif 'project_schema_id' == k:
                    print('{}: {}\n'.format(k, project[k]))
                    projects_dict[k] = project[k]
                elif 'project_schema' == k:
                    print('{}: {}\n'.format(k, project[k]))
                    projects_dict[k] = project[k]
                elif 'custom_attributes' == k:
                    print('{}: {}\n'.format(k, project[k]))
                    projects_dict[k] = project[k]
                else:
                    pass

            if projects_dict:
                projects_lst.append(projects_dict)

        return projects_lst


class Project_name_get(Project_name_getUI):
    def __init__(self, parent=None):
        super(Project_name_get, self).__init__(parent)
        # self.input_project_name.textChanged.connect(self.input_project_name.placeholderText)

        self.set_pushbutton.clicked.connect(lambda: self.execute())
        self.cancel_pushbutton.clicked.connect(self.close)

        self.listWidget.itemSelectionChanged.connect(
            self._update_attributes_by_list_selection)
        self.disk_combobox.currentIndexChanged.connect(self.update_disk)
        self.schema_combobox.currentIndexChanged.connect(self.update_schema)
        self.project_dir.textChanged.connect(self.update_disk)
        self.fps.textChanged.connect(self.update_fps)
        self.handles.textChanged.connect(self.update_handles)
        self.resolution_w.textChanged.connect(self.update_resolution)
        self.resolution_h.textChanged.connect(self.update_resolution)

    def update_handles(self):
        self.projects[self.new_index]['custom_attributes']['handles'] = int(
            self.handles.text())

    def update_fps(self):
        self.projects[self.new_index]['custom_attributes']['fps'] = int(
            self.fps.text())

    def update_schema(self):
        self.projects[self.new_index]['project_schema'] = self.schemas_from_ft[
            self.schema_combobox.currentIndex()]
        self.projects[self.new_index]['project_schema_id'] = self.projects[
            self.new_index]['project_schema']['id']

    def execute(self):
        # import ft_utils
        # import hiero
        # get the project which has been selected
        print("well and what")
        # set the project as context and create entity
        # entity is task created with the name of user which is creating it

        # get the project_path and create dir if there is not any
        print(self.projects[self.new_index]['project_path'].replace(
            self.disk_combobox.currentText().split(' ')[-1].lower(), ''))

        # get the schema and recreate a starting project regarding the selection
        # set_hiero_template(project_schema=self.projects[self.new_index][
        #     'project_schema']['name'])

        # set all project properities
        # project = hiero.core.Project()
        # project.setFramerate(
        #     int(self.projects[self.new_index]['custom_attributes']['fps']))
        # project.projectRoot()
        # print 'handles: {}'.format(self.projects[self.new_index]['custom_attributes']['handles'])
        # print 'resolution_width: {}'.format(self.projects[self.new_index]['custom_attributes']["resolutionWidth"])
        # print 'resolution_width: {}'.format(self.projects[self.new_index]['custom_attributes']["resolutionHeight"])
        # print "<< {}".format(self.projects[self.new_index])

        # get path for the hrox file
        # root = context.data('ftrackData')['Project']['root']
        # hrox_script_path = ft_utils.getPathsYaml(taskid, templateList=templates, root=root)

        # save the hrox into the correct path
        self.session.commit()
        self.close()

#
# def set_hiero_template(project_schema=None):
#     import hiero
#     hiero.core.closeAllProjects()
#     hiero_plugin_path = [
#         p for p in os.environ['HIERO_PLUGIN_PATH'].split(';')
#         if 'hiero_plugin_path' in p
#     ][0]
#     path = os.path.normpath(
#         os.path.join(hiero_plugin_path, 'Templates', project_schema + '.hrox'))
#     print('---> path to template: {}'.format(path))
#     return hiero.core.openProject(path)


# def set_out_ft_session():
#     session = ftrack_api.Session()
#     projects_to_ft = session.query('Project where status is active')


def main():
    import sys
    app = QtWidgets.QApplication(sys.argv)
    panel = Project_name_get()
    panel.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
