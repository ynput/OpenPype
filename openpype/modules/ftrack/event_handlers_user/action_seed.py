import os
from operator import itemgetter
from openpype_modules.ftrack.lib import BaseAction, statics_icon


class SeedDebugProject(BaseAction):
    '''Edit meta data action.'''

    #: Action identifier.
    identifier = "seed.debug.project"
    #: Action label.
    label = "Seed Debug Project"
    #: Action description.
    description = "Description"
    #: priority
    priority = 100
    #: roles that are allowed to register this action
    icon = statics_icon("ftrack", "action_icons", "SeedProject.svg")

    # Asset names which will be created in `Assets` entity
    assets = [
        "Addax", "Alpaca", "Ant", "Antelope", "Aye", "Badger", "Bear", "Bee",
        "Beetle", "Bluebird", "Bongo", "Bontebok", "Butterflie", "Caiman",
        "Capuchin", "Capybara", "Cat", "Caterpillar", "Coyote", "Crocodile",
        "Cuckoo", "Deer", "Dragonfly", "Duck", "Eagle", "Egret", "Elephant",
        "Falcon", "Fossa", "Fox", "Gazelle", "Gecko", "Gerbil",
        "GiantArmadillo", "Gibbon", "Giraffe", "Goose", "Gorilla",
        "Grasshoper", "Hare", "Hawk", "Hedgehog", "Heron", "Hog",
        "Hummingbird", "Hyena", "Chameleon", "Cheetah", "Iguana", "Jackal",
        "Jaguar", "Kingfisher", "Kinglet", "Kite", "Komodo", "Lemur",
        "Leopard", "Lion", "Lizard", "Macaw", "Malachite", "Mandrill",
        "Mantis", "Marmoset", "Meadowlark", "Meerkat", "Mockingbird",
        "Mongoose", "Monkey", "Nyal", "Ocelot", "Okapi", "Oribi", "Oriole",
        "Otter", "Owl", "Panda", "Parrot", "Pelican", "Pig", "Porcupine",
        "Reedbuck", "Rhinocero", "Sandpiper", "Servil", "Skink", "Sloth",
        "Snake", "Spider", "Squirrel", "Sunbird", "Swallow", "Swift", "Tiger",
        "Sylph", "Tanager", "Vulture", "Warthog", "Waterbuck", "Woodpecker",
        "Zebra"
    ]

    # Tasks which will be created for Assets
    asset_tasks = [
        "Modeling", "Lookdev", "Rigging"
    ]
    # Tasks which will be created for Shots
    shot_tasks = [
        "Animation", "Lighting", "Compositing", "FX"
    ]

    # Define how much sequences will be created
    default_seq_count = 5
    # Define how much shots will be created for each sequence
    default_shots_count = 10

    max_entities_created_at_one_commit = 50

    existing_projects = None
    new_project_item = "< New Project >"
    current_project_item = "< Current Project >"
    settings_key = "seed_project"

    def discover(self, session, entities, event):
        ''' Validation '''
        if not self.valid_roles(session, entities, event):
            return False
        return True

    def interface(self, session, entities, event):
        if event["data"].get("values", {}):
            return

        title = "Select Project where you want to create seed data"

        items = []
        item_splitter = {"type": "label", "value": "---"}

        description_label = {
            "type": "label",
            "value": (
                "WARNING: Action does NOT check if entities already exist !!!"
            )
        }
        items.append(description_label)

        all_projects = session.query("select full_name from Project").all()
        self.existing_projects = [proj["full_name"] for proj in all_projects]
        projects_items = [
            {"label": proj, "value": proj} for proj in self.existing_projects
        ]

        data_items = []

        data_items.append({
            "label": self.new_project_item,
            "value": self.new_project_item
        })

        data_items.append({
            "label": self.current_project_item,
            "value": self.current_project_item
        })

        data_items.extend(sorted(
            projects_items,
            key=itemgetter("label"),
            reverse=False
        ))
        projects_item = {
            "label": "Choose Project",
            "type": "enumerator",
            "name": "project_name",
            "data": data_items,
            "value": self.current_project_item
        }
        items.append(projects_item)
        items.append(item_splitter)

        items.append({
            "label": "Number of assets",
            "type": "number",
            "name": "asset_count",
            "value": len(self.assets)
        })
        items.append({
            "label": "Number of sequences",
            "type": "number",
            "name": "seq_count",
            "value": self.default_seq_count
        })
        items.append({
            "label": "Number of shots",
            "type": "number",
            "name": "shots_count",
            "value": self.default_shots_count
        })
        items.append(item_splitter)

        note_label = {
            "type": "label",
            "value": (
                "<p><i>NOTE: Enter project name and choose schema if you "
                "chose `\"< New Project >\"`(code is optional)</i><p>"
            )
        }
        items.append(note_label)
        items.append({
            "label": "Project name",
            "name": "new_project_name",
            "type": "text",
            "value": ""
        })

        project_schemas = [
            sch["name"] for sch in self.session.query("ProjectSchema").all()
        ]
        schemas_item = {
            "label": "Choose Schema",
            "type": "enumerator",
            "name": "new_schema_name",
            "data": [
                {"label": sch, "value": sch} for sch in project_schemas
            ],
            "value": project_schemas[0]
        }
        items.append(schemas_item)

        items.append({
            "label": "*Project code",
            "name": "new_project_code",
            "type": "text",
            "value": "",
            "empty_text": "Optional..."
        })

        return {
            "items": items,
            "title": title
        }

    def launch(self, session, in_entities, event):
        if "values" not in event["data"]:
            return

        # THIS IS THE PROJECT PART
        values = event["data"]["values"]
        selected_project = values["project_name"]
        if selected_project == self.new_project_item:
            project_name = values["new_project_name"]
            if project_name in self.existing_projects:
                msg = "Project \"{}\" already exist".format(project_name)
                self.log.error(msg)
                return {"success": False, "message": msg}

            project_code = values["new_project_code"]
            project_schema_name = values["new_schema_name"]
            if not project_code:
                project_code = project_name
            project_code = project_code.lower().replace(" ", "_").strip()
            _project = session.query(
                "Project where name is \"{}\"".format(project_code)
            ).first()
            if _project:
                msg = "Project with code \"{}\" already exist".format(
                    project_code
                )
                self.log.error(msg)
                return {"success": False, "message": msg}

            project_schema = session.query(
                "ProjectSchema where name is \"{}\"".format(
                    project_schema_name
                )
            ).one()
            # Create the project with the chosen schema.
            self.log.debug((
                "*** Creating Project: name <{}>, code <{}>, schema <{}>"
            ).format(project_name, project_code, project_schema_name))
            project = session.create("Project", {
                "name": project_code,
                "full_name": project_name,
                "project_schema": project_schema
            })
            session.commit()

        elif selected_project == self.current_project_item:
            entity = in_entities[0]
            if entity.entity_type.lower() == "project":
                project = entity
            else:
                if "project" in entity:
                    project = entity["project"]
                else:
                    project = entity["parent"]["project"]
            project_schema = project["project_schema"]
            self.log.debug((
                "*** Using Project: name <{}>, code <{}>, schema <{}>"
            ).format(
                project["full_name"], project["name"], project_schema["name"]
            ))
        else:
            project = session.query("Project where full_name is \"{}\"".format(
                selected_project
            )).one()
            project_schema = project["project_schema"]
            self.log.debug((
                "*** Using Project: name <{}>, code <{}>, schema <{}>"
            ).format(
                project["full_name"], project["name"], project_schema["name"]
            ))

        # THIS IS THE MAGIC PART
        task_types = {}
        for _type in project_schema["_task_type_schema"]["types"]:
            if _type["name"] not in task_types:
                task_types[_type["name"]] = _type
        self.task_types = task_types

        asset_count = values.get("asset_count") or len(self.assets)
        seq_count = values.get("seq_count") or self.default_seq_count
        shots_count = values.get("shots_count") or self.default_shots_count

        self.create_assets(project, asset_count)
        self.create_shots(project, seq_count, shots_count)

        return True

    def create_assets(self, project, asset_count):
        self.log.debug("*** Creating assets:")

        try:
            asset_count = int(asset_count)
        except ValueError:
            asset_count = 0

        if asset_count <= 0:
            self.log.debug("No assets to create")
            return

        main_entity = self.session.create("Folder", {
            "name": "Assets",
            "parent": project
        })
        self.log.debug("- Assets")
        available_assets = len(self.assets)
        repetitive_times = (
            int(asset_count / available_assets) +
            (asset_count % available_assets > 0)
        )

        index = 0
        created_entities = 0
        to_create_length = asset_count + (asset_count * len(self.asset_tasks))
        for _asset_name in self.assets:
            if created_entities >= to_create_length:
                break
            for asset_num in range(1, repetitive_times + 1):
                if created_entities >= asset_count:
                    break
                asset_name = "%s_%02d" % (_asset_name, asset_num)
                asset = self.session.create("AssetBuild", {
                    "name": asset_name,
                    "parent": main_entity
                })
                self.log.debug("- Assets/{}".format(asset_name))

                created_entities += 1
                index += 1
                if self.temp_commit(index, created_entities, to_create_length):
                    index = 0

                for task_name in self.asset_tasks:
                    self.session.create("Task", {
                        "name": task_name,
                        "parent": asset,
                        "type": self.task_types[task_name]
                    })
                    self.log.debug("- Assets/{}/{}".format(
                        asset_name, task_name
                    ))

                    created_entities += 1
                    index += 1
                    if self.temp_commit(
                        index, created_entities, to_create_length
                    ):
                        index = 0

        self.log.debug("*** Commiting Assets")
        self.log.debug("Commiting entities. {}/{}".format(
            created_entities, to_create_length
        ))
        self.session.commit()

    def create_shots(self, project, seq_count, shots_count):
        self.log.debug("*** Creating shots:")

        # Convert counts to integers
        try:
            seq_count = int(seq_count)
        except ValueError:
            seq_count = 0

        try:
            shots_count = int(shots_count)
        except ValueError:
            shots_count = 0

        # Check if both are higher than 0
        missing = []
        if seq_count <= 0:
            missing.append("sequences")

        if shots_count <= 0:
            missing.append("shots")

        if missing:
            self.log.debug("No {} to create".format(" and ".join(missing)))
            return

        # Create Folder "Shots"
        main_entity = self.session.create("Folder", {
            "name": "Shots",
            "parent": project
        })
        self.log.debug("- Shots")

        index = 0
        created_entities = 0
        to_create_length = (
            seq_count
            + (seq_count * shots_count)
            + (seq_count * shots_count * len(self.shot_tasks))
        )
        for seq_num in range(1, seq_count + 1):
            seq_name = "sq%03d" % seq_num
            seq = self.session.create("Sequence", {
                "name": seq_name,
                "parent": main_entity
            })
            self.log.debug("- Shots/{}".format(seq_name))

            created_entities += 1
            index += 1
            if self.temp_commit(index, created_entities, to_create_length):
                index = 0

            for shot_num in range(1, shots_count + 1):
                shot_name = "%ssh%04d" % (seq_name, (shot_num * 10))
                shot = self.session.create("Shot", {
                    "name": shot_name,
                    "parent": seq
                })
                self.log.debug("- Shots/{}/{}".format(seq_name, shot_name))

                created_entities += 1
                index += 1
                if self.temp_commit(index, created_entities, to_create_length):
                    index = 0

                for task_name in self.shot_tasks:
                    self.session.create("Task", {
                        "name": task_name,
                        "parent": shot,
                        "type": self.task_types[task_name]
                    })
                    self.log.debug("- Shots/{}/{}/{}".format(
                        seq_name, shot_name, task_name
                    ))

                    created_entities += 1
                    index += 1
                    if self.temp_commit(
                        index, created_entities, to_create_length
                    ):
                        index = 0

        self.log.debug("*** Commiting Shots")
        self.log.debug("Commiting entities. {}/{}".format(
            created_entities, to_create_length
        ))
        self.session.commit()

    def temp_commit(self, index, created_entities, to_create_length):
        if index < self.max_entities_created_at_one_commit:
            return False
        self.log.debug("Commiting {} entities. {}/{}".format(
            index, created_entities, to_create_length
        ))
        self.session.commit()
        return True


def register(session):
    '''Register plugin. Called when used as an plugin.'''

    SeedDebugProject(session).register()
