import os
import json


def default_custom_attributes_definition():
    json_file_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "custom_attributes.json"
    )
    with open(json_file_path, "r") as json_stream:
        data = json.load(json_stream)
    return data


def app_definitions_from_app_manager(app_manager):
    app_definitions = []
    for app_name, app in app_manager.applications.items():
        if app.enabled and app.is_host:
            app_definitions.append({
                app_name: app.full_label
            })

    if not app_definitions:
        app_definitions.append({"empty": "< Empty >"})
    return app_definitions


def tool_definitions_from_app_manager(app_manager):
    tools_data = []
    for tool_name, tool in app_manager.tools.items():
        tools_data.append({
            tool_name: tool.label
        })

    # Make sure there is at least one item
    if not tools_data:
        tools_data.append({"empty": "< Empty >"})
    return tools_data
