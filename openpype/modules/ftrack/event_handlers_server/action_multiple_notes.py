from openpype_modules.ftrack.lib import ServerAction


class MultipleNotesServer(ServerAction):
    """Action adds same note for muliple AssetVersions.

    Note is added to selection of AssetVersions. Note is created with user
    who triggered the action. It is possible to define note category of note.
    """

    identifier = "multiple.notes.server"
    label = "Multiple Notes (Server)"
    description = "Add same note to multiple Asset Versions"

    _none_category = "__NONE__"

    def discover(self, session, entities, event):
        """Show action only on AssetVersions."""
        if not entities:
            return False

        for entity in entities:
            if entity.entity_type.lower() != "assetversion":
                return False
        return True

    def interface(self, session, entities, event):
        event_source = event["source"]
        user_info = event_source.get("user") or {}
        user_id = user_info.get("id")
        if not user_id:
            return None

        values = event["data"].get("values")
        if values:
            return None

        note_label = {
            "type": "label",
            "value": "# Enter note: #"
        }

        note_value = {
            "name": "note",
            "type": "textarea"
        }

        category_label = {
            "type": "label",
            "value": "## Category: ##"
        }

        category_data = []
        category_data.append({
            "label": "- None -",
            "value": self._none_category
        })
        all_categories = session.query(
            "select id, name from NoteCategory"
        ).all()
        for cat in all_categories:
            category_data.append({
                "label": cat["name"],
                "value": cat["id"]
            })
        category_value = {
            "type": "enumerator",
            "name": "category",
            "data": category_data,
            "value": self._none_category
        }

        splitter = {
            "type": "label",
            "value": "---"
        }

        return [
            note_label,
            note_value,
            splitter,
            category_label,
            category_value
        ]

    def launch(self, session, entities, event):
        if "values" not in event["data"]:
            return None

        values = event["data"]["values"]
        if len(values) <= 0 or "note" not in values:
            return False

        # Get Note text
        note_value = values["note"]
        if note_value.lower().strip() == "":
            return {
                "success": True,
                "message": "Note was not entered. Skipping"
            }

        # Get User
        event_source = event["source"]
        user_info = event_source.get("user") or {}
        user_id = user_info.get("id")
        user = None
        if user_id:
            user = session.query(
                'User where id is "{}"'.format(user_id)
            ).first()

        if not user:
            return {
                "success": False,
                "message": "Couldn't get user information."
            }

        # Logging message preparation
        # - username
        username = user.get("username") or "N/A"

        # - AssetVersion ids
        asset_version_ids_str = ",".join([entity["id"] for entity in entities])

        # Base note data
        note_data = {
            "content": note_value,
            "author": user
        }

        # Get category
        category_id = values["category"]
        if category_id == self._none_category:
            category_id = None

        category_name = None
        if category_id is not None:
            category = session.query(
                "select id, name from NoteCategory where id is \"{}\"".format(
                    category_id
                )
            ).first()
            if category:
                note_data["category"] = category
                category_name = category["name"]

        category_msg = ""
        if category_name:
            category_msg = " with category: \"{}\"".format(category_name)

        self.log.warning((
            "Creating note{} as User \"{}\" on "
            "AssetVersions: {} with value \"{}\""
        ).format(category_msg, username, asset_version_ids_str, note_value))

        # Create notes for entities
        for entity in entities:
            new_note = session.create("Note", note_data)
            entity["notes"].append(new_note)
            session.commit()
        return True


def register(session):
    '''Register plugin. Called when used as an plugin.'''

    MultipleNotesServer(session).register()
