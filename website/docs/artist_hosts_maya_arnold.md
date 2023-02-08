---
id: artist_hosts_maya_arnold
title: Arnold for Maya
sidebar_label: Arnold
---
## Arnold Scene Source (.ass)
Arnold Scene Source can be published as a single file or a sequence of files, determined by the frame range.

When creating the instance, two objectsets are created; `content` and `proxy`. Meshes in the `proxy` objectset will be the viewport representation when loading as `standin`. Proxy representations are stored as `resources` of the subset.

## Standin
Arnold Scene Source `ass` and Alembic `abc` are supported to load as standins.

If a subset has a proxy representation, this will be used as display in the viewport. At render time the standin path will be replaced using the recommended string replacement workflow;

https://help.autodesk.com/view/ARNOL/ENU/?guid=arnold_for_maya_operators_am_Updating_procedural_file_paths_with_string_replace_html
