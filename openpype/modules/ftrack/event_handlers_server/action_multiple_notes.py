from openpype.modules.ftrack.lib import ServerAction


class MultipleNotesServer(ServerAction):
    """Action adds same note for muliple AssetVersions."""

    identifier = "multiple.notes.server"
    label = "Multiple Notes (Server)"
    description = "Add same note to multiple Asset Versions"

    _none_category = "__NONE__"

    def discover(self, session, entities, event):
        ''' Validation '''
        valid = True
        for entity in entities:
            if entity.entity_type.lower() != "assetversion":
                valid = False
                break
        return valid

    def interface(self, session, entities, event):
        event_source = event["source"]
        user_info = event_source.get("user") or {}
        user_id = user_info.get("id")
        if not user_id:
            return {
                "success": False,
                "message": "Couldn't get user information."
            }

        if not event['data'].get('values', {}):
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
            all_categories = session.query('NoteCategory').all()
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
            return

        values = event["data"]["values"]
        if len(values) <= 0 or "note" not in values:
            return False

        # Get Note text
        note_value = values["note"]
        if note_value.lower().strip() == "":
            return False

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

        # Base note data
        note_data = {
            "content": note_value,
            "author": user
        }
        # Get category
        category_value = values["category"]
        if category_value != self._none_category:
            category = session.query(
                "NoteCategory where id is \"{}\"".format(category_value)
            ).one()
            note_data["category"] = category
        # Create notes for entities
        for entity in entities:
            new_note = session.create("Note", note_data)
            entity["notes"].append(new_note)
            session.commit()
        return True


def register(session):
    '''Register plugin. Called when used as an plugin.'''

    MultipleNotesServer(session).register()
