# Changelog


## [3.18.7](https://github.com/ynput/OpenPype/tree/3.18.7)


[Full Changelog](https://github.com/ynput/OpenPype/compare/3.18.6...3.18.7)

### **🆕 New features**


<details>
<summary>Chore: Wrapper for click proposal <a href="https://github.com/ynput/OpenPype/pull/5928">#5928</a></summary>

This is a proposal how to resolve issues with `click` python module. Issue https://github.com/ynput/OpenPype/issues/5921 reported that in Houdini 20+ is our click clashing with click in houdini, where is expected higher version. We can't update our version to support older pythons (NOTE older Python 3).


___

</details>

### **🚀 Enhancements**


<details>
<summary>Maya: Add repair action to hidden joints validator <a href="https://github.com/ynput/OpenPype/pull/6214">#6214</a></summary>

Joints Hidden is missing repair action, this adds it back


___

</details>


<details>
<summary>Blender: output node and EXR <a href="https://github.com/ynput/OpenPype/pull/6086">#6086</a></summary>

Output node now works correctly for Multilayer EXR and keeps existing links. The output now is handled entirely by the compositor node tree.


___

</details>


<details>
<summary>AYON Switch tool: Keep version after switch <a href="https://github.com/ynput/OpenPype/pull/6104">#6104</a></summary>

Keep version if only representation did change. The AYON variant of https://github.com/ynput/OpenPype/pull/4629


___

</details>


<details>
<summary>Loader AYON: Reset loader window on open <a href="https://github.com/ynput/OpenPype/pull/6170">#6170</a></summary>

Make sure loader tool is reset on each show.


___

</details>


<details>
<summary>Publisher: Show message with error on action failure <a href="https://github.com/ynput/OpenPype/pull/6179">#6179</a></summary>

This PR adds support for the publisher to show error message from running actions.Errors from actions will otherwise be hidden from user in various console outputs.Also include card for when action is finished.


___

</details>


<details>
<summary>AYON Applications: Remove djvview group from default applications <a href="https://github.com/ynput/OpenPype/pull/6188">#6188</a></summary>

The djv does not have group defined in models so the values are not used anywhere.


___

</details>


<details>
<summary>General: added fallback for broken ffprobe return <a href="https://github.com/ynput/OpenPype/pull/6189">#6189</a></summary>

Customer provided .exr returned width and height equal to 0 which caused error in `extract_thumbnail`. This tries to use oiiotool to get metadata about file, in our case it read it correctly.


___

</details>


<details>
<summary>Photoshop: High scaling in UIs <a href="https://github.com/ynput/OpenPype/pull/6190">#6190</a></summary>

Use `get_openpype_qt_app` to create `QApplication` in Photoshop.


___

</details>


<details>
<summary>Ftrack: Status update settings are not case insensitive. <a href="https://github.com/ynput/OpenPype/pull/6195">#6195</a></summary>

Make values for project_settings/ftrack/events/status_update case insensitive.


___

</details>


<details>
<summary>Thumbnail product filtering <a href="https://github.com/ynput/OpenPype/pull/6197">#6197</a></summary>

This PR introduces subset filtering for thumbnail extraction. This is to skip passes like zdepth which is not needed and can cause issues with extraction. Also speeds up publishing.


___

</details>


<details>
<summary>TimersManager: Idle dialog always on top <a href="https://github.com/ynput/OpenPype/pull/6201">#6201</a></summary>

Make stop timer dialog always on tophttps://app.clickup.com/t/6658547/OP-8033


___

</details>


<details>
<summary>AfterEffects: added toggle for applying values from DB during creation <a href="https://github.com/ynput/OpenPype/pull/6204">#6204</a></summary>

Previously values (resolution, duration) from Asset (eg. DB) were applied explicitly when instance of `render` product type was created. This PR adds toggle to Settings to disable this. (This allows artist to publish non standard length of composition, disabling of `Validate Scene Settings` is still required.)


___

</details>


<details>
<summary>Unreal: Update plugin commit <a href="https://github.com/ynput/OpenPype/pull/6208">#6208</a></summary>

Updated unreal plugin to latest main.


___

</details>

### **🐛 Bug fixes**


<details>
<summary>Traypublisher: editorial avoid audio tracks processing <a href="https://github.com/ynput/OpenPype/pull/6038">#6038</a></summary>

Avoiding audio tracks from EDL editorial publishing.


___

</details>


<details>
<summary>Resolve Inventory offsets clips when swapping versions <a href="https://github.com/ynput/OpenPype/pull/6128">#6128</a></summary>

Swapped version retain the offset and IDT of the timelime clip.closes: https://github.com/ynput/OpenPype/issues/6125


___

</details>


<details>
<summary>Publisher window as dialog <a href="https://github.com/ynput/OpenPype/pull/6176">#6176</a></summary>

Changing back Publisher window to QDialog.


___

</details>


<details>
<summary>Nuke: Validate write node fix error report - OP-8088 <a href="https://github.com/ynput/OpenPype/pull/6183">#6183</a></summary>

Report error was not printing the expected values from settings, but instead the values on the write node, leading to confusing messages like:
```
Traceback (most recent call last):
  File "C:\Users\tokejepsen\AppData\Local\Ynput\AYON\dependency_packages\ayon_2310271602_windows.zip\dependencies\pyblish\plugin.py", line 527, in __explicit_process
    runner(*args)
  File "C:\Users\tokejepsen\OpenPype\openpype\hosts\nuke\plugins\publish\validate_write_nodes.py", line 135, in process
    self._make_error(check)
  File "C:\Users\tokejepsen\OpenPype\openpype\hosts\nuke\plugins\publish\validate_write_nodes.py", line 149, in _make_error
    raise PublishXmlValidationError(
openpype.pipeline.publish.publish_plugins.PublishXmlValidationError: Write node's knobs values are not correct!
Knob 'channels' > Correct: `rgb` > Wrong: `rgb`
```
This PR changes the error report to:
```
Traceback (most recent call last):
  File "C:\Users\tokejepsen\AppData\Local\Ynput\AYON\dependency_packages\ayon_2310271602_windows.zip\dependencies\pyblish\plugin.py", line 527, in __explicit_process
    runner(*args)
  File "C:\Users\tokejepsen\OpenPype\openpype\hosts\nuke\plugins\publish\validate_write_nodes.py", line 135, in process
    self._make_error(check)
  File "C:\Users\tokejepsen\OpenPype\openpype\hosts\nuke\plugins\publish\validate_write_nodes.py", line 149, in _make_error
    raise PublishXmlValidationError(
openpype.pipeline.publish.publish_plugins.PublishXmlValidationError: Write node's knobs values are not correct!
Knob 'channels' > Expected: `['rg']` > Current: `rgb`
```



___

</details>


<details>
<summary>Nuke: Camera product type loaded is not updating - OP-7973 <a href="https://github.com/ynput/OpenPype/pull/6184">#6184</a></summary>

When updating the camera this error would appear:
```
(...)openpype/hosts/nuke/plugins/load/load_camera_abc.py", line 142, in update
    camera_node = nuke.toNode(object_name)
TypeError: toNode() argument 1 must be str, not Node
```



___

</details>


<details>
<summary>AYON settings: Use bundle name as variant in dev mode <a href="https://github.com/ynput/OpenPype/pull/6187">#6187</a></summary>

Make sure the bundle name is used in dev mode for settings variant.


___

</details>


<details>
<summary>Fusion: fix unwanted change to field name in Settings <a href="https://github.com/ynput/OpenPype/pull/6193">#6193</a></summary>

It should be `image_format` but in previous refactoring PR it fell back to original `output_formats` which caused enum not to show up and propagate into plugin.


___

</details>


<details>
<summary>Bugfix: AYON menu disappeared when the workspace has been changed in 3dsMax <a href="https://github.com/ynput/OpenPype/pull/6200">#6200</a></summary>

AYON plugins are not correctly registered when switching to different workspaces.


___

</details>


<details>
<summary>TrayPublisher: adding settings category to base creator classes <a href="https://github.com/ynput/OpenPype/pull/6202">#6202</a></summary>

Settings are resolving correctly as they suppose to.


___

</details>


<details>
<summary>Nuke: expose knobs backward compatibility fix - OP-8164 <a href="https://github.com/ynput/OpenPype/pull/6211">#6211</a></summary>

Fix backwards compatibility for settings `project_settings/nuke/create/CreateWriteRender/exposed_knobs`.


___

</details>


<details>
<summary>AE: fix local render doesn't push thumbnail to Ftrack <a href="https://github.com/ynput/OpenPype/pull/6212">#6212</a></summary>

Without thumbnail review is not clickable from main Versions list


___

</details>


<details>
<summary>Nuke: openpype expose knobs validator - OP-8166 <a href="https://github.com/ynput/OpenPype/pull/6213">#6213</a></summary>

Fix exposed knobs validator for backwards compatibility with missing settings.


___

</details>


<details>
<summary>Ftrack: Post-launch hook fix value lowering <a href="https://github.com/ynput/OpenPype/pull/6221">#6221</a></summary>

Fix lowerin of values in status mapping.


___

</details>

### **🔀 Refactored code**


<details>
<summary>Maya: Remove `shelf` class and shelf build on maya `userSetup.py` <a href="https://github.com/ynput/OpenPype/pull/5837">#5837</a></summary>

Remove shelf builder logic. It appeared to be unused and had bugs.


___

</details>

### **Merged pull requests**


<details>
<summary>Max: updated implementation of save_scene + small QOL improvements to host <a href="https://github.com/ynput/OpenPype/pull/6186">#6186</a></summary>

- Removed `has_unsaved_changes` from Max host as it looks to have been unused and unimplemented.
- Added and implemented `workfile_has_unsaved_changes` to Max host.
- Mirrored the Houdini host to implement the above into `save_scene` publish for Max.
- Added a line to `startup.ms` which opens the usual 'default' menu inside of Max (see screenshots).Current (Likely opens this menu due to one or more of the startup scripts used to insert OP menu):New:


___

</details>


<details>
<summary>Fusion: Use better resolution of Ayon apps on 4k display <a href="https://github.com/ynput/OpenPype/pull/6199">#6199</a></summary>

Changes size (makes it smaller) of Ayon apps (Workfiles, Loader) in Fusion on high definitions displays.


___

</details>


<details>
<summary>Update CONTRIBUTING.md <a href="https://github.com/ynput/OpenPype/pull/6210">#6210</a></summary>

Updating contributing guidelines to reflect the EOL state of repository
___

</details>


<details>
<summary>Deadline: Remove redundant instance_skeleton_data code - OP-8269 <a href="https://github.com/ynput/OpenPype/pull/6219">#6219</a></summary>

This PR https://github.com/ynput/OpenPype/pull/5186 re-introduced code about for the `instance_skeleton_data` but its actually not used since this variable gets overwritten later.


___

</details>




## [3.18.6](https://github.com/ynput/OpenPype/tree/3.18.6)


[Full Changelog](https://github.com/ynput/OpenPype/compare/3.18.5...3.18.6)

### **🚀 Enhancements**


<details>
<summary>AYON: Use `SettingsField` from ayon server <a href="https://github.com/ynput/OpenPype/pull/6173">#6173</a></summary>

This is preparation for new version of pydantic which will require to customize the field class for AYON purposes as raw pydantic Field could not be used.


___

</details>


<details>
<summary>Nuke: Expose write knobs - OP-7592 <a href="https://github.com/ynput/OpenPype/pull/6137">#6137</a></summary>

This PR adds `exposed_knobs` to the creator plugins settings at `ayon+settings://nuke/create/CreateWriteRender/exposed_knobs`.When exposed knobs will be linked from the write node to the outside publish group, for users to adjust.


___

</details>


<details>
<summary>AYON: Remove kitsu addon <a href="https://github.com/ynput/OpenPype/pull/6172">#6172</a></summary>

Removed kitsu addon from server addons because already has own repository.


___

</details>

### **🐛 Bug fixes**


<details>
<summary>Fusion: provide better logging for validate saver crash due type error <a href="https://github.com/ynput/OpenPype/pull/6082">#6082</a></summary>

Handles reported issue for `NoneType` error thrown in conversion `int(tool["Comments"][frame])`. It is most likely happening when saver node has no input connections.There is a validator for that, but it might be not obvious, that this error is caused by missing input connections and it has been already reported by `"Validate Saver Has Input"`.


___

</details>


<details>
<summary>Workfile Template Builder: Use correct variable in create placeholder <a href="https://github.com/ynput/OpenPype/pull/6141">#6141</a></summary>

Use correct variable where failed instances are stored for validation.


___

</details>


<details>
<summary>ExtractOIIOTranscode: Missing product_names to subsets conversion <a href="https://github.com/ynput/OpenPype/pull/6159">#6159</a></summary>

The `Product Names` filtering should be fixed with this.


___

</details>


<details>
<summary>Blender: Fix missing animation data when updating blend assets <a href="https://github.com/ynput/OpenPype/pull/6165">#6165</a></summary>

Fix missing animation data when updating blend assets.


___

</details>


<details>
<summary>TrayPublisher: Pre-fill of version works in AYON <a href="https://github.com/ynput/OpenPype/pull/6180">#6180</a></summary>

Use `folderPath` instead of `asset` in AYON mode to calculate next available version.


___

</details>

### **🔀 Refactored code**


<details>
<summary>Chore: remove Muster <a href="https://github.com/ynput/OpenPype/pull/6085">#6085</a></summary>

Muster isn't maintained for a long time and it wasn't working anyway. This is removing related code from the code base. If there is renewed interest in Muster, it needs to be re-implemented in modern AYON compatible way.


___

</details>

### **Merged pull requests**


<details>
<summary>Maya: change label in the render settings to be more readable <a href="https://github.com/ynput/OpenPype/pull/6134">#6134</a></summary>

AYON replacement for #5713.


___

</details>




## [3.18.5](https://github.com/ynput/OpenPype/tree/3.18.5)


[Full Changelog](https://github.com/ynput/OpenPype/compare/3.18.4...3.18.5)

### **🚀 Enhancements**


<details>
<summary>Chore: Add addons dir only if exists <a href="https://github.com/ynput/OpenPype/pull/6140">#6140</a></summary>

Do not add addons directory path for addons discovery if does not exists.


___

</details>


<details>
<summary>Hiero: Effect Categories - OP-7397 <a href="https://github.com/ynput/OpenPype/pull/6143">#6143</a></summary>

This PR introduces `Effect Categories` for the Hiero settings. This allows studios to split effect stacks into meaningful subsets.


___

</details>


<details>
<summary>Nuke: Render Workfile Attributes <a href="https://github.com/ynput/OpenPype/pull/6146">#6146</a></summary>

`Workfile Dependency` default value can now be controlled from project settings.`Use Published Workfile` makes using published workfiles for rendering optional.


___

</details>

### **🐛 Bug fixes**


<details>
<summary>Maya: Attributes are locked after publishing if they are locked in Camera Family <a href="https://github.com/ynput/OpenPype/pull/6073">#6073</a></summary>

This PR is to make sure unlock attributes only during the bake context, make sure attributes are relocked after to preserve the lock state of the original node being baked.


___

</details>


<details>
<summary>Missing nuke family Windows arguments <a href="https://github.com/ynput/OpenPype/pull/6131">#6131</a></summary>

Default Windows arguments for launching the Nuke family was missing.


___

</details>


<details>
<summary>AYON: Fix the bug on the limit group not being set correctly in Maya Deadline Setting <a href="https://github.com/ynput/OpenPype/pull/6139">#6139</a></summary>

This PR is to bug-fix the limit groups from maya deadline settings errored out when the user tries to edit the setting.


___

</details>


<details>
<summary>Chore: Transcoding extensions add missing '.tif' extension <a href="https://github.com/ynput/OpenPype/pull/6142">#6142</a></summary>

Image extensions in transcoding helper was missing `.tif` extension and had `.tiff` twice.


___

</details>


<details>
<summary>Blender: Use the new API for override context <a href="https://github.com/ynput/OpenPype/pull/6145">#6145</a></summary>

Blender 4.0 disabled the old API to override context. This API updates the code to use the new API.


___

</details>


<details>
<summary>BugFix: Include Model in FBX Loader in Houdini <a href="https://github.com/ynput/OpenPype/pull/6150">#6150</a></summary>

A quick bugfig where we can't load fbx exported from blender. The bug was reported here.


___

</details>


<details>
<summary>Blender: Restore actions to objects after update <a href="https://github.com/ynput/OpenPype/pull/6153">#6153</a></summary>

Restore the actions assigned to objects after updating assets from blend files.


___

</details>


<details>
<summary>Chore: Collect template data with hierarchy context <a href="https://github.com/ynput/OpenPype/pull/6154">#6154</a></summary>

Fixed queue loop where is used wrong variable to pop items from queue.


___

</details>


<details>
<summary>OP-6382 - Thumbnail Integration Problem <a href="https://github.com/ynput/OpenPype/pull/6156">#6156</a></summary>

This ticket alerted to 3 different cases of integration issues;
- [x] Using the Tray Publisher with the same image format (extension) for representation and review representation.
- [x] Clash on publish file path from output definitions in `ExtractOIIOTranscode`.
- [x] Clash on publish file from thumbnail in `ExtractThumbnail`There might be an issue with this fix, if a studio does not use the `{output}` token in their `render` anatomy template. But thinking if they have customized it, they will be responsible to maintain these edge cases.


___

</details>


<details>
<summary>Max: Bugfix saving camera scene errored out when creating render instance with multi-camera option turned off  <a href="https://github.com/ynput/OpenPype/pull/6163">#6163</a></summary>

This PR is to make sure the integrator of saving camera scene turned off and the render submitted successfully when multi-camera options being turned off in 3dsmax


___

</details>


<details>
<summary>Chore: Fix duplicated project name on create project structure <a href="https://github.com/ynput/OpenPype/pull/6166">#6166</a></summary>

Small fix in project folders. It is not used same variable name to change values which breaks values on any next loop.


___

</details>

### **Merged pull requests**


<details>
<summary>Maya: Remove duplicate plugin <a href="https://github.com/ynput/OpenPype/pull/6157">#6157</a></summary>

The two plugins below are doing the same work, so we can remove the one focused solely on lookdev.https://github.com/ynput/OpenPype/blob/develop/openpype/hosts/maya/plugins/publish/validate_look_members_unique.pyhttps://github.com/ynput/OpenPype/blob/develop/openpype/hosts/maya/plugins/publish/validate_node_ids_unique.py


___

</details>


<details>
<summary>Publish report viewer: Report items sorting <a href="https://github.com/ynput/OpenPype/pull/6092">#6092</a></summary>

Proposal of items sorting in Publish report viewer tool. Items are sorted by report creation time. Creation time is also added to publish report data when saved from publisher tool.


___

</details>


<details>
<summary>Maya: Extended error message <a href="https://github.com/ynput/OpenPype/pull/6161">#6161</a></summary>

Added more details to message


___

</details>


<details>
<summary>Fusion: Added settings for Fusion creators to legacy OP <a href="https://github.com/ynput/OpenPype/pull/6162">#6162</a></summary>

Added missing OP variant of setting for new Fusion creator.


___

</details>




## [3.18.4](https://github.com/ynput/OpenPype/tree/3.18.4)


[Full Changelog](https://github.com/ynput/OpenPype/compare/3.18.3...3.18.4)

### **🚀 Enhancements**


<details>
<summary>multiple render camera supports for 3dsmax <a href="https://github.com/ynput/OpenPype/pull/5124">#5124</a></summary>

Supports for rendering with multiple cameras in 3dsmax
- [x] Add Batch Render Layers functions
- [x] Rewrite lib.rendersetting and lib.renderproduct
- [x] Add multi-camera options in creator.
- [x] Collector with batch render-layer when multi-camera enabled.
- [x] Add instance plugin for saving scene files with different cameras respectively by using subprocess
- [x] Refactor submit_max_deadline
- [x] Check with metadata.json in submit publish job


___

</details>


<details>
<summary>Fusion: new creator for image product type <a href="https://github.com/ynput/OpenPype/pull/6057">#6057</a></summary>

In many DCC `render` product type is expected to be sequence of files. This PR adds new explicit creator for `image` product type which is focused on single frame image. Workflows for both product types might be a bit different, this gives artists more granularity to choose better workflow.


___

</details>

### **🐛 Bug fixes**


<details>
<summary>Maya: Account and ignore free image planes. <a href="https://github.com/ynput/OpenPype/pull/5993">#5993</a></summary>

Free image planes do not have the `->` path separator, so we need to account for that.


___

</details>


<details>
<summary>Blender: Fix long names for instances <a href="https://github.com/ynput/OpenPype/pull/6070">#6070</a></summary>

Changed naming for instances to use only final part of the `folderPath`.


___

</details>


<details>
<summary>Traypublisher & Chore: Instance version on follow workfile version <a href="https://github.com/ynput/OpenPype/pull/6117">#6117</a></summary>

If `follow_workfile_version` is enabled but context does not have filled workfile version, a version on instance is used instead.


___

</details>


<details>
<summary>Substance Painter: Thumbnail errors with PBR Texture Set <a href="https://github.com/ynput/OpenPype/pull/6127">#6127</a></summary>

When publishing with PBR Metallic Roughness as Output Template, Emissive Map errors out because of the missing channel in the material and the map can't be generated in Substance Painter. This PR is to make sure `imagestance.data["publish"] = False` so that the related "empty" texture instance would be skipped to generate the output.


___

</details>


<details>
<summary>Transcoding: Fix reading image sequences through oiiotool <a href="https://github.com/ynput/OpenPype/pull/6129">#6129</a></summary>

When transcoding image sequences, the second image onwards includes the invalid xml line of `Reading path/to/file.exr` of the oiiotool output.This is most likely not the best solution, but it fixes the issue and illustrates the problem.Error:
```
ERROR:pyblish.plugin:Traceback (most recent call last):
  File "C:\Users\tokejepsen\AppData\Local\Ynput\AYON\dependency_packages\ayon_2310271602_windows.zip\dependencies\pyblish\plugin.py", line 527, in __explicit_process
    runner(*args)
  File "C:\Users\tokejepsen\OpenPype\openpype\plugins\publish\extract_color_transcode.py", line 152, in process
  File "C:\Users\tokejepsen\OpenPype\openpype\lib\transcoding.py", line 1136, in convert_colorspace
    input_info = get_oiio_info_for_input(input_path, logger=logger)
  File "C:\Users\tokejepsen\OpenPype\openpype\lib\transcoding.py", line 124, in get_oiio_info_for_input
    output.append(parse_oiio_xml_output(xml_text, logger=logger))
  File "C:\Users\tokejepsen\OpenPype\openpype\lib\transcoding.py", line 276, in parse_oiio_xml_output
    tree = xml.etree.ElementTree.fromstring(xml_string)
  File "xml\etree\ElementTree.py", line 1347, in XML
xml.etree.ElementTree.ParseError: syntax error: line 1, column 0
Traceback (most recent call last):
  File "C:\Users\tokejepsen\AppData\Local\Ynput\AYON\dependency_packages\ayon_2310271602_windows.zip\dependencies\pyblish\plugin.py", line 527, in __explicit_process
    runner(*args)
  File "<string>", line 152, in process
  File "C:\Users\tokejepsen\OpenPype\openpype\lib\transcoding.py", line 1136, in convert_colorspace
    input_info = get_oiio_info_for_input(input_path, logger=logger)
  File "C:\Users\tokejepsen\OpenPype\openpype\lib\transcoding.py", line 124, in get_oiio_info_for_input
    output.append(parse_oiio_xml_output(xml_text, logger=logger))
  File "C:\Users\tokejepsen\OpenPype\openpype\lib\transcoding.py", line 276, in parse_oiio_xml_output
    tree = xml.etree.ElementTree.fromstring(xml_string)
  File "xml\etree\ElementTree.py", line 1347, in XML
xml.etree.ElementTree.ParseError: syntax error: line 1, column 0
```



___

</details>


<details>
<summary>AYON: Remove 'IntegrateHeroVersion' conversion <a href="https://github.com/ynput/OpenPype/pull/6130">#6130</a></summary>

Remove settings conversion for `IntegrateHeroVersion`.


___

</details>


<details>
<summary>Chore tools: Make sure style object is not garbage collected <a href="https://github.com/ynput/OpenPype/pull/6136">#6136</a></summary>

Minor fix in tool utils to make sure style C++ object is not garbage collected when not stored into variable.


___

</details>




## [3.18.3](https://github.com/ynput/OpenPype/tree/3.18.3)


[Full Changelog](https://github.com/ynput/OpenPype/compare/3.18.2...3.18.3)

### **🚀 Enhancements**


<details>
<summary>Maya: Apply initial viewport shader for Redshift Proxy after loading <a href="https://github.com/ynput/OpenPype/pull/6102">#6102</a></summary>

When the published redshift proxy is being loaded, the shader of the proxy is missing. This is different from the manual load through creating redshift proxy for files. This PR is to assign the default lambert to the redshift proxy, which replicates the same approach when the user manually loads the proxy with filepath.


___

</details>


<details>
<summary>General: We should keep current subset version when we switch only the representation type <a href="https://github.com/ynput/OpenPype/pull/4629">#4629</a></summary>

When we switch only the representation type of subsets, we should not get the representation from the last version of the subset.


___

</details>


<details>
<summary>Houdini: Add loader for redshift proxy family <a href="https://github.com/ynput/OpenPype/pull/5948">#5948</a></summary>

Loader for Redshift Proxy in Houdini (Thanks for @BigRoy contribution)


___

</details>


<details>
<summary>AfterEffects: exposing Deadline pools fields in Publisher UI <a href="https://github.com/ynput/OpenPype/pull/6079">#6079</a></summary>

Deadline pools might be adhoc set by an artist during publishing. AfterEffects implementation wasn't providing this.


___

</details>


<details>
<summary>Chore: Event callbacks can have order <a href="https://github.com/ynput/OpenPype/pull/6080">#6080</a></summary>

Event callbacks can have order in which are called, and fixed issue with getting function name and file when using `partial` function as callback.


___

</details>


<details>
<summary>AYON: OpenPype addon defines runtime dependencies <a href="https://github.com/ynput/OpenPype/pull/6095">#6095</a></summary>

Moved runtime dependencies from ayon-launcher to openpype addon.


___

</details>


<details>
<summary>Max: User's setting for scene unit scale  <a href="https://github.com/ynput/OpenPype/pull/6097">#6097</a></summary>

Options for users to set the default scene unit scale for their scenes.AYONLegacy OP


___

</details>


<details>
<summary>Chore: Remove deprecated templates profiles <a href="https://github.com/ynput/OpenPype/pull/6103">#6103</a></summary>

Remove deprecated usage of template profiles from settings.


___

</details>


<details>
<summary>Publisher: Window is not always on top <a href="https://github.com/ynput/OpenPype/pull/6107">#6107</a></summary>

Goal of this PR is to avoid using `WindowStaysOnTopHint` which causes issues, especially in cases when DCC shows a popup dialog that is behind the window, in that case both Publisher and DCC are frozen and there is nothing to do.


___

</details>


<details>
<summary>Houdini: add split job export support for Redshift ROP <a href="https://github.com/ynput/OpenPype/pull/6108">#6108</a></summary>

This is adding support for splitting of export and render jobs for Redshift as is already implemented for Vray, Mantra and Arnold.


___

</details>


<details>
<summary>Fusion: automatic installation of PySide2 <a href="https://github.com/ynput/OpenPype/pull/6111">#6111</a></summary>

This PR adds hook which tries to check if PySide2 is installed in Python used by Fusion and if not, it tries to install it automatically.


___

</details>


<details>
<summary>AYON: OpenPype addon dependencies <a href="https://github.com/ynput/OpenPype/pull/6113">#6113</a></summary>

Added `click` and `six` to requirements of openpype addon, and removed `Qt.py` requirement, which is not used anywhere.


___

</details>


<details>
<summary>Chore: Thumbnail representation has 'outputName' <a href="https://github.com/ynput/OpenPype/pull/6114">#6114</a></summary>

Add thumbnail output name to thumbnail representation to prevent same output filename during integration.


___

</details>


<details>
<summary>Kitsu: Clear credentials is safe <a href="https://github.com/ynput/OpenPype/pull/6116">#6116</a></summary>

Do not remove not existing keyring items.


___

</details>

### **🐛 Bug fixes**


<details>
<summary>Maya: bug fix the playblast without textures <a href="https://github.com/ynput/OpenPype/pull/5942">#5942</a></summary>

Bug fix the texture not being displayed when users enable texture placement in the OP/AYON setting


___

</details>


<details>
<summary>Blender: Workfile instance update fix <a href="https://github.com/ynput/OpenPype/pull/6048">#6048</a></summary>

Make sure workfile instance has always available 'instance_node' in transient data.


___

</details>


<details>
<summary>Publisher: Fix issue with parenting of widgets <a href="https://github.com/ynput/OpenPype/pull/6106">#6106</a></summary>

Don't use publisher window parent (usually main DCC window) as parent for report widget.


___

</details>


<details>
<summary>:wrench: fix and update pydocstyle configuration <a href="https://github.com/ynput/OpenPype/pull/6109">#6109</a></summary>

Fix pydocstyle configuration and move it to `pyproject.toml`


___

</details>


<details>
<summary>Nuke: Create camera node with the latest camera node class in Nuke 14 <a href="https://github.com/ynput/OpenPype/pull/6118">#6118</a></summary>

Creating instance fails for certain cameras, and it seems to only exist in Nuke 14. The reason of causing that contributes to the new camera node class `Camera4`  while the camera creator is working with the `Camera2` class.


___

</details>


<details>
<summary>Site Sync: small fixes in Loader <a href="https://github.com/ynput/OpenPype/pull/6119">#6119</a></summary>

Resolves issue:
- local and studio icons were same, they should be different
- `TypeError: string indices must be integers` error when downloading/uploading workfiles


___

</details>


<details>
<summary>Chore: Template data for editorial publishing <a href="https://github.com/ynput/OpenPype/pull/6120">#6120</a></summary>

Template data for editorial publishing are filled during `CollectInstanceAnatomyData`. The structure for editorial is determined, as it's required for ExtractHierarchy AYON/OpenPype plugins.


___

</details>


<details>
<summary>SceneInventory: Fix site sync icon conversion <a href="https://github.com/ynput/OpenPype/pull/6123">#6123</a></summary>

Use 'get_qt_icon' to convert icon definitions from site sync.


___

</details>




## [3.18.2](https://github.com/ynput/OpenPype/tree/3.18.2)


[Full Changelog](https://github.com/ynput/OpenPype/compare/3.18.1...3.18.2)

### **🚀 Enhancements**


<details>
<summary>Testing: Release Maya/Deadline job from pending when testing. <a href="https://github.com/ynput/OpenPype/pull/5988">#5988</a></summary>

When testing we wont put the Deadline jobs into pending with dependencies, so the worker can start as soon as possible.


___

</details>


<details>
<summary>Max: Tweaks on Extractions for the exporters <a href="https://github.com/ynput/OpenPype/pull/5814">#5814</a></summary>

With this PR
- Suspend Refresh would be introduced in abc & obj extractors for optimization.
- Allow users to choose the custom attributes to be included in abc exports


___

</details>


<details>
<summary>Maya: Optional preserve references. <a href="https://github.com/ynput/OpenPype/pull/5994">#5994</a></summary>

Optional preserve references when publishing Maya scenes.


___

</details>


<details>
<summary>AYON ftrack: Expect 'ayon' group in custom attributes <a href="https://github.com/ynput/OpenPype/pull/6066">#6066</a></summary>

Expect `ayon` group as one of options to get custom attributes.


___

</details>


<details>
<summary>AYON Chore: Remove dependencies related to separated addons <a href="https://github.com/ynput/OpenPype/pull/6074">#6074</a></summary>

Removed dependencies from openpype client pyproject.toml that are already defined by addons which require them.


___

</details>


<details>
<summary>Editorial & chore: Stop using pathlib2 <a href="https://github.com/ynput/OpenPype/pull/6075">#6075</a></summary>

Do not use `pathlib2` which is Python 2 backport for `pathlib` module in python 3.


___

</details>


<details>
<summary>Traypublisher: Correct validator label <a href="https://github.com/ynput/OpenPype/pull/6084">#6084</a></summary>

Use correct label for Validate filepaths.


___

</details>


<details>
<summary>Nuke: Extract Review Intermediate disabled when both Extract Review Mov and Extract Review Intermediate disabled in setting <a href="https://github.com/ynput/OpenPype/pull/6089">#6089</a></summary>

Report in Discord https://discord.com/channels/517362899170230292/563751989075378201/1187874498234556477


___

</details>

### **🐛 Bug fixes**


<details>
<summary>Maya: Bug fix the file from texture node not being collected correctly in Yeti Rig <a href="https://github.com/ynput/OpenPype/pull/5990">#5990</a></summary>

Fix the bug of collect Yeti Rig not being able to get the file parameter(s) from the texture node(s), resulting to the failure of publishing the textures to the resource directory.


___

</details>


<details>
<summary>Bug: fix AYON settings for Maya workspace <a href="https://github.com/ynput/OpenPype/pull/6069">#6069</a></summary>

This is changing bug in default AYON setting for Maya workspace, where missing semicolumn caused workspace not being set. This is also syncing default workspace settings to OpenPype


___

</details>


<details>
<summary>Refactor colorspace handling in CollectColorspace plugin <a href="https://github.com/ynput/OpenPype/pull/6033">#6033</a></summary>

Traypublisher is now capable set available colorspaces or roles to publishing images sequence or video. This is fix of new implementation where we allowed to use roles in the enumerator selector.


___

</details>


<details>
<summary>Bugfix: Houdini render split bugs <a href="https://github.com/ynput/OpenPype/pull/6037">#6037</a></summary>

This PR is a follow up PR to https://github.com/ynput/OpenPype/pull/5420This PR does:
- refactor `get_output_parameter` to what is used to be.
- fix a bug with split render
- rename `exportJob` flag to `split_render`


___

</details>


<details>
<summary>Fusion: fix for single frame rendering <a href="https://github.com/ynput/OpenPype/pull/6056">#6056</a></summary>

Fixes publishes of single frame of `render` product type.


___

</details>


<details>
<summary>Photoshop: fix layer publish thumbnail missing in loader <a href="https://github.com/ynput/OpenPype/pull/6061">#6061</a></summary>

Thumbnails from any products (either `review` nor separate layer instances) weren't stored in Ayon.This resulted in not showing them in Loader and Server UI. After this PR thumbnails should be shown in the Loader and on the Server (`http://YOUR_AYON_HOSTNAME:5000/projects/YOUR_PROJECT/browser`).


___

</details>


<details>
<summary>AYON Chore: Do not use thumbnailSource for thumbnail integration <a href="https://github.com/ynput/OpenPype/pull/6063">#6063</a></summary>

Do not use `thumbnailSource` for thumbnail integration.


___

</details>


<details>
<summary>Photoshop: fix creation of .mov <a href="https://github.com/ynput/OpenPype/pull/6064">#6064</a></summary>

Generation of .mov file with 1 frame per published layer was failing.


___

</details>


<details>
<summary>Photoshop: fix Collect Color Coded settings <a href="https://github.com/ynput/OpenPype/pull/6065">#6065</a></summary>

Fix for wrong default value for `Collect Color Coded Instances` Settings


___

</details>


<details>
<summary>Bug: Fix Publisher parent window in Nuke <a href="https://github.com/ynput/OpenPype/pull/6067">#6067</a></summary>

Fixing issue where publisher parent window wasn't set because wrong use of version constant.


___

</details>


<details>
<summary>Python console widget: Save registry fix <a href="https://github.com/ynput/OpenPype/pull/6076">#6076</a></summary>

Do not save registry until there is something to save.


___

</details>


<details>
<summary>Ftrack: update asset names for multiple reviewable items <a href="https://github.com/ynput/OpenPype/pull/6077">#6077</a></summary>

Multiple reviewable assetVersion components with better grouping to asset version name.


___

</details>


<details>
<summary>Ftrack: DJV action fixes <a href="https://github.com/ynput/OpenPype/pull/6098">#6098</a></summary>

Fix bugs in DJV  ftrack action.


___

</details>


<details>
<summary>AYON Workfiles tool: Fix arrow to timezone typo <a href="https://github.com/ynput/OpenPype/pull/6099">#6099</a></summary>

Fix parenthesis typo with arrow local timezone function.


___

</details>

### **🔀 Refactored code**


<details>
<summary>Chore: Update folder-favorite icon to ayon icon <a href="https://github.com/ynput/OpenPype/pull/5718">#5718</a></summary>

Updates old "Pype-2.0-era" (from ancient greece times) to AYON logo equivalent.I believe it's only used in Nuke.


___

</details>

### **Merged pull requests**


<details>
<summary>Chore: Maya / Nuke remove publish gui filters from settings <a href="https://github.com/ynput/OpenPype/pull/5570">#5570</a></summary>

- Remove Publish GUI Filters from Nuke settings
- Remove Publish GUI Filters from Maya settings


___

</details>


<details>
<summary>Fusion: Project/User option for output format (create_saver) <a href="https://github.com/ynput/OpenPype/pull/6045">#6045</a></summary>

Adds "Output Image Format" option which can be set via project settings and overwritten by users in "Create" menu. This replaces the current behaviour of being hardcoded to "exr". Replacing the need for people to manually edit the saver path if they require a different extension.


___

</details>


<details>
<summary>Fusion: Output Image Format Updating Instances (create_saver) <a href="https://github.com/ynput/OpenPype/pull/6060">#6060</a></summary>

Adds the ability to update Saver image output format if changed in the Publish UI.~~Adds an optional validator that compares "Output Image Format" in the Publish menu against the one currently found on the saver. It then offers a repair action to update the output extension on the saver.~~


___

</details>


<details>
<summary>Tests: Fix representation count for AE legacy test <a href="https://github.com/ynput/OpenPype/pull/6072">#6072</a></summary>


___

</details>




## [3.18.1](https://github.com/ynput/OpenPype/tree/3.18.1)


[Full Changelog](https://github.com/ynput/OpenPype/compare/3.18.0...3.18.1)

### **🚀 Enhancements**


<details>
<summary>AYON: Update ayon api to 1.0.0-rc.3 <a href="https://github.com/ynput/OpenPype/pull/6052">#6052</a></summary>

Updated ayon python api to 1.0.0-rc.3.


___

</details>




## [3.18.0](https://github.com/ynput/OpenPype/tree/3.18.0)


[Full Changelog](https://github.com/ynput/OpenPype/compare/...3.18.0)

### **🐛 Bug fixes**


<details>
<summary>Chore: Fix subst paths handling <a href="https://github.com/ynput/OpenPype/pull/5702">#5702</a></summary>

Make sure that source disk ends with `\` instead of destination disk.


___

</details>




## [3.17.7](https://github.com/ynput/OpenPype/tree/3.17.7)


[Full Changelog](https://github.com/ynput/OpenPype/compare/3.17.6...3.17.7)

### **🆕 New features**


<details>
<summary>AYON: Use folder path as unique identifier <a href="https://github.com/ynput/OpenPype/pull/5817">#5817</a></summary>

Use folder path instead of asset name as unique identifier, with OpenPype compatibility.


___

</details>


<details>
<summary>Houdini: Farm caching submission to Deadline  <a href="https://github.com/ynput/OpenPype/pull/4903">#4903</a></summary>

Implements functionality to offload instances of the specific families to be processed on Deadline instead of locally. This increases productivity as artist can use local machine could be used for other tasks.Implemented for families:
- [x] ass
- [x] redshift proxy
- [x] ifd
- [x] abc
- [x] bgeo
- [x] vdb


___

</details>


<details>
<summary>Houdini: Add support to split Deadline render tasks in export + render <a href="https://github.com/ynput/OpenPype/pull/5420">#5420</a></summary>

This adds initial support in Houdini so when submitting render jobs to Deadline it's not running as a single Houdini task but rather it gets split in two different tasks: Export + Render. This way it's more efficient as we only need a Houdini license during the export step and the render tasks can run exclusively with a render license. Moreover, we aren't wasting all the overhead time of opening the render scene in Houdini for every frame.I have also added the corresponding settings json files so we can set some of the default values for the Houdini deadline submitter.


___

</details>


<details>
<summary>Wrap: new integration <a href="https://github.com/ynput/OpenPype/pull/5823">#5823</a></summary>

These modifications are necessary for adding Wrap integration (DCC handling scans and textures) .


___

</details>


<details>
<summary>AYON: Prepare for 'data' via graphql <a href="https://github.com/ynput/OpenPype/pull/5923">#5923</a></summary>

AYON server does support to query 'data' field for hierarchy entities (project > ... > representation) using GraphQl since version 0.5.5. Because of this PR in ayon-python-api it is required to modify custom graphql function in `openpype.client` to support that option.


___

</details>


<details>
<summary>Chore AYON: AYON addon class <a href="https://github.com/ynput/OpenPype/pull/5937">#5937</a></summary>

Introduced base class for AYON addon in openpype modules discovery logic.


___

</details>


<details>
<summary>Asset Usage Reporter Tool <a href="https://github.com/ynput/OpenPype/pull/5946">#5946</a></summary>

This adds simple tool for OpenPype mode that will go over all published workfiles and print linked assets and their version:This is created per project and can be exported in csv file or copied to clipboard in _"ASCII Human readable form"_.


___

</details>


<details>
<summary>Testing: dump_databases flag <a href="https://github.com/ynput/OpenPype/pull/5955">#5955</a></summary>

This introduces a `dump_databases` flag which makes it convenient to output the resulting database of a successful test run. The flag supports two formats; `bson` and `json`.Due to outputting to the test data folder, when dumping the databases, the test data folder will persist.Split from https://github.com/ynput/OpenPype/pull/5644


___

</details>


<details>
<summary>SiteSync: implemented in Ayon Loader <a href="https://github.com/ynput/OpenPype/pull/5962">#5962</a></summary>

Implemented `Availability` column in Ayon loader and redo of loaders to `ActionItems` in representation window there.


___

</details>


<details>
<summary>AYON: Workfile template build works <a href="https://github.com/ynput/OpenPype/pull/5975">#5975</a></summary>

Modified workfile template builder to work, to some degree, in AYON mode.


___

</details>

### **🚀 Enhancements**


<details>
<summary>Maya: Small Tweaks on Validator for Look Default Shader Connection for Maya 2024 <a href="https://github.com/ynput/OpenPype/pull/5957">#5957</a></summary>

Resolve https://github.com/ynput/OpenPype/issues/5269


___

</details>


<details>
<summary>Settings: Changes in default settings <a href="https://github.com/ynput/OpenPype/pull/5983">#5983</a></summary>

We've made some changes in the default settings as several application versions were obsolete (Maya 18, Nuke 11, PS 2020, etc). Also added tools and changed settings for Blender, Maya, and Blender. 

All should work as usual.
___

</details>


<details>
<summary>Testing: Do not persist data by default in Maya/Deadline. <a href="https://github.com/ynput/OpenPype/pull/5987">#5987</a></summary>

This is similar to the Maya publishing test.


___

</details>


<details>
<summary>Max: Validate loaded plugins tweaks <a href="https://github.com/ynput/OpenPype/pull/5820">#5820</a></summary>

In the current development of 3dsMax, users need to use separate validators to validate if certain plugins being loaded before the extraction. For example, usd extractor in model family, prt/tycache extractor in pointcloud/tycache family.But with the PR where implements optional validate loaded plugin, users just need to put what kind of plugins they want to validate in the settings. They no longer need to go through all the separate plugin validators when publishing, and only one validator would do all the check on the loaded plugins before extraction.


___

</details>


<details>
<summary>Nuke: Change context label enhancement <a href="https://github.com/ynput/OpenPype/pull/5887">#5887</a></summary>

Use QAction to change label of context label in Nuke pipeline menu.


___

</details>


<details>
<summary>Chore: Do not use template data as source for context <a href="https://github.com/ynput/OpenPype/pull/5918">#5918</a></summary>

Use available information on context to receive context data instead of using `"anatomyData"` during publishing.


___

</details>


<details>
<summary>Houdini: Add python3.10 libs for Houdini 20 startup <a href="https://github.com/ynput/OpenPype/pull/5932">#5932</a></summary>

Add python3.10 libs for Houdini 20 startup


___

</details>


<details>
<summary>General: Use colorspace data when creating thumbnail <a href="https://github.com/ynput/OpenPype/pull/5938">#5938</a></summary>

Thumbnails with applied colormanagement.


___

</details>


<details>
<summary>Ftrack: rewriting component creation to support multiple thumbnails <a href="https://github.com/ynput/OpenPype/pull/5939">#5939</a></summary>

The creation of Ftrack components needs to allow for multiple thumbnails. This is important in situations where there could be several reviewable streams, like in the case of a nuke intermediate files preset. Customers have asked for unique thumbnails for each data stream.For instance, one stream might contain a baked LUT file along with Display and View. Another stream might only include the baked Display and View. These variations can change the overall look. Thus, we found it necessary to depict these differences via thumbnails.


___

</details>


<details>
<summary>Chore: PySide6 tree view style <a href="https://github.com/ynput/OpenPype/pull/5940">#5940</a></summary>

Define solid color for background of branch in QTreeView.


___

</details>


<details>
<summary>Nuke: Explicit Thumbnail workflow <a href="https://github.com/ynput/OpenPype/pull/5941">#5941</a></summary>

Nuke made a shift from using its own plugin to a global one for thumbnail creation. This was because it had to handle several thumbnail workflows for baking intermediate data streams. To manage this, the global plugin had to be upgraded. Now, each baking stream can set a unique tag 'need_thumbnail'. This tag is used to mark representations that need a thumbnail.


___

</details>


<details>
<summary>Global: extract thumbnail with new settings <a href="https://github.com/ynput/OpenPype/pull/5944">#5944</a></summary>

Settings are now configurable for the following:
- target size of thumbnail - source or constrained to specific
- where should be frame taken from in sequence or video file
- if thumbnail should be integrated or not
- background color for letter boxes
- added AYON settings


___

</details>


<details>
<summary>RoyalRender: inject submitter environment to the royal render job <a href="https://github.com/ynput/OpenPype/pull/5958">#5958</a></summary>

This is an attempt to solve runtime environment injection for render jobs in RoyalRender as there is no easy way to implement something like `GlobalJobPreload` logic in Deadline. Idea is to inject OpenPype environments directly to the job itself.


___

</details>


<details>
<summary>General: Use manual thumbnail if present when publishing <a href="https://github.com/ynput/OpenPype/pull/5969">#5969</a></summary>

Use manual thumbnail added to the publisher instead of using it from published representation.


___

</details>


<details>
<summary>AYON: Change of server url should work as expected <a href="https://github.com/ynput/OpenPype/pull/5971">#5971</a></summary>

Using login action in tray menu to change server url should correctly start new process without issues of missing bundle or previous url.


___

</details>


<details>
<summary>AYON: make sure the AYON menu bar in 3dsMax is named AYON when AYON launches <a href="https://github.com/ynput/OpenPype/pull/5972">#5972</a></summary>

Renaming the menu bar in 3dsMax for AYON and some cosmetic fix in the docstring


___

</details>


<details>
<summary>Resolve: renaming menu to AYON <a href="https://github.com/ynput/OpenPype/pull/5974">#5974</a></summary>

Resolve in Ayon is now having aligned name.


___

</details>


<details>
<summary>Hiero: custom tools menu rename <a href="https://github.com/ynput/OpenPype/pull/5976">#5976</a></summary>

- OpenPype Tools are now Custom Tools menu
- fixing order of tools. Create should be first.


___

</details>


<details>
<summary>nuke: updating name for custom tools menu item <a href="https://github.com/ynput/OpenPype/pull/5977">#5977</a></summary>

- Ayon variant of settings renamed `Custom Tools` menu item


___

</details>


<details>
<summary>fusion: AYON renaming menu <a href="https://github.com/ynput/OpenPype/pull/5978">#5978</a></summary>

Fusion is having Ayon menu.


___

</details>


<details>
<summary>Blender: Changed the labels for Layout JSON Extractor <a href="https://github.com/ynput/OpenPype/pull/5981">#5981</a></summary>

Changed the labels for Blender's Layout JSON Extractor.


___

</details>


<details>
<summary>Testing: Skip Arnold license for test rendering. <a href="https://github.com/ynput/OpenPype/pull/5984">#5984</a></summary>

Skip license check when rendering for testing.


___

</details>


<details>
<summary>Testing: Validate errors and failed status from Deadline jobs. <a href="https://github.com/ynput/OpenPype/pull/5986">#5986</a></summary>

While waiting for the Deadline jobs to finish, we query the errors on the job and its dependent jobs to fail as early as possible. Plus the failed status.


___

</details>


<details>
<summary>AYON: rename Openpype Tools as Custom Tools in Maya Host <a href="https://github.com/ynput/OpenPype/pull/5991">#5991</a></summary>

Rename Openpype Tools as Custom Tools in Maya Host in


___

</details>


<details>
<summary>AYON: Use AYON label in ayon mode <a href="https://github.com/ynput/OpenPype/pull/5995">#5995</a></summary>

Replaced OpenPype with AYON in AYON mode and added bundle nam to information.


___

</details>


<details>
<summary>AYON: Update ayon python api <a href="https://github.com/ynput/OpenPype/pull/6002">#6002</a></summary>

Updated ayon-python-api to '1.0.0-rc.1'.


___

</details>


<details>
<summary>Max: Add missing repair action in validate resolution setting <a href="https://github.com/ynput/OpenPype/pull/6014">#6014</a></summary>

Add missing repair action for validate resolution setting


___

</details>


<details>
<summary>Add the AYON/OP settings to enable extractor for model family in 3dsmax <a href="https://github.com/ynput/OpenPype/pull/6027">#6027</a></summary>

Add the AYON/OP settings to enable extractor for model family in 3dsmax


___

</details>


<details>
<summary>Bugfix: Fix error message formatting if ayon executable can't be found by deadline <a href="https://github.com/ynput/OpenPype/pull/6028">#6028</a></summary>

Without this fix the error message would report executables string with `;` between EACH character, similar to this PR: https://github.com/ynput/OpenPype/pull/5815However that PR apparently missed also fixing it in `GlobalJobPreLoad` and only fixed it in `Ayon.py` plugin.


___

</details>


<details>
<summary>Show slightly different info in AYON mode <a href="https://github.com/ynput/OpenPype/pull/6031">#6031</a></summary>

This PR changes what is shown in Tray menu in AYON mode. Previously, it showed version of OpenPype that is very confusing in AYON mode. So this now shows AYON version instead. When clicked, it will opene AYON info window, where OpenPype version is now added, for debugging purposes.


___

</details>


<details>
<summary>AYON Editorial: Hierarchy context have names as keys <a href="https://github.com/ynput/OpenPype/pull/6041">#6041</a></summary>

Use folder name as keys in `hierarchyContext` and modify hierachy extraction accordingly.


___

</details>


<details>
<summary>AYON: Convert the createAt value to local timezone <a href="https://github.com/ynput/OpenPype/pull/6043">#6043</a></summary>

Show correct create time in UIs.


___

</details>

### **🐛 Bug fixes**


<details>
<summary>Maya: Render creation - fix broken imports <a href="https://github.com/ynput/OpenPype/pull/5893">#5893</a></summary>

Maya specific imports were moved to specific methods but not in all cases by #5775. This is just quickly restoring functionality without questioning that decision.


___

</details>


<details>
<summary>Maya: fix crashing model renderset collector <a href="https://github.com/ynput/OpenPype/pull/5929">#5929</a></summary>

This fix is handling case where model is in some type of render sets but no other connections are made there. Publishing this model would fail with `RuntimeError: Found no items to list the history for.`


___

</details>


<details>
<summary>Maya: Remove duplicated attributes of MTOA verbosity level  <a href="https://github.com/ynput/OpenPype/pull/5945">#5945</a></summary>

Remove duplicated attributes implementation mentioned in https://github.com/ynput/OpenPype/pull/5931#discussion_r1402175289


___

</details>


<details>
<summary>Maya: Bug fix Redshift Proxy not being successfully published <a href="https://github.com/ynput/OpenPype/pull/5956">#5956</a></summary>

Bug fix redshift proxy family not being successfully published due to the error found in integrate.py


___

</details>


<details>
<summary>Maya: Bug fix load image for texturesetMain <a href="https://github.com/ynput/OpenPype/pull/6011">#6011</a></summary>

Bug fix load image with file node for texturesetMain


___

</details>


<details>
<summary>Maya: bug fix the repair function in validate_rendersettings <a href="https://github.com/ynput/OpenPype/pull/6021">#6021</a></summary>

The following error has been encountered below:
```
// pyblish.pyblish.plugin.Action : Finding failed instances..
// pyblish.pyblish.plugin.Action : Attempting repair for instance: renderLookdevMain ...
// Error: pyblish.plugin : Traceback (most recent call last):
//   File "C:\Users\lbate\AppData\Local\Ynput\AYON\dependency_packages\ayon_2310271602_windows.zip\dependencies\pyblish\plugin.py", line 527, in __explicit_process
//     runner(*args)
//   File "C:\Users\lbate\AppData\Local\Ynput\AYON\addons\openpype_3.17.7-nightly.6\openpype\pipeline\publish\publish_plugins.py", line 241, in process
//     plugin.repair(instance)
//   File "C:\Users\lbate\AppData\Local\Ynput\AYON\addons\openpype_3.17.7-nightly.6\openpype\hosts\maya\plugins\publish\validate_rendersettings.py", line 395, in repair
//     cmds.setAttr("{}.{}".format(node, prefix_attr),
// UnboundLocalError: local variable 'node' referenced before assignment
// Traceback (most recent call last):
//   File "C:\Users\lbate\AppData\Local\Ynput\AYON\dependency_packages\ayon_2310271602_windows.zip\dependencies\pyblish\plugin.py", line 527, in __explicit_process
//     runner(*args)
//   File "C:\Users\lbate\AppData\Local\Ynput\AYON\addons\openpype_3.17.7-nightly.6\openpype\pipeline\publish\publish_plugins.py", line 241, in process
//     plugin.repair(instance)
//   File "C:\Users\lbate\AppData\Local\Ynput\AYON\addons\openpype_3.17.7-nightly.6\openpype\hosts\maya\plugins\publish\validate_rendersettings.py", line 395, in repair
//     cmds.setAttr("{}.{}".format(node, prefix_attr),
// UnboundLocalError: local variable 'node' referenced before assignment
```
This PR is a fix for that


___

</details>


<details>
<summary>Fusion: Render avoid unhashable type `BlackmagicFusion.PyRemoteObject` error <a href="https://github.com/ynput/OpenPype/pull/5672">#5672</a></summary>

Fix Fusion 18.6+ support: Avoid issues with Fusion's `BlackmagicFusion.PyRemoteObject` instances being unhashable.
```python
Traceback (most recent call last):
  File "E:\openpype\OpenPype\.venv\lib\site-packages\pyblish\plugin.py", line 527, in __explicit_process
    runner(*args)
  File "E:\openpype\OpenPype\openpype\hosts\fusion\plugins\publish\extract_render_local.py", line 61, in process
    result = self.render(instance)
  File "E:\openpype\OpenPype\openpype\hosts\fusion\plugins\publish\extract_render_local.py", line 118, in render
    with enabled_savers(current_comp, savers_to_render):
  File "C:\Users\User\AppData\Local\Programs\Python\Python39\lib\contextlib.py", line 119, in __enter__
    return next(self.gen)
  File "E:\openpype\OpenPype\openpype\hosts\fusion\plugins\publish\extract_render_local.py", line 33, in enabled_savers
    original_states[saver] = original_state
TypeError: unhashable type: 'BlackmagicFusion.PyRemoteObject'
```



___

</details>


<details>
<summary>Nuke: Validate Nuke Write Nodes refactor to use variable `node_value` instead of `value` <a href="https://github.com/ynput/OpenPype/pull/5764">#5764</a></summary>

Nuke: Validate Nuke Write Nodes refactor to use variable `node_value` instead of `value`The variable `value` only exists as the last variable value in the `for value in values` loop and might not be declared if `values` is an empty iterable.


___

</details>


<details>
<summary>resolve: fixing loader handles calculation <a href="https://github.com/ynput/OpenPype/pull/5863">#5863</a></summary>

Resolve was not correctly calculating duration of database related duration.


___

</details>


<details>
<summary>Chore: Staging mode determination <a href="https://github.com/ynput/OpenPype/pull/5895">#5895</a></summary>

Resources use `is_staging_enabled` function instead of `is_running_staging` to determine if should use staging icon. And fixed comparison bug in `is_running_staging`.


___

</details>


<details>
<summary>AYON: Handle staging templates category <a href="https://github.com/ynput/OpenPype/pull/5905">#5905</a></summary>

Staging anatomy templates category is handled during project templates conversion. The keys are stored into `others` with `"staging_"` prefix.


___

</details>


<details>
<summary>Max: fix the subset name not changing accordingly after the variant name changes <a href="https://github.com/ynput/OpenPype/pull/5911">#5911</a></summary>

Resolve #5902


___

</details>


<details>
<summary>AYON: Loader tool bugs hunt <a href="https://github.com/ynput/OpenPype/pull/5915">#5915</a></summary>

Fix issues with invalid representation ids in loaded containers and handle missing product type in server database.


___

</details>


<details>
<summary>Publisher: Bugfixes and enhancements <a href="https://github.com/ynput/OpenPype/pull/5924">#5924</a></summary>

Small fixes/enhancements in publisher UI.


___

</details>


<details>
<summary>Maya: Supports for additional Job Info and Plugin Info in deadline submission <a href="https://github.com/ynput/OpenPype/pull/5931">#5931</a></summary>

This PR is to resolve some of the attributes such as MTOA's `ArnoldVerbose` are not preserved on farm and users can use the project settings to add the attributes back to either job or plugin Info.


___

</details>


<details>
<summary>Bugfix: Houdini license validator missing families <a href="https://github.com/ynput/OpenPype/pull/5934">#5934</a></summary>

Adding missing families to Houdini license validator.


___

</details>


<details>
<summary>TrayPublisher: adding back `asset_doc` variable <a href="https://github.com/ynput/OpenPype/pull/5943">#5943</a></summary>

Returning variable which had been removed accidentally in previous PR.


___

</details>


<details>
<summary>Settings: Fix ModulesManager init args <a href="https://github.com/ynput/OpenPype/pull/5947">#5947</a></summary>

Remove usage of kwargs to create ModulesManager.


___

</details>


<details>
<summary>Blender: Fix Deadline Frames per task <a href="https://github.com/ynput/OpenPype/pull/5949">#5949</a></summary>

Fixed a problem with Frames per task setting not being applied when publishing a render.


___

</details>


<details>
<summary>Testing: Fix is_test_failed <a href="https://github.com/ynput/OpenPype/pull/5951">#5951</a></summary>

`is_test_failed` is used (exclusively) on module fixtures to determine whether the tests have failed or not. This determines whether to run tear down code like cleaning up the database and temporary files.But in the module scope `request.node.rep_call` is not available, which results in `is_test_failed` always returning `True`, and no tear down code get executed.The solution was taken from; https://github.com/pytest-dev/pytest/issues/5090


___

</details>


<details>
<summary>Harmony: Fix local rendering <a href="https://github.com/ynput/OpenPype/pull/5953">#5953</a></summary>

Local rendering was throwing warning about license, but didn't fail per se. It just didn't produce anything.


___

</details>


<details>
<summary>Testing: hou module should be within class code. <a href="https://github.com/ynput/OpenPype/pull/5954">#5954</a></summary>

`hou` module should be within the class code else we'll get pyblish errors from needing to skip the plugin.


___

</details>


<details>
<summary>Maya: Add Label to MayaUSDReferenceLoader <a href="https://github.com/ynput/OpenPype/pull/5964">#5964</a></summary>

As the create placeholder dialog displays the two distinct loaders with the same name, this PR is to distinguish Maya USD Reference Loaders from the loaders of which inherited from. See the screenshot below:


___

</details>


<details>
<summary>Max: Bug fix the resolution not being shown correctly in review burnin  <a href="https://github.com/ynput/OpenPype/pull/5965">#5965</a></summary>

The resolution is not being shown correctly in review burnin


___

</details>


<details>
<summary>AYON: Fix thumbnail integration <a href="https://github.com/ynput/OpenPype/pull/5970">#5970</a></summary>

Thumbnail integration could cause crash of server if thumbnail id was changed for the same entity id multiple times. Modified the code to avoid that issue.


___

</details>


<details>
<summary>Photoshop: Updated label in Settings <a href="https://github.com/ynput/OpenPype/pull/5980">#5980</a></summary>

Replaced wrong label from different plugin.


___

</details>


<details>
<summary>Photoshop: Fix removed unsupported Path <a href="https://github.com/ynput/OpenPype/pull/5996">#5996</a></summary>

Path is not json serializable by default, it is not necessary, better model reused.


___

</details>


<details>
<summary>AYON: Prepare functions for newer ayon-python-api <a href="https://github.com/ynput/OpenPype/pull/5997">#5997</a></summary>

Newer ayon python api will add new filtering options or change order of existing. Kwargs are used in client code to prevent issues on update.


___

</details>


<details>
<summary>AYON: Conversion of the new playblast settings in Maya <a href="https://github.com/ynput/OpenPype/pull/6000">#6000</a></summary>

Conversion of the new playblast settings in Maya


___

</details>


<details>
<summary>AYON: Bug fix for loading Mesh in Substance Painter as new project not working <a href="https://github.com/ynput/OpenPype/pull/6004">#6004</a></summary>

Substance Painter in AYON can't load mesh for creating a new project


___

</details>


<details>
<summary>Deadline: correct webservice couldn't be selected in Ayon <a href="https://github.com/ynput/OpenPype/pull/6007">#6007</a></summary>

Changed the Setting model to mimic more OP approach as it needs to live together for time being.


___

</details>


<details>
<summary>AYON tools: Fix refresh thread <a href="https://github.com/ynput/OpenPype/pull/6008">#6008</a></summary>

Trigger 'refresh_finished' signal out of 'run' method.


___

</details>


<details>
<summary>Ftrack: multiple reviewable components missing variable <a href="https://github.com/ynput/OpenPype/pull/6013">#6013</a></summary>

Missing variable in code for editorial publishing in traypublisher.


___

</details>


<details>
<summary>TVPaint: Expect legacy instances in metadata <a href="https://github.com/ynput/OpenPype/pull/6015">#6015</a></summary>

Do not expect `"workfileInstances"` constains only new type instance data with `creator_identifier`.


___

</details>


<details>
<summary>Bugfix: handle missing key in Deadline <a href="https://github.com/ynput/OpenPype/pull/6019">#6019</a></summary>

This quickly fixes bug introduced by #5420


___

</details>


<details>
<summary>Revert `extractenvironments` behaviour <a href="https://github.com/ynput/OpenPype/pull/6020">#6020</a></summary>

This is returning original behaviour of `extractenvironments` command from before #5958 so we restore functionality.


___

</details>


<details>
<summary>OP-7535 - Fix renaming composition in AE <a href="https://github.com/ynput/OpenPype/pull/6025">#6025</a></summary>

Removing of `render` instance caused renaming of composition to `dummyComp` which caused issue in publishing in next attempt.This PR stores original composition name(cleaned up for product name creation) and uses it if instance needs to be removed.


___

</details>


<details>
<summary>Refactor code to skip instance creation for new assets <a href="https://github.com/ynput/OpenPype/pull/6029">#6029</a></summary>

Publishing effects from hiero during editorial publish is working as expected again.


___

</details>


<details>
<summary>Refactor code to handle missing "representations" key in instance data <a href="https://github.com/ynput/OpenPype/pull/6032">#6032</a></summary>

Minor code change for optimisation of thumbnail workflow.


___

</details>


<details>
<summary>Traypublisher: editorial preserve clip case sensitivity <a href="https://github.com/ynput/OpenPype/pull/6036">#6036</a></summary>

Keep EDL clip name inheritance with case sensitivity.


___

</details>


<details>
<summary>Bugfix/add missing houdini settings <a href="https://github.com/ynput/OpenPype/pull/6039">#6039</a></summary>

add missing settings. now, it looks like this:| Ayon | OpenPype || -- | -- | |  |  ||  |  |


___

</details>

### **🔀 Refactored code**


<details>
<summary>Maya: Remove RenderSetup layer observers <a href="https://github.com/ynput/OpenPype/pull/5836">#5836</a></summary>

Remove RenderSetup layer observers that are not needed since new publisher since Renderlayer Creators manage these themselves on Collect and Save/Update of instances.


___

</details>

### **Merged pull requests**


<details>
<summary>Tests: Removed render instance <a href="https://github.com/ynput/OpenPype/pull/6026">#6026</a></summary>

This test was created as simple model and workfile publish, without Deadline rendering. Cleaned up render elements.


___

</details>


<details>
<summary>Tests: update after thumbnail default change <a href="https://github.com/ynput/OpenPype/pull/6040">#6040</a></summary>

https://github.com/ynput/OpenPype/pull/5944 changed default state of integration of Thumbnails to NOT integrate. This PR updates automatic tests to follow that.


___

</details>


<details>
<summary>Houdini: Remove legacy LOPs USD output processors <a href="https://github.com/ynput/OpenPype/pull/5861">#5861</a></summary>

Remove unused/broken legacy code for Houdini Solaris USD LOPs output processors. The code was originally written in Avalon, against early Houdini 18 betas which had a different API for output processors and thus the current state doesn't even work in recent versions of Houdini.


___

</details>


<details>
<summary>Chore: Substance Painter Addons for Ayon <a href="https://github.com/ynput/OpenPype/pull/5914">#5914</a></summary>

Substance Painter Addons for Ayon 


___

</details>


<details>
<summary>Ayon: Updated name of Adobe extension to Ayon <a href="https://github.com/ynput/OpenPype/pull/5992">#5992</a></summary>

This changes name in menu in Adobe extensions to Ayon.


___

</details>


<details>
<summary>Chore/houdini update startup log <a href="https://github.com/ynput/OpenPype/pull/6003">#6003</a></summary>

print `Installing AYON ...` on startup when launching houdini from launcher in ayon mode.also update submenu to `ayon_menu` instead of `openpype_menu`


___

</details>


<details>
<summary>Revert "Ayon: Updated name of Adobe extension to Ayon" <a href="https://github.com/ynput/OpenPype/pull/6010">#6010</a></summary>

Reverts ynput/OpenPype#5992

That PR is only applicable to Ayon.
___

</details>


<details>
<summary>Standalone/Tray Publisher: Remove simple Unreal texture publishing <a href="https://github.com/ynput/OpenPype/pull/6012">#6012</a></summary>

We are removing _simple Unreal Texture publishing_ that was just renaming texture files to fit to Unreal naming conventions but without any additional functionality. We might return this functionality back with better texture publishing system.Related to #5983


___

</details>


<details>
<summary>Deadline: Bump version because of Settings changes for Deadline <a href="https://github.com/ynput/OpenPype/pull/6023">#6023</a></summary>


___

</details>


<details>
<summary>Change ASCII art in the Console based on the server mode <a href="https://github.com/ynput/OpenPype/pull/6030">#6030</a></summary>

This changes ASCII art in the console based on the AYON/OpenPype mode


___

</details>




## [3.17.6](https://github.com/ynput/OpenPype/tree/3.17.6)


[Full Changelog](https://github.com/ynput/OpenPype/compare/3.17.5...3.17.6)

### **🚀 Enhancements**


<details>
<summary>Testing: Validate Maya Logs <a href="https://github.com/ynput/OpenPype/pull/5775">#5775</a></summary>

This PR adds testing of the logs within Maya such as Python and Pyblish errors.The reason why we need to touch so many files outside of Maya is because of the pyblish errors below;
```
pyblish (ERROR) (line: 1371) pyblish.plugin:
Skipped: "collect_otio_frame_ranges" (No module named 'opentimelineio')
# Error: pyblish.plugin : Skipped: "collect_otio_frame_ranges" (No module named 'opentimelineio') #
pyblish (ERROR) (line: 1371) pyblish.plugin:
Skipped: "collect_otio_review" (No module named 'opentimelineio')
# Error: pyblish.plugin : Skipped: "collect_otio_review" (No module named 'opentimelineio') #
pyblish (ERROR) (line: 1371) pyblish.plugin:
Skipped: "collect_otio_subset_resources" (No module named 'opentimelineio')
# Error: pyblish.plugin : Skipped: "collect_otio_subset_resources" (No module named 'opentimelineio') #
pyblish (ERROR) (line: 1371) pyblish.plugin:
Skipped: "extract_otio_audio_tracks" (No module named 'opentimelineio')
# Error: pyblish.plugin : Skipped: "extract_otio_audio_tracks" (No module named 'opentimelineio') #
pyblish (ERROR) (line: 1371) pyblish.plugin:
Skipped: "extract_otio_file" (No module named 'opentimelineio')
# Error: pyblish.plugin : Skipped: "extract_otio_file" (No module named 'opentimelineio') #
pyblish (ERROR) (line: 1371) pyblish.plugin:
Skipped: "extract_otio_review" (No module named 'opentimelineio')
# Error: pyblish.plugin : Skipped: "extract_otio_review" (No module named 'opentimelineio') #
pyblish (ERROR) (line: 1371) pyblish.plugin:
Skipped: "extract_otio_trimming_video" (No module named 'opentimelineio')
# Error: pyblish.plugin : Skipped: "extract_otio_trimming_video" (No module named 'opentimelineio') #
pyblish (ERROR) (line: 1371) pyblish.plugin:
Skipped: "submit_blender_deadline" (No module named 'bpy')
# Error: pyblish.plugin : Skipped: "submit_blender_deadline" (No module named 'bpy') #
pyblish (ERROR) (line: 1371) pyblish.plugin:
Skipped: "submit_houdini_remote_publish" (No module named 'hou')
# Error: pyblish.plugin : Skipped: "submit_houdini_remote_publish" (No module named 'hou') #
pyblish (ERROR) (line: 1371) pyblish.plugin:
Skipped: "submit_houdini_render_deadline" (No module named 'hou')
# Error: pyblish.plugin : Skipped: "submit_houdini_render_deadline" (No module named 'hou') #
pyblish (ERROR) (line: 1371) pyblish.plugin:
Skipped: "submit_max_deadline" (No module named 'pymxs')
# Error: pyblish.plugin : Skipped: "submit_max_deadline" (No module named 'pymxs') #
pyblish (ERROR) (line: 1371) pyblish.plugin:
Skipped: "submit_nuke_deadline" (No module named 'nuke')
# Error: pyblish.plugin : Skipped: "submit_nuke_deadline" (No module named 'nuke') #
```
We also needed to `stdout` and `stderr` from the launched application to capture the output.Split from #5644.Dependent on #5734


___

</details>


<details>
<summary>Maya: Render Settings cleanup remove global `RENDER_ATTRS` <a href="https://github.com/ynput/OpenPype/pull/5801">#5801</a></summary>

Remove global `lib.RENDER_ATTRS` and implement a `RenderSettings.get_padding_attr(renderer)` method instead.


___

</details>


<details>
<summary>Testing: Ingest expected files and input workfile <a href="https://github.com/ynput/OpenPype/pull/5840">#5840</a></summary>

This ingests the Maya workfile from the Drive storage. Have changed the format to MayaAscii so its easier to see what changes are happening in a PR. This meant changing the expected files and database entries as well.


___

</details>


<details>
<summary>Chore: Create plugin auto-apply settings <a href="https://github.com/ynput/OpenPype/pull/5908">#5908</a></summary>

Create plugins can auto-apply settings.


___

</details>


<details>
<summary>Resolve: Add save current file button + "Save" shortcut when menu is active <a href="https://github.com/ynput/OpenPype/pull/5691">#5691</a></summary>

Adds a "Save current file" to the OpenPype menu.Also adds a "Save" shortcut key sequence (CTRL+S on Windows) to the button, so that clicking CTRL+S when the menu is active will save the current workfile. However this of course does not work if the menu does not receive the key press event (e.g. when Resolve UI is active instead)Resolves #5684


___

</details>


<details>
<summary>Reference USD file as maya native geometry <a href="https://github.com/ynput/OpenPype/pull/5781">#5781</a></summary>

Add MayaUsdReferenceLoader to reference USD as Maya native geometry using `mayaUSDImport` file translator.


___

</details>


<details>
<summary>Max: Bug fix on wrong aspect ratio and viewport not being maximized during context in review family <a href="https://github.com/ynput/OpenPype/pull/5839">#5839</a></summary>

This PR will fix the bug on wrong aspect ratio and viewport not being maximized when creating preview animationBesides, the support of tga image format and the options for AA quality are implemented in this PR


___

</details>


<details>
<summary>Blender: Incorporate blender "Collections" into Publish/Load <a href="https://github.com/ynput/OpenPype/pull/5841">#5841</a></summary>

Allow `blendScene` family to include collections.


___

</details>


<details>
<summary>Max: Allows user preset the setting of preview animation in OP/AYON Setting <a href="https://github.com/ynput/OpenPype/pull/5859">#5859</a></summary>

Allows user preset the setting of preview animation in OP/AYON Setting for review family.
- [x] Openpype
- [x] AYON


___

</details>


<details>
<summary>Publisher: Center publisher window on first show <a href="https://github.com/ynput/OpenPype/pull/5877">#5877</a></summary>

Move publisher window to center of a screen on first show.


___

</details>


<details>
<summary>Publisher: Instance context changes confirm works <a href="https://github.com/ynput/OpenPype/pull/5881">#5881</a></summary>

Confirmation of context changes in publisher on existing instances does not cause glitches.


___

</details>


<details>
<summary>AYON workfiles tools: Revisit workfiles tool <a href="https://github.com/ynput/OpenPype/pull/5897">#5897</a></summary>

Revisited workfiles tool for AYON mode to reuse common models and widgets.


___

</details>


<details>
<summary>Nuke: updated colorspace settings <a href="https://github.com/ynput/OpenPype/pull/5906">#5906</a></summary>

Updating nuke colorspace settings into more convenient way with usage of ocio config roles rather then particular colorspace names. This way we should not have troubles to switch between linear Rec709 or ACES configs without any additional settings changes.


___

</details>


<details>
<summary>Blender: Refactor to new publisher <a href="https://github.com/ynput/OpenPype/pull/5910">#5910</a></summary>

Refactor Blender integration to use the new publisher


___

</details>


<details>
<summary>Enhancement: Some publish logs cosmetics <a href="https://github.com/ynput/OpenPype/pull/5917">#5917</a></summary>

General logging message tweaks:
- Sort some lists of folder/filenames so they appear sorted in the logs
- Fix some grammar / typos
- In some cases provide slightly more information in a log


___

</details>


<details>
<summary>Blender: Better name of 'asset_name' function <a href="https://github.com/ynput/OpenPype/pull/5927">#5927</a></summary>

Renamed function `asset_name` to `prepare_scene_name`.


___

</details>

### **🐛 Bug fixes**


<details>
<summary>Maya: Bug fix the fbx animation export errored out when the skeletonAnim set is empty <a href="https://github.com/ynput/OpenPype/pull/5875">#5875</a></summary>

Resolve this bug discordIf the skeletonAnim SET is empty and fbx animation collect, the fbx animation extractor would skip the fbx extraction


___

</details>


<details>
<summary>Bugfix: fix few typos in houdini's and Maya's Ayon settings <a href="https://github.com/ynput/OpenPype/pull/5882">#5882</a></summary>

Fixing few typos
- [x] Maya unreal static mesh
- [x] Houdini static mesh
- [x] Houdini collect asset handles


___

</details>


<details>
<summary>Bugfix: Ayon Deadline env vars + error message on no executable found <a href="https://github.com/ynput/OpenPype/pull/5815">#5815</a></summary>

Fix some Ayon x Deadline issues as came up in this topic:
- missing Environment Variables issue explained here for `deadlinePlugin.RunProcess` for the AYON _extract environments_ call.
- wrong error formatting described here with a `;` between each character like this: `Ayon executable was not found in the semicolon separated list "C;:;/;P;r;o;g;r;a;m; ;F;i;l;e;s;/;Y;n;p;u;t;/;A;Y;O;N; ;1;.;0;.;0;-;b;e;t;a;.;5;/;a;y;o;n;_;c;o;n;s;o;l;e;.;e;x;e". The path to the render executable can be configured from the Plugin Configuration in the Deadline Monitor.`


___

</details>


<details>
<summary>AYON: Fix bundles access in settings <a href="https://github.com/ynput/OpenPype/pull/5856">#5856</a></summary>

Fixed access to bundles data in settings to define correct develop variant.


___

</details>


<details>
<summary>AYON 3dsMax settings: 'ValidateAttributes' settings converte only if available <a href="https://github.com/ynput/OpenPype/pull/5878">#5878</a></summary>

Convert `ValidateAttributes` settings only if are available in AYON settings.


___

</details>


<details>
<summary>AYON: Fix TrayPublisher editorial settings <a href="https://github.com/ynput/OpenPype/pull/5880">#5880</a></summary>

Fixing Traypublisher settings for adding task in simple editorial.


___

</details>


<details>
<summary>TrayPublisher: editorial frame range check not needed <a href="https://github.com/ynput/OpenPype/pull/5884">#5884</a></summary>

Validator for frame ranges is not needed during editorial publishing since entity data are not yet in database.


___

</details>


<details>
<summary>Update houdini license validator <a href="https://github.com/ynput/OpenPype/pull/5886">#5886</a></summary>

As reported in this community commentHoudini USD publishing is only restricted in Houdini apprentice.


___

</details>


<details>
<summary>Blender: Fix blend extraction and packed images <a href="https://github.com/ynput/OpenPype/pull/5888">#5888</a></summary>

Fixed a with blend extractor and packed images.


___

</details>


<details>
<summary>AYON: Initialize connection with all information <a href="https://github.com/ynput/OpenPype/pull/5890">#5890</a></summary>

Create global AYON api connection with all informations all the time.


___

</details>


<details>
<summary>AYON: Scene inventory tool without site sync <a href="https://github.com/ynput/OpenPype/pull/5896">#5896</a></summary>

Skip 'get_site_icons' if site sync addon is disabled.


___

</details>


<details>
<summary>Publish report tool: Fix PySide6 <a href="https://github.com/ynput/OpenPype/pull/5898">#5898</a></summary>

Use constants from classes instead of objects.


___

</details>


<details>
<summary>fusion: removing hardcoded template name for saver <a href="https://github.com/ynput/OpenPype/pull/5907">#5907</a></summary>

Fusion is not hardcoded for `render` anatomy template only anymore. This was blocking AYON deployment.


___

</details>




## [3.17.5](https://github.com/ynput/OpenPype/tree/3.17.5)


[Full Changelog](https://github.com/ynput/OpenPype/compare/3.17.4...3.17.5)

### **🆕 New features**


<details>
<summary>Fusion: Add USD loader <a href="https://github.com/ynput/OpenPype/pull/4896">#4896</a></summary>

Add an OpenPype managed USD loader (`uLoader`) for Fusion.


___

</details>


<details>
<summary>Fusion: Resolution validator <a href="https://github.com/ynput/OpenPype/pull/5325">#5325</a></summary>

Added a resolution validator.The code is from my old PR (https://github.com/ynput/OpenPype/pull/4921) that I closed because the PR also contained a frame range validator that no longer is needed.


___

</details>


<details>
<summary>Context Selection tool: Refactor Context tool (for AYON) <a href="https://github.com/ynput/OpenPype/pull/5766">#5766</a></summary>

Context selection tool has AYON variant.


___

</details>


<details>
<summary>AYON: Use AYON username for user in template data <a href="https://github.com/ynput/OpenPype/pull/5842">#5842</a></summary>

Use ayon username for template data in AYON mode.


___

</details>


<details>
<summary>Testing: app_group flag <a href="https://github.com/ynput/OpenPype/pull/5869">#5869</a></summary>

`app_group` command flag. This is for changing which flavour of the host to launch. In the case of Maya, you can launch Maya and MayaPy, but it can be used for the Nuke family as well.Split from #5644


___

</details>

### **🚀 Enhancements**


<details>
<summary>Enhancement: Fusion fix saver creation + minor Blender/Fusion logging tweaks <a href="https://github.com/ynput/OpenPype/pull/5558">#5558</a></summary>

- Blender change logs to `debug` level in preparation for new publisher artist facing reports (note that it currently still uses the old publisher)
- Fusion: Create Saver fix redeclaration of default_variants
- Fusion: Fix saver being created in incorrect state without saving directly after create
- Fusion: Allow reset frame range on render family
- Fusion: Tweak logging level for artist-facing report


___

</details>


<details>
<summary>Resolve: load clip to timeline at set time <a href="https://github.com/ynput/OpenPype/pull/5665">#5665</a></summary>

It is possible to load clip to correct place on timeline.


___

</details>


<details>
<summary>Nuke: Optional Deadline workfile dependency. <a href="https://github.com/ynput/OpenPype/pull/5732">#5732</a></summary>

Adds option to add the workfile as dependency for the Deadline job.Think it used to have something like this, but it disappeared. Usecase is for remote workflow where the Nuke script needs to be synced before the job can start.


___

</details>


<details>
<summary>Enhancement/houdini rearrange ayon houdini settings files <a href="https://github.com/ynput/OpenPype/pull/5748">#5748</a></summary>

Rearranging Houdini Settings to be more readable, easier to edit, update settings (include all families/product types)This PR is mainly for Ayon Settings to have more organized files. For Openpype, I'll make sure that  each Houdini setting in Ayon has an equivalent in Openpype.
- [x] update Ayon settings, fix typos and remove deprecated settings.
- [x] Sync with Openpype
- [x] Test in Openpype
- [x] Test in Ayon


___

</details>


<details>
<summary>Chore: updating create ayon addon script <a href="https://github.com/ynput/OpenPype/pull/5822">#5822</a></summary>

Adding developers environment options.


___

</details>


<details>
<summary>Max: Implement Validator for Properties/Attributes Value Check <a href="https://github.com/ynput/OpenPype/pull/5824">#5824</a></summary>

Add optional validator which can check if the property attributes are valid in Max


___

</details>


<details>
<summary>Nuke: Remove unused 'get_render_path' function <a href="https://github.com/ynput/OpenPype/pull/5826">#5826</a></summary>

Remove unused function `get_render_path` from nuke integration.


___

</details>


<details>
<summary>Chore: Limit current context template data function <a href="https://github.com/ynput/OpenPype/pull/5845">#5845</a></summary>

Current implementation of `get_current_context_template_data` does return the same values as base template data function `get_template_data`.


___

</details>


<details>
<summary>Max: Make sure Collect Render not ignoring instance asset <a href="https://github.com/ynput/OpenPype/pull/5847">#5847</a></summary>

- Make sure Collect Render is not always using asset from context.
- Make sure Scene version being collected
- Clean up unnecessary uses of code in the collector.


___

</details>


<details>
<summary>Ftrack: Events are not processed if project is not available in OpenPype <a href="https://github.com/ynput/OpenPype/pull/5853">#5853</a></summary>

Events that happened on project which is not in OpenPype is not processed.


___

</details>


<details>
<summary>Nuke: Add Nuke 11.0 as default setting <a href="https://github.com/ynput/OpenPype/pull/5855">#5855</a></summary>

Found I needed Nuke 11.0 in the default settings to help with unit testing.


___

</details>


<details>
<summary>TVPaint: Code cleanup <a href="https://github.com/ynput/OpenPype/pull/5857">#5857</a></summary>

Removed unused import. Use `AYON` label in ayon mode. Removed unused data in publish context `"previous_context"`.


___

</details>


<details>
<summary>AYON settings: Use correct label for follow workfile version <a href="https://github.com/ynput/OpenPype/pull/5874">#5874</a></summary>

Follow workfile version label was marked as Collect Anatomy Instance Data label.


___

</details>

### **🐛 Bug fixes**


<details>
<summary>Nuke: Fix workfile template builder so representations get loaded next to each other <a href="https://github.com/ynput/OpenPype/pull/5061">#5061</a></summary>

Refactor when the cleanup of the placeholder happens for the cases where multiple representations are loaded by a single placeholder.The existing code didn't take into account the case where a template placeholder can load multiple representations so it was trying to do the cleanup of the placeholder node and the re-arrangement of the imported nodes too early. I assume this was designed only for the cases where a single representation can load multiple nodes.


___

</details>


<details>
<summary>Nuke: Dont update node name on update <a href="https://github.com/ynput/OpenPype/pull/5704">#5704</a></summary>

When updating `Image` containers the code is trying to set the name of the node. This results in a warning message from Nuke shown below;Suggesting to not change the node name when updating.


___

</details>


<details>
<summary>UIDefLabel can be unique <a href="https://github.com/ynput/OpenPype/pull/5827">#5827</a></summary>

`UILabelDef` have implemented comparison and uniqueness.


___

</details>


<details>
<summary>AYON: Skip kitsu module when creating ayon addons <a href="https://github.com/ynput/OpenPype/pull/5828">#5828</a></summary>

Create AYON packages is skipping kitsu module in creation of modules/addons and kitsu module is not loaded from modules on start. The addon already has it's repository https://github.com/ynput/ayon-kitsu.


___

</details>


<details>
<summary>Bugfix: Collect Rendered Files only collecting first instance <a href="https://github.com/ynput/OpenPype/pull/5832">#5832</a></summary>

Collect all instances from the metadata file - don't return on first instance iteration.


___

</details>


<details>
<summary>Houdini: set frame range for the created composite ROP <a href="https://github.com/ynput/OpenPype/pull/5833">#5833</a></summary>

Quick bug fix for created composite ROP, set its frame range to the frame range of the playbar.


___

</details>


<details>
<summary>Fix registering launcher actions from OpenPypeModules <a href="https://github.com/ynput/OpenPype/pull/5843">#5843</a></summary>

Fix typo `actions_dir` -> `path` to fix register launcher actions fromm OpenPypeModule


___

</details>


<details>
<summary>Bugfix in houdini shelves manager and beautify settings  <a href="https://github.com/ynput/OpenPype/pull/5844">#5844</a></summary>

This PR fixes the problem in this PR https://github.com/ynput/OpenPype/issues/5457 by using the right function to load a pre-made houdini `.shelf` fileAlso, it beautifies houdini shelves settings to provide better guidance for users which helps with other issue https://github.com/ynput/OpenPype/issues/5458 , Rather adding default shelf and set names, I'll educate users how to use the tool correctly.Users now are able to select between the two options.| OpenPype | Ayon || -- | -- ||  |  |


___

</details>


<details>
<summary>Blender: Fix missing Grease Pencils in review <a href="https://github.com/ynput/OpenPype/pull/5848">#5848</a></summary>

Fix Grease Pencil missing in review when isolating objects.


___

</details>


<details>
<summary>Blender: Fix Render Settings in Ayon <a href="https://github.com/ynput/OpenPype/pull/5849">#5849</a></summary>

Fix Render Settings in Ayon for Blender.


___

</details>


<details>
<summary>Bugfix: houdini tab menu working as expected <a href="https://github.com/ynput/OpenPype/pull/5850">#5850</a></summary>

This PR:Tab menu name changes to Ayon when using ayon get_network_categories is checked in all creator plugins.  | Product | Network Category |  | -- | -- |  | Alembic camera | rop, obj | | Arnold Ass | rop | | Arnold ROP | rop | | Bgeo | rop, sop | | composite sequence | cop2, rop | | hda | obj | | Karma ROP | rop | | Mantra ROP | rop | | ABC | rop, sop | | RS proxy | rop, sop|  | RS ROP | rop | | Review | rop | | Static mesh | rop, obj, sop | | USD | lop, rop | | USD Render | rop | | VDB | rop, obj, sop | | V Ray | rop |


___

</details>


<details>
<summary>Bigfix: Houdini skip frame_range_validator if node has no 'trange' parameter <a href="https://github.com/ynput/OpenPype/pull/5851">#5851</a></summary>

I faced a bug when publishing HDA instance as it has no `trange` parameter. As this PR title says : skip  frame_range_validator  if node has no 'trange' parameter


___

</details>


<details>
<summary>Bugfix: houdini image sequence loading and missing frames <a href="https://github.com/ynput/OpenPype/pull/5852">#5852</a></summary>

I made this PR in to fix issues mentioned here https://github.com/ynput/OpenPype/pull/5833#issuecomment-1789207727in short:
- image load doesn't work
- publisher only publish one frame


___

</details>


<details>
<summary>Nuke: loaders' containers updating as nodes <a href="https://github.com/ynput/OpenPype/pull/5854">#5854</a></summary>

Nuke loaded containers are updating correctly even they have been duplicating of originally loaded nodes. This had previously been removed duplicated nodes.


___

</details>


<details>
<summary>deadline: settings are not blocking extension input <a href="https://github.com/ynput/OpenPype/pull/5864">#5864</a></summary>

Settings are not blocking user input.


___

</details>


<details>
<summary>Blender: Fix loading of blend layouts <a href="https://github.com/ynput/OpenPype/pull/5866">#5866</a></summary>

Fix a problem with loading blend layouts.


___

</details>


<details>
<summary>AYON: Launcher refresh issues <a href="https://github.com/ynput/OpenPype/pull/5867">#5867</a></summary>

Fixed refresh of projects issue in launcher tool. And renamed Qt models to contain `Qt` in their name (it was really hard to find out where were used). It is not possible to click on disabled item in launcher's projects view.


___

</details>


<details>
<summary>Fix the Wrong key words for tycache workfile template settings in AYON <a href="https://github.com/ynput/OpenPype/pull/5870">#5870</a></summary>

Fix the wrong key words for the tycache workfile template settings in AYON(i.e. Instead of families, product_types should be used)


___

</details>


<details>
<summary>AYON tools: Handle empty icon definition <a href="https://github.com/ynput/OpenPype/pull/5876">#5876</a></summary>

Ignore if passed icon definition is `None`.


___

</details>

### **🔀 Refactored code**


<details>
<summary>Houdini: Remove on instance toggled callback <a href="https://github.com/ynput/OpenPype/pull/5860">#5860</a></summary>

Remove on instance toggled callback which isn't relevant to the new publisher


___

</details>


<details>
<summary>Chore: Remove unused `instanceToggled` callbacks <a href="https://github.com/ynput/OpenPype/pull/5862">#5862</a></summary>

The `instanceToggled` callbacks should be irrelevant for new publisher.


___

</details>




## [3.17.4](https://github.com/ynput/OpenPype/tree/3.17.4)


[Full Changelog](https://github.com/ynput/OpenPype/compare/3.17.3...3.17.4)

### **🆕 New features**


<details>
<summary>Add Support for Husk-AYON Integration <a href="https://github.com/ynput/OpenPype/pull/5816">#5816</a></summary>

This draft pull request introduces support for integrating Husk with AYON within the OpenPype repository.


___

</details>


<details>
<summary>Push to project tool: Prepare push to project tool for AYON <a href="https://github.com/ynput/OpenPype/pull/5770">#5770</a></summary>

Cloned Push to project tool for AYON and modified it.


___

</details>

### **🚀 Enhancements**


<details>
<summary>Max: tycache family support <a href="https://github.com/ynput/OpenPype/pull/5624">#5624</a></summary>

Tycache family supports for Tyflow Plugin in Max


___

</details>


<details>
<summary>Unreal: Changed behaviour for updating assets <a href="https://github.com/ynput/OpenPype/pull/5670">#5670</a></summary>

Changed how assets are updated in Unreal.


___

</details>


<details>
<summary>Unreal: Improved error reporting for Sequence Frame Validator <a href="https://github.com/ynput/OpenPype/pull/5730">#5730</a></summary>

Improved error reporting for Sequence Frame Validator.


___

</details>


<details>
<summary>Max: Setting tweaks on Review Family <a href="https://github.com/ynput/OpenPype/pull/5744">#5744</a></summary>

- Bug fix of not being able to publish the preferred visual style when creating preview animation
- Exposes the parameters after creating instance
- Add the Quality settings and viewport texture settings for preview animation
- add use selection for create review


___

</details>


<details>
<summary>Max: Add families with frame range extractions back to the frame range validator <a href="https://github.com/ynput/OpenPype/pull/5757">#5757</a></summary>

In 3dsMax, there are some instances which exports the files in frame range but not being added to the optional frame range validator. In this PR, these instances would have the optional frame range validators to allow users to check if frame range aligns with the context data from DB.The following families have been added to have optional frame range validator:
- maxrender
- review
- camera
- redshift proxy
- pointcache
- point cloud(tyFlow PRT)


___

</details>


<details>
<summary>TimersManager: Use available data to get context info <a href="https://github.com/ynput/OpenPype/pull/5804">#5804</a></summary>

Get context information from pyblish context data instead of using `legacy_io`.


___

</details>


<details>
<summary>Chore: Removed unused variable from `AbstractCollectRender` <a href="https://github.com/ynput/OpenPype/pull/5805">#5805</a></summary>

Removed unused `_asset` variable from `RenderInstance`.


___

</details>

### **🐛 Bug fixes**


<details>
<summary>Bugfix/houdini:  wrong frame calculation with handles <a href="https://github.com/ynput/OpenPype/pull/5698">#5698</a></summary>

This PR make collect plugins to consider `handleStart` and `handleEnd` when collecting frame range it affects three parts:
- get frame range in collect plugins
- expected file in render plugins
- submit houdini job deadline plugin


___

</details>


<details>
<summary>Nuke: ayon server settings improvements <a href="https://github.com/ynput/OpenPype/pull/5746">#5746</a></summary>

Nuke settings were not aligned with OpenPype settings. Also labels needed to be improved.


___

</details>


<details>
<summary>Blender: Fix pointcache family and fix alembic extractor <a href="https://github.com/ynput/OpenPype/pull/5747">#5747</a></summary>

Fixed `pointcache` family and fixed behaviour of the alembic extractor.


___

</details>


<details>
<summary>AYON: Remove 'shotgun_api3' from dependencies <a href="https://github.com/ynput/OpenPype/pull/5803">#5803</a></summary>

Removed `shotgun_api3` dependency from openpype dependencies for AYON launcher. The dependency is already defined in shotgrid addon and change of version causes clashes.


___

</details>


<details>
<summary>Chore: Fix typo in filename <a href="https://github.com/ynput/OpenPype/pull/5807">#5807</a></summary>

Move content of `contants.py` into `constants.py`.


___

</details>


<details>
<summary>Chore: Create context respects instance changes <a href="https://github.com/ynput/OpenPype/pull/5809">#5809</a></summary>

Fix issue with unrespected change propagation in `CreateContext`. All successfully saved instances are marked as saved so they have no changes. Origin data of an instance are explicitly not handled directly by the object but by the attribute wrappers.


___

</details>


<details>
<summary>Blender: Fix tools handling in AYON mode <a href="https://github.com/ynput/OpenPype/pull/5811">#5811</a></summary>

Skip logic in `before_window_show` in blender when in AYON mode. Most of the stuff called there happes on show automatically.


___

</details>


<details>
<summary>Blender: Include Grease Pencil in review and thumbnails <a href="https://github.com/ynput/OpenPype/pull/5812">#5812</a></summary>

Include Grease Pencil in review and thumbnails.


___

</details>


<details>
<summary>Workfiles tool AYON: Fix double click of workfile <a href="https://github.com/ynput/OpenPype/pull/5813">#5813</a></summary>

Fix double click on workfiles in workfiles tool to open the file.


___

</details>


<details>
<summary>Webpublisher: removal of usage of no_of_frames in error message <a href="https://github.com/ynput/OpenPype/pull/5819">#5819</a></summary>

If it throws exception, `no_of_frames` value  wont be available, so it doesn't make sense to log it.


___

</details>


<details>
<summary>Attribute Defs: Hide multivalue widget in Number by default <a href="https://github.com/ynput/OpenPype/pull/5821">#5821</a></summary>

Fixed default look of `NumberAttrWidget` by hiding its multiselection widget.


___

</details>

### **Merged pull requests**


<details>
<summary>Corrected a typo in Readme.md (Top -> To) <a href="https://github.com/ynput/OpenPype/pull/5800">#5800</a></summary>


___

</details>


<details>
<summary>Photoshop: Removed redundant copy of extension.zxp <a href="https://github.com/ynput/OpenPype/pull/5802">#5802</a></summary>

`extension.zxp` shouldn't be inside of extension folder.


___

</details>




## [3.17.3](https://github.com/ynput/OpenPype/tree/3.17.3)


[Full Changelog](https://github.com/ynput/OpenPype/compare/3.17.2...3.17.3)

### **🆕 New features**


<details>
<summary>Maya: Multi-shot Layout Creator <a href="https://github.com/ynput/OpenPype/pull/5710">#5710</a></summary>

New Multi-shot Layout creator is a way of automating creation of the new Layout instances in Maya, associated with correct shots, frame ranges and Camera Sequencer in Maya.


___

</details>


<details>
<summary>Colorspace: ociolook file product type workflow <a href="https://github.com/ynput/OpenPype/pull/5541">#5541</a></summary>

Traypublisher support for publishing of colorspace look files (ociolook) which are json files holding any LUT files. This new product is available for loading in Nuke host at the moment.Added colorspace selector to publisher attribute with better labeling. We are supporting also Roles and Alias (only v2 configs).


___

</details>


<details>
<summary>Scene Inventory tool: Refactor Scene Inventory tool (for AYON) <a href="https://github.com/ynput/OpenPype/pull/5758">#5758</a></summary>

Modified scene inventory tool for AYON. The main difference is in how project name is defined and replacement of assets combobox with folders dialog.


___

</details>


<details>
<summary>AYON: Support dev bundles <a href="https://github.com/ynput/OpenPype/pull/5783">#5783</a></summary>

Modules can be loaded in AYON dev mode from different location.


___

</details>

### **🚀 Enhancements**


<details>
<summary>Testing: Ingest Maya userSetup <a href="https://github.com/ynput/OpenPype/pull/5734">#5734</a></summary>

Suggesting to ingest `userSetup.py` startup script for easier collaboration and transparency of testing.


___

</details>


<details>
<summary>Fusion: Work with pathmaps <a href="https://github.com/ynput/OpenPype/pull/5329">#5329</a></summary>

Path maps are a big part of our Fusion workflow. We map the project folder to a path map within Fusion so all loaders and savers point to the path map variable. This way any computer on any OS can open any comp no matter where the project folder is located.


___

</details>


<details>
<summary>Maya: Add Maya 2024 and remove pre 2022. <a href="https://github.com/ynput/OpenPype/pull/5674">#5674</a></summary>

Adding Maya 2024 as default application variant.Removing Maya 2020 and older, as these are not supported anymore.


___

</details>


<details>
<summary>Enhancement: Houdini: Allow using template keys in Houdini shelves manager <a href="https://github.com/ynput/OpenPype/pull/5727">#5727</a></summary>

Allow using Template keys in Houdini shelves manager.


___

</details>


<details>
<summary>Houdini: Fix Show in usdview loader action <a href="https://github.com/ynput/OpenPype/pull/5737">#5737</a></summary>

Fix the "Show in USD View" loader to show up in Houdini


___

</details>


<details>
<summary>Nuke: validator of asset context with repair actions <a href="https://github.com/ynput/OpenPype/pull/5749">#5749</a></summary>

Instance nodes with different context of asset and task can be now validated and repaired via repair action.


___

</details>


<details>
<summary>AYON: Tools enhancements <a href="https://github.com/ynput/OpenPype/pull/5753">#5753</a></summary>

Few enhancements and tweaks of AYON related tools.


___

</details>


<details>
<summary>Max: Tweaks on ValidateMaxContents <a href="https://github.com/ynput/OpenPype/pull/5759">#5759</a></summary>

This PR provides enhancements on ValidateMaxContent as follow:
- Rename `ValidateMaxContents` to `ValidateContainers`
- Add related families which are required to pass the validation(All families except `Render` as the render instance is the one which only allows empty container)


___

</details>


<details>
<summary>Enhancement: Nuke refactor `SelectInvalidAction` <a href="https://github.com/ynput/OpenPype/pull/5762">#5762</a></summary>

Refactor `SelectInvalidAction` to behave like other action for other host, create `SelectInstanceNodeAction` as dedicated action to select the instance node for a failed plugin.
- Note: Selecting Instance Node will still select the instance node even if the user has currently 'fixed' the problem.


___

</details>


<details>
<summary>Enhancement: Tweak logging for Nuke for artist facing reports <a href="https://github.com/ynput/OpenPype/pull/5763">#5763</a></summary>

Tweak logs that are not artist-facing to debug level + in some cases clarify what the logged value is.


___

</details>


<details>
<summary>AYON Settings: Disk mapping <a href="https://github.com/ynput/OpenPype/pull/5786">#5786</a></summary>

Added disk mapping settings to core addon settings.


___

</details>

### **🐛 Bug fixes**


<details>
<summary>Maya: add colorspace argument to redshiftTextureProcessor <a href="https://github.com/ynput/OpenPype/pull/5645">#5645</a></summary>

In color managed Maya, texture processing during Look Extraction wasn't passing texture colorspaces set on textures to `redshiftTextureProcessor` tool. This in effect caused this tool to produce non-zero exit code (even though the texture was converted into wrong colorspace) and therefor crash of the extractor. This PR is passing colorspace to that tool if color management is enabled.


___

</details>


<details>
<summary>Maya: don't call `cmds.ogs()` in headless mode <a href="https://github.com/ynput/OpenPype/pull/5769">#5769</a></summary>

`cmds.ogs()` is a call that will crash if Maya is running in headless mode (mayabatch, mayapy). This is handling that case.


___

</details>


<details>
<summary>Resolve: inventory management fix <a href="https://github.com/ynput/OpenPype/pull/5673">#5673</a></summary>

Loaded Timeline item containers are now updating correctly and version management is working as it suppose to.
- [x] updating loaded timeline items
- [x] Removing of loaded timeline items


___

</details>


<details>
<summary>Blender: Remove 'update_hierarchy' <a href="https://github.com/ynput/OpenPype/pull/5756">#5756</a></summary>

Remove `update_hierarchy` function which is causing crashes in scene inventory tool.


___

</details>


<details>
<summary>Max: bug fix on the settings in pointcloud family <a href="https://github.com/ynput/OpenPype/pull/5768">#5768</a></summary>

Bug fix on the settings being errored out in validate point cloud(see links:https://github.com/ynput/OpenPype/pull/5759#pullrequestreview-1676681705) and passibly in point cloud extractor.


___

</details>


<details>
<summary>AYON settings: Fix default factory of tools <a href="https://github.com/ynput/OpenPype/pull/5773">#5773</a></summary>

Fix default factory of application tools.


___

</details>


<details>
<summary>Fusion: added missing OPENPYPE_VERSION <a href="https://github.com/ynput/OpenPype/pull/5776">#5776</a></summary>

Fusion submission to Deadline was missing OPENPYPE_VERSION env var when submitting from build (not source code directly). This missing env var might break rendering on DL if path to OP executable (openpype_console.exe) is not set explicitly and might cause an issue when different versions of OP are deployed.This PR adds this environment variable.


___

</details>


<details>
<summary>Ftrack: Skip tasks when looking for asset equivalent entity <a href="https://github.com/ynput/OpenPype/pull/5777">#5777</a></summary>

Skip tasks when looking for asset equivalent entity.


___

</details>


<details>
<summary>Nuke: loading gizmos fixes <a href="https://github.com/ynput/OpenPype/pull/5779">#5779</a></summary>

Gizmo product is not offered in Loader as plugin. It is also updating as expected.


___

</details>


<details>
<summary>General: thumbnail extractor as last extractor <a href="https://github.com/ynput/OpenPype/pull/5780">#5780</a></summary>

Fixing issue with the order of the `ExtractOIIOTranscode` and `ExtractThumbnail` plugins. The problem was that the `ExtractThumbnail` plugin was processed before the `ExtractOIIOTranscode` plugin. As a result, the `ExtractThumbnail` plugin did not inherit the `review` tag into the representation data. This caused the `ExtractThumbnail` plugin to fail in processing and creating thumbnails.


___

</details>


<details>
<summary>Bug: fix key in application json <a href="https://github.com/ynput/OpenPype/pull/5787">#5787</a></summary>

In PR #5705 `maya` was wrongly used instead of `mayapy`, breaking AYON defaults in AYON Application Addon.


___

</details>


<details>
<summary>'NumberAttrWidget' shows 'Multiselection' label on multiselection <a href="https://github.com/ynput/OpenPype/pull/5792">#5792</a></summary>

Attribute definition widget 'NumberAttrWidget' shows `< Multiselection >`  label on multiselection.


___

</details>


<details>
<summary>Publisher: Selection change by enabled checkbox on instance update attributes <a href="https://github.com/ynput/OpenPype/pull/5793">#5793</a></summary>

Change of instance by clicking on enabled checkbox will actually update attributes on right side to match the selection.


___

</details>


<details>
<summary>Houdini: Remove `setParms` call since it's responsibility of `self.imprint` to set the values <a href="https://github.com/ynput/OpenPype/pull/5796">#5796</a></summary>

Revert a recent change made in #5621 due to this comment. However the change is faulty as can be seen mentioned here


___

</details>


<details>
<summary>AYON loader: Fix SubsetLoader functionality <a href="https://github.com/ynput/OpenPype/pull/5799">#5799</a></summary>

Fix SubsetLoader plugin processing in AYON loader tool.


___

</details>

### **Merged pull requests**


<details>
<summary>Houdini: Add self publish button <a href="https://github.com/ynput/OpenPype/pull/5621">#5621</a></summary>

This PR allows single publishing by adding a publish button to created rop nodes in HoudiniAdmins are much welcomed to enable it from houdini general settingsPublish Button also includes all input publish instances. in this screen shot the alembic instance is ignored because the switch is turned off


___

</details>


<details>
<summary>Nuke: fixing UNC support for OCIO path <a href="https://github.com/ynput/OpenPype/pull/5771">#5771</a></summary>

UNC paths were broken on windows for custom OCIO path and this is solving the issue with removed double slash at start of path


___

</details>




## [3.17.2](https://github.com/ynput/OpenPype/tree/3.17.2)


[Full Changelog](https://github.com/ynput/OpenPype/compare/3.17.1...3.17.2)

### **🆕 New features**


<details>
<summary>Maya: Add MayaPy application. <a href="https://github.com/ynput/OpenPype/pull/5705">#5705</a></summary>

This adds mayapy to the application to be launched from a task.


___

</details>


<details>
<summary>Feature: Copy resources when downloading last workfile <a href="https://github.com/ynput/OpenPype/pull/4944">#4944</a></summary>

When the last published workfile is downloaded as a prelaunch hook, all resource files referenced in the workfile representation are copied to the `resources` folder, which is inside the local workfile folder.


___

</details>


<details>
<summary>Blender: Deadline support <a href="https://github.com/ynput/OpenPype/pull/5438">#5438</a></summary>

Add Deadline support for Blender.


___

</details>


<details>
<summary>Fusion: implement toggle to use Deadline plugin FusionCmd <a href="https://github.com/ynput/OpenPype/pull/5678">#5678</a></summary>

Fusion 17 doesn't work in DL 10.3, but FusionCmd does. It might be probably better option as headless variant.Fusion plugin seems to be closing and reopening application when worker is running on artist machine, not so with FusionCmdAdded configuration to Project Settings for admin to select appropriate Deadline plugin:


___

</details>


<details>
<summary>Loader tool: Refactor loader tool (for AYON) <a href="https://github.com/ynput/OpenPype/pull/5729">#5729</a></summary>

Refactored loader tool to new tool. Separated backend and frontend logic. Refactored logic is AYON-centric and is used only in AYON mode, so it does not affect OpenPype. The tool is also replacing library loader.


___

</details>

### **🚀 Enhancements**


<details>
<summary>Maya: implement matchmove publishing <a href="https://github.com/ynput/OpenPype/pull/5445">#5445</a></summary>

Add possibility to export multiple cameras in single `matchmove` family instance, both in `abc` and `ma`.Exposed flag 'Keep image planes' to control export of image planes.


___

</details>


<details>
<summary>Maya: Add optional Fbx extractors in Rig and Animation family <a href="https://github.com/ynput/OpenPype/pull/5589">#5589</a></summary>

This PR allows user to export control rigs(optionally with mesh) and animated rig in fbx optionally by attaching the rig objects to the two newly introduced sets.


___

</details>


<details>
<summary>Maya: Optional Resolution Validator for Render <a href="https://github.com/ynput/OpenPype/pull/5693">#5693</a></summary>

Adding optional resolution validator for maya in render family, similar to the one in Max.It checks if the resolution in render setting aligns with that in setting from the db.


___

</details>


<details>
<summary>Use host's node uniqueness for instance id in new publisher <a href="https://github.com/ynput/OpenPype/pull/5490">#5490</a></summary>

Instead of writing `instance_id` as parm or attributes on the publish instances we can, for some hosts, just rely on a unique name or path within the scene to refer to that particular instance. By doing so we fix #4820 because upon duplicating such a publish instance using the host's (DCC) functionality the uniqueness for the duplicate is then already ensured instead of attributes remaining exact same value as where to were duplicated from, making `instance_id` a non-unique value.


___

</details>


<details>
<summary>Max: Implementation of OCIO configuration  <a href="https://github.com/ynput/OpenPype/pull/5499">#5499</a></summary>

Resolve #5473 Implementation of OCIO configuration for Max 2024 regarding to the update of Max 2024


___

</details>


<details>
<summary>Nuke: Multiple format supports for ExtractReviewDataMov <a href="https://github.com/ynput/OpenPype/pull/5623">#5623</a></summary>

This PR would fix the bug of  the plugin `ExtractReviewDataMov` not being able to support extensions other than `mov`. The plugin is also renamed to `ExtractReviewDataBakingStreams` as i provides multiple format supoort.


___

</details>


<details>
<summary>Bugfix: houdini switching context doesnt update variables <a href="https://github.com/ynput/OpenPype/pull/5651">#5651</a></summary>

Allows admins to have a list of vars (e.g. JOB) with (dynamic) values that will be updated on context changes, e.g. when switching to another asset or task.Using template keys is supported but formatting keys capitalization variants is not, e.g. {Asset} and {ASSET} won't workDisabling Update Houdini vars on context change feature will leave all Houdini vars unmanaged and thus no context update changes will occur.Also, this PR adds a new button in menu to update vars on demand. 


___

</details>


<details>
<summary>Publisher: Fix report maker memory leak + optimize lookups using set <a href="https://github.com/ynput/OpenPype/pull/5667">#5667</a></summary>

Fixes a memory leak where resetting publisher does not clear the stored plugins for the Publish Report Maker.Also changes the stored plugins to a `set` to optimize the lookup speeds.


___

</details>


<details>
<summary>Add openpype_mongo command flag for testing. <a href="https://github.com/ynput/OpenPype/pull/5676">#5676</a></summary>

Instead of changing the environment, this command flag allows for changing the database.


___

</details>


<details>
<summary>Nuke: minor docstring and code tweaks for ExtractReviewMov <a href="https://github.com/ynput/OpenPype/pull/5695">#5695</a></summary>

Code and docstring tweaks on https://github.com/ynput/OpenPype/pull/5623


___

</details>


<details>
<summary>AYON: Small settings fixes <a href="https://github.com/ynput/OpenPype/pull/5699">#5699</a></summary>

Small changes/fixes related to AYON settings. All foundry apps variant `13-0` has label `13.0`. Key `"ExtractReviewIntermediates"` is not mandatory in settings.


___

</details>


<details>
<summary>Blender: Alembic Animation loader <a href="https://github.com/ynput/OpenPype/pull/5711">#5711</a></summary>

Implemented loading Alembic Animations in Blender.


___

</details>

### **🐛 Bug fixes**


<details>
<summary>Maya: Missing "data" field and enabling of audio <a href="https://github.com/ynput/OpenPype/pull/5618">#5618</a></summary>

When updating audio containers, the field "data" was missing and the audio node was not enabled on the timeline.


___

</details>


<details>
<summary>Maya: Bug in validate Plug-in Path Attribute <a href="https://github.com/ynput/OpenPype/pull/5687">#5687</a></summary>

Overwriting list with string is causing `TypeError: string indices must be integers` in subsequent iterations, crashing the validator plugin.


___

</details>


<details>
<summary>General: Avoid fallback if value is 0 for handle start/end <a href="https://github.com/ynput/OpenPype/pull/5652">#5652</a></summary>

There's a bug on the `pyblish_functions.get_time_data_from_instance_or_context` where if `handleStart` or `handleEnd` on the instance are set to value 0 it's falling back to grabbing the handles from the instance context. Instead, the logic should be that it only falls back to the `instance.context` if the key doesn't exist.This change was only affecting me on the `handleStart`/`handleEnd` and it's unlikely it could cause issues on `frameStart`, `frameEnd` or `fps` but regardless, the `get` logic is wrong.


___

</details>


<details>
<summary>Fusion: added missing env vars to Deadline submission <a href="https://github.com/ynput/OpenPype/pull/5659">#5659</a></summary>

Environment variables discerning type of job was missing. Without this injection of environment variables won't start.


___

</details>


<details>
<summary>Nuke: workfile version synchronization settings fixed <a href="https://github.com/ynput/OpenPype/pull/5662">#5662</a></summary>

Settings for synchronizing workfile version to published products is fixed.


___

</details>


<details>
<summary>AYON Workfiles Tool: Open workfile changes context <a href="https://github.com/ynput/OpenPype/pull/5671">#5671</a></summary>

Change context when workfile is opened.


___

</details>


<details>
<summary>Blender: Fix remove/update in new layout instance <a href="https://github.com/ynput/OpenPype/pull/5679">#5679</a></summary>

Fixes an error that occurs when removing or updating an asset in a new layout instance.


___

</details>


<details>
<summary>AYON Launcher tool: Fix refresh btn <a href="https://github.com/ynput/OpenPype/pull/5685">#5685</a></summary>

Refresh button does propagate refreshed content properly. Folders and tasks are cached for 60 seconds instead of 10 seconds. Auto-refresh in launcher will refresh only actions and related data which is project and project settings.


___

</details>


<details>
<summary>Deadline: handle all valid paths in RenderExecutable <a href="https://github.com/ynput/OpenPype/pull/5694">#5694</a></summary>

This commit enhances the path resolution mechanism in the RenderExecutable function of the Ayon plugin. Previously, the function only considered paths starting with a tilde (~), ignoring other valid paths listed in exe_list. This limitation led to an empty expanded_paths list when none of the paths in exe_list started with a tilde, causing the function to fail in finding the Ayon executable.With this fix, the RenderExecutable function now correctly processes and includes all valid paths from exe_list, improving its reliability and preventing unnecessary errors related to Ayon executable location.


___

</details>


<details>
<summary>AYON Launcher tool: Fix skip last workfile boolean <a href="https://github.com/ynput/OpenPype/pull/5700">#5700</a></summary>

Skip last workfile boolean works as expected.


___

</details>


<details>
<summary>Chore: Explore here action can work without task <a href="https://github.com/ynput/OpenPype/pull/5703">#5703</a></summary>

Explore here action does not crash when task is not selected, and change error message a little.


___

</details>


<details>
<summary>Testing: Inject mongo_url argument earlier <a href="https://github.com/ynput/OpenPype/pull/5706">#5706</a></summary>

Fix for https://github.com/ynput/OpenPype/pull/5676The Mongo url is used earlier in the execution.


___

</details>


<details>
<summary>Blender: Add support to auto-install PySide2 in blender 4 <a href="https://github.com/ynput/OpenPype/pull/5723">#5723</a></summary>

Change version regex to support blender 4 subfolder.


___

</details>


<details>
<summary>Fix: Hardcoded main site and wrongly copied workfile <a href="https://github.com/ynput/OpenPype/pull/5733">#5733</a></summary>

Fixing these two issues:
- Hardcoded main site -> Replaced by `anatomy.fill_root`.
- Workfiles can sometimes be copied while they shouldn't.


___

</details>


<details>
<summary>Bugfix: ServerDeleteOperation asset -> folder conversion typo <a href="https://github.com/ynput/OpenPype/pull/5735">#5735</a></summary>

Fix ServerDeleteOperation asset -> folder conversion typo


___

</details>


<details>
<summary>Nuke: loaders are filtering correctly <a href="https://github.com/ynput/OpenPype/pull/5739">#5739</a></summary>

Variable name for filtering by extensions were not correct - it suppose to be plural. It is fixed now and filtering is working as suppose to.


___

</details>


<details>
<summary>Nuke: failing multiple thumbnails integration <a href="https://github.com/ynput/OpenPype/pull/5741">#5741</a></summary>

This handles the situation when `ExtractReviewIntermediates` (previously `ExtractReviewDataMov`) has multiple outputs, including thumbnails that need to be integrated. Previously, integrating the thumbnail representation was causing an issue in the integration process. However, we have now resolved this issue by no longer integrating thumbnails as loadable representations.NOW default is that thumbnail representation are NOT integrated (eg. they will not show up in DB > couldn't be Loaded in Loader) and no `_thumb.jpg` will be left in `render` (most likely) publish folder.IF there would be need to override this behavior, please use `project_settings/global/publish/PreIntegrateThumbnails`


___

</details>


<details>
<summary>AYON Settings: Fix global overrides <a href="https://github.com/ynput/OpenPype/pull/5745">#5745</a></summary>

The `output` dictionary that gets passed into `ayon_settings._convert_global_project_settings` gets replaced when converting the settings for `ExtractOIIOTranscode`. This results in `global` not being in the output dictionary and thus the defaults being used and not the project overrides.


___

</details>


<details>
<summary>Chore: AYON query functions arguments <a href="https://github.com/ynput/OpenPype/pull/5752">#5752</a></summary>

Fixed how `archived` argument is handled in get subsets/assets function.


___

</details>

### **🔀 Refactored code**


<details>
<summary>Publisher: Refactor Report Maker plugin data storage to be a dict by plugin.id <a href="https://github.com/ynput/OpenPype/pull/5668">#5668</a></summary>

Refactor Report Maker plugin data storage to be a dict by `plugin.id`Also fixes `_current_plugin_data` type on `__init__`


___

</details>


<details>
<summary>Chore: Refactor Resolve into new style HostBase, IWorkfileHost, ILoadHost <a href="https://github.com/ynput/OpenPype/pull/5701">#5701</a></summary>

Refactor Resolve into new style HostBase, IWorkfileHost, ILoadHost


___

</details>

### **Merged pull requests**


<details>
<summary>Chore: Maya reduce get project settings calls <a href="https://github.com/ynput/OpenPype/pull/5669">#5669</a></summary>

Re-use system settings / project settings where we can instead of requerying.


___

</details>


<details>
<summary>Extended error message when getting subset name <a href="https://github.com/ynput/OpenPype/pull/5649">#5649</a></summary>

Each Creator is using `get_subset_name` functions which collects context data and fills configured template with placeholders.If any key is missing in the template, non descriptive error is thrown.This should provide more verbose message:


___

</details>


<details>
<summary>Tests: Remove checks for env var <a href="https://github.com/ynput/OpenPype/pull/5696">#5696</a></summary>

Env var will be filled in `env_var` fixture, here it is too early to check


___

</details>




## [3.17.1](https://github.com/ynput/OpenPype/tree/3.17.1)


[Full Changelog](https://github.com/ynput/OpenPype/compare/3.17.0...3.17.1)

### **🆕 New features**


<details>
<summary>Unreal: Yeti support <a href="https://github.com/ynput/OpenPype/pull/5643">#5643</a></summary>

Implemented Yeti support for Unreal.


___

</details>


<details>
<summary>Houdini: Add Static Mesh product-type (family) <a href="https://github.com/ynput/OpenPype/pull/5481">#5481</a></summary>

This PR adds support to publish Unreal Static Mesh in Houdini as FBXQuick recap
- [x] Add UE Static Mesh Creator
- [x] Dynamic subset name like in Maya
- [x] Collect Static Mesh Type
- [x] Update collect output node
- [x] Validate FBX output node
- [x] Validate mesh is static
- [x] Validate Unreal Static Mesh Name
- [x] Validate Subset Name
- [x] FBX Extractor
- [x] FBX Loader
- [x] Update OP Settings
- [x] Update AYON Settings


___

</details>


<details>
<summary>Launcher tool: Refactor launcher tool (for AYON) <a href="https://github.com/ynput/OpenPype/pull/5612">#5612</a></summary>

Refactored launcher tool to new tool. Separated backend and frontend logic. Refactored logic is AYON-centric and is used only in AYON mode, so it does not affect OpenPype.


___

</details>

### **🚀 Enhancements**


<details>
<summary>Maya: Use custom staging dir function for Maya renders - OP-5265 <a href="https://github.com/ynput/OpenPype/pull/5186">#5186</a></summary>

Check for custom staging dir when setting the renders output folder in Maya.


___

</details>


<details>
<summary>Colorspace: updating file path detection methods <a href="https://github.com/ynput/OpenPype/pull/5273">#5273</a></summary>

Support for OCIO v2 file rules integrated into the available color management API


___

</details>


<details>
<summary>Chore: add default isort config <a href="https://github.com/ynput/OpenPype/pull/5572">#5572</a></summary>

Add default configuration for isort tool


___

</details>


<details>
<summary>Deadline: set PATH environment in deadline jobs by GlobalJobPreLoad <a href="https://github.com/ynput/OpenPype/pull/5622">#5622</a></summary>

This PR makes `GlobalJobPreLoad` to set `PATH` environment in deadline jobs so that we don't have to use the full executable path for deadline to launch the dcc app. This trick should save us adding logic to pass houdini patch version and modifying Houdini deadline plugin. This trick should work with other DCCs


___

</details>


<details>
<summary>nuke: extract review data mov read node with expression <a href="https://github.com/ynput/OpenPype/pull/5635">#5635</a></summary>

Some productions might have set default values for read nodes, those settings are not colliding anymore now.


___

</details>

### **🐛 Bug fixes**


<details>
<summary>Maya: Support new publisher for colorsets validation. <a href="https://github.com/ynput/OpenPype/pull/5630">#5630</a></summary>

Fix `validate_color_sets` for the new publisher.In current `develop` the repair option does not appear due to wrong error raising.


___

</details>


<details>
<summary>Houdini: Camera Loader fix mismatch for Maya cameras <a href="https://github.com/ynput/OpenPype/pull/5584">#5584</a></summary>

This PR adds
- A workaround to match Maya render mask in Houdini
- `SetCameraResolution` inventory action
- set camera resolution when loading or updating camera


___

</details>


<details>
<summary>Nuke: fix set colorspace on writes <a href="https://github.com/ynput/OpenPype/pull/5634">#5634</a></summary>

Colorspace is set correctly to any write node created from publisher.


___

</details>


<details>
<summary>TVPaint: Fix review family extraction <a href="https://github.com/ynput/OpenPype/pull/5637">#5637</a></summary>

Extractor marks representation of review instance with review tag.


___

</details>


<details>
<summary>AYON settings: Extract OIIO transcode settings <a href="https://github.com/ynput/OpenPype/pull/5639">#5639</a></summary>

Output definitions of Extract OIIO transcode have name to match OpenPype settings, and the settings are converted to dictionary in settings conversion.


___

</details>


<details>
<summary>AYON: Fix task type short name conversion <a href="https://github.com/ynput/OpenPype/pull/5641">#5641</a></summary>

Convert AYON task type short name for OpenPype correctly.


___

</details>


<details>
<summary>colorspace: missing `allowed_exts` fix <a href="https://github.com/ynput/OpenPype/pull/5646">#5646</a></summary>

Colorspace module is not failing due to missing `allowed_exts` attribute.


___

</details>


<details>
<summary>Photoshop: remove trailing underscore in subset name <a href="https://github.com/ynput/OpenPype/pull/5647">#5647</a></summary>

If {layer} placeholder is at the end of subset name template and not used (for example in `auto_image` where separating it by layer doesn't make any sense) trailing '_' was kept. This updates cleaning logic and extracts it as it might be similar in regular `image` instance.


___

</details>


<details>
<summary>traypublisher: missing `assetEntity` in context data <a href="https://github.com/ynput/OpenPype/pull/5648">#5648</a></summary>

Issue with missing `assetEnity` key in context data is not problem anymore.


___

</details>


<details>
<summary>AYON: Workfiles tool save button works <a href="https://github.com/ynput/OpenPype/pull/5653">#5653</a></summary>

Fix save as button in workfiles tool.(It is mystery why this stopped to work??)


___

</details>


<details>
<summary>Max: bug fix delete items from container <a href="https://github.com/ynput/OpenPype/pull/5658">#5658</a></summary>

Fix the bug shown when clicking "Delete Items from Container" and selecting nothing and press ok.


___

</details>

### **🔀 Refactored code**


<details>
<summary>Chore: Remove unused functions from Fusion integration <a href="https://github.com/ynput/OpenPype/pull/5617">#5617</a></summary>

Cleanup unused code from Fusion integration


___

</details>

### **Merged pull requests**


<details>
<summary>Increase timout for deadline test <a href="https://github.com/ynput/OpenPype/pull/5654">#5654</a></summary>

DL picks up jobs quite slow, so bump up delay.


___

</details>




## [3.17.0](https://github.com/ynput/OpenPype/tree/3.17.0)


[Full Changelog](https://github.com/ynput/OpenPype/compare/3.16.7...3.17.0)

### **🚀 Enhancements**


<details>
<summary>Chore: Remove schema from OpenPype root <a href="https://github.com/ynput/OpenPype/pull/5355">#5355</a></summary>

Remove unused schema directory in root of repository which was moved inside openpype/pipeline/schema.


___

</details>


<details>
<summary>Igniter: Allow custom Qt scale factor rounding policy <a href="https://github.com/ynput/OpenPype/pull/5554">#5554</a></summary>

Do not force `PassThrough` rounding policy if different policy is defined via env variable.


___

</details>

### **🐛 Bug fixes**


<details>
<summary>Chore: Lower urllib3 to support older OpenSSL <a href="https://github.com/ynput/OpenPype/pull/5538">#5538</a></summary>

Lowered `urllib3` to `1.26.16` to support older OpenSSL.


___

</details>


<details>
<summary>Chore: Do not try to add schema to zip files <a href="https://github.com/ynput/OpenPype/pull/5557">#5557</a></summary>

Do not add `schema` folder to zip file. This fixes issue cause by https://github.com/ynput/OpenPype/pull/5355 .


___

</details>


<details>
<summary>Chore: Lower click dependency version <a href="https://github.com/ynput/OpenPype/pull/5629">#5629</a></summary>

Lower click version to support older versions of python.


___

</details>

### **Merged pull requests**


<details>
<summary>Bump certifi from 2023.5.7 to 2023.7.22 <a href="https://github.com/ynput/OpenPype/pull/5351">#5351</a></summary>

Bumps [certifi](https://github.com/certifi/python-certifi) from 2023.5.7 to 2023.7.22.
<details>
<summary>Commits</summary>
<ul>
<li><a href="https://github.com/certifi/python-certifi/commit/8fb96ed81f71e7097ed11bc4d9b19afd7ea5c909"><code>8fb96ed</code></a> 2023.07.22</li>
<li><a href="https://github.com/certifi/python-certifi/commit/afe77220e0eaa722593fc5d294213ff5275d1b40"><code>afe7722</code></a> Bump actions/setup-python from 4.6.1 to 4.7.0 (<a href="https://redirect.github.com/certifi/python-certifi/issues/230">#230</a>)</li>
<li><a href="https://github.com/certifi/python-certifi/commit/2038739ad56abec7aaddfa90ad2ce6b3ed7f5c7b"><code>2038739</code></a> Bump dessant/lock-threads from 3.0.0 to 4.0.1 (<a href="https://redirect.github.com/certifi/python-certifi/issues/229">#229</a>)</li>
<li><a href="https://github.com/certifi/python-certifi/commit/44df761f4c09d19f32b3cc09208a739043a5e25b"><code>44df761</code></a> Hash pin Actions and enable dependabot (<a href="https://redirect.github.com/certifi/python-certifi/issues/228">#228</a>)</li>
<li>See full diff in <a href="https://github.com/certifi/python-certifi/compare/2023.05.07...2023.07.22">compare view</a></li>
</ul>
</details>
<br />


[![Dependabot compatibility score](https://dependabot-badges.githubapp.com/badges/compatibility_score?dependency-name=certifi&package-manager=pip&previous-version=2023.5.7&new-version=2023.7.22)](https://docs.github.com/en/github/managing-security-vulnerabilities/about-dependabot-security-updates#about-compatibility-scores)

You can trigger a rebase of this PR by commenting `@dependabot rebase`.

[//]: # (dependabot-automerge-start)
[//]: # (dependabot-automerge-end)

---

<details>
<summary>Dependabot commands and options</summary>
<br />

You can trigger Dependabot actions by commenting on this PR:
- `@dependabot rebase` will rebase this PR
- `@dependabot recreate` will recreate this PR, overwriting any edits that have been made to it
- `@dependabot merge` will merge this PR after your CI passes on it
- `@dependabot squash and merge` will squash and merge this PR after your CI passes on it
- `@dependabot cancel merge` will cancel a previously requested merge and block automerging
- `@dependabot reopen` will reopen this PR if it is closed
- `@dependabot close` will close this PR and stop Dependabot recreating it. You can achieve the same result by closing it manually
- `@dependabot ignore this major version` will close this PR and stop Dependabot creating any more for this major version (unless you reopen the PR or upgrade to it yourself)
- `@dependabot ignore this minor version` will close this PR and stop Dependabot creating any more for this minor version (unless you reopen the PR or upgrade to it yourself)
- `@dependabot ignore this dependency` will close this PR and stop Dependabot creating any more for this dependency (unless you reopen the PR or upgrade to it yourself)
You can disable automated security fix PRs for this repo from the [Security Alerts page](https://github.com/ynput/OpenPype/network/alerts).

</details>

> **Note**
> Automatic rebases have been disabled on this pull request as it has been open for over 30 days.

___

</details>




## [3.16.7](https://github.com/ynput/OpenPype/tree/3.16.7)


[Full Changelog](https://github.com/ynput/OpenPype/compare/3.16.6...3.16.7)

### **🆕 New features**


<details>
<summary>Maya: Extract active view as thumbnail when no thumbnail set <a href="https://github.com/ynput/OpenPype/pull/5426">#5426</a></summary>

This sets the Maya instance's thumbnail to the current active view if no thumbnail was set yet.


___

</details>


<details>
<summary>Maya: Implement USD publish and load using native `mayaUsdPlugin` <a href="https://github.com/ynput/OpenPype/pull/5573">#5573</a></summary>

Implement Creator and Loaders for extraction and loading of USD files using Maya's own `mayaUsdPlugin`.Also adds support to load a `usd` file into an Arnold Standin (`aiStandin`) and assigning looks to it.


___

</details>


<details>
<summary>AYON: Ignore separated modules <a href="https://github.com/ynput/OpenPype/pull/5619">#5619</a></summary>

Do not load already separated modules from default directory.


___

</details>

### **🚀 Enhancements**


<details>
<summary>Maya: Reduce amount of code for Collect Looks <a href="https://github.com/ynput/OpenPype/pull/5253">#5253</a></summary>

- Refactor `get_file_node_files` because popping from `paths` by index should have been done in reversed order anyway. It's now changed to not need popping at all.
- Removed unused `RENDERER_NODE_TYPES` and if-branch which collected `node_attrs` list which was unused + collected members which was also done outside of the if branch and thus generated no extra data.
- Collected all materials from look set attributes at once instead of multiple queries
- Collected all file nodes in history from a single query instead of per type
- Restructured assignment of `instance.data["resources"]` to be more readable
- Cached `PXR_NODES` only ones (Note: plugin load is checked on discovery of the collect look plugin) instead of querying plugin load and its nodes per file node per attribute
- Removed some debug logs or combined some messages


___

</details>


<details>
<summary>AYON: Mark deprecated settings in Maya <a href="https://github.com/ynput/OpenPype/pull/5627">#5627</a></summary>

Added deprecated info to docstrings of maya colormanagement settings.Resolves: https://github.com/ynput/OpenPype/issues/5556


___

</details>


<details>
<summary>Max: switching versions of maxScene maintain parentage/links with the loaders <a href="https://github.com/ynput/OpenPype/pull/5424">#5424</a></summary>

When using scene inventory to manage or update the version of the loading objects, the linked modifiers or parentage of the objects would be kept.Meanwhile, loaded objects from all loaders no longer parented to the container with OP Data.


___

</details>


<details>
<summary>3ds max: small tweaks to obj extractor and model publishing flow <a href="https://github.com/ynput/OpenPype/pull/5605">#5605</a></summary>

There migh be situation where OBJ Extractor passes without failure, but no obj file is produced. This is adding simple check directly into the extractor to catch it earlier then in the integration phase. Also switched `Validate USD Plugin` to optional, because it was always run no matter if the Extract USD was enabled or not, hindering testing (and publishing).


___

</details>


<details>
<summary>TVPaint: Plugin can be reopened <a href="https://github.com/ynput/OpenPype/pull/5610">#5610</a></summary>

TVPaint plugin can be reopened.


___

</details>


<details>
<summary>Maya: Remove context prompt <a href="https://github.com/ynput/OpenPype/pull/5632">#5632</a></summary>

More of a plea than a PR, but could we please remove the context prompt in Maya when switching tasks?


___

</details>


<details>
<summary>General: Create a desktop icon is checked <a href="https://github.com/ynput/OpenPype/pull/5636">#5636</a></summary>

In OP Installer `Create a desktop icon` is checked by default. 
___

</details>

### **🐛 Bug fixes**


<details>
<summary>Maya: Extract look is not AYON compatible - OP-5375 <a href="https://github.com/ynput/OpenPype/pull/5341">#5341</a></summary>

The textures that would use hardlinking are going through texture processors. Currently all texture processors are hardcoded to copy texture instead of respecting the settings of forcing to copy.The texture processors were last modified 4 months ago, so effectively all clients that are on any pipeline updated in the last 4 months wont be utilizing hardlinking at all, since the hardcoded texture processors will copy texture no matter the OS.This opts for completely disabling the hardlinking feature, while we figure out what to do about it.


___

</details>


<details>
<summary>Maya: Multiverse USD Override inherit from correct new style creator <a href="https://github.com/ynput/OpenPype/pull/5566">#5566</a></summary>

Fix Creator for Multiverse USD Override by inheriting from correct new style creator class type


___

</details>


<details>
<summary>Max: Bug Fix  Alembic Loaders with Ornatrix <a href="https://github.com/ynput/OpenPype/pull/5434">#5434</a></summary>

Bugfix the alembic loader with both ornatrix alembic and max alembic supportsAdd the ornatrix alembic loaders for loading the alembic with Ornatrix-related modifiers.


___

</details>


<details>
<summary>AYON: Avoid creation of duplicated links <a href="https://github.com/ynput/OpenPype/pull/5593">#5593</a></summary>

Handle cases when an existing link should be recreated and do not create the same link multitple times during single publishing.


___

</details>


<details>
<summary>Extract Review: Multilayer specification for ffmpeg <a href="https://github.com/ynput/OpenPype/pull/5613">#5613</a></summary>

Extract review is specifying layer name when exr is multilayer.


___

</details>


<details>
<summary>Fussion: added support for Fusion 17 <a href="https://github.com/ynput/OpenPype/pull/5614">#5614</a></summary>

Fusion 17 still uses Python 3.6 which causes issues with some our delivered libraries. Vendorized necessary set for Python 3.6


___

</details>


<details>
<summary>Publisher: Fix screenshot widget <a href="https://github.com/ynput/OpenPype/pull/5615">#5615</a></summary>

Use correct super method name.EDITED:Removed fade animation which is not triggered at some cases, e.g. in Nuke the animation does not start. I do expect that is caused by `exec_` on the dialog, which blocks event processing to the animation, even when I've added the window as parent it still didn't trigger registered callback.Modified how the "empty" space is not filled by using paths instead of clear mode on painter. Added render hints to add antialiasing.


___

</details>


<details>
<summary>Photoshop: auto_images without alpha will not fail <a href="https://github.com/ynput/OpenPype/pull/5620">#5620</a></summary>

ExtractReview caused issue on `auto_image` instance without alpha channel, this fixes it.


___

</details>


<details>
<summary>Fix - _id key used instead of id in get_last_version_by_subset_name <a href="https://github.com/ynput/OpenPype/pull/5626">#5626</a></summary>

Just 'id' is not returned because value in fields. Caused KeyError.


___

</details>


<details>
<summary>Bugfix: create symlinks for ssl libs on Centos 7 <a href="https://github.com/ynput/OpenPype/pull/5633">#5633</a></summary>

Docker build was missing `libssl.1.1.so` and `libcrypto.1.1.so` symlinks needed by the executable itself, because Python is now explicitly built with OpenSSL 1.1.1


___

</details>

### **📃 Documentation**


<details>
<summary>Documentation/local settings <a href="https://github.com/ynput/OpenPype/pull/5102">#5102</a></summary>

I completed the "Working with local settings" page. I updated the screenshot, wrote an explanation for each empty category, and if available, linked the more detailed pages already existing. I also added the "Environments" category.


___

</details>




## [3.16.6](https://github.com/ynput/OpenPype/tree/3.16.6)


[Full Changelog](https://github.com/ynput/OpenPype/compare/3.16.5...3.16.6)

### **🆕 New features**


<details>
<summary>Workfiles tool: Refactor workfiles tool (for AYON) <a href="https://github.com/ynput/OpenPype/pull/5550">#5550</a></summary>

Refactored workfiles tool to new tool. Separated backend and frontend logic. Refactored logic is AYON-centric and is used only in AYON mode, so it does not affect OpenPype.


___

</details>


<details>
<summary>AfterEffects: added validator for missing files in FootageItems <a href="https://github.com/ynput/OpenPype/pull/5590">#5590</a></summary>

Published composition in AE could contain multiple FootageItems as a layers. If FootageItem contains imported file and it doesn't exist, render triggered by Publish process will silently fail and no output is generated. This could cause failure later in the process with unclear reason. (In `ExtractReview`).This PR adds validation to protect from this.


___

</details>

### **🚀 Enhancements**


<details>
<summary>Maya: Yeti Cache Include viewport preview settings from source <a href="https://github.com/ynput/OpenPype/pull/5561">#5561</a></summary>

When publishing and loading yeti caches persist the display output and preview colors + settings to ensure consistency in the view


___

</details>


<details>
<summary>Houdini: validate colorspace in review rop <a href="https://github.com/ynput/OpenPype/pull/5322">#5322</a></summary>

Adding a validator that checks if 'OCIO Colorspace' parameter on  review rop was set to a valid value.It is a step towards managing colorspace in review ropvalid values are the ones in the dropdown menuthis validator also provides some helper actions This PR is related to #4836 and #4833


___

</details>


<details>
<summary>Colorspace: adding abstraction of publishing related functions <a href="https://github.com/ynput/OpenPype/pull/5497">#5497</a></summary>

The functionality of Colorspace has been abstracted for greater usability.


___

</details>


<details>
<summary>Nuke: removing redundant workfile colorspace attributes <a href="https://github.com/ynput/OpenPype/pull/5580">#5580</a></summary>

Nuke root workfile colorspace data type knobs are long time configured automatically via config roles or the default values are also working well. Therefore there is no need for pipeline managed knobs.


___

</details>


<details>
<summary>Ftrack: Less verbose logs for Ftrack integration in artist facing logs <a href="https://github.com/ynput/OpenPype/pull/5596">#5596</a></summary>

- Reduce artist-facing logs for component integration for Ftrack
- Avoid "Comment is not set" log in artist facing report for Kitsu and Ftrack
- Remove info log about `ffprobe` inspecting a file (changed to debug log)
- interesting to see however that it ffprobes the same jpeg twice - but maybe once for thumbnail?


___

</details>

### **🐛 Bug fixes**


<details>
<summary>Maya: Fix rig validators for new out_SET and controls_SET names  <a href="https://github.com/ynput/OpenPype/pull/5595">#5595</a></summary>

Fix usage of `out_SET` and `controls_SET` since #5310 because they can now be prefixed by the subset name.


___

</details>


<details>
<summary>TrayPublisher: set default frame values to sequential data <a href="https://github.com/ynput/OpenPype/pull/5530">#5530</a></summary>

We are inheriting  default frame handles and fps data either from project or setting them to 0. This is just for case a production will decide not to injest the sequential representations with asset based metadata.


___

</details>


<details>
<summary>Publisher: Screenshot opacity value fix <a href="https://github.com/ynput/OpenPype/pull/5576">#5576</a></summary>

Fix opacity value.


___

</details>


<details>
<summary>AfterEffects: fix imports of image sequences <a href="https://github.com/ynput/OpenPype/pull/5581">#5581</a></summary>

#4602 broke imports of image sequences.


___

</details>


<details>
<summary>AYON: Fix representation context conversion <a href="https://github.com/ynput/OpenPype/pull/5591">#5591</a></summary>

Do not fix `"folder"` key in representation context until it is needed.


___

</details>


<details>
<summary>ayon-nuke: default factory to lists  <a href="https://github.com/ynput/OpenPype/pull/5594">#5594</a></summary>

Default factory were missing in settings schemas for complicated objects like lists and it was causing settings to be failing saving.


___

</details>


<details>
<summary>Maya: Fix look assigner showing no asset if 'not found' representations are present <a href="https://github.com/ynput/OpenPype/pull/5597">#5597</a></summary>

Fix Maya Look assigner failing to show any content if it finds an invalid container for which it can't find the asset in the current project. (This can happen when e.g. loading something from a library project).There was logic already to avoid this but there was a bug where it used variable `_id` which did not exist and likely had to be `asset_id`.I've fixed that and improved the logged message a bit, e.g.:
```
// Warning: openpype.hosts.maya.tools.mayalookassigner.commands : Id found on 22 nodes for which no asset is found database, skipping '641d78ec85c3c5b102e836b0'
```
Example not found representation in Loader:The issue isn't necessarily related to NOT FOUND representations but in essence boils down to finding nodes with asset ids that do not exist in the current project which could very well just be local meshes in your scene.**Note:**I've excluded logging the nodes themselves because that tends to be a very long list of nodes. Only downside to removing that is that it's unclear which nodes are related to that `id`. If there are any ideas on how to still provide a concise informational message about that that'd be great so I could add it. Things I had considered:
- Report the containers, issue here is that it's about asset ids on nodes which don't HAVE to be in containers - it could be local geometry
- Report the namespaces, issue here is that it could be nodes without namespaces (plus potentially not about ALL nodes in a namespace)
- Report the short names of the nodes; it's shorter and readable but still likely a lot of nodes.@tokejepsen @LiborBatek any other ideas?


___

</details>


<details>
<summary>Photoshop: fixed blank Flatten image <a href="https://github.com/ynput/OpenPype/pull/5600">#5600</a></summary>

Flatten image is simplified publishing approach where all visible layers are "flatten" and published together. This image could be used as a reference etc.This is implemented by auto creator which wasn't updated after first publish. This would result in missing newly created layers after `auto_image` instance was created.


___

</details>


<details>
<summary>Blender: Remove Hardcoded Subset Name for Reviews <a href="https://github.com/ynput/OpenPype/pull/5603">#5603</a></summary>

Fixes hardcoded subset name for Reviews in Blender.


___

</details>


<details>
<summary>TVPaint: Fix tool callbacks <a href="https://github.com/ynput/OpenPype/pull/5608">#5608</a></summary>

Do not wait for callback to finish.


___

</details>

### **🔀 Refactored code**


<details>
<summary>Chore: Remove unused variables and cleanup <a href="https://github.com/ynput/OpenPype/pull/5588">#5588</a></summary>

Removing some unused variables. In some cases the unused variables _seemed like they should've been used - maybe?_ so please **double check the code whether it doesn't hint to an already existing bug**.Also tweaked some other small bugs in code + tweaked logging levels.


___

</details>

### **Merged pull requests**


<details>
<summary>Chore: Loader log deprecation warning for 'fname' attribute <a href="https://github.com/ynput/OpenPype/pull/5587">#5587</a></summary>

Since https://github.com/ynput/OpenPype/pull/4602 the `fname` attribute on the `LoaderPlugin` should've been deprecated and set for removal over time. However, no deprecation warning was logged whatsoever and thus one usage appears to have sneaked in (fixed with this PR) and a new one tried to sneak in with a recent PR


___

</details>




## [3.16.5](https://github.com/ynput/OpenPype/tree/3.16.5)


[Full Changelog](https://github.com/ynput/OpenPype/compare/3.16.4...3.16.5)

### **🆕 New features**


<details>
<summary>Attribute Definitions: Multiselection enum def <a href="https://github.com/ynput/OpenPype/pull/5547">#5547</a></summary>

Added `multiselection` option to `EnumDef`.


___

</details>

### **🚀 Enhancements**


<details>
<summary>Farm: adding target collector <a href="https://github.com/ynput/OpenPype/pull/5494">#5494</a></summary>

Enhancing farm publishing workflow.


___

</details>


<details>
<summary>Maya: Optimize validate plug-in path attributes <a href="https://github.com/ynput/OpenPype/pull/5522">#5522</a></summary>

- Optimize query (use `cmds.ls` once)
- Add Select Invalid action
- Improve validation report
- Avoid "Unknown object type" errors


___

</details>


<details>
<summary>Maya: Remove Validate Instance Attributes plug-in <a href="https://github.com/ynput/OpenPype/pull/5525">#5525</a></summary>

Remove Validate Instance Attributes plug-in.


___

</details>


<details>
<summary>Enhancement: Tweak logging for artist facing reports <a href="https://github.com/ynput/OpenPype/pull/5537">#5537</a></summary>

Tweak the logging of publishing for global, deadline, maya and a fusion plugin to have a cleaner artist-facing report.
- Fix context being reported correctly from CollectContext
- Fix ValidateMeshArnoldAttributes: fix when arnold is not loaded, fix applying settings, fix for when ai attributes do not exist


___

</details>


<details>
<summary>AYON: Update settings <a href="https://github.com/ynput/OpenPype/pull/5544">#5544</a></summary>

Updated settings in AYON addons and conversion of AYON settings in OpenPype.


___

</details>


<details>
<summary>Chore: Removed Ass export script <a href="https://github.com/ynput/OpenPype/pull/5560">#5560</a></summary>

Removed Arnold render script, which was obsolete and unused.


___

</details>


<details>
<summary>Nuke: Allow for knob values to be validated against multiple values. <a href="https://github.com/ynput/OpenPype/pull/5042">#5042</a></summary>

Knob values can now be validated against multiple values, so you can allow write nodes to be `exr` and `png`, or `16-bit` and `32-bit`.


___

</details>


<details>
<summary>Enhancement: Cosmetics for Higher version of publish already exists validation error <a href="https://github.com/ynput/OpenPype/pull/5190">#5190</a></summary>

Fix double spaces in message.Example output **after** the PR:


___

</details>


<details>
<summary>Nuke: publish existing frames on farm <a href="https://github.com/ynput/OpenPype/pull/5409">#5409</a></summary>

This PR proposes adding a fourth option in Nuke render publish called "Use Existing Frames - Farm". This would be useful when the farm is busy or when the artist lacks enough farm licenses. Additionally, some artists prefer rendering on the farm but still want to check frames before publishing.By adding the "Use Existing Frames - Farm" option, artists will have more flexibility and control over their render publishing process. This enhancement will streamline the workflow and improve efficiency for Nuke users.


___

</details>


<details>
<summary>Unreal: Create project in temp location and move to final when done <a href="https://github.com/ynput/OpenPype/pull/5476">#5476</a></summary>

Create Unreal project in local temporary folder and when done, move it to final destination.


___

</details>


<details>
<summary>TrayPublisher: adding audio product type into default presets <a href="https://github.com/ynput/OpenPype/pull/5489">#5489</a></summary>

Adding Audio product type into default presets so anybody can publish audio to their shots.


___

</details>


<details>
<summary>Global: avoiding cleanup of flagged representation <a href="https://github.com/ynput/OpenPype/pull/5502">#5502</a></summary>

Publishing folder can be flagged as persistent at representation level.


___

</details>


<details>
<summary>General: missing tag could raise error <a href="https://github.com/ynput/OpenPype/pull/5511">#5511</a></summary>

- avoiding potential situation where missing Tag key could raise error


___

</details>


<details>
<summary>Chore: Queued event system <a href="https://github.com/ynput/OpenPype/pull/5514">#5514</a></summary>

Implemented event system with more expected behavior of event system. If an event is triggered during other event callback, it is not processed immediately but waits until all callbacks of previous events are done. The event system also allows to not trigger events directly once `emit_event` is called which gives option to process events in custom loops.


___

</details>


<details>
<summary>Publisher: Tweak log message to provide plugin name after "Plugin" <a href="https://github.com/ynput/OpenPype/pull/5521">#5521</a></summary>

Fix logged message for settings automatically applied to plugin attributes


___

</details>


<details>
<summary>Houdini: Improve VDB Selection <a href="https://github.com/ynput/OpenPype/pull/5523">#5523</a></summary>

Improves VDB selection if selection is `SopNode`:   return the selected sop nodeif selection is `ObjNode`:   get the output node with the minimum 'outputidx' or the node with display flag


___

</details>


<details>
<summary>Maya: Refactor/tweak Validate Instance In same Context plug-in <a href="https://github.com/ynput/OpenPype/pull/5526">#5526</a></summary>

- Chore/Refactor: Re-use existing select invalid and repair actions
- Enhancement: provide more elaborate PublishValidationError report
- Bugfix: fix "optional" support by using `OptionalPyblishPluginMixin` base class.


___

</details>


<details>
<summary>Enhancement: Update houdini main menu <a href="https://github.com/ynput/OpenPype/pull/5527">#5527</a></summary>

This PR adds two updates:
- dynamic main menu
- dynamic asset name and task


___

</details>


<details>
<summary>Houdini: Reset FPS when clicking Set Frame Range <a href="https://github.com/ynput/OpenPype/pull/5528">#5528</a></summary>

_Similar to Maya,_ Make `Set Frame Range` resets FPS, issue https://github.com/ynput/OpenPype/issues/5516


___

</details>


<details>
<summary>Enhancement: Deadline plugins optimize, cleanup and fix optional support for validate deadline pools <a href="https://github.com/ynput/OpenPype/pull/5531">#5531</a></summary>

- Fix optional support of validate deadline pools
- Query deadline webservice only once per URL for verification, and once for available deadline pools instead of for every instance
- Use `deadlineUrl` in `instance.data` when validating pools if it is set.
- Code cleanup: Re-use existing `requests_get` implementation


___

</details>


<details>
<summary>Chore: PowerShell script for docker build <a href="https://github.com/ynput/OpenPype/pull/5535">#5535</a></summary>

Added PowerShell script to run docker build.


___

</details>


<details>
<summary>AYON: Deadline expand userpaths in executables list <a href="https://github.com/ynput/OpenPype/pull/5540">#5540</a></summary>

Expande `~` paths in executables list.


___

</details>


<details>
<summary>Chore: Use correct git url <a href="https://github.com/ynput/OpenPype/pull/5542">#5542</a></summary>

Fixed github url in README.md.


___

</details>


<details>
<summary>Chore: Create plugin does not expect system settings <a href="https://github.com/ynput/OpenPype/pull/5553">#5553</a></summary>

System settings are not passed to initialization of create plugin initialization (and `apply_settings`).


___

</details>


<details>
<summary>Chore: Allow custom Qt scale factor rounding policy <a href="https://github.com/ynput/OpenPype/pull/5555">#5555</a></summary>

Do not force `PassThrough` rounding policy if different policy is defined via env variable.


___

</details>


<details>
<summary>Houdini: Fix outdated containers pop-up on opening last workfile on launch <a href="https://github.com/ynput/OpenPype/pull/5567">#5567</a></summary>

Fix Houdini not showing outdated containers pop-up on scene open when launching with last workfile argument


___

</details>


<details>
<summary>Houdini: Improve errors e.g. raise PublishValidationError or cosmetics <a href="https://github.com/ynput/OpenPype/pull/5568">#5568</a></summary>

Improve errors e.g. raise PublishValidationError or cosmeticsThis also fixes the Increment Current File plug-in since due to an invalid import it was previously broken


___

</details>


<details>
<summary>Fusion: Code updates <a href="https://github.com/ynput/OpenPype/pull/5569">#5569</a></summary>

Update fusion code which contains obsolete code. Removed `switch_ui.py` script from fusion with related script in scripts.


___

</details>

### **🐛 Bug fixes**


<details>
<summary>Maya: Validate Shape Zero fix repair action + provide informational artist-facing report <a href="https://github.com/ynput/OpenPype/pull/5524">#5524</a></summary>

Refactor to PublishValidationError to allow the RepairAction to work + provide informational report message


___

</details>


<details>
<summary>Maya: Fix attribute definitions for `CreateYetiCache` <a href="https://github.com/ynput/OpenPype/pull/5574">#5574</a></summary>

Fix attribute definitions for `CreateYetiCache`


___

</details>


<details>
<summary>Max: Optional Renderable Camera Validator for Render Instance <a href="https://github.com/ynput/OpenPype/pull/5286">#5286</a></summary>

Optional validation to check on renderable camera being set up correctly for deadline submission.If not being set up correctly, it wont pass the validation and user can perform repair actions.


___

</details>


<details>
<summary>Max: Adding custom modifiers back to the loaded objects  <a href="https://github.com/ynput/OpenPype/pull/5378">#5378</a></summary>

The custom parameters OpenpypeData doesn't show in the loaded container when it is being loaded through the loader.


___

</details>


<details>
<summary>Houdini: Use default_variant to Houdini Node TAB Creator <a href="https://github.com/ynput/OpenPype/pull/5421">#5421</a></summary>

Use the default variant of the creator plugins on the interactive creator from the TAB node search instead of hard-coding it to `Main`.


___

</details>


<details>
<summary>Nuke: adding inherited colorspace from instance <a href="https://github.com/ynput/OpenPype/pull/5454">#5454</a></summary>

Thumbnails are extracted with inherited colorspace collected from rendering write node.


___

</details>


<details>
<summary>Add kitsu credentials to deadline publish job  <a href="https://github.com/ynput/OpenPype/pull/5455">#5455</a></summary>

This PR hopefully fixes this issue #5440


___

</details>


<details>
<summary>AYON: Fill entities during editorial <a href="https://github.com/ynput/OpenPype/pull/5475">#5475</a></summary>

Fill entities and update template data on instances during extract AYON hierarchy.


___

</details>


<details>
<summary>Ftrack: Fix version 0 when integrating to Ftrack - OP-6595 <a href="https://github.com/ynput/OpenPype/pull/5477">#5477</a></summary>

Fix publishing version 0 to Ftrack.


___

</details>


<details>
<summary>OCIO: windows unc path support in Nuke and Hiero <a href="https://github.com/ynput/OpenPype/pull/5479">#5479</a></summary>

Hiero and Nuke is not supporting windows unc path formatting in OCIO environment variable.


___

</details>


<details>
<summary>Deadline: Added super call to init <a href="https://github.com/ynput/OpenPype/pull/5480">#5480</a></summary>

DL 10.3 requires plugin inheriting from DeadlinePlugin to call super's **init** explicitly.


___

</details>


<details>
<summary>Nuke: fixing thumbnail and monitor out root attributes <a href="https://github.com/ynput/OpenPype/pull/5483">#5483</a></summary>

Nuke Root Colorspace settings for Thumbnail and Monitor Out schema was gradually changed between version 12, 13, 14 and we needed to address those changes individually for particular version.


___

</details>


<details>
<summary>Nuke: fixing missing `instance_id` error <a href="https://github.com/ynput/OpenPype/pull/5484">#5484</a></summary>

Workfiles with Instances created in old publisher workflow were rising error during converting method since they were missing `instance_id` key introduced in new publisher workflow.


___

</details>


<details>
<summary>Nuke: existing frames validator is repairing render target <a href="https://github.com/ynput/OpenPype/pull/5486">#5486</a></summary>

Nuke is now correctly repairing render target after the existing frames validator finds missing frames and repair action is used.


___

</details>


<details>
<summary>added UE to extract burnins families <a href="https://github.com/ynput/OpenPype/pull/5487">#5487</a></summary>

This PR fixes missing burnins in reviewables when rendering from UE.
___

</details>


<details>
<summary>Harmony: refresh code for current Deadline <a href="https://github.com/ynput/OpenPype/pull/5493">#5493</a></summary>

- Added support in Deadline Plug-in for new versions of Harmony, in particular version 21 and 22.
- Remove review=False flag on render instance
- Add farm=True flag on render instance
- Fix is_in_tests function call in Harmony Deadline submission plugin
- Force HarmonyOpenPype.py Deadline Python plug-in to py3
- Fix cosmetics/hound in HarmonyOpenPype.py Deadline Python plug-in


___

</details>


<details>
<summary>Publisher: Fix multiselection value <a href="https://github.com/ynput/OpenPype/pull/5505">#5505</a></summary>

Selection of multiple instances in Publisher does not cause that all instances change all publish attributes to the same value.


___

</details>


<details>
<summary>Publisher: Avoid warnings on thumbnails if source image also has alpha channel <a href="https://github.com/ynput/OpenPype/pull/5510">#5510</a></summary>

Avoids the following warning from `ExtractThumbnailFromSource`:
```
// pyblish.ExtractThumbnailFromSource : oiiotool WARNING: -o : Can't save 4 channels to jpeg... saving only R,G,B
```



___

</details>


<details>
<summary>Update ayon-python-api <a href="https://github.com/ynput/OpenPype/pull/5512">#5512</a></summary>

Update ayon python api and related callbacks.


___

</details>


<details>
<summary>Max: Fixing the bug of falling back to use workfile for Arnold or any renderers except Redshift <a href="https://github.com/ynput/OpenPype/pull/5520">#5520</a></summary>

Fix the bug of falling back to use workfile for Arnold


___

</details>


<details>
<summary>General: Fix Validate Publish Dir Validator <a href="https://github.com/ynput/OpenPype/pull/5534">#5534</a></summary>

Nonsensical "family" key was used instead of real value (as 'render' etc.) which would result in wrong translation of intermediate family names.Updated docstring.


___

</details>


<details>
<summary>have the addons loading respect a custom AYON_ADDONS_DIR <a href="https://github.com/ynput/OpenPype/pull/5539">#5539</a></summary>

When using a custom AYON_ADDONS_DIR environment variable that variable is used in the launcher correctly and downloads and extracts addons to there, however when running Ayon does not respect this environment variable


___

</details>


<details>
<summary>Deadline: files on representation cannot be single item list <a href="https://github.com/ynput/OpenPype/pull/5545">#5545</a></summary>

Further logic expects that single item files will be only 'string' not 'list' (eg. repre["files"] = "abc.exr" not repre["files"] = ["abc.exr"].This would cause an issue in ExtractReview later.This could happen if DL rendered single frame file with different frame value.


___

</details>


<details>
<summary>Webpublisher: better encode list values for click <a href="https://github.com/ynput/OpenPype/pull/5546">#5546</a></summary>

Targets could be a list, original implementation pushed it as a separate items, it must be added as `--targets webpulish --targets filepublish`.`wepublish_routes` handles triggering from UI, changes in `publish_functions` handle triggering from cmd (for tests, api access).


___

</details>


<details>
<summary>Houdini: Introduce imprint function for correct version in hda loader <a href="https://github.com/ynput/OpenPype/pull/5548">#5548</a></summary>

Resolve #5478


___

</details>


<details>
<summary>AYON: Fill entities during editorial (2) <a href="https://github.com/ynput/OpenPype/pull/5549">#5549</a></summary>

Fix changes made in https://github.com/ynput/OpenPype/pull/5475.


___

</details>


<details>
<summary>Max: OP Data updates in Loaders <a href="https://github.com/ynput/OpenPype/pull/5563">#5563</a></summary>

Fix the bug on the loaders not being able to load the objects when iterating key and values with the dict.Max prefers list over the list in dict.


___

</details>


<details>
<summary>Create Plugins: Better check of overriden '__init__' method <a href="https://github.com/ynput/OpenPype/pull/5571">#5571</a></summary>

Create plugins do not log warning messages about each create plugin because of wrong `__init__` method check.


___

</details>

### **Merged pull requests**


<details>
<summary>Tests: fix unit tests <a href="https://github.com/ynput/OpenPype/pull/5533">#5533</a></summary>

Fixed failing tests.Updated Unreal's validator to match removed general one which had a couple of issues fixed.


___

</details>




## [3.16.4](https://github.com/ynput/OpenPype/tree/3.16.4)


[Full Changelog](https://github.com/ynput/OpenPype/compare/3.16.3...3.16.4)

### **🆕 New features**


<details>
<summary>Feature: Download last published workfile specify version <a href="https://github.com/ynput/OpenPype/pull/4998">#4998</a></summary>

Setting `workfile_version` key to hook's `self.launch_context.data` allow you to specify the workfile version you want sync service to download if none is matched locally. This is helpful if the last version hasn't been correctly published/synchronized, and you want to recover the previous one (or some you'd like).Version could be set in two ways:
- OP's absolute version, matching the `version` index in DB.
- Relative version in reverse order from the last one: `-2`, `-3`...I don't know where I should write documentation about that.


___

</details>

### **🚀 Enhancements**


<details>
<summary>Maya: allow not creation of group for Import loaders <a href="https://github.com/ynput/OpenPype/pull/5427">#5427</a></summary>

This PR enhances previous one. All ReferenceLoaders could not wrap imported products into explicit group.Also `Import` Loaders have same options. Control for this is separate in Settings, eg. Reference might wrap loaded items in group, `Import` might not.


___

</details>


<details>
<summary>3dsMax: Settings for Ayon <a href="https://github.com/ynput/OpenPype/pull/5388">#5388</a></summary>

Max Addon Setting for Ayon


___

</details>


<details>
<summary>General: Navigation to Folder from Launcher <a href="https://github.com/ynput/OpenPype/pull/5404">#5404</a></summary>

Adds an action in launcher to open the directory of the asset.


___

</details>


<details>
<summary>Chore: Default variant in create plugin  <a href="https://github.com/ynput/OpenPype/pull/5429">#5429</a></summary>

Attribute `default_variant` on create plugins always returns string and if default variant is not filled other ways how to get one are implemented.


___

</details>


<details>
<summary>Publisher: Thumbnail widget enhancements <a href="https://github.com/ynput/OpenPype/pull/5439">#5439</a></summary>

Thumbnails widget in Publisher has new 3 options to choose from: Paste (from clipboard), Take screenshot and Browse. Clear button and new options are not visible by default, user must expand options button to show them.


___

</details>


<details>
<summary>AYON: Update ayon api to '0.3.5' <a href="https://github.com/ynput/OpenPype/pull/5460">#5460</a></summary>

Updated ayon-python-api to 0.3.5.


___

</details>

### **🐛 Bug fixes**


<details>
<summary>AYON: Apply unknown ayon settings first <a href="https://github.com/ynput/OpenPype/pull/5435">#5435</a></summary>

Settings of custom addons are available in converted settings.


___

</details>


<details>
<summary>Maya: Fix wrong subset name of render family in deadline <a href="https://github.com/ynput/OpenPype/pull/5442">#5442</a></summary>

New Publisher is creating different subset names than previously which resulted in duplication of `render` string in final subset name of `render` family published on Deadline.This PR solves that, it also fixes issues with legacy instances from old publisher, it matches the subset name as was before.This solves same issue in Max implementation.


___

</details>


<details>
<summary>Maya: Fix setting of version to workfile instance <a href="https://github.com/ynput/OpenPype/pull/5452">#5452</a></summary>

If there are multiple instances of renderlayer published, previous logic resulted in unpredictable rewrite of instance family to 'workfile' if `Sync render version with workfile` was on.


___

</details>


<details>
<summary>Maya: Context plugin shouldn't be tied to family <a href="https://github.com/ynput/OpenPype/pull/5464">#5464</a></summary>

`Maya Current File` collector was tied to `workfile` unnecessary. It should run even if `workile` instance is not being published.


___

</details>


<details>
<summary>Unreal: Fix loading hero version for static and skeletal meshes <a href="https://github.com/ynput/OpenPype/pull/5393">#5393</a></summary>

Fixed a problem with loading hero versions for static ans skeletal meshes.


___

</details>


<details>
<summary>TVPaint: Fix 'repeat' behavior <a href="https://github.com/ynput/OpenPype/pull/5412">#5412</a></summary>

Calculation of frames for repeat behavior is working correctly.


___

</details>


<details>
<summary>AYON: Thumbnails cache and api prep <a href="https://github.com/ynput/OpenPype/pull/5437">#5437</a></summary>

Moved thumbnails cache from ayon python api to OpenPype and prepare AYON thumbnail resolver for new api functions. Current implementation should work with old and new ayon-python-api.


___

</details>


<details>
<summary>Nuke: Name of the Read Node should be updated correctly when switching versions or assets. <a href="https://github.com/ynput/OpenPype/pull/5444">#5444</a></summary>

Bug fixing of the read node's name not being updated correctly when setting version or switching asset.


___

</details>


<details>
<summary>Farm publishing: asymmetric handles fixed <a href="https://github.com/ynput/OpenPype/pull/5446">#5446</a></summary>

Handles are now set correctly on farm published product version if asymmetric were set to shot attributes.


___

</details>


<details>
<summary>Scene Inventory: Provider icons fix <a href="https://github.com/ynput/OpenPype/pull/5450">#5450</a></summary>

Fix how provider icons are accessed in scene inventory.


___

</details>


<details>
<summary>Fix typo on Deadline OP plugin name <a href="https://github.com/ynput/OpenPype/pull/5453">#5453</a></summary>

Surprised that no one has hit this bug yet... but it seems like there was a typo on the name of the OP Deadline plugin when submitting jobs to it.


___

</details>


<details>
<summary>AYON: Fix version attributes update <a href="https://github.com/ynput/OpenPype/pull/5472">#5472</a></summary>

Fixed updates of attribs in AYON mode.


___

</details>

### **Merged pull requests**


<details>
<summary>Added missing defaults for import_loader <a href="https://github.com/ynput/OpenPype/pull/5447">#5447</a></summary>


___

</details>


<details>
<summary>Bug: Local settings don't open on 3.14.7  <a href="https://github.com/ynput/OpenPype/pull/5220">#5220</a></summary>

### Before posting a new ticket, have you looked through the documentation to find an answer?

Yes I have

### Have you looked through the existing tickets to find any related issues ?

Not yet

### Author of the bug

@FadyFS

### Version

3.15.11-nightly.3

### What platform you are running OpenPype on?

Linux / Centos

### Current Behavior:

the previous behavior (bug) : 
![image](https://github.com/quadproduction/OpenPype/assets/135602303/09bff9d5-3f8b-4339-a1e5-30c04ade828c)


### Expected Behavior:

![image](https://github.com/quadproduction/OpenPype/assets/135602303/c505a103-7965-4796-bcdf-73bcc48a469b)


### What type of bug is it ?

Happened only once in a particular configuration

### Which project / workfile / asset / ...

open settings with 3.14.7 

### Steps To Reproduce:

1. Run openpype on the 3.15.11-nightly.3 version 
2. Open settings in 3.14.7 version

### Relevant log output:

_No response_

### Additional context:

_No response_

___

</details>


<details>
<summary>Tests: Add automated targets for tests <a href="https://github.com/ynput/OpenPype/pull/5443">#5443</a></summary>

Without it plugins with 'automated' targets won't be triggered (eg `CloseAE` etc.)


___

</details>




## [3.16.3](https://github.com/ynput/OpenPype/tree/3.16.3)


[Full Changelog](https://github.com/ynput/OpenPype/compare/3.16.2...3.16.3)

### **🆕 New features**


<details>
<summary>AYON: 3rd party addon usage <a href="https://github.com/ynput/OpenPype/pull/5300">#5300</a></summary>

Prepare OpenPype code to be able use `ayon-third-party` addon which supply ffmpeg and OpenImageIO executables. Because they both can support to define custom arguments (more than one) a new functions were needed to supply.New functions are `get_ffmpeg_tool_args` and `get_oiio_tool_args`. They work similar to previous but instead of string are returning list of strings. All places using previous functions `get_ffmpeg_tool_path` and `get_oiio_tool_path` are now using new ones. They should be backwards compatible and even with addon if returns single argument.


___

</details>


<details>
<summary>AYON: Addon settings in OpenPype <a href="https://github.com/ynput/OpenPype/pull/5347">#5347</a></summary>

Moved settings addons to OpenPype server addon. Modified create package to create zip files for server for each settings addon and for openpype addon.


___

</details>


<details>
<summary>AYON: Add folder to template data <a href="https://github.com/ynput/OpenPype/pull/5417">#5417</a></summary>

Added `folder` to template data, so `{folder[name]}` can be used in templates.


___

</details>


<details>
<summary>Option to start versioning from 0 <a href="https://github.com/ynput/OpenPype/pull/5262">#5262</a></summary>

This PR adds a settings option to start all versioning from 0.This PR will replace #4455.


___

</details>


<details>
<summary>Ayon: deadline implementation <a href="https://github.com/ynput/OpenPype/pull/5321">#5321</a></summary>

Quick implementation of deadline in Ayon. New Ayon plugin added for Deadline repository


___

</details>


<details>
<summary>AYON: Remove AYON launch logic from OpenPype <a href="https://github.com/ynput/OpenPype/pull/5348">#5348</a></summary>

Removed AYON launch logic from OpenPype. The logic is outdated at this moment and is replaced by `ayon-launcher`.


___

</details>

### **🚀 Enhancements**


<details>
<summary>Bug: Error on multiple instance rig with maya <a href="https://github.com/ynput/OpenPype/pull/5310">#5310</a></summary>

I change endswith method by startswith method because the set are automacaly name out_SET, out_SET1, out_SET2 ...


___

</details>


<details>
<summary>Applications: Use prelaunch hooks to extract environments <a href="https://github.com/ynput/OpenPype/pull/5387">#5387</a></summary>

Environment variable preparation is based on prelaunch hooks. This should allow to pass OCIO environment variables to farm jobs.


___

</details>


<details>
<summary>Applications: Launch hooks cleanup <a href="https://github.com/ynput/OpenPype/pull/5395">#5395</a></summary>

Use `set` instead of `list` for filtering attributes in launch hooks. Celaction hooks dir does not contain `__init__.py`. Celaction prelaunch hook is reusing `CELACTION_ROOT_DIR`. Launch hooks are using full import from `openpype.lib.applications`.


___

</details>


<details>
<summary>Applications: Environment variables order <a href="https://github.com/ynput/OpenPype/pull/5245">#5245</a></summary>

Changed order of set environment variables. First are set context environment variables and then project environment overrides. Also asset and task environemnt variables are optional.


___

</details>


<details>
<summary>Autosave preferences can be read after Nuke opens the script <a href="https://github.com/ynput/OpenPype/pull/5295">#5295</a></summary>

Looks like I need to open the script in Nuke to be able to correctly load the autosave preferences.This PR reads the Nuke script in context, and offers owerwriting the current script with autosaved one if autosave exists.


___

</details>


<details>
<summary>Resolve: Update with compatible resolve version and latest docs <a href="https://github.com/ynput/OpenPype/pull/5317">#5317</a></summary>

Missing information about compatible Resolve version and latest docs from https://github.com/ynput/OpenPype/tree/develop/openpype/hosts/resolve


___

</details>


<details>
<summary>Chore: Remove deprecated functions <a href="https://github.com/ynput/OpenPype/pull/5323">#5323</a></summary>

Removed functions/classes that are deprecated and marked to be removed.


___

</details>


<details>
<summary>Nuke Render and Prerender nodes Process Order - OP-3555 <a href="https://github.com/ynput/OpenPype/pull/5332">#5332</a></summary>

This PR exposes control over the order of processing of the instances, by sorting the instances created. The sorting happens on the `render_order` and subset name. If the knob `render_order` is found on the instance, we'll sort by that first before sorting by subset name.`render_order` instances are processed before nodes without `render_order`. This could be extended in the future by querying other knobs but I dont know of a usecase for this.Hardcoded the creator `order` attribute of the `prerender` class to be before the `render`. Could be exposed to the user/studio but dont know of a use case for this.


___

</details>


<details>
<summary>Unreal: Python Environment Improvements <a href="https://github.com/ynput/OpenPype/pull/5344">#5344</a></summary>

Automatically set `UE_PYTHONPATH` as `PYTHONPATH` when launching Unreal.


___

</details>


<details>
<summary>Unreal: Custom location for Unreal Ayon Plugin <a href="https://github.com/ynput/OpenPype/pull/5346">#5346</a></summary>

Added a new environment variable `AYON_BUILT_UNREAL_PLUGIN` to set an already existing and built Ayon Plugin for Unreal.


___

</details>


<details>
<summary>Unreal: Better handling of Exceptions in UE Worker threads <a href="https://github.com/ynput/OpenPype/pull/5349">#5349</a></summary>

Implemented a new `UEWorker` base class to handle exception during the execution of UE Workers.


___

</details>


<details>
<summary>Houdini: Add farm toggle on creation menu <a href="https://github.com/ynput/OpenPype/pull/5350">#5350</a></summary>

Deadline Farm publishing and Rendering for Houdini was possible with this PR #4825 farm publishing is enabled by default some ROP nodes which may surprise new users (like me).I think adding a toggle (on by default) on creation UI is better so that users will be aware that there's a farm option for this publish instance.ROPs Modified :
- [x] Mantra ROP
- [x] Karma ROP
- [x] Arnold ROP
- [x] Redshift ROP
- [x] Vray ROP


___

</details>


<details>
<summary>Ftrack: Sync to avalon settings <a href="https://github.com/ynput/OpenPype/pull/5353">#5353</a></summary>

Added roles settings for sync to avalon action.


___

</details>


<details>
<summary>Chore: Schemas inside OpenPype <a href="https://github.com/ynput/OpenPype/pull/5354">#5354</a></summary>

Moved/copied schemas from repository root inside openpype/pipeline.


___

</details>


<details>
<summary>AYON: Addons creation enhancements <a href="https://github.com/ynput/OpenPype/pull/5356">#5356</a></summary>

Enhanced AYON addons creation. Fix issue with `Pattern` typehint. Zip filenames contain version. OpenPype package is skipping modules that are already separated in AYON. Updated settings of addons.


___

</details>


<details>
<summary>AYON: Update staging icons <a href="https://github.com/ynput/OpenPype/pull/5372">#5372</a></summary>

Updated staging icons for staging mode.


___

</details>


<details>
<summary>Enhancement: Houdini Update pointcache labels <a href="https://github.com/ynput/OpenPype/pull/5373">#5373</a></summary>

To me it's logical to find pointcaches types listed one after another, but they were named differentlySo, I made this PR to update their labels


___

</details>


<details>
<summary>nuke: split write node product instance features <a href="https://github.com/ynput/OpenPype/pull/5389">#5389</a></summary>

Improving Write node product instances by allowing precise activation of specific features.


___

</details>


<details>
<summary>Max: Use the empty modifiers in container to store AYON Parameter <a href="https://github.com/ynput/OpenPype/pull/5396">#5396</a></summary>

Instead of adding AYON/OP Parameter along with other attributes inside the container, empty modifiers would be created to store AYON/OP custom attributes


___

</details>


<details>
<summary>AfterEffects: Removed unused imports <a href="https://github.com/ynput/OpenPype/pull/5397">#5397</a></summary>

Removed unused import from extract local render plugin file.


___

</details>


<details>
<summary>Nuke: adding BBox knob type to settings <a href="https://github.com/ynput/OpenPype/pull/5405">#5405</a></summary>

Nuke knob types in settings having new `Box` type for reposition nodes like Crop or Reformat.


___

</details>


<details>
<summary>SyncServer: Existence of module is optional <a href="https://github.com/ynput/OpenPype/pull/5413">#5413</a></summary>

Existence of SyncServer module is optional and not required. Added `sync_server` module back to ignored modules when openpype addon is created for AYON. Command `syncserver` is marked as deprecated and redirected to sync server cli.


___

</details>


<details>
<summary>Webpublisher: Self contain test publish logic <a href="https://github.com/ynput/OpenPype/pull/5414">#5414</a></summary>

Moved test logic of publishing to webpublisher. Simplified `remote_publish` to remove webpublisher specific logic.


___

</details>


<details>
<summary>Webpublisher: Cleanup targets <a href="https://github.com/ynput/OpenPype/pull/5418">#5418</a></summary>

Removed `remote` target from webpublisher and replaced it with 2 targets `webpublisher` and `automated`.


___

</details>


<details>
<summary>nuke: update server addon settings with box <a href="https://github.com/ynput/OpenPype/pull/5419">#5419</a></summary>

updtaing nuke ayon server settings for Box option in knob types.


___

</details>

### **🐛 Bug fixes**


<details>
<summary>Maya: fix validate frame range on review attached to other instances <a href="https://github.com/ynput/OpenPype/pull/5296">#5296</a></summary>

Fixes situation where frame range validator can't be turned off on models if they are attached to reviewable camera in Maya.


___

</details>


<details>
<summary>Maya: Apply project settings to creators <a href="https://github.com/ynput/OpenPype/pull/5303">#5303</a></summary>

Project settings were not applied to the creators.


___

</details>


<details>
<summary>Maya: Validate Model Content <a href="https://github.com/ynput/OpenPype/pull/5336">#5336</a></summary>

`assemblies` in `cmds.ls` does not seem to work;
```python

from maya import cmds


content_instance = ['|group2|pSphere1_GEO', '|group2|pSphere1_GEO|pSphere1_GEOShape', '|group1|pSphere1_GEO', '|group1|pSphere1_GEO|pSphere1_GEOShape']
assemblies = cmds.ls(content_instance, assemblies=True, long=True)
print(assemblies)
```

Fixing with string splitting instead.


___

</details>


<details>
<summary>Bugfix: Maya update defaults variable <a href="https://github.com/ynput/OpenPype/pull/5368">#5368</a></summary>

So, something was forgotten while moving out from `LegacyCreator` to `NewCreator``LegacyCreator` used `defaults` to list suggested subset names which was changed into `default_variants` in the the `NewCreator`and setting `defaults` to any values has no effect!This update affects:
- [x] Model
- [x] Set Dress


___

</details>


<details>
<summary>Chore: Python 2 support fix <a href="https://github.com/ynput/OpenPype/pull/5375">#5375</a></summary>

Fix Python 2 support by adding `click` into python 2 dependencies and removing f-string from maya.


___

</details>


<details>
<summary>Maya: do not create top level group on reference <a href="https://github.com/ynput/OpenPype/pull/5402">#5402</a></summary>

This PR allows to not wrapping loaded referenced assets in top level group either explicitly for artist or by configuration in Settings.Artists can control group creation in ReferenceLoader options.Default no group creation could be set by emptying `Group Name` in `project_settings/maya/load/reference_loader`


___

</details>


<details>
<summary>Settings: Houdini & Maya create plugin settings <a href="https://github.com/ynput/OpenPype/pull/5436">#5436</a></summary>

Fixes related to Maya and Houdini settings. Renamed `defaults` to `default_variants` in plugin settings to match attribute name on create plugin in both OpenPype and AYON settings. Fixed Houdini AYON settings where were missing settings for defautlt varaints and fixed Maya AYON settings where default factory had wrong assignment.


___

</details>


<details>
<summary>Maya: Hide CreateAnimation <a href="https://github.com/ynput/OpenPype/pull/5297">#5297</a></summary>

When converting `animation` family or loading a `rig` family, need to include the `animation` creator but hide it in creator context.


___

</details>


<details>
<summary>Nuke Anamorphic slate - Read pixel aspect from input <a href="https://github.com/ynput/OpenPype/pull/5304">#5304</a></summary>

When asset pixel aspect differs from rendered pixel aspect, Nuke slate pixel aspect is not longer taken from asset, but is readed via ffprobe.


___

</details>


<details>
<summary>Nuke - Allow ExtractReviewDataMov with no timecode knob <a href="https://github.com/ynput/OpenPype/pull/5305">#5305</a></summary>

ExtractReviewDataMov allows to specify file type. Trying to write some other extension than mov fails on generate_mov assuming that mov64_write_timecode knob exists.


___

</details>


<details>
<summary>Nuke: removing settings schema with defaults for OpenPype <a href="https://github.com/ynput/OpenPype/pull/5306">#5306</a></summary>

continuation of https://github.com/ynput/OpenPype/pull/5275


___

</details>


<details>
<summary>Bugfix: Dependency without 'inputLinks' not downloaded <a href="https://github.com/ynput/OpenPype/pull/5337">#5337</a></summary>

Remove condition that avoids downloading dependency without `inputLinks`.


___

</details>


<details>
<summary>Bugfix: Houdini Creator use selection even if it was toggled off <a href="https://github.com/ynput/OpenPype/pull/5359">#5359</a></summary>

When creating many product types (families) one after another without refreshing the creator window manually if you toggled `Use selection` once, all the later product types will use selection even if it was toggled offHere's Before it will keep use selection even if it was toggled off, unless you refresh window manuallyhttps://github.com/ynput/OpenPype/assets/20871534/8b890122-5b53-4c6b-897d-6a2f3aa3388aHere's After it works as expectedhttps://github.com/ynput/OpenPype/assets/20871534/6b1db990-de1b-428e-8828-04ab59a44e28


___

</details>


<details>
<summary>Houdini: Correct camera selection for karma renderer when using selected node <a href="https://github.com/ynput/OpenPype/pull/5360">#5360</a></summary>

When user creates the karma rop with selected camera by use selection, it will give the error message of "no render camera found in selection".This PR is to fix the bug of creating karma rop when using selected camera node in Houdini


___

</details>


<details>
<summary>AYON: Environment variables and functions <a href="https://github.com/ynput/OpenPype/pull/5361">#5361</a></summary>

Prepare code for ayon-launcher compatibility. Fix ayon launcher subprocess calls, added more checks for `AYON_SERVER_ENABLED`, use ayon launcher suitable environment variables in AYON mode and changed outputs of some functions. Replaced usages of `OPENPYPE_REPOS_ROOT` environment variable with `PACKAGE_DIR` variable -> correct paths are used.


___

</details>


<details>
<summary>Nuke: farm rendering of prerender ignore roots in nuke <a href="https://github.com/ynput/OpenPype/pull/5366">#5366</a></summary>

`prerender` family was using wrong subset, same as `render` which should be different.


___

</details>


<details>
<summary>Bugfix: Houdini update defaults variable <a href="https://github.com/ynput/OpenPype/pull/5367">#5367</a></summary>

So, something was forgotten while moving out from `LegacyCreator` to `NewCreator``LegacyCreator` used `defaults` to list suggested subset names which was changed into `default_variants` in the the `NewCreator`and setting `defaults` to any values has no effect!This update affects:
- [x] Arnold ASS
- [x] Arnold ROP
- [x] Karma ROP
- [x] Mantra ROP
- [x] Redshift ROP
- [x] VRay ROP


___

</details>


<details>
<summary>Publisher: Fix create/publish animation <a href="https://github.com/ynput/OpenPype/pull/5369">#5369</a></summary>

Use geometry movement instead of changing min/max width.


___

</details>


<details>
<summary>Unreal: Move unreal splash screen to unreal <a href="https://github.com/ynput/OpenPype/pull/5370">#5370</a></summary>

Moved splash screen code to unreal integration and removed import from Igniter.


___

</details>


<details>
<summary>Nuke: returned not cleaning of renders folder on the farm <a href="https://github.com/ynput/OpenPype/pull/5374">#5374</a></summary>

Previous PR enabled explicit cleanup of `renders` folder after farm publishing. This is not matching customer's workflows. Customer wants to have access to files in `renders` folder and potentially redo some frames for long frame sequences.This PR extends logic of marking rendered files for deletion only if instance doesn't have `stagingDir_persistent`.For backwards compatibility all Nuke instances have `stagingDir_persistent` set to True, eg. `renders` folder won't be cleaned after farm publish.


___

</details>


<details>
<summary>Nuke: loading sequences is working <a href="https://github.com/ynput/OpenPype/pull/5376">#5376</a></summary>

Loading image sequences was broken after the latest release, version 3.16. However, I am pleased to inform you that it is now functioning as expected.


___

</details>


<details>
<summary>AYON: Fix settings conversion for ayon addons <a href="https://github.com/ynput/OpenPype/pull/5377">#5377</a></summary>

AYON addon settings are available in system settings and does not have available the same values in `"modules"` subkey.


___

</details>


<details>
<summary>Nuke: OCIO env var workflow <a href="https://github.com/ynput/OpenPype/pull/5379">#5379</a></summary>

The OCIO environment variable needs to be consistently handled across all platforms. Nuke resolves the custom OCIO config path differently depending on the platform, so we included the ocio config path in the workfile with a partial replacement using an environment variable. Additionally, for Windows sessions, we replaced backward slashes with a TCL expression.


___

</details>


<details>
<summary>Unreal: Fix Unreal build script <a href="https://github.com/ynput/OpenPype/pull/5381">#5381</a></summary>

Define 'AYON_UNREAL_ROOT' environment variable in unreal addon.


___

</details>


<details>
<summary>3dsMax: Use relative path to MAX_HOST_DIR <a href="https://github.com/ynput/OpenPype/pull/5382">#5382</a></summary>

Use `MAX_HOST_DIR` to calculate startup script path instead of use relative path to `OPENPYPE_ROOT` environment variable.


___

</details>


<details>
<summary>Bugfix: Houdini abc validator error message <a href="https://github.com/ynput/OpenPype/pull/5386">#5386</a></summary>

When ABC path validator fails, it prints node objects not node paths or namesThis bug happened because of updating `get_invalid` method to return nodes instead of node pathsBeforeAfter


___

</details>


<details>
<summary>Nuke: node name influence product (subset) name <a href="https://github.com/ynput/OpenPype/pull/5392">#5392</a></summary>

Nuke now allows users to duplicate publishing instances, making the workflow easier. By duplicating a node and changing its name, users can set the product (subset) name in the publishing context.Users now have the ability to change the variant name in Publisher, which will automatically rename the associated instance node.


___

</details>


<details>
<summary>Houdini: delete redundant bgeo sop validator <a href="https://github.com/ynput/OpenPype/pull/5394">#5394</a></summary>

I found out that this `Validate BGEO SOP Path` validator is redundant, it catches two cases that are already implemented in "Validate Output Node". "Validate Output Node" works with `bgeo` as well as `abc` because `"pointcache"` is listed in its families


___

</details>


<details>
<summary>Nuke: workfile is not reopening after change of context <a href="https://github.com/ynput/OpenPype/pull/5399">#5399</a></summary>

Nuke no longer reopens the latest workfile when the context is changed to a different task using the Workfile tool. The issue also affected the Script Clean (from Nuke File menu) and Close feature, but it has now been fixed.


___

</details>


<details>
<summary>Bugfix: houdini hard coded project settings <a href="https://github.com/ynput/OpenPype/pull/5400">#5400</a></summary>

I made this PR to solve the issue with hard-coded settings in houdini


___

</details>


<details>
<summary>AYON: 3dsMax settings <a href="https://github.com/ynput/OpenPype/pull/5401">#5401</a></summary>

Keep `adsk_3dsmax` group in applications settings.


___

</details>


<details>
<summary>Bugfix: update defaults to default_variants in maya and houdini OP DCC settings <a href="https://github.com/ynput/OpenPype/pull/5407">#5407</a></summary>

On moving out to new creator in Maya and Houdini updating settings was missed.


___

</details>


<details>
<summary>Applications: Attributes creation <a href="https://github.com/ynput/OpenPype/pull/5408">#5408</a></summary>

Applications addon does not cause infinite server restart loop.


___

</details>


<details>
<summary>Max: fix the bug of handling Object deletion in OP Parameter <a href="https://github.com/ynput/OpenPype/pull/5410">#5410</a></summary>

If the object is added to the OP parameter and user delete it in the scene thereafter, it will error out the container with OP attributes. This PR resolves the bug.This PR also fixes the bug of not adding the attribute into OP parameter correctly when the user enables "use selections" to link the object into the OP parameter.


___

</details>


<details>
<summary>Colorspace: including environments from launcher process <a href="https://github.com/ynput/OpenPype/pull/5411">#5411</a></summary>

Fixed bug in GitHub PR where the OCIO config template was not properly formatting environment variables from System Settings `general/environment`.


___

</details>


<details>
<summary>Nuke: workfile template fixes <a href="https://github.com/ynput/OpenPype/pull/5428">#5428</a></summary>

Some bunch of small bugs needed to be fixed


___

</details>


<details>
<summary>Houdini, Max: Fix missed function interface change <a href="https://github.com/ynput/OpenPype/pull/5430">#5430</a></summary>

This PR https://github.com/ynput/OpenPype/pull/5321/files from @kalisp missed updating the `add_render_job_env_var` in Houdini and Max as they are passing an extra arg:
```
TypeError: add_render_job_env_var() takes 1 positional argument but 2 were given
```


___

</details>


<details>
<summary>Scene Inventory: Fix issue with 'sync_server' <a href="https://github.com/ynput/OpenPype/pull/5431">#5431</a></summary>

Fix accesss to `sync_server` attribute in scene inventory.


___

</details>


<details>
<summary>Unpack project: Fix import issue <a href="https://github.com/ynput/OpenPype/pull/5433">#5433</a></summary>

Added `load_json_file`, `replace_project_documents` and `store_project_documents` to mongo init.


___

</details>


<details>
<summary>Chore: Versions post fixes <a href="https://github.com/ynput/OpenPype/pull/5441">#5441</a></summary>

Fixed issues caused by my fault. Filled right version value to anatomy data.


___

</details>

### **📃 Testing**


<details>
<summary>Tests: Copy file_handler as it will be removed by purging ayon code <a href="https://github.com/ynput/OpenPype/pull/5357">#5357</a></summary>

Ayon code will get purged in the future from this repo/addon, therefore all `ayon_common` will be gone. `file_handler` gets internalized to tests as it is not used anywhere else.


___

</details>




## [3.16.2](https://github.com/ynput/OpenPype/tree/3.16.2)


[Full Changelog](https://github.com/ynput/OpenPype/compare/3.16.1...3.16.2)

### **🆕 New features**


<details>
<summary>Fusion - Set selected tool to active <a href="https://github.com/ynput/OpenPype/pull/5327">#5327</a></summary>

When you run the action to select a node, this PR makes the node-flow show the selected node + you'll see the nodes controls in the inspector.


___

</details>

### **🚀 Enhancements**


<details>
<summary>Maya: All base create plugins <a href="https://github.com/ynput/OpenPype/pull/5326">#5326</a></summary>

Prepared base classes for each creator type in Maya. Extended `MayaCreatorBase` to have default implementations of common logic with instances which is used in each type of plugin.


___

</details>


<details>
<summary>Windows: Support long paths on zip updates. <a href="https://github.com/ynput/OpenPype/pull/5265">#5265</a></summary>

Support long paths for version extract on Windows.Use case is when having long paths in for example an addon. You can install to the C drive but because the zip files are extracted in the local users folder, it'll add additional sub directories to the paths and quickly get too long paths for Windows to handle the zip updates.


___

</details>


<details>
<summary>Blender: Added setting to set resolution and start/end frames at startup <a href="https://github.com/ynput/OpenPype/pull/5338">#5338</a></summary>

This PR adds `set_resolution_startup`and `set_frames_startup` settings. They automatically set respectively the resolution and start/end frames and FPS in Blender when opening a file or creating a new one.


___

</details>


<details>
<summary>Blender: Support for ExtractBurnin <a href="https://github.com/ynput/OpenPype/pull/5339">#5339</a></summary>

This PR adds support for ExtractBurnin for Blender, when publishing a Review.


___

</details>


<details>
<summary>Blender: Extract Camera as Alembic <a href="https://github.com/ynput/OpenPype/pull/5343">#5343</a></summary>

Added support to extract Alembic Cameras in Blender.


___

</details>

### **🐛 Bug fixes**


<details>
<summary>Maya: Validate Instance In Context <a href="https://github.com/ynput/OpenPype/pull/5335">#5335</a></summary>

Missing new publisher error so the repair action shows up.


___

</details>


<details>
<summary>Settings: Fix default settings <a href="https://github.com/ynput/OpenPype/pull/5311">#5311</a></summary>

Fixed defautl settings for shotgrid. Renamed `FarmRootEnumEntity` to `DynamicEnumEntity` and removed doubled ABC metaclass definition (all settings entities have abstract metaclass).


___

</details>


<details>
<summary>Deadline: missing context argument <a href="https://github.com/ynput/OpenPype/pull/5312">#5312</a></summary>

Updated function arguments


___

</details>


<details>
<summary>Qt UI: Multiselection combobox PySide6 compatibility <a href="https://github.com/ynput/OpenPype/pull/5314">#5314</a></summary>

- The check states are replaced with the values for PySide6
- `QtCore.Qt.ItemIsUserTristate` is used instead of `QtCore.Qt.ItemIsTristate` to avoid crashes on PySide6


___

</details>


<details>
<summary>Docker: handle openssl 1.1.1 for centos 7 docker build <a href="https://github.com/ynput/OpenPype/pull/5319">#5319</a></summary>

Move to python 3.9 has added need to use openssl 1.1.x - but it is not by default available on centos 7 image. This is fixing it.


___

</details>


<details>
<summary>houdini: fix typo in redshift proxy <a href="https://github.com/ynput/OpenPype/pull/5320">#5320</a></summary>

I believe there's a typo in `create_redshift_proxy.py`   ( extra ` )  in filename, and I made this PR to suggest a fix


___

</details>


<details>
<summary>Houdini: fix wrong creator identifier in pointCache workflow <a href="https://github.com/ynput/OpenPype/pull/5324">#5324</a></summary>

FIxing a bug in publishing alembics, were invalid creator identifier caused missing family association.


___

</details>


<details>
<summary>Fix colorspace compatibility check <a href="https://github.com/ynput/OpenPype/pull/5334">#5334</a></summary>

for some reason a user may have `PyOpenColorIO` installed to his machine,  _in my case it came with renderman._it can trick the compatibility check as `import PyOpenColorIO` won't raise an error however it may be an old version _like my case_Beforecompatibility check was true and It used wrapper directly After Fix It will use wrapper via subprocess instead


___

</details>

### **Merged pull requests**


<details>
<summary>Remove forgotten dev logging <a href="https://github.com/ynput/OpenPype/pull/5315">#5315</a></summary>


___

</details>




## [3.16.1](https://github.com/ynput/OpenPype/tree/3.16.1)


[Full Changelog](https://github.com/ynput/OpenPype/compare/3.16.0...3.16.1)

### **🆕 New features**


<details>
<summary>Royal Render: Maya and Nuke support <a href="https://github.com/ynput/OpenPype/pull/5191">#5191</a></summary>

Basic working implementation of Royal Render support in Maya.It expects New publisher implemented in Maya.


___

</details>


<details>
<summary>Blender: Blend File Family <a href="https://github.com/ynput/OpenPype/pull/4321">#4321</a></summary>

<strong>Implementation of the Blend File family analogue to the Maya Scene one.

</strong>
___

</details>


<details>
<summary>Houdini: simple bgeo publishing <a href="https://github.com/ynput/OpenPype/pull/4588">#4588</a></summary>

<strong>Support for simple publishing of bgeo files.

</strong>This is adding basic support for bgeo publishing in Houdini. It will allow publishing bgeo in all supported formats (selectable in the creator options).  If selected node has `output` on sop level, it will be used automatically as path in file node.


___

</details>

### **🚀 Enhancements**


<details>
<summary>General: delivery action add renamed frame number in Loader <a href="https://github.com/ynput/OpenPype/pull/5024">#5024</a></summary>

Frame Offset options for delivery in Openpype loader


___

</details>


<details>
<summary>Enhancement/houdini add path action for abc validator <a href="https://github.com/ynput/OpenPype/pull/5237">#5237</a></summary>

Add a default path attribute Action.it's a helper action more than a repair action, which used to add a default single value.


___

</details>


<details>
<summary>Nuke: auto apply all settings after template build <a href="https://github.com/ynput/OpenPype/pull/5277">#5277</a></summary>

Adding auto run of Apply All Settings after template is builder is finishing its process. This will apply Frame-range, Image size, Colorspace found in context of a task shot.


___

</details>


<details>
<summary>Harmony:Removed loader settings for Harmony <a href="https://github.com/ynput/OpenPype/pull/5289">#5289</a></summary>

It shouldn't be configurable, it is internal logic. By adding additional extension it wouldn't start to work magically.


___

</details>

### **🐛 Bug fixes**


<details>
<summary>AYON: Make appdirs case sensitive <a href="https://github.com/ynput/OpenPype/pull/5298">#5298</a></summary>

Appdirs for AYON are case sensitive for linux and mac so we needed to change them to match ayon launcher. Changed 'ayon' to 'AYON' and 'ynput' to 'Ynput'.


___

</details>


<details>
<summary>Traypublisher: Fix plugin order <a href="https://github.com/ynput/OpenPype/pull/5299">#5299</a></summary>

Frame range collector for traypublisher was moved to traypublisher plugins and changed order to make sure `assetEntity` is filled in `instance.data`.


___

</details>


<details>
<summary>Deadline: removing OPENPYPE_VERSION from some host submitters <a href="https://github.com/ynput/OpenPype/pull/5302">#5302</a></summary>

Removing deprecated method of adding OPENPYPE_VERSION to job environment. It was leftover and other hosts have already been cleared.


___

</details>


<details>
<summary>AYON: Fix args for workfile conversion util <a href="https://github.com/ynput/OpenPype/pull/5308">#5308</a></summary>

Workfile update conversion util function have right expected arguments.


___

</details>

### **🔀 Refactored code**


<details>
<summary>Maya: Refactor imports to `lib.get_reference_node` since the other function… <a href="https://github.com/ynput/OpenPype/pull/5258">#5258</a></summary>

Refactor imports to `lib.get_reference_node` since the other function is deprecated.


___

</details>




## [3.16.0](https://github.com/ynput/OpenPype/tree/3.16.0)


[Full Changelog](https://github.com/ynput/OpenPype/compare/...3.16.0)

### **🆕 New features**


<details>
<summary>General: Reduce usage of legacy io <a href="https://github.com/ynput/OpenPype/pull/4723">#4723</a></summary>

Replace usages of `legacy_io` with getter methods or reuse already available information. Create plugins using CreateContext are using context from CreateContext object. Loaders are usign getter function from context tools. Publish plugin are using information instance.data or context.data. In some cases were pieces of code refactored a little e.g. fps getter in maya.


___

</details>


<details>
<summary>Documentation: API docs reborn - yet again <a href="https://github.com/ynput/OpenPype/pull/4419">#4419</a></summary>

## Feature

Add functional base for API Documentation using Sphinx and AutoAPI.

After unsuccessful #2512, #834 and #210 this is yet another try. But this time without ambition to solve the whole issue. This is making Shinx script to work and nothing else. Any changes and improvements in API docs should be made in subsequent PRs.

## How to use it

You can run:

```sh
cd .\docs
make.bat html
```

or

```sh
cd ./docs
make html
```

This will go over our code and generate **.rst** files in `/docs/source/autoapi` and from those it will generate full html documentation in `/docs/build/html`.

During the build you'll see tons of red errors that are pointing to our issues:

1) **Wrong imports**
    Invalid import are usually wrong relative imports (too deep) or circular imports.

2) **Invalid doc-strings**
   Doc-strings to be processed into documentation needs to follow some syntax - this can be checked by running
   `pydocstyle` that is already included with OpenPype
3) **Invalid markdown/rst files**
    md/rst files can be included inside rst files using `.. include::` directive. But they have to be properly formatted.


## Editing rst templates

Everything starts with `/docs/source/index.rst` - this file should be properly edited, Right now it just includes `readme.rst` that in turn include and parse main `README.md`. This is entrypoint to API documentation. All templates generated by AutoAPI are in `/docs/source/autoapi`. They should be eventually commited to repository and edited too.

## Steps for enhancing API documentation

1) Run `/docs/make.bat html`
2) Read the red errors/warnings - fix it in the code
3) Run `/docs/make.bat html` again until  there are not red lines
4) Edit rst files and add some meaningfull content there

> **Note**
> This can (should) be merged as is without doc-string fixes in the code or changes in templates. All additional improvements on API documentation should be made in new PRs.

> **Warning**
> You need to add new dependencies to use it. Run `create_venv`.

Connected to #2490
___

</details>


<details>
<summary>Global: custom location for OP local versions <a href="https://github.com/ynput/OpenPype/pull/4673">#4673</a></summary>

This provides configurable location to unzip Openpype version zips. By default, it was hardcoded to artist's app data folder, which might be problematic/slow with roaming profiles.Location must be accessible by user running OP Tray with write permissions (so `Program Files` might be problematic)


___

</details>


<details>
<summary>AYON: Update settings conversion <a href="https://github.com/ynput/OpenPype/pull/4837">#4837</a></summary>

Updated conversion script of AYON settings to v3 settings. PR is related to changes in addons repository https://github.com/ynput/ayon-addons/pull/6 . Changed how the conversion happens -> conversion output does not start with openpype defaults but as empty dictionary.


___

</details>


<details>
<summary>AYON: Implement integrate links publish plugin <a href="https://github.com/ynput/OpenPype/pull/4842">#4842</a></summary>

Implemented entity links get/create functions. Added new integrator which replaces v3 integrator for links.


___

</details>


<details>
<summary>General: Version attributes integration <a href="https://github.com/ynput/OpenPype/pull/4991">#4991</a></summary>

Implemented unified integrate plugin to update version attributes after all integrations for AYON. The goal is to be able update attribute values in a unified way to a version when all addon integrators are done, so e.g. ftrack can add ftrack id to matching version in AYON server etc.The can be stored under `"versionAttributes"` key.


___

</details>


<details>
<summary>AYON: Staging versions can be used <a href="https://github.com/ynput/OpenPype/pull/4992">#4992</a></summary>

Added ability to use staging versions in AYON mode.


___

</details>


<details>
<summary>AYON: Preparation for products <a href="https://github.com/ynput/OpenPype/pull/5038">#5038</a></summary>

Prepare ayon settings conversion script for `product` settings conversion.


___

</details>


<details>
<summary>Loader: Hide inactive versions in UI <a href="https://github.com/ynput/OpenPype/pull/5101">#5101</a></summary>

Added support for `active` argument to hide versions with active set to False in Loader UI when in AYON mode.


___

</details>


<details>
<summary>General: CLI addon command <a href="https://github.com/ynput/OpenPype/pull/5109">#5109</a></summary>

Added `addon` alias for `module` in OpenPype cli commands.


___

</details>


<details>
<summary>AYON: OpenPype as server addon <a href="https://github.com/ynput/OpenPype/pull/5199">#5199</a></summary>

OpenPype repository can be converted to AYON addon for distribution. Addon has defined dependencies that are required to use it and are not in base ayon-launcher (desktop application).


___

</details>


<details>
<summary>General: Runtime dependencies <a href="https://github.com/ynput/OpenPype/pull/5206">#5206</a></summary>

Defined runtime dependencies in pyproject toml. Moved python ocio and otio modules there.


___

</details>


<details>
<summary>AYON: Bundle distribution <a href="https://github.com/ynput/OpenPype/pull/5209">#5209</a></summary>

Since AYON server 0.3.0 are addon versions defined by bundles which affects how addons, dependency packages and installers are handled. Only source of truth, about any version of anything that should be used, is server bundle.


___

</details>


<details>
<summary>Feature/blender handle q application <a href="https://github.com/ynput/OpenPype/pull/5264">#5264</a></summary>

This edit is to change the way the QApplication is run for Blender. It calls in the singleton (QApplication) during the register. This is made so that other Qt applications and addons are able to run on Blender. In its current implementation, if a QApplication is already running, all functionality of OpenPype becomes unavailable.


___

</details>

### **🚀 Enhancements**


<details>
<summary>General: Connect to AYON server (base) <a href="https://github.com/ynput/OpenPype/pull/3924">#3924</a></summary>

<strong>Initial implementation of being able use AYON server in current OpenPype client. Added ability to connect to AYON server and use base queries.

</strong>AYON mode has it's own executable (and start script). To start in AYON mode just replace `start.py` with `ayon_start.py` (added tray start script to tools). Added constant `AYON_SERVER_ENABLED` to `openpype/__init__.py` to know if ayon mode is enabled. In that case Mongo is not used at all and any attempts will cause crashes.I had to modify `~/openpype/client` content to be able do this switch. Mongo implementation was moved to `mongo` subfolder and use "star imports" in files from where current imports are used. Logic of any tool or query in code was not changed at all. Since functions were based on mongo queries they don't use full potential of AYON server abilities.ATM implementation has login UI, distribution of files from server and replacement of mongo queries. For queries is used `ayon_api` module. Which is in live development so the versions may change from day to day.


___

</details>


<details>
<summary>Enhancement kitsu note with exceptions <a href="https://github.com/ynput/OpenPype/pull/4537">#4537</a></summary>

Adding a setting to choose some exceptions to IntegrateKitsuNote task status changes.


___

</details>


<details>
<summary>General: Environment variable for default OCIO configs <a href="https://github.com/ynput/OpenPype/pull/4670">#4670</a></summary>

Define environment variable which lead to root of builtin ocio configs to be able change the root without changing settings. For the path in settings was used `"{OPENPYPE_ROOT}/vendor/bin/ocioconfig/OpenColorIOConfig"` which disallow to change the root somewhere else. That will be needed in AYON where configs won't be part of desktop application but downloaded from server.


___

</details>


<details>
<summary>AYON: Editorial hierarchy creation <a href="https://github.com/ynput/OpenPype/pull/4699">#4699</a></summary>

Implemented extract hierarchy to AYON plugin which created entities in AYON using ayon api.


___

</details>


<details>
<summary>AYON: Vendorize ayon api <a href="https://github.com/ynput/OpenPype/pull/4753">#4753</a></summary>

Vendorize ayon api into openpype vendor directory. The reason is that `ayon-python-api` is in live development and will fix/add features often in next few weeks/months, and because update of dependency requires new release -> new build, we want to avoid the need of doing that as it would affect OpenPype development.


___

</details>


<details>
<summary>General: Update PySide 6 for MacOs <a href="https://github.com/ynput/OpenPype/pull/4764">#4764</a></summary>

New version of PySide6 does not have issues with settings UI. It is still breaking UI stylesheets so it is not changed for other plaforms but it is enhancement from previous state.


___

</details>


<details>
<summary>General: Removed unused cli commands <a href="https://github.com/ynput/OpenPype/pull/4902">#4902</a></summary>

Removed `texturecopy` and `launch` cli commands from cli commands.


___

</details>


<details>
<summary>AYON: Linux & MacOS launch script <a href="https://github.com/ynput/OpenPype/pull/4970">#4970</a></summary>

Added shell script to launch tray in AYON mode.


___

</details>


<details>
<summary>General: Qt scale enhancement <a href="https://github.com/ynput/OpenPype/pull/5059">#5059</a></summary>

Set ~~'QT_SCALE_FACTOR_ROUNDING_POLICY'~~ scale factor rounding policy of QApplication to `PassThrough` so the scaling can be 'float' number and not just 'int' (150% -> 1.5 scale).


___

</details>


<details>
<summary>CI: WPS linting instead of Hound (rebase) 2 <a href="https://github.com/ynput/OpenPype/pull/5115">#5115</a></summary>

Because Hound currently used to lint the code on GH ships with really old flake8 support, it fails miserably on any newer Python syntax. This PR is adding WPS linter to GitHub workflows that should step in.


___

</details>


<details>
<summary>Max: OP parameters only displays what is attached to the container <a href="https://github.com/ynput/OpenPype/pull/5229">#5229</a></summary>

The OP parameter in 3dsmax only displays what is currently attached to the container while deleting while you can see the items which is not added when you are adding to the container.


___

</details>


<details>
<summary>Testing: improving logging during testing <a href="https://github.com/ynput/OpenPype/pull/5271">#5271</a></summary>

Unit testing logging was crashing on more then one nested layers of inherited loggers.


___

</details>


<details>
<summary>Nuke: removing deprecated settings in baking <a href="https://github.com/ynput/OpenPype/pull/5275">#5275</a></summary>

Removing deprecated settings for baking with reformat. This option was only for single reformat node and it had been substituted with multiple reposition nodes.


___

</details>

### **🐛 Bug fixes**


<details>
<summary>AYON: General fixes and updates <a href="https://github.com/ynput/OpenPype/pull/4975">#4975</a></summary>

Few smaller fixes related to AYON connection. Some of fixes were taken from this PR.


___

</details>


<details>
<summary>Start script: Change returncode on validate or list versions <a href="https://github.com/ynput/OpenPype/pull/4515">#4515</a></summary>

<strong>Change exit code from `1` to `0` when versions  are printed or when version is validated.

</strong>Return code `1` is indicating error but there didn't happen any error.


___

</details>


<details>
<summary>AYON: Change login UI works <a href="https://github.com/ynput/OpenPype/pull/4754">#4754</a></summary>

Fixed change of login UI. Logic change UI did show up, new login was successful, but after restart was used the previous login. This change fix the issue.


___

</details>


<details>
<summary>AYON: General issues <a href="https://github.com/ynput/OpenPype/pull/4763">#4763</a></summary>

Vendorized `ayon_api` from PR broke OpenPype launch, because `ayon_api` is not available. Moved `ayon_api` from ayon specific subforlder to `common` python vendor in OpenPype, and removed login in ayon start script (which was invalid anyway). Also made fixed compatibility with PySide6 by using `qtpy` instead of `Qt` and changing code which is not PySide6 compatible.


___

</details>


<details>
<summary>AYON: Small fixes <a href="https://github.com/ynput/OpenPype/pull/4841">#4841</a></summary>

Bugsfixes and enhancements related to AYON logic. Define `BUILTIN_OCIO_ROOT` environment variable so OCIO configs are working. Use constants from ayon api instead of hardcoding them in codebase. Change process name from "openpype" to "ayon". Don't execute login dialog when application is not yet running but use `open` method instead. Fixed missing modules settings which were not taken from openpype defaults. Updated ayon api to `0.1.17`.


___

</details>


<details>
<summary>Bugfix - Update gazu to 0.9.3 <a href="https://github.com/ynput/OpenPype/pull/4845">#4845</a></summary>

This updates Gazu to 0.9.3 to make sure Gazu works with Kitsu and Zou 0.16.x+


___

</details>


<details>
<summary>Igniter: fix error reports in silent mode <a href="https://github.com/ynput/OpenPype/pull/4909">#4909</a></summary>

Some errors in silent mode commands in Igniter were suppressed and not visible for example in Deadline log.


___

</details>


<details>
<summary>General: Remove ayon api from poetry lock <a href="https://github.com/ynput/OpenPype/pull/4964">#4964</a></summary>

Remove AYON python api from pyproject.toml and poetry.lock again.


___

</details>


<details>
<summary>Ftrack: Fix AYON settings conversion <a href="https://github.com/ynput/OpenPype/pull/4967">#4967</a></summary>

Fix conversion of ftrack settings in AYON mode.


___

</details>


<details>
<summary>AYON: ISO date format conversion issues <a href="https://github.com/ynput/OpenPype/pull/4981">#4981</a></summary>

Function `datetime.fromisoformat` was replaced with `arrow.get` to be used instead.


___

</details>


<details>
<summary>AYON: Missing files on representations <a href="https://github.com/ynput/OpenPype/pull/4989">#4989</a></summary>

Fix integration of files into representation in server database.


___

</details>


<details>
<summary>General: Fix Python 2 vendor for arrow <a href="https://github.com/ynput/OpenPype/pull/4993">#4993</a></summary>

Moved remaining dependencies for arrow from ftrack to python 2 vendor.


___

</details>


<details>
<summary>General: Fix new load plugins for next minor relase <a href="https://github.com/ynput/OpenPype/pull/5000">#5000</a></summary>

Fix access to `fname` attribute which is not available on load plugin anymore.


___

</details>


<details>
<summary>General: Fix mongo secure connection <a href="https://github.com/ynput/OpenPype/pull/5031">#5031</a></summary>

Fix `ssl` and `tls` keys checks in mongo uri query string.


___

</details>


<details>
<summary>AYON: Fix site sync settings <a href="https://github.com/ynput/OpenPype/pull/5069">#5069</a></summary>

Fixed settings for AYON variant of sync server.


___

</details>


<details>
<summary>General: Replace deprecated keyword argument in PyMongo <a href="https://github.com/ynput/OpenPype/pull/5080">#5080</a></summary>

Use argument `tlsCAFile` instead of `ssl_ca_certs` to avoid deprecation warnings.


___

</details>


<details>
<summary>Igniter: QApplication is created <a href="https://github.com/ynput/OpenPype/pull/5081">#5081</a></summary>

Function `_get_qt_app` actually creates new `QApplication` if was not created yet.


___

</details>


<details>
<summary>General: Lower unidecode version <a href="https://github.com/ynput/OpenPype/pull/5090">#5090</a></summary>

Use older version of Unidecode module to support Python 2.


___

</details>


<details>
<summary>General: Lower cryptography to 39.0.0 <a href="https://github.com/ynput/OpenPype/pull/5099">#5099</a></summary>

Lower cryptography to 39.0.0 to avoid breaking of DCCs like Maya and Nuke.


___

</details>


<details>
<summary>AYON: Global environments key fix <a href="https://github.com/ynput/OpenPype/pull/5118">#5118</a></summary>

Seems that when converting ayon settings to OP settings the `environments` setting is put under the `environments` key in `general` however when populating the environment the `environment` key gets picked up, which does not contain the environment variables from the `core/environments` setting


___

</details>


<details>
<summary>Add collector to tray publisher for getting frame range data <a href="https://github.com/ynput/OpenPype/pull/5152">#5152</a></summary>

Add collector to tray publisher to get frame range data. User can choose to enable this collector if they need this in the publisher.Resolve #5136


___

</details>


<details>
<summary>Unreal: get current project settings not using unreal project name <a href="https://github.com/ynput/OpenPype/pull/5170">#5170</a></summary>

There was a bug where Unreal project name was used to query project settings. But Unreal project name can differ from the "real" one because of naming convention rules set by Unreal. This is fixing it by asking for current project settings.


___

</details>


<details>
<summary>Substance Painter: Fix Collect Texture Set Images unable to copy.deepcopy due to QMenu <a href="https://github.com/ynput/OpenPype/pull/5238">#5238</a></summary>

Fix `copy.deepcopy` of `instance.data`.


___

</details>


<details>
<summary>Ayon: server returns different key <a href="https://github.com/ynput/OpenPype/pull/5251">#5251</a></summary>

Package returned from server has `filename` instead of `name`.


___

</details>


<details>
<summary>Substance Painter: Fix default color management settings <a href="https://github.com/ynput/OpenPype/pull/5259">#5259</a></summary>

The default settings for color management for Substance Painter were invalid, it was set to override the global config by default but specified no valid config paths of its own - and thus errored that the paths were not correct.This sets the defaults correctly to match other hosts._I quickly checked - this seems to be the only host with the wrong default settings_


___

</details>


<details>
<summary>Nuke: fixing container data if windows path in value <a href="https://github.com/ynput/OpenPype/pull/5267">#5267</a></summary>

Windows path in container data are reformatted. Previously it was reported that Nuke was rising `utf8 0xc0` error if backward slashes were in data values.


___

</details>


<details>
<summary>Houdini: fix typo error in collect arnold rop <a href="https://github.com/ynput/OpenPype/pull/5281">#5281</a></summary>

Fixing a typo error in `collect_arnold_rop.py`Reference: #5280


___

</details>


<details>
<summary>Slack - enhanced logging and protection against failure <a href="https://github.com/ynput/OpenPype/pull/5287">#5287</a></summary>

Covered issues found in production on customer site. SlackAPI exception doesn't need to have 'error', covered uncaught exception.


___

</details>


<details>
<summary>Maya: Removed unnecessary import of pyblish.cli <a href="https://github.com/ynput/OpenPype/pull/5292">#5292</a></summary>

This import resulted in adding additional logging handler which lead to duplication of logs in hosts with plugins containing `is_in_tests` method. Import is unnecessary for testing functionality.


___

</details>

### **🔀 Refactored code**


<details>
<summary>Loader: Remove `context` argument from Loader.__init__() <a href="https://github.com/ynput/OpenPype/pull/4602">#4602</a></summary>

Remove the previously required `context` argument.


___

</details>


<details>
<summary>Global: Remove legacy integrator <a href="https://github.com/ynput/OpenPype/pull/4786">#4786</a></summary>

Remove the legacy integrator.


___

</details>

### **📃 Documentation**


<details>
<summary>Next Minor Release <a href="https://github.com/ynput/OpenPype/pull/5291">#5291</a></summary>


___

</details>

### **Merged pull requests**


<details>
<summary>Maya: Refactor to new publisher <a href="https://github.com/ynput/OpenPype/pull/4388">#4388</a></summary>

<strong>**Refactor Maya to use the new publisher with new creators.**

</strong>
- [x] Legacy instance can be converted in UI using `SubsetConvertorPlugin`
- [x] Fix support for old style "render" and "vrayscene" instance to the new per layer format.
- [x] Context data is stored with scene
- [x] Workfile instance converted to AutoCreator
- [x] Converted Creator classes
- [x] Create animation
- [x] Create ass
- [x] Create assembly
- [x] Create camera
- [x] Create layout
- [x] Create look
- [x] Create mayascene
- [x] Create model
- [x] Create multiverse look
- [x] Create multiverse usd
- [x] Create multiverse usd comp
- [x] Create multiverse usd over
- [x] Create pointcache
- [x] Create proxy abc
- [x] Create redshift proxy
- [x] Create render
- [x] Create rendersetup
- [x] Create review
- [x] Create rig
- [x] Create setdress
- [x] Create unreal skeletalmesh
- [x] Create unreal staticmesh
- [x] Create vrayproxy
- [x] Create vrayscene
- [x] Create xgen
- [x] Create yeti cache
- [x] Create yeti rig
- [ ] Tested new Creator publishes
- [x] Publish animation
- [x] Publish ass
- [x] Publish assembly
- [x] Publish camera
- [x] Publish layout
- [x] Publish look
- [x] Publish mayascene
- [x] Publish model
- [ ] Publish multiverse look
- [ ] Publish multiverse usd
- [ ] Publish multiverse usd comp
- [ ] Publish multiverse usd over
- [x] Publish pointcache
- [x] Publish proxy abc
- [x] Publish redshift proxy
- [x] Publish render
- [x] Publish rendersetup
- [x] Publish review
- [x] Publish rig
- [x] Publish setdress
- [x] Publish unreal skeletalmesh
- [x] Publish unreal staticmesh
- [x] Publish vrayproxy
- [x] Publish vrayscene
- [x] Publish xgen
- [x] Publish yeti cache
- [x] Publish yeti rig
- [x] Publish workfile
- [x] Rig loader correctly generates a new style animation creator instance
- [ ] Validations / Error messages for common validation failures look nice and usable as a report.
- [ ] Make Create Animation hidden to the user (should not create manually?)
- [x] Correctly detect difference between **'creator_attributes'** and **'instance_data'** since both are "flattened" to the top node.


___

</details>


<details>
<summary>Start script: Fix possible issues with destination drive path <a href="https://github.com/ynput/OpenPype/pull/4478">#4478</a></summary>

<strong>Drive paths for windows are fixing possibly missing slash at the end of destination path.

</strong>Windows `subst` command require to have destination path with slash if it's a drive (it should be `G:\` not `G:`).


___

</details>


<details>
<summary>Global: Move PyOpenColorIO to vendor/python  <a href="https://github.com/ynput/OpenPype/pull/4946">#4946</a></summary>

So that DCCs don't conflict with their own.

See https://github.com/ynput/OpenPype/pull/4267#issuecomment-1537153263 for the issue with Gaffer.

I'm not sure if this is the correct approach, but I assume PySide/Shiboken is under `vendor/python` for this reason as well...
___

</details>


<details>
<summary>RuntimeError with Click on deadline publish <a href="https://github.com/ynput/OpenPype/pull/5065">#5065</a></summary>

I changed Click to version 8.0 instead of 7.1.2 to solve this error:
```
2023-05-30 16:16:51:  0: STDOUT: Traceback (most recent call last):
2023-05-30 16:16:51:  0: STDOUT:   File "start.py", line 1126, in boot
2023-05-30 16:16:51:  0: STDOUT:   File "/prod/softprod/apps/openpype/LINUX/3.15/dependencies/click/core.py", line 829, in __call__
2023-05-30 16:16:51:  0: STDOUT:     return self.main(*args, **kwargs)
2023-05-30 16:16:51:  0: STDOUT:   File "/prod/softprod/apps/openpype/LINUX/3.15/dependencies/click/core.py", line 760, in main
2023-05-30 16:16:51:  0: STDOUT:     _verify_python3_env()
2023-05-30 16:16:51:  0: STDOUT:   File "/prod/softprod/apps/openpype/LINUX/3.15/dependencies/click/_unicodefun.py", line 126, in _verify_python3_env
2023-05-30 16:16:51:  0: STDOUT:     raise RuntimeError(
2023-05-30 16:16:51:  0: STDOUT: RuntimeError: Click will abort further execution because Python 3 was configured to use ASCII as encoding for the environment. Consult https://click.palletsprojects.com/python3/ for mitigation steps.
```


___

</details>




## [3.15.12](https://github.com/ynput/OpenPype/tree/3.15.12)


[Full Changelog](https://github.com/ynput/OpenPype/compare/3.15.11...3.15.12)

### **🆕 New features**


<details>
<summary>Tray Publisher: User can set colorspace per instance explicitly <a href="https://github.com/ynput/OpenPype/pull/4901">#4901</a></summary>

With this feature a user can set/override the colorspace for the representations of an instance explicitly instead of relying on the File Rules from project settings or alike. This way you can ingest any file and explicitly say "this file is colorspace X".


___

</details>


<details>
<summary>Review Family in Max <a href="https://github.com/ynput/OpenPype/pull/5001">#5001</a></summary>

Review Feature by creating preview animation in 3dsmax(The code is still cleaning up so there is going to be some updates until it is ready for review)


___

</details>


<details>
<summary>AfterEffects: support for workfile template builder <a href="https://github.com/ynput/OpenPype/pull/5163">#5163</a></summary>

This PR add functionality of templated workfile builder. It allows someone to prepare AE workfile with placeholders as for automatically loading particular representation of particular subset of particular asset from context where workfile is opened.Selection from multiple prepared workfiles is provided with usage of templates, specific type of tasks could use particular workfile template etc.Artists then can build workfile from template when opening new workfile.


___

</details>


<details>
<summary>CreatePlugin: Get next version helper <a href="https://github.com/ynput/OpenPype/pull/5242">#5242</a></summary>

Implemented helper functions to get next available versions for create instances.


___

</details>

### **🚀 Enhancements**


<details>
<summary>Maya: Improve Templates <a href="https://github.com/ynput/OpenPype/pull/4854">#4854</a></summary>

Use library method for fetching reference node and support parent in hierarchy.


___

</details>


<details>
<summary>Bug: Maya - xgen sidecar files arent moved when saving workfile as an new asset workfile changing context - OP-6222 <a href="https://github.com/ynput/OpenPype/pull/5215">#5215</a></summary>

This PR manages the Xgen files when switching context in the Workfiles app.


___

</details>


<details>
<summary>node references to check for duplicates in Max <a href="https://github.com/ynput/OpenPype/pull/5192">#5192</a></summary>

No duplicates for node references in Max when users trying to select nodes before publishing


___

</details>


<details>
<summary>Tweak profiles logging to debug level <a href="https://github.com/ynput/OpenPype/pull/5194">#5194</a></summary>

Tweak profiles logging to debug level since they aren't artist facing logs.


___

</details>


<details>
<summary>Enhancement: Reduce more visual clutter for artists in new publisher reports <a href="https://github.com/ynput/OpenPype/pull/5208">#5208</a></summary>

Got this from one of our artists' reports - figured some of these logs were definitely not for the artist, reduced those logs to debug level.


___

</details>


<details>
<summary>Cosmetics: Tweak pyblish repair actions (icon, logs, docstring) <a href="https://github.com/ynput/OpenPype/pull/5213">#5213</a></summary>

- Add icon to RepairContextAction
- logs to debug level
- also add attempt repair for RepairAction for consistency
- fix RepairContextAction docstring to mention correct argument name

#### Additional info

We should not forget to remove this ["deprecated" actions.py file](https://github.com/ynput/OpenPype/blob/3501d0d23a78fbaef106da2fffe946cb49bef855/openpype/action.py) in 3.16 (next-minor)

## Testing notes:

1. Run some fabulous repairs!

___

</details>


<details>
<summary>Maya: fix save file prompt on launch last workfile with color management enabled + restructure `set_colorspace` <a href="https://github.com/ynput/OpenPype/pull/5225">#5225</a></summary>

- Only set `configFilePath` when OCIO env var is not set since it doesn't do anything if OCIO var is set anyway.
- Set the Maya 2022+ default OCIO path using the resources path instead of "" to avoid Maya Save File on new file after launch
- **Bugfix: This is what fixes the Save prompt on open last workfile feature with Global color management enabled**
- Move all code related to applying the maya settings together after querying the settings
- Swap around the `if use_workfile_settings` since the check was reversed
- Use `get_current_project_name()` instead of environment vars


___

</details>


<details>
<summary>Enhancement: More descriptive error messages for Loaders <a href="https://github.com/ynput/OpenPype/pull/5227">#5227</a></summary>

Tweak raised errors and error messages for loader errors.


___

</details>


<details>
<summary>Houdini: add select invalid action for ValidateSopOutputNode <a href="https://github.com/ynput/OpenPype/pull/5231">#5231</a></summary>

This PR adds `SelectROPAction` action to `houdini\api\action.py`and it's used in `Validate Output Node``SelectROPAction` is used to select the associated ROPs with the errored instances.


___

</details>


<details>
<summary>Remove new lines from the delivery template string <a href="https://github.com/ynput/OpenPype/pull/5235">#5235</a></summary>

If the delivery template has a new line symbol at the end, say it was copied from the text editor, the delivery process will fail with `OSError` due to incorrect destination path. To avoid that I added `rstrip()` to the `delivery_path` processing.


___

</details>


<details>
<summary>Houdini: better selection on pointcache creation  <a href="https://github.com/ynput/OpenPype/pull/5250">#5250</a></summary>

Houdini  allows `ObjNode` path as `sop_path` in the `ROP` unlike OP/ Ayon require `sop_path` to be set to a sop node path explicitly In this code, better selection is used to filter out invalid selections from OP/ Ayon  point of viewValid selections are
- `SopNode` that has parent of type `geo` or `subnet`
- `ObjNode` of type `geo` that has
- `SopNode` of type `output`
- `SopNode` with render flag `on` (if no `Sopnode` of type `output`)this effectively  filter
- empty `ObjNode`
- `ObjNode`(s) of other types like `cam` and `dopnet`
- `SopNode`(s) that thier parents of other types like `cam` and `sop solver`


___

</details>


<details>
<summary>Update scene inventory even if any errors occurred during update <a href="https://github.com/ynput/OpenPype/pull/5252">#5252</a></summary>

When selecting many items in the scene inventory to update versions and one of the items would error out the updating stops. However, before this PR the scene inventory would also NOT refresh making you think it did nothing.Also implemented as method to allow some code deduplication.


___

</details>

### **🐛 Bug fixes**


<details>
<summary>Maya: Convert frame values to integers <a href="https://github.com/ynput/OpenPype/pull/5188">#5188</a></summary>

Convert frame values to integers.


___

</details>


<details>
<summary>Maya: fix the register_event_callback correctly collecting workfile save after <a href="https://github.com/ynput/OpenPype/pull/5214">#5214</a></summary>

fixing the bug of register_event_callback not being able to collect action of "workfile_save_after" for lock file action


___

</details>


<details>
<summary>Maya: aligning default settings to distributed aces 1.2 config <a href="https://github.com/ynput/OpenPype/pull/5233">#5233</a></summary>

Maya colorspace setttings defaults are set the way they align our distributed ACES 1.2 config file set in global colorspace configs.


___

</details>


<details>
<summary>RepairAction and SelectInvalidAction filter instances failed on the exact plugin <a href="https://github.com/ynput/OpenPype/pull/5240">#5240</a></summary>

RepairAction and SelectInvalidAction actually filter to instances that failed on the exact plugin - not on "any failure"


___

</details>


<details>
<summary>Maya: Bugfix look update nodes by id with non-unique shape names (query with `fullPath`) <a href="https://github.com/ynput/OpenPype/pull/5257">#5257</a></summary>

Fixes a bug where updating attributes on nodes with assigned shader if shape name existed more than once in the scene due to `cmds.listRelatives` call not being done with the `fullPath=True` flag.Original error:
```python
# Traceback (most recent call last):
#   File "E:\openpype\OpenPype\openpype\tools\sceneinventory\view.py", line 264, in <lambda>
#     lambda: self._show_version_dialog(items))
#   File "E:\openpype\OpenPype\openpype\tools\sceneinventory\view.py", line 722, in _show_version_dialog
#     self._update_containers(items, version)
#   File "E:\openpype\OpenPype\openpype\tools\sceneinventory\view.py", line 849, in _update_containers
#     update_container(item, item_version)
#   File "E:\openpype\OpenPype\openpype\pipeline\load\utils.py", line 502, in update_container
#     return loader.update(container, new_representation)
#   File "E:\openpype\OpenPype\openpype\hosts\maya\plugins\load\load_look.py", line 119, in update
#     nodes_by_id[lib.get_id(n)].append(n)
#   File "E:\openpype\OpenPype\openpype\hosts\maya\api\lib.py", line 1420, in get_id
#     sel.add(node)
```


___

</details>


<details>
<summary>Nuke: Create nodes with inpanel=False <a href="https://github.com/ynput/OpenPype/pull/5051">#5051</a></summary>

This PR is meant to remove the annoyance of the UI changing focus to the properties window just for the property window of the newly created node to disappear. Instead of using node.hideControlPanel I'm implementing the concealment during the creation of the node which will not change the focus of the current window.
___

</details>


<details>
<summary>Fix the reset frame range not setting up the right timeline in Max <a href="https://github.com/ynput/OpenPype/pull/5187">#5187</a></summary>

Resolve #5181


___

</details>


<details>
<summary>Resolve: after launch automatization fixes <a href="https://github.com/ynput/OpenPype/pull/5193">#5193</a></summary>

Workfile is no correctly created and aligned witch actual project. Also the launching mechanism is now fixed so even no workfile had been saved yet it will open OpenPype menu automatically.


___

</details>


<details>
<summary>General: Revert backward incompatible change of path to template to multiplatform <a href="https://github.com/ynput/OpenPype/pull/5197">#5197</a></summary>

Now platformity is still handed by usage of `work[root]` (or any other root that is accessible across platforms.)


___

</details>


<details>
<summary>Nuke: root set format updating in node graph <a href="https://github.com/ynput/OpenPype/pull/5198">#5198</a></summary>

Nuke root node needs to be reset on some values so any knobs could be updated in node graph. This works the same way as an user would change frame number so expressions would update its values in knobs.


___

</details>


<details>
<summary>Hiero: fixing otio current project and cosmetics <a href="https://github.com/ynput/OpenPype/pull/5200">#5200</a></summary>

Otio were not returning correct current project once additional Untitled project was open in project manager stack.


___

</details>


<details>
<summary>Max: Publisher instances dont hold its enabled disabled states when Publisher reopened again <a href="https://github.com/ynput/OpenPype/pull/5202">#5202</a></summary>

Resolve #5183, general maxscript conversion issue to python (e.g. bool conversion, true in maxscript while True in Python)(Also resolve the ValueError when you change the subset to publish into list view menu)


___

</details>


<details>
<summary>Burnins: Filter script is defined only for video streams <a href="https://github.com/ynput/OpenPype/pull/5205">#5205</a></summary>

Burnins are working for inputs with audio.


___

</details>


<details>
<summary>Colorspace lib fix compatible python version comparison <a href="https://github.com/ynput/OpenPype/pull/5212">#5212</a></summary>

Fix python version comparison.


___

</details>


<details>
<summary>Houdini: Fix `get_color_management_preferences` <a href="https://github.com/ynput/OpenPype/pull/5217">#5217</a></summary>

Fix the issue described here where the logic for retrieving the current OCIO display and view was incorrectly trying to apply a regex to it.


___

</details>


<details>
<summary>Houdini: Redshift ROP image format bug <a href="https://github.com/ynput/OpenPype/pull/5218">#5218</a></summary>

Problem :
"RS_outputFileFormat" parm value was missing
and there were more "image_format" than redshift rop supports

Fix:
1)  removed unnecessary formats from `image_format_enum`
2) add the selected format value to `RS_outputFileFormat`
___

</details>


<details>
<summary>Colorspace: check PyOpenColorIO rather then python version <a href="https://github.com/ynput/OpenPype/pull/5223">#5223</a></summary>

Fixing previously merged PR (https://github.com/ynput/OpenPype/pull/5212) And applying better way to check compatibility with PyOpenColorIO python api.


___

</details>


<details>
<summary>Validate delivery action representations status <a href="https://github.com/ynput/OpenPype/pull/5228">#5228</a></summary>

- disable delivery button if no representations checked
- fix macos combobox layout
- add error message if no delivery templates found


___

</details>


<details>
<summary> Houdini: Add geometry check for pointcache family <a href="https://github.com/ynput/OpenPype/pull/5230">#5230</a></summary>

When `sop_path`  on ABC ROP node points to a  non `SopNode`, these validators `validate_abc_primitive_to_detail.py`, `validate_primitive_hierarchy_paths.py` will error and crash when this line is executed `geo = output_node.geometryAtFrame(frame)`


___

</details>


<details>
<summary>Houdini: Add geometry check for VDB family <a href="https://github.com/ynput/OpenPype/pull/5232">#5232</a></summary>

When `sop_path` on Geometry ROP node points to a non SopNode, this validator `validate_vdb_output_node.py` will error and crash when this line is executed`sop_node.geometryAtFrame(frame)`


___

</details>


<details>
<summary>Substance Painter: Include the setting only in publish tab <a href="https://github.com/ynput/OpenPype/pull/5234">#5234</a></summary>

Instead of having two settings in both create and publish tab, there is solely one setting in the publish tab for users to set up the parameters.Resolve #5172


___

</details>


<details>
<summary>Maya: Fix collecting arnold prefix when none <a href="https://github.com/ynput/OpenPype/pull/5243">#5243</a></summary>

When no prefix is specified in render settings, the renderlayer collector would error.


___

</details>


<details>
<summary>Deadline: OPENPYPE_VERSION should only be added when running from build <a href="https://github.com/ynput/OpenPype/pull/5244">#5244</a></summary>

When running from source the environment variable `OPENPYPE_VERSION` should not be added. This is a bugfix for the feature #4489


___

</details>


<details>
<summary>Fix no prompt for "unsaved changes" showing when opening workfile in Houdini <a href="https://github.com/ynput/OpenPype/pull/5246">#5246</a></summary>

Fix no prompt for "unsaved changes" showing when opening workfile in Houdini.


___

</details>


<details>
<summary>Fix no prompt for "unsaved changes" showing when opening workfile in Substance Painter <a href="https://github.com/ynput/OpenPype/pull/5248">#5248</a></summary>

Fix no prompt for "unsaved changes" showing when opening workfile in Substance Painter.


___

</details>


<details>
<summary>General: add the os library before os.environ.get <a href="https://github.com/ynput/OpenPype/pull/5249">#5249</a></summary>

Adding os library into `creator_plugins.py` due to `os.environ.get` in line 667


___

</details>


<details>
<summary>Maya: Fix set_attribute for enum attributes <a href="https://github.com/ynput/OpenPype/pull/5261">#5261</a></summary>

Fix for #5260


___

</details>


<details>
<summary>Unreal: Move Qt imports away from module init <a href="https://github.com/ynput/OpenPype/pull/5268">#5268</a></summary>

Importing `Window` creates errors in headless mode.
```
*** WRN: >>> { ModulesLoader }: [  FAILED to import host folder unreal  ]
=============================
No Qt bindings could be found
=============================
Traceback (most recent call last):
  File "C:\Users\tokejepsen\OpenPype\.venv\lib\site-packages\qtpy\__init__.py", line 252, in <module>
    from PySide6 import __version__ as PYSIDE_VERSION  # analysis:ignore
ModuleNotFoundERROR: No module named 'PySide6'

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "C:\Users\tokejepsen\OpenPype\openpype\modules\base.py", line 385, in _load_modules
    default_module = __import__(
  File "C:\Users\tokejepsen\OpenPype\openpype\hosts\unreal\__init__.py", line 1, in <module>
    from .addon import UnrealAddon
  File "C:\Users\tokejepsen\OpenPype\openpype\hosts\unreal\addon.py", line 4, in <module>
    from openpype.widgets.message_window import Window
  File "C:\Users\tokejepsen\OpenPype\openpype\widgets\__init__.py", line 1, in <module>
    from .password_dialog import PasswordDialog
  File "C:\Users\tokejepsen\OpenPype\openpype\widgets\password_dialog.py", line 1, in <module>
    from qtpy import QtWidgets, QtCore, QtGui
  File "C:\Users\tokejepsen\OpenPype\.venv\lib\site-packages\qtpy\__init__.py", line 259, in <module>
    raise QtBindingsNotFoundERROR()
qtpy.QtBindingsNotFoundERROR: No Qt bindings could be found
```


___

</details>

### **🔀 Refactored code**


<details>
<summary>Maya: Minor refactoring and code cleanup <a href="https://github.com/ynput/OpenPype/pull/5226">#5226</a></summary>

Some small cleanup and refactoring of logic. Removing old comments, unused imports and some minor optimization. Also removed the prints of the loader names of each container the scene in `fix_incompatible_containers` + optimizing by using `set` and defining only once. Moved some UI related code/tweaks to run `on_init` only if not in headless mode. Removed an empty `obj.py` file.Each commit message kind of describes why the change was made.


___

</details>

### **Merged pull requests**


<details>
<summary>Bug: Template builder fails when loading data without outliner representation <a href="https://github.com/ynput/OpenPype/pull/5222">#5222</a></summary>

I add an assertion management in case the container does not have a represention in outliner.


___

</details>


<details>
<summary>AfterEffects - add container check validator to AE settings <a href="https://github.com/ynput/OpenPype/pull/5203">#5203</a></summary>

Adds check if scene contains only latest version of loaded containers.


___

</details>




## [3.15.11](https://github.com/ynput/OpenPype/tree/3.15.11)


[Full Changelog](https://github.com/ynput/OpenPype/compare/3.15.10...3.15.11)

### **🆕 New features**


<details>
<summary>Ftrack: Task status during publishing <a href="https://github.com/ynput/OpenPype/pull/5123">#5123</a></summary>

Added option to change task status during publishing for 3 possible cases: "sending to farm", "local integration" and "on farm integration".


___

</details>


<details>
<summary>Nuke: Allow for more complex temp rendering paths <a href="https://github.com/ynput/OpenPype/pull/5132">#5132</a></summary>

When changing the temporary rendering template (i.e., add `{asset}` to the path) to something a bit more complex the formatting was erroring due to missing keys.


___

</details>


<details>
<summary>Blender: Add support for custom path for app templates <a href="https://github.com/ynput/OpenPype/pull/5137">#5137</a></summary>

This PR adds support for a custom App Templates path in Blender by setting the `BLENDER_USER_SCRIPTS` environment variable to the path specified in `OPENPYPE_APP_TEMPLATES_PATH`. This allows users to use their own custom app templates in Blender.


___

</details>


<details>
<summary>TrayPublisher & StandalonePublisher: Specify version <a href="https://github.com/ynput/OpenPype/pull/5142">#5142</a></summary>

Simple creators in TrayPublisher can affect which version will be integrated. Standalone publisher respects the version change from UI.


___

</details>

### **🚀 Enhancements**


<details>
<summary>Workfile Builder UI: Workfile builder window is not modal <a href="https://github.com/ynput/OpenPype/pull/5131">#5131</a></summary>

Workfile Templates Builder:
- Create dialog is not a modal dialog
- Create dialog remains open after create, so you can directly create a new placeholder with similar settings
- In Maya allow to create root level placeholders (no selection during create) - **this felt more like a bugfix than anything else.**


___

</details>


<details>
<summary>3dsmax: Use custom modifiers to hold instance members <a href="https://github.com/ynput/OpenPype/pull/4931">#4931</a></summary>

Moving logic to handle members of publishing instance from children/parent relationship on Container to tracking via custom attribute on modifier. This eliminates limitations where you couldn't have one node multiple times under one Container and because it stores those relationships as weak references, they are easily transferable even when original nodes are renamed.


___

</details>


<details>
<summary>Add height, width and fps setup to project manager <a href="https://github.com/ynput/OpenPype/pull/5075">#5075</a></summary>

Add Width, Height, FPS, Pixel Aspect and Frame Start/End to the Project creation dialogue in the Project Manager.I understand that the Project manager will be replaced in the upcoming Ayon, but for the time being I believe setting new project with these options available would be more fun.


___

</details>


<details>
<summary>Nuke: connect custom write node script to the OP setting <a href="https://github.com/ynput/OpenPype/pull/5113">#5113</a></summary>

Allows user to customize the values of knobs attribute in the OP setting and use it in custom write node


___

</details>


<details>
<summary>Keep `publisher.create_widget` variant when creating subsets <a href="https://github.com/ynput/OpenPype/pull/5119">#5119</a></summary>

Whenever a person is creating a subset to publish, the "creator" widget resets (where you choose the variant, product, etc.) so if the person is publishing several images of the a variant which is not the default one, they have to keep selecting the correct one after every "create".

This commit resets the original variant upon successful creation of a subset for publishing.

Demo:
[Screencast from 2023-06-08 10-46-40.webm](https://github.com/ynput/OpenPype/assets/1800151/ca1c91d4-b8f3-43d2-a7b7-35987f5b6a3f)

## Testing notes:
1. Launch AYON/OP
2. Launch the publisher (select a project, shot, etc.)
3. Crete a publish type (any works)
4. Choose a variant for the publish that is not the default
5. "Create >>"

The Variant fields should still have the variant you choose.



___

</details>


<details>
<summary>Color Management- added color management support for simple expected files on Deadline <a href="https://github.com/ynput/OpenPype/pull/5122">#5122</a></summary>

Running of `ExtractOIIOTranscode` during Deadline publish was previously implemented only on DCCs with AOVs (Maya, Max).This PR extends this for other DCCs with flat structure of expected files.


___

</details>


<details>
<summary>hide macos dock icon on build <a href="https://github.com/ynput/OpenPype/pull/5133">#5133</a></summary>

Set `LSUIElement` to `1` in the `Info.plist` to hide OP icon from the macos dock by default.


___

</details>


<details>
<summary>Pack project: Raise exception with reasonable message <a href="https://github.com/ynput/OpenPype/pull/5145">#5145</a></summary>

Pack project crashes with relevant message when destination directory is not set.


___

</details>


<details>
<summary>Allow "inventory" actions to be supplied by a Module/Addon. <a href="https://github.com/ynput/OpenPype/pull/5146">#5146</a></summary>

Adds "inventory" as a possible key to the plugin paths to be returned from a module.


___

</details>


<details>
<summary>3dsmax: make code compatible with 3dsmax 2022 <a href="https://github.com/ynput/OpenPype/pull/5164">#5164</a></summary>

Python 3.7 in 3dsmax 2022 is not supporting walrus operator. This is removing it from the code for the sake of compatibility


___

</details>

### **🐛 Bug fixes**


<details>
<summary>Maya: Support same attribute names on different node types. <a href="https://github.com/ynput/OpenPype/pull/5054">#5054</a></summary>

When validating render settings attributes, support same attribute names on different node types.


___

</details>


<details>
<summary>Maya: bug fix the standin being not loaded when they are first loaded <a href="https://github.com/ynput/OpenPype/pull/5143">#5143</a></summary>

fix the bug of raising error when the first two standins are loaded through the loaderThe bug mentioned in the related issue: https://github.com/ynput/OpenPype/issues/5129For some reason, `defaultArnoldRenderOptions.operator` is not listed in the connection node attribute even if `cmds.loadPlugin("mtoa", quiet=True)` executed before loading the object as standins for the first time.But if you manually turn on mtoa through plugin preference and load the standins for the first time, it won't raise the related  `defaultArnoldRenderOptions.operator` error.


___

</details>


<details>
<summary>Maya: bug fix arnoldExportAss unable to export selected set members <a href="https://github.com/ynput/OpenPype/pull/5150">#5150</a></summary>

See #5108 fix the bug arnoldExportAss being not able to export and error out during extraction.


___

</details>


<details>
<summary>Maya: Xgen multiple descriptions on single shape - OP-6039 <a href="https://github.com/ynput/OpenPype/pull/5160">#5160</a></summary>

When having multiple descriptions on the same geometry, the extraction would produce redundant duplicate geometries.


___

</details>


<details>
<summary>Maya: Xgen export of Abc's during Render Publishing - OP-6206 <a href="https://github.com/ynput/OpenPype/pull/5167">#5167</a></summary>

Shading assignments was missing duplicating the setup for Xgen publishing and the exporting of patches was getting the end frame incorrectly.


___

</details>


<details>
<summary>Maya: Include handles - OP-6236 <a href="https://github.com/ynput/OpenPype/pull/5175">#5175</a></summary>

Render range was missing the handles.


___

</details>


<details>
<summary>OCIO: Support working with single frame renders <a href="https://github.com/ynput/OpenPype/pull/5053">#5053</a></summary>

When there is only 1 file, the datamember `files` on the representation should be a string.


___

</details>


<details>
<summary>Burnins: Refactored burnins script <a href="https://github.com/ynput/OpenPype/pull/5094">#5094</a></summary>

Refactored list value for burnins and fixed command length limit by using temp file for filters string.


___

</details>


<details>
<summary>Nuke: open_file function can open autosave script <a href="https://github.com/ynput/OpenPype/pull/5107">#5107</a></summary>

Fix the bug of the workfile dialog being unable to open autosave nuke script


___

</details>


<details>
<summary>ImageIO: Minor fixes <a href="https://github.com/ynput/OpenPype/pull/5147">#5147</a></summary>

Resolve few minor fixes related to latest image io changes from PR.


___

</details>


<details>
<summary>Publisher: Fix save shortcut <a href="https://github.com/ynput/OpenPype/pull/5148">#5148</a></summary>

Save shortcut should work for both PySide2 and PySide6.


___

</details>


<details>
<summary>Pack Project: Fix files packing <a href="https://github.com/ynput/OpenPype/pull/5154">#5154</a></summary>

Packing of project with files does work again.


___

</details>


<details>
<summary>Maya: Xgen version mismatch after publish - OP-6204 <a href="https://github.com/ynput/OpenPype/pull/5161">#5161</a></summary>

Xgen was not updating correctly when for example adding or removing descriptions. This resolve the issue by overwritting the workspace xgen file.


___

</details>


<details>
<summary>Publisher: Edge case fixes <a href="https://github.com/ynput/OpenPype/pull/5165">#5165</a></summary>

Fix few edge case issues that may cause issues in Publisher UI.


___

</details>


<details>
<summary>Colorspace: host config path backward compatibility <a href="https://github.com/ynput/OpenPype/pull/5166">#5166</a></summary>

Old project settings overrides are now fully backward compatible. The issue with host config paths overrides were solved and now once a project used to be set to ocio_config **enabled** with found filepaths - this is now considered as activated host ocio_config paths overrides.Nuke is having an popup dialogue which is letting know to a user that settings for config path were changed.


___

</details>


<details>
<summary>Maya: import workfile missing - OP-6233 <a href="https://github.com/ynput/OpenPype/pull/5174">#5174</a></summary>

Missing `workfile` family to import.


___

</details>


<details>
<summary>Ftrack: Fix ignore sync filter <a href="https://github.com/ynput/OpenPype/pull/5176">#5176</a></summary>

Ftrack ignore filter does not crash because of dictionary modifications during it's iteration.


___

</details>


<details>
<summary>Webpublisher - headless publish shouldn't be blocking operation <a href="https://github.com/ynput/OpenPype/pull/5177">#5177</a></summary>

`subprocess.call` was blocking, which resulted in UI non responsiveness as it was waiting for publish to finish.


___

</details>


<details>
<summary>Publisher: Fix disappearing actions <a href="https://github.com/ynput/OpenPype/pull/5184">#5184</a></summary>

Pyblish plugin actions are visible as expected.


___

</details>

### **Merged pull requests**


<details>
<summary>Enhancement:animation family loaded as standing (abc) uses "use file sequence" <a href="https://github.com/ynput/OpenPype/pull/5110">#5110</a></summary>

The changes are the following. We started by updating the the is_sequence(files) function allowing it to return True for a list of files which has only one file, since our animation in this provides just one alembic file. For the correct FPS number, we got the fps from the published ass/abc from the version data.


___

</details>


<details>
<summary>add label to matching family <a href="https://github.com/ynput/OpenPype/pull/5128">#5128</a></summary>

I added the possibility to filter the `family smart select` with the label in addition to the family.


___

</details>




## [3.15.10](https://github.com/ynput/OpenPype/tree/3.15.10)


[Full Changelog](https://github.com/ynput/OpenPype/compare/3.15.9...3.15.10)

### **🆕 New features**


<details>
<summary>ImageIO: Adding ImageIO activation toggle to all hosts <a href="https://github.com/ynput/OpenPype/pull/4700">#4700</a></summary>

Colorspace management can now be enabled at the project level, although it is disabled by default. Once enabled, all hosts will use the OCIO config file defined in the settings. If settings are disabled, the system switches to DCC's native color space management, and we do not store colorspace information at the representative level.


___

</details>


<details>
<summary>Redshift Proxy Support in 3dsMax <a href="https://github.com/ynput/OpenPype/pull/4625">#4625</a></summary>

Redshift Proxy Support for 3dsMax.
- [x] Creator
- [x] Loader
- [x] Extractor
- [x] Validator
- [x]  Add documentation


___

</details>


<details>
<summary>Houdini farm publishing and rendering <a href="https://github.com/ynput/OpenPype/pull/4825">#4825</a></summary>

Deadline Farm publishing and Rendering for Houdini
- [x] Mantra
- [x] Karma(including usd renders)
- [x] Arnold
- [x] Elaborate Redshift ROP for deadline submission
- [x]  fix the existing bug in Redshift ROP
- [x] Vray
- [x] add docs


___

</details>


<details>
<summary>Feature: Blender hook to execute python scripts at launch <a href="https://github.com/ynput/OpenPype/pull/4905">#4905</a></summary>

Hook to allow hooks to add path to a python script that will be executed when Blender starts.


___

</details>


<details>
<summary>Feature: Resolve: Open last workfile on launch through .scriptlib  <a href="https://github.com/ynput/OpenPype/pull/5047">#5047</a></summary>

Added implementation to Resolve integration to open last workfile on launch.


___

</details>


<details>
<summary>General: Remove default windowFlags from publisher <a href="https://github.com/ynput/OpenPype/pull/5089">#5089</a></summary>

The default windowFlags is making the publisher window (in Linux at least) only show the close button and it's frustrating as many times you just want to minimize the window and get back to the validation after. Removing that line I get what I'd expect.**Before:****After:**


___

</details>


<details>
<summary>General: Show user who created the workfile on the details pane of workfile manager <a href="https://github.com/ynput/OpenPype/pull/5093">#5093</a></summary>

New PR for https://github.com/ynput/OpenPype/pull/5087, which was closed after merging `next-minor` branch and then realizing we don't need to target it as it was decided it's not required to support windows. More info on that PR discussion.Small addition to add name of the `user` who created the workfile on the details pane of the workfile manager:


___

</details>


<details>
<summary>Loader: Hide inactive versions in UI <a href="https://github.com/ynput/OpenPype/pull/5100">#5100</a></summary>

Hide versions with `active` set to `False` in Loader UI.


___

</details>

### **🚀 Enhancements**


<details>
<summary>Maya: Repair RenderPass token when merging AOVs. <a href="https://github.com/ynput/OpenPype/pull/5055">#5055</a></summary>

Validator was flagging that `<RenderPass>` was in the image prefix, but did not repair the issue.


___

</details>


<details>
<summary>Maya: Improve error feedback when no renderable cameras exist for ASS family. <a href="https://github.com/ynput/OpenPype/pull/5092">#5092</a></summary>

When collecting cameras for `ass` family, this improves the error message when no cameras are renderable.


___

</details>


<details>
<summary>Nuke: Custom script to set frame range of read nodes <a href="https://github.com/ynput/OpenPype/pull/5039">#5039</a></summary>

Adding option to set frame range specifically for the read nodes in Openpype Panel. User can set up their preferred frame range with the frame range dialog, which can be showed after clicking `Set Frame Range (Read Node)` in Openpype Tools


___

</details>


<details>
<summary>Update extract review letterbox docs <a href="https://github.com/ynput/OpenPype/pull/5074">#5074</a></summary>

Update Extract Review - Letter Box section in Docs. Letterbox type description is removed.


___

</details>


<details>
<summary>Project pack: Documents only skips roots validation <a href="https://github.com/ynput/OpenPype/pull/5082">#5082</a></summary>

Single roots validation is skipped if only documents are extracted.


___

</details>


<details>
<summary>Nuke: custom settings for write node without publish <a href="https://github.com/ynput/OpenPype/pull/5084">#5084</a></summary>

Set Render Output and other settings to write nodes for non-publish purposes.


___

</details>

### **🐛 Bug fixes**


<details>
<summary>Maya: Deadline servers <a href="https://github.com/ynput/OpenPype/pull/5052">#5052</a></summary>

Fix working with multiple Deadline servers in Maya.
- Pools (primary and secondary) attributes were not recreated correctly.
- Order of collector plugins were wrong, so collected data was not injected into render instances.
- Server attribute was not converted to string so comparing with settings was incorrect.
- Improve debug logging for where the webservice url is getting fetched from.


___

</details>


<details>
<summary>Maya: Fix Load Reference. <a href="https://github.com/ynput/OpenPype/pull/5091">#5091</a></summary>

Fix bug introduced with https://github.com/ynput/OpenPype/pull/4751 where `cmds.ls` returns a list.


___

</details>


<details>
<summary>3dsmax: Publishing Deadline jobs from RedShift  <a href="https://github.com/ynput/OpenPype/pull/4960">#4960</a></summary>

Fix the bug of being uable to publish deadline jobs from RedshiftUse Current File instead of Published Scene for just Redshift.
- add save scene before rendering to ensure the scene is saved after the modification.
- add separated aov files option to allow users to choose to have aovs in render output
- add validator for render publish to aovid overriding the previous renders


___

</details>


<details>
<summary>Houdini: Fix missing frame range for pointcache and camera exports <a href="https://github.com/ynput/OpenPype/pull/5026">#5026</a></summary>

Fix missing frame range for pointcache and camera exports on published version.


___

</details>


<details>
<summary>Global: collect_frame_fix plugin fix and cleanup <a href="https://github.com/ynput/OpenPype/pull/5064">#5064</a></summary>

Previous implementation https://github.com/ynput/OpenPype/pull/5036 was broken this is fixing the issue where attribute is found in instance data although the settings were disabled for the plugin.


___

</details>


<details>
<summary>Hiero: Fix apply settings Clip Load <a href="https://github.com/ynput/OpenPype/pull/5073">#5073</a></summary>

Changed `apply_settings` to classmethod which fixes the issue with settings.


___

</details>


<details>
<summary>Resolve: Make sure scripts dir exists <a href="https://github.com/ynput/OpenPype/pull/5078">#5078</a></summary>

Make sure the scripts directory exists before looping over it's content.


___

</details>


<details>
<summary>removing info knob from nuke creators <a href="https://github.com/ynput/OpenPype/pull/5083">#5083</a></summary>

- removing instance node if removed via publisher
- removing info knob since it is not needed any more (was there only for the transition phase)


___

</details>


<details>
<summary>Tray: Fix restart arguments on update <a href="https://github.com/ynput/OpenPype/pull/5085">#5085</a></summary>

Fix arguments on restart.


___

</details>


<details>
<summary>Maya: bug fix on repair action in Arnold Scene Source CBID Validator <a href="https://github.com/ynput/OpenPype/pull/5096">#5096</a></summary>

Fix the bug of not being able to use repair action  in Arnold Scene Source CBID Validator


___

</details>


<details>
<summary>Nuke: batch of small fixes <a href="https://github.com/ynput/OpenPype/pull/5103">#5103</a></summary>

- default settings for `imageio.requiredNodes` **CreateWriteImage**
- default settings for **LoadImage** representations
- **Create** and **Publish** menu items with `parent=main_window` (version > 14)


___

</details>


<details>
<summary>Deadline: make prerender check safer <a href="https://github.com/ynput/OpenPype/pull/5104">#5104</a></summary>

Prerender wasn't correctly recognized and was replaced with just 'render' family.In Nuke it is correctly `prerender.farm` in families, which wasn't handled here. It resulted into using `render` in templates even if `render` and `prerender` templates were split.


___

</details>


<details>
<summary>General: Sort launcher actions alphabetically <a href="https://github.com/ynput/OpenPype/pull/5106">#5106</a></summary>

The launcher actions weren't being sorted by its label but its name (which on the case of the apps it's the version number) and thus the order wasn't consistent and we kept getting a different order on every launch. From my debugging session, this was the result of what the `actions` variable held after the `filter_compatible_actions` function before these changes:
```
(Pdb) for p in actions: print(p.order, p.name)
0 14-02
0 14-02
0 14-02
0 14-02
0 14-02
0 19-5-493
0 2023
0 3-41
0 6-01
```This caused already a couple bugs from our artists thinking they had launched Nuke X and instead launched Nuke and telling us their Nuke was missing nodes**Before:****After:**


___

</details>


<details>
<summary>TrayPublisher: Editorial video stream discovery <a href="https://github.com/ynput/OpenPype/pull/5120">#5120</a></summary>

Editorial create plugin in traypublisher does not expect that first stream in input is video.


___

</details>

### **🔀 Refactored code**


<details>
<summary>3dsmax: Move from deprecated interface <a href="https://github.com/ynput/OpenPype/pull/5117">#5117</a></summary>

`INewPublisher` interface is deprecated, this PR is changing the use to `IPublishHost` instead.


___

</details>

### **Merged pull requests**


<details>
<summary>add movalex as a contributor for code <a href="https://github.com/ynput/OpenPype/pull/5076">#5076</a></summary>

Adds @movalex as a contributor for code.

This was requested by mkolar [in this comment](https://github.com/ynput/OpenPype/pull/4916#issuecomment-1571498425)

[skip ci]
___

</details>


<details>
<summary>3dsmax: refactor load plugins <a href="https://github.com/ynput/OpenPype/pull/5079">#5079</a></summary>


___

</details>




## [3.15.9](https://github.com/ynput/OpenPype/tree/3.15.9)


[Full Changelog](https://github.com/ynput/OpenPype/compare/3.15.8...3.15.9)

### **🆕 New features**


<details>
<summary>Blender: Implemented Loading of Alembic Camera <a href="https://github.com/ynput/OpenPype/pull/4990">#4990</a></summary>

Implemented loading of Alembic cameras in Blender.


___

</details>


<details>
<summary>Unreal: Implemented Creator, Loader and Extractor for Levels <a href="https://github.com/ynput/OpenPype/pull/5008">#5008</a></summary>

Creator, Loader and Extractor for Unreal Levels have been implemented.


___

</details>

### **🚀 Enhancements**


<details>
<summary>Blender: Added setting for base unit scale <a href="https://github.com/ynput/OpenPype/pull/4987">#4987</a></summary>

A setting for the base unit scale has been added for Blender.The unit scale is automatically applied when opening a file or creating a new one.


___

</details>


<details>
<summary>Unreal: Changed naming and path of Camera Levels <a href="https://github.com/ynput/OpenPype/pull/5010">#5010</a></summary>

The levels created for the camera in Unreal now include `_camera` in the name, to be better identifiable, and are placed in the camera folder.


___

</details>


<details>
<summary>Settings: Added option to nest settings templates <a href="https://github.com/ynput/OpenPype/pull/5022">#5022</a></summary>

It is possible to nest settings templates in another templates.


___

</details>


<details>
<summary>Enhancement/publisher: Remove "hit play to continue" label on continue <a href="https://github.com/ynput/OpenPype/pull/5029">#5029</a></summary>

Remove "hit play to continue" message on continue so that it doesn't show anymore when play was clicked.


___

</details>


<details>
<summary>Ftrack: Limit number of ftrack events to query at once <a href="https://github.com/ynput/OpenPype/pull/5033">#5033</a></summary>

Limit the amount of ftrack events received from mongo at once to 100.


___

</details>


<details>
<summary>General: Small code cleanups <a href="https://github.com/ynput/OpenPype/pull/5034">#5034</a></summary>

Small code cleanup and updates.


___

</details>


<details>
<summary>Global: collect frames to fix with settings <a href="https://github.com/ynput/OpenPype/pull/5036">#5036</a></summary>

Settings for `Collect Frames to Fix` will allow disable per project the plugin. Also `Rewriting latest version` attribute is hiddable from settings.


___

</details>


<details>
<summary>General: Publish plugin apply settings can expect only project settings <a href="https://github.com/ynput/OpenPype/pull/5037">#5037</a></summary>

Only project settings are passed to optional `apply_settings` method, if the method expects only one argument.


___

</details>

### **🐛 Bug fixes**


<details>
<summary>Maya: Load Assembly fix invalid imports  <a href="https://github.com/ynput/OpenPype/pull/4859">#4859</a></summary>

Refactors imports so they are now correct.


___

</details>


<details>
<summary>Maya: Skipping rendersetup for members. <a href="https://github.com/ynput/OpenPype/pull/4973">#4973</a></summary>

When publishing a `rendersetup`, the objectset is and should be empty.


___

</details>


<details>
<summary>Maya: Validate Rig Output IDs <a href="https://github.com/ynput/OpenPype/pull/5016">#5016</a></summary>

Absolute names of node were not used, so plugin did not fetch the nodes properly.Also missed pymel command.


___

</details>


<details>
<summary>Deadline: escape rootless path in publish job <a href="https://github.com/ynput/OpenPype/pull/4910">#4910</a></summary>

If the publish path on Deadline job contains spaces or other characters, command was failing because the path wasn't properly escaped. This is fixing it.


___

</details>


<details>
<summary>General: Company name and URL changed <a href="https://github.com/ynput/OpenPype/pull/4974">#4974</a></summary>

The current records were obsolete in inno_setup, changed to the up-to-date.
___

</details>


<details>
<summary>Unreal: Fix usage of 'get_full_path' function <a href="https://github.com/ynput/OpenPype/pull/5014">#5014</a></summary>

This PR changes all the occurrences of `get_full_path` functions to alternatives to get the path of the objects.


___

</details>


<details>
<summary>Unreal: Fix sequence frames validator to use correct data <a href="https://github.com/ynput/OpenPype/pull/5021">#5021</a></summary>

Fix sequence frames validator to use clipIn and clipOut data instead of frameStart and frameEnd.


___

</details>


<details>
<summary>Unreal: Fix render instances collection to use correct data <a href="https://github.com/ynput/OpenPype/pull/5023">#5023</a></summary>

Fix render instances collection to use `frameStart` and `frameEnd` from the Project Manager, instead of the sequence's ones.


___

</details>


<details>
<summary>Resolve: loader is opening even if no timeline in project <a href="https://github.com/ynput/OpenPype/pull/5025">#5025</a></summary>

Loader is opening now even no timeline is available in a project.


___

</details>


<details>
<summary>nuke: callback for dirmapping is on demand <a href="https://github.com/ynput/OpenPype/pull/5030">#5030</a></summary>

Nuke was slowed down on processing due this callback. Since it is disabled by default it made sense to add it only on demand.


___

</details>


<details>
<summary>Publisher: UI works with instances without label <a href="https://github.com/ynput/OpenPype/pull/5032">#5032</a></summary>

Publisher UI does not crash if instance don't have filled 'label' key in instance data.


___

</details>


<details>
<summary>Publisher: Call explicitly prepared tab methods <a href="https://github.com/ynput/OpenPype/pull/5044">#5044</a></summary>

It is not possible to go to Create tab during publishing from OpenPype menu.


___

</details>


<details>
<summary>Ftrack: Role names are not case sensitive in ftrack event server status action <a href="https://github.com/ynput/OpenPype/pull/5058">#5058</a></summary>

Event server status action is not case sensitive for role names of user.


___

</details>


<details>
<summary>Publisher: Fix border widget <a href="https://github.com/ynput/OpenPype/pull/5063">#5063</a></summary>

Fixed border lines in Publisher UI to be painted correctly with correct indentation and size.


___

</details>


<details>
<summary>Unreal: Fix Commandlet Project and Permissions <a href="https://github.com/ynput/OpenPype/pull/5066">#5066</a></summary>

Fix problem when creating an Unreal Project when Commandlet Project is in a protected location.


___

</details>


<details>
<summary>Unreal: Added verification for Unreal app name format <a href="https://github.com/ynput/OpenPype/pull/5070">#5070</a></summary>

The Unreal app name is used to determine the Unreal version folder, so it is necessary that if follows the format `x-x`, where `x` is any integer. This PR adds a verification that the app name follows that format.


___

</details>

### **📃 Documentation**


<details>
<summary>Docs: Display wrong image in ExtractOIIOTranscode <a href="https://github.com/ynput/OpenPype/pull/5045">#5045</a></summary>

Wrong image display in `https://openpype.io/docs/project_settings/settings_project_global#extract-oiio-transcode`.


___

</details>

### **Merged pull requests**


<details>
<summary>Drop-down menu to list all families in create placeholder <a href="https://github.com/ynput/OpenPype/pull/4928">#4928</a></summary>

Currently in the create placeholder window, we need to write the family manually. This replace the text field by an enum field with all families for the current software.


___

</details>


<details>
<summary>add sync to specific projects or listen only <a href="https://github.com/ynput/OpenPype/pull/4919">#4919</a></summary>

Extend kitsu sync service with additional arguments to sync specific projects.


___

</details>




## [3.15.8](https://github.com/ynput/OpenPype/tree/3.15.8)


[Full Changelog](https://github.com/ynput/OpenPype/compare/3.15.7...3.15.8)

### **🆕 New features**


<details>
<summary>Publisher: Show instances in report page <a href="https://github.com/ynput/OpenPype/pull/4915">#4915</a></summary>

Show publish instances in report page. Also added basic log view with logs grouped by instance. Validation error detail now have 2 colums, one with erro details second with logs. Crashed state shows fast access to report action buttons. Success will show only logs. Publish frame is shrunked automatically on publish stop.


___

</details>


<details>
<summary>Fusion - Loader plugins updates <a href="https://github.com/ynput/OpenPype/pull/4920">#4920</a></summary>

Update to some Fusion loader plugins:The sequence loader can now load footage from the image and online family.The FBX loader can now import all formats Fusions FBX node can read.You can now import the content of another workfile into your current comp with the workfile loader.


___

</details>


<details>
<summary>Fusion: deadline farm rendering <a href="https://github.com/ynput/OpenPype/pull/4955">#4955</a></summary>

Enabling Fusion for deadline farm rendering.


___

</details>


<details>
<summary>AfterEffects: set frame range and resolution <a href="https://github.com/ynput/OpenPype/pull/4983">#4983</a></summary>

Frame information (frame start, duration, fps) and resolution (width and height) is applied to selected composition from Asset Management System (Ftrack or DB) automatically when published instance is created.It is also possible explicitly propagate both values from DB to selected composition by newly added menu buttons.


___

</details>


<details>
<summary>Publish: Enhance automated publish plugin settings <a href="https://github.com/ynput/OpenPype/pull/4986">#4986</a></summary>

Added plugins option to define settings category where to look for settings of a plugin and added public helper functions to apply settings `get_plugin_settings` and `apply_plugin_settings_automatically`.


___

</details>

### **🚀 Enhancements**


<details>
<summary>Load Rig References - Change Rig to Animation in Animation instance <a href="https://github.com/ynput/OpenPype/pull/4877">#4877</a></summary>

We are using the template builder to build an animation scene. All the rig placeholders are imported correctly, but the automatically created animation instances retain the rig family in their names and subsets. In our example, we need animationMain instead of rigMain, because this name will be used in the following steps like lighting.Here is the result we need. I checked, and it's not a template builder problem, because even if I load a rig as a reference, the result is the same. For me, since we are in the animation instance, it makes more sense to have animation instead of rig in the name. The naming is just fine if we use create from the Openpype menu.


___

</details>


<details>
<summary>Enhancement: Resolve prelaunch code refactoring and update defaults <a href="https://github.com/ynput/OpenPype/pull/4916">#4916</a></summary>

The main reason of this PR is wrong default settings in `openpype/settings/defaults/system_settings/applications.json` for Resolve host. The `bin` folder should not be a part of the macos and Linux `RESOLVE_PYTHON3_PATH` variable.The rest of this PR is some code cleanups for Resolve prelaunch hook to simplify further development.Also added a .gitignore for vscode workspace files.


___

</details>


<details>
<summary>Unreal: 🚚 move Unreal plugin to separate repository <a href="https://github.com/ynput/OpenPype/pull/4980">#4980</a></summary>

To support Epic Marketplace have to move AYON Unreal integration plugins to separate repository. This is replacing current files with git submodule, so the change should be functionally without impact.New repository lives here: https://github.com/ynput/ayon-unreal-plugin


___

</details>


<details>
<summary>General: Lib code cleanup <a href="https://github.com/ynput/OpenPype/pull/5003">#5003</a></summary>

Small cleanup in lib files in openpype.


___

</details>


<details>
<summary>Allow to open with djv by extension instead of representation name <a href="https://github.com/ynput/OpenPype/pull/5004">#5004</a></summary>

Filter open in djv action by extension instead of representation.


___

</details>


<details>
<summary>DJV open action `extensions` as `set` <a href="https://github.com/ynput/OpenPype/pull/5005">#5005</a></summary>

Change `extensions` attribute to `set`.


___

</details>


<details>
<summary>Nuke: extract thumbnail with multiple reposition nodes <a href="https://github.com/ynput/OpenPype/pull/5011">#5011</a></summary>

Added support for multiple reposition nodes.


___

</details>


<details>
<summary>Enhancement: Improve logging levels and messages for artist facing publish reports <a href="https://github.com/ynput/OpenPype/pull/5018">#5018</a></summary>

Tweak the logging levels and messages to try and only show those logs that an artist should see and could understand. Move anything that's slightly more involved into a "debug" message instead.


___

</details>

### **🐛 Bug fixes**


<details>
<summary>Bugfix/frame variable fix <a href="https://github.com/ynput/OpenPype/pull/4978">#4978</a></summary>

Renamed variables to match OpenPype terminology to reduce confusion and add consistency.
___

</details>


<details>
<summary>Global: plugins cleanup plugin will leave beauty rendered files <a href="https://github.com/ynput/OpenPype/pull/4790">#4790</a></summary>

Attempt to mark more files to be cleaned up explicitly in intermediate `renders` folder in work area for farm jobs.


___

</details>


<details>
<summary>Fix: Download last workfile doesn't work if not already downloaded <a href="https://github.com/ynput/OpenPype/pull/4942">#4942</a></summary>

Some optimization condition is messing with the feature: if the published workfile is not already downloaded, it won't download it...


___

</details>


<details>
<summary>Unreal: Fix transform when loading layout to match existing assets <a href="https://github.com/ynput/OpenPype/pull/4972">#4972</a></summary>

Fixed transform when loading layout to match existing assets.


___

</details>


<details>
<summary>fix the bug of fbx loaders in Max <a href="https://github.com/ynput/OpenPype/pull/4977">#4977</a></summary>

bug fix of fbx loaders for not being able to parent to the CON instances while importing cameras(and models) which is published from other DCCs such as Maya.


___

</details>


<details>
<summary>AfterEffects: allow returning stub with not saved workfile <a href="https://github.com/ynput/OpenPype/pull/4984">#4984</a></summary>

Allows to use Workfile app to Save first empty workfile.


___

</details>


<details>
<summary>Blender: Fix Alembic loading <a href="https://github.com/ynput/OpenPype/pull/4985">#4985</a></summary>

Fixed problem occurring when trying to load an Alembic model in Blender.


___

</details>


<details>
<summary>Unreal: Addon Py2 compatibility <a href="https://github.com/ynput/OpenPype/pull/4994">#4994</a></summary>

Fixed Python 2 compatibility of unreal addon.


___

</details>


<details>
<summary>Nuke: fixed missing files key in representation <a href="https://github.com/ynput/OpenPype/pull/4999">#4999</a></summary>

Issue with missing keys once rendering target set to existing frames is fixed. Instance has to be evaluated in validation for missing files.


___

</details>


<details>
<summary>Unreal: Fix the frame range when loading camera <a href="https://github.com/ynput/OpenPype/pull/5002">#5002</a></summary>

The keyframes of the camera, when loaded, were not using the correct frame range.


___

</details>


<details>
<summary>Fusion: fixing frame range targeting <a href="https://github.com/ynput/OpenPype/pull/5013">#5013</a></summary>

Frame range targeting at Rendering instances is now following configured options.


___

</details>


<details>
<summary>Deadline: fix selection from multiple webservices <a href="https://github.com/ynput/OpenPype/pull/5015">#5015</a></summary>

Multiple different DL webservice could be configured. First they must by configured in System Settings., then they could be configured per project in `project_settings/deadline/deadline_servers`.Only single webservice could be a target of publish though.


___

</details>

### **Merged pull requests**


<details>
<summary>3dsmax: Refactored publish plugins to use proper implementation of pymxs <a href="https://github.com/ynput/OpenPype/pull/4988">#4988</a></summary>


___

</details>




## [3.15.7](https://github.com/ynput/OpenPype/tree/3.15.7)


[Full Changelog](https://github.com/ynput/OpenPype/compare/3.15.6...3.15.7)

### **🆕 New features**


<details>
<summary>Addons directory <a href="https://github.com/ynput/OpenPype/pull/4893">#4893</a></summary>

This adds a directory for Addons, for easier distribution of studio specific code.


___

</details>


<details>
<summary>Kitsu - Add "image", "online" and "plate" to review families <a href="https://github.com/ynput/OpenPype/pull/4923">#4923</a></summary>

This PR adds "image", "online" and "plate" to the review families so they also can be uploaded to Kitsu.It also adds the `Add review to Kitsu` tag to the default png review. Without it the user would manually need to add it for single image uploads to Kitsu and might confuse users (it confused me first for a while as movies did work).


___

</details>


<details>
<summary>Feature/remove and load inv action <a href="https://github.com/ynput/OpenPype/pull/4930">#4930</a></summary>

Added the ability to remove and load a container, as a way to reset it.This can be useful in cases where a container breaks in a way that can be fixed by removing it, then reloading it.Also added the ability to add `InventoryAction` plugins by placing them in `openpype/plugins/inventory`.


___

</details>

### **🚀 Enhancements**


<details>
<summary>Load Rig References - Change Rig to Animation in Animation instance <a href="https://github.com/ynput/OpenPype/pull/4877">#4877</a></summary>

We are using the template builder to build an animation scene. All the rig placeholders are imported correctly, but the automatically created animation instances retain the rig family in their names and subsets. In our example, we need animationMain instead of rigMain, because this name will be used in the following steps like lighting.Here is the result we need. I checked, and it's not a template builder problem, because even if I load a rig as a reference, the result is the same. For me, since we are in the animation instance, it makes more sense to have animation instead of rig in the name. The naming is just fine if we use create from the Openpype menu.


___

</details>


<details>
<summary>Maya template builder - preserve all references when importing a template <a href="https://github.com/ynput/OpenPype/pull/4797">#4797</a></summary>

When building a template with Maya template builder, we import the template and also the references inside the template file. This causes some problems:
- We cannot use the references to version assets imported by the template.
- When we import the file, the internal reference files are also imported. As a side effect, Maya complains about a reference that no longer exists.`// Error: file: /xxx/maya/2023.3/linux/scripts/AETemplates/AEtransformRelated.mel line 58: Reference node 'turntable_mayaSceneMain_01_RN' is not associated with a reference file.`


___

</details>


<details>
<summary>Unreal: Renaming the integration plugin to Ayon. <a href="https://github.com/ynput/OpenPype/pull/4646">#4646</a></summary>

Renamed the .h, and .cpp files to Ayon. Also renamed the classes to with the Ayon keyword.


___

</details>


<details>
<summary>3dsMax: render dialogue needs to be closed <a href="https://github.com/ynput/OpenPype/pull/4729">#4729</a></summary>

Make sure the render setup dialog is in a closed state for the update of resolution and other render settings


___

</details>


<details>
<summary>Maya Template Builder - Remove default cameras from renderable cameras <a href="https://github.com/ynput/OpenPype/pull/4815">#4815</a></summary>

When we build an asset workfile with build workfile from template inside Maya, we load our turntable camera. But then we end up with 2 renderables camera : **persp** the one imported from the template.We need to remove the **persp** camera (or any other default camera) from renderable cameras when building the work file.


___

</details>


<details>
<summary>Validators for Frame Range in Max <a href="https://github.com/ynput/OpenPype/pull/4914">#4914</a></summary>

Switch Render Frame Range Type to 3 for specific ranges (initial setup for the range type is 4)Reset Frame Range will also set the frame range for render settingsRender Collector won't take the frame range from context data but take the range directly from render settingAdd validators for render frame range type and frame range respectively with repair action


___

</details>


<details>
<summary>Fusion: Saver creator settings <a href="https://github.com/ynput/OpenPype/pull/4943">#4943</a></summary>

Adding Saver creator settings and enhanced rendering path with template.


___

</details>


<details>
<summary>General: Project Anatomy on creators <a href="https://github.com/ynput/OpenPype/pull/4962">#4962</a></summary>

Anatomy object of current project is available on `CreateContext` and create plugins.


___

</details>

### **🐛 Bug fixes**


<details>
<summary>Maya: Validate shader name - OP-5903 <a href="https://github.com/ynput/OpenPype/pull/4971">#4971</a></summary>

Running the plugin would error with:
```
// TypeError: 'str' object cannot be interpreted as an integer
```Fixed and added setting `active`.


___

</details>


<details>
<summary>Houdini: Fix slow Houdini launch due to shelves generation <a href="https://github.com/ynput/OpenPype/pull/4829">#4829</a></summary>

Shelf generation during Houdini startup would add an insane amount of delay for the Houdini UI to launch correctly. By deferring the shelf generation this takes away the 5+ minutes of delay for the Houdini UI to launch.


___

</details>


<details>
<summary>Fusion - Fixed "optional validation" <a href="https://github.com/ynput/OpenPype/pull/4912">#4912</a></summary>

Added OptionalPyblishPluginMixin and is_active checks for all publish tools that should be optional


___

</details>


<details>
<summary>Bug: add missing `pyblish.util` import <a href="https://github.com/ynput/OpenPype/pull/4937">#4937</a></summary>

remote publishing was missing import of `remote_publish`. This is adding it back.


___

</details>


<details>
<summary>Unreal: Fix missing 'object_path' property <a href="https://github.com/ynput/OpenPype/pull/4938">#4938</a></summary>

Epic removed the `object_path` property from `AssetData`. This PR fixes usages of that property.Fixes #4936


___

</details>


<details>
<summary>Remove obsolete global validator <a href="https://github.com/ynput/OpenPype/pull/4939">#4939</a></summary>

Removing `Validate Sequence Frames` validator from global plugins as it wasn't handling correctly many things and was by mistake enabled, breaking functionality on Deadline.


___

</details>


<details>
<summary>General: fix build_workfile get_linked_assets missing project_name arg <a href="https://github.com/ynput/OpenPype/pull/4940">#4940</a></summary>

Linked assets collection don't work within `build_workfile` because `get_linked_assets` function call has a missing `project_name`argument.
- Added the `project_name` arg to the `get_linked_assets` function call.


___

</details>


<details>
<summary>General: fix Scene Inventory switch version error dialog missing parent arg on init <a href="https://github.com/ynput/OpenPype/pull/4941">#4941</a></summary>

QuickFix for the switch version error dialog to set inventory widget as parent.


___

</details>


<details>
<summary>Unreal: Fix camera frame range <a href="https://github.com/ynput/OpenPype/pull/4956">#4956</a></summary>

Fix the frame range of the level sequence for the Camera in Unreal.


___

</details>


<details>
<summary>Unreal: Fix missing parameter when updating Alembic StaticMesh <a href="https://github.com/ynput/OpenPype/pull/4957">#4957</a></summary>

Fix an error when updating an Alembic StaticMesh in Unreal, due to a missing parameter in a function call.


___

</details>


<details>
<summary>Unreal: Fix render extraction <a href="https://github.com/ynput/OpenPype/pull/4963">#4963</a></summary>

Fix a problem with the extraction of renders in Unreal.


___

</details>


<details>
<summary>Unreal: Remove Python 3.8 syntax from addon <a href="https://github.com/ynput/OpenPype/pull/4965">#4965</a></summary>

Removed Python 3.8 syntax from addon.


___

</details>


<details>
<summary>Ftrack: Fix editorial task creation <a href="https://github.com/ynput/OpenPype/pull/4966">#4966</a></summary>

Fix key assignment on instance data during editorial publishing in ftrack hierarchy integration.


___

</details>

### **Merged pull requests**


<details>
<summary>Add "shortcut" to Scripts Menu Definition <a href="https://github.com/ynput/OpenPype/pull/4927">#4927</a></summary>

Add the possibility to associate a shorcut for an entry in the script menu definition with the key "shortcut"


___

</details>




## [3.15.6](https://github.com/ynput/OpenPype/tree/3.15.6)


[Full Changelog](https://github.com/ynput/OpenPype/compare/3.15.5...3.15.6)

### **🆕 New features**


<details>
<summary>Substance Painter Integration <a href="https://github.com/ynput/OpenPype/pull/4283">#4283</a></summary>

<strong>This implements a part of #4205 by implementing a Substance Painter integration

</strong>Status:
- [x] Implement Host
- [x] start substance with last workfile using `AddLastWorkfileToLaunchArgs` prelaunch hook
- [x] Implement Qt tools
- [x] Implement loaders
- [x] Implemented a Set project mesh loader (this is relatively special case because a Project will always have exactly one mesh - a Substance Painter project cannot exist without a mesh).
- [x] Implement project open callback
- [x] On project open it notifies the user if the loaded model is outdated
- [x] Implement publishing logic
- [x] Workfile publishing
- [x] Export Texture Sets
- [x] Support OCIO using #4195 (draft brach is set up - see comment)
- [ ] Likely needs more testing on the OCIO front
- [x] Validate all outputs of the Export template are exported/generated
- [x] Allow validation to be optional **(issue: there's no API method to detect what maps will be exported without doing an actual export to disk)**
- [x] Support extracting/integration if not all outputs are generated
- [x] Support multiple materials/texture sets per instance
- [ ] Add validator that can enforce only a single texture set output if studio prefers that.
- [ ] Implement Export File Format (extensions) override in Creator
- [ ] Add settings so Admin can choose which extensions are available.


___

</details>


<details>
<summary>Data Exchange: Geometry in 3dsMax <a href="https://github.com/ynput/OpenPype/pull/4555">#4555</a></summary>

<strong>Introduces and updates a creator, extractors and loaders for model family

</strong>Introduces new creator, extractors and loaders for model family while adding model families into the existing max scene loader and extractor
- [x] creators
- [x]  adding model family into max scene loader and extractor
- [x]  fbx loader
- [x]  fbx extractor
- [x]  usd loader
- [x]  usd extractor
- [x] validator for model family
- [x]  obj loader(update function)
- [x]  fix the update function of the loader as #4675
- [x]  Add documentation


___

</details>


<details>
<summary>AfterEffects: add review flag to each instance <a href="https://github.com/ynput/OpenPype/pull/4884">#4884</a></summary>

Adds `mark_for_review` flag to the Creator to allow artists to disable review if necessary.Exposed this flag in Settings, by default set to True (eg. same behavior as previously).


___

</details>

### **🚀 Enhancements**


<details>
<summary>Houdini: Fix Validate Output Node (VDB) <a href="https://github.com/ynput/OpenPype/pull/4819">#4819</a></summary>

- Removes plug-in that was a duplicate of this plug-in.
- Optimize logging of many prims slightly
- Fix error reporting like https://github.com/ynput/OpenPype/pull/4818 did


___

</details>


<details>
<summary>Houdini: Add null node as output indicator when using TAB search <a href="https://github.com/ynput/OpenPype/pull/4834">#4834</a></summary>


___

</details>


<details>
<summary>Houdini: Don't error in collect review if camera is not set correctly <a href="https://github.com/ynput/OpenPype/pull/4874">#4874</a></summary>

Do not raise an error in collector when invalid path is set as camera path. Allow camera path to not be set correctly in review instance until validation so it's nicely shown in a validation report.


___

</details>


<details>
<summary>Project packager: Backup and restore can store only database <a href="https://github.com/ynput/OpenPype/pull/4879">#4879</a></summary>

Pack project functionality have option to zip only project database without project files. Unpack project can skip project copy if the folder is not found.Added helper functions to `openpype.client.mongo` that can be also used for tests as replacement of mongo dump.


___

</details>


<details>
<summary>Houdini: ExtractOpenGL for Review instance not optional <a href="https://github.com/ynput/OpenPype/pull/4881">#4881</a></summary>

Don't make ExtractOpenGL optional for review instance optional.


___

</details>


<details>
<summary>Publisher: Small style changes <a href="https://github.com/ynput/OpenPype/pull/4894">#4894</a></summary>

Small changes in styles and form of publisher UI.


___

</details>


<details>
<summary>Houdini: Workfile icon in new publisher <a href="https://github.com/ynput/OpenPype/pull/4898">#4898</a></summary>

Fix icon for the workfile instance in new publisher


___

</details>


<details>
<summary>Fusion: Simplify creator icons code <a href="https://github.com/ynput/OpenPype/pull/4899">#4899</a></summary>

Simplify code for setting the icons for the Fusion creators


___

</details>


<details>
<summary>Enhancement: Fix PySide 6.5 support for loader <a href="https://github.com/ynput/OpenPype/pull/4900">#4900</a></summary>

Fixes PySide 6.5 support in Loader.


___

</details>

### **🐛 Bug fixes**


<details>
<summary>Maya: Validate Attributes <a href="https://github.com/ynput/OpenPype/pull/4917">#4917</a></summary>

This plugin was broken due to bad fetching of data and wrong repair action.


___

</details>


<details>
<summary>Fix: Locally copied version of last published workfile is not incremented <a href="https://github.com/ynput/OpenPype/pull/4722">#4722</a></summary>

### Fix 1
When copied, the local workfile version keeps the published version number, when it must be +1 to follow OP's naming convention.

### Fix 2
Local workfile version's name is built from anatomy. This avoids to get workfiles with their publish template naming.

### Fix 3
In the case a subset has at least two tasks with published workfiles, for example `Modeling` and `Rigging`, launching `Rigging` was getting the first one with the `next` and trying to find representations, therefore `workfileModeling` and trying to match the current `task_name` (`Rigging`) with the `representation["context"]["task"]["name"]` of a Modeling representation, which was ending up to a `workfile_representation` to `None`, and exiting the process.

Trying to find the `task_name` in the `subset['name']` fixes it.

### Fix 4
Fetch input dependencies of workfile.

Replacing https://github.com/ynput/OpenPype/pull/4102 for changes to bring this home.
___

</details>


<details>
<summary>Maya: soft-fail when pan/zoom locked on camera when playblasting <a href="https://github.com/ynput/OpenPype/pull/4929">#4929</a></summary>

When pan/zoom enabled attribute on camera is locked, playblasting with pan/zoom fails because it is trying to restore it. This is fixing it by skipping over with warning.


___

</details>

### **Merged pull requests**


<details>
<summary>Maya Load References - Add Display Handle Setting <a href="https://github.com/ynput/OpenPype/pull/4904">#4904</a></summary>

When we load a reference in Maya using OpenPype loader, display handle is checked by default and prevent us to select easily the object in the viewport. I understand that some productions like to keep this option, so I propose to add display handle to the reference loader settings.


___

</details>


<details>
<summary>Photoshop: add autocreators for review and flat image <a href="https://github.com/ynput/OpenPype/pull/4871">#4871</a></summary>

Review and flatten image (produced when no instance of `image` family was created) were created somehow magically. This PRintroduces two new auto creators which allow artists to disable review or flatten image.For all `image` instances `Review` flag was added to provide functionality to create separate review per `image` instance. Previously was possible only to have separate instance of `review` family.Review is not enabled on `image` family by default. (Eg. follows original behavior)Review auto creator is enabled by default as it was before.Flatten image creator must be set in Settings in `project_settings/photoshop/create/AutoImageCreator`.


___

</details>




## [3.15.5](https://github.com/ynput/OpenPype/tree/3.15.5)


[Full Changelog](https://github.com/ynput/OpenPype/compare/3.15.4...3.15.5)

### **🚀 Enhancements**


<details>
<summary>Maya: Playblast profiles <a href="https://github.com/ynput/OpenPype/pull/4777">#4777</a></summary>

Support playblast profiles.This enables studios to customize what playblast settings should be on a per task and/or subset basis. For example `modeling` should have `Wireframe On Shaded` enabled, while all other tasks should have it disabled.


___

</details>


<details>
<summary>Maya: Support .abc files directly for Arnold standin look assignment <a href="https://github.com/ynput/OpenPype/pull/4856">#4856</a></summary>

If `.abc` file is loaded into arnold standin support look assignment through the `cbId` attributes in the alembic file.


___

</details>


<details>
<summary>Maya: Hide animation instance in creator <a href="https://github.com/ynput/OpenPype/pull/4872">#4872</a></summary>

- Hide animation instance in creator
- Add inventory action to recreate animation publish instance for loaded rigs


___

</details>


<details>
<summary>Unreal: Render Creator enhancements <a href="https://github.com/ynput/OpenPype/pull/4477">#4477</a></summary>

<strong>Improvements to the creator for render family

</strong>This PR introduces some enhancements to the creator for the render family in Unreal Engine:
- Added the option to create a new, empty sequence for the render.
- Added the option to not include the whole hierarchy for the selected sequence.
- Improvements of the error messages.


___

</details>


<details>
<summary>Unreal: Added settings for rendering <a href="https://github.com/ynput/OpenPype/pull/4575">#4575</a></summary>

<strong>Added settings for rendering in Unreal Engine.

</strong>Two settings has been added:
- Pre roll frames, to set how many frames are used to load the scene before starting the actual rendering.
- Configuration path, to allow to save a preset of settings from Unreal, and use it for rendering.


___

</details>


<details>
<summary>Global: Optimize anatomy formatting by only formatting used templates instead <a href="https://github.com/ynput/OpenPype/pull/4784">#4784</a></summary>

Optimization to not format full anatomy when only a single template is used. Instead format only the single template instead.


___

</details>


<details>
<summary>Patchelf version locked <a href="https://github.com/ynput/OpenPype/pull/4853">#4853</a></summary>

For Centos dockerfile it is necessary to lock the patchelf version to the older, otherwise the build process fails.

___

</details>


<details>
<summary>Houdini: Implement `switch` method on loaders <a href="https://github.com/ynput/OpenPype/pull/4866">#4866</a></summary>

Implement `switch` method on loaders


___

</details>


<details>
<summary>Code: Tweak docstrings and return type hints <a href="https://github.com/ynput/OpenPype/pull/4875">#4875</a></summary>

Tweak docstrings and return type hints for functions in `openpype.client.entities`.


___

</details>


<details>
<summary>Publisher: Clear comment on successful publish and on window close <a href="https://github.com/ynput/OpenPype/pull/4885">#4885</a></summary>

Clear comment text field on successful publish and on window close.


___

</details>


<details>
<summary>Publisher: Make sure to reset asset widget when hidden and reshown <a href="https://github.com/ynput/OpenPype/pull/4886">#4886</a></summary>

Make sure to reset asset widget when hidden and reshown. Without this the asset list would never refresh in the set asset widget when changing context on an existing instance and thus would not show new assets from after the first time launching that widget.


___

</details>

### **🐛 Bug fixes**


<details>
<summary>Maya: Fix nested model instances. <a href="https://github.com/ynput/OpenPype/pull/4852">#4852</a></summary>

Fix nested model instance under review instance, where data collection was not including "Display Lights" and "Focal Length".


___

</details>


<details>
<summary>Maya: Make default namespace naming backwards compatible <a href="https://github.com/ynput/OpenPype/pull/4873">#4873</a></summary>

Namespaces of loaded references are now _by default_ back to what they were before #4511


___

</details>


<details>
<summary>Nuke: Legacy convertor skips deprecation warnings <a href="https://github.com/ynput/OpenPype/pull/4846">#4846</a></summary>

Nuke legacy convertor was triggering deprecated function which is causing a lot of logs which slows down whole process. Changed the convertor to skip all nodes without `AVALON_TAB` to avoid the warnings.


___

</details>


<details>
<summary>3dsmax: move startup script logic to hook <a href="https://github.com/ynput/OpenPype/pull/4849">#4849</a></summary>

Startup script for OpenPype was interfering with Open Last Workfile feature. Moving this loggic from simple command line argument in the Settings to pre-launch hook is solving the order of command line arguments and making both features work.


___

</details>


<details>
<summary>Maya: Don't change time slider ranges in `get_frame_range` <a href="https://github.com/ynput/OpenPype/pull/4858">#4858</a></summary>

Don't change time slider ranges in `get_frame_range`


___

</details>


<details>
<summary>Maya: Looks - calculate hash for tx texture <a href="https://github.com/ynput/OpenPype/pull/4878">#4878</a></summary>

Texture hash is calculated for textures used in published look and it is used as key in dictionary. In recent changes, this hash is not calculated for TX files, resulting in `None` value as key in dictionary, crashing publishing. This PR is adding texture hash for TX files to solve that issue.


___

</details>


<details>
<summary>Houdini: Collect `currentFile` context data separate from workfile instance <a href="https://github.com/ynput/OpenPype/pull/4883">#4883</a></summary>

Fix publishing without an active workfile instance due to missing `currentFile` data.Now collect `currentFile` into context in houdini through context plugin no matter the active instances.


___

</details>


<details>
<summary>Nuke: fixed broken slate workflow once published on deadline <a href="https://github.com/ynput/OpenPype/pull/4887">#4887</a></summary>

Slate workflow is now working as expected and Validate Sequence Frames is not raising the once slate frame is included.


___

</details>


<details>
<summary>Add fps as instance.data in collect review in Houdini. <a href="https://github.com/ynput/OpenPype/pull/4888">#4888</a></summary>

fix the bug of failing to publish extract review in HoudiniOriginal error:
```python
  File "OpenPype\build\exe.win-amd64-3.9\openpype\plugins\publish\extract_review.py", line 516, in prepare_temp_data
    "fps": float(instance.data["fps"]),
KeyError: 'fps'
```


___

</details>


<details>
<summary>TrayPublisher: Fill missing data for instances with review <a href="https://github.com/ynput/OpenPype/pull/4891">#4891</a></summary>

Fill required data to instance in traypublisher if instance has review family. The data are required by ExtractReview and it would be complicated to do proper fix at this moment! The collector does for review instances what did https://github.com/ynput/OpenPype/pull/4383


___

</details>


<details>
<summary>Publisher: Keep track about current context and fix context selection widget <a href="https://github.com/ynput/OpenPype/pull/4892">#4892</a></summary>

Change selected context to current context on reset. Fix bug when context widget is re-enabled.


___

</details>


<details>
<summary>Scene inventory: Model refresh fix with cherry picking <a href="https://github.com/ynput/OpenPype/pull/4895">#4895</a></summary>

Fix cherry pick issue in scene inventory.


___

</details>


<details>
<summary>Nuke: Pre-render and missing review flag on instance causing crash <a href="https://github.com/ynput/OpenPype/pull/4897">#4897</a></summary>

If instance created in nuke was missing `review` flag, collector crashed.


___

</details>

### **Merged pull requests**


<details>
<summary>After Effects: fix handles KeyError <a href="https://github.com/ynput/OpenPype/pull/4727">#4727</a></summary>

Sometimes when publishing with AE (we only saw this error on AE 2023), we got a KeyError for the handles in the "Collect Workfile" step. So I did get the handles from the context if ther's no handles in the asset entity.


___

</details>




## [3.15.4](https://github.com/ynput/OpenPype/tree/3.15.4)


[Full Changelog](https://github.com/ynput/OpenPype/compare/3.15.3...3.15.4)

### **🆕 New features**


<details>
<summary>Maya: Cant assign shaders to the ass file - OP-4859  <a href="https://github.com/ynput/OpenPype/pull/4460">#4460</a></summary>

<strong>Support AiStandIn nodes for look assignment.

</strong>Using operators we assign shaders and attribute/parameters to nodes within standins. Initially there is only support for a limited mount of attributes but we can add support as needed;
```
primaryVisibility
castsShadows
receiveShadows
aiSelfShadows
aiOpaque
aiMatte
aiVisibleInDiffuseTransmission
aiVisibleInSpecularTransmission
aiVisibleInVolume
aiVisibleInDiffuseReflection
aiVisibleInSpecularReflection
aiSubdivUvSmoothing
aiDispHeight
aiDispPadding
aiDispZeroValue
aiStepSize
aiVolumePadding
aiSubdivType
aiSubdivIterations
```


___

</details>


<details>
<summary>Maya: GPU cache representation <a href="https://github.com/ynput/OpenPype/pull/4649">#4649</a></summary>

Implement GPU cache for model, animation and pointcache.


___

</details>


<details>
<summary>Houdini: Implement review family with opengl node <a href="https://github.com/ynput/OpenPype/pull/3839">#3839</a></summary>

<strong>Implements a first pass for Reviews publishing in Houdini. Resolves #2720

</strong>Uses the `opengl` ROP node to produce PNG images.


___

</details>


<details>
<summary>Maya: Camera focal length visible in review - OP-3278 <a href="https://github.com/ynput/OpenPype/pull/4531">#4531</a></summary>

<strong>Camera focal length visible in review.

</strong>Support camera focal length in review; static and dynamic.Resolves #3220


___

</details>


<details>
<summary>Maya: Defining plugins to load on Maya start - OP-4994 <a href="https://github.com/ynput/OpenPype/pull/4714">#4714</a></summary>

Feature to define plugins to load on Maya launch.


___

</details>


<details>
<summary>Nuke, DL: Returning Suspended Publishing attribute <a href="https://github.com/ynput/OpenPype/pull/4715">#4715</a></summary>

Old Nuke Publisher's feature for suspended publishing job on render farm was added back to the current Publisher.


___

</details>


<details>
<summary>Settings UI: Allow setting a size hint for text fields <a href="https://github.com/ynput/OpenPype/pull/4821">#4821</a></summary>

Text entity have `minimum_lines_count` which allows to change minimum size hint of UI input.


___

</details>


<details>
<summary>TrayPublisher: Move 'BatchMovieCreator' settings to 'create' subcategory <a href="https://github.com/ynput/OpenPype/pull/4827">#4827</a></summary>

Moved settings for `BatchMoviewCreator` into subcategory `create` in settings. Changes are made to match other hosts settings chema and structure.


___

</details>

### **🚀 Enhancements**


<details>
<summary>Maya looks: support for native Redshift texture format <a href="https://github.com/ynput/OpenPype/pull/2971">#2971</a></summary>

<strong>Add support for native Redshift textures handling. Closes #2599

</strong>Uses Redshift's Texture Processor executable to convert textures being used in renders to the Redshift ".rstexbin" format.


___

</details>


<details>
<summary>Maya: custom namespace for references <a href="https://github.com/ynput/OpenPype/pull/4511">#4511</a></summary>

<strong>Adding an option in Project Settings > Maya > Loader plugins to set custom namespace. If no namespace is set, the default one is used.

</strong>
___

</details>


<details>
<summary>Maya: Set correct framerange with handles on file opening <a href="https://github.com/ynput/OpenPype/pull/4664">#4664</a></summary>

Set the range of playback from the asset data, counting handles, to get the correct data when calling the "collect_animation_data" function.


___

</details>


<details>
<summary>Maya: Fix camera update <a href="https://github.com/ynput/OpenPype/pull/4751">#4751</a></summary>

Fix resetting any modelPanel to a different camera when loading a camera and updating.


___

</details>


<details>
<summary>Maya: Remove single assembly validation for animation instances <a href="https://github.com/ynput/OpenPype/pull/4840">#4840</a></summary>

Rig groups may now be parented to others groups when `includeParentHierarchy` attribute on the instance is "off".


___

</details>


<details>
<summary>Maya: Optional control of display lights on playblast. <a href="https://github.com/ynput/OpenPype/pull/4145">#4145</a></summary>

<strong>Optional control of display lights on playblast.

</strong>Giving control to what display lights are on the playblasts.


___

</details>


<details>
<summary>Kitsu: note family requirements <a href="https://github.com/ynput/OpenPype/pull/4551">#4551</a></summary>

<strong>Allowing to add family requirements to `IntegrateKitsuNote` task status change.

</strong>Adds a `Family requirements` setting to `Integrate Kitsu Note`, so you can add requirements to determine if kitsu task status should be changed based on which families are published or not. For instance you could have the status change only if another subset than workfile is published (but workfile can still be included) by adding an item set to `Not equal` and `workfile`.


___

</details>


<details>
<summary>Deactivate closed Kitsu projects on OP <a href="https://github.com/ynput/OpenPype/pull/4619">#4619</a></summary>

Deactivate project on OP when the project is closed on Kitsu.


___

</details>


<details>
<summary>Maya: Suggestion to change capture labels. <a href="https://github.com/ynput/OpenPype/pull/4691">#4691</a></summary>

Change capture labels.


___

</details>


<details>
<summary>Houdini: Change node type for OpenPypeContext `null` -> `subnet` <a href="https://github.com/ynput/OpenPype/pull/4745">#4745</a></summary>

Change the node type for OpenPype's hidden context node in Houdini from `null` to `subnet`. This fixes #4734


___

</details>


<details>
<summary>General: Extract burnin hosts filters <a href="https://github.com/ynput/OpenPype/pull/4749">#4749</a></summary>

Removed hosts filter from ExtractBurnin plugin. Instance without representations won't cause crash but just skip the instance. We've discovered because Blender already has review but did not create burnins.


___

</details>


<details>
<summary>Global: Improve speed of Collect Custom Staging Directory <a href="https://github.com/ynput/OpenPype/pull/4768">#4768</a></summary>

Improve speed of Collect Custom Staging Directory.


___

</details>


<details>
<summary>General: Anatomy templates formatting <a href="https://github.com/ynput/OpenPype/pull/4773">#4773</a></summary>

Added option to format only single template from anatomy instead of formatting all of them all the time. Formatting of all templates is causing slowdowns e.g. during publishing of hundreds of instances.


___

</details>


<details>
<summary>Harmony: Handle zip files with deeper structure <a href="https://github.com/ynput/OpenPype/pull/4782">#4782</a></summary>

External Harmony zip files might contain one additional level with scene name.


___

</details>


<details>
<summary>Unreal: Use common logic to configure executable <a href="https://github.com/ynput/OpenPype/pull/4788">#4788</a></summary>

Unreal Editor location and version was autodetected. This easied configuration in some cases but was not flexible enought. This PR is changing the way Unreal Editor location is set, unifying it with the logic other hosts are using.


___

</details>


<details>
<summary>Github: Grammar tweaks + uppercase issue title <a href="https://github.com/ynput/OpenPype/pull/4813">#4813</a></summary>

Tweak some of the grammar in the issue form templates.


___

</details>


<details>
<summary>Houdini: Allow creation of publish instances via Houdini TAB menu <a href="https://github.com/ynput/OpenPype/pull/4831">#4831</a></summary>

Register the available Creator's as houdini tools so an artist can add publish instances via the Houdini TAB node search menu from within the network editor.


___

</details>

### **🐛 Bug fixes**


<details>
<summary>Maya: Fix Collect Render for V-Ray, Redshift and Renderman for missing colorspace <a href="https://github.com/ynput/OpenPype/pull/4650">#4650</a></summary>

Fix Collect Render not working for Redshift, V-Ray and Renderman due to missing `colorspace` argument to `RenderProduct` dataclass.


___

</details>


<details>
<summary>Maya: Xgen fixes <a href="https://github.com/ynput/OpenPype/pull/4707">#4707</a></summary>

Fix for Xgen extraction of world parented nodes and validation for required namespace.


___

</details>


<details>
<summary>Maya: Fix extract review and thumbnail for Maya 2020 <a href="https://github.com/ynput/OpenPype/pull/4744">#4744</a></summary>

Fix playblasting in Maya 2020 with override viewport options enabled. Fixes #4730.


___

</details>


<details>
<summary>Maya: local variable 'arnold_standins' referenced before assignment - OP-5542 <a href="https://github.com/ynput/OpenPype/pull/4778">#4778</a></summary>

MayaLookAssigner erroring when MTOA is not loaded:
```
# Traceback (most recent call last):
#   File "\openpype\hosts\maya\tools\mayalookassigner\app.py", line 272, in on_process_selected
#     nodes = list(set(item["nodes"]).difference(arnold_standins))
# UnboundLocalError: local variable 'arnold_standins' referenced before assignment
```


___

</details>


<details>
<summary>Maya: Fix getting view and display in Maya 2020 - OP-5035 <a href="https://github.com/ynput/OpenPype/pull/4795">#4795</a></summary>

The `view_transform` returns a different format in Maya 2020. Fixes #4540 (hopefully).


___

</details>


<details>
<summary>Maya: Fix Look Maya 2020 Py2 support for Extract Look <a href="https://github.com/ynput/OpenPype/pull/4808">#4808</a></summary>

Fix Extract Look supporting python 2.7 for Maya 2020.


___

</details>


<details>
<summary>Maya: Fix Validate Mesh Overlapping UVs plugin <a href="https://github.com/ynput/OpenPype/pull/4816">#4816</a></summary>

Fix typo in the code where a maya command returns a `list` instead of `str`.


___

</details>


<details>
<summary>Maya: Fix tile rendering with Vray - OP-5566 <a href="https://github.com/ynput/OpenPype/pull/4832">#4832</a></summary>

Fixes tile rendering with Vray.


___

</details>


<details>
<summary>Deadline: checking existing frames fails when there is number in file name <a href="https://github.com/ynput/OpenPype/pull/4698">#4698</a></summary>

Previous implementation of validator failed on files with any other number in rendered file names.Used regular expression pattern now handles numbers in the file names  (eg "Main_beauty.v001.1001.exr", "Main_beauty_v001.1001.exr", "Main_beauty.1001.1001.exr") but not numbers behind frames (eg. "Main_beauty.1001.v001.exr")


___

</details>


<details>
<summary>Maya: Validate Render Settings. <a href="https://github.com/ynput/OpenPype/pull/4735">#4735</a></summary>

Fixes error message when using attribute validation.


___

</details>


<details>
<summary>General: Hero version sites recalculation <a href="https://github.com/ynput/OpenPype/pull/4737">#4737</a></summary>

Sites recalculation in integrate hero version did expect that it is integrated exactly same amount of files as in previous integration. This is not the case in many cases, so the sites recalculation happens in a different way, first are prepared all sites from previous representation files, and all of them are added to each file in new representation.


___

</details>


<details>
<summary>Houdini: Fix collect current file <a href="https://github.com/ynput/OpenPype/pull/4739">#4739</a></summary>

Fixes the Workfile publishing getting added into every instance being published from Houdini


___

</details>


<details>
<summary>Global: Fix Extract Burnin + Colorspace functions for conflicting python environments with PYTHONHOME <a href="https://github.com/ynput/OpenPype/pull/4740">#4740</a></summary>

This fixes the running of openpype processes from e.g. a host with conflicting python versions that had `PYTHONHOME` said additionally to `PYTHONPATH`, like e.g. Houdini Py3.7 together with OpenPype Py3.9 when using Extract Burnin for a review in #3839This fix applies to Extract Burnin and some of the colorspace functions that use `run_openpype_process`


___

</details>


<details>
<summary>Harmony: render what is in timeline in Harmony locally <a href="https://github.com/ynput/OpenPype/pull/4741">#4741</a></summary>

Previously it wasn't possible to render according to what was set in Timeline in scene start/end, just by what it was set in whole timeline.This allows artist to override what is in DB with what they require (with disabled `Validate Scene Settings`). Now artist can extend scene by additional frames, that shouldn't be rendered, but which might be desired.Removed explicit set scene settings (eg. applying frames and resolution directly to the scene after launch), added separate menu item to allow artist to do it themselves.


___

</details>


<details>
<summary>Maya: Extract Review settings add Use Background Gradient <a href="https://github.com/ynput/OpenPype/pull/4747">#4747</a></summary>

Add Display Gradient Background toggle in settings to fix support for setting flat background color for reviews.


___

</details>


<details>
<summary>Nuke: publisher is offering review on write families on demand <a href="https://github.com/ynput/OpenPype/pull/4755">#4755</a></summary>

Original idea where reviewable toggle will be offered in publisher on demand is fixed and now `review` attribute can be disabled in settings.


___

</details>


<details>
<summary>Workfiles: keep Browse always enabled <a href="https://github.com/ynput/OpenPype/pull/4766">#4766</a></summary>

Browse might make sense even if there are no workfiles present, actually in that case it makes the most sense (eg. I want to locate workfile from outside - from Desktop for example).


___

</details>


<details>
<summary>Global: label key in instance data is optional <a href="https://github.com/ynput/OpenPype/pull/4779">#4779</a></summary>

Collect OTIO review plugin is not crashing if `label` key is missing in instance data.


___

</details>


<details>
<summary>Loader: Fix missing variable <a href="https://github.com/ynput/OpenPype/pull/4781">#4781</a></summary>

There is missing variable `handles` in loader tool after https://github.com/ynput/OpenPype/pull/4746. The variable was renamed to `handles_label` and is initialized to `None` if handles are not available.


___

</details>


<details>
<summary>Nuke: Workfile Template builder fixes <a href="https://github.com/ynput/OpenPype/pull/4783">#4783</a></summary>

Popup window after Nuke start is not showing. Knobs with X/Y coordination on nodes where were converted from placeholders are not added if `keepPlaceholders` is witched off.


___

</details>


<details>
<summary>Maya: Add family filter 'review' to burnin profile with focal length <a href="https://github.com/ynput/OpenPype/pull/4791">#4791</a></summary>

Avoid profile burnin with `focalLength` key for renders, but use only for playblast reviews.


___

</details>


<details>
<summary>add farm instance to the render collector in 3dsMax <a href="https://github.com/ynput/OpenPype/pull/4794">#4794</a></summary>

bug fix for the failure of submitting publish job in 3dsmax


___

</details>


<details>
<summary>Publisher: Plugin active attribute is respected <a href="https://github.com/ynput/OpenPype/pull/4798">#4798</a></summary>

Publisher consider plugin's `active` attribute, so the plugin is not processed when `active` is set to `False`. But we use the attribute in `OptionalPyblishPluginMixin` for different purposes, so I've added hack bypass of the active state validation when plugin inherit from the mixin. This is temporary solution which cannot be changed until all hosts use Publisher otherwise global plugins would be broken. Also plugins which have `enabled` set to `False` are filtered out -> this happened only when automated settings were applied and the settings contained `"enabled"` key se to `False`.


___

</details>


<details>
<summary>Nuke: settings and optional attribute in publisher for some validators <a href="https://github.com/ynput/OpenPype/pull/4811">#4811</a></summary>

New publisher is supporting optional switch for plugins which is offered in Publisher in Right panel. Some plugins were missing this switch and also settings which would offer the optionality.


___

</details>


<details>
<summary>Settings: Version settings popup fix <a href="https://github.com/ynput/OpenPype/pull/4822">#4822</a></summary>

Version completer popup have issues on some platforms, this should fix those edge cases. Also fixed issue when completer stayed shown fater reset (save).


___

</details>


<details>
<summary>Hiero/Nuke: adding monitorOut key to settings <a href="https://github.com/ynput/OpenPype/pull/4826">#4826</a></summary>

New versions of Hiero were introduced with new colorspace property for Monitor Out. It have been added into project settings. Also added new config names into settings enumerator option.


___

</details>


<details>
<summary>Nuke: removed default workfile template builder preset <a href="https://github.com/ynput/OpenPype/pull/4835">#4835</a></summary>

Default for workfile template builder should have been empty.


___

</details>


<details>
<summary>TVPaint: Review can be made from any instance <a href="https://github.com/ynput/OpenPype/pull/4843">#4843</a></summary>

Add `"review"` tag to output of extract sequence if instance is marked for review. At this moment only instances with family `"review"` were able to define input for `ExtractReview` plugin which is not right.


___

</details>

### **🔀 Refactored code**


<details>
<summary>Deadline: Remove unused FramesPerTask job info submission <a href="https://github.com/ynput/OpenPype/pull/4657">#4657</a></summary>

Remove unused `FramesPerTask` job info submission to Deadline.


___

</details>


<details>
<summary>Maya: Remove pymel dependency <a href="https://github.com/ynput/OpenPype/pull/4724">#4724</a></summary>

Refactors code written using `pymel` to use standard maya python libraries instead like `maya.cmds` or `maya.api.OpenMaya`


___

</details>


<details>
<summary>Remove "preview" data from representation <a href="https://github.com/ynput/OpenPype/pull/4759">#4759</a></summary>

Remove "preview" data from representation


___

</details>


<details>
<summary>Maya: Collect Review cleanup code for attached subsets <a href="https://github.com/ynput/OpenPype/pull/4720">#4720</a></summary>

Refactor some code for Maya: Collect Review for attached subsets.


___

</details>


<details>
<summary>Refactor: Remove `handles`, `edit_in` and `edit_out` backwards compatibility <a href="https://github.com/ynput/OpenPype/pull/4746">#4746</a></summary>

Removes backward compatibiliy fallback for data called `handles`, `edit_in` and `edit_out`.


___

</details>

### **📃 Documentation**


<details>
<summary>Bump webpack from 5.69.1 to 5.76.1 in /website <a href="https://github.com/ynput/OpenPype/pull/4624">#4624</a></summary>

Bumps [webpack](https://github.com/webpack/webpack) from 5.69.1 to 5.76.1.
<details>
<summary>Release notes</summary>
<p><em>Sourced from <a href="https://github.com/webpack/webpack/releases">webpack's releases</a>.</em></p>
<blockquote>
<h2>v5.76.1</h2>
<h2>Fixed</h2>
<ul>
<li>Added <code>assert/strict</code> built-in to <code>NodeTargetPlugin</code></li>
</ul>
<h2>Revert</h2>
<ul>
<li>Improve performance of <code>hashRegExp</code> lookup by <a href="https://github.com/ryanwilsonperkin"><code>@​ryanwilsonperkin</code></a> in <a href="https://redirect.github.com/webpack/webpack/pull/16759">webpack/webpack#16759</a></li>
</ul>
<h2>v5.76.0</h2>
<h2>Bugfixes</h2>
<ul>
<li>Avoid cross-realm object access by <a href="https://github.com/Jack-Works"><code>@​Jack-Works</code></a> in <a href="https://redirect.github.com/webpack/webpack/pull/16500">webpack/webpack#16500</a></li>
<li>Improve hash performance via conditional initialization by <a href="https://github.com/lvivski"><code>@​lvivski</code></a> in <a href="https://redirect.github.com/webpack/webpack/pull/16491">webpack/webpack#16491</a></li>
<li>Serialize <code>generatedCode</code> info to fix bug in asset module cache restoration by <a href="https://github.com/ryanwilsonperkin"><code>@​ryanwilsonperkin</code></a> in <a href="https://redirect.github.com/webpack/webpack/pull/16703">webpack/webpack#16703</a></li>
<li>Improve performance of <code>hashRegExp</code> lookup by <a href="https://github.com/ryanwilsonperkin"><code>@​ryanwilsonperkin</code></a> in <a href="https://redirect.github.com/webpack/webpack/pull/16759">webpack/webpack#16759</a></li>
</ul>
<h2>Features</h2>
<ul>
<li>add <code>target</code> to <code>LoaderContext</code> type by <a href="https://github.com/askoufis"><code>@​askoufis</code></a> in <a href="https://redirect.github.com/webpack/webpack/pull/16781">webpack/webpack#16781</a></li>
</ul>
<h2>Security</h2>
<ul>
<li><a href="https://github.com/advisories/GHSA-3rfm-jhwj-7488">CVE-2022-37603</a> fixed by <a href="https://github.com/akhilgkrishnan"><code>@​akhilgkrishnan</code></a> in <a href="https://redirect.github.com/webpack/webpack/pull/16446">webpack/webpack#16446</a></li>
</ul>
<h2>Repo Changes</h2>
<ul>
<li>Fix HTML5 logo in README by <a href="https://github.com/jakebailey"><code>@​jakebailey</code></a> in <a href="https://redirect.github.com/webpack/webpack/pull/16614">webpack/webpack#16614</a></li>
<li>Replace TypeScript logo in README by <a href="https://github.com/jakebailey"><code>@​jakebailey</code></a> in <a href="https://redirect.github.com/webpack/webpack/pull/16613">webpack/webpack#16613</a></li>
<li>Update actions/cache dependencies by <a href="https://github.com/piwysocki"><code>@​piwysocki</code></a> in <a href="https://redirect.github.com/webpack/webpack/pull/16493">webpack/webpack#16493</a></li>
</ul>
<h2>New Contributors</h2>
<ul>
<li><a href="https://github.com/Jack-Works"><code>@​Jack-Works</code></a> made their first contribution in <a href="https://redirect.github.com/webpack/webpack/pull/16500">webpack/webpack#16500</a></li>
<li><a href="https://github.com/lvivski"><code>@​lvivski</code></a> made their first contribution in <a href="https://redirect.github.com/webpack/webpack/pull/16491">webpack/webpack#16491</a></li>
<li><a href="https://github.com/jakebailey"><code>@​jakebailey</code></a> made their first contribution in <a href="https://redirect.github.com/webpack/webpack/pull/16614">webpack/webpack#16614</a></li>
<li><a href="https://github.com/akhilgkrishnan"><code>@​akhilgkrishnan</code></a> made their first contribution in <a href="https://redirect.github.com/webpack/webpack/pull/16446">webpack/webpack#16446</a></li>
<li><a href="https://github.com/ryanwilsonperkin"><code>@​ryanwilsonperkin</code></a> made their first contribution in <a href="https://redirect.github.com/webpack/webpack/pull/16703">webpack/webpack#16703</a></li>
<li><a href="https://github.com/piwysocki"><code>@​piwysocki</code></a> made their first contribution in <a href="https://redirect.github.com/webpack/webpack/pull/16493">webpack/webpack#16493</a></li>
<li><a href="https://github.com/askoufis"><code>@​askoufis</code></a> made their first contribution in <a href="https://redirect.github.com/webpack/webpack/pull/16781">webpack/webpack#16781</a></li>
</ul>
<p><strong>Full Changelog</strong>: <a href="https://github.com/webpack/webpack/compare/v5.75.0...v5.76.0">https://github.com/webpack/webpack/compare/v5.75.0...v5.76.0</a></p>
<h2>v5.75.0</h2>
<h1>Bugfixes</h1>
<ul>
<li><code>experiments.*</code> normalize to <code>false</code> when opt-out</li>
<li>avoid <code>NaN%</code></li>
<li>show the correct error when using a conflicting chunk name in code</li>
<li>HMR code tests existance of <code>window</code> before trying to access it</li>
<li>fix <code>eval-nosources-*</code> actually exclude sources</li>
<li>fix race condition where no module is returned from processing module</li>
<li>fix position of standalong semicolon in runtime code</li>
</ul>
<h1>Features</h1>
<ul>
<li>add support for <code>@import</code> to extenal CSS when using experimental CSS in node</li>
</ul>
<!-- raw HTML omitted -->
</blockquote>
<p>... (truncated)</p>
</details>
<details>
<summary>Commits</summary>
<ul>
<li><a href="https://github.com/webpack/webpack/commit/21be52b681c477f8ebc41c1b0e7a7a8ac4fa7008"><code>21be52b</code></a> Merge pull request <a href="https://redirect.github.com/webpack/webpack/issues/16804">#16804</a> from webpack/chore-patch-release</li>
<li><a href="https://github.com/webpack/webpack/commit/1cce945dd6c3576d37d3940a0233fd087ce3f6ff"><code>1cce945</code></a> chore(release): 5.76.1</li>
<li><a href="https://github.com/webpack/webpack/commit/e76ad9e724410f10209caa2ba86875ca8cf5ed61"><code>e76ad9e</code></a> Merge pull request <a href="https://redirect.github.com/webpack/webpack/issues/16803">#16803</a> from ryanwilsonperkin/revert-16759-real-content-has...</li>
<li><a href="https://github.com/webpack/webpack/commit/52b1b0e4ada7c11e7f1b4f3d69b50684938c684e"><code>52b1b0e</code></a> Revert &quot;Improve performance of hashRegExp lookup&quot;</li>
<li><a href="https://github.com/webpack/webpack/commit/c989143379d344543e4161fec60f3a21beb9e3ce"><code>c989143</code></a> Merge pull request <a href="https://redirect.github.com/webpack/webpack/issues/16766">#16766</a> from piranna/patch-1</li>
<li><a href="https://github.com/webpack/webpack/commit/710eaf4ddaea505e040a24beeb45a769f9e3761b"><code>710eaf4</code></a> Merge pull request <a href="https://redirect.github.com/webpack/webpack/issues/16789">#16789</a> from dmichon-msft/contenthash-hashsalt</li>
<li><a href="https://github.com/webpack/webpack/commit/5d6446822aff579a5d3d9503ec2a16437d2f71d1"><code>5d64468</code></a> Merge pull request <a href="https://redirect.github.com/webpack/webpack/issues/16792">#16792</a> from webpack/update-version</li>
<li><a href="https://github.com/webpack/webpack/commit/67af5ec1f05fb7cf06be6acf27353aef105ddcbc"><code>67af5ec</code></a> chore(release): 5.76.0</li>
<li><a href="https://github.com/webpack/webpack/commit/97b1718720c33f1b17302a74c5284b01e02ec001"><code>97b1718</code></a> Merge pull request <a href="https://redirect.github.com/webpack/webpack/issues/16781">#16781</a> from askoufis/loader-context-target-type</li>
<li><a href="https://github.com/webpack/webpack/commit/b84efe6224b276bf72e4c5e2f4e76acddfaeef07"><code>b84efe6</code></a> Merge pull request <a href="https://redirect.github.com/webpack/webpack/issues/16759">#16759</a> from ryanwilsonperkin/real-content-hash-regex-perf</li>
<li>Additional commits viewable in <a href="https://github.com/webpack/webpack/compare/v5.69.1...v5.76.1">compare view</a></li>
</ul>
</details>
<details>
<summary>Maintainer changes</summary>
<p>This version was pushed to npm by <a href="https://www.npmjs.com/~evilebottnawi">evilebottnawi</a>, a new releaser for webpack since your current version.</p>
</details>
<br />


[![Dependabot compatibility score](https://dependabot-badges.githubapp.com/badges/compatibility_score?dependency-name=webpack&package-manager=npm_and_yarn&previous-version=5.69.1&new-version=5.76.1)](https://docs.github.com/en/github/managing-security-vulnerabilities/about-dependabot-security-updates#about-compatibility-scores)

Dependabot will resolve any conflicts with this PR as long as you don't alter it yourself. You can also trigger a rebase manually by commenting `@dependabot rebase`.

[//]: # (dependabot-automerge-start)
[//]: # (dependabot-automerge-end)

---

<details>
<summary>Dependabot commands and options</summary>
<br />

You can trigger Dependabot actions by commenting on this PR:
- `@dependabot rebase` will rebase this PR
- `@dependabot recreate` will recreate this PR, overwriting any edits that have been made to it
- `@dependabot merge` will merge this PR after your CI passes on it
- `@dependabot squash and merge` will squash and merge this PR after your CI passes on it
- `@dependabot cancel merge` will cancel a previously requested merge and block automerging
- `@dependabot reopen` will reopen this PR if it is closed
- `@dependabot close` will close this PR and stop Dependabot recreating it. You can achieve the same result by closing it manually
- `@dependabot ignore this major version` will close this PR and stop Dependabot creating any more for this major version (unless you reopen the PR or upgrade to it yourself)
- `@dependabot ignore this minor version` will close this PR and stop Dependabot creating any more for this minor version (unless you reopen the PR or upgrade to it yourself)
- `@dependabot ignore this dependency` will close this PR and stop Dependabot creating any more for this dependency (unless you reopen the PR or upgrade to it yourself)
- `@dependabot use these labels` will set the current labels as the default for future PRs for this repo and language
- `@dependabot use these reviewers` will set the current reviewers as the default for future PRs for this repo and language
- `@dependabot use these assignees` will set the current assignees as the default for future PRs for this repo and language
- `@dependabot use this milestone` will set the current milestone as the default for future PRs for this repo and language

You can disable automated security fix PRs for this repo from the [Security Alerts page](https://github.com/ynput/OpenPype/network/alerts).

</details>
___

</details>


<details>
<summary>Documentation: Add Extract Burnin documentation <a href="https://github.com/ynput/OpenPype/pull/4765">#4765</a></summary>

Add documentation for Extract Burnin global plugin settings.


___

</details>


<details>
<summary>Documentation: Move publisher related tips to publisher area <a href="https://github.com/ynput/OpenPype/pull/4772">#4772</a></summary>

Move publisher related tips for After Effects artist documentation to the correct position.


___

</details>


<details>
<summary>Documentation: Add extra terminology to the key concepts glossary <a href="https://github.com/ynput/OpenPype/pull/4838">#4838</a></summary>

Tweak some of the key concepts in the documentation.


___

</details>

### **Merged pull requests**


<details>
<summary>Maya: Refactor Extract Look with dedicated processors for maketx <a href="https://github.com/ynput/OpenPype/pull/4711">#4711</a></summary>

Refactor Maya extract look to fix some issues:
- [x] Allow Extraction with maketx with OCIO Color Management enabled in Maya.
- [x] Fix file hashing so it includes arguments to maketx, so that when arguments change it correctly generates a new hash
- [x] Fix maketx destination colorspace when OCIO is enabled
- [x] Use pre-collected colorspaces of the resources instead of trying to retrieve again in Extract Look
- [x] Fix colorspace attributes being reinterpreted by maya on export (fix remapping) - goal is to resolve #2337
- [x] Fix support for checking config path of maya default OCIO config (due to using `lib.get_color_management_preferences` which remaps that path)
- [x] Merged in #2971 to refactor MakeTX into TextureProcessor and also support generating Redshift `.rstexbin` files. - goal is to resolve #2599
- [x] Allow custom arguments to `maketx` from OpenPype Settings like mentioned here by @fabiaserra for arguments like: `--monochrome-detect`, `--opaque-detect`, `--checknan`.
- [x] Actually fix the code and make it work. :) (I'll try to keep below checkboxes in sync with my code changes)
- [x] Publishing without texture processor should work (no maketx + no rstexbin)
- [x] Publishing with maketx should work
- [x] Publishing with  rstexbin should work
- [x] Test it. (This is just me doing some test-runs, please still test the PR!)


___

</details>


<details>
<summary>Maya template builder load all assets linked to the shot <a href="https://github.com/ynput/OpenPype/pull/4761">#4761</a></summary>

Problem
All the assets of the ftrack project are loaded and not those linked to the shot

How get error
Open maya in the context of shot, then build a new scene with the "Build Workfile from template" button in "OpenPype" menu.
![image](https://user-images.githubusercontent.com/7068597/229124652-573a23d7-a2b2-4d50-81bf-7592c00d24dc.png)


___

</details>


<details>
<summary>Global: Do not force instance data with frame ranges of the asset <a href="https://github.com/ynput/OpenPype/pull/4383">#4383</a></summary>

<strong>This aims to resolve #4317

</strong>
___

</details>


<details>
<summary>Cosmetics: Fix some grammar in docstrings and messages (and some code) <a href="https://github.com/ynput/OpenPype/pull/4752">#4752</a></summary>

Tweak some grammar in codebase


___

</details>


<details>
<summary>Deadline: Submit publish job fails due root work hardcode - OP-5528 <a href="https://github.com/ynput/OpenPype/pull/4775">#4775</a></summary>

Generating config templates was hardcoded to `root[work]`. This PR fixes that.


___

</details>


<details>
<summary>CreateContext: Added option to remove Unknown attributes <a href="https://github.com/ynput/OpenPype/pull/4776">#4776</a></summary>

Added option to remove attributes with UnkownAttrDef on instances. Pop of key will also remove the attribute definition from attribute values, so they're not recreated again.


___

</details>



## [3.15.3](https://github.com/ynput/OpenPype/tree/3.15.3)


[Full Changelog](https://github.com/ynput/OpenPype/compare/3.15.2...3.15.3)

### **🆕 New features**


<details>
<summary>Blender: Extract Review <a href="https://github.com/ynput/OpenPype/pull/3616">#3616</a></summary>

<strong>Added Review to Blender.

</strong>This implementation is based on #3508 but made compatible for the current implementation of OpenPype for Blender.


___

</details>


<details>
<summary>Data Exchanges: Point Cloud for 3dsMax <a href="https://github.com/ynput/OpenPype/pull/4532">#4532</a></summary>

<strong>Publish PRT format with tyFlow in 3dsmax

</strong>Publish PRT format with tyFlow in 3dsmax and possibly set up loader to load the format too.
- [x] creator
- [x] extractor
- [x] validator
- [x] loader


___

</details>


<details>
<summary>Global: persistent staging directory for renders <a href="https://github.com/ynput/OpenPype/pull/4583">#4583</a></summary>

<strong>Allows configure if staging directory (`stagingDir`) should be persistent with use of profiles.

</strong>With this feature, users can specify a transient data folder path based on presets, which can be used during the creation and publishing stages. In some cases, these DCCs automatically add a rendering path during the creation stage, which is then used in publishing.One of the key advantages of this feature is that it allows users to take advantage of faster storages for rendering, which can help improve workflow efficiency. Additionally, this feature allows users to keep their rendered data persistent, and use their own infrastructure for regular cleaning.However, it should be noted that some productions may want to use this feature without persistency. Furthermore, there may be a need for retargeting the rendering folder to faster storages, which is also not supported at the moment.It is studio responsibility to clean up obsolete folders with data.Location of the folder is configured in `project_anatomy/templates/others`. ('transient' key is expected, with 'folder' key, could be more templates)Which family/task type/subset is applicable is configured in:`project_settings/global/tools/publish/transient_dir_profiles`


___

</details>


<details>
<summary>Kitsu custom comment template <a href="https://github.com/ynput/OpenPype/pull/4599">#4599</a></summary>

Kitsu allows to write markdown in its comment field. This can be something very powerful to deliver dynamic comments with the help the data from the instance.This feature is defaults to off so the admin have to manually set up the comment field the way they want.I have added a basic example on how the comment can look like as the comment-fields default value.To this I want to add some documentation also but that's on its way when the code itself looks good for the reviewers.


___

</details>


<details>
<summary>MaxScene Family  <a href="https://github.com/ynput/OpenPype/pull/4615">#4615</a></summary>

Introduction of the Max Scene Family


___

</details>

### **🚀 Enhancements**


<details>
<summary>Maya: Multiple values on single render attribute - OP-4131 <a href="https://github.com/ynput/OpenPype/pull/4631">#4631</a></summary>

When validating render attributes, this adds support for multiple values. When repairing first value in list is used.


___

</details>


<details>
<summary>Maya: enable 2D Pan/Zoom for playblasts - OP-5213 <a href="https://github.com/ynput/OpenPype/pull/4687">#4687</a></summary>

Setting for enabling 2D Pan/Zoom on reviews.


___

</details>


<details>
<summary>Copy existing or generate new Fusion profile on prelaunch <a href="https://github.com/ynput/OpenPype/pull/4572">#4572</a></summary>

<strong>Fusion preferences will be copied to the predefined `~/.openpype/hosts/fusion/prefs` folder (or any other folder set in system settings) on launch.

</strong>The idea is to create a copy of existing Fusion profile, adding an OpenPype menu to the Fusion instance.By default the copy setting is turned off, so no file copying is performed. Instead the clean Fusion profile is created by Fusion in the predefined folder. The default locaion is set to `~/.openpype/hosts/fusion/prefs`, to better comply with the other os platforms. After creating the default profile, some modifications are applied:
- forced Python3
- forced English interface
- setup Openpype specific path maps.If the `copy_prefs` checkbox is toggled, a copy of existing Fusion profile folder will be placed in the mentioned location. Then they are altered the same way as described above. The operation is run only once, on the first launch, unless the `force_sync [Resync profile on each launch]` is toggled.English interface is forced because the `FUSION16_PROFILE_DIR` environment variable is not read otherwise (seems to be a Fusion bug).


___

</details>


<details>
<summary>Houdini: Create button open new publisher's "create" tab <a href="https://github.com/ynput/OpenPype/pull/4601">#4601</a></summary>

During a talk with @maxpareschi he mentioned that the new publisher in Houdini felt super confusing due to "Create" going to the older creator but now being completely empty and the publish button directly went to the publish tab.This resolves that by fixing the Create button to now open the new publisher but on the Create tab.Also made publish button enforce going to the "publish" tab for consistency in usage.@antirotor I think changing the Create button's callback was just missed in this commit or was there a specific reason to not change that around yet?


___

</details>


<details>
<summary>Clockify: refresh and fix the integration <a href="https://github.com/ynput/OpenPype/pull/4607">#4607</a></summary>

Due to recent API changes, Clockify requires `user_id` to operate with the timers. I updated this part and currently it is a WIP for making it fully functional. Most functions, such as start and stop timer, and projects sync are currently working. For the rate limiting task new dependency is added: https://pypi.org/project/ratelimiter/


___

</details>


<details>
<summary>Fusion publish existing frames <a href="https://github.com/ynput/OpenPype/pull/4611">#4611</a></summary>

This PR adds the function to publish existing frames instead of having to re-render all of them for each new publish.I have split the render_locally plugin so the review-part is its own plugin now.I also change the saver-creator-plugin's label from Saver to Render (saver) as I intend to add a Prerender creator like in Nuke.


___

</details>


<details>
<summary>Resolution settings referenced from DB record for 3dsMax <a href="https://github.com/ynput/OpenPype/pull/4652">#4652</a></summary>

- Add Callback for setting the resolution according to DB after the new scene is created.
- Add a new Action into openpype menu which allows the user to reset the resolution in 3dsMax


___

</details>


<details>
<summary>3dsmax: render instance settings in Publish tab <a href="https://github.com/ynput/OpenPype/pull/4658">#4658</a></summary>

Allows user preset the pools, group and use_published settings in Render Creator in the Max Hosts.User can set the settings before or after creating instance in the new publisher


___

</details>


<details>
<summary>scene length setting referenced from DB record for 3dsMax <a href="https://github.com/ynput/OpenPype/pull/4665">#4665</a></summary>

Setting the timeline length based on DB record in 3dsMax Hosts


___

</details>


<details>
<summary>Publisher: Windows reduce command window pop-ups during Publishing <a href="https://github.com/ynput/OpenPype/pull/4672">#4672</a></summary>

Reduce the command line pop-ups that show on Windows during publishing.


___

</details>


<details>
<summary>Publisher: Explicit save <a href="https://github.com/ynput/OpenPype/pull/4676">#4676</a></summary>

Publisher have explicit button to save changes, so reset can happen without saving any changes. Save still happens automatically when publishing is started or on publisher window close. But a popup is shown if context of host has changed. Important context was enhanced by workfile path (if host integration supports it) so workfile changes are captured too. In that case a dialog with confirmation is shown to user. All callbacks that may require save of context were moved to main window to be able handle dialog show at one place. Save changes now returns success so the rest of logic is skipped -> publishing won't start, when save of instances fails.Save and reset buttons have shortcuts (Ctrl + s and Ctrls + r).


___

</details>


<details>
<summary>CelAction: conditional workfile parameters from settings <a href="https://github.com/ynput/OpenPype/pull/4677">#4677</a></summary>

Since some productions were requesting excluding some workfile parameters from publishing submission, we needed to move them to settings so those could be altered per project.


___

</details>


<details>
<summary>Improve logging of used app + tool envs on application launch <a href="https://github.com/ynput/OpenPype/pull/4682">#4682</a></summary>

Improve logging of what apps + tool environments got loaded for an application launch.


___

</details>


<details>
<summary>Fix name and docstring for Create Workdir Extra Folders prelaunch hook <a href="https://github.com/ynput/OpenPype/pull/4683">#4683</a></summary>

Fix class name and docstring for Create Workdir Extra Folders prelaunch hookThe class name and docstring were originally copied from another plug-in and didn't match the plug-in logic.This also fixes potentially seeing this twice in your logs. Before:After:Where it was actually running both this prelaunch hook and the actual `AddLastWorkfileToLaunchArgs` plugin.


___

</details>


<details>
<summary>Application launch context: Include app group name in logger <a href="https://github.com/ynput/OpenPype/pull/4684">#4684</a></summary>

Clarify in logs better what app group the ApplicationLaunchContext belongs to and what application is being launched.Before:After:


___

</details>


<details>
<summary>increment workfile version 3dsmax <a href="https://github.com/ynput/OpenPype/pull/4685">#4685</a></summary>

increment workfile version in 3dsmax as if in blender and maya hosts.


___

</details>

### **🐛 Bug fixes**


<details>
<summary>Maya: Fix getting non-active model panel. <a href="https://github.com/ynput/OpenPype/pull/2968">#2968</a></summary>

<strong>When capturing multiple cameras with image planes that have file sequences playing, only the active (first) camera will play through the file sequence.

</strong>
___

</details>


<details>
<summary>Maya: Fix broken review publishing. <a href="https://github.com/ynput/OpenPype/pull/4549">#4549</a></summary>

<strong>Resolves #4547

</strong>
___

</details>


<details>
<summary>Maya: Avoid error on right click in Loader if `mtoa` is not loaded <a href="https://github.com/ynput/OpenPype/pull/4616">#4616</a></summary>

Fix an error on right clicking in the Loader when `mtoa` is not a loaded plug-in.Additionally if `mtoa` isn't loaded the loader will now load the plug-in before trying to create the arnold standin.


___

</details>


<details>
<summary>Maya: Fix extract look colorspace detection <a href="https://github.com/ynput/OpenPype/pull/4618">#4618</a></summary>

Fix the logic which guesses the colorspace using `arnold` python library.
- Previously it'd error if `mtoa` was not available on path so it still required `mtoa` to be available.
- The guessing colorspace logic doesn't actually require `mtoa` to be loaded, but just the `arnold` python library to be available. This changes the logic so it doesn't require the `mtoa` plugin to get loaded to guess the colorspace.
- The if/else branch was likely not doing what was intended `cmds.loadPlugin("mtoa", quiet=True)` returns None if the plug-in was already loaded. So this would only ever be true if it ends up loading the `mtoa` plugin the first time.
```python
# Tested in Maya 2022.1
print(cmds.loadPlugin("mtoa", quiet=True))
# ['mtoa']
print(cmds.loadPlugin("mtoa", quiet=True))
# None
```


___

</details>


<details>
<summary>Maya: Maya Playblast Options overrides - OP-3847 <a href="https://github.com/ynput/OpenPype/pull/4634">#4634</a></summary>

When publishing a review in Maya, the extractor would fail due to wrong (long) panel name.


___

</details>


<details>
<summary>Bugfix/op 2834 fix extract playblast <a href="https://github.com/ynput/OpenPype/pull/4701">#4701</a></summary>

Paragraphs contain detailed information on the changes made to the product or service, providing an in-depth description of the updates and enhancements. They can be used to explain the reasoning behind the changes, or to highlight the importance of the new features. Paragraphs can often include links to further information or support documentation.


___

</details>


<details>
<summary>Bugfix/op 2834 fix extract playblast <a href="https://github.com/ynput/OpenPype/pull/4704">#4704</a></summary>

Paragraphs contain detailed information on the changes made to the product or service, providing an in-depth description of the updates and enhancements. They can be used to explain the reasoning behind the changes, or to highlight the importance of the new features. Paragraphs can often include links to further information or support documentation.


___

</details>


<details>
<summary>Maya: bug fix for passing zoom settings if review is attached to subset <a href="https://github.com/ynput/OpenPype/pull/4716">#4716</a></summary>

Fix for attaching review to subset with pan/zoom option.


___

</details>


<details>
<summary>Maya: tile assembly fail in draft - OP-4820 <a href="https://github.com/ynput/OpenPype/pull/4416">#4416</a></summary>

<strong>Tile assembly in Deadline was broken.

</strong>Initial bug report revealed other areas of the tile assembly that needed fixing.


___

</details>


<details>
<summary>Maya: Yeti Validate Rig Input - OP-3454 <a href="https://github.com/ynput/OpenPype/pull/4554">#4554</a></summary>

<strong>Fix Yeti Validate Rig Input

</strong>Existing workflow was broken due to this #3297.


___

</details>


<details>
<summary>Scene inventory: Fix code errors when "not found" entries are found <a href="https://github.com/ynput/OpenPype/pull/4594">#4594</a></summary>

Whenever a "NOT FOUND" entry is present a lot of errors happened in the Scene Inventory:
- It started spamming a lot of errors for the VersionDelegate since it had no numeric version (no version at all).Error reported on Discord:
```python
Traceback (most recent call last):
  File "C:\Users\videopro\Documents\github\OpenPype\openpype\tools\utils\delegates.py", line 65, in paint
    text = self.displayText(
  File "C:\Users\videopro\Documents\github\OpenPype\openpype\tools\utils\delegates.py", line 33, in displayText
    assert isinstance(value, numbers.Integral), (
AssertionError: Version is not integer. "None" <class 'NoneType'>
```
- Right click menu would error on NOT FOUND entries, and thus not show. With this PR it will now _disregard_ not found items for "Set version" and "Remove" but still allow actions.This PR resolves those.


___

</details>


<details>
<summary>Kitsu: Sync OP with zou, make sure value-data is int or float <a href="https://github.com/ynput/OpenPype/pull/4596">#4596</a></summary>

Currently the data zou pulls is a string and not a value causing some bugs in the pipe where a value is expected (like `Set frame range` in Fusion).



This PR makes sure each value is set with int() or float() so these bugs can't happen later on.



_(A request to cgwire has also bin sent to allow force values only for some metadata columns, but currently the user can enter what ever they want in there)_


___

</details>


<details>
<summary>Max: fix the bug of removing an instance <a href="https://github.com/ynput/OpenPype/pull/4617">#4617</a></summary>

fix the bug of removing an instance in 3dsMax


___

</details>


<details>
<summary>Global | Nuke: fixing farm publishing workflow <a href="https://github.com/ynput/OpenPype/pull/4623">#4623</a></summary>

After Nuke had adopted new publisher with new creators new issues were introduced. Those issues were addressed with this PR. Those are for example broken reviewable video files publishing if published via farm. Also fixed local publishing.


___

</details>


<details>
<summary>Ftrack: Ftrack additional families filtering <a href="https://github.com/ynput/OpenPype/pull/4633">#4633</a></summary>

Ftrack family collector makes sure the subset family is also in instance families for additional families filtering.


___

</details>


<details>
<summary>Ftrack: Hierarchical <> Non-Hierarchical attributes sync fix <a href="https://github.com/ynput/OpenPype/pull/4635">#4635</a></summary>

Sync between hierarchical and non-hierarchical attributes should be fixed and work as expected. Action should sync the values as expected and event handler should do it too and only on newly created entities.


___

</details>


<details>
<summary>bugfix for 3dsmax publishing error <a href="https://github.com/ynput/OpenPype/pull/4637">#4637</a></summary>

fix the bug of failing publishing job in 3dsMax


___

</details>


<details>
<summary>General: Use right validation for ffmpeg executable <a href="https://github.com/ynput/OpenPype/pull/4640">#4640</a></summary>

Use ffmpeg exec validation for ffmpeg executables instead of oiio exec validation. The validation is used as last possible source of ffmpeg from `PATH` environment variables, which is an edge case but can cause issues.


___

</details>


<details>
<summary>3dsmax: opening last workfile <a href="https://github.com/ynput/OpenPype/pull/4644">#4644</a></summary>

Supports opening last saved workfile in 3dsmax host.


___

</details>


<details>
<summary>Fixed a bug where a QThread in the splash screen could be destroyed before finishing execution <a href="https://github.com/ynput/OpenPype/pull/4647">#4647</a></summary>

This should fix the occasional behavior of the QThread being destroyed before even its worker returns from the `run()` function.After quiting, it should wait for the QThread object to properly close itself.


___

</details>


<details>
<summary>General: Use right plugin class for Collect Comment <a href="https://github.com/ynput/OpenPype/pull/4653">#4653</a></summary>

Collect Comment plugin is instance plugin so should inherit from `InstancePlugin` instead of `ContextPlugin`.


___

</details>


<details>
<summary>Global: add tags field to thumbnail representation <a href="https://github.com/ynput/OpenPype/pull/4660">#4660</a></summary>

Thumbnail representation might be missing tags field.


___

</details>


<details>
<summary>Integrator: Enforce unique destination transfers, disallow overwrites in queued transfers <a href="https://github.com/ynput/OpenPype/pull/4662">#4662</a></summary>

Fix #4656 by enforcing unique destination transfers in the Integrator. It's now disallowed to a destination in the file transaction queue with a new source path during the publish.


___

</details>


<details>
<summary>Hiero: Creator with correct workfile numeric padding input <a href="https://github.com/ynput/OpenPype/pull/4666">#4666</a></summary>

Creator was showing 99 in workfile input for long time, even if users set default value to 1001 in studio settings. This has been fixed now.


___

</details>


<details>
<summary>Nuke: Nukenodes family instance without frame range <a href="https://github.com/ynput/OpenPype/pull/4669">#4669</a></summary>

No need to add frame range data into `nukenodes` (backdrop) family publishes - since those are timeless.


___

</details>


<details>
<summary>TVPaint: Optional Validation plugins can be de/activated by user <a href="https://github.com/ynput/OpenPype/pull/4674">#4674</a></summary>

Added `OptionalPyblishPluginMixin` to TVpaint plugins that can be optional.


___

</details>


<details>
<summary>Kitsu: Slightly less strict with instance data <a href="https://github.com/ynput/OpenPype/pull/4678">#4678</a></summary>

- Allow to take task name from context if asset doesn't have any. Fixes an issue with Photoshop's review instance not having `task` in data.
- Allow to match "review" against both `instance.data["family"]` and `instance.data["families"]` because some instances don't have the primary family in families, e.g. in Photoshop and TVPaint.
- Do not error on Integrate Kitsu Review whenever for whatever reason Integrate Kitsu Note did not created a comment but just log the message that it was unable to connect a review.


___

</details>


<details>
<summary>Publisher: Fix reset shortcut sequence <a href="https://github.com/ynput/OpenPype/pull/4694">#4694</a></summary>

Fix bug created in https://github.com/ynput/OpenPype/pull/4676 where key sequence is checked using unsupported method. The check was changed to convert event into `QKeySequence` object which can be compared to prepared sequence.


___

</details>


<details>
<summary>Refactor _capture <a href="https://github.com/ynput/OpenPype/pull/4702">#4702</a></summary>

Paragraphs contain detailed information on the changes made to the product or service, providing an in-depth description of the updates and enhancements. They can be used to explain the reasoning behind the changes, or to highlight the importance of the new features. Paragraphs can often include links to further information or support documentation.


___

</details>


<details>
<summary>Hiero: correct container colors if UpToDate <a href="https://github.com/ynput/OpenPype/pull/4708">#4708</a></summary>

Colors on loaded containers are now correctly identifying real state of version. `Red` for out of date and `green` for up to date.


___

</details>

### **🔀 Refactored code**


<details>
<summary>Look Assigner: Move Look Assigner tool since it's Maya only <a href="https://github.com/ynput/OpenPype/pull/4604">#4604</a></summary>

Fix #4357: Move Look Assigner tool to maya since it's Maya only


___

</details>


<details>
<summary>Maya: Remove unused functions from Extract Look <a href="https://github.com/ynput/OpenPype/pull/4671">#4671</a></summary>

Remove unused functions from Maya Extract Look plug-in


___

</details>


<details>
<summary>Extract Review code refactor <a href="https://github.com/ynput/OpenPype/pull/3930">#3930</a></summary>

<strong>Trying to reduce complexity of Extract Review plug-in
- Re-use profile filtering from lib
- Remove "combination families" additional filtering which supposedly was from OP v2
- Simplify 'formatting' for filling gaps
- Use `legacy_io.Session` over `os.environ`

</strong>
___

</details>


<details>
<summary>Maya: Replace last usages of Qt module <a href="https://github.com/ynput/OpenPype/pull/4610">#4610</a></summary>

Replace last usage of `Qt` module with `qtpy`. This change is needed for `PySide6` support. All changes happened in Maya loader plugins.


___

</details>


<details>
<summary>Update tests and documentation for  `ColormanagedPyblishPluginMixin` <a href="https://github.com/ynput/OpenPype/pull/4612">#4612</a></summary>

Refactor `ExtractorColormanaged` to `ColormanagedPyblishPluginMixin` in tests and documentation.


___

</details>


<details>
<summary>Improve logging of used app + tool envs on application launch (minor tweak) <a href="https://github.com/ynput/OpenPype/pull/4686">#4686</a></summary>

Use `app.full_name` for change done in #4682


___

</details>

### **📃 Documentation**


<details>
<summary>Docs/add architecture document <a href="https://github.com/ynput/OpenPype/pull/4344">#4344</a></summary>

<strong>Add `ARCHITECTURE.md` document.

</strong>his document attemps to give a quick overview of the project to help onboarding, it's not an extensive documentation but more of a elevator pitch one-line descriptions of files/directories and what the attempt to do.


___

</details>


<details>
<summary>Documentation: Tweak grammar and fix some typos <a href="https://github.com/ynput/OpenPype/pull/4613">#4613</a></summary>

This resolves some grammar and typos in the documentation.Also fixes the extension of some images in after effects docs which used uppercase extension even though files were lowercase extension.


___

</details>


<details>
<summary>Docs: Fix some minor grammar/typos <a href="https://github.com/ynput/OpenPype/pull/4680">#4680</a></summary>

Typo/grammar fixes in documentation.


___

</details>

### **Merged pull requests**


<details>
<summary>Maya: Implement image file node loader <a href="https://github.com/ynput/OpenPype/pull/4313">#4313</a></summary>

<strong>Implements a loader for loading texture image into a `file` node in Maya.

</strong>Similar to Maya's hypershade creation of textures on load you have the option to choose for three modes of creating:
- Texture
- Projection
- StencilThese should match what Maya generates if you create those in Maya.
- [x] Load and manage file nodes
- [x] Apply color spaces after #4195
- [x] Support for _either_ UDIM or image sequence - currently it seems to always load sequences as UDIM automatically.
- [ ] Add support for animation sequences of UDIM textures using the `<f>.<udim>.exr` path format?


___

</details>


<details>
<summary>Maya Look Assigner: Don't rely on containers for get all assets <a href="https://github.com/ynput/OpenPype/pull/4600">#4600</a></summary>

This resolves #4044 by not actually relying on containers in the scene but instead just rely on finding nodes with `cbId` attributes. As such, imported nodes would also be found and a shader can be assigned (similar to when using get from selection).**Please take into consideration the potential downsides below**Potential downsides would be:
- IF an already loaded look has any dagNodes, say a 3D Projection node - then that will also show up as a loaded asset where previously nodes from loaded looks were ignored.
- If any dag nodes were created locally - they would have gotten `cbId` attributes on scene save and thus the current asset would almost always show?


___

</details>


<details>
<summary>Maya: Unify menu labels for "Set Frame Range" and "Set Resolution" <a href="https://github.com/ynput/OpenPype/pull/4605">#4605</a></summary>

Fix #4109: Unify menu labels for "Set Frame Range" and "Set Resolution"This also tweaks it in Houdini from Reset Frame Range to Set Frame Range.


___

</details>


<details>
<summary>Resolve missing OPENPYPE_MONGO in deadline global job preload  <a href="https://github.com/ynput/OpenPype/pull/4484">#4484</a></summary>

<strong>In the GlobalJobPreLoad plugin, we propose to replace the SpawnProcess by a sub-process and to pass the environment variables in the parameters, since the SpawnProcess under Centos Linux does not pass the environment variables.

</strong>In the GlobalJobPreLoad plugin, the Deadline SpawnProcess is used to start the OpenPype process. The problem is that the SpawnProcess does not pass environment variables, including OPENPYPE_MONGO, to the process when it is under Centos7 linux, and the process gets stuck. We propose to replace it by a subprocess and to pass the variable in the parameters.


___

</details>


<details>
<summary>Tests: Added setup_only to tests <a href="https://github.com/ynput/OpenPype/pull/4591">#4591</a></summary>

Allows to download test zip, unzip and restore DB in preparation for new test.


___

</details>


<details>
<summary>Maya: Arnold don't reset maya timeline frame range on render creation (or setting render settings) <a href="https://github.com/ynput/OpenPype/pull/4603">#4603</a></summary>

Fix #4429: Do not reset fps or playback timeline on applying or creating render settings


___

</details>


<details>
<summary>Bump @sideway/formula from 3.0.0 to 3.0.1 in /website <a href="https://github.com/ynput/OpenPype/pull/4609">#4609</a></summary>

Bumps [@sideway/formula](https://github.com/sideway/formula) from 3.0.0 to 3.0.1.
<details>
<summary>Commits</summary>
<ul>
<li><a href="https://github.com/hapijs/formula/commit/5b44c1bffc38135616fb91d5ad46eaf64f03d23b"><code>5b44c1b</code></a> 3.0.1</li>
<li><a href="https://github.com/hapijs/formula/commit/9fbc20a02d75ae809c37a610a57802cd1b41b3fe"><code>9fbc20a</code></a> chore: better number regex</li>
<li><a href="https://github.com/hapijs/formula/commit/41ae98e0421913b100886adb0107a25d552d9e1a"><code>41ae98e</code></a> Cleanup</li>
<li><a href="https://github.com/hapijs/formula/commit/c59f35ec401e18cead10e0cedfb44291517610b1"><code>c59f35e</code></a> Move to Sideway</li>
<li>See full diff in <a href="https://github.com/sideway/formula/compare/v3.0.0...v3.0.1">compare view</a></li>
</ul>
</details>
<details>
<summary>Maintainer changes</summary>
<p>This version was pushed to npm by <a href="https://www.npmjs.com/~marsup">marsup</a>, a new releaser for <code>@​sideway/formula</code> since your current version.</p>
</details>
<br />


[![Dependabot compatibility score](https://dependabot-badges.githubapp.com/badges/compatibility_score?dependency-name=@sideway/formula&package-manager=npm_and_yarn&previous-version=3.0.0&new-version=3.0.1)](https://docs.github.com/en/github/managing-security-vulnerabilities/about-dependabot-security-updates#about-compatibility-scores)

Dependabot will resolve any conflicts with this PR as long as you don't alter it yourself. You can also trigger a rebase manually by commenting `@dependabot rebase`.

[//]: # (dependabot-automerge-start)
[//]: # (dependabot-automerge-end)

---

<details>
<summary>Dependabot commands and options</summary>
<br />

You can trigger Dependabot actions by commenting on this PR:
- `@dependabot rebase` will rebase this PR
- `@dependabot recreate` will recreate this PR, overwriting any edits that have been made to it
- `@dependabot merge` will merge this PR after your CI passes on it
- `@dependabot squash and merge` will squash and merge this PR after your CI passes on it
- `@dependabot cancel merge` will cancel a previously requested merge and block automerging
- `@dependabot reopen` will reopen this PR if it is closed
- `@dependabot close` will close this PR and stop Dependabot recreating it. You can achieve the same result by closing it manually
- `@dependabot ignore this major version` will close this PR and stop Dependabot creating any more for this major version (unless you reopen the PR or upgrade to it yourself)
- `@dependabot ignore this minor version` will close this PR and stop Dependabot creating any more for this minor version (unless you reopen the PR or upgrade to it yourself)
- `@dependabot ignore this dependency` will close this PR and stop Dependabot creating any more for this dependency (unless you reopen the PR or upgrade to it yourself)
- `@dependabot use these labels` will set the current labels as the default for future PRs for this repo and language
- `@dependabot use these reviewers` will set the current reviewers as the default for future PRs for this repo and language
- `@dependabot use these assignees` will set the current assignees as the default for future PRs for this repo and language
- `@dependabot use this milestone` will set the current milestone as the default for future PRs for this repo and language

You can disable automated security fix PRs for this repo from the [Security Alerts page](https://github.com/ynput/OpenPype/network/alerts).

</details>
___

</details>


<details>
<summary>Update artist_hosts_maya_arnold.md <a href="https://github.com/ynput/OpenPype/pull/4626">#4626</a></summary>

Correct Arnold docs.
___

</details>


<details>
<summary>Maya: Add "Include Parent Hierarchy" option in animation creator plugin <a href="https://github.com/ynput/OpenPype/pull/4645">#4645</a></summary>

Add an option in Project Settings > Maya > Creator Plugins > Create Animation to include (or not) parent hierarchy. This is to avoid artists to check manually the option for all create animation.


___

</details>


<details>
<summary>General: Filter available applications <a href="https://github.com/ynput/OpenPype/pull/4667">#4667</a></summary>

Added option to filter applications that don't have valid executable available in settings in launcher and ftrack actions. This option can be disabled in new settings category `Applications`. The filtering is by default disabled.


___

</details>


<details>
<summary>3dsmax: make sure that startup script executes <a href="https://github.com/ynput/OpenPype/pull/4695">#4695</a></summary>

Fixing reliability of OpenPype startup in 3dsmax.


___

</details>


<details>
<summary>Project Manager: Change minimum frame start/end to '0' <a href="https://github.com/ynput/OpenPype/pull/4719">#4719</a></summary>

Project manager can have frame start/end set to `0`.


___

</details>



## [3.15.2](https://github.com/ynput/OpenPype/tree/3.15.2)

[Full Changelog](https://github.com/ynput/OpenPype/compare/3.15.1...3.15.2)

### **🆕 New features**


<details>
<summary>maya gltf texture convertor and validator <a href="https://github.com/ynput/OpenPype/pull/4261">#4261</a></summary>

<strong>Continuity of the gltf extractor implementation

</strong>Continuity of the gltf extractor https://github.com/pypeclub/OpenPype/pull/4192UPDATE:**Validator for GLSL Shader**:  Validate whether the mesh uses GLSL Shader. If not it will error out. The user can choose to perform the repair action and it will help to assign glsl shader. If the mesh with Stringray PBS, the repair action will also check to see if there is any linked texture such as Color, Occulsion, and Normal Map. If yes, it will help to relink the related textures to the glsl shader.*****If the mesh uses the PBS Shader,


___

</details>


<details>
<summary>Unreal: New Publisher <a href="https://github.com/ynput/OpenPype/pull/4370">#4370</a></summary>

<strong>Implementation of the new publisher for Unreal.

</strong>The implementation of the new publisher for Unreal. This PR includes the changes for all the existing creators to be compatible with the new publisher.The basic creator has been split in two distinct creators:
- `UnrealAssetCreator`, works with assets in the Content Browser.
- `UnrealActorCreator` that works with actors in the scene.


___

</details>


<details>
<summary>Implementation of a new splash screen <a href="https://github.com/ynput/OpenPype/pull/4592">#4592</a></summary>

Implemented a new splash screen widget to reflect a process running in the background. This widget can be used for other tasks than UE. **Also fixed the compilation error of the AssetContainer.cpp when trying to build the plugin in UE 5.0**


___

</details>


<details>
<summary>Deadline for 3dsMax <a href="https://github.com/ynput/OpenPype/pull/4439">#4439</a></summary>

<strong>Setting up deadline for 3dsmax

</strong>Setting up deadline for 3dsmax by setting render outputs and viewport camera


___

</details>


<details>
<summary>Nuke: adding nukeassist  <a href="https://github.com/ynput/OpenPype/pull/4494">#4494</a></summary>

<strong>Adding support for NukeAssist

</strong>For support of NukeAssist we had to limit some Nuke features since NukeAssist itself Nuke with limitations. We do not support Creator and Publisher. User can only Load versions with version control. User can also set Framerange and Colorspace.


___

</details>

### **🚀 Enhancements**


<details>
<summary>Maya: OP-2630 acescg maya <a href="https://github.com/ynput/OpenPype/pull/4340">#4340</a></summary>

<strong>Resolves #2712

</strong>
___

</details>


<details>
<summary>Default Ftrack Family on RenderLayer <a href="https://github.com/ynput/OpenPype/pull/4458">#4458</a></summary>

<strong>With default settings, renderlayers in Maya were not being tagged with the Ftrack family leading to confusion when doing reviews.

</strong>
___

</details>


<details>
<summary>Maya: Maya Playblast Options - OP-3783 <a href="https://github.com/ynput/OpenPype/pull/4487">#4487</a></summary>

<strong>Replacement PR for #3912. Adds more options for playblasts to preferences/settings.

</strong>Adds the following as options in generating playblasts, matching viewport settings.
- Use default material
- Wireframe on shaded
- X-ray
- X-ray Joints
- X-ray active component


___

</details>


<details>
<summary>Maya: Passing custom attributes to alembic - OP-4111 <a href="https://github.com/ynput/OpenPype/pull/4516">#4516</a></summary>

<strong>Passing custom attributes to alembic

</strong>This PR makes it possible to pass all user defined attributes along to the alembic representation.


___

</details>


<details>
<summary>Maya: Options for VrayProxy output - OP-2010 <a href="https://github.com/ynput/OpenPype/pull/4525">#4525</a></summary>

<strong>Options for output of VrayProxy.

</strong>Client requested more granular control of output from VrayProxy instance. Exposed options on the instance and settings for vrmesh and alembic.


___

</details>


<details>
<summary>Maya: Validate missing instance attributes <a href="https://github.com/ynput/OpenPype/pull/4559">#4559</a></summary>

<strong>Validate missing instance attributes.

</strong>New attributes can be introduced as new features come in. Old instances will need to be updated with these attributes for the documentation to make sense, and users do not have to recreate the instances.


___

</details>


<details>
<summary>Refactored Generation of UE Projects, installation of plugins moved to the engine <a href="https://github.com/ynput/OpenPype/pull/4369">#4369</a></summary>

<strong>Improved the way how OpenPype works with generation of UE projects. Also the installation of the plugin has been altered to install into the engine

</strong>OpenPype now uses the appropriate tools to generate UE projects. Unreal Build Tool (UBT) and a "Commandlet Project" is needed to properly generate a BP project, or C++ code in case that `dev_mode = True`, folders, the .uproject file and many other resources.On the plugin's side, it is built seperately with the UnrealAutomationTool (UAT) and then it's contents are moved under the `Engine/Plugins/Marketplace/OpenPype` directory.


___

</details>


<details>
<summary>Unreal: Use client functions in Layout loader  <a href="https://github.com/ynput/OpenPype/pull/4578">#4578</a></summary>

<strong>Use 'get_representations' instead of 'legacy_io' query in layout loader.

</strong>This is removing usage of `find_one` called on `legacy_io` and use rather client functions as preparation for AYON connection. Also all representations are queried at once instead of one by one.


___

</details>


<details>
<summary>General: Support for extensions filtering in loaders <a href="https://github.com/ynput/OpenPype/pull/4492">#4492</a></summary>

<strong>Added extensions filtering support to loader plugins.

</strong>To avoid possible backwards compatibility break is filtering exactly the same and filtering by extensions is enabled only if class attribute 'extensions' is set.


___

</details>


<details>
<summary>Nuke: multiple reformat in baking review profiles <a href="https://github.com/ynput/OpenPype/pull/4514">#4514</a></summary>

<strong>Added support for multiple reformat nodes in baking profiles.

</strong>Old settings for single reformat node is supported and prioritised just in case studios are using it and backward compatibility is needed. Warnings in Nuke terminal are notifying users to switch settings to new workflow. Settings are also explaining the migration way.


___

</details>


<details>
<summary>Nuke: Add option to use new creating system in workfile template builder <a href="https://github.com/ynput/OpenPype/pull/4545">#4545</a></summary>

<strong>Nuke workfile template builder can use new creators instead of legacy creators.

</strong>Modified workfile template builder to have option to say if legacy creators should be used or new creators. Legacy creators are disabled by default, so Maya has changed the value.


___

</details>


<details>
<summary>Global, Nuke: Workfile first version with template processing <a href="https://github.com/ynput/OpenPype/pull/4579">#4579</a></summary>

<strong>Supporting new template workfile builder with toggle for creation of first version of workfile in case there is none yet.

</strong>
___

</details>


<details>
<summary>Fusion: New Publisher <a href="https://github.com/ynput/OpenPype/pull/4523">#4523</a></summary>

<strong>This is an updated PR for @BigRoy 's old PR (https://github.com/ynput/OpenPype/pull/3892).I have merged it with code from OP 3.15.1-nightly.6 and made sure it works as expected.This converts the old publishing system to the new one. It implements Fusion as a new host addon.

</strong>
- Create button removed in OpenPype menu in favor of the new Publisher
- Draft refactor validations to raise PublishValidationError
- Implement Creator for New Publisher
- Implement Fusion as Host addon


___

</details>


<details>
<summary>TVPaint: Use Publisher tool <a href="https://github.com/ynput/OpenPype/pull/4471">#4471</a></summary>

<strong>Use Publisher tool and new creation system in TVPaint integration.

</strong>Using new creation system makes TVPaint integration a little bit easier to maintain for artists. Removed unneeded tools Creator and Subset Manager tools. Goal is to keep the integration work as close as possible to previous integration. Some changes were made but primarilly because they were not right using previous system.All creators create instance with final family instead of changing the family during extraction. Render passes are not related to group id but to render layer instance. Render layer is still related to group. Workfile, review and scene render instances are created using autocreators instead of auto-collection during publishing. Subset names are fully filled during publishing but instance labels are filled on refresh with the last known right value. Implemented basic of legacy convertor which should convert render layers and render passes.


___

</details>


<details>
<summary>TVPaint: Auto-detect render creation <a href="https://github.com/ynput/OpenPype/pull/4496">#4496</a></summary>

<strong>Create plugin which will create Render Layer and Render Pass instances based on information in the scene.

</strong>Added new creator that must be triggered by artist. The create plugin will first create Render Layer instances if were not created yet. For variant is used color group name. The creator has option to rename color groups by template defined in settings -> Template may use index of group by it's usage in scene (from bottom to top). After Render Layers will create Render Passes. Render Pass is created for each individual TVPaint layer in any group that had created Render Layer. It's name is used as variant (pass).


___

</details>


<details>
<summary>TVPaint: Small enhancements <a href="https://github.com/ynput/OpenPype/pull/4501">#4501</a></summary>

<strong>Small enhancements in TVPaint integration which did not get to https://github.com/ynput/OpenPype/pull/4471.

</strong>It was found out that `opacity` returned from `tv_layerinfo` is always empty and is dangerous to add it to layer information. Added information about "current" layer to layers information. Disable review of Render Layer and Render Pass instances by default. In most of productions is used only "scene review". Skip usage of `"enabled"` key from settings in automated layer/pass creation.


___

</details>


<details>
<summary>Global: color v3 global oiio transcoder plugin <a href="https://github.com/ynput/OpenPype/pull/4291">#4291</a></summary>

<strong>Implements possibility to use `oiiotool` to transcode image sequences from one color space to another(s).

</strong>Uses collected `colorspaceData` information about source color spaces, these information needs to be collected previously in each DCC interested in color management.Uses profiles configured in Settings to create single or multiple new representations (and file extensions) with different color spaces.New representations might replace existing one, each new representation might contain different tags and custom tags to control its integration step.


___

</details>


<details>
<summary>Deadline: Added support for multiple install dirs in Deadline <a href="https://github.com/ynput/OpenPype/pull/4451">#4451</a></summary>

<strong>SearchDirectoryList returns FIRST existing so if you would have multiple OP install dirs, it won't search for appropriate version in later ones.

</strong>
___

</details>


<details>
<summary>Ftrack: Upload reviewables with original name <a href="https://github.com/ynput/OpenPype/pull/4483">#4483</a></summary>

<strong>Ftrack can integrate reviewables with original filenames.

</strong>As ftrack have restrictions about names of components the only way how to achieve the result was to upload the same file twice, one with required name and one with origin name.


___

</details>


<details>
<summary>TVPaint: Ignore transparency in Render Pass <a href="https://github.com/ynput/OpenPype/pull/4499">#4499</a></summary>

<strong>It is possible to ignore layers transparency during Render Pass extraction.

</strong>Render pass extraction does not respect opacity of TVPaint layers set in scene during extraction. It can be enabled/disabled in settings.


___

</details>


<details>
<summary>Anatomy: Preparation for different root overrides <a href="https://github.com/ynput/OpenPype/pull/4521">#4521</a></summary>

<strong>Prepare Anatomy to handle only 'studio' site override on it's own.

</strong>Change how Anatomy fill root overrides based on requested site name. The logic which decide what is active site was moved to sync server addon and the same for receiving root overrides of local site. The Anatomy resolve only studio site overrides anything else is handled by sync server. BaseAnatomy only expect root overrides value and does not need site name. Validation of site name happens in sync server same as resolving if site name is local or not.


___

</details>


<details>
<summary>Nuke | Global: colormanaged plugin in collection <a href="https://github.com/ynput/OpenPype/pull/4556">#4556</a></summary>

<strong>Colormanaged extractor had changed to Mixin class so it can be added to any stage of publishing rather then just to Exctracting.Nuke is no collecting colorspaceData to representation collected on already rendered images.

</strong>Mixin class can no be used as secondary  parent in publishing plugins.


___

</details>

### **🐛 Bug fixes**


<details>
<summary>look publishing and srgb colorspace in maya  <a href="https://github.com/ynput/OpenPype/pull/4276">#4276</a></summary>

<strong>Check the OCIO color management is enabled before doing linearize colorspace for converting the texture maps into tx files.

</strong>Check whether the OCIO color management is enabled before the condition of converting the texture to tx extension.


___

</details>


<details>
<summary>Maya: extract Thumbnail "No active model panel found" - OP-3849 <a href="https://github.com/ynput/OpenPype/pull/4421">#4421</a></summary>

<strong>Error when extracting playblast with no model panel.

</strong>If `project_settings/maya/publish/ExtractPlayblast/capture_preset/Viewport Options/override_viewport_options` were off and publishing without showing any model panel, the extraction would fail.


___

</details>


<details>
<summary>Maya: Fix setting scene fps with float input <a href="https://github.com/ynput/OpenPype/pull/4488">#4488</a></summary>

<strong>Returned value of float fps on integer values would return float.

</strong>This PR fixes the case when switching between integer fps values for example 24 > 25. Issue was when setting the scene fps, the original float value was used which makes it unpredictable whether the value is float or integer when mapping the fps values.


___

</details>


<details>
<summary>Maya: Multipart fix <a href="https://github.com/ynput/OpenPype/pull/4497">#4497</a></summary>

<strong>Fix multipart logic in render products.

</strong>Each renderer has a different way of defining whether output images is multipart, so we need to define it for each renderer. Also before the `multipart` class variable was defined multiple times in several places, which made it tricky to debug where `multipart` was defined. Now its created on initialization and referenced as `self.multipart`


___

</details>


<details>
<summary>Maya: Set pool on tile assembly - OP-2012 <a href="https://github.com/ynput/OpenPype/pull/4520">#4520</a></summary>

<strong>Set pool on tile assembly

</strong>Pool for publishing and tiling jobs, need to use the settings (`project_settings/deadline/publish/ProcessSubmittedJobOnFarm/deadline_pool`) else fallback on primary pool (`project_settings/deadline/publish/CollectDeadlinePools/primary_pool`)


___

</details>


<details>
<summary>Maya: Extract review with handles <a href="https://github.com/ynput/OpenPype/pull/4527">#4527</a></summary>

<strong>Review was not extracting properly with/without handles.

</strong>Review instance was not created properly resulting in the frame range on the instance including handles.


___

</details>


<details>
<summary>Maya: Fix broken lib. <a href="https://github.com/ynput/OpenPype/pull/4529">#4529</a></summary>

<strong>Fix broken lib.

</strong>This commit from this PR broke the Maya lib module.


___

</details>


<details>
<summary>Maya: Validate model name - OP-4983 <a href="https://github.com/ynput/OpenPype/pull/4539">#4539</a></summary>

<strong>Validate model name issues.

</strong>Couple of issues with validate model name;
- missing platform extraction from settings
- map function should be list comprehension
- code cosmetics


___

</details>


<details>
<summary>Maya: SkeletalMesh family loadable as reference <a href="https://github.com/ynput/OpenPype/pull/4573">#4573</a></summary>

<strong>In Maya, fix the SkeletalMesh family not loadable as reference.

</strong>
___

</details>


<details>
<summary>Unreal: fix loaders because of missing AssetContainer <a href="https://github.com/ynput/OpenPype/pull/4536">#4536</a></summary>

<strong>Fixing Unreal loaders, where changes in OpenPype Unreal integration plugin deleted AssetContainer.

</strong>`AssetContainer` and `AssetContainerFactory` are still used to mark loaded instances. Because of optimizations in Integration plugin we've accidentally removed them but that broke loader.


___

</details>


<details>
<summary>3dsmax unable to delete loaded asset in the scene inventory <a href="https://github.com/ynput/OpenPype/pull/4507">#4507</a></summary>

<strong>Fix the bug of being unable to delete loaded asset in the Scene Inventory

</strong>Fix the bug of being unable to delete loaded asset in the Scene Inventory


___

</details>


<details>
<summary>Hiero/Nuke: originalBasename editorial publishing and loading <a href="https://github.com/ynput/OpenPype/pull/4453">#4453</a></summary>

<strong>Publishing and loading `originalBasename` is working as expected

</strong>Frame-ranges on version document is now correctly defined to fit original media frame range which is published. It means loading is now correctly identifying frame start and end on clip loader in Nuke.


___

</details>


<details>
<summary>Nuke: Fix workfile template placeholder creation <a href="https://github.com/ynput/OpenPype/pull/4512">#4512</a></summary>

<strong>Template placeholder creation was erroring out in Nuke due to the Workfile template builder not being able to find any of the plugins for the Nuke host.

</strong>Move `get_workfile_build_placeholder_plugins` function to NukeHost class as workfile template builder expects.


___

</details>


<details>
<summary>Nuke: creator farm attributes from deadline submit plugin settings <a href="https://github.com/ynput/OpenPype/pull/4519">#4519</a></summary>

<strong>Defaults in farm attributes are sourced from settings.

</strong>Settings for deadline nuke submitter are now used during nuke render and prerender creator plugins.


___

</details>


<details>
<summary>Nuke: fix clip sequence loading <a href="https://github.com/ynput/OpenPype/pull/4574">#4574</a></summary>

<strong>Nuke is loading correctly clip  from image sequence created without "{originalBasename}" token in anatomy template.

</strong>
___

</details>


<details>
<summary>Fusion: Fix files collection and small bug-fixes <a href="https://github.com/ynput/OpenPype/pull/4423">#4423</a></summary>

<strong>Fixed Fusion review-representation and small bug-fixes

</strong>This fixes the problem with review-file generation that stopped the publishing on second publish before the fix.The problem was that Fusion simply looked at all the files in the render-folder instead of only gathering the needed frames for the review.Also includes a fix to get the handle start/end that before throw an error if the data didn't exist (like from a kitsu sync).


___

</details>


<details>
<summary>Fusion: Updated render_local.py to not only process the first instance <a href="https://github.com/ynput/OpenPype/pull/4522">#4522</a></summary>

Moved the `__hasRun` to `render_once()` so the check only happens with the rendering. Currently only the first render node gets the representations added.Critical PR


___

</details>


<details>
<summary>Fusion: Load sequence fix filepath resolving from representation <a href="https://github.com/ynput/OpenPype/pull/4580">#4580</a></summary>

<strong>Resolves issue mentioned on discord by @movalex:The loader was incorrectly trying to find the file in the publish folder which resulted in just picking 'any first file'.

</strong>This gets the filepath from representation instead of taking the first file from listing files from publish folder.


___

</details>


<details>
<summary>Fusion: Fix review burnin start and end frame <a href="https://github.com/ynput/OpenPype/pull/4590">#4590</a></summary>

Fix the burnin start and end frame for reviews. Without this the asset document's start and end handle would've been added to the _burnin_ frame range even though that would've been incorrect since the handles are based on the comp saver's render range instead.


___

</details>


<details>
<summary>Harmony: missing set of frame range when opening scene <a href="https://github.com/ynput/OpenPype/pull/4485">#4485</a></summary>

<strong>Frame range gets set from DB everytime scene is opened.

</strong>Added also check for not up-to-date loaded containers.


___

</details>


<details>
<summary>Photoshop: context is not changed in publisher <a href="https://github.com/ynput/OpenPype/pull/4570">#4570</a></summary>

<strong>When PS is already open and artists launch new task, it should keep only opened PS open, but change context.

</strong>Problem were occurring in Workfile app where under new task files from old task were shown. This fixes this and adds opening of last workfile for new context if workfile exists.


___

</details>


<details>
<summary>hiero: fix effect item node class <a href="https://github.com/ynput/OpenPype/pull/4543">#4543</a></summary>

<strong>Collected effect name after renaming is saving correct class name.

</strong>
___

</details>


<details>
<summary>Bugfix/OP-4616 vray multipart <a href="https://github.com/ynput/OpenPype/pull/4297">#4297</a></summary>

<strong>This fixes a bug where multipart vray renders would not make a review in Ftrack.

</strong>
___

</details>


<details>
<summary>Maya: Fix changed location of reset_frame_range <a href="https://github.com/ynput/OpenPype/pull/4491">#4491</a></summary>

<strong>Location in commands caused cyclic import

</strong>
___

</details>


<details>
<summary>global: source template fixed frame duplication <a href="https://github.com/ynput/OpenPype/pull/4503">#4503</a></summary>

<strong>Duplication is not happening.

</strong>Template is using `originalBasename` which already assume all necessary elements are part of the file name so there was no need for additional optional name elements.


___

</details>


<details>
<summary>Deadline: Hint to use Python 3 <a href="https://github.com/ynput/OpenPype/pull/4518">#4518</a></summary>

<strong>Added shebank to give deadline hint which python should be used.

</strong>Deadline has issues with Python 2 (especially with `os.scandir`). When a shebank is added to file header deadline will use python 3 mode instead of python 2 which fix the issue.


___

</details>


<details>
<summary>Publisher: Prevent access to create tab after publish start <a href="https://github.com/ynput/OpenPype/pull/4528">#4528</a></summary>

<strong>Prevent access to create tab after publish start.

</strong>Disable create button in instance view on publish start and enable it again on reset. Even with that make sure that it is not possible to go to create tab if the tab is disabled.


___

</details>


<details>
<summary>Color Transcoding: store target_colorspace as new colorspace <a href="https://github.com/ynput/OpenPype/pull/4544">#4544</a></summary>

<strong>When transcoding into new colorspace, representation must carry this information instead original color space.

</strong>
___

</details>


<details>
<summary>Deadline: fix submit_publish_job <a href="https://github.com/ynput/OpenPype/pull/4552">#4552</a></summary>

<strong>Fix submit_publish_job

</strong>Resolves #4541


___

</details>


<details>
<summary>Kitsu: Fix task itteration in update-op-with-zou <a href="https://github.com/ynput/OpenPype/pull/4577">#4577</a></summary>

From the last PR (https://github.com/ynput/OpenPype/pull/4425) a comment-commit last second messed up the code and resulted in two lines being the same, crashing the script. This PR fixes that.
___

</details>


<details>
<summary>AttrDefs: Fix type for PySide6 <a href="https://github.com/ynput/OpenPype/pull/4584">#4584</a></summary>

<strong>Use right type in signal emit for value change of attribute definitions.

</strong>Changed `UUID` type to `str`. This is not an issue with PySide2 but it is with PySide6.


___

</details>

### **🔀 Refactored code**


<details>
<summary>Scene Inventory: Avoid using ObjectId <a href="https://github.com/ynput/OpenPype/pull/4524">#4524</a></summary>

<strong>Avoid using conversion to ObjectId type in scene inventory tool.

</strong>Preparation for AYON compatibility where ObjectId won't be used for ids. Representation ids from loaded containers are not converted to ObjectId but kept as strings which also required some changes when working with representation documents.


___

</details>

### **Merged pull requests**


<details>
<summary>SiteSync: host dirmap is not working properly <a href="https://github.com/ynput/OpenPype/pull/4563">#4563</a></summary>

<strong>If artists uses SiteSync with real remote (gdrive, dropbox, sftp) drive, Local Settings were throwing error `string indices must be integers`.

</strong>Logic was reworked to provide only `local_drive` values to be overrriden by Local Settings. If remote site is `gdrive` etc. mapping to `studio` is provided as it is expected that workfiles will have imported from `studio` location and not from `gdrive` folder.Also Nuke dirmap was reworked to be less verbose and much faster.


___

</details>


<details>
<summary>General: Input representation ids are not ObjectIds <a href="https://github.com/ynput/OpenPype/pull/4576">#4576</a></summary>

<strong>Don't use `ObjectId` as representation ids during publishing.

</strong>Representation ids are kept as strings during publishing instead of converting them to `ObjectId`. This change is pre-requirement for AYON connection.Inputs are used for integration of links and for farm publishing (or at least it looks like).


___

</details>


<details>
<summary>Shotgrid: Fixes on Deadline submissions <a href="https://github.com/ynput/OpenPype/pull/4498">#4498</a></summary>

<strong>A few other bug fixes for getting Nuke submission to Deadline work smoothly using Shotgrid integration.

</strong>Continuing on the work done on this other PR this fixes a few other bugs I came across with further tests.


___

</details>


<details>
<summary>Fusion: New Publisher <a href="https://github.com/ynput/OpenPype/pull/3892">#3892</a></summary>

<strong>This converts the old publishing system to the new one. It implements Fusion as a new host addon.

</strong>
- Create button removed in OpenPype menu in favor of the new Publisher
- Draft refactor validations to raise `PublishValidationError`
- Implement Creator for New Publisher
- Implement Fusion as Host addon


___

</details>


<details>
<summary>Make Kitsu work with Tray Publisher, added kitsureview tag, fixed sync-problems. <a href="https://github.com/ynput/OpenPype/pull/4425">#4425</a></summary>

<strong>Make Kitsu work with Tray Publisher, added kitsureview tag, fixed sync-problems.

</strong>This PR updates the way the module gather info for the current publish so it now works with Tray Publisher.It fixes the data that gets synced from Kitsu to OP so all needed data gets registered even if it doesn't exist on Kitsus side.It also adds the tag "Add review to Kitsu" and adds it to Burn In so previews gets generated by default to Kitsu.


___

</details>


<details>
<summary>Maya: V-Ray Set Image Format from settings <a href="https://github.com/ynput/OpenPype/pull/4566">#4566</a></summary>

<strong>Resolves #4565

</strong>Set V-Ray Image Format using settings.


___

</details>




## [3.15.1](https://github.com/ynput/OpenPype/tree/3.15.1)

[Full Changelog](https://github.com/ynput/OpenPype/compare/3.15.0...3.15.1)

### **🆕 New features**




<details>
<summary>Maya: Xgen (<i><font color='#367F6C';>3d</font> </i> <i><font style='color:#365E7F';>/ maya</font></i> ) - <a href="https://github.com/ynput/OpenPype/pull/4256">#4256</a></summary>

___

#### Brief description

Initial Xgen implementation.



#### Description

Client request of Xgen pipeline.




___

</details>



<details>
<summary>Data exchange cameras for 3d Studio Max (<i><font color='#367F6C';>3d</font> </i> <i><font style='color:#365E7F';>/ 3dsmax</font></i> ) - <a href="https://github.com/ynput/OpenPype/pull/4376">#4376</a></summary>

___

#### Brief description

Add Camera Family into the 3d Studio Max



#### Description

Adding Camera Extractors(extract abc camera and extract fbx camera) and validators(for camera contents) into 3dMaxAlso add the extractor for exporting 3d max raw scene (which is also related to 3dMax Scene Family) for camera family




___

</details>


### **🚀 Enhancements**




<details>
<summary>Adding path validator for non-maya nodes (<i><font color='#367F6C';>3d</font> </i> <i><font style='color:#365E7F';>/ maya</font></i> ) - <a href="https://github.com/ynput/OpenPype/pull/4271">#4271</a></summary>

___

#### Brief description

Adding a path validator for filepaths from non-maya nodes, which are created by plugins such as Renderman, Yeti and abcImport.



#### Description

As File Path Editor cannot catch the wrong filenpaths from non-maya nodes such as AlembicNodes, It is neccessary to have a new validator to ensure the existence of the filepaths from the nodes.




___

</details>



<details>
<summary>Deadline: Allow disabling strict error check in Maya submissions (<i><font color='#367F6C';>3d</font> </i> <i><font style='color:#365E7F';>/ maya</font></i> <i><font style='color:#1E1B7B';>/ deadline</font></i> ) - <a href="https://github.com/ynput/OpenPype/pull/4420">#4420</a></summary>

___

#### Brief description

DL by default has Strict error checking, but some errors are not fatal.



#### Description

This allows to set profile based on Task and Subset values to temporarily disable Strict Error Checks.Subset and task names should support regular expressions. (not wildcard notation though).




___

</details>



<details>
<summary>Houdini: New publisher code tweak (<i><font color='#367F6C';>3d</font> </i> <i><font style='color:#365E7F';>/ houdini</font></i> ) - <a href="https://github.com/ynput/OpenPype/pull/4374">#4374</a></summary>

___

#### Brief description

This is cosmetics only - the previous code to me felt quite unreadable due to the lengthy strings being used.



#### Description

Code should do roughly the same, but just be reformatted.




___

</details>



<details>
<summary>3dsmax: enhance alembic loader update function (<i><font color='#367F6C';>3d</font> </i> <i><font style='color:#365E7F';>/ 3dsmax</font></i> ) - <a href="https://github.com/ynput/OpenPype/pull/4387">#4387</a></summary>

___

## Enhancement



This PR is adding update/switch ability to pointcache/alembic loader in 3dsmax and fixing wrong tool shown when clicking on "Manage" item on OpenPype menu, that is now correctly Scene Inventory (but was Subset Manager).



Alembic update has still one caveat - it doesn't cope with changed number of object inside alembic, since loading alembic in max involves creating all those objects as first class nodes. So it will keep the objects in scene, just update path to alembic file on them.
___

</details>



<details>
<summary>Global: supporting `OPENPYPE_TMPDIR` in staging dir maker (<i><font color='#367F6C';>editorial</font> </i> <i><font style='color:#365E7F';>/ hiero</font></i> ) - <a href="https://github.com/ynput/OpenPype/pull/4398">#4398</a></summary>

___

#### Brief description

Productions can use OPENPYPE_TMPDIR for staging temp publishing directory



#### Description

Studios were demanding to be able to configure their own shared storages as temporary staging directories. Template formatting is also supported with optional keys formatting and following anatomy keys:    - root[work | <root name key>]    - project[name | code]




___

</details>



<details>
<summary>General: Functions for current context (<i><font color='#367F6C';>other</font> </i> ) - <a href="https://github.com/ynput/OpenPype/pull/4324">#4324</a></summary>

___

#### Brief description

Defined more functions to receive current context information and added the methods to host integration so host can affect the result.



#### Description

This is one of steps to reduce usage of `legacy_io.Session`. This change define how to receive current context information -> call functions instead of accessing `legacy_io.Session` or `os.environ` directly. Plus, direct access on session or environments is unfortunatelly not enough for some DCCs where multiple workfiles can be opened at one time which can heavily affect the context but host integration sometimes can't affect that at all.`HostBase` already had implemented `get_current_context`, that was enhanced by adding more specific methods `get_current_project_name`, `get_current_asset_name` and `get_current_task_name`. The same functions were added to `~/openpype/pipeline/cotext_tools.py`. The functions in context tools are calling host integration methods (if are available) otherwise are using environent variables as default implementation does. Also was added `get_current_host_name` to receive host name from registered host if is available or from environment variable.




___

</details>



<details>
<summary>Houdini: Do not visualize the hidden OpenPypeContext node (<i><font color='#367F6C';>other</font> </i> <i><font style='color:#365E7F';>/ houdini</font></i> ) - <a href="https://github.com/ynput/OpenPype/pull/4382">#4382</a></summary>

___

#### Brief description

Using the new publisher UI would generate a visible 'null' locator at the origin. It's confusing to the user since it's supposed to be 'hidden'.



#### Description

Before this PR the user would see a locator/null at the origin which was the 'hidden' `/obj/OpenPypeContext` node. This null would suddenly appear if the user would've ever opened the Publisher UI once.After this PR it will not show:Nice and tidy.




___

</details>



<details>
<summary>Maya + Blender: Pyblish plugins removed unused `version` and `category` attributes (<i><font color='#367F6C';>other</font> </i> ) - <a href="https://github.com/ynput/OpenPype/pull/4402">#4402</a></summary>

___

#### Brief description

Once upon a time in a land far far away there lived a few plug-ins who felt like they didn't belong in generic boxes and felt they needed to be versioned well above others. They tried, but with no success.



#### Description

Even though they now lived in a universe with elaborate `version` and `category` attributes embedded into their tiny little plug-in DNA this particular deviation has been greatly unused. There is nothing special about the version, nothing special about the category.It does nothing.




___

</details>



<details>
<summary>General: Fix original basename frame issues (<i><font color='#367F6C';>other</font> </i> ) - <a href="https://github.com/ynput/OpenPype/pull/4452">#4452</a></summary>

___

#### Brief description

Treat `{originalBasename}` in different way then standard files processing. In case template should use `{originalBasename}` the transfers will use them as they are without any changes or handling of frames.



#### Description

Frames handling is problematic with original basename because their padding can't be defined to match padding in source filenames. Also it limits the usage of functionality to "must have frame at end of fiename". This is proposal how that could be solved by simply ignoring frame handling and using filenames as are on representation. First frame is still stored to representation context but is not used in formatting part. This way we don't have to care about padding of frames at all.




___

</details>



<details>
<summary>Publisher: Report also crashed creators and convertors (<i><font color='#367F6C';>other</font> </i> ) - <a href="https://github.com/ynput/OpenPype/pull/4473">#4473</a></summary>

___

#### Brief description

Added crashes of creators and convertos discovery (lazy solution).



#### Description

Report in Publisher also contains information about crashed files caused during creator plugin discovery and convertor plugin discovery. They're not separated into categroies and there is no other information in the report about them, but this helps a lot during development. This change does not need to change format/schema of the report nor UI logic.




___

</details>


### **🐛 Bug fixes**




<details>
<summary>Maya: Fix Validate Attributes plugin (<i><font color='#367F6C';>3d</font> </i> <i><font style='color:#365E7F';>/ maya</font></i> ) - <a href="https://github.com/ynput/OpenPype/pull/4401">#4401</a></summary>

___

#### Brief description

Code was broken. So either plug-in was unused or it had gone unnoticed.



#### Description

Looking at the commit history of the plug-in itself it seems this might have been broken somewhere between two to three years. I think it's broken since two years since this commit.Should this plug-in be removed completely?@tokejepsen Is there still a use case where we should have this plug-in? (You created the original one)




___

</details>



<details>
<summary>Maya: Ignore workfile lock in Untitled scene (<i><font color='#367F6C';>3d</font> </i> <i><font style='color:#365E7F';>/ maya</font></i> ) - <a href="https://github.com/ynput/OpenPype/pull/4414">#4414</a></summary>

___

#### Brief description

Skip workfile lock check if current scene is 'Untitled'.




___

</details>



<details>
<summary>Maya: fps rounding - OP-2549 (<i><font color='#367F6C';>3d</font> </i> <i><font style='color:#365E7F';>/ maya</font></i> ) - <a href="https://github.com/ynput/OpenPype/pull/4424">#4424</a></summary>

___

#### Brief description

When FPS is registered in for example Ftrack and round either down or up (floor/ceil), comparing to Maya FPS can fail. Example:23.97 (Ftrack/Mongo) != 23.976023976023978 (Maya)



#### Description

Since Maya only has a select number of supported framerates, I've taken the approach of converting any fps to supported framerates in Maya. We validate the input fps to make sure they are supported in Maya in two ways:Whole Numbers - are validated straight against the supported framerates in Maya.Demical Numbers - we find the closest supported framerate in Maya. If the difference to the closest supported framerate, is more than 0.5 we'll throw an error.If Maya ever supports arbitrary framerates, then we might have a problem but I'm not holding my breath...




___

</details>



<details>
<summary>Strict Error Checking Default (<i><font color='#367F6C';>3d</font> </i> <i><font style='color:#365E7F';>/ maya</font></i> ) - <a href="https://github.com/ynput/OpenPype/pull/4457">#4457</a></summary>

___

#### Brief description

Provide default of strict error checking for instances created prior to PR.




___

</details>



<details>
<summary>Create: Enhance instance & context changes (<i><font color='#367F6C';>3d</font> </i> <i><font style='color:#365E7F';>/ houdini,after effects,3dsmax</font></i> ) - <a href="https://github.com/ynput/OpenPype/pull/4375">#4375</a></summary>

___

#### Brief description

Changes of instances and context have complex, hard to get structure. The structure did not change but instead of complex dictionaries are used objected data.



#### Description

This is poposal of changes data improvement for creators. Implemented `TrackChangesItem` which handles the changes for us. The item is creating changes based on old and new value and can provide information about changed keys or access to full old or new value. Can give the values on any "sub-dictionary".Used this new approach to fix change in houdini and 3ds max and also modified one aftereffects plugin using changes.




___

</details>



<details>
<summary>Houdini: hotfix condition (<i><font color='#367F6C';>3d</font> </i> <i><font style='color:#365E7F';>/ houdini</font></i> ) - <a href="https://github.com/ynput/OpenPype/pull/4391">#4391</a></summary>

___

## Hotfix



This is fixing bug introduced int #4374
___

</details>



<details>
<summary>Houdini: Houdini shelf tools fixes (<i><font color='#367F6C';>3d</font> </i> <i><font style='color:#365E7F';>/ houdini</font></i> ) - <a href="https://github.com/ynput/OpenPype/pull/4428">#4428</a></summary>

___

#### Brief description

Fix Houdini shelf tools.



#### Description

Use `label` as mandatory key instead of `name`. Changed how shelves are created. If the script is empty it is gracefully skipping it instead of crashing.




___

</details>



<details>
<summary>3dsmax: startup fixes (<i><font color='#367F6C';>3d</font> </i> <i><font style='color:#365E7F';>/ 3dsmax</font></i> ) - <a href="https://github.com/ynput/OpenPype/pull/4412">#4412</a></summary>

___

#### Brief description

This is fixing various issues that can occur on some of the 3dsmax versions.



#### Description

On displays with +4K resolution UI was broken, some 3dsmax versions couldn't process `PYTHONPATH` correctly. This PR is forcing `sys.path` and disabling `QT_AUTO_SCREEN_SCALE_FACTOR`




___

</details>



<details>
<summary>Fix features for gizmo menu (<i><font color='#367F6C';>2d</font> </i> <i><font style='color:#365E7F';>/ nuke</font></i> ) - <a href="https://github.com/ynput/OpenPype/pull/4280">#4280</a></summary>

___

#### Brief description

Fix features for the Gizmo Menu project settings (shortcut for python type of usage and file type of usage functionality)




___

</details>



<details>
<summary>Photoshop: fix missing legacy io for legacy instances (<i><font color='#367F6C';>2d</font> </i> <i><font style='color:#365E7F';>/ photoshop,after effects</font></i> ) - <a href="https://github.com/ynput/OpenPype/pull/4467">#4467</a></summary>

___

#### Brief description

`legacy_io` import was removed, but usage stayed.



#### Description

Usage of `legacy_io` should be eradicated, in creators it should be replaced by `self.create_context.get_current_project_name/asset_name/task_name`.




___

</details>



<details>
<summary>Fix - addSite loader handles hero version (<i><font color='#367F6C';>other</font> </i> <i><font style='color:#1E1B7B';>/ sitesync</font></i> ) - <a href="https://github.com/ynput/OpenPype/pull/4359">#4359</a></summary>

___

#### Brief description

If adding site to representation presence of hero version is checked, if found hero version is marked to be donwloaded too.Replacing https://github.com/ynput/OpenPype/pull/4191




___

</details>



<details>
<summary>Remove OIIO build for macos (<i><font color='#367F6C';>other</font> </i> ) - <a href="https://github.com/ynput/OpenPype/pull/4381">#4381</a></summary>

___

## Fix



Since we are not able to provide OpenImageIO tools binaries for macos, we should remove the item from th `pyproject.toml`. This PR is taking care of it.



It is also changing the way `fetch_thirdparty_libs` script works in that it doesn't crash when lib cannot be processed, it only issue warning.





Resolves #3858
___

</details>



<details>
<summary>General: Attribute definitions fixes (<i><font color='#367F6C';>other</font> </i> ) - <a href="https://github.com/ynput/OpenPype/pull/4392">#4392</a></summary>

___

#### Brief description

Fix possible issues with attribute definitions in publisher if there is unknown attribute on an instance.



#### Description

Source of the issue is that attribute definitions from creator plugin could be "expanded" during `CreatedInstance` initialization. Which would affect all other instances using the same list of attributes -> literally object of list. If the same list object is used in "BaseClass" for other creators it would affect all instances (because of 1 instance). There had to be implemented other changes to fix the issue and keep behavior the same.Object of `CreatedInstance` can be created without reference to creator object. `CreatedInstance` is responsible to give UI attribute definitions (technically is prepared for cases when each instance may have different attribute definitions -> not yet).Attribute definition has added more conditions for `__eq__` method and have implemented `__ne__` method (which is required for Py 2 compatibility). Renamed `AbtractAttrDef` to `AbstractAttrDef` (fix typo).




___

</details>



<details>
<summary>Ftrack: Don't force ftrackapp endpoint (<i><font color='#367F6C';>other</font> </i> <i><font style='color:#1E1B7B';>/ ftrack</font></i> ) - <a href="https://github.com/ynput/OpenPype/pull/4411">#4411</a></summary>

___

#### Brief description

Auto-fill of ftrack url don't break custom urls. Custom urls couldn't be used as `ftrackapp.com` is added if is not in the url.



#### Description

The code was changed in a way that auto-fill is still supported but before `ftrackapp` is added it will try to use url as is. If the connection works as is it is used.




___

</details>



<details>
<summary>Fix: DL on MacOS (<i><font color='#367F6C';>other</font> </i> ) - <a href="https://github.com/ynput/OpenPype/pull/4418">#4418</a></summary>

___

#### Brief description

This works if DL Openpype plugin Installation Directories is set to level of app bundle (eg. '/Applications/OpenPype 3.15.0.app')




___

</details>



<details>
<summary>Photoshop: make usage of layer name in subset name more controllable (<i><font color='#367F6C';>other</font> </i> ) - <a href="https://github.com/ynput/OpenPype/pull/4432">#4432</a></summary>

___

#### Brief description

Layer name was previously used in subset name only if multiple instances were being created in single step. This adds explicit toggle.



#### Description

Toggling this button allows to use layer name in created subset name even if single instance is being created.This follows more closely implementation if AE.




___

</details>



<details>
<summary>SiteSync: fix dirmap (<i><font color='#367F6C';>other</font> </i> ) - <a href="https://github.com/ynput/OpenPype/pull/4436">#4436</a></summary>

___

#### Brief description

Fixed issue in dirmap in Maya and Nuke



#### Description

Loads of error were thrown in Nuke console about dictionary value.`AttributeError: 'dict' object has no attribute 'lower'`




___

</details>



<details>
<summary>General: Ignore decode error of stdout/stderr in run_subprocess (<i><font color='#367F6C';>other</font> </i> ) - <a href="https://github.com/ynput/OpenPype/pull/4446">#4446</a></summary>

___

#### Brief description

Ignore decode errors and replace invalid character (byte) with escaped byte character.



#### Description

Calling of `run_subprocess` may cause crashes if output contains some unicode character which (for example Polish name of encoder handler).




___

</details>



<details>
<summary>Publisher: Fix reopen bug (<i><font color='#367F6C';>other</font> </i> ) - <a href="https://github.com/ynput/OpenPype/pull/4463">#4463</a></summary>

___

#### Brief description

Use right name of constant 'ActiveWindow' -> 'WindowActive'.




___

</details>



<details>
<summary>Publisher: Fix compatibility of QAction in Publisher (<i><font color='#367F6C';>other</font> </i> ) - <a href="https://github.com/ynput/OpenPype/pull/4474">#4474</a></summary>

___

#### Brief description

Fix `QAction` for older version of Qt bindings where QAction requires a parent on initialization.



#### Description

This bug was discovered in Nuke 11. Fixed by creating QAction when QMenu is already available and can be used as parent.




___

</details>


### **🔀 Refactored code**




<details>
<summary>General: Remove 'openpype.api' (<i><font color='#367F6C';>other</font> </i> ) - <a href="https://github.com/ynput/OpenPype/pull/4413">#4413</a></summary>

___

#### Brief description

PR is removing `openpype/api.py` file which is causing a lot of troubles and cross-imports.



#### Description

I wanted to remove the file slowly function by function but it always reappear somewhere in codebase even if most of the functionality imported from there is triggering deprecation warnings. This is small change which may have huge impact.There shouldn't be anything in openpype codebase which is using `openpype.api` anymore so only possible issues are in customized repositories or custom addons.




___

</details>


### **📃 Documentation**




<details>
<summary>docs-user-Getting Started adjustments (<i><font color='#367F6C';>other</font> </i> ) - <a href="https://github.com/ynput/OpenPype/pull/4365">#4365</a></summary>

___

#### Brief description

Small typo fixes here and there, additional info on install/ running OP.




___

</details>


### **Merged pull requests**




<details>
<summary>Renderman support for sample and display filters (<i><font color='#367F6C';>3d</font> </i> <i><font style='color:#365E7F';>/ maya</font></i> ) - <a href="https://github.com/ynput/OpenPype/pull/4003">#4003</a></summary>

___

#### Brief description

User can set up both sample and display filters in Openpype settings if they are using Renderman as renderer.



#### Description

You can preset which sample and display filters for renderman , including the cryptomatte renderpass, in Openpype settings. Once you select which filters to be included in openpype settings and then create render instance for your camera in maya, it would automatically tell the system to generate your selected filters in render settings.The place you can find for setting up the filters: _Maya > Render Settings > Renderman Renderer > Display Filters/ Sample Filters_




___

</details>



<details>
<summary>Maya: Create Arnold options on repair. (<i><font color='#367F6C';>3d</font> </i> <i><font style='color:#365E7F';>/ maya</font></i> ) - <a href="https://github.com/ynput/OpenPype/pull/4448">#4448</a></summary>

___

#### Brief description

When validating/repairing we previously required users to open render settings to create the Arnold options. This is done through code now.




___

</details>



<details>
<summary>Update Asset field of creator Instances in Maya Template Builder (<i><font color='#367F6C';>3d</font> </i> <i><font style='color:#365E7F';>/ maya</font></i> ) - <a href="https://github.com/ynput/OpenPype/pull/4470">#4470</a></summary>

___

#### Brief description

When we build a template with Maya Template Builder, it will update the asset field of the sets (creator instances) that are imported from the template.



#### Description

When building a template, we also want to define the publishable content in advance: create an instance of a model, or look, etc., to speed up the workflow and reduce the number of questions we are asked. After building a work file from a saved template that contains pre-created instances, the template builder should update the asset field to the current asset.




___

</details>



<details>
<summary>Blender: fix import workfile all families (<i><font color='#367F6C';>3d</font> </i> <i><font style='color:#365E7F';>/ blender</font></i> ) - <a href="https://github.com/ynput/OpenPype/pull/4405">#4405</a></summary>

___

#### Brief description

Having this feature related to workfile available for any family is absurd.




___

</details>



<details>
<summary>Nuke: update rendered frames in latest version (<i><font color='#367F6C';>2d</font> </i> <i><font style='color:#365E7F';>/ nuke</font></i> ) - <a href="https://github.com/ynput/OpenPype/pull/4362">#4362</a></summary>

___

#### Brief description

Introduced new field to insert frame(s) to rerender only.



#### Description

Rendering is expensive, sometimes it is helpful only to re-render changed frames and reuse existing.Artists can in Publisher fill which frame(s) should be re-rendered.If there is already published version of currently publishing subset, all representation files are collected (currently for `render` family only) and then when Nuke is rendering (locally only for now), old published files are copied into into temporary render folder where will be rewritten only by frames explicitly set in new field.That way review/burnin process could also reuse old files and recreate reviews/burnins.New version is produced during this process!




___

</details>



<details>
<summary>Feature: Keep synced hero representations up-to-date. (<i><font color='#367F6C';>other</font> </i> ) - <a href="https://github.com/ynput/OpenPype/pull/4343">#4343</a></summary>

___

#### Brief description

Keep previously synchronized sites up-to-date by comparing old and new sites and adding old sites if missing in new ones.Fix #4331




___

</details>



<details>
<summary>Maya: Fix template builder bug where assets are not put in the right hierarchy (<i><font color='#367F6C';>other</font> </i> ) - <a href="https://github.com/ynput/OpenPype/pull/4367">#4367</a></summary>

___

#### Brief description

When buiding scene from template, the assets loaded from the placeholders are not put in the hierarchy. Plus, the assets are loaded in double.




___

</details>



<details>
<summary>Bump ua-parser-js from 0.7.31 to 0.7.33 in /website (<i><font color='#367F6C';>other</font> </i> ) - <a href="https://github.com/ynput/OpenPype/pull/4371">#4371</a></summary>

___

Bumps [ua-parser-js](https://github.com/faisalman/ua-parser-js) from 0.7.31 to 0.7.33.
<details>
<summary>Changelog</summary>
<p><em>Sourced from <a href="https://github.com/faisalman/ua-parser-js/blob/master/changelog.md">ua-parser-js's changelog</a>.</em></p>
<blockquote>
<h2>Version 0.7.31 / 1.0.2</h2>
<ul>
<li>Fix OPPO Reno A5 incorrect detection</li>
<li>Fix TypeError Bug</li>
<li>Use AST to extract regexes and verify them with safe-regex</li>
</ul>
<h2>Version 0.7.32 / 1.0.32</h2>
<ul>
<li>Add new browser : DuckDuckGo, Huawei Browser, LinkedIn</li>
<li>Add new OS : HarmonyOS</li>
<li>Add some Huawei models</li>
<li>Add Sharp Aquos TV</li>
<li>Improve detection Xiaomi Mi CC9</li>
<li>Fix Sony Xperia 1 III misidentified as Acer tablet</li>
<li>Fix Detect Sony BRAVIA as SmartTV</li>
<li>Fix Detect Xiaomi Mi TV as SmartTV</li>
<li>Fix Detect Galaxy Tab S8 as tablet</li>
<li>Fix WeGame mistakenly identified as WeChat</li>
<li>Fix included commas in Safari / Mobile Safari version</li>
<li>Increase UA_MAX_LENGTH to 350</li>
</ul>
<h2>Version 0.7.33 / 1.0.33</h2>
<ul>
<li>Add new browser : Cobalt</li>
<li>Identify Macintosh as an Apple device</li>
<li>Fix ReDoS vulnerability</li>
</ul>
<h1>Version 0.8</h1>
<p>Version 0.8 was created by accident. This version is now deprecated and no longer maintained, please update to version 0.7 / 1.0.</p>
</blockquote>
</details>
<details>
<summary>Commits</summary>
<ul>
<li><a href="https://github.com/faisalman/ua-parser-js/commit/f2d0db001d87da15de7b9b1df7be9f2eacefd8c5"><code>f2d0db0</code></a> Bump version 0.7.33</li>
<li><a href="https://github.com/faisalman/ua-parser-js/commit/a6140a17dd0300a35cfc9cff999545f267889411"><code>a6140a1</code></a> Remove unsafe regex in trim() function</li>
<li><a href="https://github.com/faisalman/ua-parser-js/commit/a88660493568d6144a551424a8139d6c876635f6"><code>a886604</code></a> Fix <a href="https://github-redirect.dependabot.com/faisalman/ua-parser-js/issues/605">#605</a> - Identify Macintosh as Apple device</li>
<li><a href="https://github.com/faisalman/ua-parser-js/commit/b814bcd79198e730936c82462e2d729eb5423e3c"><code>b814bcd</code></a> Merge pull request <a href="https://github-redirect.dependabot.com/faisalman/ua-parser-js/issues/606">#606</a> from rileyjshaw/patch-1</li>
<li><a href="https://github.com/faisalman/ua-parser-js/commit/7f71024161399b7aa5d5cd10dba9e059f0218262"><code>7f71024</code></a> Fix documentation</li>
<li><a href="https://github.com/faisalman/ua-parser-js/commit/c239ac5167abd574a635cb809a2b4fa35810d23b"><code>c239ac5</code></a> Merge pull request <a href="https://github-redirect.dependabot.com/faisalman/ua-parser-js/issues/604">#604</a> from obecerra3/master</li>
<li><a href="https://github.com/faisalman/ua-parser-js/commit/8d3c2d327cf540ff2c050f1cc67bca8c6f8e4458"><code>8d3c2d3</code></a> Add new browser: Cobalt</li>
<li><a href="https://github.com/faisalman/ua-parser-js/commit/d11fc47dc9b6acc0f89fc10c120cea08e10cd31a"><code>d11fc47</code></a> Bump version 0.7.32</li>
<li><a href="https://github.com/faisalman/ua-parser-js/commit/b490110109de586deab96c775c9ef0dfc9c919c4"><code>b490110</code></a> Merge branch 'develop' of github.com:faisalman/ua-parser-js</li>
<li><a href="https://github.com/faisalman/ua-parser-js/commit/cb5da5ea4b220d5b60fe209e123b7f911d8e0d4a"><code>cb5da5e</code></a> Merge pull request <a href="https://github-redirect.dependabot.com/faisalman/ua-parser-js/issues/600">#600</a> from moekm/develop</li>
<li>Additional commits viewable in <a href="https://github.com/faisalman/ua-parser-js/compare/0.7.31...0.7.33">compare view</a></li>
</ul>
</details>
<br />


[![Dependabot compatibility score](https://dependabot-badges.githubapp.com/badges/compatibility_score?dependency-name=ua-parser-js&package-manager=npm_and_yarn&previous-version=0.7.31&new-version=0.7.33)](https://docs.github.com/en/github/managing-security-vulnerabilities/about-dependabot-security-updates#about-compatibility-scores)

Dependabot will resolve any conflicts with this PR as long as you don't alter it yourself. You can also trigger a rebase manually by commenting `@dependabot rebase`.

[//]: # (dependabot-automerge-start)
[//]: # (dependabot-automerge-end)

---

<details>
<summary>Dependabot commands and options</summary>
<br />

You can trigger Dependabot actions by commenting on this PR:
- `@dependabot rebase` will rebase this PR
- `@dependabot recreate` will recreate this PR, overwriting any edits that have been made to it
- `@dependabot merge` will merge this PR after your CI passes on it
- `@dependabot squash and merge` will squash and merge this PR after your CI passes on it
- `@dependabot cancel merge` will cancel a previously requested merge and block automerging
- `@dependabot reopen` will reopen this PR if it is closed
- `@dependabot close` will close this PR and stop Dependabot recreating it. You can achieve the same result by closing it manually
- `@dependabot ignore this major version` will close this PR and stop Dependabot creating any more for this major version (unless you reopen the PR or upgrade to it yourself)
- `@dependabot ignore this minor version` will close this PR and stop Dependabot creating any more for this minor version (unless you reopen the PR or upgrade to it yourself)
- `@dependabot ignore this dependency` will close this PR and stop Dependabot creating any more for this dependency (unless you reopen the PR or upgrade to it yourself)
- `@dependabot use these labels` will set the current labels as the default for future PRs for this repo and language
- `@dependabot use these reviewers` will set the current reviewers as the default for future PRs for this repo and language
- `@dependabot use these assignees` will set the current assignees as the default for future PRs for this repo and language
- `@dependabot use this milestone` will set the current milestone as the default for future PRs for this repo and language

You can disable automated security fix PRs for this repo from the [Security Alerts page](https://github.com/ynput/OpenPype/network/alerts).

</details>
___

</details>



<details>
<summary>Docs: Question about renaming in Kitsu (<i><font color='#367F6C';>other</font> </i> ) - <a href="https://github.com/ynput/OpenPype/pull/4384">#4384</a></summary>

___

#### Brief description

To keep memory of this discussion: https://discord.com/channels/517362899170230292/563751989075378201/1068112668491255818




___

</details>



<details>
<summary>New Publisher: Fix Creator error typo (<i><font color='#367F6C';>other</font> </i> ) - <a href="https://github.com/ynput/OpenPype/pull/4396">#4396</a></summary>

___

#### Brief description

Fixes typo in error message.




___

</details>



<details>
<summary>Chore: pyproject.toml version because of Poetry (<i><font color='#367F6C';>other</font> </i> ) - <a href="https://github.com/ynput/OpenPype/pull/4408">#4408</a></summary>

___

#### Brief description

Automatization injects wrong format




___

</details>



<details>
<summary>Fix - remove minor part in toml (<i><font color='#367F6C';>other</font> </i> ) - <a href="https://github.com/ynput/OpenPype/pull/4437">#4437</a></summary>

___

#### Brief description

Causes issue in create_env and new Poetry




___

</details>



<details>
<summary>General: Add project code to anatomy (<i><font color='#367F6C';>other</font> </i> ) - <a href="https://github.com/ynput/OpenPype/pull/4445">#4445</a></summary>

___

#### Brief description

Added attribute `project_code` to `Anatomy` object.



#### Description

Anatomy already have access to almost all attributes from project anatomy except project code. This PR changing it. Technically `Anatomy` is everything what would be needed to get fill data of project.

```

{

    "project": {

        "name": anatomy.project_name,

        "code": anatomy.project_code

    }

}

```


___

</details>



<details>
<summary>Maya: Arnold Scene Source overhaul - OP-4865 (<i><font color='#367F6C';>other</font> </i> <i><font style='color:#365E7F';>/ maya</font></i> ) - <a href="https://github.com/ynput/OpenPype/pull/4449">#4449</a></summary>

___

#### Brief description

General overhaul of the Arnold Scene Source (ASS) workflow.



#### Description

This originally was to support static files (non-sequencial) ASS publishing, but digging deeper whole workflow needed an update to get ready for further issues. During this overhaul the following changes were made:

- Generalized Arnold Standin workflow to a single loader.

- Support multiple nodes as proxies.

- Support proxies for `pointcache` family.

- Generalized approach to proxies as resources, so they can be the same file format as the original.This workflow should allow further expansion to utilize operators and eventually USD.




___

</details>




## [3.15.0](https://github.com/ynput/OpenPype/tree/3.15.0)

[Full Changelog](https://github.com/ynput/OpenPype/compare/3.14.10...3.15.0)

**Deprecated:**

- General: Fill default values of new publish template profiles [\#4245](https://github.com/ynput/OpenPype/pull/4245)

### 📖 Documentation

- documentation: Split tools into separate entries [\#4342](https://github.com/ynput/OpenPype/pull/4342)
- Documentation: Fix harmony docs [\#4301](https://github.com/ynput/OpenPype/pull/4301)
- Remove staging logic set by OpenPype version [\#3979](https://github.com/ynput/OpenPype/pull/3979)

**🆕 New features**

- General: Push to studio library [\#4284](https://github.com/ynput/OpenPype/pull/4284)
- Colorspace Management and Distribution [\#4195](https://github.com/ynput/OpenPype/pull/4195)
- Nuke: refactor to latest publisher workfow [\#4006](https://github.com/ynput/OpenPype/pull/4006)
- Update to Python 3.9 [\#3546](https://github.com/ynput/OpenPype/pull/3546)

**🚀 Enhancements**

- Unreal: Don't use mongo queries in 'ExistingLayoutLoader' [\#4356](https://github.com/ynput/OpenPype/pull/4356)
- General: Loader and Creator plugins can be disabled [\#4310](https://github.com/ynput/OpenPype/pull/4310)
- General: Unbind poetry version [\#4306](https://github.com/ynput/OpenPype/pull/4306)
- General: Enhanced enum def items [\#4295](https://github.com/ynput/OpenPype/pull/4295)
- Git: add pre-commit hooks [\#4289](https://github.com/ynput/OpenPype/pull/4289)
- Tray Publisher: Improve Online family functionality [\#4263](https://github.com/ynput/OpenPype/pull/4263)
- General: Update MacOs to PySide6 [\#4255](https://github.com/ynput/OpenPype/pull/4255)
- Build: update to Gazu in toml [\#4208](https://github.com/ynput/OpenPype/pull/4208)
- Global: adding imageio to settings [\#4158](https://github.com/ynput/OpenPype/pull/4158)
- Blender: added project settings for validator no colons in name [\#4149](https://github.com/ynput/OpenPype/pull/4149)
- Dockerfile for Debian Bullseye [\#4108](https://github.com/ynput/OpenPype/pull/4108)
- AfterEffects: publish multiple compositions [\#4092](https://github.com/ynput/OpenPype/pull/4092)
- AfterEffects: make new publisher default [\#4056](https://github.com/ynput/OpenPype/pull/4056)
- Photoshop: make new publisher default [\#4051](https://github.com/ynput/OpenPype/pull/4051)
- Feature/multiverse [\#4046](https://github.com/ynput/OpenPype/pull/4046)
- Tests: add support for deadline for automatic tests [\#3989](https://github.com/ynput/OpenPype/pull/3989)
- Add version to shortcut name [\#3906](https://github.com/ynput/OpenPype/pull/3906)
- TrayPublisher: Removed from experimental tools [\#3667](https://github.com/ynput/OpenPype/pull/3667)

**🐛 Bug fixes**

- change 3.7 to 3.9 in folder name [\#4354](https://github.com/ynput/OpenPype/pull/4354)
- PushToProject: Fix hierarchy of project change [\#4350](https://github.com/ynput/OpenPype/pull/4350)
- Fix photoshop workfile save-as [\#4347](https://github.com/ynput/OpenPype/pull/4347)
- Nuke Input process node sourcing improvements [\#4341](https://github.com/ynput/OpenPype/pull/4341)
- New publisher: Some validation plugin tweaks [\#4339](https://github.com/ynput/OpenPype/pull/4339)
- Harmony: fix unable to change workfile on Mac [\#4334](https://github.com/ynput/OpenPype/pull/4334)
- Global: fixing in-place source publishing for editorial [\#4333](https://github.com/ynput/OpenPype/pull/4333)
- General: Use class constants of QMessageBox [\#4332](https://github.com/ynput/OpenPype/pull/4332)
- TVPaint: Fix plugin for TVPaint 11.7 [\#4328](https://github.com/ynput/OpenPype/pull/4328)
- Exctract OTIO review has improved quality [\#4325](https://github.com/ynput/OpenPype/pull/4325)
- Ftrack: fix typos causing bugs in sync [\#4322](https://github.com/ynput/OpenPype/pull/4322)
- General: Python 2 compatibility of instance collector [\#4320](https://github.com/ynput/OpenPype/pull/4320)
- Slack: user groups speedup [\#4318](https://github.com/ynput/OpenPype/pull/4318)
- Maya: Bug - Multiverse extractor executed on plain animation family [\#4315](https://github.com/ynput/OpenPype/pull/4315)
- Fix run\_documentation.ps1 [\#4312](https://github.com/ynput/OpenPype/pull/4312)
- Nuke: new creators fixes [\#4308](https://github.com/ynput/OpenPype/pull/4308)
- General: missing comment on standalone and tray publisher [\#4303](https://github.com/ynput/OpenPype/pull/4303)
- AfterEffects: Fix for audio from mp4 layer [\#4296](https://github.com/ynput/OpenPype/pull/4296)
- General: Update gazu in poetry lock [\#4247](https://github.com/ynput/OpenPype/pull/4247)
- Bug: Fixing version detection and filtering in Igniter [\#3914](https://github.com/ynput/OpenPype/pull/3914)
- Bug: Create missing version dir [\#3903](https://github.com/ynput/OpenPype/pull/3903)

**🔀 Refactored code**

- Remove redundant export\_alembic method. [\#4293](https://github.com/ynput/OpenPype/pull/4293)
- Igniter: Use qtpy modules instead of Qt [\#4237](https://github.com/ynput/OpenPype/pull/4237)

**Merged pull requests:**

- Sort families by alphabetical order in the Create plugin [\#4346](https://github.com/ynput/OpenPype/pull/4346)
- Global: Validate unique subsets [\#4336](https://github.com/ynput/OpenPype/pull/4336)
- Maya: Collect instances preserve handles even if frameStart + frameEnd matches context [\#3437](https://github.com/ynput/OpenPype/pull/3437)

## [3.14.10](https://github.com/ynput/OpenPype/tree/HEAD)

[Full Changelog](https://github.com/ynput/OpenPype/compare/3.14.9...3.14.10)

**🆕 New features**

- Global | Nuke: Creator placeholders in workfile template builder [\#4266](https://github.com/ynput/OpenPype/pull/4266)
- Slack: Added dynamic message [\#4265](https://github.com/ynput/OpenPype/pull/4265)
- Blender: Workfile Loader [\#4234](https://github.com/ynput/OpenPype/pull/4234)
- Unreal: Publishing and Loading for UAssets [\#4198](https://github.com/ynput/OpenPype/pull/4198)
- Publish: register publishes without copying them [\#4157](https://github.com/ynput/OpenPype/pull/4157)

**🚀 Enhancements**

- General: Added install method with docstring to HostBase [\#4298](https://github.com/ynput/OpenPype/pull/4298)
- Traypublisher: simple editorial multiple edl [\#4248](https://github.com/ynput/OpenPype/pull/4248)
- General: Extend 'IPluginPaths' to have more available methods [\#4214](https://github.com/ynput/OpenPype/pull/4214)
- Refactorization of folder coloring [\#4211](https://github.com/ynput/OpenPype/pull/4211)
- Flame - loading multilayer with controlled layer names [\#4204](https://github.com/ynput/OpenPype/pull/4204)

**🐛 Bug fixes**

- Unreal: fix missing `maintained_selection` call [\#4300](https://github.com/ynput/OpenPype/pull/4300)
- Ftrack: Fix receive of host ip on MacOs [\#4288](https://github.com/ynput/OpenPype/pull/4288)
- SiteSync: sftp connection failing when shouldnt be tested [\#4278](https://github.com/ynput/OpenPype/pull/4278)
- Deadline: fix default value for passing mongo url [\#4275](https://github.com/ynput/OpenPype/pull/4275)
- Scene Manager: Fix variable name [\#4268](https://github.com/ynput/OpenPype/pull/4268)
- Slack: notification fails because of missing published path [\#4264](https://github.com/ynput/OpenPype/pull/4264)
- hiero: creator gui with min max  [\#4257](https://github.com/ynput/OpenPype/pull/4257)
- NiceCheckbox: Fix checker positioning in Python 2 [\#4253](https://github.com/ynput/OpenPype/pull/4253)
- Publisher: Fix 'CreatorType' not equal for Python 2 DCCs [\#4249](https://github.com/ynput/OpenPype/pull/4249)
- Deadline: fix dependencies [\#4242](https://github.com/ynput/OpenPype/pull/4242)
- Houdini: hotfix instance data access [\#4236](https://github.com/ynput/OpenPype/pull/4236)
- bugfix/image plane load error [\#4222](https://github.com/ynput/OpenPype/pull/4222)
- Hiero: thumbnail from multilayer exr [\#4209](https://github.com/ynput/OpenPype/pull/4209)

**🔀 Refactored code**

- Resolve: Use qtpy in Resolve [\#4254](https://github.com/ynput/OpenPype/pull/4254)
- Houdini: Use qtpy in Houdini [\#4252](https://github.com/ynput/OpenPype/pull/4252)
- Max: Use qtpy in Max [\#4251](https://github.com/ynput/OpenPype/pull/4251)
- Maya: Use qtpy in Maya [\#4250](https://github.com/ynput/OpenPype/pull/4250)
- Hiero: Use qtpy in Hiero [\#4240](https://github.com/ynput/OpenPype/pull/4240)
- Nuke: Use qtpy in Nuke [\#4239](https://github.com/ynput/OpenPype/pull/4239)
- Flame: Use qtpy in flame [\#4238](https://github.com/ynput/OpenPype/pull/4238)
- General: Legacy io not used in global plugins [\#4134](https://github.com/ynput/OpenPype/pull/4134)

**Merged pull requests:**

- Bump json5 from 1.0.1 to 1.0.2 in /website [\#4292](https://github.com/ynput/OpenPype/pull/4292)
- Maya: Fix validate frame range repair + fix create render with deadline disabled [\#4279](https://github.com/ynput/OpenPype/pull/4279)


## [3.14.9](https://github.com/pypeclub/OpenPype/tree/3.14.9)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.14.8...3.14.9)

### 📖 Documentation

- Documentation: Testing on Deadline [\#4185](https://github.com/pypeclub/OpenPype/pull/4185)
- Consistent Python version [\#4160](https://github.com/pypeclub/OpenPype/pull/4160)

**🆕 New features**

- Feature/op 4397 gl tf extractor for maya [\#4192](https://github.com/pypeclub/OpenPype/pull/4192)
- Maya: Extractor for Unreal SkeletalMesh [\#4174](https://github.com/pypeclub/OpenPype/pull/4174)
- 3dsmax: integration [\#4168](https://github.com/pypeclub/OpenPype/pull/4168)
- Blender: Extract Alembic Animations [\#4128](https://github.com/pypeclub/OpenPype/pull/4128)
- Unreal: Load Alembic Animations [\#4127](https://github.com/pypeclub/OpenPype/pull/4127)

**🚀 Enhancements**

- Houdini: Use new interface class name for publish host [\#4220](https://github.com/pypeclub/OpenPype/pull/4220)
- General: Default command for headless mode is interactive [\#4203](https://github.com/pypeclub/OpenPype/pull/4203)
- Maya: Enhanced ASS publishing [\#4196](https://github.com/pypeclub/OpenPype/pull/4196)
- Feature/op 3924 implement ass extractor [\#4188](https://github.com/pypeclub/OpenPype/pull/4188)
- File transactions: Source path is destination path [\#4184](https://github.com/pypeclub/OpenPype/pull/4184)
- Deadline: improve environment processing [\#4182](https://github.com/pypeclub/OpenPype/pull/4182)
- General: Comment per instance in Publisher [\#4178](https://github.com/pypeclub/OpenPype/pull/4178)
- Ensure Mongo database directory exists in Windows. [\#4166](https://github.com/pypeclub/OpenPype/pull/4166)
- Note about unrestricted execution on Windows. [\#4161](https://github.com/pypeclub/OpenPype/pull/4161)
- Maya: Enable thumbnail transparency on extraction. [\#4147](https://github.com/pypeclub/OpenPype/pull/4147)
- Maya: Disable viewport Pan/Zoom on playblast extraction. [\#4146](https://github.com/pypeclub/OpenPype/pull/4146)
- Maya: Optional viewport refresh on pointcache extraction [\#4144](https://github.com/pypeclub/OpenPype/pull/4144)
- CelAction: refactory integration to current openpype [\#4140](https://github.com/pypeclub/OpenPype/pull/4140)
- Maya: create and publish bounding box geometry [\#4131](https://github.com/pypeclub/OpenPype/pull/4131)
- Changed the UOpenPypePublishInstance to use the UDataAsset class [\#4124](https://github.com/pypeclub/OpenPype/pull/4124)
- General: Collection Audio speed up [\#4110](https://github.com/pypeclub/OpenPype/pull/4110)
- Maya: keep existing AOVs when creating render instance [\#4087](https://github.com/pypeclub/OpenPype/pull/4087)
- General: Oiio conversion multipart fix [\#4060](https://github.com/pypeclub/OpenPype/pull/4060)

**🐛 Bug fixes**

- Publisher: Signal type issues in Python 2 DCCs [\#4230](https://github.com/pypeclub/OpenPype/pull/4230)
- Blender: Fix Layout Family Versioning [\#4228](https://github.com/pypeclub/OpenPype/pull/4228)
- Blender: Fix Create Camera "Use selection" [\#4226](https://github.com/pypeclub/OpenPype/pull/4226)
- TrayPublisher - join needs list [\#4224](https://github.com/pypeclub/OpenPype/pull/4224)
- General: Event callbacks pass event to callbacks as expected [\#4210](https://github.com/pypeclub/OpenPype/pull/4210)
- Build:Revert .toml update of Gazu [\#4207](https://github.com/pypeclub/OpenPype/pull/4207)
- Nuke: fixed imageio node overrides subset filter [\#4202](https://github.com/pypeclub/OpenPype/pull/4202)
- Maya: pointcache [\#4201](https://github.com/pypeclub/OpenPype/pull/4201)
- Unreal: Support for Unreal Engine 5.1 [\#4199](https://github.com/pypeclub/OpenPype/pull/4199)
- General: Integrate thumbnail looks for thumbnail to multiple places [\#4181](https://github.com/pypeclub/OpenPype/pull/4181)
- Various minor bugfixes [\#4172](https://github.com/pypeclub/OpenPype/pull/4172)
- Nuke/Hiero: Remove tkinter library paths before launch [\#4171](https://github.com/pypeclub/OpenPype/pull/4171)
- Flame: vertical alignment of layers [\#4169](https://github.com/pypeclub/OpenPype/pull/4169)
- Nuke: correct detection of viewer and display [\#4165](https://github.com/pypeclub/OpenPype/pull/4165)
- Settings UI: Don't create QApplication if already exists [\#4156](https://github.com/pypeclub/OpenPype/pull/4156)
- General: Extract review handle start offset of sequences [\#4152](https://github.com/pypeclub/OpenPype/pull/4152)
- Maya: Maintain time connections on Alembic update. [\#4143](https://github.com/pypeclub/OpenPype/pull/4143)

**🔀 Refactored code**

- General: Use qtpy in modules and hosts UIs which are running in OpenPype process [\#4225](https://github.com/pypeclub/OpenPype/pull/4225)
- Tools: Use qtpy instead of Qt in standalone tools [\#4223](https://github.com/pypeclub/OpenPype/pull/4223)
- General: Use qtpy in settings UI [\#4215](https://github.com/pypeclub/OpenPype/pull/4215)

**Merged pull requests:**

- layout publish more than one container issue [\#4098](https://github.com/pypeclub/OpenPype/pull/4098)

## [3.14.8](https://github.com/pypeclub/OpenPype/tree/3.14.8)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.14.7...3.14.8)

**🚀 Enhancements**

- General: Refactored extract hierarchy plugin [\#4139](https://github.com/pypeclub/OpenPype/pull/4139)
- General: Find executable enhancement [\#4137](https://github.com/pypeclub/OpenPype/pull/4137)
- Ftrack: Reset session before instance processing [\#4129](https://github.com/pypeclub/OpenPype/pull/4129)
- Ftrack: Editorial asset sync issue [\#4126](https://github.com/pypeclub/OpenPype/pull/4126)
- Deadline: Build version resolving [\#4115](https://github.com/pypeclub/OpenPype/pull/4115)
- Houdini: New Publisher [\#3046](https://github.com/pypeclub/OpenPype/pull/3046)
- Fix: Standalone Publish Directories [\#4148](https://github.com/pypeclub/OpenPype/pull/4148)

**🐛 Bug fixes**

- Ftrack: Fix occational double parents issue [\#4153](https://github.com/pypeclub/OpenPype/pull/4153)
- General: Maketx executable issue [\#4136](https://github.com/pypeclub/OpenPype/pull/4136)
- Maya: Looks - add all connections [\#4135](https://github.com/pypeclub/OpenPype/pull/4135)
- General: Fix variable check in collect anatomy instance data [\#4117](https://github.com/pypeclub/OpenPype/pull/4117)

## [3.14.7](https://github.com/pypeclub/OpenPype/tree/3.14.7)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.14.6...3.14.7)

**🆕 New features**

- Hiero: loading effect family to timeline [\#4055](https://github.com/pypeclub/OpenPype/pull/4055)

**🚀 Enhancements**

- Photoshop: bug with pop-up window on Instance Creator [\#4121](https://github.com/pypeclub/OpenPype/pull/4121)
- Publisher: Open on specific tab [\#4120](https://github.com/pypeclub/OpenPype/pull/4120)
- Publisher: Hide unknown publish values [\#4116](https://github.com/pypeclub/OpenPype/pull/4116)
- Ftrack: Event server status give more information about version locations [\#4112](https://github.com/pypeclub/OpenPype/pull/4112)
- General: Allow higher numbers in frames and clips [\#4101](https://github.com/pypeclub/OpenPype/pull/4101)
- Publisher: Settings for validate frame range [\#4097](https://github.com/pypeclub/OpenPype/pull/4097)
- Publisher: Ignore escape button [\#4090](https://github.com/pypeclub/OpenPype/pull/4090)
- Flame: Loading clip with native colorspace resolved from mapping [\#4079](https://github.com/pypeclub/OpenPype/pull/4079)
- General: Extract review single frame output [\#4064](https://github.com/pypeclub/OpenPype/pull/4064)
- Publisher: Prepared common function for instance data cache [\#4063](https://github.com/pypeclub/OpenPype/pull/4063)
- Publisher: Easy access to publish page from create page [\#4058](https://github.com/pypeclub/OpenPype/pull/4058)
- General/TVPaint: Attribute defs dialog [\#4052](https://github.com/pypeclub/OpenPype/pull/4052)
- Publisher: Better reset defer [\#4048](https://github.com/pypeclub/OpenPype/pull/4048)
- Publisher: Add thumbnail sources [\#4042](https://github.com/pypeclub/OpenPype/pull/4042)

**🐛 Bug fixes**

- General: Move default settings for template name [\#4119](https://github.com/pypeclub/OpenPype/pull/4119)
- Slack: notification fail in new tray publisher [\#4118](https://github.com/pypeclub/OpenPype/pull/4118)
- Nuke: loaded nodes set to first tab [\#4114](https://github.com/pypeclub/OpenPype/pull/4114)
- Nuke: load image first frame [\#4113](https://github.com/pypeclub/OpenPype/pull/4113)
- Files Widget: Ignore case sensitivity of extensions [\#4096](https://github.com/pypeclub/OpenPype/pull/4096)
- Webpublisher: extension is lowercased in Setting and in uploaded files [\#4095](https://github.com/pypeclub/OpenPype/pull/4095)
- Publish Report Viewer: Fix small bugs [\#4086](https://github.com/pypeclub/OpenPype/pull/4086)
- Igniter: fix regex to match semver better [\#4085](https://github.com/pypeclub/OpenPype/pull/4085)
- Maya: aov filtering [\#4083](https://github.com/pypeclub/OpenPype/pull/4083)
- Flame/Flare: Loading to multiple batches [\#4080](https://github.com/pypeclub/OpenPype/pull/4080)
- hiero: creator from settings with set maximum [\#4077](https://github.com/pypeclub/OpenPype/pull/4077)
- Nuke: resolve hashes in file name only for frame token [\#4074](https://github.com/pypeclub/OpenPype/pull/4074)
- Publisher: Fix cache of asset docs [\#4070](https://github.com/pypeclub/OpenPype/pull/4070)
- Webpublisher: cleanup wp extract thumbnail [\#4067](https://github.com/pypeclub/OpenPype/pull/4067)
- Settings UI: Locked setting can't bypass lock [\#4066](https://github.com/pypeclub/OpenPype/pull/4066)
- Loader: Fix comparison of repre name [\#4053](https://github.com/pypeclub/OpenPype/pull/4053)
- Deadline: Extract environment subprocess failure [\#4050](https://github.com/pypeclub/OpenPype/pull/4050)

**🔀 Refactored code**

- General: Collect entities plugin minor changes [\#4089](https://github.com/pypeclub/OpenPype/pull/4089)
- General: Direct interfaces import [\#4065](https://github.com/pypeclub/OpenPype/pull/4065)

**Merged pull requests:**

- Bump loader-utils from 1.4.1 to 1.4.2 in /website [\#4100](https://github.com/pypeclub/OpenPype/pull/4100)
- Online family for Tray Publisher [\#4093](https://github.com/pypeclub/OpenPype/pull/4093)
- Bump loader-utils from 1.4.0 to 1.4.1 in /website [\#4081](https://github.com/pypeclub/OpenPype/pull/4081)
- remove underscore from subset name [\#4059](https://github.com/pypeclub/OpenPype/pull/4059)
- Alembic Loader as Arnold Standin [\#4047](https://github.com/pypeclub/OpenPype/pull/4047)

## [3.14.6](https://github.com/pypeclub/OpenPype/tree/3.14.6)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.14.5...3.14.6)

### 📖 Documentation

- Documentation: Minor updates to dev\_requirements.md [\#4025](https://github.com/pypeclub/OpenPype/pull/4025)

**🆕 New features**

- Nuke: add 13.2 variant [\#4041](https://github.com/pypeclub/OpenPype/pull/4041)

**🚀 Enhancements**

- Publish Report Viewer: Store reports locally on machine [\#4040](https://github.com/pypeclub/OpenPype/pull/4040)
- General: More specific error in burnins script [\#4026](https://github.com/pypeclub/OpenPype/pull/4026)
- General: Extract review does not crash with old settings overrides [\#4023](https://github.com/pypeclub/OpenPype/pull/4023)
- Publisher: Convertors for legacy instances [\#4020](https://github.com/pypeclub/OpenPype/pull/4020)
- workflows: adding milestone creator and assigner [\#4018](https://github.com/pypeclub/OpenPype/pull/4018)
- Publisher: Catch creator errors [\#4015](https://github.com/pypeclub/OpenPype/pull/4015)

**🐛 Bug fixes**

- Hiero - effect collection fixes [\#4038](https://github.com/pypeclub/OpenPype/pull/4038)
- Nuke - loader clip correct hash conversion in path [\#4037](https://github.com/pypeclub/OpenPype/pull/4037)
- Maya: Soft fail when applying capture preset [\#4034](https://github.com/pypeclub/OpenPype/pull/4034)
- Igniter: handle missing directory [\#4032](https://github.com/pypeclub/OpenPype/pull/4032)
- StandalonePublisher: Fix thumbnail publishing [\#4029](https://github.com/pypeclub/OpenPype/pull/4029)
- Experimental Tools: Fix publisher import [\#4027](https://github.com/pypeclub/OpenPype/pull/4027)
- Houdini: fix wrong path in ASS loader [\#4016](https://github.com/pypeclub/OpenPype/pull/4016)

**🔀 Refactored code**

- General: Import lib functions from lib [\#4017](https://github.com/pypeclub/OpenPype/pull/4017)

## [3.14.5](https://github.com/pypeclub/OpenPype/tree/3.14.5) (2022-10-24)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.14.4...3.14.5)

**🚀 Enhancements**

- Maya: add OBJ extractor to model family [\#4021](https://github.com/pypeclub/OpenPype/pull/4021)
- Publish report viewer tool [\#4010](https://github.com/pypeclub/OpenPype/pull/4010)
- Nuke | Global: adding custom tags representation filtering [\#4009](https://github.com/pypeclub/OpenPype/pull/4009)
- Publisher: Create context has shared data for collection phase [\#3995](https://github.com/pypeclub/OpenPype/pull/3995)
- Resolve: updating to v18 compatibility [\#3986](https://github.com/pypeclub/OpenPype/pull/3986)

**🐛 Bug fixes**

- TrayPublisher: Fix missing argument [\#4019](https://github.com/pypeclub/OpenPype/pull/4019)
- General: Fix python 2 compatibility of ffmpeg and oiio tools discovery [\#4011](https://github.com/pypeclub/OpenPype/pull/4011)

**🔀 Refactored code**

- Maya: Removed unused imports [\#4008](https://github.com/pypeclub/OpenPype/pull/4008)
- Unreal: Fix import of moved function [\#4007](https://github.com/pypeclub/OpenPype/pull/4007)
- Houdini: Change import of RepairAction [\#4005](https://github.com/pypeclub/OpenPype/pull/4005)
- Nuke/Hiero: Refactor openpype.api imports [\#4000](https://github.com/pypeclub/OpenPype/pull/4000)
- TVPaint: Defined with HostBase [\#3994](https://github.com/pypeclub/OpenPype/pull/3994)

**Merged pull requests:**

- Unreal: Remove redundant Creator stub [\#4012](https://github.com/pypeclub/OpenPype/pull/4012)
- Unreal: add `uproject` extension to Unreal project template [\#4004](https://github.com/pypeclub/OpenPype/pull/4004)
- Unreal: fix order of includes [\#4002](https://github.com/pypeclub/OpenPype/pull/4002)
- Fusion: Implement backwards compatibility \(+/- Fusion 17.2\) [\#3958](https://github.com/pypeclub/OpenPype/pull/3958)

## [3.14.4](https://github.com/pypeclub/OpenPype/tree/3.14.4) (2022-10-19)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.14.3...3.14.4)

**🆕 New features**

- Webpublisher: use max next published version number  for all items in batch [\#3961](https://github.com/pypeclub/OpenPype/pull/3961)
- General: Control Thumbnail integration via explicit configuration profiles [\#3951](https://github.com/pypeclub/OpenPype/pull/3951)

**🚀 Enhancements**

- Publisher: Multiselection in card view [\#3993](https://github.com/pypeclub/OpenPype/pull/3993)
- TrayPublisher: Original Basename cause crash too early [\#3990](https://github.com/pypeclub/OpenPype/pull/3990)
- Tray Publisher: add `originalBasename` data to simple creators [\#3988](https://github.com/pypeclub/OpenPype/pull/3988)
- General: Custom paths to ffmpeg and OpenImageIO tools [\#3982](https://github.com/pypeclub/OpenPype/pull/3982)
- Integrate: Preserve existing subset group if instance does not set it for new version [\#3976](https://github.com/pypeclub/OpenPype/pull/3976)
- Publisher: Prepare publisher controller  for remote publishing [\#3972](https://github.com/pypeclub/OpenPype/pull/3972)
- Maya: new style dataclasses in maya deadline submitter plugin [\#3968](https://github.com/pypeclub/OpenPype/pull/3968)
- Maya: Define preffered Qt bindings for Qt.py and qtpy [\#3963](https://github.com/pypeclub/OpenPype/pull/3963)
- Settings: Move imageio from project anatomy to project settings \[pypeclub\] [\#3959](https://github.com/pypeclub/OpenPype/pull/3959)
- TrayPublisher: Extract thumbnail for other families [\#3952](https://github.com/pypeclub/OpenPype/pull/3952)
- Publisher: Pass instance to subset name method on update [\#3949](https://github.com/pypeclub/OpenPype/pull/3949)
- General: Set root environments before DCC launch [\#3947](https://github.com/pypeclub/OpenPype/pull/3947)
- Refactor: changed legacy way to update database for Hero version integrate [\#3941](https://github.com/pypeclub/OpenPype/pull/3941)
- Maya: Moved plugin from global to maya [\#3939](https://github.com/pypeclub/OpenPype/pull/3939)
- Publisher: Create dialog is part of main window [\#3936](https://github.com/pypeclub/OpenPype/pull/3936)
- Fusion: Implement Alembic and FBX mesh loader [\#3927](https://github.com/pypeclub/OpenPype/pull/3927)

**🐛 Bug fixes**

- TrayPublisher: Disable sequences in batch mov creator [\#3996](https://github.com/pypeclub/OpenPype/pull/3996)
- Fix - tags might be missing on representation [\#3985](https://github.com/pypeclub/OpenPype/pull/3985)
- Resolve: Fix usage of functions from lib [\#3983](https://github.com/pypeclub/OpenPype/pull/3983)
- Maya: remove invalid prefix token for non-multipart outputs [\#3981](https://github.com/pypeclub/OpenPype/pull/3981)
- Ftrack: Fix schema cache for Python 2 [\#3980](https://github.com/pypeclub/OpenPype/pull/3980)
- Maya: add object to attr.s declaration [\#3973](https://github.com/pypeclub/OpenPype/pull/3973)
- Maya: Deadline OutputFilePath hack regression for Renderman [\#3950](https://github.com/pypeclub/OpenPype/pull/3950)
- Houdini: Fix validate workfile paths for non-parm file references [\#3948](https://github.com/pypeclub/OpenPype/pull/3948)
- Photoshop: missed sync published version of workfile with workfile [\#3946](https://github.com/pypeclub/OpenPype/pull/3946)
- Maya: Set default value for RenderSetupIncludeLights option [\#3944](https://github.com/pypeclub/OpenPype/pull/3944)
- Maya: fix regression of Renderman Deadline hack [\#3943](https://github.com/pypeclub/OpenPype/pull/3943)
- Kitsu: 2 fixes, nb\_frames and Shot type error [\#3940](https://github.com/pypeclub/OpenPype/pull/3940)
- Tray: Change order of attribute changes [\#3938](https://github.com/pypeclub/OpenPype/pull/3938)
- AttributeDefs: Fix crashing multivalue of files widget [\#3937](https://github.com/pypeclub/OpenPype/pull/3937)
- General: Fix links query on hero version [\#3900](https://github.com/pypeclub/OpenPype/pull/3900)
- Publisher: Files Drag n Drop cleanup [\#3888](https://github.com/pypeclub/OpenPype/pull/3888)

**🔀 Refactored code**

- Flame: Import lib functions from lib [\#3992](https://github.com/pypeclub/OpenPype/pull/3992)
- General: Fix deprecated warning in legacy creator [\#3978](https://github.com/pypeclub/OpenPype/pull/3978)
- Blender: Remove openpype api imports [\#3977](https://github.com/pypeclub/OpenPype/pull/3977)
- General: Use direct import of resources [\#3964](https://github.com/pypeclub/OpenPype/pull/3964)
- General: Direct settings imports [\#3934](https://github.com/pypeclub/OpenPype/pull/3934)
- General: import 'Logger' from 'openpype.lib' [\#3926](https://github.com/pypeclub/OpenPype/pull/3926)
- General: Remove deprecated functions from lib [\#3907](https://github.com/pypeclub/OpenPype/pull/3907)

**Merged pull requests:**

- Maya + Yeti: Load Yeti Cache fix frame number recognition [\#3942](https://github.com/pypeclub/OpenPype/pull/3942)
- Fusion: Implement callbacks to Fusion's event system thread [\#3928](https://github.com/pypeclub/OpenPype/pull/3928)
- Photoshop: create single frame image in Ftrack as review [\#3908](https://github.com/pypeclub/OpenPype/pull/3908)

## [3.14.3](https://github.com/pypeclub/OpenPype/tree/3.14.3) (2022-10-03)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.14.2...3.14.3)

**🚀 Enhancements**

- Publisher: Enhancement proposals [\#3897](https://github.com/pypeclub/OpenPype/pull/3897)

**🐛 Bug fixes**

- Maya: Fix Render single camera validator [\#3929](https://github.com/pypeclub/OpenPype/pull/3929)
- Flame: loading multilayer exr to batch/reel is working [\#3901](https://github.com/pypeclub/OpenPype/pull/3901)
- Hiero: Fix inventory check on launch [\#3895](https://github.com/pypeclub/OpenPype/pull/3895)
- WebPublisher: Fix import after refactor [\#3891](https://github.com/pypeclub/OpenPype/pull/3891)

**🔀 Refactored code**

- Maya: Remove unused 'openpype.api' imports in plugins [\#3925](https://github.com/pypeclub/OpenPype/pull/3925)
- Resolve: Use new Extractor location [\#3918](https://github.com/pypeclub/OpenPype/pull/3918)
- Unreal: Use new Extractor location [\#3917](https://github.com/pypeclub/OpenPype/pull/3917)
- Flame: Use new Extractor location [\#3916](https://github.com/pypeclub/OpenPype/pull/3916)
- Houdini: Use new Extractor location [\#3894](https://github.com/pypeclub/OpenPype/pull/3894)
- Harmony: Use new Extractor location [\#3893](https://github.com/pypeclub/OpenPype/pull/3893)

**Merged pull requests:**

- Maya: Fix Scene Inventory possibly starting off-screen due to maya preferences [\#3923](https://github.com/pypeclub/OpenPype/pull/3923)

## [3.14.2](https://github.com/pypeclub/OpenPype/tree/3.14.2) (2022-09-12)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.14.1...3.14.2)

### 📖 Documentation

- Documentation: Anatomy templates [\#3618](https://github.com/pypeclub/OpenPype/pull/3618)

**🆕 New features**

- Nuke: Build workfile by template [\#3763](https://github.com/pypeclub/OpenPype/pull/3763)
- Houdini: Publishing workfiles [\#3697](https://github.com/pypeclub/OpenPype/pull/3697)
- Global: making collect audio plugin global [\#3679](https://github.com/pypeclub/OpenPype/pull/3679)

**🚀 Enhancements**

- Flame: Adding Creator's retimed shot and handles switch [\#3826](https://github.com/pypeclub/OpenPype/pull/3826)
- Flame: OpenPype submenu to batch and media manager [\#3825](https://github.com/pypeclub/OpenPype/pull/3825)
- General: Better pixmap scaling [\#3809](https://github.com/pypeclub/OpenPype/pull/3809)
- Photoshop: attempt to speed up ExtractImage [\#3793](https://github.com/pypeclub/OpenPype/pull/3793)
- SyncServer: Added cli commands for sync server [\#3765](https://github.com/pypeclub/OpenPype/pull/3765)
- Kitsu: Drop 'entities root' setting. [\#3739](https://github.com/pypeclub/OpenPype/pull/3739)
- git: update gitignore [\#3722](https://github.com/pypeclub/OpenPype/pull/3722)
- Blender: Publisher collect workfile representation [\#3670](https://github.com/pypeclub/OpenPype/pull/3670)
- Maya: move set render settings menu entry [\#3669](https://github.com/pypeclub/OpenPype/pull/3669)
- Scene Inventory: Maya add actions to select from or to scene [\#3659](https://github.com/pypeclub/OpenPype/pull/3659)
- Scene Inventory: Add subsetGroup column [\#3658](https://github.com/pypeclub/OpenPype/pull/3658)

**🐛 Bug fixes**

- General: Fix Pattern access in client code [\#3828](https://github.com/pypeclub/OpenPype/pull/3828)
- Launcher: Skip opening last work file works for groups [\#3822](https://github.com/pypeclub/OpenPype/pull/3822)
- Maya: Publishing data key change [\#3811](https://github.com/pypeclub/OpenPype/pull/3811)
- Igniter: Fix status handling when version is already installed [\#3804](https://github.com/pypeclub/OpenPype/pull/3804)
- Resolve: Addon import is Python 2 compatible [\#3798](https://github.com/pypeclub/OpenPype/pull/3798)
- Hiero: retimed clip publishing is working [\#3792](https://github.com/pypeclub/OpenPype/pull/3792)
- nuke: validate write node is not failing due wrong type [\#3780](https://github.com/pypeclub/OpenPype/pull/3780)
- Fix - changed format of version string in pyproject.toml [\#3777](https://github.com/pypeclub/OpenPype/pull/3777)
- Ftrack status fix typo prgoress -\> progress [\#3761](https://github.com/pypeclub/OpenPype/pull/3761)
- Fix version resolution [\#3757](https://github.com/pypeclub/OpenPype/pull/3757)
- Maya: `containerise` dont skip empty values [\#3674](https://github.com/pypeclub/OpenPype/pull/3674)

**🔀 Refactored code**

- Photoshop: Use new Extractor location [\#3789](https://github.com/pypeclub/OpenPype/pull/3789)
- Blender: Use new Extractor location [\#3787](https://github.com/pypeclub/OpenPype/pull/3787)
- AfterEffects: Use new Extractor location [\#3784](https://github.com/pypeclub/OpenPype/pull/3784)
- General: Remove unused teshost [\#3773](https://github.com/pypeclub/OpenPype/pull/3773)
- General: Copied 'Extractor' plugin to publish pipeline [\#3771](https://github.com/pypeclub/OpenPype/pull/3771)
- General: Move queries of asset and representation links [\#3770](https://github.com/pypeclub/OpenPype/pull/3770)
- General: Move create project folders to pipeline [\#3768](https://github.com/pypeclub/OpenPype/pull/3768)
- General: Create project function moved to client code [\#3766](https://github.com/pypeclub/OpenPype/pull/3766)
- Maya: Refactor submit deadline to use AbstractSubmitDeadline [\#3759](https://github.com/pypeclub/OpenPype/pull/3759)
- General: Change publish template settings location [\#3755](https://github.com/pypeclub/OpenPype/pull/3755)
- General: Move hostdirname functionality into host [\#3749](https://github.com/pypeclub/OpenPype/pull/3749)
- General: Move publish utils to pipeline [\#3745](https://github.com/pypeclub/OpenPype/pull/3745)
- Houdini: Define houdini as addon [\#3735](https://github.com/pypeclub/OpenPype/pull/3735)
- Fusion: Defined fusion as addon [\#3733](https://github.com/pypeclub/OpenPype/pull/3733)
- Flame: Defined flame as addon [\#3732](https://github.com/pypeclub/OpenPype/pull/3732)
- Resolve: Define resolve as addon [\#3727](https://github.com/pypeclub/OpenPype/pull/3727)

**Merged pull requests:**

- Standalone Publisher: Ignore empty labels, then still use name like other asset models [\#3779](https://github.com/pypeclub/OpenPype/pull/3779)
- Kitsu - sync\_all\_project - add list ignore\_projects [\#3776](https://github.com/pypeclub/OpenPype/pull/3776)

## [3.14.1](https://github.com/pypeclub/OpenPype/tree/3.14.1) (2022-08-30)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.14.0...3.14.1)

### 📖 Documentation

- Documentation: Few updates [\#3698](https://github.com/pypeclub/OpenPype/pull/3698)
- Documentation: Settings development [\#3660](https://github.com/pypeclub/OpenPype/pull/3660)

**🆕 New features**

- Webpublisher:change create flatten image into tri state [\#3678](https://github.com/pypeclub/OpenPype/pull/3678)
- Blender: validators code correction with settings and defaults [\#3662](https://github.com/pypeclub/OpenPype/pull/3662)

**🚀 Enhancements**

- General: Thumbnail can use project roots [\#3750](https://github.com/pypeclub/OpenPype/pull/3750)
- Settings: Remove settings lock on tray exit [\#3720](https://github.com/pypeclub/OpenPype/pull/3720)
- General: Added helper getters to modules manager [\#3712](https://github.com/pypeclub/OpenPype/pull/3712)
- Unreal: Define unreal as module and use host class [\#3701](https://github.com/pypeclub/OpenPype/pull/3701)
- Settings: Lock settings UI session [\#3700](https://github.com/pypeclub/OpenPype/pull/3700)
- General: Benevolent context label collector [\#3686](https://github.com/pypeclub/OpenPype/pull/3686)
- Ftrack: Store ftrack entities on hierarchy integration to instances [\#3677](https://github.com/pypeclub/OpenPype/pull/3677)
- Ftrack: More logs related to auto sync value change [\#3671](https://github.com/pypeclub/OpenPype/pull/3671)
- Blender: ops refresh manager after process events [\#3663](https://github.com/pypeclub/OpenPype/pull/3663)

**🐛 Bug fixes**

- Maya: Fix typo in getPanel argument `with_focus` -\> `withFocus` [\#3753](https://github.com/pypeclub/OpenPype/pull/3753)
- General: Smaller fixes of imports [\#3748](https://github.com/pypeclub/OpenPype/pull/3748)
- General: Logger tweaks [\#3741](https://github.com/pypeclub/OpenPype/pull/3741)
- Nuke: missing job dependency if multiple bake streams [\#3737](https://github.com/pypeclub/OpenPype/pull/3737)
- Nuke: color-space settings from anatomy is working [\#3721](https://github.com/pypeclub/OpenPype/pull/3721)
- Settings: Fix studio default anatomy save [\#3716](https://github.com/pypeclub/OpenPype/pull/3716)
- Maya: Use project name instead of project code [\#3709](https://github.com/pypeclub/OpenPype/pull/3709)
- Settings: Fix project overrides save [\#3708](https://github.com/pypeclub/OpenPype/pull/3708)
- Workfiles tool: Fix published workfile filtering [\#3704](https://github.com/pypeclub/OpenPype/pull/3704)
- PS, AE: Provide default variant value for workfile subset [\#3703](https://github.com/pypeclub/OpenPype/pull/3703)
- RoyalRender: handle host name that is not set [\#3695](https://github.com/pypeclub/OpenPype/pull/3695)
- Flame: retime is working on clip publishing [\#3684](https://github.com/pypeclub/OpenPype/pull/3684)
- Webpublisher: added check for empty context [\#3682](https://github.com/pypeclub/OpenPype/pull/3682)

**🔀 Refactored code**

- General: Move delivery logic to pipeline [\#3751](https://github.com/pypeclub/OpenPype/pull/3751)
- General: Host addons cleanup [\#3744](https://github.com/pypeclub/OpenPype/pull/3744)
- Webpublisher: Webpublisher is used as addon [\#3740](https://github.com/pypeclub/OpenPype/pull/3740)
- Photoshop: Defined photoshop as addon [\#3736](https://github.com/pypeclub/OpenPype/pull/3736)
- Harmony: Defined harmony as addon [\#3734](https://github.com/pypeclub/OpenPype/pull/3734)
- General: Module interfaces cleanup [\#3731](https://github.com/pypeclub/OpenPype/pull/3731)
- AfterEffects: Move AE functions from general lib [\#3730](https://github.com/pypeclub/OpenPype/pull/3730)
- Blender: Define blender as module [\#3729](https://github.com/pypeclub/OpenPype/pull/3729)
- AfterEffects: Define AfterEffects as module [\#3728](https://github.com/pypeclub/OpenPype/pull/3728)
- General: Replace PypeLogger with Logger [\#3725](https://github.com/pypeclub/OpenPype/pull/3725)
- Nuke: Define nuke as module [\#3724](https://github.com/pypeclub/OpenPype/pull/3724)
- General: Move subset name functionality [\#3723](https://github.com/pypeclub/OpenPype/pull/3723)
- General: Move creators plugin getter [\#3714](https://github.com/pypeclub/OpenPype/pull/3714)
- General: Move constants from lib to client [\#3713](https://github.com/pypeclub/OpenPype/pull/3713)
- Loader: Subset groups using client operations [\#3710](https://github.com/pypeclub/OpenPype/pull/3710)
- TVPaint: Defined as module [\#3707](https://github.com/pypeclub/OpenPype/pull/3707)
- StandalonePublisher: Define StandalonePublisher as module [\#3706](https://github.com/pypeclub/OpenPype/pull/3706)
- TrayPublisher: Define TrayPublisher as module [\#3705](https://github.com/pypeclub/OpenPype/pull/3705)
- General: Move context specific functions to context tools [\#3702](https://github.com/pypeclub/OpenPype/pull/3702)

**Merged pull requests:**

- Hiero: Define hiero as module [\#3717](https://github.com/pypeclub/OpenPype/pull/3717)
- Deadline: better logging for DL webservice failures [\#3694](https://github.com/pypeclub/OpenPype/pull/3694)
- Photoshop: resize saved images in ExtractReview for ffmpeg [\#3676](https://github.com/pypeclub/OpenPype/pull/3676)
- Nuke: Validation refactory to new publisher [\#3567](https://github.com/pypeclub/OpenPype/pull/3567)

## [3.14.0](https://github.com/pypeclub/OpenPype/tree/3.14.0) (2022-08-18)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.13.0...3.14.0)

**🆕 New features**

- Maya: Build workfile by template [\#3578](https://github.com/pypeclub/OpenPype/pull/3578)
- Maya: Implementation of JSON layout for Unreal workflow [\#3353](https://github.com/pypeclub/OpenPype/pull/3353)
- Maya: Build workfile by template [\#3315](https://github.com/pypeclub/OpenPype/pull/3315)

**🚀 Enhancements**

- Ftrack: Addiotional component metadata [\#3685](https://github.com/pypeclub/OpenPype/pull/3685)
- Ftrack: Set task status on farm publishing [\#3680](https://github.com/pypeclub/OpenPype/pull/3680)
- Ftrack: Set task status on task creation in integrate hierarchy [\#3675](https://github.com/pypeclub/OpenPype/pull/3675)
- Maya: Disable rendering of all lights for render instances submitted through Deadline. [\#3661](https://github.com/pypeclub/OpenPype/pull/3661)
- General: Optimized OCIO configs [\#3650](https://github.com/pypeclub/OpenPype/pull/3650)

**🐛 Bug fixes**

- General: Switch from hero version to versioned works [\#3691](https://github.com/pypeclub/OpenPype/pull/3691)
- General: Fix finding of last version [\#3656](https://github.com/pypeclub/OpenPype/pull/3656)
- General: Extract Review can scale with pixel aspect ratio [\#3644](https://github.com/pypeclub/OpenPype/pull/3644)
- Maya: Refactor moved usage of CreateRender settings [\#3643](https://github.com/pypeclub/OpenPype/pull/3643)
- General: Hero version representations have full context [\#3638](https://github.com/pypeclub/OpenPype/pull/3638)
- Nuke: color settings for render write node is working now [\#3632](https://github.com/pypeclub/OpenPype/pull/3632)
- Maya: FBX support for update in reference loader [\#3631](https://github.com/pypeclub/OpenPype/pull/3631)

**🔀 Refactored code**

- General: Use client projects getter [\#3673](https://github.com/pypeclub/OpenPype/pull/3673)
- Resolve: Match folder structure to other hosts [\#3653](https://github.com/pypeclub/OpenPype/pull/3653)
- Maya: Hosts as modules [\#3647](https://github.com/pypeclub/OpenPype/pull/3647)
- TimersManager: Plugins are in timers manager module [\#3639](https://github.com/pypeclub/OpenPype/pull/3639)
- General: Move workfiles functions into pipeline [\#3637](https://github.com/pypeclub/OpenPype/pull/3637)
- General: Workfiles builder using query functions [\#3598](https://github.com/pypeclub/OpenPype/pull/3598)

**Merged pull requests:**

- Deadline: Global job pre load is not Pype 2 compatible [\#3666](https://github.com/pypeclub/OpenPype/pull/3666)
- Maya: Remove unused get current renderer logic [\#3645](https://github.com/pypeclub/OpenPype/pull/3645)
- Kitsu|Fix: Movie project type fails & first loop children names [\#3636](https://github.com/pypeclub/OpenPype/pull/3636)
- fix the bug of failing to extract look when UDIMs format used in AiImage [\#3628](https://github.com/pypeclub/OpenPype/pull/3628)

## [3.13.0](https://github.com/pypeclub/OpenPype/tree/3.13.0) (2022-08-09)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.12.2...3.13.0)

**🆕 New features**

- Support for mutliple installed versions - 3.13 [\#3605](https://github.com/pypeclub/OpenPype/pull/3605)
- Traypublisher: simple editorial publishing [\#3492](https://github.com/pypeclub/OpenPype/pull/3492)

**🚀 Enhancements**

- Editorial: Mix audio use side file for ffmpeg filters [\#3630](https://github.com/pypeclub/OpenPype/pull/3630)
- Ftrack: Comment template can contain optional keys [\#3615](https://github.com/pypeclub/OpenPype/pull/3615)
- Ftrack: Add more metadata to ftrack components [\#3612](https://github.com/pypeclub/OpenPype/pull/3612)
- General: Add context to pyblish context [\#3594](https://github.com/pypeclub/OpenPype/pull/3594)
- Kitsu: Shot&Sequence name with prefix over appends [\#3593](https://github.com/pypeclub/OpenPype/pull/3593)
- Photoshop: implemented {layer} placeholder in subset template [\#3591](https://github.com/pypeclub/OpenPype/pull/3591)
- General: Python module appdirs from git [\#3589](https://github.com/pypeclub/OpenPype/pull/3589)
- Ftrack: Update ftrack api to 2.3.3 [\#3588](https://github.com/pypeclub/OpenPype/pull/3588)
- General: New Integrator small fixes [\#3583](https://github.com/pypeclub/OpenPype/pull/3583)
- Maya: Render Creator has configurable options. [\#3097](https://github.com/pypeclub/OpenPype/pull/3097)

**🐛 Bug fixes**

- Maya:  fix aov separator in Redshift [\#3625](https://github.com/pypeclub/OpenPype/pull/3625)
- Fix for multi-version build on Mac [\#3622](https://github.com/pypeclub/OpenPype/pull/3622)
- Ftrack: Sync hierarchical attributes can handle new created entities [\#3621](https://github.com/pypeclub/OpenPype/pull/3621)
- General: Extract review aspect ratio scale is calculated by ffmpeg [\#3620](https://github.com/pypeclub/OpenPype/pull/3620)
- Maya: Fix types of default settings [\#3617](https://github.com/pypeclub/OpenPype/pull/3617)
- Integrator: Don't force to have dot before frame [\#3611](https://github.com/pypeclub/OpenPype/pull/3611)
- AfterEffects: refactored integrate doesnt work formulti frame publishes [\#3610](https://github.com/pypeclub/OpenPype/pull/3610)
- Maya look data contents fails with custom attribute on group [\#3607](https://github.com/pypeclub/OpenPype/pull/3607)
- TrayPublisher: Fix wrong conflict merge [\#3600](https://github.com/pypeclub/OpenPype/pull/3600)
- Bugfix: Add OCIO as submodule to prepare for handling `maketx` color space conversion. [\#3590](https://github.com/pypeclub/OpenPype/pull/3590)
- Fix general settings environment variables resolution [\#3587](https://github.com/pypeclub/OpenPype/pull/3587)
- Editorial publishing workflow improvements [\#3580](https://github.com/pypeclub/OpenPype/pull/3580)
- General: Update imports in start script [\#3579](https://github.com/pypeclub/OpenPype/pull/3579)
- Nuke: render family integration consistency  [\#3576](https://github.com/pypeclub/OpenPype/pull/3576)
- Ftrack: Handle missing published path in integrator [\#3570](https://github.com/pypeclub/OpenPype/pull/3570)
- Nuke: publish existing frames with slate with correct range [\#3555](https://github.com/pypeclub/OpenPype/pull/3555)

**🔀 Refactored code**

- General: Plugin settings handled by plugins [\#3623](https://github.com/pypeclub/OpenPype/pull/3623)
- General: Naive implementation of document create, update, delete [\#3601](https://github.com/pypeclub/OpenPype/pull/3601)
- General: Use query functions in general code [\#3596](https://github.com/pypeclub/OpenPype/pull/3596)
- General: Separate extraction of template data into more functions [\#3574](https://github.com/pypeclub/OpenPype/pull/3574)
- General: Lib cleanup [\#3571](https://github.com/pypeclub/OpenPype/pull/3571)

**Merged pull requests:**

- Webpublisher: timeout for PS studio processing [\#3619](https://github.com/pypeclub/OpenPype/pull/3619)
- Core: translated validate\_containers.py into New publisher style [\#3614](https://github.com/pypeclub/OpenPype/pull/3614)
- Enable write color sets on animation publish automatically [\#3582](https://github.com/pypeclub/OpenPype/pull/3582)

## [3.12.2](https://github.com/pypeclub/OpenPype/tree/3.12.2) (2022-07-27)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.12.1...3.12.2)

### 📖 Documentation

- Update website with more studios [\#3554](https://github.com/pypeclub/OpenPype/pull/3554)
- Documentation: Update publishing dev docs [\#3549](https://github.com/pypeclub/OpenPype/pull/3549)

**🚀 Enhancements**

- General: Global thumbnail extractor is ready for more cases [\#3561](https://github.com/pypeclub/OpenPype/pull/3561)
- Maya: add additional validators to Settings [\#3540](https://github.com/pypeclub/OpenPype/pull/3540)
- General: Interactive console in cli [\#3526](https://github.com/pypeclub/OpenPype/pull/3526)
- Ftrack: Automatic daily review session creation can define trigger hour [\#3516](https://github.com/pypeclub/OpenPype/pull/3516)
- Ftrack: add source into Note [\#3509](https://github.com/pypeclub/OpenPype/pull/3509)
- Ftrack: Trigger custom ftrack topic of project structure creation [\#3506](https://github.com/pypeclub/OpenPype/pull/3506)
- Settings UI: Add extract to file action on project view [\#3505](https://github.com/pypeclub/OpenPype/pull/3505)
- Add pack and unpack convenience scripts [\#3502](https://github.com/pypeclub/OpenPype/pull/3502)
- General: Event system [\#3499](https://github.com/pypeclub/OpenPype/pull/3499)
- NewPublisher: Keep plugins with mismatch target in report [\#3498](https://github.com/pypeclub/OpenPype/pull/3498)
- Nuke: load clip with options from settings [\#3497](https://github.com/pypeclub/OpenPype/pull/3497)
- TrayPublisher: implemented render\_mov\_batch  [\#3486](https://github.com/pypeclub/OpenPype/pull/3486)
- Migrate basic families to the new Tray Publisher [\#3469](https://github.com/pypeclub/OpenPype/pull/3469)
- Enhance powershell build scripts [\#1827](https://github.com/pypeclub/OpenPype/pull/1827)

**🐛 Bug fixes**

- Maya: fix Review image plane attribute  [\#3569](https://github.com/pypeclub/OpenPype/pull/3569)
- Maya: Fix animated attributes \(ie. overscan\) on loaded cameras breaking review publishing. [\#3562](https://github.com/pypeclub/OpenPype/pull/3562)
- NewPublisher: Python 2 compatible html escape [\#3559](https://github.com/pypeclub/OpenPype/pull/3559)
- Remove invalid submodules from `/vendor` [\#3557](https://github.com/pypeclub/OpenPype/pull/3557)
- General: Remove hosts filter on integrator plugins [\#3556](https://github.com/pypeclub/OpenPype/pull/3556)
- Settings: Clean default values of environments [\#3550](https://github.com/pypeclub/OpenPype/pull/3550)
- Module interfaces: Fix import error [\#3547](https://github.com/pypeclub/OpenPype/pull/3547)
- Workfiles tool: Show of tool and it's flags [\#3539](https://github.com/pypeclub/OpenPype/pull/3539)
- General: Create workfile documents works again [\#3538](https://github.com/pypeclub/OpenPype/pull/3538)
- Additional fixes for powershell scripts [\#3525](https://github.com/pypeclub/OpenPype/pull/3525)
- Maya: Added wrapper around cmds.setAttr [\#3523](https://github.com/pypeclub/OpenPype/pull/3523)
- Nuke: double slate [\#3521](https://github.com/pypeclub/OpenPype/pull/3521)
- General: Fix hash of centos oiio archive [\#3519](https://github.com/pypeclub/OpenPype/pull/3519)
- Maya: Renderman display output fix [\#3514](https://github.com/pypeclub/OpenPype/pull/3514)
- TrayPublisher: Simple creation enhancements and fixes [\#3513](https://github.com/pypeclub/OpenPype/pull/3513)
- NewPublisher: Publish attributes are properly collected [\#3510](https://github.com/pypeclub/OpenPype/pull/3510)
- TrayPublisher: Make sure host name is filled [\#3504](https://github.com/pypeclub/OpenPype/pull/3504)
- NewPublisher: Groups work and enum multivalue [\#3501](https://github.com/pypeclub/OpenPype/pull/3501)

**🔀 Refactored code**

- General: Use query functions in integrator [\#3563](https://github.com/pypeclub/OpenPype/pull/3563)
- General: Mongo core connection moved to client [\#3531](https://github.com/pypeclub/OpenPype/pull/3531)
- Refactor Integrate Asset [\#3530](https://github.com/pypeclub/OpenPype/pull/3530)
- General: Client docstrings cleanup [\#3529](https://github.com/pypeclub/OpenPype/pull/3529)
- General: Move load related functions into pipeline [\#3527](https://github.com/pypeclub/OpenPype/pull/3527)
- General: Get current context document functions [\#3522](https://github.com/pypeclub/OpenPype/pull/3522)
- Kitsu: Use query function from client [\#3496](https://github.com/pypeclub/OpenPype/pull/3496)
- TimersManager: Use query functions [\#3495](https://github.com/pypeclub/OpenPype/pull/3495)
- Deadline: Use query functions [\#3466](https://github.com/pypeclub/OpenPype/pull/3466)
- Refactor Integrate Asset [\#2898](https://github.com/pypeclub/OpenPype/pull/2898)

**Merged pull requests:**

- Maya: fix active pane loss [\#3566](https://github.com/pypeclub/OpenPype/pull/3566)

## [3.12.1](https://github.com/pypeclub/OpenPype/tree/3.12.1) (2022-07-13)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.12.0...3.12.1)

### 📖 Documentation

- Docs: Added minimal permissions for MongoDB [\#3441](https://github.com/pypeclub/OpenPype/pull/3441)

**🆕 New features**

- Maya: Add VDB to Arnold loader [\#3433](https://github.com/pypeclub/OpenPype/pull/3433)

**🚀 Enhancements**

- TrayPublisher: Added more options for grouping of instances [\#3494](https://github.com/pypeclub/OpenPype/pull/3494)
- NewPublisher: Align creator attributes from top to bottom [\#3487](https://github.com/pypeclub/OpenPype/pull/3487)
- NewPublisher: Added ability to use label of instance [\#3484](https://github.com/pypeclub/OpenPype/pull/3484)
- General: Creator Plugins have access to project [\#3476](https://github.com/pypeclub/OpenPype/pull/3476)
- General: Better arguments order in creator init [\#3475](https://github.com/pypeclub/OpenPype/pull/3475)
- Ftrack: Trigger custom ftrack events on project creation and preparation [\#3465](https://github.com/pypeclub/OpenPype/pull/3465)
- Windows installer: Clean old files and add version subfolder [\#3445](https://github.com/pypeclub/OpenPype/pull/3445)
- Blender: Bugfix - Set fps properly on open [\#3426](https://github.com/pypeclub/OpenPype/pull/3426)
- Hiero: Add custom scripts menu [\#3425](https://github.com/pypeclub/OpenPype/pull/3425)
- Blender: pre pyside install for all platforms [\#3400](https://github.com/pypeclub/OpenPype/pull/3400)
- Maya: Add additional playblast options to review Extractor. [\#3384](https://github.com/pypeclub/OpenPype/pull/3384)
- Maya: Ability to set resolution for playblasts from asset, and override through review instance. [\#3360](https://github.com/pypeclub/OpenPype/pull/3360)
- Maya: Redshift Volume Loader Implement update, remove, switch + fix vdb sequence support [\#3197](https://github.com/pypeclub/OpenPype/pull/3197)
- Maya: Implement `iter_visible_nodes_in_range` for extracting Alembics [\#3100](https://github.com/pypeclub/OpenPype/pull/3100)

**🐛 Bug fixes**

- TrayPublisher: Keep use instance label in list view [\#3493](https://github.com/pypeclub/OpenPype/pull/3493)
- General: Extract review use first frame of input sequence [\#3491](https://github.com/pypeclub/OpenPype/pull/3491)
- General: Fix Plist loading for application launch [\#3485](https://github.com/pypeclub/OpenPype/pull/3485)
- Nuke: Workfile tools open on start [\#3479](https://github.com/pypeclub/OpenPype/pull/3479)
- New Publisher: Disabled context change allows creation [\#3478](https://github.com/pypeclub/OpenPype/pull/3478)
- General: thumbnail extractor fix [\#3474](https://github.com/pypeclub/OpenPype/pull/3474)
- Kitsu: bugfix with sync-service ans publish plugins [\#3473](https://github.com/pypeclub/OpenPype/pull/3473)
- Flame: solved problem with multi-selected loading [\#3470](https://github.com/pypeclub/OpenPype/pull/3470)
- General: Fix query function in update logic [\#3468](https://github.com/pypeclub/OpenPype/pull/3468)
- Resolve: removed few bugs [\#3464](https://github.com/pypeclub/OpenPype/pull/3464)
- General: Delete old versions is safer when ftrack is disabled [\#3462](https://github.com/pypeclub/OpenPype/pull/3462)
- Nuke: fixing metadata slate TC difference [\#3455](https://github.com/pypeclub/OpenPype/pull/3455)
- Nuke: prerender reviewable fails [\#3450](https://github.com/pypeclub/OpenPype/pull/3450)
- Maya: fix hashing in Python 3 for tile rendering [\#3447](https://github.com/pypeclub/OpenPype/pull/3447)
- LogViewer: Escape html characters in log message [\#3443](https://github.com/pypeclub/OpenPype/pull/3443)
- Nuke: Slate frame is integrated [\#3427](https://github.com/pypeclub/OpenPype/pull/3427)
- Maya: Camera extra data - additional fix for \#3304 [\#3386](https://github.com/pypeclub/OpenPype/pull/3386)
- Maya: Handle excluding `model` family from frame range validator. [\#3370](https://github.com/pypeclub/OpenPype/pull/3370)

**🔀 Refactored code**

- Maya: Merge animation + pointcache extractor logic [\#3461](https://github.com/pypeclub/OpenPype/pull/3461)
- Maya: Re-use `maintained_time` from lib [\#3460](https://github.com/pypeclub/OpenPype/pull/3460)
- General: Use query functions in global plugins [\#3459](https://github.com/pypeclub/OpenPype/pull/3459)
- Clockify: Use query functions in clockify actions [\#3458](https://github.com/pypeclub/OpenPype/pull/3458)
- General: Use query functions in rest api calls [\#3457](https://github.com/pypeclub/OpenPype/pull/3457)
- General: Use query functions in openpype lib functions [\#3454](https://github.com/pypeclub/OpenPype/pull/3454)
- General: Use query functions in load utils [\#3446](https://github.com/pypeclub/OpenPype/pull/3446)
- General: Move publish plugin and publish render abstractions [\#3442](https://github.com/pypeclub/OpenPype/pull/3442)
- General: Use Anatomy after move to pipeline [\#3436](https://github.com/pypeclub/OpenPype/pull/3436)
- General: Anatomy moved to pipeline [\#3435](https://github.com/pypeclub/OpenPype/pull/3435)
- Fusion: Use client query functions [\#3380](https://github.com/pypeclub/OpenPype/pull/3380)
- Resolve: Use client query functions [\#3379](https://github.com/pypeclub/OpenPype/pull/3379)
- General: Host implementation defined with class [\#3337](https://github.com/pypeclub/OpenPype/pull/3337)

## [3.12.0](https://github.com/pypeclub/OpenPype/tree/3.12.0) (2022-06-28)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.11.1...3.12.0)

### 📖 Documentation

- Fix typo in documentation: pyenv on mac [\#3417](https://github.com/pypeclub/OpenPype/pull/3417)
- Linux: update OIIO package [\#3401](https://github.com/pypeclub/OpenPype/pull/3401)

**🆕 New features**

- Shotgrid: Add production beta of shotgrid integration [\#2921](https://github.com/pypeclub/OpenPype/pull/2921)

**🚀 Enhancements**

- Webserver: Added CORS middleware [\#3422](https://github.com/pypeclub/OpenPype/pull/3422)
- Attribute Defs UI: Files widget show what is allowed to drop in [\#3411](https://github.com/pypeclub/OpenPype/pull/3411)
- General: Add ability to change user value for templates [\#3366](https://github.com/pypeclub/OpenPype/pull/3366)
- Hosts: More options for in-host callbacks [\#3357](https://github.com/pypeclub/OpenPype/pull/3357)
- Multiverse: expose some settings to GUI [\#3350](https://github.com/pypeclub/OpenPype/pull/3350)
- Maya: Allow more data to be published along camera 🎥  [\#3304](https://github.com/pypeclub/OpenPype/pull/3304)
- Add root keys and project keys to create starting folder [\#2755](https://github.com/pypeclub/OpenPype/pull/2755)

**🐛 Bug fixes**

- NewPublisher: Fix subset name change on change of creator plugin [\#3420](https://github.com/pypeclub/OpenPype/pull/3420)
- Bug: fix invalid avalon import [\#3418](https://github.com/pypeclub/OpenPype/pull/3418)
- Nuke: Fix keyword argument in query function [\#3414](https://github.com/pypeclub/OpenPype/pull/3414)
- Houdini: fix loading and updating vbd/bgeo sequences [\#3408](https://github.com/pypeclub/OpenPype/pull/3408)
- Nuke: Collect representation files based on Write [\#3407](https://github.com/pypeclub/OpenPype/pull/3407)
- General: Filter representations before integration start [\#3398](https://github.com/pypeclub/OpenPype/pull/3398)
- Maya: look collector typo [\#3392](https://github.com/pypeclub/OpenPype/pull/3392)
- TVPaint: Make sure exit code is set to not None [\#3382](https://github.com/pypeclub/OpenPype/pull/3382)
- Maya: vray device aspect ratio fix [\#3381](https://github.com/pypeclub/OpenPype/pull/3381)
- Flame: bunch of publishing issues [\#3377](https://github.com/pypeclub/OpenPype/pull/3377)
- Harmony: added unc path to zifile command in Harmony [\#3372](https://github.com/pypeclub/OpenPype/pull/3372)
- Standalone: settings improvements [\#3355](https://github.com/pypeclub/OpenPype/pull/3355)
- Nuke: Load full model hierarchy by default [\#3328](https://github.com/pypeclub/OpenPype/pull/3328)
- Nuke: multiple baking streams with correct slate [\#3245](https://github.com/pypeclub/OpenPype/pull/3245)
- Maya: fix image prefix warning in validator [\#3128](https://github.com/pypeclub/OpenPype/pull/3128)

**🔀 Refactored code**

- Unreal: Use client query functions [\#3421](https://github.com/pypeclub/OpenPype/pull/3421)
- General: Move editorial lib to pipeline [\#3419](https://github.com/pypeclub/OpenPype/pull/3419)
- Kitsu: renaming to plural func sync\_all\_projects [\#3397](https://github.com/pypeclub/OpenPype/pull/3397)
- Houdini: Use client query functions [\#3395](https://github.com/pypeclub/OpenPype/pull/3395)
- Hiero: Use client query functions [\#3393](https://github.com/pypeclub/OpenPype/pull/3393)
- Nuke: Use client query functions [\#3391](https://github.com/pypeclub/OpenPype/pull/3391)
- Maya: Use client query functions [\#3385](https://github.com/pypeclub/OpenPype/pull/3385)
- Harmony: Use client query functions [\#3378](https://github.com/pypeclub/OpenPype/pull/3378)
- Celaction: Use client query functions [\#3376](https://github.com/pypeclub/OpenPype/pull/3376)
- Photoshop: Use client query functions [\#3375](https://github.com/pypeclub/OpenPype/pull/3375)
- AfterEffects: Use client query functions [\#3374](https://github.com/pypeclub/OpenPype/pull/3374)
- TVPaint: Use client query functions [\#3340](https://github.com/pypeclub/OpenPype/pull/3340)
- Ftrack: Use client query functions [\#3339](https://github.com/pypeclub/OpenPype/pull/3339)
- Standalone Publisher: Use client query functions [\#3330](https://github.com/pypeclub/OpenPype/pull/3330)

**Merged pull requests:**

- Sync Queue: Added far future value for null values for dates [\#3371](https://github.com/pypeclub/OpenPype/pull/3371)
- Maya - added support for single frame playblast review [\#3369](https://github.com/pypeclub/OpenPype/pull/3369)
- Houdini: Implement Redshift Proxy Export [\#3196](https://github.com/pypeclub/OpenPype/pull/3196)

## [3.11.1](https://github.com/pypeclub/OpenPype/tree/3.11.1) (2022-06-20)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.11.0...3.11.1)

**🆕 New features**

- Flame: custom export temp folder [\#3346](https://github.com/pypeclub/OpenPype/pull/3346)
- Nuke: removing third-party plugins   [\#3344](https://github.com/pypeclub/OpenPype/pull/3344)

**🚀 Enhancements**

- Pyblish Pype: Hiding/Close issues [\#3367](https://github.com/pypeclub/OpenPype/pull/3367)
- Ftrack: Removed requirement of pypeclub role from default settings [\#3354](https://github.com/pypeclub/OpenPype/pull/3354)
- Kitsu: Prevent crash on missing frames information [\#3352](https://github.com/pypeclub/OpenPype/pull/3352)
- Ftrack: Open browser from tray [\#3320](https://github.com/pypeclub/OpenPype/pull/3320)
- Enhancement: More control over thumbnail processing. [\#3259](https://github.com/pypeclub/OpenPype/pull/3259)

**🐛 Bug fixes**

- Nuke: bake streams with slate on farm [\#3368](https://github.com/pypeclub/OpenPype/pull/3368)
- Harmony: audio validator has wrong logic [\#3364](https://github.com/pypeclub/OpenPype/pull/3364)
- Nuke: Fix missing variable in extract thumbnail [\#3363](https://github.com/pypeclub/OpenPype/pull/3363)
- Nuke: Fix precollect writes [\#3361](https://github.com/pypeclub/OpenPype/pull/3361)
- AE- fix validate\_scene\_settings and renderLocal [\#3358](https://github.com/pypeclub/OpenPype/pull/3358)
- deadline: fixing misidentification of revieables [\#3356](https://github.com/pypeclub/OpenPype/pull/3356)
- General: Create only one thumbnail per instance [\#3351](https://github.com/pypeclub/OpenPype/pull/3351)
- nuke: adding extract thumbnail settings 3.10 [\#3347](https://github.com/pypeclub/OpenPype/pull/3347)
- General: Fix last version function [\#3345](https://github.com/pypeclub/OpenPype/pull/3345)
- Deadline: added OPENPYPE\_MONGO to filter [\#3336](https://github.com/pypeclub/OpenPype/pull/3336)
- Nuke: fixing farm publishing if review is disabled [\#3306](https://github.com/pypeclub/OpenPype/pull/3306)
- Maya: Fix Yeti errors on Create, Publish and Load [\#3198](https://github.com/pypeclub/OpenPype/pull/3198)

**🔀 Refactored code**

- Webpublisher: Use client query functions [\#3333](https://github.com/pypeclub/OpenPype/pull/3333)

## [3.11.0](https://github.com/pypeclub/OpenPype/tree/3.11.0) (2022-06-17)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.10.0...3.11.0)

### 📖 Documentation

- Documentation: Add app key to template documentation [\#3299](https://github.com/pypeclub/OpenPype/pull/3299)
- doc: adding royal render and multiverse to the web site [\#3285](https://github.com/pypeclub/OpenPype/pull/3285)
- Module: Kitsu module [\#2650](https://github.com/pypeclub/OpenPype/pull/2650)

**🆕 New features**

- Multiverse: fixed composition write, full docs, cosmetics [\#3178](https://github.com/pypeclub/OpenPype/pull/3178)

**🚀 Enhancements**

- Settings: Settings can be extracted from UI [\#3323](https://github.com/pypeclub/OpenPype/pull/3323)
- updated poetry installation source [\#3316](https://github.com/pypeclub/OpenPype/pull/3316)
- Ftrack: Action to easily create daily review session [\#3310](https://github.com/pypeclub/OpenPype/pull/3310)
- TVPaint: Extractor use mark in/out range to render [\#3309](https://github.com/pypeclub/OpenPype/pull/3309)
- Ftrack: Delivery action can work on ReviewSessions [\#3307](https://github.com/pypeclub/OpenPype/pull/3307)
- Maya: Look assigner UI improvements [\#3298](https://github.com/pypeclub/OpenPype/pull/3298)
- Ftrack: Action to transfer values of hierarchical attributes [\#3284](https://github.com/pypeclub/OpenPype/pull/3284)
- Maya: better handling of legacy review subsets names [\#3269](https://github.com/pypeclub/OpenPype/pull/3269)
- General: Updated windows oiio tool [\#3268](https://github.com/pypeclub/OpenPype/pull/3268)
- Unreal: add support for skeletalMesh and staticMesh to loaders [\#3267](https://github.com/pypeclub/OpenPype/pull/3267)
- Maya: reference loaders could store placeholder in referenced url [\#3264](https://github.com/pypeclub/OpenPype/pull/3264)
- TVPaint: Init file for TVPaint worker also handle guideline images [\#3250](https://github.com/pypeclub/OpenPype/pull/3250)
- Nuke: Change default icon path in settings [\#3247](https://github.com/pypeclub/OpenPype/pull/3247)
- Maya: publishing of animation and pointcache on a farm [\#3225](https://github.com/pypeclub/OpenPype/pull/3225)
- Maya: Look assigner UI improvements [\#3208](https://github.com/pypeclub/OpenPype/pull/3208)
- Nuke: add pointcache and animation to loader [\#3186](https://github.com/pypeclub/OpenPype/pull/3186)
- Nuke: Add a gizmo menu [\#3172](https://github.com/pypeclub/OpenPype/pull/3172)
- Support for Unreal 5 [\#3122](https://github.com/pypeclub/OpenPype/pull/3122)

**🐛 Bug fixes**

- General: Handle empty source key on instance [\#3342](https://github.com/pypeclub/OpenPype/pull/3342)
- Houdini: Fix Houdini VDB manage update wrong file attribute name [\#3322](https://github.com/pypeclub/OpenPype/pull/3322)
- Nuke: anatomy compatibility issue hacks [\#3321](https://github.com/pypeclub/OpenPype/pull/3321)
- hiero: otio p3 compatibility issue - metadata on effect use update 3.11 [\#3314](https://github.com/pypeclub/OpenPype/pull/3314)
- General: Vendorized modules for Python 2 and update poetry lock [\#3305](https://github.com/pypeclub/OpenPype/pull/3305)
- Fix - added local targets to install host [\#3303](https://github.com/pypeclub/OpenPype/pull/3303)
- Settings: Add missing default settings for nuke gizmo [\#3301](https://github.com/pypeclub/OpenPype/pull/3301)
- Maya: Fix swaped width and height in reviews [\#3300](https://github.com/pypeclub/OpenPype/pull/3300)
- Maya: point cache publish handles Maya instances [\#3297](https://github.com/pypeclub/OpenPype/pull/3297)
- Global: extract review slate issues [\#3286](https://github.com/pypeclub/OpenPype/pull/3286)
- Webpublisher: return only active projects in ProjectsEndpoint [\#3281](https://github.com/pypeclub/OpenPype/pull/3281)
- Hiero: add support for task tags 3.10.x [\#3279](https://github.com/pypeclub/OpenPype/pull/3279)
- General: Fix Oiio tool path resolving [\#3278](https://github.com/pypeclub/OpenPype/pull/3278)
- Maya: Fix udim support for e.g. uppercase \<UDIM\> tag [\#3266](https://github.com/pypeclub/OpenPype/pull/3266)
- Nuke: bake reformat was failing on string type [\#3261](https://github.com/pypeclub/OpenPype/pull/3261)
- Maya: hotfix Pxr multitexture in looks [\#3260](https://github.com/pypeclub/OpenPype/pull/3260)
- Unreal: Fix Camera Loading if Layout is missing [\#3255](https://github.com/pypeclub/OpenPype/pull/3255)
- Unreal: Fixed Animation loading in UE5 [\#3240](https://github.com/pypeclub/OpenPype/pull/3240)
- Unreal: Fixed Render creation in UE5 [\#3239](https://github.com/pypeclub/OpenPype/pull/3239)
- Unreal: Fixed Camera loading in UE5 [\#3238](https://github.com/pypeclub/OpenPype/pull/3238)
- Flame: debugging [\#3224](https://github.com/pypeclub/OpenPype/pull/3224)
- add silent audio to slate [\#3162](https://github.com/pypeclub/OpenPype/pull/3162)
- Add timecode to slate [\#2929](https://github.com/pypeclub/OpenPype/pull/2929)

**🔀 Refactored code**

- Blender: Use client query functions [\#3331](https://github.com/pypeclub/OpenPype/pull/3331)
- General: Define query functions [\#3288](https://github.com/pypeclub/OpenPype/pull/3288)

**Merged pull requests:**

- Maya: add pointcache family to gpu cache loader [\#3318](https://github.com/pypeclub/OpenPype/pull/3318)
- Maya look: skip empty file attributes [\#3274](https://github.com/pypeclub/OpenPype/pull/3274)

## [3.10.0](https://github.com/pypeclub/OpenPype/tree/3.10.0) (2022-05-26)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.9.8...3.10.0)

### 📖 Documentation

- Docs: add all-contributors config and initial list [\#3094](https://github.com/pypeclub/OpenPype/pull/3094)
- Nuke docs with videos [\#3052](https://github.com/pypeclub/OpenPype/pull/3052)

**🆕 New features**

- General: OpenPype modules publish plugins are registered in host [\#3180](https://github.com/pypeclub/OpenPype/pull/3180)
- General: Creator plugins from addons can be registered [\#3179](https://github.com/pypeclub/OpenPype/pull/3179)
- Ftrack: Single image reviewable [\#3157](https://github.com/pypeclub/OpenPype/pull/3157)
- Nuke: Expose write attributes to settings [\#3123](https://github.com/pypeclub/OpenPype/pull/3123)
- Hiero: Initial frame publish support [\#3106](https://github.com/pypeclub/OpenPype/pull/3106)
- Unreal: Render Publishing [\#2917](https://github.com/pypeclub/OpenPype/pull/2917)
- AfterEffects: Implemented New Publisher [\#2838](https://github.com/pypeclub/OpenPype/pull/2838)
- Unreal: Rendering implementation [\#2410](https://github.com/pypeclub/OpenPype/pull/2410)

**🚀 Enhancements**

- Maya: FBX camera export [\#3253](https://github.com/pypeclub/OpenPype/pull/3253)
- General: updating common vendor `scriptmenu` to 1.5.2 [\#3246](https://github.com/pypeclub/OpenPype/pull/3246)
- Project Manager: Allow to paste Tasks into multiple assets at the same time [\#3226](https://github.com/pypeclub/OpenPype/pull/3226)
- Project manager: Sped up project load [\#3216](https://github.com/pypeclub/OpenPype/pull/3216)
- Loader UI: Speed issues of loader with sync server [\#3199](https://github.com/pypeclub/OpenPype/pull/3199)
- Looks: add basic support for Renderman [\#3190](https://github.com/pypeclub/OpenPype/pull/3190)
- Maya: added clean\_import option to Import loader [\#3181](https://github.com/pypeclub/OpenPype/pull/3181)
- Add the scripts menu definition to nuke [\#3168](https://github.com/pypeclub/OpenPype/pull/3168)
- Maya: add maya 2023 to default applications [\#3167](https://github.com/pypeclub/OpenPype/pull/3167)
- Compressed bgeo publishing in SAP and Houdini loader [\#3153](https://github.com/pypeclub/OpenPype/pull/3153)
- General: Add 'dataclasses' to required python modules [\#3149](https://github.com/pypeclub/OpenPype/pull/3149)
- Hooks: Tweak logging grammar [\#3147](https://github.com/pypeclub/OpenPype/pull/3147)
- Nuke: settings for reformat node in CreateWriteRender node [\#3143](https://github.com/pypeclub/OpenPype/pull/3143)
- Houdini: Add loader for alembic through Alembic Archive node [\#3140](https://github.com/pypeclub/OpenPype/pull/3140)
- Publisher: UI Modifications and fixes [\#3139](https://github.com/pypeclub/OpenPype/pull/3139)
- General: Simplified OP modules/addons import [\#3137](https://github.com/pypeclub/OpenPype/pull/3137)
- Terminal: Tweak coloring of TrayModuleManager logging enabled states [\#3133](https://github.com/pypeclub/OpenPype/pull/3133)
- General: Cleanup some Loader docstrings [\#3131](https://github.com/pypeclub/OpenPype/pull/3131)
- Nuke: render instance with subset name filtered overrides [\#3117](https://github.com/pypeclub/OpenPype/pull/3117)
- Unreal: Layout and Camera update and remove functions reimplemented and improvements [\#3116](https://github.com/pypeclub/OpenPype/pull/3116)
- Settings: Remove environment groups from settings [\#3115](https://github.com/pypeclub/OpenPype/pull/3115)
- TVPaint: Match renderlayer key with other hosts [\#3110](https://github.com/pypeclub/OpenPype/pull/3110)
- Ftrack: AssetVersion status on publish [\#3108](https://github.com/pypeclub/OpenPype/pull/3108)
- Tray publisher: Simple families from settings [\#3105](https://github.com/pypeclub/OpenPype/pull/3105)
- Local Settings UI: Overlay messages on save and reset [\#3104](https://github.com/pypeclub/OpenPype/pull/3104)
- General: Remove repos related logic [\#3087](https://github.com/pypeclub/OpenPype/pull/3087)
- Standalone publisher: add support for bgeo and vdb [\#3080](https://github.com/pypeclub/OpenPype/pull/3080)
- Houdini: Fix FPS + outdated content pop-ups [\#3079](https://github.com/pypeclub/OpenPype/pull/3079)
- General: Add global log verbose arguments [\#3070](https://github.com/pypeclub/OpenPype/pull/3070)
- Flame: extract presets distribution [\#3063](https://github.com/pypeclub/OpenPype/pull/3063)
- Update collect\_render.py [\#3055](https://github.com/pypeclub/OpenPype/pull/3055)
- SiteSync: Added compute\_resource\_sync\_sites to sync\_server\_module [\#2983](https://github.com/pypeclub/OpenPype/pull/2983)
- Maya: Implement Hardware Renderer 2.0 support for Render Products [\#2611](https://github.com/pypeclub/OpenPype/pull/2611)

**🐛 Bug fixes**

- nuke: use framerange issue [\#3254](https://github.com/pypeclub/OpenPype/pull/3254)
- Ftrack: Chunk sizes for queries has minimal condition [\#3244](https://github.com/pypeclub/OpenPype/pull/3244)
- Maya: renderman displays needs to be filtered [\#3242](https://github.com/pypeclub/OpenPype/pull/3242)
- Ftrack: Validate that the user exists on ftrack [\#3237](https://github.com/pypeclub/OpenPype/pull/3237)
- Maya: Fix support for multiple resolutions [\#3236](https://github.com/pypeclub/OpenPype/pull/3236)
- TVPaint: Look for more groups than 12 [\#3228](https://github.com/pypeclub/OpenPype/pull/3228)
- Hiero: debugging frame range and other 3.10 [\#3222](https://github.com/pypeclub/OpenPype/pull/3222)
- Project Manager: Fix persistent editors on project change [\#3218](https://github.com/pypeclub/OpenPype/pull/3218)
- Deadline: instance data overwrite fix [\#3214](https://github.com/pypeclub/OpenPype/pull/3214)
- Ftrack: Push hierarchical attributes action works [\#3210](https://github.com/pypeclub/OpenPype/pull/3210)
- Standalone Publisher: Always create new representation for thumbnail [\#3203](https://github.com/pypeclub/OpenPype/pull/3203)
- Photoshop: skip collector when automatic testing [\#3202](https://github.com/pypeclub/OpenPype/pull/3202)
- Nuke: render/workfile version sync doesn't work on farm [\#3185](https://github.com/pypeclub/OpenPype/pull/3185)
- Ftrack: Review image only if there are no mp4 reviews [\#3183](https://github.com/pypeclub/OpenPype/pull/3183)
- Ftrack: Locations deepcopy issue [\#3177](https://github.com/pypeclub/OpenPype/pull/3177)
- General: Avoid creating multiple thumbnails [\#3176](https://github.com/pypeclub/OpenPype/pull/3176)
- General/Hiero: better clip duration calculation [\#3169](https://github.com/pypeclub/OpenPype/pull/3169)
- General: Oiio conversion for ffmpeg checks for invalid characters [\#3166](https://github.com/pypeclub/OpenPype/pull/3166)
- Fix for attaching render to subset [\#3164](https://github.com/pypeclub/OpenPype/pull/3164)
- Harmony: fixed missing task name in render instance [\#3163](https://github.com/pypeclub/OpenPype/pull/3163)
- Ftrack: Action delete old versions formatting works [\#3152](https://github.com/pypeclub/OpenPype/pull/3152)
- Deadline: fix the output directory [\#3144](https://github.com/pypeclub/OpenPype/pull/3144)
- General: New Session schema [\#3141](https://github.com/pypeclub/OpenPype/pull/3141)
- General: Missing version on headless mode crash properly [\#3136](https://github.com/pypeclub/OpenPype/pull/3136)
- TVPaint: Composite layers in reversed order [\#3135](https://github.com/pypeclub/OpenPype/pull/3135)
- Nuke: fixing default settings for workfile builder loaders [\#3120](https://github.com/pypeclub/OpenPype/pull/3120)
- Nuke: fix anatomy imageio regex default [\#3119](https://github.com/pypeclub/OpenPype/pull/3119)
- General: Python 3 compatibility in queries [\#3112](https://github.com/pypeclub/OpenPype/pull/3112)
- General: TemplateResult can be copied [\#3099](https://github.com/pypeclub/OpenPype/pull/3099)
- General: Collect loaded versions skips not existing representations [\#3095](https://github.com/pypeclub/OpenPype/pull/3095)
- RoyalRender Control Submission - AVALON\_APP\_NAME default [\#3091](https://github.com/pypeclub/OpenPype/pull/3091)
- Ftrack: Update Create Folders action [\#3089](https://github.com/pypeclub/OpenPype/pull/3089)
- Maya: Collect Render fix any render cameras check [\#3088](https://github.com/pypeclub/OpenPype/pull/3088)
- Project Manager: Avoid unnecessary updates of asset documents [\#3083](https://github.com/pypeclub/OpenPype/pull/3083)
- Standalone publisher: Fix plugins install [\#3077](https://github.com/pypeclub/OpenPype/pull/3077)
- General: Extract review sequence is not converted with same names [\#3076](https://github.com/pypeclub/OpenPype/pull/3076)
- Webpublisher: Use variant value [\#3068](https://github.com/pypeclub/OpenPype/pull/3068)
- Nuke: Add aov matching even for remainder and prerender [\#3060](https://github.com/pypeclub/OpenPype/pull/3060)
- Fix support for Renderman in Maya [\#3006](https://github.com/pypeclub/OpenPype/pull/3006)

**🔀 Refactored code**

- Avalon repo removed from Jobs workflow [\#3193](https://github.com/pypeclub/OpenPype/pull/3193)
- General: Remove remaining imports from avalon [\#3130](https://github.com/pypeclub/OpenPype/pull/3130)
- General: Move mongo db logic and remove avalon repository [\#3066](https://github.com/pypeclub/OpenPype/pull/3066)
- General: Move host install [\#3009](https://github.com/pypeclub/OpenPype/pull/3009)

**Merged pull requests:**

- Harmony: message length in 21.1 [\#3257](https://github.com/pypeclub/OpenPype/pull/3257)
- Harmony: 21.1 fix [\#3249](https://github.com/pypeclub/OpenPype/pull/3249)
- Maya: added jpg to filter for Image Plane Loader [\#3223](https://github.com/pypeclub/OpenPype/pull/3223)
- Webpublisher: replace space by underscore in subset names [\#3160](https://github.com/pypeclub/OpenPype/pull/3160)
- StandalonePublisher: removed Extract Background plugins [\#3093](https://github.com/pypeclub/OpenPype/pull/3093)
- Nuke: added suspend\_publish knob [\#3078](https://github.com/pypeclub/OpenPype/pull/3078)
- Bump async from 2.6.3 to 2.6.4 in /website [\#3065](https://github.com/pypeclub/OpenPype/pull/3065)
- SiteSync: Download all workfile inputs [\#2966](https://github.com/pypeclub/OpenPype/pull/2966)
- Photoshop: New Publisher [\#2933](https://github.com/pypeclub/OpenPype/pull/2933)
- Bump pillow from 9.0.0 to 9.0.1 [\#2880](https://github.com/pypeclub/OpenPype/pull/2880)
- AfterEffects: Allow configuration of default variant via Settings [\#2856](https://github.com/pypeclub/OpenPype/pull/2856)

## [3.9.8](https://github.com/pypeclub/OpenPype/tree/3.9.8) (2022-05-19)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.9.7...3.9.8)

## [3.9.7](https://github.com/pypeclub/OpenPype/tree/3.9.7) (2022-05-11)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.9.6...3.9.7)

## [3.9.6](https://github.com/pypeclub/OpenPype/tree/3.9.6) (2022-05-03)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.9.5...3.9.6)

## [3.9.5](https://github.com/pypeclub/OpenPype/tree/3.9.5) (2022-04-25)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.9.4...3.9.5)

## [3.9.4](https://github.com/pypeclub/OpenPype/tree/3.9.4) (2022-04-15)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.9.3...3.9.4)

### 📖 Documentation

- Documentation: more info about Tasks [\#3062](https://github.com/pypeclub/OpenPype/pull/3062)
- Documentation: Python requirements to 3.7.9 [\#3035](https://github.com/pypeclub/OpenPype/pull/3035)
- Website Docs: Remove unused pages [\#2974](https://github.com/pypeclub/OpenPype/pull/2974)

**🆕 New features**

- General: Local overrides for environment variables [\#3045](https://github.com/pypeclub/OpenPype/pull/3045)
- Flame: Flare integration preparation [\#2928](https://github.com/pypeclub/OpenPype/pull/2928)

**🚀 Enhancements**

- TVPaint: Added init file for worker to triggers missing sound file dialog [\#3053](https://github.com/pypeclub/OpenPype/pull/3053)
- Ftrack: Custom attributes can be filled in slate values [\#3036](https://github.com/pypeclub/OpenPype/pull/3036)
- Resolve environment variable in google drive credential path  [\#3008](https://github.com/pypeclub/OpenPype/pull/3008)

**🐛 Bug fixes**

- GitHub: Updated push-protected action in github workflow [\#3064](https://github.com/pypeclub/OpenPype/pull/3064)
- Nuke: Typos in imports from Nuke implementation [\#3061](https://github.com/pypeclub/OpenPype/pull/3061)
- Hotfix: fixing deadline job publishing [\#3059](https://github.com/pypeclub/OpenPype/pull/3059)
- General: Extract Review handle invalid characters for ffmpeg [\#3050](https://github.com/pypeclub/OpenPype/pull/3050)
- Slate Review: Support to keep format on slate concatenation [\#3049](https://github.com/pypeclub/OpenPype/pull/3049)
- Webpublisher: fix processing of workfile [\#3048](https://github.com/pypeclub/OpenPype/pull/3048)
- Ftrack: Integrate ftrack api fix [\#3044](https://github.com/pypeclub/OpenPype/pull/3044)
- Webpublisher - removed wrong hardcoded family [\#3043](https://github.com/pypeclub/OpenPype/pull/3043)
- LibraryLoader: Use current project for asset query in families filter [\#3042](https://github.com/pypeclub/OpenPype/pull/3042)
- SiteSync: Providers ignore that site is disabled [\#3041](https://github.com/pypeclub/OpenPype/pull/3041)
- Unreal: Creator import fixes [\#3040](https://github.com/pypeclub/OpenPype/pull/3040)
- SiteSync: fix transitive alternate sites, fix dropdown in Local Settings [\#3018](https://github.com/pypeclub/OpenPype/pull/3018)
- Maya: invalid review flag on rendered AOVs [\#2915](https://github.com/pypeclub/OpenPype/pull/2915)

**Merged pull requests:**

- Deadline: reworked pools assignment [\#3051](https://github.com/pypeclub/OpenPype/pull/3051)
- Houdini: Avoid ImportError on `hdefereval` when Houdini runs without UI [\#2987](https://github.com/pypeclub/OpenPype/pull/2987)

## [3.9.3](https://github.com/pypeclub/OpenPype/tree/3.9.3) (2022-04-07)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.9.2...3.9.3)

### 📖 Documentation

- Documentation: Added mention of adding My Drive as a root [\#2999](https://github.com/pypeclub/OpenPype/pull/2999)
- Website Docs: Manager Ftrack fix broken links [\#2979](https://github.com/pypeclub/OpenPype/pull/2979)
- Docs: Added MongoDB requirements [\#2951](https://github.com/pypeclub/OpenPype/pull/2951)
- Documentation: New publisher develop docs [\#2896](https://github.com/pypeclub/OpenPype/pull/2896)

**🆕 New features**

- Ftrack: Add description integrator [\#3027](https://github.com/pypeclub/OpenPype/pull/3027)
- nuke: bypass baking [\#2992](https://github.com/pypeclub/OpenPype/pull/2992)
- Publishing textures for Unreal [\#2988](https://github.com/pypeclub/OpenPype/pull/2988)
- Maya to Unreal: Static and Skeletal Meshes [\#2978](https://github.com/pypeclub/OpenPype/pull/2978)
- Multiverse: Initial Support [\#2908](https://github.com/pypeclub/OpenPype/pull/2908)

**🚀 Enhancements**

- General: default workfile subset name for workfile [\#3011](https://github.com/pypeclub/OpenPype/pull/3011)
- Ftrack: Add more options for note text of integrate ftrack note [\#3025](https://github.com/pypeclub/OpenPype/pull/3025)
- Console Interpreter: Changed how console splitter size are reused on show [\#3016](https://github.com/pypeclub/OpenPype/pull/3016)
- Deadline: Use more suitable name for sequence review logic [\#3015](https://github.com/pypeclub/OpenPype/pull/3015)
- Nuke: add concurrency attr to deadline job [\#3005](https://github.com/pypeclub/OpenPype/pull/3005)
- Photoshop: create image without instance [\#3001](https://github.com/pypeclub/OpenPype/pull/3001)
- TVPaint: Render scene family [\#3000](https://github.com/pypeclub/OpenPype/pull/3000)
- Deadline: priority configurable in Maya jobs [\#2995](https://github.com/pypeclub/OpenPype/pull/2995)
- Nuke: ReviewDataMov Read RAW attribute [\#2985](https://github.com/pypeclub/OpenPype/pull/2985)
- General: `METADATA_KEYS` constant as `frozenset` for optimal immutable lookup [\#2980](https://github.com/pypeclub/OpenPype/pull/2980)
- General: Tools with host filters [\#2975](https://github.com/pypeclub/OpenPype/pull/2975)
- Hero versions: Use custom templates [\#2967](https://github.com/pypeclub/OpenPype/pull/2967)
- Slack: Added configurable maximum file size of review upload to Slack [\#2945](https://github.com/pypeclub/OpenPype/pull/2945)
- NewPublisher: Prepared implementation of optional pyblish plugin [\#2943](https://github.com/pypeclub/OpenPype/pull/2943)
- TVPaint: Extractor to convert PNG into EXR [\#2942](https://github.com/pypeclub/OpenPype/pull/2942)
- Workfiles tool: Save as published workfiles [\#2937](https://github.com/pypeclub/OpenPype/pull/2937)
- Workfiles: Open published workfiles [\#2925](https://github.com/pypeclub/OpenPype/pull/2925)
- General: Default modules loaded dynamically [\#2923](https://github.com/pypeclub/OpenPype/pull/2923)
- CI: change the version bump logic [\#2919](https://github.com/pypeclub/OpenPype/pull/2919)
- Deadline: Add headless argument [\#2916](https://github.com/pypeclub/OpenPype/pull/2916)
- Nuke: Add no-audio Tag [\#2911](https://github.com/pypeclub/OpenPype/pull/2911)
- Ftrack: Fill workfile in custom attribute [\#2906](https://github.com/pypeclub/OpenPype/pull/2906)
- Nuke: improving readability [\#2903](https://github.com/pypeclub/OpenPype/pull/2903)
- Settings UI: Add simple tooltips for settings entities [\#2901](https://github.com/pypeclub/OpenPype/pull/2901)

**🐛 Bug fixes**

- General: Fix validate asset docs plug-in filename and class name [\#3029](https://github.com/pypeclub/OpenPype/pull/3029)
- Deadline: Fixed default value of use sequence for review [\#3033](https://github.com/pypeclub/OpenPype/pull/3033)
- Settings UI: Version column can be extended so version are visible [\#3032](https://github.com/pypeclub/OpenPype/pull/3032)
- General: Fix import after movements [\#3028](https://github.com/pypeclub/OpenPype/pull/3028)
- Harmony: Added creating subset name for workfile from template [\#3024](https://github.com/pypeclub/OpenPype/pull/3024)
- AfterEffects: Added creating subset name for workfile from template [\#3023](https://github.com/pypeclub/OpenPype/pull/3023)
- General: Add example addons to ignored [\#3022](https://github.com/pypeclub/OpenPype/pull/3022)
- Maya: Remove missing import [\#3017](https://github.com/pypeclub/OpenPype/pull/3017)
- Ftrack: multiple  reviewable componets [\#3012](https://github.com/pypeclub/OpenPype/pull/3012)
- Tray publisher: Fixes after code movement [\#3010](https://github.com/pypeclub/OpenPype/pull/3010)
- Hosts: Remove path existence checks in 'add\_implementation\_envs' [\#3004](https://github.com/pypeclub/OpenPype/pull/3004)
- Nuke: fixing unicode type detection in effect loaders [\#3002](https://github.com/pypeclub/OpenPype/pull/3002)
- Fix - remove doubled dot in workfile created from template [\#2998](https://github.com/pypeclub/OpenPype/pull/2998)
- Nuke: removing redundant Ftrack asset when farm publishing [\#2996](https://github.com/pypeclub/OpenPype/pull/2996)
- PS: fix renaming subset incorrectly in PS [\#2991](https://github.com/pypeclub/OpenPype/pull/2991)
- Fix: Disable setuptools auto discovery [\#2990](https://github.com/pypeclub/OpenPype/pull/2990)
- AEL: fix opening existing workfile if no scene opened [\#2989](https://github.com/pypeclub/OpenPype/pull/2989)
- Maya: Don't do hardlinks on windows for look publishing [\#2986](https://github.com/pypeclub/OpenPype/pull/2986)
- Settings UI: Fix version completer on linux [\#2981](https://github.com/pypeclub/OpenPype/pull/2981)
- Photoshop: Fix creation of subset names in PS review and workfile [\#2969](https://github.com/pypeclub/OpenPype/pull/2969)
- Slack: Added default for review\_upload\_limit for Slack [\#2965](https://github.com/pypeclub/OpenPype/pull/2965)
- General: OIIO conversion for ffmeg can handle sequences [\#2958](https://github.com/pypeclub/OpenPype/pull/2958)
- Settings: Conditional dictionary avoid invalid logs [\#2956](https://github.com/pypeclub/OpenPype/pull/2956)
- General: Smaller fixes and typos [\#2950](https://github.com/pypeclub/OpenPype/pull/2950)
- LogViewer: Don't refresh on initialization [\#2949](https://github.com/pypeclub/OpenPype/pull/2949)
- nuke: python3 compatibility issue with `iteritems` [\#2948](https://github.com/pypeclub/OpenPype/pull/2948)
- General: anatomy data with correct task short key [\#2947](https://github.com/pypeclub/OpenPype/pull/2947)
- SceneInventory: Fix imports in UI [\#2944](https://github.com/pypeclub/OpenPype/pull/2944)
- Slack: add generic exception [\#2941](https://github.com/pypeclub/OpenPype/pull/2941)
- General: Python specific vendor paths on env injection [\#2939](https://github.com/pypeclub/OpenPype/pull/2939)
- General: More fail safe delete old versions [\#2936](https://github.com/pypeclub/OpenPype/pull/2936)
- Settings UI: Collapsed of collapsible wrapper works as expected [\#2934](https://github.com/pypeclub/OpenPype/pull/2934)
- Maya: Do not pass `set` to maya commands \(fixes support for older maya versions\) [\#2932](https://github.com/pypeclub/OpenPype/pull/2932)
- General: Don't print log record on OSError [\#2926](https://github.com/pypeclub/OpenPype/pull/2926)
- Hiero: Fix import of 'register\_event\_callback' [\#2924](https://github.com/pypeclub/OpenPype/pull/2924)
- Flame: centos related debugging [\#2922](https://github.com/pypeclub/OpenPype/pull/2922)
- Ftrack: Missing Ftrack id after editorial publish [\#2905](https://github.com/pypeclub/OpenPype/pull/2905)
- AfterEffects: Fix rendering for single frame in DL [\#2875](https://github.com/pypeclub/OpenPype/pull/2875)

**🔀 Refactored code**

- General: Move plugins register and discover [\#2935](https://github.com/pypeclub/OpenPype/pull/2935)
- General: Move Attribute Definitions from pipeline [\#2931](https://github.com/pypeclub/OpenPype/pull/2931)
- General: Removed silo references and terminal splash [\#2927](https://github.com/pypeclub/OpenPype/pull/2927)
- General: Move pipeline constants to OpenPype [\#2918](https://github.com/pypeclub/OpenPype/pull/2918)
- General: Move formatting and workfile functions [\#2914](https://github.com/pypeclub/OpenPype/pull/2914)
- General: Move remaining plugins from avalon [\#2912](https://github.com/pypeclub/OpenPype/pull/2912)

**Merged pull requests:**

- Maya: Allow to select invalid camera contents if no cameras found [\#3030](https://github.com/pypeclub/OpenPype/pull/3030)
- Bump paramiko from 2.9.2 to 2.10.1 [\#2973](https://github.com/pypeclub/OpenPype/pull/2973)
- Bump minimist from 1.2.5 to 1.2.6 in /website [\#2954](https://github.com/pypeclub/OpenPype/pull/2954)
- Bump node-forge from 1.2.1 to 1.3.0 in /website [\#2953](https://github.com/pypeclub/OpenPype/pull/2953)
- Maya - added transparency into review creator [\#2952](https://github.com/pypeclub/OpenPype/pull/2952)

## [3.9.2](https://github.com/pypeclub/OpenPype/tree/3.9.2) (2022-04-04)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.9.1...3.9.2)

## [3.9.1](https://github.com/pypeclub/OpenPype/tree/3.9.1) (2022-03-18)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.9.0...3.9.1)

**🚀 Enhancements**

- General: Change how OPENPYPE\_DEBUG value is handled [\#2907](https://github.com/pypeclub/OpenPype/pull/2907)
- nuke: imageio adding ocio config version 1.2 [\#2897](https://github.com/pypeclub/OpenPype/pull/2897)
- Flame: support for comment with xml attribute overrides [\#2892](https://github.com/pypeclub/OpenPype/pull/2892)
- Nuke: ExtractReviewSlate can handle more codes and profiles [\#2879](https://github.com/pypeclub/OpenPype/pull/2879)
- Flame: sequence used for reference video [\#2869](https://github.com/pypeclub/OpenPype/pull/2869)

**🐛 Bug fixes**

- General: Fix use of Anatomy roots [\#2904](https://github.com/pypeclub/OpenPype/pull/2904)
- Fixing gap detection in extract review [\#2902](https://github.com/pypeclub/OpenPype/pull/2902)
- Pyblish Pype - ensure current state is correct when entering new group order [\#2899](https://github.com/pypeclub/OpenPype/pull/2899)
- SceneInventory: Fix import of load function [\#2894](https://github.com/pypeclub/OpenPype/pull/2894)
- Harmony - fixed creator issue [\#2891](https://github.com/pypeclub/OpenPype/pull/2891)
- General: Remove forgotten use of avalon Creator [\#2885](https://github.com/pypeclub/OpenPype/pull/2885)
- General: Avoid circular import [\#2884](https://github.com/pypeclub/OpenPype/pull/2884)
- Fixes for attaching loaded containers \(\#2837\) [\#2874](https://github.com/pypeclub/OpenPype/pull/2874)
- Maya: Deformer node ids validation plugin [\#2826](https://github.com/pypeclub/OpenPype/pull/2826)
- Flame Babypublisher optimalization [\#2806](https://github.com/pypeclub/OpenPype/pull/2806)
- hotfix: OIIO tool path - add extension on windows [\#2618](https://github.com/pypeclub/OpenPype/pull/2618)

**🔀 Refactored code**

- General: Reduce style usage to OpenPype repository [\#2889](https://github.com/pypeclub/OpenPype/pull/2889)
- General: Move loader logic from avalon to openpype [\#2886](https://github.com/pypeclub/OpenPype/pull/2886)

## [3.9.0](https://github.com/pypeclub/OpenPype/tree/3.9.0) (2022-03-14)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.8.2...3.9.0)

**Deprecated:**

- Houdini: Remove unused code [\#2779](https://github.com/pypeclub/OpenPype/pull/2779)
- Loader: Remove default family states for hosts from code [\#2706](https://github.com/pypeclub/OpenPype/pull/2706)
- AssetCreator: Remove the tool [\#2845](https://github.com/pypeclub/OpenPype/pull/2845)

### 📖 Documentation

- Documentation: fixed broken links [\#2799](https://github.com/pypeclub/OpenPype/pull/2799)
- Documentation: broken link fix [\#2785](https://github.com/pypeclub/OpenPype/pull/2785)
- Documentation: link fixes [\#2772](https://github.com/pypeclub/OpenPype/pull/2772)
- Update docusaurus to latest version [\#2760](https://github.com/pypeclub/OpenPype/pull/2760)
- Various testing updates [\#2726](https://github.com/pypeclub/OpenPype/pull/2726)
- documentation: add example to `repack-version` command [\#2669](https://github.com/pypeclub/OpenPype/pull/2669)
- Update docusaurus [\#2639](https://github.com/pypeclub/OpenPype/pull/2639)
- Documentation: Fixed relative links [\#2621](https://github.com/pypeclub/OpenPype/pull/2621)
- Documentation: Change Photoshop & AfterEffects plugin path [\#2878](https://github.com/pypeclub/OpenPype/pull/2878)

**🆕 New features**

- Flame: loading clips to reels [\#2622](https://github.com/pypeclub/OpenPype/pull/2622)
- General: Store settings by OpenPype version [\#2570](https://github.com/pypeclub/OpenPype/pull/2570)

**🚀 Enhancements**

- New: Validation exceptions [\#2841](https://github.com/pypeclub/OpenPype/pull/2841)
- General: Set context environments for non host applications [\#2803](https://github.com/pypeclub/OpenPype/pull/2803)
- Houdini: Remove duplicate ValidateOutputNode plug-in [\#2780](https://github.com/pypeclub/OpenPype/pull/2780)
- Tray publisher: New Tray Publisher host \(beta\) [\#2778](https://github.com/pypeclub/OpenPype/pull/2778)
- Slack: Added regex for filtering on subset names [\#2775](https://github.com/pypeclub/OpenPype/pull/2775)
- Houdini: Implement Reset Frame Range [\#2770](https://github.com/pypeclub/OpenPype/pull/2770)
- Pyblish Pype: Remove redundant new line in installed fonts printing [\#2758](https://github.com/pypeclub/OpenPype/pull/2758)
- Flame: use Shot Name on segment for asset name [\#2751](https://github.com/pypeclub/OpenPype/pull/2751)
- Flame: adding validator source clip [\#2746](https://github.com/pypeclub/OpenPype/pull/2746)
- Work Files: Preserve subversion comment of current filename by default [\#2734](https://github.com/pypeclub/OpenPype/pull/2734)
- Maya: set Deadline job/batch name to original source workfile name instead of published workfile [\#2733](https://github.com/pypeclub/OpenPype/pull/2733)
- Ftrack: Disable ftrack module by default [\#2732](https://github.com/pypeclub/OpenPype/pull/2732)
- Project Manager: Disable add task, add asset and save button when not in a project [\#2727](https://github.com/pypeclub/OpenPype/pull/2727)
- dropbox handle big file [\#2718](https://github.com/pypeclub/OpenPype/pull/2718)
- Fusion Move PR: Minor tweaks to Fusion integration [\#2716](https://github.com/pypeclub/OpenPype/pull/2716)
- RoyalRender: Minor enhancements [\#2700](https://github.com/pypeclub/OpenPype/pull/2700)
- Nuke: prerender with review knob [\#2691](https://github.com/pypeclub/OpenPype/pull/2691)
- Maya configurable unit validator [\#2680](https://github.com/pypeclub/OpenPype/pull/2680)
- General: Add settings for CleanUpFarm and disable the plugin by default [\#2679](https://github.com/pypeclub/OpenPype/pull/2679)
- Project Manager: Only allow scroll wheel edits when spinbox is active [\#2678](https://github.com/pypeclub/OpenPype/pull/2678)
- Ftrack: Sync description to assets [\#2670](https://github.com/pypeclub/OpenPype/pull/2670)
- Houdini: Moved to OpenPype [\#2658](https://github.com/pypeclub/OpenPype/pull/2658)
- Maya: Move implementation to OpenPype [\#2649](https://github.com/pypeclub/OpenPype/pull/2649)
- General: FFmpeg conversion also check attribute string length [\#2635](https://github.com/pypeclub/OpenPype/pull/2635)
- Houdini: Load Arnold .ass procedurals into Houdini [\#2606](https://github.com/pypeclub/OpenPype/pull/2606)
- Deadline: Simplify GlobalJobPreLoad logic [\#2605](https://github.com/pypeclub/OpenPype/pull/2605)
- Houdini: Implement Arnold .ass standin extraction from Houdini \(also support .ass.gz\) [\#2603](https://github.com/pypeclub/OpenPype/pull/2603)
- New Publisher: New features and preparations for new standalone publisher [\#2556](https://github.com/pypeclub/OpenPype/pull/2556)
- Fix Maya 2022 Python 3 compatibility [\#2445](https://github.com/pypeclub/OpenPype/pull/2445)
- TVPaint: Use new publisher exceptions in validators [\#2435](https://github.com/pypeclub/OpenPype/pull/2435)
- Harmony: Added new style validations for New Publisher [\#2434](https://github.com/pypeclub/OpenPype/pull/2434)
- Aftereffects: New style validations for New publisher [\#2430](https://github.com/pypeclub/OpenPype/pull/2430)
- Farm publishing: New cleanup plugin for Maya renders on farm [\#2390](https://github.com/pypeclub/OpenPype/pull/2390)
- General: Subset name filtering in ExtractReview outpus [\#2872](https://github.com/pypeclub/OpenPype/pull/2872)
- NewPublisher: Descriptions and Icons in creator dialog [\#2867](https://github.com/pypeclub/OpenPype/pull/2867)
- NewPublisher: Changing task on publishing instance [\#2863](https://github.com/pypeclub/OpenPype/pull/2863)
- TrayPublisher: Choose project widget is more clear [\#2859](https://github.com/pypeclub/OpenPype/pull/2859)
- Maya: add loaded containers to published instance [\#2837](https://github.com/pypeclub/OpenPype/pull/2837)
- Ftrack: Can sync fps as string [\#2836](https://github.com/pypeclub/OpenPype/pull/2836)
- General: Custom function for find executable [\#2822](https://github.com/pypeclub/OpenPype/pull/2822)
- General: Color dialog UI fixes [\#2817](https://github.com/pypeclub/OpenPype/pull/2817)
- global: letter box calculated on output as last process [\#2812](https://github.com/pypeclub/OpenPype/pull/2812)
- Nuke: adding Reformat to baking mov plugin  [\#2811](https://github.com/pypeclub/OpenPype/pull/2811)
- Manager: Update all to latest button [\#2805](https://github.com/pypeclub/OpenPype/pull/2805)
- Houdini: Move Houdini Save Current File to beginning of ExtractorOrder [\#2747](https://github.com/pypeclub/OpenPype/pull/2747)
- Global: adding studio name/code to anatomy template formatting data [\#2630](https://github.com/pypeclub/OpenPype/pull/2630)

**🐛 Bug fixes**

- Settings UI: Search case sensitivity [\#2810](https://github.com/pypeclub/OpenPype/pull/2810)
- resolve: fixing fusion module loading [\#2802](https://github.com/pypeclub/OpenPype/pull/2802)
- Ftrack: Unset task ids from asset versions before tasks are removed [\#2800](https://github.com/pypeclub/OpenPype/pull/2800)
- Slack: fail gracefully if slack exception [\#2798](https://github.com/pypeclub/OpenPype/pull/2798)
- Flame: Fix version string in default settings [\#2783](https://github.com/pypeclub/OpenPype/pull/2783)
- After Effects: Fix typo in name `afftereffects` -\> `aftereffects` [\#2768](https://github.com/pypeclub/OpenPype/pull/2768)
- Houdini: Fix open last workfile [\#2767](https://github.com/pypeclub/OpenPype/pull/2767)
- Avoid renaming udim indexes [\#2765](https://github.com/pypeclub/OpenPype/pull/2765)
- Maya: Fix `unique_namespace` when in an namespace that is empty [\#2759](https://github.com/pypeclub/OpenPype/pull/2759)
- Loader UI: Fix right click in representation widget [\#2757](https://github.com/pypeclub/OpenPype/pull/2757)
- Harmony: Rendering in Deadline didn't work in other machines than submitter [\#2754](https://github.com/pypeclub/OpenPype/pull/2754)
- Aftereffects 2022 and Deadline [\#2748](https://github.com/pypeclub/OpenPype/pull/2748)
- Flame: bunch of bugs [\#2745](https://github.com/pypeclub/OpenPype/pull/2745)
- Maya: Save current scene on workfile publish [\#2744](https://github.com/pypeclub/OpenPype/pull/2744)
- Version Up: Preserve parts of filename after version number \(like subversion\) on version\_up [\#2741](https://github.com/pypeclub/OpenPype/pull/2741)
- Loader UI: Multiple asset selection and underline colors fixed [\#2731](https://github.com/pypeclub/OpenPype/pull/2731)
- General: Fix loading of unused chars in xml format [\#2729](https://github.com/pypeclub/OpenPype/pull/2729)
- TVPaint: Set objectName with members [\#2725](https://github.com/pypeclub/OpenPype/pull/2725)
- General: Don't use 'objectName' from loaded references [\#2715](https://github.com/pypeclub/OpenPype/pull/2715)
- Settings: Studio Project anatomy is queried using right keys [\#2711](https://github.com/pypeclub/OpenPype/pull/2711)
- Local Settings: Additional applications don't break UI [\#2710](https://github.com/pypeclub/OpenPype/pull/2710)
- Maya: Remove some unused code [\#2709](https://github.com/pypeclub/OpenPype/pull/2709)
- Houdini: Fix refactor of Houdini host move for CreateArnoldAss [\#2704](https://github.com/pypeclub/OpenPype/pull/2704)
- LookAssigner: Fix imports after moving code to OpenPype repository [\#2701](https://github.com/pypeclub/OpenPype/pull/2701)
- Multiple hosts: unify menu style across hosts [\#2693](https://github.com/pypeclub/OpenPype/pull/2693)
- Maya Redshift fixes [\#2692](https://github.com/pypeclub/OpenPype/pull/2692)
- Maya: fix fps validation popup [\#2685](https://github.com/pypeclub/OpenPype/pull/2685)
- Houdini Explicitly collect correct frame name even in case of single frame render when `frameStart` is provided [\#2676](https://github.com/pypeclub/OpenPype/pull/2676)
- hiero: fix effect collector name and order [\#2673](https://github.com/pypeclub/OpenPype/pull/2673)
- Maya: Fix menu callbacks [\#2671](https://github.com/pypeclub/OpenPype/pull/2671)
- hiero: removing obsolete unsupported plugin [\#2667](https://github.com/pypeclub/OpenPype/pull/2667)
- Launcher: Fix access to 'data' attribute on actions [\#2659](https://github.com/pypeclub/OpenPype/pull/2659)
- Maya `vrscene` loader fixes [\#2633](https://github.com/pypeclub/OpenPype/pull/2633)
- Houdini: fix usd family in loader and integrators [\#2631](https://github.com/pypeclub/OpenPype/pull/2631)
- Maya: Add only reference node to look family container like with other families [\#2508](https://github.com/pypeclub/OpenPype/pull/2508)
- General: Missing time function [\#2877](https://github.com/pypeclub/OpenPype/pull/2877)
- Deadline: Fix plugin name for tile assemble [\#2868](https://github.com/pypeclub/OpenPype/pull/2868)
- Nuke: gizmo precollect fix [\#2866](https://github.com/pypeclub/OpenPype/pull/2866)
- General: Fix hardlink for windows [\#2864](https://github.com/pypeclub/OpenPype/pull/2864)
- General: ffmpeg was crashing on slate merge [\#2860](https://github.com/pypeclub/OpenPype/pull/2860)
- WebPublisher: Video file was published with one too many frame [\#2858](https://github.com/pypeclub/OpenPype/pull/2858)
- New Publisher: Error dialog got right styles [\#2857](https://github.com/pypeclub/OpenPype/pull/2857)
- General: Fix getattr clalback on dynamic modules [\#2855](https://github.com/pypeclub/OpenPype/pull/2855)
- Nuke: slate resolution to input video resolution [\#2853](https://github.com/pypeclub/OpenPype/pull/2853)
- WebPublisher: Fix username stored in DB [\#2852](https://github.com/pypeclub/OpenPype/pull/2852)
- WebPublisher: Fix wrong number of frames for video file [\#2851](https://github.com/pypeclub/OpenPype/pull/2851)
- Nuke: Fix family test in validate\_write\_legacy to work with stillImage [\#2847](https://github.com/pypeclub/OpenPype/pull/2847)
- Nuke: fix multiple baking profile farm publishing [\#2842](https://github.com/pypeclub/OpenPype/pull/2842)
- Blender: Fixed parameters for FBX export of the camera [\#2840](https://github.com/pypeclub/OpenPype/pull/2840)
- Maya: Stop creation of reviews for Cryptomattes [\#2832](https://github.com/pypeclub/OpenPype/pull/2832)
- Deadline: Remove recreated event [\#2828](https://github.com/pypeclub/OpenPype/pull/2828)
- Deadline: Added missing events folder [\#2827](https://github.com/pypeclub/OpenPype/pull/2827)
- Settings: Missing document with OP versions may break start of OpenPype [\#2825](https://github.com/pypeclub/OpenPype/pull/2825)
- Deadline: more detailed temp file name for environment json [\#2824](https://github.com/pypeclub/OpenPype/pull/2824)
- General: Host name was formed from obsolete code [\#2821](https://github.com/pypeclub/OpenPype/pull/2821)
- Settings UI: Fix "Apply from" action [\#2820](https://github.com/pypeclub/OpenPype/pull/2820)
- Ftrack: Job killer with missing user [\#2819](https://github.com/pypeclub/OpenPype/pull/2819)
- Nuke: Use AVALON\_APP to get value for "app" key [\#2818](https://github.com/pypeclub/OpenPype/pull/2818)
- StandalonePublisher: use dynamic groups in subset names [\#2816](https://github.com/pypeclub/OpenPype/pull/2816)

**🔀 Refactored code**

- Ftrack: Moved module one hierarchy level higher [\#2792](https://github.com/pypeclub/OpenPype/pull/2792)
- SyncServer: Moved module one hierarchy level higher [\#2791](https://github.com/pypeclub/OpenPype/pull/2791)
- Royal render: Move module one hierarchy level higher [\#2790](https://github.com/pypeclub/OpenPype/pull/2790)
- Deadline: Move module one hierarchy level higher [\#2789](https://github.com/pypeclub/OpenPype/pull/2789)
- Refactor: move webserver tool to openpype [\#2876](https://github.com/pypeclub/OpenPype/pull/2876)
- General: Move create logic from avalon to OpenPype [\#2854](https://github.com/pypeclub/OpenPype/pull/2854)
- General: Add vendors from avalon [\#2848](https://github.com/pypeclub/OpenPype/pull/2848)
- General: Basic event system [\#2846](https://github.com/pypeclub/OpenPype/pull/2846)
- General: Move change context functions [\#2839](https://github.com/pypeclub/OpenPype/pull/2839)
- Tools: Don't use avalon tools code [\#2829](https://github.com/pypeclub/OpenPype/pull/2829)
- Move Unreal Implementation to OpenPype [\#2823](https://github.com/pypeclub/OpenPype/pull/2823)
- General: Extract template formatting from anatomy [\#2766](https://github.com/pypeclub/OpenPype/pull/2766)

**Merged pull requests:**

- Fusion: Moved implementation into OpenPype [\#2713](https://github.com/pypeclub/OpenPype/pull/2713)
- TVPaint: Plugin build without dependencies [\#2705](https://github.com/pypeclub/OpenPype/pull/2705)
- Webpublisher: Photoshop create a beauty png [\#2689](https://github.com/pypeclub/OpenPype/pull/2689)
- Ftrack: Hierarchical attributes are queried properly [\#2682](https://github.com/pypeclub/OpenPype/pull/2682)
- Maya: Add Validate Frame Range settings [\#2661](https://github.com/pypeclub/OpenPype/pull/2661)
- Harmony: move to Openpype [\#2657](https://github.com/pypeclub/OpenPype/pull/2657)
- Maya: cleanup duplicate rendersetup code [\#2642](https://github.com/pypeclub/OpenPype/pull/2642)
- Deadline: Be able to pass Mongo url to job [\#2616](https://github.com/pypeclub/OpenPype/pull/2616)

## [3.8.2](https://github.com/pypeclub/OpenPype/tree/3.8.2) (2022-02-07)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.8.1...3.8.2)

### 📖 Documentation

- Cosmetics: Fix common typos in openpype/website [\#2617](https://github.com/pypeclub/OpenPype/pull/2617)

**🚀 Enhancements**

- TVPaint: Image loaders also work on review family [\#2638](https://github.com/pypeclub/OpenPype/pull/2638)
- General: Project backup tools [\#2629](https://github.com/pypeclub/OpenPype/pull/2629)
- nuke: adding clear button to write nodes [\#2627](https://github.com/pypeclub/OpenPype/pull/2627)
- Ftrack: Family to Asset type mapping is in settings [\#2602](https://github.com/pypeclub/OpenPype/pull/2602)
- Nuke: load color space from representation data [\#2576](https://github.com/pypeclub/OpenPype/pull/2576)

**🐛 Bug fixes**

- Fix pulling of cx\_freeze 6.10 [\#2628](https://github.com/pypeclub/OpenPype/pull/2628)
- Global: fix broken otio review extractor [\#2590](https://github.com/pypeclub/OpenPype/pull/2590)

**Merged pull requests:**

- WebPublisher: fix instance duplicates [\#2641](https://github.com/pypeclub/OpenPype/pull/2641)
- Fix - safer pulling of task name for webpublishing from PS [\#2613](https://github.com/pypeclub/OpenPype/pull/2613)

## [3.8.1](https://github.com/pypeclub/OpenPype/tree/3.8.1) (2022-02-01)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.8.0...3.8.1)

**🚀 Enhancements**

- Webpublisher: Thumbnail extractor [\#2600](https://github.com/pypeclub/OpenPype/pull/2600)
- Loader: Allow to toggle default family filters between "include" or "exclude" filtering [\#2541](https://github.com/pypeclub/OpenPype/pull/2541)
- Launcher: Added context menu to to skip opening last workfile [\#2536](https://github.com/pypeclub/OpenPype/pull/2536)
- Unreal: JSON Layout Loading support [\#2066](https://github.com/pypeclub/OpenPype/pull/2066)

**🐛 Bug fixes**

- Release/3.8.0 [\#2619](https://github.com/pypeclub/OpenPype/pull/2619)
- Settings: Enum does not store empty string if has single item to select [\#2615](https://github.com/pypeclub/OpenPype/pull/2615)
- switch distutils to sysconfig for `get_platform()` [\#2594](https://github.com/pypeclub/OpenPype/pull/2594)
- Fix poetry index and speedcopy update [\#2589](https://github.com/pypeclub/OpenPype/pull/2589)
- Webpublisher: Fix - subset names from processed .psd used wrong value for task [\#2586](https://github.com/pypeclub/OpenPype/pull/2586)
- `vrscene` creator Deadline webservice URL handling [\#2580](https://github.com/pypeclub/OpenPype/pull/2580)
- global: track name was failing if duplicated root word in name [\#2568](https://github.com/pypeclub/OpenPype/pull/2568)
- Validate Maya Rig produces no cycle errors [\#2484](https://github.com/pypeclub/OpenPype/pull/2484)

**Merged pull requests:**

- Bump pillow from 8.4.0 to 9.0.0 [\#2595](https://github.com/pypeclub/OpenPype/pull/2595)
- Webpublisher: Skip version collect [\#2591](https://github.com/pypeclub/OpenPype/pull/2591)
- build\(deps\): bump pillow from 8.4.0 to 9.0.0 [\#2523](https://github.com/pypeclub/OpenPype/pull/2523)

## [3.8.0](https://github.com/pypeclub/OpenPype/tree/3.8.0) (2022-01-24)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.7.0...3.8.0)

### 📖 Documentation

- Variable in docs renamed to proper name [\#2546](https://github.com/pypeclub/OpenPype/pull/2546)

**🆕 New features**

- Flame: extracting segments with trans-coding  [\#2547](https://github.com/pypeclub/OpenPype/pull/2547)
- Maya : V-Ray Proxy - load all ABC files via proxy [\#2544](https://github.com/pypeclub/OpenPype/pull/2544)
- Maya to Unreal: Extended static mesh workflow [\#2537](https://github.com/pypeclub/OpenPype/pull/2537)
- Flame: collecting publishable instances [\#2519](https://github.com/pypeclub/OpenPype/pull/2519)
- Flame: create publishable clips [\#2495](https://github.com/pypeclub/OpenPype/pull/2495)
- Flame: OpenTimelineIO Export Modul [\#2398](https://github.com/pypeclub/OpenPype/pull/2398)

**🚀 Enhancements**

- Webpublisher: Moved error at the beginning of the log [\#2559](https://github.com/pypeclub/OpenPype/pull/2559)
- Ftrack: Use ApplicationManager to get DJV path [\#2558](https://github.com/pypeclub/OpenPype/pull/2558)
- Webpublisher: Added endpoint to reprocess batch through UI [\#2555](https://github.com/pypeclub/OpenPype/pull/2555)
- Settings: PathInput strip passed string [\#2550](https://github.com/pypeclub/OpenPype/pull/2550)
- Global: Exctract Review anatomy fill data with output name [\#2548](https://github.com/pypeclub/OpenPype/pull/2548)
- Cosmetics: Clean up some cosmetics / typos [\#2542](https://github.com/pypeclub/OpenPype/pull/2542)
- General: Validate if current process OpenPype version is requested version [\#2529](https://github.com/pypeclub/OpenPype/pull/2529)
- General: Be able to use anatomy data in ffmpeg output arguments [\#2525](https://github.com/pypeclub/OpenPype/pull/2525)
- Expose toggle publish plug-in settings for Maya Look Shading Engine Naming [\#2521](https://github.com/pypeclub/OpenPype/pull/2521)
- Photoshop: Move implementation to OpenPype [\#2510](https://github.com/pypeclub/OpenPype/pull/2510)
- TimersManager: Move module one hierarchy higher [\#2501](https://github.com/pypeclub/OpenPype/pull/2501)
- Slack: notifications are sent with Openpype logo and bot name [\#2499](https://github.com/pypeclub/OpenPype/pull/2499)
- Slack: Add review to notification message [\#2498](https://github.com/pypeclub/OpenPype/pull/2498)
- Ftrack: Event handlers settings [\#2496](https://github.com/pypeclub/OpenPype/pull/2496)
- Tools: Fix style and modality of errors in loader and creator [\#2489](https://github.com/pypeclub/OpenPype/pull/2489)
- Maya: Collect 'fps' animation data only for "review" instances [\#2486](https://github.com/pypeclub/OpenPype/pull/2486)
- Project Manager: Remove project button cleanup [\#2482](https://github.com/pypeclub/OpenPype/pull/2482)
- Tools: Be able to change models of tasks and assets widgets [\#2475](https://github.com/pypeclub/OpenPype/pull/2475)
- Publish pype: Reduce publish process defering [\#2464](https://github.com/pypeclub/OpenPype/pull/2464)
- Maya: Improve speed of Collect History logic [\#2460](https://github.com/pypeclub/OpenPype/pull/2460)
- Maya: Validate Rig Controllers - fix Error: in script editor [\#2459](https://github.com/pypeclub/OpenPype/pull/2459)
- Maya: Validate NGONs simplify and speed-up [\#2458](https://github.com/pypeclub/OpenPype/pull/2458)
- Maya: Optimize Validate Locked Normals speed for dense polymeshes [\#2457](https://github.com/pypeclub/OpenPype/pull/2457)
- Maya: Refactor missing \_get\_reference\_node method [\#2455](https://github.com/pypeclub/OpenPype/pull/2455)
- Houdini: Remove broken unique name counter [\#2450](https://github.com/pypeclub/OpenPype/pull/2450)
- Maya: Improve lib.polyConstraint performance when Select tool is not the active tool context [\#2447](https://github.com/pypeclub/OpenPype/pull/2447)
- General: Validate third party before build [\#2425](https://github.com/pypeclub/OpenPype/pull/2425)
- Maya : add option to not group reference in ReferenceLoader [\#2383](https://github.com/pypeclub/OpenPype/pull/2383)

**🐛 Bug fixes**

- AfterEffects: Fix - removed obsolete import [\#2577](https://github.com/pypeclub/OpenPype/pull/2577)
- General: OpenPype version updates [\#2575](https://github.com/pypeclub/OpenPype/pull/2575)
- Ftrack: Delete action revision [\#2563](https://github.com/pypeclub/OpenPype/pull/2563)
- Webpublisher: ftrack shows incorrect user names [\#2560](https://github.com/pypeclub/OpenPype/pull/2560)
- General: Do not validate version if build does not support it [\#2557](https://github.com/pypeclub/OpenPype/pull/2557)
- Webpublisher: Fixed progress reporting [\#2553](https://github.com/pypeclub/OpenPype/pull/2553)
- Fix Maya AssProxyLoader version switch [\#2551](https://github.com/pypeclub/OpenPype/pull/2551)
- General: Fix install thread in igniter [\#2549](https://github.com/pypeclub/OpenPype/pull/2549)
- Houdini: vdbcache family preserve frame numbers on publish integration + enable validate version for Houdini [\#2535](https://github.com/pypeclub/OpenPype/pull/2535)
- Maya: Fix Load VDB to V-Ray [\#2533](https://github.com/pypeclub/OpenPype/pull/2533)
- Maya: ReferenceLoader fix not unique group name error for attach to root [\#2532](https://github.com/pypeclub/OpenPype/pull/2532)
- Maya: namespaced context go back to original namespace when started from inside a namespace [\#2531](https://github.com/pypeclub/OpenPype/pull/2531)
- Fix create zip tool - path argument [\#2522](https://github.com/pypeclub/OpenPype/pull/2522)
- Maya: Fix Extract Look with space in names [\#2518](https://github.com/pypeclub/OpenPype/pull/2518)
- Fix published frame content for sequence starting with 0 [\#2513](https://github.com/pypeclub/OpenPype/pull/2513)
- Maya: reset empty string attributes correctly to "" instead of "None" [\#2506](https://github.com/pypeclub/OpenPype/pull/2506)
- Improve FusionPreLaunch hook errors [\#2505](https://github.com/pypeclub/OpenPype/pull/2505)
- General: Settings work if OpenPypeVersion is available [\#2494](https://github.com/pypeclub/OpenPype/pull/2494)
- General: PYTHONPATH may break OpenPype dependencies [\#2493](https://github.com/pypeclub/OpenPype/pull/2493)
- General: Modules import function output fix [\#2492](https://github.com/pypeclub/OpenPype/pull/2492)
- AE: fix hiding of alert window below Publish [\#2491](https://github.com/pypeclub/OpenPype/pull/2491)
- Workfiles tool: Files widget show files on first show [\#2488](https://github.com/pypeclub/OpenPype/pull/2488)
- General: Custom template paths filter fix [\#2483](https://github.com/pypeclub/OpenPype/pull/2483)
- Loader: Remove always on top flag in tray [\#2480](https://github.com/pypeclub/OpenPype/pull/2480)
- General: Anatomy does not return root envs as unicode [\#2465](https://github.com/pypeclub/OpenPype/pull/2465)
- Maya: Validate Shape Zero do not keep fixed geometry vertices selected/active after repair [\#2456](https://github.com/pypeclub/OpenPype/pull/2456)

**Merged pull requests:**

- AfterEffects: Move implementation to OpenPype [\#2543](https://github.com/pypeclub/OpenPype/pull/2543)
- Maya: Remove Maya Look Assigner check on startup [\#2540](https://github.com/pypeclub/OpenPype/pull/2540)
- build\(deps\): bump shelljs from 0.8.4 to 0.8.5 in /website [\#2538](https://github.com/pypeclub/OpenPype/pull/2538)
- build\(deps\): bump follow-redirects from 1.14.4 to 1.14.7 in /website [\#2534](https://github.com/pypeclub/OpenPype/pull/2534)
- Nuke: Merge avalon's implementation into OpenPype [\#2514](https://github.com/pypeclub/OpenPype/pull/2514)
- Maya: Vray fix proxies look assignment [\#2392](https://github.com/pypeclub/OpenPype/pull/2392)
- Bump algoliasearch-helper from 3.4.4 to 3.6.2 in /website [\#2297](https://github.com/pypeclub/OpenPype/pull/2297)

## [3.7.0](https://github.com/pypeclub/OpenPype/tree/3.7.0) (2022-01-04)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.6.4...3.7.0)

**Deprecated:**

- General: Default modules hierarchy n2 [\#2368](https://github.com/pypeclub/OpenPype/pull/2368)

### 📖 Documentation

- docs\[website\]: Add Ellipse Studio \(logo\) as an OpenPype contributor [\#2324](https://github.com/pypeclub/OpenPype/pull/2324)

**🆕 New features**

- Settings UI use OpenPype styles [\#2296](https://github.com/pypeclub/OpenPype/pull/2296)
- Store typed version dependencies for workfiles [\#2192](https://github.com/pypeclub/OpenPype/pull/2192)
- OpenPypeV3: add key task type, task shortname and user to path templating construction [\#2157](https://github.com/pypeclub/OpenPype/pull/2157)
- Nuke: Alembic model workflow [\#2140](https://github.com/pypeclub/OpenPype/pull/2140)
- TVPaint: Load workfile from published. [\#1980](https://github.com/pypeclub/OpenPype/pull/1980)

**🚀 Enhancements**

- General: Workdir extra folders [\#2462](https://github.com/pypeclub/OpenPype/pull/2462)
- Photoshop: New style validations for New publisher [\#2429](https://github.com/pypeclub/OpenPype/pull/2429)
- General: Environment variables groups [\#2424](https://github.com/pypeclub/OpenPype/pull/2424)
- Unreal: Dynamic menu created in Python [\#2422](https://github.com/pypeclub/OpenPype/pull/2422)
- Settings UI: Hyperlinks to settings [\#2420](https://github.com/pypeclub/OpenPype/pull/2420)
- Modules: JobQueue module moved one hierarchy level higher [\#2419](https://github.com/pypeclub/OpenPype/pull/2419)
- TimersManager: Start timer post launch hook [\#2418](https://github.com/pypeclub/OpenPype/pull/2418)
- General: Run applications as separate processes under linux [\#2408](https://github.com/pypeclub/OpenPype/pull/2408)
- Ftrack: Check existence of object type on recreation [\#2404](https://github.com/pypeclub/OpenPype/pull/2404)
- Enhancement: Global cleanup plugin that explicitly remove paths from context [\#2402](https://github.com/pypeclub/OpenPype/pull/2402)
- General: MongoDB ability to specify replica set groups [\#2401](https://github.com/pypeclub/OpenPype/pull/2401)
- Flame: moving `utility_scripts` to api folder also with `scripts` [\#2385](https://github.com/pypeclub/OpenPype/pull/2385)
- Centos 7 dependency compatibility [\#2384](https://github.com/pypeclub/OpenPype/pull/2384)
- Enhancement: Settings: Use project settings values from another project [\#2382](https://github.com/pypeclub/OpenPype/pull/2382)
- Blender 3: Support auto install for new blender version [\#2377](https://github.com/pypeclub/OpenPype/pull/2377)
- Maya add render image path to settings [\#2375](https://github.com/pypeclub/OpenPype/pull/2375)
- Settings: Webpublisher in hosts enum [\#2367](https://github.com/pypeclub/OpenPype/pull/2367)
- Hiero: python3 compatibility [\#2365](https://github.com/pypeclub/OpenPype/pull/2365)
- Burnins: Be able recognize mxf OPAtom format [\#2361](https://github.com/pypeclub/OpenPype/pull/2361)
- Maya: Add is\_static\_image\_plane and is\_in\_all\_views option in imagePlaneLoader [\#2356](https://github.com/pypeclub/OpenPype/pull/2356)
- Local settings: Copyable studio paths [\#2349](https://github.com/pypeclub/OpenPype/pull/2349)
- Assets Widget: Clear model on project change [\#2345](https://github.com/pypeclub/OpenPype/pull/2345)
- General: OpenPype default modules hierarchy [\#2338](https://github.com/pypeclub/OpenPype/pull/2338)
- TVPaint: Move implementation to OpenPype [\#2336](https://github.com/pypeclub/OpenPype/pull/2336)
- General: FFprobe error exception contain original error message [\#2328](https://github.com/pypeclub/OpenPype/pull/2328)
- Resolve: Add experimental button to menu [\#2325](https://github.com/pypeclub/OpenPype/pull/2325)
- Hiero: Add experimental tools action [\#2323](https://github.com/pypeclub/OpenPype/pull/2323)
- Input links: Cleanup and unification of differences [\#2322](https://github.com/pypeclub/OpenPype/pull/2322)
- General: Don't validate vendor bin with executing them [\#2317](https://github.com/pypeclub/OpenPype/pull/2317)
- General: Multilayer EXRs support [\#2315](https://github.com/pypeclub/OpenPype/pull/2315)
- General: Run process log stderr as info log level [\#2309](https://github.com/pypeclub/OpenPype/pull/2309)
- General: Reduce vendor imports [\#2305](https://github.com/pypeclub/OpenPype/pull/2305)
- Tools: Cleanup of unused classes [\#2304](https://github.com/pypeclub/OpenPype/pull/2304)
- Project Manager: Added ability to delete project [\#2298](https://github.com/pypeclub/OpenPype/pull/2298)
- Ftrack: Synchronize input links [\#2287](https://github.com/pypeclub/OpenPype/pull/2287)
- StandalonePublisher: Remove unused plugin ExtractHarmonyZip [\#2277](https://github.com/pypeclub/OpenPype/pull/2277)
- Ftrack: Support multiple reviews [\#2271](https://github.com/pypeclub/OpenPype/pull/2271)
- Ftrack: Remove unused clean component plugin [\#2269](https://github.com/pypeclub/OpenPype/pull/2269)
- Royal Render: Support for rr channels in separate dirs [\#2268](https://github.com/pypeclub/OpenPype/pull/2268)
- Houdini: Add experimental tools action [\#2267](https://github.com/pypeclub/OpenPype/pull/2267)
- Nuke: extract baked review videos presets [\#2248](https://github.com/pypeclub/OpenPype/pull/2248)
- TVPaint: Workers rendering [\#2209](https://github.com/pypeclub/OpenPype/pull/2209)
- OpenPypeV3: Add key parent asset to path templating construction [\#2186](https://github.com/pypeclub/OpenPype/pull/2186)

**🐛 Bug fixes**

- TVPaint: Create render layer dialog is in front [\#2471](https://github.com/pypeclub/OpenPype/pull/2471)
- Short Pyblish plugin path [\#2428](https://github.com/pypeclub/OpenPype/pull/2428)
- PS: Introduced settings for invalid characters to use in ValidateNaming plugin [\#2417](https://github.com/pypeclub/OpenPype/pull/2417)
- Settings UI: Breadcrumbs path does not create new entities [\#2416](https://github.com/pypeclub/OpenPype/pull/2416)
- AfterEffects: Variant 2022 is in defaults but missing in schemas [\#2412](https://github.com/pypeclub/OpenPype/pull/2412)
- Nuke: baking representations was not additive [\#2406](https://github.com/pypeclub/OpenPype/pull/2406)
- General: Fix access to environments from default settings [\#2403](https://github.com/pypeclub/OpenPype/pull/2403)
- Fix: Placeholder Input color set fix [\#2399](https://github.com/pypeclub/OpenPype/pull/2399)
- Settings: Fix state change of wrapper label [\#2396](https://github.com/pypeclub/OpenPype/pull/2396)
- Flame: fix ftrack publisher [\#2381](https://github.com/pypeclub/OpenPype/pull/2381)
- hiero: solve custom ocio path  [\#2379](https://github.com/pypeclub/OpenPype/pull/2379)
- hiero: fix workio and flatten [\#2378](https://github.com/pypeclub/OpenPype/pull/2378)
- Nuke: fixing menu re-drawing during context change  [\#2374](https://github.com/pypeclub/OpenPype/pull/2374)
- Webpublisher: Fix assignment of families of TVpaint instances [\#2373](https://github.com/pypeclub/OpenPype/pull/2373)
- Nuke: fixing node name based on switched asset name [\#2369](https://github.com/pypeclub/OpenPype/pull/2369)
- JobQueue: Fix loading of settings [\#2362](https://github.com/pypeclub/OpenPype/pull/2362)
- Tools: Placeholder color [\#2359](https://github.com/pypeclub/OpenPype/pull/2359)
- Launcher: Minimize button on MacOs [\#2355](https://github.com/pypeclub/OpenPype/pull/2355)
- StandalonePublisher: Fix import of constant [\#2354](https://github.com/pypeclub/OpenPype/pull/2354)
- Houdini: Fix HDA creation [\#2350](https://github.com/pypeclub/OpenPype/pull/2350)
- Adobe products show issue [\#2347](https://github.com/pypeclub/OpenPype/pull/2347)
- Maya Look Assigner: Fix Python 3 compatibility [\#2343](https://github.com/pypeclub/OpenPype/pull/2343)
- Remove wrongly used host for hook [\#2342](https://github.com/pypeclub/OpenPype/pull/2342)
- Tools: Use Qt context on tools show [\#2340](https://github.com/pypeclub/OpenPype/pull/2340)
- Flame: Fix default argument value in custom dictionary [\#2339](https://github.com/pypeclub/OpenPype/pull/2339)
- Timers Manager: Disable auto stop timer on linux platform [\#2334](https://github.com/pypeclub/OpenPype/pull/2334)
- nuke: bake preset single input exception  [\#2331](https://github.com/pypeclub/OpenPype/pull/2331)
- Hiero: fixing multiple templates at a hierarchy parent [\#2330](https://github.com/pypeclub/OpenPype/pull/2330)
- Fix - provider icons are pulled from a folder [\#2326](https://github.com/pypeclub/OpenPype/pull/2326)
- InputLinks: Typo in "inputLinks" key [\#2314](https://github.com/pypeclub/OpenPype/pull/2314)
- Deadline timeout and logging [\#2312](https://github.com/pypeclub/OpenPype/pull/2312)
- nuke: do not multiply representation on class method [\#2311](https://github.com/pypeclub/OpenPype/pull/2311)
- Workfiles tool: Fix task formatting [\#2306](https://github.com/pypeclub/OpenPype/pull/2306)
- Delivery: Fix delivery paths created on windows [\#2302](https://github.com/pypeclub/OpenPype/pull/2302)
- Maya: Deadline - fix limit groups [\#2295](https://github.com/pypeclub/OpenPype/pull/2295)
- Royal Render: Fix plugin order and OpenPype auto-detection [\#2291](https://github.com/pypeclub/OpenPype/pull/2291)
- New Publisher: Fix mapping of indexes [\#2285](https://github.com/pypeclub/OpenPype/pull/2285)
- Alternate site for site sync doesnt work for sequences [\#2284](https://github.com/pypeclub/OpenPype/pull/2284)
- FFmpeg: Execute ffprobe using list of arguments instead of string command [\#2281](https://github.com/pypeclub/OpenPype/pull/2281)
- Nuke: Anatomy fill data use task as dictionary [\#2278](https://github.com/pypeclub/OpenPype/pull/2278)
- Bug: fix variable name \_asset\_id in workfiles application [\#2274](https://github.com/pypeclub/OpenPype/pull/2274)
- Version handling fixes [\#2272](https://github.com/pypeclub/OpenPype/pull/2272)

**Merged pull requests:**

- Maya: Replaced PATH usage with vendored oiio path for maketx utility [\#2405](https://github.com/pypeclub/OpenPype/pull/2405)
- \[Fix\]\[MAYA\] Handle message type attribute within CollectLook [\#2394](https://github.com/pypeclub/OpenPype/pull/2394)
- Add validator to check correct version of extension for PS and AE [\#2387](https://github.com/pypeclub/OpenPype/pull/2387)
- Maya: configurable model top level validation [\#2321](https://github.com/pypeclub/OpenPype/pull/2321)
- Create test publish class for After Effects [\#2270](https://github.com/pypeclub/OpenPype/pull/2270)

## [3.6.4](https://github.com/pypeclub/OpenPype/tree/3.6.4) (2021-11-23)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.6.3...3.6.4)

**🐛 Bug fixes**

- Nuke: inventory update removes all loaded read nodes [\#2294](https://github.com/pypeclub/OpenPype/pull/2294)

## [3.6.3](https://github.com/pypeclub/OpenPype/tree/3.6.3) (2021-11-19)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.6.2...3.6.3)

**🐛 Bug fixes**

- Deadline: Fix publish targets [\#2280](https://github.com/pypeclub/OpenPype/pull/2280)

## [3.6.2](https://github.com/pypeclub/OpenPype/tree/3.6.2) (2021-11-18)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.6.1...3.6.2)

**🚀 Enhancements**

- Tools: Assets widget [\#2265](https://github.com/pypeclub/OpenPype/pull/2265)
- SceneInventory: Choose loader in asset switcher [\#2262](https://github.com/pypeclub/OpenPype/pull/2262)
- Style: New fonts in OpenPype style [\#2256](https://github.com/pypeclub/OpenPype/pull/2256)
- Tools: SceneInventory in OpenPype  [\#2255](https://github.com/pypeclub/OpenPype/pull/2255)
- Tools: Tasks widget [\#2251](https://github.com/pypeclub/OpenPype/pull/2251)
- Tools: Creator in OpenPype [\#2244](https://github.com/pypeclub/OpenPype/pull/2244)
- Added endpoint for configured extensions [\#2221](https://github.com/pypeclub/OpenPype/pull/2221)

**🐛 Bug fixes**

- Tools: Parenting of tools in Nuke and Hiero [\#2266](https://github.com/pypeclub/OpenPype/pull/2266)
- limiting validator to specific editorial hosts [\#2264](https://github.com/pypeclub/OpenPype/pull/2264)
- Tools: Select Context dialog attribute fix [\#2261](https://github.com/pypeclub/OpenPype/pull/2261)
- Maya: Render publishing fails on linux [\#2260](https://github.com/pypeclub/OpenPype/pull/2260)
- LookAssigner: Fix tool reopen [\#2259](https://github.com/pypeclub/OpenPype/pull/2259)
- Standalone: editorial not publishing thumbnails on all subsets [\#2258](https://github.com/pypeclub/OpenPype/pull/2258)
- Burnins: Support mxf metadata [\#2247](https://github.com/pypeclub/OpenPype/pull/2247)
- Maya: Support for configurable AOV separator characters [\#2197](https://github.com/pypeclub/OpenPype/pull/2197)
- Maya: texture colorspace modes in looks [\#2195](https://github.com/pypeclub/OpenPype/pull/2195)

## [3.6.1](https://github.com/pypeclub/OpenPype/tree/3.6.1) (2021-11-16)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.6.0...3.6.1)

**🐛 Bug fixes**

- Loader doesn't allow changing of version before loading [\#2254](https://github.com/pypeclub/OpenPype/pull/2254)

## [3.6.0](https://github.com/pypeclub/OpenPype/tree/3.6.0) (2021-11-15)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.5.0...3.6.0)

### 📖 Documentation

- Add alternative sites for Site Sync [\#2206](https://github.com/pypeclub/OpenPype/pull/2206)
- Add command line way of running site sync server [\#2188](https://github.com/pypeclub/OpenPype/pull/2188)

**🆕 New features**

- Add validate active site button to sync queue on a project [\#2176](https://github.com/pypeclub/OpenPype/pull/2176)
- Maya : Colorspace configuration  [\#2170](https://github.com/pypeclub/OpenPype/pull/2170)
- Blender: Added support for audio [\#2168](https://github.com/pypeclub/OpenPype/pull/2168)
- Flame: a host basic integration [\#2165](https://github.com/pypeclub/OpenPype/pull/2165)
- Houdini: simple HDA workflow [\#2072](https://github.com/pypeclub/OpenPype/pull/2072)
- Basic Royal Render Integration ✨ [\#2061](https://github.com/pypeclub/OpenPype/pull/2061)
- Camera handling between Blender and Unreal [\#1988](https://github.com/pypeclub/OpenPype/pull/1988)
- switch PyQt5 for PySide2 [\#1744](https://github.com/pypeclub/OpenPype/pull/1744)

**🚀 Enhancements**

- Tools: Subset manager in OpenPype [\#2243](https://github.com/pypeclub/OpenPype/pull/2243)
- General: Skip module directories without init file [\#2239](https://github.com/pypeclub/OpenPype/pull/2239)
- General: Static interfaces [\#2238](https://github.com/pypeclub/OpenPype/pull/2238)
- Style: Fix transparent image in style [\#2235](https://github.com/pypeclub/OpenPype/pull/2235)
- Add a "following workfile versioning" option on publish [\#2225](https://github.com/pypeclub/OpenPype/pull/2225)
- Modules: Module can add cli commands [\#2224](https://github.com/pypeclub/OpenPype/pull/2224)
- Webpublisher: Separate webpublisher logic [\#2222](https://github.com/pypeclub/OpenPype/pull/2222)
- Add both side availability on Site Sync sites to Loader [\#2220](https://github.com/pypeclub/OpenPype/pull/2220)
- Tools: Center loader and library loader on show [\#2219](https://github.com/pypeclub/OpenPype/pull/2219)
- Maya : Validate shape zero [\#2212](https://github.com/pypeclub/OpenPype/pull/2212)
- Maya : validate unique names [\#2211](https://github.com/pypeclub/OpenPype/pull/2211)
- Tools: OpenPype stylesheet in workfiles tool [\#2208](https://github.com/pypeclub/OpenPype/pull/2208)
- Ftrack: Replace Queue with deque in event handlers logic [\#2204](https://github.com/pypeclub/OpenPype/pull/2204)
- Tools: New select context dialog [\#2200](https://github.com/pypeclub/OpenPype/pull/2200)
- Maya : Validate mesh ngons [\#2199](https://github.com/pypeclub/OpenPype/pull/2199)
- Dirmap in Nuke [\#2198](https://github.com/pypeclub/OpenPype/pull/2198)
- Delivery: Check 'frame' key in template for sequence delivery [\#2196](https://github.com/pypeclub/OpenPype/pull/2196)
- Settings: Site sync project settings improvement [\#2193](https://github.com/pypeclub/OpenPype/pull/2193)
- Usage of tools code [\#2185](https://github.com/pypeclub/OpenPype/pull/2185)
- Settings: Dictionary based on project roots [\#2184](https://github.com/pypeclub/OpenPype/pull/2184)
- Subset name: Be able to pass asset document to get subset name [\#2179](https://github.com/pypeclub/OpenPype/pull/2179)
- Tools: Experimental tools [\#2167](https://github.com/pypeclub/OpenPype/pull/2167)
- Loader: Refactor and use OpenPype stylesheets [\#2166](https://github.com/pypeclub/OpenPype/pull/2166)
- Add loader for linked smart objects in photoshop [\#2149](https://github.com/pypeclub/OpenPype/pull/2149)
- Burnins: DNxHD profiles handling [\#2142](https://github.com/pypeclub/OpenPype/pull/2142)
- Tools: Single access point for host tools [\#2139](https://github.com/pypeclub/OpenPype/pull/2139)

**🐛 Bug fixes**

- Ftrack: Sync project ftrack id cache issue [\#2250](https://github.com/pypeclub/OpenPype/pull/2250)
- Ftrack: Session creation and Prepare project [\#2245](https://github.com/pypeclub/OpenPype/pull/2245)
- Added queue for studio processing in PS [\#2237](https://github.com/pypeclub/OpenPype/pull/2237)
- Python 2: Unicode to string conversion [\#2236](https://github.com/pypeclub/OpenPype/pull/2236)
- Fix - enum for color coding in PS [\#2234](https://github.com/pypeclub/OpenPype/pull/2234)
- Pyblish Tool: Fix targets handling [\#2232](https://github.com/pypeclub/OpenPype/pull/2232)
- Ftrack: Base event fix of 'get\_project\_from\_entity' method [\#2214](https://github.com/pypeclub/OpenPype/pull/2214)
- Maya : multiple subsets review broken [\#2210](https://github.com/pypeclub/OpenPype/pull/2210)
- Fix - different command used for Linux and Mac OS [\#2207](https://github.com/pypeclub/OpenPype/pull/2207)
- Tools: Workfiles tool don't use avalon widgets [\#2205](https://github.com/pypeclub/OpenPype/pull/2205)
- Ftrack: Fill missing ftrack id on mongo project [\#2203](https://github.com/pypeclub/OpenPype/pull/2203)
- Project Manager: Fix copying of tasks [\#2191](https://github.com/pypeclub/OpenPype/pull/2191)
- StandalonePublisher: Source validator don't expect representations [\#2190](https://github.com/pypeclub/OpenPype/pull/2190)
- Blender: Fix trying to pack an image when the shader node has no texture [\#2183](https://github.com/pypeclub/OpenPype/pull/2183)
- Maya: review viewport settings [\#2177](https://github.com/pypeclub/OpenPype/pull/2177)
- MacOS: Launching of applications may cause Permissions error [\#2175](https://github.com/pypeclub/OpenPype/pull/2175)
- Maya: Aspect ratio [\#2174](https://github.com/pypeclub/OpenPype/pull/2174)
- Blender: Fix 'Deselect All' with object not in 'Object Mode' [\#2163](https://github.com/pypeclub/OpenPype/pull/2163)
- Tools: Stylesheets are applied after tool show [\#2161](https://github.com/pypeclub/OpenPype/pull/2161)
- Maya: Collect render - fix UNC path support 🐛 [\#2158](https://github.com/pypeclub/OpenPype/pull/2158)
- Maya: Fix hotbox broken by scriptsmenu [\#2151](https://github.com/pypeclub/OpenPype/pull/2151)
- Ftrack: Ignore save warnings exception in Prepare project action [\#2150](https://github.com/pypeclub/OpenPype/pull/2150)
- Loader thumbnails with smooth edges [\#2147](https://github.com/pypeclub/OpenPype/pull/2147)
- Added validator for source files for Standalone Publisher [\#2138](https://github.com/pypeclub/OpenPype/pull/2138)

**Merged pull requests:**

- Bump pillow from 8.2.0 to 8.3.2 [\#2162](https://github.com/pypeclub/OpenPype/pull/2162)
- Bump axios from 0.21.1 to 0.21.4 in /website [\#2059](https://github.com/pypeclub/OpenPype/pull/2059)

## [3.5.0](https://github.com/pypeclub/OpenPype/tree/3.5.0) (2021-10-17)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.4.1...3.5.0)

**Deprecated:**

- Maya: Change mayaAscii family to mayaScene [\#2106](https://github.com/pypeclub/OpenPype/pull/2106)

**🆕 New features**

- Added project and task into context change message in Maya [\#2131](https://github.com/pypeclub/OpenPype/pull/2131)
- Add ExtractBurnin to photoshop review [\#2124](https://github.com/pypeclub/OpenPype/pull/2124)
- PYPE-1218 - changed namespace to contain subset name in Maya [\#2114](https://github.com/pypeclub/OpenPype/pull/2114)
- Added running configurable disk mapping command before start of OP [\#2091](https://github.com/pypeclub/OpenPype/pull/2091)
- SFTP provider [\#2073](https://github.com/pypeclub/OpenPype/pull/2073)
- Maya: Validate setdress top group [\#2068](https://github.com/pypeclub/OpenPype/pull/2068)
- Maya: Enable publishing render attrib sets \(e.g. V-Ray Displacement\) with model [\#1955](https://github.com/pypeclub/OpenPype/pull/1955)

**🚀 Enhancements**

- Maya: make rig validators configurable in settings [\#2137](https://github.com/pypeclub/OpenPype/pull/2137)
- Settings: Updated readme for entity types in settings [\#2132](https://github.com/pypeclub/OpenPype/pull/2132)
- Nuke: unified clip loader [\#2128](https://github.com/pypeclub/OpenPype/pull/2128)
- Settings UI: Project model refreshing and sorting [\#2104](https://github.com/pypeclub/OpenPype/pull/2104)
- Create Read From Rendered - Disable Relative paths by default [\#2093](https://github.com/pypeclub/OpenPype/pull/2093)
- Added choosing different dirmap mapping if workfile synched locally [\#2088](https://github.com/pypeclub/OpenPype/pull/2088)
- General: Remove IdleManager module [\#2084](https://github.com/pypeclub/OpenPype/pull/2084)
- Tray UI: Message box about missing settings defaults [\#2080](https://github.com/pypeclub/OpenPype/pull/2080)
- Tray UI: Show menu where first click happened [\#2079](https://github.com/pypeclub/OpenPype/pull/2079)
- Global: add global validators to settings [\#2078](https://github.com/pypeclub/OpenPype/pull/2078)
- Use CRF for burnin when available [\#2070](https://github.com/pypeclub/OpenPype/pull/2070)
- Project manager: Filter first item after selection of project [\#2069](https://github.com/pypeclub/OpenPype/pull/2069)
- Nuke: Adding `still` image family workflow [\#2064](https://github.com/pypeclub/OpenPype/pull/2064)
- Maya: validate authorized loaded plugins [\#2062](https://github.com/pypeclub/OpenPype/pull/2062)
- Tools: add support for pyenv on windows [\#2051](https://github.com/pypeclub/OpenPype/pull/2051)
- SyncServer: Dropbox Provider [\#1979](https://github.com/pypeclub/OpenPype/pull/1979)
- Burnin: Get data from context with defined keys. [\#1897](https://github.com/pypeclub/OpenPype/pull/1897)
- Timers manager: Get task time [\#1896](https://github.com/pypeclub/OpenPype/pull/1896)
- TVPaint: Option to stop timer on application exit. [\#1887](https://github.com/pypeclub/OpenPype/pull/1887)

**🐛 Bug fixes**

- Maya: fix model publishing [\#2130](https://github.com/pypeclub/OpenPype/pull/2130)
- Fix - oiiotool wasn't recognized even if present [\#2129](https://github.com/pypeclub/OpenPype/pull/2129)
- General: Disk mapping group [\#2120](https://github.com/pypeclub/OpenPype/pull/2120)
- Hiero: publishing effect first time makes wrong resources path [\#2115](https://github.com/pypeclub/OpenPype/pull/2115)
- Add startup script for Houdini Core.  [\#2110](https://github.com/pypeclub/OpenPype/pull/2110)
- TVPaint: Behavior name of loop also accept repeat [\#2109](https://github.com/pypeclub/OpenPype/pull/2109)
- Ftrack: Project settings save custom attributes skip unknown attributes [\#2103](https://github.com/pypeclub/OpenPype/pull/2103)
- Blender: Fix NoneType error when animation\_data is missing for a rig [\#2101](https://github.com/pypeclub/OpenPype/pull/2101)
- Fix broken import in sftp provider [\#2100](https://github.com/pypeclub/OpenPype/pull/2100)
- Global: Fix docstring on publish plugin extract review [\#2097](https://github.com/pypeclub/OpenPype/pull/2097)
- Delivery Action Files Sequence fix [\#2096](https://github.com/pypeclub/OpenPype/pull/2096)
- General: Cloud mongo ca certificate issue [\#2095](https://github.com/pypeclub/OpenPype/pull/2095)
- TVPaint: Creator use context from workfile [\#2087](https://github.com/pypeclub/OpenPype/pull/2087)
- Blender: fix texture missing when publishing blend files [\#2085](https://github.com/pypeclub/OpenPype/pull/2085)
- General: Startup validations oiio tool path fix on linux [\#2083](https://github.com/pypeclub/OpenPype/pull/2083)
- Deadline: Collect deadline server does not check existence of deadline key [\#2082](https://github.com/pypeclub/OpenPype/pull/2082)
- Blender: fixed Curves with modifiers in Rigs [\#2081](https://github.com/pypeclub/OpenPype/pull/2081)
- Nuke UI scaling [\#2077](https://github.com/pypeclub/OpenPype/pull/2077)
- Maya: Fix multi-camera renders [\#2065](https://github.com/pypeclub/OpenPype/pull/2065)
- Fix Sync Queue when project disabled [\#2063](https://github.com/pypeclub/OpenPype/pull/2063)

**Merged pull requests:**

- Bump pywin32 from 300 to 301 [\#2086](https://github.com/pypeclub/OpenPype/pull/2086)

## [3.4.1](https://github.com/pypeclub/OpenPype/tree/3.4.1) (2021-09-23)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.4.0...3.4.1)

**🆕 New features**

- Settings: Flag project as deactivated and hide from tools' view [\#2008](https://github.com/pypeclub/OpenPype/pull/2008)

**🚀 Enhancements**

- General: Startup validations [\#2054](https://github.com/pypeclub/OpenPype/pull/2054)
- Nuke: proxy mode validator [\#2052](https://github.com/pypeclub/OpenPype/pull/2052)
- Ftrack: Removed ftrack interface [\#2049](https://github.com/pypeclub/OpenPype/pull/2049)
- Settings UI: Deffered set value on entity [\#2044](https://github.com/pypeclub/OpenPype/pull/2044)
- Loader: Families filtering [\#2043](https://github.com/pypeclub/OpenPype/pull/2043)
- Settings UI: Project view enhancements [\#2042](https://github.com/pypeclub/OpenPype/pull/2042)
- Settings for Nuke IncrementScriptVersion [\#2039](https://github.com/pypeclub/OpenPype/pull/2039)
- Loader & Library loader: Use tools from OpenPype [\#2038](https://github.com/pypeclub/OpenPype/pull/2038)
- Adding predefined project folders creation in PM [\#2030](https://github.com/pypeclub/OpenPype/pull/2030)
- WebserverModule: Removed interface of webserver module [\#2028](https://github.com/pypeclub/OpenPype/pull/2028)
- TimersManager: Removed interface of timers manager [\#2024](https://github.com/pypeclub/OpenPype/pull/2024)
- Feature Maya import asset from scene inventory [\#2018](https://github.com/pypeclub/OpenPype/pull/2018)

**🐛 Bug fixes**

- Timers manger: Typo fix [\#2058](https://github.com/pypeclub/OpenPype/pull/2058)
- Hiero: Editorial fixes [\#2057](https://github.com/pypeclub/OpenPype/pull/2057)
- Differentiate jpg sequences from thumbnail [\#2056](https://github.com/pypeclub/OpenPype/pull/2056)
- FFmpeg: Split command to list does not work [\#2046](https://github.com/pypeclub/OpenPype/pull/2046)
- Removed shell flag in subprocess call [\#2045](https://github.com/pypeclub/OpenPype/pull/2045)

**Merged pull requests:**

- Bump prismjs from 1.24.0 to 1.25.0 in /website [\#2050](https://github.com/pypeclub/OpenPype/pull/2050)

## [3.4.0](https://github.com/pypeclub/OpenPype/tree/3.4.0) (2021-09-17)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.3.1...3.4.0)

### 📖 Documentation

- Documentation: Ftrack launch argsuments update [\#2014](https://github.com/pypeclub/OpenPype/pull/2014)
- Nuke Quick Start / Tutorial [\#1952](https://github.com/pypeclub/OpenPype/pull/1952)
- Houdini: add Camera, Point Cache, Composite, Redshift ROP and VDB Cache support [\#1821](https://github.com/pypeclub/OpenPype/pull/1821)

**🆕 New features**

- Nuke: Compatibility with Nuke 13 [\#2003](https://github.com/pypeclub/OpenPype/pull/2003)
- Maya: Add Xgen family support [\#1947](https://github.com/pypeclub/OpenPype/pull/1947)
- Feature/webpublisher backend [\#1876](https://github.com/pypeclub/OpenPype/pull/1876)
- Blender: Improved assets handling [\#1615](https://github.com/pypeclub/OpenPype/pull/1615)

**🚀 Enhancements**

- Added possibility to configure of synchronization of workfile version… [\#2041](https://github.com/pypeclub/OpenPype/pull/2041)
- General: Task types in profiles [\#2036](https://github.com/pypeclub/OpenPype/pull/2036)
- Console interpreter: Handle invalid sizes on initialization [\#2022](https://github.com/pypeclub/OpenPype/pull/2022)
- Ftrack: Show OpenPype versions in event server status [\#2019](https://github.com/pypeclub/OpenPype/pull/2019)
- General: Staging icon [\#2017](https://github.com/pypeclub/OpenPype/pull/2017)
- Ftrack: Sync to avalon actions have jobs [\#2015](https://github.com/pypeclub/OpenPype/pull/2015)
- Modules: Connect method is not required [\#2009](https://github.com/pypeclub/OpenPype/pull/2009)
- Settings UI: Number with configurable steps [\#2001](https://github.com/pypeclub/OpenPype/pull/2001)
- Moving project folder structure creation out of ftrack module \#1989 [\#1996](https://github.com/pypeclub/OpenPype/pull/1996)
- Configurable items for providers without Settings [\#1987](https://github.com/pypeclub/OpenPype/pull/1987)
- Global: Example addons [\#1986](https://github.com/pypeclub/OpenPype/pull/1986)
- Standalone Publisher: Extract harmony zip handle workfile template [\#1982](https://github.com/pypeclub/OpenPype/pull/1982)
- Settings UI: Number sliders [\#1978](https://github.com/pypeclub/OpenPype/pull/1978)
- Workfiles: Support more workfile templates [\#1966](https://github.com/pypeclub/OpenPype/pull/1966)
- Launcher: Fix crashes on action click [\#1964](https://github.com/pypeclub/OpenPype/pull/1964)
- Settings: Minor fixes in UI and missing default values [\#1963](https://github.com/pypeclub/OpenPype/pull/1963)
- Blender: Toggle system console works on windows [\#1962](https://github.com/pypeclub/OpenPype/pull/1962)
- Global: Settings defined by Addons/Modules [\#1959](https://github.com/pypeclub/OpenPype/pull/1959)
- CI: change release numbering triggers [\#1954](https://github.com/pypeclub/OpenPype/pull/1954)
- Global: Avalon Host name collector [\#1949](https://github.com/pypeclub/OpenPype/pull/1949)
- Global: Define hosts in CollectSceneVersion [\#1948](https://github.com/pypeclub/OpenPype/pull/1948)
- Add face sets to exported alembics [\#1942](https://github.com/pypeclub/OpenPype/pull/1942)
- OpenPype: Add version validation and `--headless` mode and update progress 🔄 [\#1939](https://github.com/pypeclub/OpenPype/pull/1939)
- \#1894 - adds host to template\_name\_profiles for filtering [\#1915](https://github.com/pypeclub/OpenPype/pull/1915)
- Environments: Tool environments in alphabetical order [\#1910](https://github.com/pypeclub/OpenPype/pull/1910)
- Disregard publishing time. [\#1888](https://github.com/pypeclub/OpenPype/pull/1888)
- Dynamic modules [\#1872](https://github.com/pypeclub/OpenPype/pull/1872)

**🐛 Bug fixes**

- Workfiles tool: Task selection [\#2040](https://github.com/pypeclub/OpenPype/pull/2040)
- Ftrack: Delete old versions missing settings key [\#2037](https://github.com/pypeclub/OpenPype/pull/2037)
- Nuke: typo on a button [\#2034](https://github.com/pypeclub/OpenPype/pull/2034)
- Hiero: Fix "none" named tags [\#2033](https://github.com/pypeclub/OpenPype/pull/2033)
- FFmpeg: Subprocess arguments as list [\#2032](https://github.com/pypeclub/OpenPype/pull/2032)
- General: Fix Python 2 breaking line [\#2016](https://github.com/pypeclub/OpenPype/pull/2016)
- Bugfix/webpublisher task type [\#2006](https://github.com/pypeclub/OpenPype/pull/2006)
- Nuke thumbnails generated from middle of the sequence [\#1992](https://github.com/pypeclub/OpenPype/pull/1992)
- Nuke: last version from path gets correct version [\#1990](https://github.com/pypeclub/OpenPype/pull/1990)
- nuke, resolve, hiero: precollector order lest then 0.5 [\#1984](https://github.com/pypeclub/OpenPype/pull/1984)
- Last workfile with multiple work templates [\#1981](https://github.com/pypeclub/OpenPype/pull/1981)
- Collectors order [\#1977](https://github.com/pypeclub/OpenPype/pull/1977)
- Stop timer was within validator order range. [\#1975](https://github.com/pypeclub/OpenPype/pull/1975)
- Ftrack: arrow submodule has https url source [\#1974](https://github.com/pypeclub/OpenPype/pull/1974)
- Ftrack: Fix hosts attribute in collect ftrack username [\#1972](https://github.com/pypeclub/OpenPype/pull/1972)
- Deadline: Houdini plugins in different hierarchy [\#1970](https://github.com/pypeclub/OpenPype/pull/1970)
- Removed deprecated submodules [\#1967](https://github.com/pypeclub/OpenPype/pull/1967)
- Global: ExtractJpeg can handle filepaths with spaces [\#1961](https://github.com/pypeclub/OpenPype/pull/1961)
- Resolve path when adding to zip [\#1960](https://github.com/pypeclub/OpenPype/pull/1960)

**Merged pull requests:**

- Bump url-parse from 1.5.1 to 1.5.3 in /website [\#1958](https://github.com/pypeclub/OpenPype/pull/1958)
- Bump path-parse from 1.0.6 to 1.0.7 in /website [\#1933](https://github.com/pypeclub/OpenPype/pull/1933)

## [3.3.1](https://github.com/pypeclub/OpenPype/tree/3.3.1) (2021-08-20)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.3.0...3.3.1)

**🐛 Bug fixes**

- TVPaint: Fixed rendered frame indexes [\#1946](https://github.com/pypeclub/OpenPype/pull/1946)
- Maya: Menu actions fix [\#1945](https://github.com/pypeclub/OpenPype/pull/1945)
- standalone: editorial shared object problem [\#1941](https://github.com/pypeclub/OpenPype/pull/1941)
- Bugfix nuke deadline app name [\#1928](https://github.com/pypeclub/OpenPype/pull/1928)

## [3.3.0](https://github.com/pypeclub/OpenPype/tree/3.3.0) (2021-08-17)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.2.0...3.3.0)

### 📖 Documentation

- Standalone Publish of textures family [\#1834](https://github.com/pypeclub/OpenPype/pull/1834)

**🆕 New features**

- Settings UI: Breadcrumbs in settings [\#1932](https://github.com/pypeclub/OpenPype/pull/1932)
- Maya: Scene patching 🩹on submission to Deadline [\#1923](https://github.com/pypeclub/OpenPype/pull/1923)
- Feature AE local render [\#1901](https://github.com/pypeclub/OpenPype/pull/1901)

**🚀 Enhancements**

- Python console interpreter [\#1940](https://github.com/pypeclub/OpenPype/pull/1940)
- Global: Updated logos and Default settings [\#1927](https://github.com/pypeclub/OpenPype/pull/1927)
- Check for missing ✨ Python when using `pyenv` [\#1925](https://github.com/pypeclub/OpenPype/pull/1925)
- Settings: Default values for enum [\#1920](https://github.com/pypeclub/OpenPype/pull/1920)
- Settings UI: Modifiable dict view enhance [\#1919](https://github.com/pypeclub/OpenPype/pull/1919)
- submodules: avalon-core update [\#1911](https://github.com/pypeclub/OpenPype/pull/1911)
- Ftrack: Where I run action enhancement [\#1900](https://github.com/pypeclub/OpenPype/pull/1900)
- Ftrack: Private project server actions [\#1899](https://github.com/pypeclub/OpenPype/pull/1899)
- Support nested studio plugins paths. [\#1898](https://github.com/pypeclub/OpenPype/pull/1898)
- Settings: global validators with options [\#1892](https://github.com/pypeclub/OpenPype/pull/1892)
- Settings: Conditional dict enum positioning [\#1891](https://github.com/pypeclub/OpenPype/pull/1891)
- Expose stop timer through rest api. [\#1886](https://github.com/pypeclub/OpenPype/pull/1886)
- TVPaint: Increment workfile [\#1885](https://github.com/pypeclub/OpenPype/pull/1885)
- Allow Multiple Notes to run on tasks. [\#1882](https://github.com/pypeclub/OpenPype/pull/1882)
- Prepare for pyside2 [\#1869](https://github.com/pypeclub/OpenPype/pull/1869)
- Filter hosts in settings host-enum [\#1868](https://github.com/pypeclub/OpenPype/pull/1868)
- Local actions with process identifier [\#1867](https://github.com/pypeclub/OpenPype/pull/1867)
- Workfile tool start at host launch support [\#1865](https://github.com/pypeclub/OpenPype/pull/1865)
- Anatomy schema validation [\#1864](https://github.com/pypeclub/OpenPype/pull/1864)
- Ftrack prepare project structure [\#1861](https://github.com/pypeclub/OpenPype/pull/1861)
- Maya: support for configurable `dirmap` 🗺️ [\#1859](https://github.com/pypeclub/OpenPype/pull/1859)
- Independent general environments [\#1853](https://github.com/pypeclub/OpenPype/pull/1853)
- TVPaint Start Frame [\#1844](https://github.com/pypeclub/OpenPype/pull/1844)
- Ftrack push attributes action adds traceback to job [\#1843](https://github.com/pypeclub/OpenPype/pull/1843)
- Prepare project action enhance [\#1838](https://github.com/pypeclub/OpenPype/pull/1838)
- nuke: settings create missing default subsets [\#1829](https://github.com/pypeclub/OpenPype/pull/1829)
- Update poetry lock [\#1823](https://github.com/pypeclub/OpenPype/pull/1823)
- Settings: settings for plugins [\#1819](https://github.com/pypeclub/OpenPype/pull/1819)
- Settings list can use template or schema as object type [\#1815](https://github.com/pypeclub/OpenPype/pull/1815)
- Maya: Deadline custom settings  [\#1797](https://github.com/pypeclub/OpenPype/pull/1797)
- Maya: Shader name validation [\#1762](https://github.com/pypeclub/OpenPype/pull/1762)

**🐛 Bug fixes**

- Fix - ftrack family was added incorrectly in some cases [\#1935](https://github.com/pypeclub/OpenPype/pull/1935)
- Fix - Deadline publish on Linux started Tray instead of headless publishing [\#1930](https://github.com/pypeclub/OpenPype/pull/1930)
- Maya: Validate Model Name - repair accident deletion in settings defaults [\#1929](https://github.com/pypeclub/OpenPype/pull/1929)
- Nuke: submit to farm failed due `ftrack` family remove [\#1926](https://github.com/pypeclub/OpenPype/pull/1926)
- Fix - validate takes repre\["files"\] as list all the time [\#1922](https://github.com/pypeclub/OpenPype/pull/1922)
- standalone: validator asset parents [\#1917](https://github.com/pypeclub/OpenPype/pull/1917)
- Nuke: update video file crassing [\#1916](https://github.com/pypeclub/OpenPype/pull/1916)
- Fix - texture validators for workfiles triggers only for textures workfiles [\#1914](https://github.com/pypeclub/OpenPype/pull/1914)
- Settings UI: List order works as expected [\#1906](https://github.com/pypeclub/OpenPype/pull/1906)
- Hiero: loaded clip was not set colorspace from version data [\#1904](https://github.com/pypeclub/OpenPype/pull/1904)
- Pyblish UI: Fix collecting stage processing [\#1903](https://github.com/pypeclub/OpenPype/pull/1903)
- Burnins: Use input's bitrate in h624 [\#1902](https://github.com/pypeclub/OpenPype/pull/1902)
- Bug: fixed python detection [\#1893](https://github.com/pypeclub/OpenPype/pull/1893)
- global: integrate name missing default template [\#1890](https://github.com/pypeclub/OpenPype/pull/1890)
- publisher: editorial plugins fixes [\#1889](https://github.com/pypeclub/OpenPype/pull/1889)
- Normalize path returned from Workfiles. [\#1880](https://github.com/pypeclub/OpenPype/pull/1880)
- Workfiles tool event arguments fix [\#1862](https://github.com/pypeclub/OpenPype/pull/1862)
- imageio: fix grouping  [\#1856](https://github.com/pypeclub/OpenPype/pull/1856)
- Maya: don't add reference members as connections to the container set 📦 [\#1855](https://github.com/pypeclub/OpenPype/pull/1855)
- publisher: missing version in subset prop [\#1849](https://github.com/pypeclub/OpenPype/pull/1849)
- Ftrack type error fix in sync to avalon event handler [\#1845](https://github.com/pypeclub/OpenPype/pull/1845)
- Nuke: updating effects subset fail [\#1841](https://github.com/pypeclub/OpenPype/pull/1841)
- nuke: write render node skipped with crop [\#1836](https://github.com/pypeclub/OpenPype/pull/1836)
- Project folder structure overrides [\#1813](https://github.com/pypeclub/OpenPype/pull/1813)
- Maya: fix yeti settings path in extractor [\#1809](https://github.com/pypeclub/OpenPype/pull/1809)
- Failsafe for cross project containers. [\#1806](https://github.com/pypeclub/OpenPype/pull/1806)
- Houdini colector formatting keys fix [\#1802](https://github.com/pypeclub/OpenPype/pull/1802)
- Settings error dialog on show [\#1798](https://github.com/pypeclub/OpenPype/pull/1798)
- Application launch stdout/stderr in GUI build [\#1684](https://github.com/pypeclub/OpenPype/pull/1684)
- Nuke: re-use instance nodes output path [\#1577](https://github.com/pypeclub/OpenPype/pull/1577)

**Merged pull requests:**

- Fix - make AE workfile publish to Ftrack configurable [\#1937](https://github.com/pypeclub/OpenPype/pull/1937)
- Add support for multiple Deadline ☠️➖ servers [\#1905](https://github.com/pypeclub/OpenPype/pull/1905)
- Maya: add support for `RedshiftNormalMap` node, fix `tx` linear space 🚀 [\#1863](https://github.com/pypeclub/OpenPype/pull/1863)
- Maya: expected files -\> render products ⚙️ overhaul [\#1812](https://github.com/pypeclub/OpenPype/pull/1812)
- PS, AE - send actual context when another webserver is running [\#1811](https://github.com/pypeclub/OpenPype/pull/1811)

## [3.2.0](https://github.com/pypeclub/OpenPype/tree/3.2.0) (2021-07-13)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/2.18.4...3.2.0)

### 📖 Documentation

- Fix: staging and `--use-version` option [\#1786](https://github.com/pypeclub/OpenPype/pull/1786)
- Subset template and TVPaint subset template docs [\#1717](https://github.com/pypeclub/OpenPype/pull/1717)
- Overscan color extract review [\#1701](https://github.com/pypeclub/OpenPype/pull/1701)

**🚀 Enhancements**

- Nuke: ftrack family plugin settings preset [\#1805](https://github.com/pypeclub/OpenPype/pull/1805)
- Standalone publisher last project [\#1799](https://github.com/pypeclub/OpenPype/pull/1799)
- Ftrack Multiple notes as server action [\#1795](https://github.com/pypeclub/OpenPype/pull/1795)
- Settings conditional dict [\#1777](https://github.com/pypeclub/OpenPype/pull/1777)
- Settings application use python 2 only where needed [\#1776](https://github.com/pypeclub/OpenPype/pull/1776)
- Settings UI copy/paste [\#1769](https://github.com/pypeclub/OpenPype/pull/1769)
- Workfile tool widths [\#1766](https://github.com/pypeclub/OpenPype/pull/1766)
- Push hierarchical attributes care about task parent changes [\#1763](https://github.com/pypeclub/OpenPype/pull/1763)
- Application executables with environment variables [\#1757](https://github.com/pypeclub/OpenPype/pull/1757)
- Deadline: Nuke submission additional attributes [\#1756](https://github.com/pypeclub/OpenPype/pull/1756)
- Settings schema without prefill [\#1753](https://github.com/pypeclub/OpenPype/pull/1753)
- Settings Hosts enum [\#1739](https://github.com/pypeclub/OpenPype/pull/1739)
- Validate containers settings [\#1736](https://github.com/pypeclub/OpenPype/pull/1736)
- PS - added loader from sequence [\#1726](https://github.com/pypeclub/OpenPype/pull/1726)
- Autoupdate launcher [\#1725](https://github.com/pypeclub/OpenPype/pull/1725)
- Toggle Ftrack upload in StandalonePublisher [\#1708](https://github.com/pypeclub/OpenPype/pull/1708)
- Nuke: Prerender Frame Range by default [\#1699](https://github.com/pypeclub/OpenPype/pull/1699)
- Smoother edges of color triangle [\#1695](https://github.com/pypeclub/OpenPype/pull/1695)

**🐛 Bug fixes**

- nuke: fixing wrong name of family folder when `used existing frames` [\#1803](https://github.com/pypeclub/OpenPype/pull/1803)
- Collect ftrack family bugs [\#1801](https://github.com/pypeclub/OpenPype/pull/1801)
- Invitee email can be None which break the Ftrack commit. [\#1788](https://github.com/pypeclub/OpenPype/pull/1788)
- Otio unrelated error on import [\#1782](https://github.com/pypeclub/OpenPype/pull/1782)
- FFprobe streams order [\#1775](https://github.com/pypeclub/OpenPype/pull/1775)
- Fix - single file files are str only, cast it to list to count properly [\#1772](https://github.com/pypeclub/OpenPype/pull/1772)
- Environments in app executable for MacOS [\#1768](https://github.com/pypeclub/OpenPype/pull/1768)
- Project specific environments [\#1767](https://github.com/pypeclub/OpenPype/pull/1767)
- Settings UI with refresh button [\#1764](https://github.com/pypeclub/OpenPype/pull/1764)
- Standalone publisher thumbnail extractor fix [\#1761](https://github.com/pypeclub/OpenPype/pull/1761)
- Anatomy others templates don't cause crash [\#1758](https://github.com/pypeclub/OpenPype/pull/1758)
- Backend acre module commit update [\#1745](https://github.com/pypeclub/OpenPype/pull/1745)
- hiero: precollect instances failing when audio selected [\#1743](https://github.com/pypeclub/OpenPype/pull/1743)
- Hiero: creator instance error [\#1742](https://github.com/pypeclub/OpenPype/pull/1742)
- Nuke: fixing render creator for no selection format failing [\#1741](https://github.com/pypeclub/OpenPype/pull/1741)
- StandalonePublisher: failing collector for editorial [\#1738](https://github.com/pypeclub/OpenPype/pull/1738)
- Local settings UI crash on missing defaults [\#1737](https://github.com/pypeclub/OpenPype/pull/1737)
- TVPaint white background on thumbnail [\#1735](https://github.com/pypeclub/OpenPype/pull/1735)
- Ftrack missing custom attribute message [\#1734](https://github.com/pypeclub/OpenPype/pull/1734)
- Launcher project changes [\#1733](https://github.com/pypeclub/OpenPype/pull/1733)
- Ftrack sync status [\#1732](https://github.com/pypeclub/OpenPype/pull/1732)
- TVPaint use layer name for default variant [\#1724](https://github.com/pypeclub/OpenPype/pull/1724)
- Default subset template for TVPaint review and workfile families [\#1716](https://github.com/pypeclub/OpenPype/pull/1716)
- Maya: Extract review hotfix [\#1714](https://github.com/pypeclub/OpenPype/pull/1714)
- Settings: Imageio improving granularity [\#1711](https://github.com/pypeclub/OpenPype/pull/1711)
- Application without executables [\#1679](https://github.com/pypeclub/OpenPype/pull/1679)
- Unreal: launching on Linux [\#1672](https://github.com/pypeclub/OpenPype/pull/1672)

**Merged pull requests:**

- Bump prismjs from 1.23.0 to 1.24.0 in /website [\#1773](https://github.com/pypeclub/OpenPype/pull/1773)
- TVPaint ftrack family [\#1755](https://github.com/pypeclub/OpenPype/pull/1755)

## [2.18.4](https://github.com/pypeclub/OpenPype/tree/2.18.4) (2021-06-24)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/2.18.3...2.18.4)

## [2.18.3](https://github.com/pypeclub/OpenPype/tree/2.18.3) (2021-06-23)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/2.18.2...2.18.3)

## [2.18.2](https://github.com/pypeclub/OpenPype/tree/2.18.2) (2021-06-16)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.1.0...2.18.2)

## [3.1.0](https://github.com/pypeclub/OpenPype/tree/3.1.0) (2021-06-15)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.0.0...3.1.0)

### 📖 Documentation

- Feature Slack integration [\#1657](https://github.com/pypeclub/OpenPype/pull/1657)

**🚀 Enhancements**

- Log Viewer with OpenPype style [\#1703](https://github.com/pypeclub/OpenPype/pull/1703)
- Scrolling in OpenPype info widget [\#1702](https://github.com/pypeclub/OpenPype/pull/1702)
- OpenPype style in modules [\#1694](https://github.com/pypeclub/OpenPype/pull/1694)
- Sort applications and tools alphabetically in Settings UI [\#1689](https://github.com/pypeclub/OpenPype/pull/1689)
- \#683 - Validate Frame Range in Standalone Publisher [\#1683](https://github.com/pypeclub/OpenPype/pull/1683)
- Hiero: old container versions identify with red color [\#1682](https://github.com/pypeclub/OpenPype/pull/1682)
- Project Manger: Default name column width [\#1669](https://github.com/pypeclub/OpenPype/pull/1669)
- Remove outline in stylesheet [\#1667](https://github.com/pypeclub/OpenPype/pull/1667)
- TVPaint: Creator take layer name as default value for subset variant [\#1663](https://github.com/pypeclub/OpenPype/pull/1663)
- TVPaint custom subset template [\#1662](https://github.com/pypeclub/OpenPype/pull/1662)
- Editorial: conform assets validator [\#1659](https://github.com/pypeclub/OpenPype/pull/1659)
- Nuke - Publish simplification [\#1653](https://github.com/pypeclub/OpenPype/pull/1653)
- \#1333 - added tooltip hints to Pyblish buttons [\#1649](https://github.com/pypeclub/OpenPype/pull/1649)

**🐛 Bug fixes**

- Nuke: broken publishing rendered frames [\#1707](https://github.com/pypeclub/OpenPype/pull/1707)
- Standalone publisher Thumbnail export args [\#1705](https://github.com/pypeclub/OpenPype/pull/1705)
- Bad zip can break OpenPype start [\#1691](https://github.com/pypeclub/OpenPype/pull/1691)
- Hiero: published whole edit mov [\#1687](https://github.com/pypeclub/OpenPype/pull/1687)
- Ftrack subprocess handle of stdout/stderr [\#1675](https://github.com/pypeclub/OpenPype/pull/1675)
- Settings list race condifiton and mutable dict list conversion [\#1671](https://github.com/pypeclub/OpenPype/pull/1671)
- Mac launch arguments fix [\#1660](https://github.com/pypeclub/OpenPype/pull/1660)
- Fix missing dbm python module [\#1652](https://github.com/pypeclub/OpenPype/pull/1652)
- Transparent branches in view on Mac [\#1648](https://github.com/pypeclub/OpenPype/pull/1648)
- Add asset on task item [\#1646](https://github.com/pypeclub/OpenPype/pull/1646)
- Project manager save and queue [\#1645](https://github.com/pypeclub/OpenPype/pull/1645)
- New project anatomy values [\#1644](https://github.com/pypeclub/OpenPype/pull/1644)
- Farm publishing: check if published items do exist [\#1573](https://github.com/pypeclub/OpenPype/pull/1573)

**Merged pull requests:**

- Bump normalize-url from 4.5.0 to 4.5.1 in /website [\#1686](https://github.com/pypeclub/OpenPype/pull/1686)


## [3.0.0](https://github.com/pypeclub/openpype/tree/3.0.0)

[Full Changelog](https://github.com/pypeclub/openpype/compare/2.18.1...3.0.0)

### Configuration
- Studio Settings GUI: no more json configuration files.
- OpenPype Modules can be turned on and off.
- Easy to add Application versions.
- Per Project Environment and plugin management.
- Robust profile system for creating reviewables and burnins, with filtering based on Application, Task and data family.
- Configurable publish plugins.
- Options to make any validator or extractor, optional or disabled.
- Color Management is now unified under anatomy settings.
- Subset naming and grouping is fully configurable.
- All project attributes can now be set directly in OpenPype settings.
- Studio Setting can be locked to prevent unwanted artist changes.
- You can now add per project and per task type templates for workfile initialization in most hosts.
- Too many other individual configurable option to list in this changelog :)

### Local Settings
- Local Settings GUI where users can change certain option on individual basis.
    - Application executables.
    - Project roots.
    - Project site sync settings.

### Build, Installation and Deployments
- No requirements on artist machine.
- Fully distributed workflow possible.
- Self-contained installation.
- Available on all three major platforms.
- Automatic artist OpenPype updates.
- Studio OpenPype repository for updates distribution.
- Robust Build system.
- Safe studio update versioning with staging and production options.
- MacOS build generates .app and .dmg installer.
- Windows build with installer creation script.

### Misc
- System and diagnostic info tool in the tray.
- Launching application from Launcher indicates activity.
- All project roots are now named. Single root project are now achieved by having a single named root in the project anatomy.
- Every project root is cast into environment variable as well, so it can be used in DCC instead of absolute path (depends on DCC support for env vars).
- Basic support for task types, on top of task names.
- Timer now change automatically when the context is switched inside running application.
- 'Master" versions have been renamed to "Hero".
- Extract Burnins now supports file sequences and color settings.
- Extract Review support overscan cropping, better letterboxes and background colour fill.
- Delivery tool for copying and renaming any published assets in bulk.
- Harmony, Photoshop and After Effects now connect directly with OpenPype tray instead of spawning their own terminal.

### Project Manager GUI
- Create Projects.
- Create Shots and Assets.
- Create Tasks and assign task types.
- Fill required asset attributes.
- Validations for duplicated or unsupported names.
- Archive Assets.
- Move Asset within hierarchy.

### Site Sync (beta)
- Synchronization of published files between workstations and central storage.
- Ability to add arbitrary storage providers to the Site Sync system.
- Default setup includes Disk and Google Drive providers as examples.
- Access to availability information from Loader and Scene Manager.
- Sync queue GUI with filtering, error and status reporting.
- Site sync can be configured on a per-project basis.
- Bulk upload and download from the loader.

### Ftrack
- Actions have customisable roles.
- Settings on all actions are updated live and don't need openpype restart.
- Ftrack module can now be turned off completely.
- It is enough to specify ftrack server name and the URL will be formed correctly. So instead of mystudio.ftrackapp.com, it's possible to use simply: "mystudio".

### Editorial
- Fully OTIO based editorial publishing.
- Completely re-done Hiero publishing to be a lot simpler and faster.
- Consistent conforming from Resolve, Hiero and Standalone Publisher.

### Backend
- OpenPype and Avalon now always share the same database (in 2.x is was possible to split them).
- Major codebase refactoring to allow for better CI, versioning and control of individual integrations.
- OTIO is bundled with build.
- OIIO is bundled with build.
- FFMPEG is bundled with build.
- Rest API and host WebSocket servers have been unified into a single local webserver.
- Maya look assigner has been integrated into the main codebase.
- Publish GUI has been integrated into the main codebase.
- Studio and Project settings overrides are now stored in Mongo.
- Too many other backend fixes and tweaks to list :), you can see full changelog on github for those.
- OpenPype uses Poetry to manage it's virtual environment when running from code.
- all applications can be marked as python 2 or 3 compatible to make the switch a bit easier.


### Pull Requests since 3.0.0-rc.6


**Implemented enhancements:**

- settings: task types enum entity [\#1605](https://github.com/pypeclub/OpenPype/issues/1605)
- Settings: ignore keys in referenced schema [\#1600](https://github.com/pypeclub/OpenPype/issues/1600)
- Maya: support for frame steps and frame lists [\#1585](https://github.com/pypeclub/OpenPype/issues/1585)
- TVPaint: Publish workfile. [\#1548](https://github.com/pypeclub/OpenPype/issues/1548)
- Loader: Current Asset Button [\#1448](https://github.com/pypeclub/OpenPype/issues/1448)
- Hiero: publish with retiming [\#1377](https://github.com/pypeclub/OpenPype/issues/1377)
- Ask user to restart after changing global environments in settings [\#910](https://github.com/pypeclub/OpenPype/issues/910)
- add option to define paht to workfile template [\#895](https://github.com/pypeclub/OpenPype/issues/895)
- Harmony: move server console to system tray [\#676](https://github.com/pypeclub/OpenPype/issues/676)
- Standalone style [\#1630](https://github.com/pypeclub/OpenPype/pull/1630) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Faster hierarchical values push [\#1627](https://github.com/pypeclub/OpenPype/pull/1627) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Launcher tool style [\#1624](https://github.com/pypeclub/OpenPype/pull/1624) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Loader and Library loader enhancements [\#1623](https://github.com/pypeclub/OpenPype/pull/1623) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Tray style [\#1622](https://github.com/pypeclub/OpenPype/pull/1622) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Maya schemas cleanup [\#1610](https://github.com/pypeclub/OpenPype/pull/1610) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Settings: ignore keys in referenced schema [\#1608](https://github.com/pypeclub/OpenPype/pull/1608) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- settings: task types enum entity [\#1606](https://github.com/pypeclub/OpenPype/pull/1606) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- Openpype style [\#1604](https://github.com/pypeclub/OpenPype/pull/1604) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- TVPaint: Publish workfile. [\#1597](https://github.com/pypeclub/OpenPype/pull/1597) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- Nuke: add option to define path to workfile template [\#1571](https://github.com/pypeclub/OpenPype/pull/1571) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- Crop overscan in Extract Review [\#1569](https://github.com/pypeclub/OpenPype/pull/1569) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Unreal and Blender: Material Workflow [\#1562](https://github.com/pypeclub/OpenPype/pull/1562) ([simonebarbieri](https://github.com/simonebarbieri))
- Harmony: move server console to system tray [\#1560](https://github.com/pypeclub/OpenPype/pull/1560) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- Ask user to restart after changing global environments in settings [\#1550](https://github.com/pypeclub/OpenPype/pull/1550) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- Hiero: publish with retiming [\#1545](https://github.com/pypeclub/OpenPype/pull/1545) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))

**Fixed bugs:**

- Library loader load asset documents on OpenPype start [\#1603](https://github.com/pypeclub/OpenPype/issues/1603)
- Resolve: unable to load the same footage twice [\#1317](https://github.com/pypeclub/OpenPype/issues/1317)
- Resolve: unable to load footage [\#1316](https://github.com/pypeclub/OpenPype/issues/1316)
- Add required Python 2 modules [\#1291](https://github.com/pypeclub/OpenPype/issues/1291)
- GUi scaling with hires displays [\#705](https://github.com/pypeclub/OpenPype/issues/705)
- Maya: non unicode string in publish validation [\#673](https://github.com/pypeclub/OpenPype/issues/673)
- Nuke: Rendered Frame validation is triggered by multiple collections [\#156](https://github.com/pypeclub/OpenPype/issues/156)
- avalon-core debugging failing [\#80](https://github.com/pypeclub/OpenPype/issues/80)
- Only check arnold shading group if arnold is used [\#72](https://github.com/pypeclub/OpenPype/issues/72)
- Sync server Qt layout fix [\#1621](https://github.com/pypeclub/OpenPype/pull/1621) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Console Listener on Python 2 fix [\#1620](https://github.com/pypeclub/OpenPype/pull/1620) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Bug: Initialize blessed term only in console mode [\#1619](https://github.com/pypeclub/OpenPype/pull/1619) ([antirotor](https://github.com/antirotor))
- Settings template skip paths support wrappers [\#1618](https://github.com/pypeclub/OpenPype/pull/1618) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Maya capture 'isolate\_view' fix + minor corrections [\#1617](https://github.com/pypeclub/OpenPype/pull/1617) ([2-REC](https://github.com/2-REC))
- MacOs Fix launch of standalone publisher [\#1616](https://github.com/pypeclub/OpenPype/pull/1616) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- 'Delivery action' report fix + typos [\#1612](https://github.com/pypeclub/OpenPype/pull/1612) ([2-REC](https://github.com/2-REC))
- List append fix in mutable dict settings [\#1599](https://github.com/pypeclub/OpenPype/pull/1599) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Documentation: Maya: fix review [\#1598](https://github.com/pypeclub/OpenPype/pull/1598) ([antirotor](https://github.com/antirotor))
- Bugfix: Set certifi CA bundle for all platforms [\#1596](https://github.com/pypeclub/OpenPype/pull/1596) ([antirotor](https://github.com/antirotor))

**Merged pull requests:**

- Bump dns-packet from 1.3.1 to 1.3.4 in /website [\#1611](https://github.com/pypeclub/OpenPype/pull/1611) ([dependabot[bot]](https://github.com/apps/dependabot))
- Maya: Render workflow fixes [\#1607](https://github.com/pypeclub/OpenPype/pull/1607) ([antirotor](https://github.com/antirotor))
- Maya: support for frame steps and frame lists [\#1586](https://github.com/pypeclub/OpenPype/pull/1586) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- 3.0.0 - curated changelog [\#1284](https://github.com/pypeclub/OpenPype/pull/1284) ([mkolar](https://github.com/mkolar))

## [2.18.1](https://github.com/pypeclub/openpype/tree/2.18.1) (2021-06-03)

[Full Changelog](https://github.com/pypeclub/openpype/compare/2.18.0...2.18.1)

**Enhancements:**

- Faster hierarchical values push [\#1626](https://github.com/pypeclub/OpenPype/pull/1626)
- Feature Delivery in library loader [\#1549](https://github.com/pypeclub/OpenPype/pull/1549)
- Hiero: Initial frame publish support. [\#1172](https://github.com/pypeclub/OpenPype/pull/1172)

**Fixed bugs:**

- Maya capture 'isolate\_view' fix + minor corrections [\#1614](https://github.com/pypeclub/OpenPype/pull/1614)
- 'Delivery action' report fix +typos [\#1613](https://github.com/pypeclub/OpenPype/pull/1613)
- Delivery in LibraryLoader - fixed sequence issue [\#1590](https://github.com/pypeclub/OpenPype/pull/1590)
- FFmpeg filters in quote marks [\#1588](https://github.com/pypeclub/OpenPype/pull/1588)
- Ftrack delete action cause circular error [\#1581](https://github.com/pypeclub/OpenPype/pull/1581)
- Fix Maya playblast. [\#1566](https://github.com/pypeclub/OpenPype/pull/1566)
- More failsafes prevent errored runs. [\#1554](https://github.com/pypeclub/OpenPype/pull/1554)
- Celaction publishing [\#1539](https://github.com/pypeclub/OpenPype/pull/1539)
- celaction: app not starting [\#1533](https://github.com/pypeclub/OpenPype/pull/1533)

**Merged pull requests:**

- Maya: Render workflow fixes - 2.0 backport [\#1609](https://github.com/pypeclub/OpenPype/pull/1609)
- Maya Hardware support [\#1553](https://github.com/pypeclub/OpenPype/pull/1553)


## [CI/3.0.0-rc.6](https://github.com/pypeclub/openpype/tree/CI/3.0.0-rc.6) (2021-05-27)

[Full Changelog](https://github.com/pypeclub/openpype/compare/CI/3.0.0-rc.5...CI/3.0.0-rc.6)

**Implemented enhancements:**

- Hiero: publish color and transformation soft-effects [\#1376](https://github.com/pypeclub/OpenPype/issues/1376)
- Get rid of `AVALON\_HIERARCHY` and `hiearchy` key on asset [\#432](https://github.com/pypeclub/OpenPype/issues/432)
- Sync to avalon do not store hierarchy key [\#1582](https://github.com/pypeclub/OpenPype/pull/1582) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Tools: launcher scripts for project manager [\#1557](https://github.com/pypeclub/OpenPype/pull/1557) ([antirotor](https://github.com/antirotor))
- Simple tvpaint publish [\#1555](https://github.com/pypeclub/OpenPype/pull/1555) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Feature Delivery in library loader [\#1546](https://github.com/pypeclub/OpenPype/pull/1546) ([kalisp](https://github.com/kalisp))
- Documentation: Dev and system build documentation [\#1543](https://github.com/pypeclub/OpenPype/pull/1543) ([antirotor](https://github.com/antirotor))
- Color entity [\#1542](https://github.com/pypeclub/OpenPype/pull/1542) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Extract review bg color [\#1534](https://github.com/pypeclub/OpenPype/pull/1534) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- TVPaint loader settings [\#1530](https://github.com/pypeclub/OpenPype/pull/1530) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Blender can initialize differente user script paths [\#1528](https://github.com/pypeclub/OpenPype/pull/1528) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Blender and Unreal: Improved Animation Workflow [\#1514](https://github.com/pypeclub/OpenPype/pull/1514) ([simonebarbieri](https://github.com/simonebarbieri))
- Hiero: publish color and transformation soft-effects [\#1511](https://github.com/pypeclub/OpenPype/pull/1511) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))

**Fixed bugs:**

- OpenPype specific version issues [\#1583](https://github.com/pypeclub/OpenPype/issues/1583)
- Ftrack login server can't work without stderr [\#1576](https://github.com/pypeclub/OpenPype/issues/1576)
- Mac application launch [\#1575](https://github.com/pypeclub/OpenPype/issues/1575)
- Settings are not propagated to Nuke write nodes [\#1538](https://github.com/pypeclub/OpenPype/issues/1538)
- Subset names settings not applied for publishing [\#1537](https://github.com/pypeclub/OpenPype/issues/1537)
- Nuke: callback at start not setting colorspace [\#1412](https://github.com/pypeclub/OpenPype/issues/1412)
- Pype 3: Missing icon for Settings [\#1272](https://github.com/pypeclub/OpenPype/issues/1272)
- Blender: cannot initialize Avalon if BLENDER\_USER\_SCRIPTS is already used [\#1050](https://github.com/pypeclub/OpenPype/issues/1050)
- Ftrack delete action cause circular error [\#206](https://github.com/pypeclub/OpenPype/issues/206)
- Build: stop cleaning of pyc files in build directory [\#1592](https://github.com/pypeclub/OpenPype/pull/1592) ([antirotor](https://github.com/antirotor))
- Ftrack login server can't work without stderr [\#1591](https://github.com/pypeclub/OpenPype/pull/1591) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- FFmpeg filters in quote marks [\#1589](https://github.com/pypeclub/OpenPype/pull/1589) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- OpenPype specific version issues [\#1584](https://github.com/pypeclub/OpenPype/pull/1584) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- Mac application launch [\#1580](https://github.com/pypeclub/OpenPype/pull/1580) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- Ftrack delete action cause circular error [\#1579](https://github.com/pypeclub/OpenPype/pull/1579) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Hiero: publishing issues  [\#1578](https://github.com/pypeclub/OpenPype/pull/1578) ([jezscha](https://github.com/jezscha))
- Nuke: callback at start not setting colorspace [\#1561](https://github.com/pypeclub/OpenPype/pull/1561) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- Bugfix  PS subset and quick review [\#1541](https://github.com/pypeclub/OpenPype/pull/1541) ([kalisp](https://github.com/kalisp))
- Settings are not propagated to Nuke write nodes [\#1540](https://github.com/pypeclub/OpenPype/pull/1540) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- OpenPype: Powershell scripts polishing [\#1536](https://github.com/pypeclub/OpenPype/pull/1536) ([antirotor](https://github.com/antirotor))
- Host name collecting fix [\#1535](https://github.com/pypeclub/OpenPype/pull/1535) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Handle duplicated task names in project manager [\#1531](https://github.com/pypeclub/OpenPype/pull/1531) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Validate is file attribute in settings schema [\#1529](https://github.com/pypeclub/OpenPype/pull/1529) ([iLLiCiTiT](https://github.com/iLLiCiTiT))

**Merged pull requests:**

- Bump postcss from 8.2.8 to 8.3.0 in /website [\#1593](https://github.com/pypeclub/OpenPype/pull/1593) ([dependabot[bot]](https://github.com/apps/dependabot))
- User installation documentation [\#1532](https://github.com/pypeclub/OpenPype/pull/1532) ([64qam](https://github.com/64qam))

## [CI/3.0.0-rc.5](https://github.com/pypeclub/openpype/tree/CI/3.0.0-rc.5) (2021-05-19)

[Full Changelog](https://github.com/pypeclub/openpype/compare/2.18.0...CI/3.0.0-rc.5)

**Implemented enhancements:**

- OpenPype: Build - Add progress bars [\#1524](https://github.com/pypeclub/OpenPype/pull/1524) ([antirotor](https://github.com/antirotor))
- Default environments per host imlementation [\#1522](https://github.com/pypeclub/OpenPype/pull/1522) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- OpenPype: use `semver` module for version resolution [\#1513](https://github.com/pypeclub/OpenPype/pull/1513) ([antirotor](https://github.com/antirotor))
- Feature Aftereffects setting cleanup documentation [\#1510](https://github.com/pypeclub/OpenPype/pull/1510) ([kalisp](https://github.com/kalisp))
- Feature Sync server settings enhancement [\#1501](https://github.com/pypeclub/OpenPype/pull/1501) ([kalisp](https://github.com/kalisp))
- Project manager [\#1396](https://github.com/pypeclub/OpenPype/pull/1396) ([iLLiCiTiT](https://github.com/iLLiCiTiT))

**Fixed bugs:**

- Unified schema definition [\#874](https://github.com/pypeclub/OpenPype/issues/874)
- Maya: fix look assignment [\#1526](https://github.com/pypeclub/OpenPype/pull/1526) ([antirotor](https://github.com/antirotor))
- Bugfix Sync server local site issues [\#1523](https://github.com/pypeclub/OpenPype/pull/1523) ([kalisp](https://github.com/kalisp))
- Store as list dictionary check initial value with right type [\#1520](https://github.com/pypeclub/OpenPype/pull/1520) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Maya: wrong collection of playblasted frames [\#1515](https://github.com/pypeclub/OpenPype/pull/1515) ([mkolar](https://github.com/mkolar))
- Convert pyblish logs to string at the moment of logging [\#1512](https://github.com/pypeclub/OpenPype/pull/1512) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- 3.0 | nuke: fixing start\_at with option gui [\#1509](https://github.com/pypeclub/OpenPype/pull/1509) ([jezscha](https://github.com/jezscha))
- Tests: fix pype -\> openpype to make tests work again [\#1508](https://github.com/pypeclub/OpenPype/pull/1508) ([antirotor](https://github.com/antirotor))

**Merged pull requests:**

- OpenPype: disable submodule update with `--no-submodule-update` [\#1525](https://github.com/pypeclub/OpenPype/pull/1525) ([antirotor](https://github.com/antirotor))
- Ftrack without autosync in Pype 3 [\#1519](https://github.com/pypeclub/OpenPype/pull/1519) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- Feature Harmony setting cleanup documentation [\#1506](https://github.com/pypeclub/OpenPype/pull/1506) ([kalisp](https://github.com/kalisp))
- Sync Server beginning of documentation [\#1471](https://github.com/pypeclub/OpenPype/pull/1471) ([kalisp](https://github.com/kalisp))
- Blender: publish layout json [\#1348](https://github.com/pypeclub/OpenPype/pull/1348) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))

## [2.18.0](https://github.com/pypeclub/openpype/tree/2.18.0) (2021-05-18)

[Full Changelog](https://github.com/pypeclub/openpype/compare/CI/3.0.0-rc.4...2.18.0)

**Implemented enhancements:**

- Default environments per host imlementation [\#1405](https://github.com/pypeclub/OpenPype/issues/1405)
- Blender: publish layout json [\#1346](https://github.com/pypeclub/OpenPype/issues/1346)
- Ftrack without autosync in Pype 3 [\#1128](https://github.com/pypeclub/OpenPype/issues/1128)
- Launcher: started action indicator [\#1102](https://github.com/pypeclub/OpenPype/issues/1102)
- Launch arguments of applications [\#1094](https://github.com/pypeclub/OpenPype/issues/1094)
- Publish: instance info [\#724](https://github.com/pypeclub/OpenPype/issues/724)
- Review: ability to control review length [\#482](https://github.com/pypeclub/OpenPype/issues/482)
- Colorized recognition of creator result [\#394](https://github.com/pypeclub/OpenPype/issues/394)
- event assign user to started task [\#49](https://github.com/pypeclub/OpenPype/issues/49)
- rebuild containers from reference in maya [\#55](https://github.com/pypeclub/OpenPype/issues/55)
- nuke Load metadata [\#66](https://github.com/pypeclub/OpenPype/issues/66)
- Maya: Safer handling of expected render output names [\#1496](https://github.com/pypeclub/OpenPype/pull/1496) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- TVPaint: Increment workfile version on successfull publish. [\#1489](https://github.com/pypeclub/OpenPype/pull/1489) ([tokejepsen](https://github.com/tokejepsen))
- Use SubsetLoader and multiple contexts for delete\_old\_versions [\#1484](https://github.com/pypeclub/OpenPype/pull/1484) ([tokejepsen](https://github.com/tokejepsen))
- Maya: Use of multiple deadline servers [\#1483](https://github.com/pypeclub/OpenPype/pull/1483) ([antirotor](https://github.com/antirotor))

**Fixed bugs:**

- Igniter version resolution doesn't consider it's own version [\#1505](https://github.com/pypeclub/OpenPype/issues/1505)
- Maya: Safer handling of expected render output names [\#1159](https://github.com/pypeclub/OpenPype/issues/1159)
- Harmony: Invalid render output from non-conventionally named instance [\#871](https://github.com/pypeclub/OpenPype/issues/871)
- Existing subsets hints in creator [\#1503](https://github.com/pypeclub/OpenPype/pull/1503) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- nuke: space in node name breaking process [\#1494](https://github.com/pypeclub/OpenPype/pull/1494) ([jezscha](https://github.com/jezscha))
-  Maya: wrong collection of playblasted frames [\#1517](https://github.com/pypeclub/OpenPype/pull/1517) ([mkolar](https://github.com/mkolar))
- Existing subsets hints in creator [\#1502](https://github.com/pypeclub/OpenPype/pull/1502) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Use instance frame start instead of timeline. [\#1486](https://github.com/pypeclub/OpenPype/pull/1486) ([tokejepsen](https://github.com/tokejepsen))
- Maya: Redshift - set proper start frame on proxy [\#1480](https://github.com/pypeclub/OpenPype/pull/1480) ([antirotor](https://github.com/antirotor))

**Closed issues:**

- Nuke: wrong "star at" value on render load [\#1352](https://github.com/pypeclub/OpenPype/issues/1352)
- DV Resolve - loading/updating - image video [\#915](https://github.com/pypeclub/OpenPype/issues/915)

**Merged pull requests:**

- nuke: fixing start\_at with option gui [\#1507](https://github.com/pypeclub/OpenPype/pull/1507) ([jezscha](https://github.com/jezscha))

## [CI/3.0.0-rc.4](https://github.com/pypeclub/openpype/tree/CI/3.0.0-rc.4) (2021-05-12)

[Full Changelog](https://github.com/pypeclub/openpype/compare/2.17.3...CI/3.0.0-rc.4)

**Implemented enhancements:**

- Resolve: documentation [\#1490](https://github.com/pypeclub/OpenPype/issues/1490)
- Hiero: audio to review [\#1378](https://github.com/pypeclub/OpenPype/issues/1378)
- nks color clips after publish [\#44](https://github.com/pypeclub/OpenPype/issues/44)
- Store data from modifiable dict as list [\#1504](https://github.com/pypeclub/OpenPype/pull/1504) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Use SubsetLoader and multiple contexts for delete\_old\_versions [\#1497](https://github.com/pypeclub/OpenPype/pull/1497) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Hiero: publish audio and add to review [\#1493](https://github.com/pypeclub/OpenPype/pull/1493) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- Resolve: documentation [\#1491](https://github.com/pypeclub/OpenPype/pull/1491) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- Change integratenew template profiles setting [\#1487](https://github.com/pypeclub/OpenPype/pull/1487) ([kalisp](https://github.com/kalisp))
- Settings tool cleanup [\#1477](https://github.com/pypeclub/OpenPype/pull/1477) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Sorted Applications and Tools in Custom attribute [\#1476](https://github.com/pypeclub/OpenPype/pull/1476) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- PS - group all published instances [\#1416](https://github.com/pypeclub/OpenPype/pull/1416) ([kalisp](https://github.com/kalisp))
- OpenPype: Support for Docker [\#1289](https://github.com/pypeclub/OpenPype/pull/1289) ([antirotor](https://github.com/antirotor))

**Fixed bugs:**

- Harmony: palettes publishing [\#1439](https://github.com/pypeclub/OpenPype/issues/1439)
- Photoshop: validation for already created images [\#1435](https://github.com/pypeclub/OpenPype/issues/1435)
- Nuke Extracts Thumbnail from frame out of shot range [\#963](https://github.com/pypeclub/OpenPype/issues/963)
- Instance in same Context repairing [\#390](https://github.com/pypeclub/OpenPype/issues/390)
- User Inactivity - Start timers sets wrong time [\#91](https://github.com/pypeclub/OpenPype/issues/91)
- Use instance frame start instead of timeline [\#1499](https://github.com/pypeclub/OpenPype/pull/1499) ([mkolar](https://github.com/mkolar))
- Various smaller fixes [\#1498](https://github.com/pypeclub/OpenPype/pull/1498) ([mkolar](https://github.com/mkolar))
- nuke: space in node name breaking process [\#1495](https://github.com/pypeclub/OpenPype/pull/1495) ([jezscha](https://github.com/jezscha))
- Codec determination in extract burnin [\#1492](https://github.com/pypeclub/OpenPype/pull/1492) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Undefined constant in subprocess module [\#1485](https://github.com/pypeclub/OpenPype/pull/1485) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- List entity catch add/remove item changes properly [\#1482](https://github.com/pypeclub/OpenPype/pull/1482) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Resolve: additional fixes of publishing workflow [\#1481](https://github.com/pypeclub/OpenPype/pull/1481) ([jezscha](https://github.com/jezscha))
- Photoshop: validation for already created images [\#1436](https://github.com/pypeclub/OpenPype/pull/1436) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))

**Merged pull requests:**

- Maya: Support for looks on VRay Proxies [\#1443](https://github.com/pypeclub/OpenPype/pull/1443) ([antirotor](https://github.com/antirotor))

## [2.17.3](https://github.com/pypeclub/openpype/tree/2.17.3) (2021-05-06)

[Full Changelog](https://github.com/pypeclub/openpype/compare/CI/3.0.0-rc.3...2.17.3)

**Fixed bugs:**

- Nuke: workfile version synced to db version always  [\#1479](https://github.com/pypeclub/OpenPype/pull/1479) ([jezscha](https://github.com/jezscha))

## [CI/3.0.0-rc.3](https://github.com/pypeclub/openpype/tree/CI/3.0.0-rc.3) (2021-05-05)

[Full Changelog](https://github.com/pypeclub/openpype/compare/CI/3.0.0-rc.2...CI/3.0.0-rc.3)

**Implemented enhancements:**

- Path entity with placeholder [\#1473](https://github.com/pypeclub/OpenPype/pull/1473) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Burnin custom font filepath [\#1472](https://github.com/pypeclub/OpenPype/pull/1472) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Poetry: Move to OpenPype [\#1449](https://github.com/pypeclub/OpenPype/pull/1449) ([antirotor](https://github.com/antirotor))

**Fixed bugs:**

- Mac SSL path needs to be relative to pype\_root [\#1469](https://github.com/pypeclub/OpenPype/issues/1469)
- Resolve: fix loading clips to timeline [\#1421](https://github.com/pypeclub/OpenPype/issues/1421)
- Wrong handling of slashes when loading on mac [\#1411](https://github.com/pypeclub/OpenPype/issues/1411)
- Nuke openpype3 [\#1342](https://github.com/pypeclub/OpenPype/issues/1342)
- Houdini launcher [\#1171](https://github.com/pypeclub/OpenPype/issues/1171)
- Fix SyncServer get\_enabled\_projects should handle global state [\#1475](https://github.com/pypeclub/OpenPype/pull/1475) ([kalisp](https://github.com/kalisp))
- Igniter buttons enable/disable fix [\#1474](https://github.com/pypeclub/OpenPype/pull/1474) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Mac SSL path needs to be relative to pype\_root [\#1470](https://github.com/pypeclub/OpenPype/pull/1470) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- Resolve: 17 compatibility issues and load image sequences [\#1422](https://github.com/pypeclub/OpenPype/pull/1422) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))

## [CI/3.0.0-rc.2](https://github.com/pypeclub/openpype/tree/CI/3.0.0-rc.2) (2021-05-04)

[Full Changelog](https://github.com/pypeclub/openpype/compare/2.17.2...CI/3.0.0-rc.2)

**Implemented enhancements:**

- Extract burnins with sequences [\#1467](https://github.com/pypeclub/OpenPype/pull/1467) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Extract burnins with color setting [\#1466](https://github.com/pypeclub/OpenPype/pull/1466) ([iLLiCiTiT](https://github.com/iLLiCiTiT))

**Fixed bugs:**

- Fix groups check in Python 2 [\#1468](https://github.com/pypeclub/OpenPype/pull/1468) ([iLLiCiTiT](https://github.com/iLLiCiTiT))

## [2.17.2](https://github.com/pypeclub/openpype/tree/2.17.2) (2021-05-04)

[Full Changelog](https://github.com/pypeclub/openpype/compare/CI/3.0.0-rc.1...2.17.2)

**Implemented enhancements:**

- Forward/Backward compatible apps and tools with OpenPype 3 [\#1463](https://github.com/pypeclub/OpenPype/pull/1463) ([iLLiCiTiT](https://github.com/iLLiCiTiT))

## [CI/3.0.0-rc.1](https://github.com/pypeclub/openpype/tree/CI/3.0.0-rc.1) (2021-05-04)

[Full Changelog](https://github.com/pypeclub/openpype/compare/2.17.1...CI/3.0.0-rc.1)

**Implemented enhancements:**

- Only show studio settings to admins [\#1406](https://github.com/pypeclub/OpenPype/issues/1406)
- Ftrack specific settings save warning messages [\#1458](https://github.com/pypeclub/OpenPype/pull/1458) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Faster settings actions [\#1446](https://github.com/pypeclub/OpenPype/pull/1446) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Feature/sync server priority [\#1444](https://github.com/pypeclub/OpenPype/pull/1444) ([kalisp](https://github.com/kalisp))
- Faster settings UI loading [\#1442](https://github.com/pypeclub/OpenPype/pull/1442) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Igniter re-write [\#1441](https://github.com/pypeclub/OpenPype/pull/1441) ([mkolar](https://github.com/mkolar))
- Wrap openpype build into installers [\#1419](https://github.com/pypeclub/OpenPype/pull/1419) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- Extract review first documentation [\#1404](https://github.com/pypeclub/OpenPype/pull/1404) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Blender PySide2 install guide [\#1403](https://github.com/pypeclub/OpenPype/pull/1403) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Nuke: deadline submission with gpu [\#1394](https://github.com/pypeclub/OpenPype/pull/1394) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- Igniter: Reverse item filter for OpenPype version [\#1349](https://github.com/pypeclub/OpenPype/pull/1349) ([antirotor](https://github.com/antirotor))

**Fixed bugs:**

- OpenPype Mongo URL definition [\#1450](https://github.com/pypeclub/OpenPype/issues/1450)
- Various typos and smaller fixes [\#1464](https://github.com/pypeclub/OpenPype/pull/1464) ([mkolar](https://github.com/mkolar))
- Validation of dynamic items in settings [\#1462](https://github.com/pypeclub/OpenPype/pull/1462) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- List can handle new items correctly [\#1459](https://github.com/pypeclub/OpenPype/pull/1459) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Settings actions process fix [\#1457](https://github.com/pypeclub/OpenPype/pull/1457) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Add to overrides actions fix [\#1456](https://github.com/pypeclub/OpenPype/pull/1456) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- OpenPype Mongo URL definition [\#1455](https://github.com/pypeclub/OpenPype/pull/1455) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- Global settings save/load out of system settings [\#1447](https://github.com/pypeclub/OpenPype/pull/1447) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Keep metadata on remove overrides [\#1445](https://github.com/pypeclub/OpenPype/pull/1445) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Nuke: fixing undo for loaded mov and sequence [\#1432](https://github.com/pypeclub/OpenPype/pull/1432) ([jezscha](https://github.com/jezscha))
- ExtractReview skip empty strings from settings [\#1431](https://github.com/pypeclub/OpenPype/pull/1431) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Bugfix Sync server tweaks [\#1430](https://github.com/pypeclub/OpenPype/pull/1430) ([kalisp](https://github.com/kalisp))
- Hiero: missing thumbnail in review [\#1429](https://github.com/pypeclub/OpenPype/pull/1429) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- Bugfix Maya in deadline for OpenPype [\#1428](https://github.com/pypeclub/OpenPype/pull/1428) ([kalisp](https://github.com/kalisp))
- AE - validation for duration was 1 frame shorter [\#1427](https://github.com/pypeclub/OpenPype/pull/1427) ([kalisp](https://github.com/kalisp))
- Houdini menu filename [\#1418](https://github.com/pypeclub/OpenPype/pull/1418) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Fix Avalon plugins attribute overrides [\#1413](https://github.com/pypeclub/OpenPype/pull/1413) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Nuke: submit to Deadline fails [\#1409](https://github.com/pypeclub/OpenPype/pull/1409) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- Validate MongoDB Url on start [\#1407](https://github.com/pypeclub/OpenPype/pull/1407) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Nuke: fix set colorspace with new settings [\#1386](https://github.com/pypeclub/OpenPype/pull/1386) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- MacOs build and install issues [\#1380](https://github.com/pypeclub/OpenPype/pull/1380) ([mkolar](https://github.com/mkolar))

**Closed issues:**

- test [\#1452](https://github.com/pypeclub/OpenPype/issues/1452)

**Merged pull requests:**

- TVPaint frame range definition [\#1425](https://github.com/pypeclub/OpenPype/pull/1425) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Only show studio settings to admins [\#1420](https://github.com/pypeclub/OpenPype/pull/1420) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- TVPaint documentation [\#1305](https://github.com/pypeclub/OpenPype/pull/1305) ([64qam](https://github.com/64qam))

## [2.17.1](https://github.com/pypeclub/openpype/tree/2.17.1) (2021-04-30)

[Full Changelog](https://github.com/pypeclub/openpype/compare/2.17.0...2.17.1)

**Enhancements:**

- Nuke: deadline submission with gpu [\#1414](https://github.com/pypeclub/OpenPype/pull/1414)
- TVPaint frame range definition [\#1424](https://github.com/pypeclub/OpenPype/pull/1424)
- PS - group all published instances [\#1415](https://github.com/pypeclub/OpenPype/pull/1415)
- Add task name to context pop up. [\#1383](https://github.com/pypeclub/OpenPype/pull/1383)
- Enhance review letterbox feature. [\#1371](https://github.com/pypeclub/OpenPype/pull/1371)

**Fixed bugs:**

- Houdini menu filename [\#1417](https://github.com/pypeclub/OpenPype/pull/1417)
- AE - validation for duration was 1 frame shorter [\#1426](https://github.com/pypeclub/OpenPype/pull/1426)

**Merged pull requests:**

- Maya: Vray - problem getting all file nodes for look publishing [\#1399](https://github.com/pypeclub/OpenPype/pull/1399)
- Maya: Support for Redshift proxies [\#1360](https://github.com/pypeclub/OpenPype/pull/1360)

## [2.17.0](https://github.com/pypeclub/openpype/tree/2.17.0) (2021-04-20)

[Full Changelog](https://github.com/pypeclub/openpype/compare/CI/3.0.0-beta.2...2.17.0)

**Enhancements:**

- Forward compatible ftrack group [\#1243](https://github.com/pypeclub/OpenPype/pull/1243)
- Settings in mongo as dict [\#1221](https://github.com/pypeclub/OpenPype/pull/1221)
- Maya: Make tx option configurable with presets [\#1328](https://github.com/pypeclub/OpenPype/pull/1328)
- TVPaint asset name validation [\#1302](https://github.com/pypeclub/OpenPype/pull/1302)
- TV Paint: Set initial project settings. [\#1299](https://github.com/pypeclub/OpenPype/pull/1299)
- TV Paint: Validate mark in and out. [\#1298](https://github.com/pypeclub/OpenPype/pull/1298)
- Validate project settings [\#1297](https://github.com/pypeclub/OpenPype/pull/1297)
- After Effects: added SubsetManager [\#1234](https://github.com/pypeclub/OpenPype/pull/1234)
- Show error message in pyblish UI [\#1206](https://github.com/pypeclub/OpenPype/pull/1206)

**Fixed bugs:**

- Hiero: fixing source frame from correct object [\#1362](https://github.com/pypeclub/OpenPype/pull/1362)
- Nuke: fix colourspace, prerenders and nuke panes opening [\#1308](https://github.com/pypeclub/OpenPype/pull/1308)
- AE remove orphaned instance from workfile - fix self.stub [\#1282](https://github.com/pypeclub/OpenPype/pull/1282)
- Nuke: deadline submission with search replaced env values from preset [\#1194](https://github.com/pypeclub/OpenPype/pull/1194)
- Ftrack custom attributes in bulks [\#1312](https://github.com/pypeclub/OpenPype/pull/1312)
- Ftrack optional pypclub role [\#1303](https://github.com/pypeclub/OpenPype/pull/1303)
- After Effects: remove orphaned instances [\#1275](https://github.com/pypeclub/OpenPype/pull/1275)
- Avalon schema names [\#1242](https://github.com/pypeclub/OpenPype/pull/1242)
- Handle duplication of Task name [\#1226](https://github.com/pypeclub/OpenPype/pull/1226)
- Modified path of plugin loads for Harmony and TVPaint [\#1217](https://github.com/pypeclub/OpenPype/pull/1217)
- Regex checks in profiles filtering [\#1214](https://github.com/pypeclub/OpenPype/pull/1214)
- Bulk mov strict task [\#1204](https://github.com/pypeclub/OpenPype/pull/1204)
- Update custom ftrack session attributes [\#1202](https://github.com/pypeclub/OpenPype/pull/1202)
- Nuke: write node colorspace ignore `default\(\)` label [\#1199](https://github.com/pypeclub/OpenPype/pull/1199)
- Nuke: reverse search to make it more versatile [\#1178](https://github.com/pypeclub/OpenPype/pull/1178)



## [2.16.0](https://github.com/pypeclub/pype/tree/2.16.0) (2021-03-22)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.15.3...2.16.0)

**Enhancements:**

- Nuke: deadline submit limit group filter [\#1167](https://github.com/pypeclub/pype/pull/1167)
- Maya: support for Deadline Group and Limit Groups - backport 2.x [\#1156](https://github.com/pypeclub/pype/pull/1156)
- Maya: fixes for Redshift support [\#1152](https://github.com/pypeclub/pype/pull/1152)
- Nuke: adding preset for a Read node name to all img and mov Loaders [\#1146](https://github.com/pypeclub/pype/pull/1146)
- nuke deadline submit with environ var from presets overrides [\#1142](https://github.com/pypeclub/pype/pull/1142)
- Change timers after task change [\#1138](https://github.com/pypeclub/pype/pull/1138)
- Nuke: shortcuts for Pype menu [\#1127](https://github.com/pypeclub/pype/pull/1127)
- Nuke: workfile template [\#1124](https://github.com/pypeclub/pype/pull/1124)
- Sites local settings by site name [\#1117](https://github.com/pypeclub/pype/pull/1117)
- Reset loader's asset selection on context change [\#1106](https://github.com/pypeclub/pype/pull/1106)
- Bulk mov render publishing [\#1101](https://github.com/pypeclub/pype/pull/1101)
- Photoshop: mark publishable instances [\#1093](https://github.com/pypeclub/pype/pull/1093)
- Added ability to define BG color for extract review [\#1088](https://github.com/pypeclub/pype/pull/1088)
- TVPaint extractor enhancement [\#1080](https://github.com/pypeclub/pype/pull/1080)
- Photoshop: added support for .psb in workfiles [\#1078](https://github.com/pypeclub/pype/pull/1078)
- Optionally add task to subset name [\#1072](https://github.com/pypeclub/pype/pull/1072)
- Only extend clip range when collecting. [\#1008](https://github.com/pypeclub/pype/pull/1008)
- Collect audio for farm reviews. [\#1073](https://github.com/pypeclub/pype/pull/1073)


**Fixed bugs:**

- Fix path spaces in jpeg extractor [\#1174](https://github.com/pypeclub/pype/pull/1174)
- Maya: Bugfix: superclass for CreateCameraRig [\#1166](https://github.com/pypeclub/pype/pull/1166)
- Maya: Submit to Deadline - fix typo in condition [\#1163](https://github.com/pypeclub/pype/pull/1163)
- Avoid dot in repre extension [\#1125](https://github.com/pypeclub/pype/pull/1125)
- Fix versions variable usage in standalone publisher [\#1090](https://github.com/pypeclub/pype/pull/1090)
- Collect instance data fix subset query [\#1082](https://github.com/pypeclub/pype/pull/1082)
- Fix getting the camera name. [\#1067](https://github.com/pypeclub/pype/pull/1067)
- Nuke: Ensure "NUKE\_TEMP\_DIR" is not part of the Deadline job environment. [\#1064](https://github.com/pypeclub/pype/pull/1064)

## [2.15.3](https://github.com/pypeclub/pype/tree/2.15.3) (2021-02-26)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.15.2...2.15.3)

**Enhancements:**

- Maya: speedup renderable camera collection [\#1053](https://github.com/pypeclub/pype/pull/1053)
- Harmony - add regex search to filter allowed task names for collectin… [\#1047](https://github.com/pypeclub/pype/pull/1047)

**Fixed bugs:**

- Ftrack integrate hierarchy fix [\#1085](https://github.com/pypeclub/pype/pull/1085)
- Explicit subset filter in anatomy instance data [\#1059](https://github.com/pypeclub/pype/pull/1059)
- TVPaint frame offset [\#1057](https://github.com/pypeclub/pype/pull/1057)
- Auto fix unicode strings [\#1046](https://github.com/pypeclub/pype/pull/1046)

## [2.15.2](https://github.com/pypeclub/pype/tree/2.15.2) (2021-02-19)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.15.1...2.15.2)

**Enhancements:**

- Maya: Vray scene publishing [\#1013](https://github.com/pypeclub/pype/pull/1013)

**Fixed bugs:**

- Fix entity move under project [\#1040](https://github.com/pypeclub/pype/pull/1040)
- smaller nuke fixes from production [\#1036](https://github.com/pypeclub/pype/pull/1036)
- TVPaint thumbnail extract fix [\#1031](https://github.com/pypeclub/pype/pull/1031)

## [2.15.1](https://github.com/pypeclub/pype/tree/2.15.1) (2021-02-12)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.15.0...2.15.1)

**Enhancements:**

- Delete version as loader action [\#1011](https://github.com/pypeclub/pype/pull/1011)
- Delete old versions [\#445](https://github.com/pypeclub/pype/pull/445)

**Fixed bugs:**

- PS - remove obsolete functions from pywin32 [\#1006](https://github.com/pypeclub/pype/pull/1006)
- Clone description of review session objects. [\#922](https://github.com/pypeclub/pype/pull/922)

## [2.15.0](https://github.com/pypeclub/pype/tree/2.15.0) (2021-02-09)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.14.6...2.15.0)

**Enhancements:**

- Resolve - loading and updating clips [\#932](https://github.com/pypeclub/pype/pull/932)
- Release/2.15.0 [\#926](https://github.com/pypeclub/pype/pull/926)
- Photoshop: add option for template.psd and prelaunch hook  [\#894](https://github.com/pypeclub/pype/pull/894)
- Nuke: deadline presets [\#993](https://github.com/pypeclub/pype/pull/993)
- Maya: Alembic only set attributes that exists. [\#986](https://github.com/pypeclub/pype/pull/986)
- Harmony: render local and handle fixes [\#981](https://github.com/pypeclub/pype/pull/981)
- PSD Bulk export of ANIM group [\#965](https://github.com/pypeclub/pype/pull/965)
- AE - added prelaunch hook for opening last or workfile from template [\#944](https://github.com/pypeclub/pype/pull/944)
- PS - safer handling of loading of workfile [\#941](https://github.com/pypeclub/pype/pull/941)
- Maya: Handling Arnold referenced AOVs [\#938](https://github.com/pypeclub/pype/pull/938)
- TVPaint: switch layer IDs for layer names during identification [\#903](https://github.com/pypeclub/pype/pull/903)
- TVPaint audio/sound loader [\#893](https://github.com/pypeclub/pype/pull/893)
- Clone review session with children. [\#891](https://github.com/pypeclub/pype/pull/891)
- Simple compositing data packager for freelancers [\#884](https://github.com/pypeclub/pype/pull/884)
- Harmony deadline submission [\#881](https://github.com/pypeclub/pype/pull/881)
- Maya: Optionally hide image planes from reviews. [\#840](https://github.com/pypeclub/pype/pull/840)
- Maya: handle referenced AOVs for Vray [\#824](https://github.com/pypeclub/pype/pull/824)
- DWAA/DWAB support on windows [\#795](https://github.com/pypeclub/pype/pull/795)
- Unreal: animation, layout and setdress updates [\#695](https://github.com/pypeclub/pype/pull/695)

**Fixed bugs:**

- Maya: Looks - disable hardlinks [\#995](https://github.com/pypeclub/pype/pull/995)
- Fix Ftrack custom attribute update [\#982](https://github.com/pypeclub/pype/pull/982)
- Prores ks in burnin script [\#960](https://github.com/pypeclub/pype/pull/960)
- terminal.py crash on import [\#839](https://github.com/pypeclub/pype/pull/839)
- Extract review handle bizarre pixel aspect ratio [\#990](https://github.com/pypeclub/pype/pull/990)
- Nuke: add nuke related env var to sumbission  [\#988](https://github.com/pypeclub/pype/pull/988)
- Nuke: missing preset's variable  [\#984](https://github.com/pypeclub/pype/pull/984)
- Get creator by name fix [\#979](https://github.com/pypeclub/pype/pull/979)
- Fix update of project's tasks on Ftrack sync [\#972](https://github.com/pypeclub/pype/pull/972)
- nuke: wrong frame offset in mov loader  [\#971](https://github.com/pypeclub/pype/pull/971)
- Create project structure action fix multiroot [\#967](https://github.com/pypeclub/pype/pull/967)
- PS: remove pywin installation from hook [\#964](https://github.com/pypeclub/pype/pull/964)
- Prores ks in burnin script [\#959](https://github.com/pypeclub/pype/pull/959)
- Subset family is now stored in subset document [\#956](https://github.com/pypeclub/pype/pull/956)
- DJV new version arguments [\#954](https://github.com/pypeclub/pype/pull/954)
- TV Paint: Fix single frame Sequence [\#953](https://github.com/pypeclub/pype/pull/953)
- nuke: missing `file` knob update  [\#933](https://github.com/pypeclub/pype/pull/933)
- Photoshop: Create from single layer was failing [\#920](https://github.com/pypeclub/pype/pull/920)
- Nuke: baking mov with correct colorspace inherited from write  [\#909](https://github.com/pypeclub/pype/pull/909)
- Launcher fix actions discover [\#896](https://github.com/pypeclub/pype/pull/896)
- Get the correct file path for the updated mov. [\#889](https://github.com/pypeclub/pype/pull/889)
- Maya: Deadline submitter - shared data access violation [\#831](https://github.com/pypeclub/pype/pull/831)
- Maya: Take into account vray master AOV switch [\#822](https://github.com/pypeclub/pype/pull/822)

**Merged pull requests:**

- Refactor blender to 3.0 format [\#934](https://github.com/pypeclub/pype/pull/934)

## [2.14.6](https://github.com/pypeclub/pype/tree/2.14.6) (2021-01-15)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.14.5...2.14.6)

**Fixed bugs:**

- Nuke: improving of hashing path  [\#885](https://github.com/pypeclub/pype/pull/885)

**Merged pull requests:**

- Hiero: cut videos with correct secons  [\#892](https://github.com/pypeclub/pype/pull/892)
- Faster sync to avalon preparation [\#869](https://github.com/pypeclub/pype/pull/869)

## [2.14.5](https://github.com/pypeclub/pype/tree/2.14.5) (2021-01-06)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.14.4...2.14.5)

**Merged pull requests:**

- Pype logger refactor [\#866](https://github.com/pypeclub/pype/pull/866)

## [2.14.4](https://github.com/pypeclub/pype/tree/2.14.4) (2020-12-18)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.14.3...2.14.4)

**Merged pull requests:**

- Fix - AE - added explicit cast to int [\#837](https://github.com/pypeclub/pype/pull/837)

## [2.14.3](https://github.com/pypeclub/pype/tree/2.14.3) (2020-12-16)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.14.2...2.14.3)

**Fixed bugs:**

- TVPaint repair invalid metadata [\#809](https://github.com/pypeclub/pype/pull/809)
- Feature/push hier value to nonhier action [\#807](https://github.com/pypeclub/pype/pull/807)
- Harmony: fix palette and image sequence loader [\#806](https://github.com/pypeclub/pype/pull/806)

**Merged pull requests:**

- respecting space in path [\#823](https://github.com/pypeclub/pype/pull/823)

## [2.14.2](https://github.com/pypeclub/pype/tree/2.14.2) (2020-12-04)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.14.1...2.14.2)

**Enhancements:**

- Collapsible wrapper in settings [\#767](https://github.com/pypeclub/pype/pull/767)

**Fixed bugs:**

- Harmony: template extraction and palettes thumbnails on mac [\#768](https://github.com/pypeclub/pype/pull/768)
- TVPaint store context to workfile metadata \(764\) [\#766](https://github.com/pypeclub/pype/pull/766)
- Extract review audio cut fix [\#763](https://github.com/pypeclub/pype/pull/763)

**Merged pull requests:**

- AE: fix publish after background load [\#781](https://github.com/pypeclub/pype/pull/781)
- TVPaint store members key [\#769](https://github.com/pypeclub/pype/pull/769)

## [2.14.1](https://github.com/pypeclub/pype/tree/2.14.1) (2020-11-27)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.14.0...2.14.1)

**Enhancements:**

- Settings required keys in modifiable dict [\#770](https://github.com/pypeclub/pype/pull/770)
- Extract review may not add audio to output [\#761](https://github.com/pypeclub/pype/pull/761)

**Fixed bugs:**

- After Effects: frame range, file format and render source scene fixes [\#760](https://github.com/pypeclub/pype/pull/760)
- Hiero: trimming review with clip event number  [\#754](https://github.com/pypeclub/pype/pull/754)
- TVPaint: fix updating of loaded subsets [\#752](https://github.com/pypeclub/pype/pull/752)
- Maya: Vray handling of default aov [\#748](https://github.com/pypeclub/pype/pull/748)
- Maya: multiple renderable cameras in layer didn't work [\#744](https://github.com/pypeclub/pype/pull/744)
- Ftrack integrate custom attributes fix [\#742](https://github.com/pypeclub/pype/pull/742)

## [2.14.0](https://github.com/pypeclub/pype/tree/2.14.0) (2020-11-23)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.13.7...2.14.0)

**Enhancements:**

- Render publish plugins abstraction [\#687](https://github.com/pypeclub/pype/pull/687)
- Shot asset build trigger status [\#736](https://github.com/pypeclub/pype/pull/736)
- Maya: add camera rig publishing option [\#721](https://github.com/pypeclub/pype/pull/721)
- Sort instances by label in pyblish gui  [\#719](https://github.com/pypeclub/pype/pull/719)
- Synchronize ftrack hierarchical and shot attributes [\#716](https://github.com/pypeclub/pype/pull/716)
- 686 standalonepublisher editorial from image sequences [\#699](https://github.com/pypeclub/pype/pull/699)
- Ask user to select non-default camera from scene or create a new. [\#678](https://github.com/pypeclub/pype/pull/678)
- TVPaint: image loader with options [\#675](https://github.com/pypeclub/pype/pull/675)
- Maya: Camera name can be added to burnins. [\#674](https://github.com/pypeclub/pype/pull/674)
- After Effects: base integration with loaders [\#667](https://github.com/pypeclub/pype/pull/667)
- Harmony: Javascript refactoring and overall stability improvements [\#666](https://github.com/pypeclub/pype/pull/666)

**Fixed bugs:**

- Bugfix Hiero Review / Plate representation publish [\#743](https://github.com/pypeclub/pype/pull/743)
- Asset fetch second fix [\#726](https://github.com/pypeclub/pype/pull/726)
- TVPaint extract review fix [\#740](https://github.com/pypeclub/pype/pull/740)
- After Effects: Review were not being sent to ftrack [\#738](https://github.com/pypeclub/pype/pull/738)
- Maya: vray proxy was not loading [\#722](https://github.com/pypeclub/pype/pull/722)
- Maya: Vray expected file fixes [\#682](https://github.com/pypeclub/pype/pull/682)
- Missing audio on farm submission. [\#639](https://github.com/pypeclub/pype/pull/639)

**Deprecated:**

- Removed artist view from pyblish gui [\#717](https://github.com/pypeclub/pype/pull/717)
- Maya: disable legacy override check for cameras [\#715](https://github.com/pypeclub/pype/pull/715)

**Merged pull requests:**

- Application manager [\#728](https://github.com/pypeclub/pype/pull/728)
- Feature \#664 3.0 lib refactor [\#706](https://github.com/pypeclub/pype/pull/706)
- Lib from illicit part 2 [\#700](https://github.com/pypeclub/pype/pull/700)
- 3.0 lib refactor - path tools [\#697](https://github.com/pypeclub/pype/pull/697)

## [2.13.7](https://github.com/pypeclub/pype/tree/2.13.7) (2020-11-19)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.13.6...2.13.7)

**Fixed bugs:**

- Standalone Publisher: getting fps from context instead of nonexistent entity  [\#729](https://github.com/pypeclub/pype/pull/729)

## [2.13.6](https://github.com/pypeclub/pype/tree/2.13.6) (2020-11-15)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.13.5...2.13.6)

**Fixed bugs:**

- Maya workfile version wasn't syncing with renders properly [\#711](https://github.com/pypeclub/pype/pull/711)
- Maya: Fix for publishing multiple cameras with review from the same scene [\#710](https://github.com/pypeclub/pype/pull/710)

## [2.13.5](https://github.com/pypeclub/pype/tree/2.13.5) (2020-11-12)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.13.4...2.13.5)

**Enhancements:**

- 3.0 lib refactor [\#664](https://github.com/pypeclub/pype/issues/664)

**Fixed bugs:**

- Wrong thumbnail file was picked when publishing sequence in standalone publisher [\#703](https://github.com/pypeclub/pype/pull/703)
- Fix: Burnin data pass and FFmpeg tool check [\#701](https://github.com/pypeclub/pype/pull/701)

## [2.13.4](https://github.com/pypeclub/pype/tree/2.13.4) (2020-11-09)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.13.3...2.13.4)

**Enhancements:**

- AfterEffects integration with Websocket [\#663](https://github.com/pypeclub/pype/issues/663)

**Fixed bugs:**

- Photoshop uhiding hidden layers [\#688](https://github.com/pypeclub/pype/issues/688)
- \#688 - Fix publishing hidden layers [\#692](https://github.com/pypeclub/pype/pull/692)

**Closed issues:**

- Nuke Favorite directories "shot dir" "project dir" - not working [\#684](https://github.com/pypeclub/pype/issues/684)

**Merged pull requests:**

- Nuke Favorite directories "shot dir" "project dir" - not working \#684 [\#685](https://github.com/pypeclub/pype/pull/685)

## [2.13.3](https://github.com/pypeclub/pype/tree/2.13.3) (2020-11-03)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.13.2...2.13.3)

**Enhancements:**

- TV paint base integration [\#612](https://github.com/pypeclub/pype/issues/612)

**Fixed bugs:**

- Fix ffmpeg executable path with spaces [\#680](https://github.com/pypeclub/pype/pull/680)
- Hotfix: Added default version number [\#679](https://github.com/pypeclub/pype/pull/679)

## [2.13.2](https://github.com/pypeclub/pype/tree/2.13.2) (2020-10-28)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.13.1...2.13.2)

**Fixed bugs:**

- Nuke: wrong conditions when fixing legacy write nodes [\#665](https://github.com/pypeclub/pype/pull/665)

## [2.13.1](https://github.com/pypeclub/pype/tree/2.13.1) (2020-10-23)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.13.0...2.13.1)

**Enhancements:**

- move maya look assigner to pype menu [\#292](https://github.com/pypeclub/pype/issues/292)

**Fixed bugs:**

- Layer name is not propagating to metadata in Photoshop [\#654](https://github.com/pypeclub/pype/issues/654)
- Loader in Photoshop fails with "can't set attribute" [\#650](https://github.com/pypeclub/pype/issues/650)
- Nuke Load mp4 wrong frame range [\#661](https://github.com/pypeclub/pype/issues/661)
- Hiero: Review video file adding one frame to the end [\#659](https://github.com/pypeclub/pype/issues/659)

## [2.13.0](https://github.com/pypeclub/pype/tree/2.13.0) (2020-10-18)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.12.5...2.13.0)

**Enhancements:**

- Deadline Output Folder [\#636](https://github.com/pypeclub/pype/issues/636)
- Nuke Camera Loader [\#565](https://github.com/pypeclub/pype/issues/565)
- Deadline publish job shows publishing output folder [\#649](https://github.com/pypeclub/pype/pull/649)
- Get latest version in lib [\#642](https://github.com/pypeclub/pype/pull/642)
- Improved publishing of multiple representation from SP [\#638](https://github.com/pypeclub/pype/pull/638)
- Launch TvPaint shot work file from within Ftrack [\#631](https://github.com/pypeclub/pype/pull/631)
- Add mp4 support for RV action. [\#628](https://github.com/pypeclub/pype/pull/628)
- Maya: allow renders to have version synced with workfile [\#618](https://github.com/pypeclub/pype/pull/618)
- Renaming nukestudio host folder to hiero [\#617](https://github.com/pypeclub/pype/pull/617)
- Harmony: More efficient publishing [\#615](https://github.com/pypeclub/pype/pull/615)
- Ftrack server action improvement [\#608](https://github.com/pypeclub/pype/pull/608)
- Deadline user defaults to pype username if present [\#607](https://github.com/pypeclub/pype/pull/607)
- Standalone publisher now has icon [\#606](https://github.com/pypeclub/pype/pull/606)
- Nuke render write targeting knob improvement [\#603](https://github.com/pypeclub/pype/pull/603)
- Animated pyblish gui [\#602](https://github.com/pypeclub/pype/pull/602)
- Maya: Deadline - make use of asset dependencies optional [\#591](https://github.com/pypeclub/pype/pull/591)
- Nuke: Publishing, loading and updating alembic cameras [\#575](https://github.com/pypeclub/pype/pull/575)
- Maya: add look assigner to pype menu even if scriptsmenu is not available [\#573](https://github.com/pypeclub/pype/pull/573)
- Store task types in the database [\#572](https://github.com/pypeclub/pype/pull/572)
- Maya: Tiled EXRs to scanline EXRs render option [\#512](https://github.com/pypeclub/pype/pull/512)
- Fusion basic integration [\#452](https://github.com/pypeclub/pype/pull/452)

**Fixed bugs:**

- Burnin script did not propagate ffmpeg output [\#640](https://github.com/pypeclub/pype/issues/640)
- Pyblish-pype spacer in terminal wasn't transparent [\#646](https://github.com/pypeclub/pype/pull/646)
- Lib subprocess without logger [\#645](https://github.com/pypeclub/pype/pull/645)
- Nuke: prevent crash if we only have single frame in sequence [\#644](https://github.com/pypeclub/pype/pull/644)
- Burnin script logs better output [\#641](https://github.com/pypeclub/pype/pull/641)
- Missing audio on farm submission. [\#639](https://github.com/pypeclub/pype/pull/639)
- review from imagesequence error [\#633](https://github.com/pypeclub/pype/pull/633)
- Hiero: wrong order of fps clip instance data collecting  [\#627](https://github.com/pypeclub/pype/pull/627)
- Add source for review instances. [\#625](https://github.com/pypeclub/pype/pull/625)
- Task processing in event sync [\#623](https://github.com/pypeclub/pype/pull/623)
- sync to avalon doesn t remove renamed task [\#619](https://github.com/pypeclub/pype/pull/619)
- Intent publish setting wasn't working with default value [\#562](https://github.com/pypeclub/pype/pull/562)
- Maya: Updating a look where the shader name changed, leaves the geo without a shader [\#514](https://github.com/pypeclub/pype/pull/514)

**Merged pull requests:**

- Avalon module without Qt [\#581](https://github.com/pypeclub/pype/pull/581)
- Ftrack module without Qt [\#577](https://github.com/pypeclub/pype/pull/577)

## [2.12.5](https://github.com/pypeclub/pype/tree/2.12.5) (2020-10-14)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.12.4...2.12.5)

**Enhancements:**

- Launch TvPaint shot work file from within Ftrack [\#629](https://github.com/pypeclub/pype/issues/629)

**Merged pull requests:**

- Harmony: Disable application launch logic [\#637](https://github.com/pypeclub/pype/pull/637)

## [2.12.4](https://github.com/pypeclub/pype/tree/2.12.4) (2020-10-08)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.12.3...2.12.4)

**Enhancements:**

- convert nukestudio to hiero host [\#616](https://github.com/pypeclub/pype/issues/616)
- Fusion basic integration  [\#451](https://github.com/pypeclub/pype/issues/451)

**Fixed bugs:**

- Sync to avalon doesn't remove renamed task [\#605](https://github.com/pypeclub/pype/issues/605)
- NukeStudio: FPS collecting into clip instances [\#624](https://github.com/pypeclub/pype/pull/624)

**Merged pull requests:**

- NukeStudio: small fixes [\#622](https://github.com/pypeclub/pype/pull/622)
- NukeStudio: broken order of plugins [\#620](https://github.com/pypeclub/pype/pull/620)

## [2.12.3](https://github.com/pypeclub/pype/tree/2.12.3) (2020-10-06)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.12.2...2.12.3)

**Enhancements:**

- Nuke Publish Camera [\#567](https://github.com/pypeclub/pype/issues/567)
- Harmony: open xstage file no matter of its name [\#526](https://github.com/pypeclub/pype/issues/526)
- Stop integration of unwanted data [\#387](https://github.com/pypeclub/pype/issues/387)
- Move avalon-launcher functionality to pype [\#229](https://github.com/pypeclub/pype/issues/229)
- avalon workfiles api [\#214](https://github.com/pypeclub/pype/issues/214)
- Store task types [\#180](https://github.com/pypeclub/pype/issues/180)
- Avalon Mongo Connection split [\#136](https://github.com/pypeclub/pype/issues/136)
- nk camera workflow [\#71](https://github.com/pypeclub/pype/issues/71)
- Hiero integration added [\#590](https://github.com/pypeclub/pype/pull/590)
- Anatomy instance data collection is substantially faster for many instances [\#560](https://github.com/pypeclub/pype/pull/560)

**Fixed bugs:**

- test issue [\#596](https://github.com/pypeclub/pype/issues/596)
- Harmony: empty scene contamination [\#583](https://github.com/pypeclub/pype/issues/583)
- Edit publishing in SP doesn't respect shot selection for publishing [\#542](https://github.com/pypeclub/pype/issues/542)
- Pathlib breaks compatibility with python2 hosts [\#281](https://github.com/pypeclub/pype/issues/281)
- Updating a look where the shader name changed leaves the geo without a shader [\#237](https://github.com/pypeclub/pype/issues/237)
- Better error handling [\#84](https://github.com/pypeclub/pype/issues/84)
- Harmony: function signature [\#609](https://github.com/pypeclub/pype/pull/609)
- Nuke: gizmo publishing error [\#594](https://github.com/pypeclub/pype/pull/594)
- Harmony: fix clashing namespace of called js functions [\#584](https://github.com/pypeclub/pype/pull/584)
- Maya: fix maya scene type preset exception [\#569](https://github.com/pypeclub/pype/pull/569)

**Closed issues:**

- Nuke Gizmo publishing [\#597](https://github.com/pypeclub/pype/issues/597)
- nuke gizmo publishing error [\#592](https://github.com/pypeclub/pype/issues/592)
- Publish EDL [\#579](https://github.com/pypeclub/pype/issues/579)
- Publish render from SP [\#576](https://github.com/pypeclub/pype/issues/576)
- rename ftrack custom attribute group to `pype` [\#184](https://github.com/pypeclub/pype/issues/184)

**Merged pull requests:**

- Audio file existence check [\#614](https://github.com/pypeclub/pype/pull/614)
- NKS small fixes [\#587](https://github.com/pypeclub/pype/pull/587)
- Standalone publisher editorial plugins interfering [\#580](https://github.com/pypeclub/pype/pull/580)

## [2.12.2](https://github.com/pypeclub/pype/tree/2.12.2) (2020-09-25)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.12.1...2.12.2)

**Enhancements:**

- pype config GUI [\#241](https://github.com/pypeclub/pype/issues/241)

**Fixed bugs:**

- Harmony: Saving heavy scenes will crash [\#507](https://github.com/pypeclub/pype/issues/507)
- Extract review a representation name with `\*\_burnin` [\#388](https://github.com/pypeclub/pype/issues/388)
- Hierarchy data was not considering active isntances [\#551](https://github.com/pypeclub/pype/pull/551)

## [2.12.1](https://github.com/pypeclub/pype/tree/2.12.1) (2020-09-15)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.12.0...2.12.1)

**Fixed bugs:**

- Pype: changelog.md is outdated [\#503](https://github.com/pypeclub/pype/issues/503)
- dependency security alert ! [\#484](https://github.com/pypeclub/pype/issues/484)
- Maya: RenderSetup is missing update [\#106](https://github.com/pypeclub/pype/issues/106)
- \<pyblish plugin\> extract effects creates new instance [\#78](https://github.com/pypeclub/pype/issues/78)

## [2.12.0](https://github.com/pypeclub/pype/tree/2.12.0) (2020-09-10)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.11.8...2.12.0)

**Enhancements:**

- Less mongo connections [\#509](https://github.com/pypeclub/pype/pull/509)
- Nuke: adding image loader  [\#499](https://github.com/pypeclub/pype/pull/499)
- Move launcher window to top if launcher action is clicked [\#450](https://github.com/pypeclub/pype/pull/450)
- Maya:  better tile rendering support in Pype [\#446](https://github.com/pypeclub/pype/pull/446)
- Implementation of non QML launcher [\#443](https://github.com/pypeclub/pype/pull/443)
- Optional skip review on renders. [\#441](https://github.com/pypeclub/pype/pull/441)
- Ftrack: Option to push status from task to latest version [\#440](https://github.com/pypeclub/pype/pull/440)
- Properly containerize image plane loads. [\#434](https://github.com/pypeclub/pype/pull/434)
- Option to keep the review files. [\#426](https://github.com/pypeclub/pype/pull/426)
- Isolate view on instance members. [\#425](https://github.com/pypeclub/pype/pull/425)
- Maya: Publishing of tile renderings on Deadline [\#398](https://github.com/pypeclub/pype/pull/398)
- Feature/little bit better logging gui [\#383](https://github.com/pypeclub/pype/pull/383)

**Fixed bugs:**

- Maya: Fix tile order for Draft Tile Assembler [\#511](https://github.com/pypeclub/pype/pull/511)
- Remove extra dash [\#501](https://github.com/pypeclub/pype/pull/501)
- Fix: strip dot from repre names in single frame renders [\#498](https://github.com/pypeclub/pype/pull/498)
- Better handling of destination during integrating [\#485](https://github.com/pypeclub/pype/pull/485)
- Fix: allow thumbnail creation for single frame renders [\#460](https://github.com/pypeclub/pype/pull/460)
- added missing argument to launch\_application in ftrack app handler [\#453](https://github.com/pypeclub/pype/pull/453)
- Burnins: Copy bit rate of input video to match quality. [\#448](https://github.com/pypeclub/pype/pull/448)
- Standalone publisher is now independent from tray [\#442](https://github.com/pypeclub/pype/pull/442)
- Bugfix/empty enumerator attributes [\#436](https://github.com/pypeclub/pype/pull/436)
- Fixed wrong order of "other" category collapssing in publisher [\#435](https://github.com/pypeclub/pype/pull/435)
- Multiple reviews where being overwritten to one. [\#424](https://github.com/pypeclub/pype/pull/424)
- Cleanup plugin fail on instances without staging dir [\#420](https://github.com/pypeclub/pype/pull/420)
- deprecated -intra parameter in ffmpeg to new `-g` [\#417](https://github.com/pypeclub/pype/pull/417)
- Delivery action can now work with entered path [\#397](https://github.com/pypeclub/pype/pull/397)

**Merged pull requests:**

- Review on instance.data  [\#473](https://github.com/pypeclub/pype/pull/473)

## [2.11.8](https://github.com/pypeclub/pype/tree/2.11.8) (2020-08-27)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.11.7...2.11.8)

**Enhancements:**

- DWAA support for Maya [\#382](https://github.com/pypeclub/pype/issues/382)
- Isolate View on Playblast [\#367](https://github.com/pypeclub/pype/issues/367)
- Maya: Tile rendering [\#297](https://github.com/pypeclub/pype/issues/297)
- single pype instance running [\#47](https://github.com/pypeclub/pype/issues/47)
- PYPE-649: projects don't guarantee backwards compatible environment [\#8](https://github.com/pypeclub/pype/issues/8)
- PYPE-663: separate venv for each deployed version [\#7](https://github.com/pypeclub/pype/issues/7)

**Fixed bugs:**

- pyblish pype - other group is collapsed before plugins are done [\#431](https://github.com/pypeclub/pype/issues/431)
- Alpha white edges in harmony on PNGs [\#412](https://github.com/pypeclub/pype/issues/412)
- harmony image loader picks wrong representations [\#404](https://github.com/pypeclub/pype/issues/404)
- Clockify crash when response contain symbol not allowed by UTF-8 [\#81](https://github.com/pypeclub/pype/issues/81)

## [2.11.7](https://github.com/pypeclub/pype/tree/2.11.7) (2020-08-21)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.11.6...2.11.7)

**Fixed bugs:**

- Clean Up Baked Movie [\#369](https://github.com/pypeclub/pype/issues/369)
- celaction last workfile [\#459](https://github.com/pypeclub/pype/pull/459)

## [2.11.6](https://github.com/pypeclub/pype/tree/2.11.6) (2020-08-18)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.11.5...2.11.6)

**Enhancements:**

- publisher app [\#56](https://github.com/pypeclub/pype/issues/56)

## [2.11.5](https://github.com/pypeclub/pype/tree/2.11.5) (2020-08-13)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.11.4...2.11.5)

**Enhancements:**

- Switch from master to equivalent [\#220](https://github.com/pypeclub/pype/issues/220)
- Standalone publisher now only groups sequence if the extension is known [\#439](https://github.com/pypeclub/pype/pull/439)

**Fixed bugs:**

- Logs have been disable for editorial by default to speed up publishing [\#433](https://github.com/pypeclub/pype/pull/433)
- additional fixes for celaction [\#430](https://github.com/pypeclub/pype/pull/430)
- Harmony: invalid variable scope in validate scene settings [\#428](https://github.com/pypeclub/pype/pull/428)
- new representation name for audio was not accepted [\#427](https://github.com/pypeclub/pype/pull/427)

## [2.11.4](https://github.com/pypeclub/pype/tree/2.11.4) (2020-08-10)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.11.3...2.11.4)

**Enhancements:**

- WebSocket server [\#135](https://github.com/pypeclub/pype/issues/135)
- standalonepublisher: editorial family features expansion \[master branch\] [\#411](https://github.com/pypeclub/pype/pull/411)

## [2.11.3](https://github.com/pypeclub/pype/tree/2.11.3) (2020-08-04)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.11.2...2.11.3)

**Fixed bugs:**

- Harmony: publishing performance issues [\#408](https://github.com/pypeclub/pype/pull/408)

## [2.11.2](https://github.com/pypeclub/pype/tree/2.11.2) (2020-07-31)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.11.1...2.11.2)

**Fixed bugs:**

- Ftrack to Avalon bug [\#406](https://github.com/pypeclub/pype/issues/406)

## [2.11.1](https://github.com/pypeclub/pype/tree/2.11.1) (2020-07-29)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.11.0...2.11.1)

**Merged pull requests:**

- Celaction: metadata json folder fixes on path  [\#393](https://github.com/pypeclub/pype/pull/393)
- CelAction - version up method taken fro pype.lib  [\#391](https://github.com/pypeclub/pype/pull/391)

<a name="2.11.0"></a>
## 2.11.0 ##

_**release date:** 27 July 2020_

**new:**
- _(blender)_ namespace support [\#341](https://github.com/pypeclub/pype/pull/341)
- _(blender)_ start end frames [\#330](https://github.com/pypeclub/pype/pull/330)
- _(blender)_ camera asset [\#322](https://github.com/pypeclub/pype/pull/322)
- _(pype)_ toggle instances per family in pyblish GUI [\#320](https://github.com/pypeclub/pype/pull/320)
- _(pype)_ current release version is now shown in the tray menu [#379](https://github.com/pypeclub/pype/pull/379)


**improved:**
- _(resolve)_ tagging for publish [\#239](https://github.com/pypeclub/pype/issues/239)
- _(pype)_ Support publishing a subset of shots with standalone editorial [\#336](https://github.com/pypeclub/pype/pull/336)
- _(harmony)_ Basic support for palettes [\#324](https://github.com/pypeclub/pype/pull/324)
- _(photoshop)_ Flag outdated containers on startup and publish. [\#309](https://github.com/pypeclub/pype/pull/309)
- _(harmony)_ Flag Outdated containers [\#302](https://github.com/pypeclub/pype/pull/302)
- _(photoshop)_ Publish review [\#298](https://github.com/pypeclub/pype/pull/298)
- _(pype)_ Optional Last workfile launch [\#365](https://github.com/pypeclub/pype/pull/365)


**fixed:**
- _(premiere)_ workflow fixes [\#346](https://github.com/pypeclub/pype/pull/346)
- _(pype)_ pype-setup does not work with space in path [\#327](https://github.com/pypeclub/pype/issues/327)
- _(ftrack)_ Ftrack delete action cause circular error [\#206](https://github.com/pypeclub/pype/issues/206)
- _(nuke)_ Priority was forced to 50 [\#345](https://github.com/pypeclub/pype/pull/345)
- _(nuke)_ Fix ValidateNukeWriteKnobs [\#340](https://github.com/pypeclub/pype/pull/340)
- _(maya)_ If camera attributes are connected, we can ignore them. [\#339](https://github.com/pypeclub/pype/pull/339)
- _(pype)_ stop appending of tools environment to existing env [\#337](https://github.com/pypeclub/pype/pull/337)
- _(ftrack)_ Ftrack timeout needs to look at AVALON\_TIMEOUT [\#325](https://github.com/pypeclub/pype/pull/325)
- _(harmony)_ Only zip files are supported. [\#310](https://github.com/pypeclub/pype/pull/310)
- _(pype)_ hotfix/Fix event server mongo uri [\#305](https://github.com/pypeclub/pype/pull/305)
- _(photoshop)_ Subset was not named or validated correctly. [\#304](https://github.com/pypeclub/pype/pull/304)



<a name="2.10.0"></a>
## 2.10.0 ##

_**release date:** 17 June 2020_

**new:**
- _(harmony)_ **Toon Boom Harmony** has been greatly extended to support rigging, scene build, animation and rendering workflows. [#270](https://github.com/pypeclub/pype/issues/270) [#271](https://github.com/pypeclub/pype/issues/271) [#190](https://github.com/pypeclub/pype/issues/190) [#191](https://github.com/pypeclub/pype/issues/191) [#172](https://github.com/pypeclub/pype/issues/172) [#168](https://github.com/pypeclub/pype/issues/168)
- _(pype)_ Added support for rudimentary **edl publishing** into individual shots. [#265](https://github.com/pypeclub/pype/issues/265)
- _(celaction)_ Simple **Celaction** integration has been added with support for workfiles and rendering. [#255](https://github.com/pypeclub/pype/issues/255)
- _(maya)_ Support for multiple job types when submitting to the farm. We can now render Maya or Standalone render jobs for Vray and Arnold (limited support for arnold) [#204](https://github.com/pypeclub/pype/issues/204)
- _(photoshop)_ Added initial support for Photoshop [#232](https://github.com/pypeclub/pype/issues/232)

**improved:**
- _(blender)_ Updated support for rigs and added support Layout family [#233](https://github.com/pypeclub/pype/issues/233) [#226](https://github.com/pypeclub/pype/issues/226)
- _(premiere)_ It is now possible to choose different storage root for workfiles of different task types. [#255](https://github.com/pypeclub/pype/issues/255)
- _(maya)_ Support for unmerged AOVs in Redshift multipart EXRs [#197](https://github.com/pypeclub/pype/issues/197)
- _(pype)_ Pype repository has been refactored in preparation for 3.0 release [#169](https://github.com/pypeclub/pype/issues/169)
- _(deadline)_ All file dependencies are now passed to deadline from maya to prevent premature start of rendering if caches or textures haven't been coppied over yet. [#195](https://github.com/pypeclub/pype/issues/195)
- _(nuke)_ Script validation can now be made optional. [#194](https://github.com/pypeclub/pype/issues/194)
- _(pype)_ Publishing can now be stopped at any time. [#194](https://github.com/pypeclub/pype/issues/194)

**fix:**
- _(pype)_ Pyblish-lite has been integrated into pype repository, plus various publishing GUI fixes. [#274](https://github.com/pypeclub/pype/issues/274) [#275](https://github.com/pypeclub/pype/issues/275) [#268](https://github.com/pypeclub/pype/issues/268) [#227](https://github.com/pypeclub/pype/issues/227) [#238](https://github.com/pypeclub/pype/issues/238)
- _(maya)_ Alembic extractor was getting wrong frame range type in certain scenarios [#254](https://github.com/pypeclub/pype/issues/254)
- _(maya)_ Attaching a render to subset in maya was not passing validation in certain scenarios  [#256](https://github.com/pypeclub/pype/issues/256)
- _(ftrack)_ Various small fixes to ftrack sync [#263](https://github.com/pypeclub/pype/issues/263) [#259](https://github.com/pypeclub/pype/issues/259)
- _(maya)_ Look extraction is now able to skp invalid connections in shaders [#207](https://github.com/pypeclub/pype/issues/207)



<a name="2.9.0"></a>
## 2.9.0 ##

_**release date:** 25 May 2020_

**new:**
- _(pype)_ Support for **Multiroot projects**. You can now store project data on multiple physical or virtual storages and target individual publishes to these locations. For instance render can be stored on a faster storage than the rest of the project. [#145](https://github.com/pypeclub/pype/issues/145), [#38](https://github.com/pypeclub/pype/issues/38)
- _(harmony)_ Basic implementation of **Toon Boom Harmony** has been added. [#142](https://github.com/pypeclub/pype/issues/142)
- _(pype)_ OSX support is in public beta now. There are issues to be expected, but the main implementation should be functional. [#141](https://github.com/pypeclub/pype/issues/141)


**improved:**

- _(pype)_ **Review extractor** has been completely rebuilt. It now supports granular filtering so you can create **multiple outputs** for different tasks, families or hosts. [#103](https://github.com/pypeclub/pype/issues/103), [#166](https://github.com/pypeclub/pype/issues/166), [#165](https://github.com/pypeclub/pype/issues/165)
- _(pype)_ **Burnin** generation had been extended to **support same multi-output filtering** as review extractor [#103](https://github.com/pypeclub/pype/issues/103)
- _(pype)_ Publishing file templates can now be specified in config for each individual family [#114](https://github.com/pypeclub/pype/issues/114)
- _(pype)_ Studio specific plugins can now be appended to pype standard publishing plugins. [#112](https://github.com/pypeclub/pype/issues/112)
- _(nukestudio)_ Reviewable clips no longer need to be previously cut, exported and re-imported to timeline. **Pype can now dynamically cut reviewable quicktimes** from continuous offline footage during publishing. [#23](https://github.com/pypeclub/pype/issues/23)
- _(deadline)_ Deadline can now correctly differentiate between staging and production pype. [#154](https://github.com/pypeclub/pype/issues/154)
- _(deadline)_ `PYPE_PYTHON_EXE` env variable can now be used to direct publishing to explicit python installation. [#120](https://github.com/pypeclub/pype/issues/120)
- _(nuke)_ Nuke now check for new version of loaded data on file open. [#140](https://github.com/pypeclub/pype/issues/140)
- _(nuke)_ frame range and limit checkboxes are now exposed on write node. [#119](https://github.com/pypeclub/pype/issues/119)



**fix:**

- _(nukestudio)_ Project Location was using backslashes which was breaking nukestudio native exporting in certains configurations [#82](https://github.com/pypeclub/pype/issues/82)
- _(nukestudio)_ Duplicity in hierarchy tags was prone to throwing publishing error [#130](https://github.com/pypeclub/pype/issues/130), [#144](https://github.com/pypeclub/pype/issues/144)
- _(ftrack)_ multiple stability improvements [#157](https://github.com/pypeclub/pype/issues/157), [#159](https://github.com/pypeclub/pype/issues/159), [#128](https://github.com/pypeclub/pype/issues/128), [#118](https://github.com/pypeclub/pype/issues/118), [#127](https://github.com/pypeclub/pype/issues/127)
- _(deadline)_ multipart EXRs were stopping review publishing on the farm. They are still not supported for automatic review generation, but the publish will go through correctly without the quicktime. [#155](https://github.com/pypeclub/pype/issues/155)
- _(deadline)_ If deadline is non-responsive it will no longer freeze host when publishing [#149](https://github.com/pypeclub/pype/issues/149)
- _(deadline)_ Sometimes deadline was trying to launch render before all the source data was coppied over. [#137](https://github.com/pypeclub/pype/issues/137) _(harmony)_ Basic implementation of **Toon Boom Harmony** has been added. [#142](https://github.com/pypeclub/pype/issues/142)
- _(nuke)_ Filepath knob wasn't updated properly. [#131](https://github.com/pypeclub/pype/issues/131)
- _(maya)_ When extracting animation, the "Write Color Set" options on the instance were not respected. [#108](https://github.com/pypeclub/pype/issues/108)
- _(maya)_ Attribute overrides for AOV only worked for the legacy render layers. Now it works for new render setup as well [#132](https://github.com/pypeclub/pype/issues/132)
- _(maya)_ Stability and usability improvements in yeti workflow [#104](https://github.com/pypeclub/pype/issues/104)



<a name="2.8.0"></a>
## 2.8.0 ##

_**release date:** 20 April 2020_

**new:**

- _(pype)_ Option to generate slates from json templates. [PYPE-628] [#26](https://github.com/pypeclub/pype/issues/26)
- _(pype)_ It is now possible to automate loading of published subsets into any scene. Documentation will follow :). [PYPE-611] [#24](https://github.com/pypeclub/pype/issues/24)

**fix:**

- _(maya)_ Some Redshift render tokens could break publishing. [PYPE-778] [#33](https://github.com/pypeclub/pype/issues/33)
- _(maya)_ Publish was not preserving maya file extension. [#39](https://github.com/pypeclub/pype/issues/39)
- _(maya)_ Rig output validator was failing on nodes without shapes. [#40](https://github.com/pypeclub/pype/issues/40)
- _(maya)_ Yeti caches can now be properly versioned up in the scene inventory. [#40](https://github.com/pypeclub/pype/issues/40)
- _(nuke)_ Build first workfiles was not accepting jpeg sequences. [#34](https://github.com/pypeclub/pype/issues/34)
- _(deadline)_ Trying to generate ffmpeg review from multipart EXRs no longer crashes publishing. [PYPE-781]
- _(deadline)_ Render publishing is more stable in multiplatform environments. [PYPE-775]



<a name="2.7.0"></a>
## 2.7.0 ##

_**release date:** 30 March 2020_

**new:**

- _(maya)_ Artist can now choose to load multiple references of the same subset at once [PYPE-646, PYPS-81]
- _(nuke)_ Option to use named OCIO colorspaces for review colour baking. [PYPS-82]
- _(pype)_ Pype can now work with `master` versions for publishing and loading. These are non-versioned publishes that are overwritten with the latest version during publish. These are now supported in all the GUIs, but their publishing is deactivated by default. [PYPE-653]
- _(blender)_ Added support for basic blender workflow. We currently support `rig`, `model` and `animation` families. [PYPE-768]
- _(pype)_ Source timecode can now be used in burn-ins. [PYPE-777]
- _(pype)_ Review outputs profiles can now specify delivery resolution different than project setting [PYPE-759]
- _(nuke)_ Bookmark to current context is now added automatically to all nuke browser windows. [PYPE-712]

**change:**

- _(maya)_ It is now possible to publish camera without. baking. Keep in mind that unbaked cameras can't be guaranteed to work in other hosts. [PYPE-595]
- _(maya)_ All the renders from maya are now grouped in the loader by their Layer name. [PYPE-482]
- _(nuke/hiero)_ Any publishes from nuke and hiero can now be versioned independently of the workfile. [PYPE-728]


**fix:**

- _(nuke)_ Mixed slashes caused issues in ocio config path.
- _(pype)_ Intent field in pyblish GUI was passing label instead of value to ftrack. [PYPE-733]
- _(nuke)_ Publishing of pre-renders was inconsistent. [PYPE-766]
- _(maya)_ Handles and frame ranges were inconsistent in various places during publishing.
- _(nuke)_ Nuke was crashing if it ran into certain missing knobs. For example DPX output missing `autocrop` [PYPE-774]
- _(deadline)_ Project overrides were not working properly with farm render publishing.
- _(hiero)_ Problems with single frame plates publishing.
- _(maya)_ Redshift RenderPass token were breaking render publishing. [PYPE-778]
- _(nuke)_ Build first workfile was not accepting jpeg sequences.
- _(maya)_ Multipart (Multilayer) EXRs were breaking review publishing due to FFMPEG incompatiblity [PYPE-781]


<a name="2.6.0"></a>
## 2.6.0 ##

_**release date:** 9 March 2020_

**change:**
- _(maya)_ render publishing has been simplified and made more robust. Render setup layers are now automatically added to publishing subsets and `render globals` family has been replaced with simple `render` [PYPE-570]
- _(avalon)_ change context and workfiles apps, have been merged into one, that allows both actions to be performed at the same time. [PYPE-747]
- _(pype)_ thumbnails are now automatically propagate to asset from the last published subset in the loader
- _(ftrack)_ publishing comment and intent are now being published to ftrack note as well as describtion. [PYPE-727]
- _(pype)_ when overriding existing version new old representations are now overriden, instead of the new ones just being appended. (to allow this behaviour, the version validator need to be disabled. [PYPE-690])
- _(pype)_ burnin preset has been significantly simplified. It now doesn't require passing function to each field, but only need the actual text template. to use this, all the current burnin PRESETS MUST BE UPDATED for all the projects.
- _(ftrack)_ credentials are now stored on a per server basis, so it's possible to switch between ftrack servers without having to log in and out. [PYPE-723]


**new:**
- _(pype)_ production and development deployments now have different colour of the tray icon. Orange for Dev and Green for production [PYPE-718]
- _(maya)_ renders can now be attached to a publishable subset rather than creating their own subset. For example it is possible to create a reviewable `look` or `model` render and have it correctly attached as a representation of the subsets [PYPE-451]
- _(maya)_ after saving current scene into a new context (as a new shot for instance), all the scene publishing subsets data gets re-generated automatically to match the new context [PYPE-532]
- _(pype)_ we now support project specific publish, load and create plugins [PYPE-740]
- _(ftrack)_ new action that allow archiving/deleting old published versions. User can keep how many of the latest version to keep when the action is ran. [PYPE-748, PYPE-715]
- _(ftrack)_ it is now possible to monitor and restart ftrack event server using ftrack action. [PYPE-658]
- _(pype)_ validator that prevent accidental overwrites of previously published versions. [PYPE-680]
- _(avalon)_ avalon core updated to version 5.6.0
- _(maya)_ added validator to make sure that relative paths are used when publishing arnold standins.
- _(nukestudio)_ it is now possible to extract and publish audio family from clip in nuke studio [PYPE-682]

**fix**:
- _(maya)_ maya set framerange button was ignoring handles [PYPE-719]
- _(ftrack)_ sync to avalon was sometime crashing when ran on empty project
- _(nukestudio)_ publishing same shots after they've been previously archived/deleted would result in a crash. [PYPE-737]
- _(nuke)_ slate workflow was breaking in certain scenarios. [PYPE-730]
- _(pype)_ rendering publish workflow has been significantly improved to prevent error resulting from implicit render collection. [PYPE-665, PYPE-746]
- _(pype)_ launching application on a non-synced project resulted in obscure [PYPE-528]
- _(pype)_ missing keys in burnins no longer result in an error. [PYPE-706]
- _(ftrack)_ create folder structure action was sometimes failing for project managers due to wrong permissions.
- _(Nukestudio)_ using `source` in the start frame tag could result in wrong frame range calculation
- _(ftrack)_ sync to avalon action and event have been improved by catching more edge cases and provessing them properly.


<a name="2.5"></a>
## 2.5.0 ##

_**release date:** 11 Feb 2020_

**change:**
- _(pype)_ added many logs for easier debugging
- _(pype)_ review presets can now be separated between 2d and 3d renders [PYPE-693]
- _(pype)_ anatomy module has been greatly improved to allow for more dynamic pulblishing and faster debugging [PYPE-685]
- _(pype)_ avalon schemas have been moved from `pype-config` to `pype` repository, for simplification. [PYPE-670]
- _(ftrack)_ updated to latest ftrack API
- _(ftrack)_ publishing comments now appear in ftrack also as a note on version with customisable category [PYPE-645]
- _(ftrack)_ delete asset/subset action had been improved. It is now able to remove multiple entities and descendants of the selected entities [PYPE-361, PYPS-72]
- _(workfiles)_ added date field to workfiles app [PYPE-603]
- _(maya)_ old deprecated loader have been removed in favour of a single unified reference loader (old scenes will upgrade automatically to the new loader upon opening) [PYPE-633, PYPE-697]
- _(avalon)_ core updated to 5.5.15 [PYPE-671]
- _(nuke)_ library loader is now available in nuke [PYPE-698]


**new:**
- _(pype)_ added pype render wrapper to allow rendering on mixed platform farms. [PYPE-634]
- _(pype)_ added `pype launch` command. It let's admin run applications with dynamically built environment based on the given context. [PYPE-634]
- _(pype)_ added support for extracting review sequences with burnins [PYPE-657]
- _(publish)_ users can now set intent next to a comment when publishing. This will then be reflected on an attribute in ftrack. [PYPE-632]
- _(burnin)_ timecode can now be added to burnin
- _(burnin)_ datetime keys can now be added to burnin and anatomy [PYPE-651]
- _(burnin)_ anatomy templates can now be used in burnins. [PYPE=626]
- _(nuke)_ new validator for render resolution
- _(nuke)_ support for attach slate to nuke renders [PYPE-630]
- _(nuke)_ png sequences were added to loaders
- _(maya)_ added maya 2020 compatibility [PYPE-677]
- _(maya)_ ability to publish and load .ASS standin sequences [PYPS-54]
- _(pype)_ thumbnails can now be published and are visible in the loader. `AVALON_THUMBNAIL_ROOT` environment variable needs to be set for this to work  [PYPE-573, PYPE-132]
- _(blender)_ base implementation of blender was added with publishing and loading of .blend files [PYPE-612]
- _(ftrack)_ new action for preparing deliveries [PYPE-639]


**fix**:
- _(burnin)_ more robust way of finding ffmpeg for burnins.
- _(pype)_ improved UNC paths remapping when sending to farm.
- _(pype)_ float frames sometimes made their way to representation context in database, breaking loaders [PYPE-668]
- _(pype)_ `pype install --force` was failing sometimes [PYPE-600]
- _(pype)_ padding in published files got calculated wrongly sometimes. It is now instead being always read from project anatomy. [PYPE-667]
- _(publish)_ comment publishing was failing in certain situations
- _(ftrack)_ multiple edge case scenario fixes in auto sync and sync-to-avalon action
- _(ftrack)_ sync to avalon now works on empty projects
- _(ftrack)_ thumbnail update event was failing when deleting entities [PYPE-561]
- _(nuke)_ loader applies proper colorspaces from Presets
- _(nuke)_ publishing handles didn't always work correctly [PYPE-686]
- _(maya)_ assembly publishing and loading wasn't working correctly




<a name="2.4.0"></a>
## 2.4.0 ##

_**release date:** 9 Dec 2019_

**change:**
- _(ftrack)_ version to status ftrack event can now be configured from Presets
  - based on preset `presets/ftracc/ftrack_config.json["status_version_to_task"]`
- _(ftrack)_ sync to avalon event has been completely re-written. It now supports most of the project management situations on ftrack including moving, renaming and deleting entities, updating attributes and working with tasks.
- _(ftrack)_ sync to avalon action has been also re-writen. It is now much faster (up to 100 times depending on a project structure), has much better logging and reporting on encountered problems, and is able to handle much more complex situations.
- _(ftrack)_ sync to avalon trigger by checking `auto-sync` toggle on ftrack [PYPE-504]
- _(pype)_ various new features in the REST api
- _(pype)_ new visual identity used across pype
- _(pype)_ started moving all requirements to pip installation rather than vendorising them in pype repository. Due to a few yet unreleased packages, this means that pype can temporarily be only installed in the offline mode.

**new:**
- _(nuke)_ support for publishing gizmos and loading them as viewer processes
- _(nuke)_ support for publishing nuke nodes from backdrops and loading them back
- _(pype)_ burnins can now work with start and end frames as keys
  - use keys `{frame_start}`, `{frame_end}` and `{current_frame}` in burnin preset to use them. [PYPS-44,PYPS-73, PYPE-602]
- _(pype)_ option to filter logs by user and level in loggin GUI
- _(pype)_ image family added to standalone publisher [PYPE-574]
- _(pype)_ matchmove family added to standalone publisher [PYPE-574]
- _(nuke)_ validator for comparing arbitrary knobs with values from presets
- _(maya)_ option to force maya to copy textures in the new look publish rather than hardlinking them
- _(pype)_ comments from pyblish GUI are now being added to ftrack version
- _(maya)_ validator for checking outdated containers in the scene
- _(maya)_ option to publish and load arnold standin sequence [PYPE-579, PYPS-54]

**fix**:
- _(pype)_ burnins were not respecting codec of the input video
- _(nuke)_ lot's of various nuke and nuke studio fixes across the board [PYPS-45]
- _(pype)_ workfiles app is not launching with the start of the app by default [PYPE-569]
- _(ftrack)_ ftrack integration during publishing was failing under certain situations [PYPS-66]
- _(pype)_ minor fixes in REST api
- _(ftrack)_ status change event was crashing when the target status was missing [PYPS-68]
- _(ftrack)_ actions will try to reconnect if they fail for some reason
- _(maya)_ problems with fps mapping when using float FPS values
- _(deadline)_ overall improvements to deadline publishing
- _(setup)_ environment variables are now remapped on the fly based on the platform pype is running on. This fixes many issues in mixed platform environments.


<a name="2.3.6"></a>
## 2.3.6 #

_**release date:** 27 Nov 2019_

**hotfix**:
- _(ftrack)_ was hiding important debug logo
- _(nuke)_ crashes during workfile publishing
- _(ftrack)_ event server crashes because of signal problems
- _(muster)_ problems with muster render submissions
- _(ftrack)_ thumbnail update event syntax errors


## 2.3.0 ##
_release date: 6 Oct 2019_

**new**:
- _(maya)_ support for yeti rigs and yeti caches
- _(maya)_ validator for comparing arbitrary attributes against ftrack
- _(pype)_ burnins can now show current date and time
- _(muster)_ pools can now be set in render globals in maya
- _(pype)_ Rest API has been implemented in beta stage
- _(nuke)_ LUT loader has been added
- _(pype)_ rudimentary user module has been added as preparation for user management
- _(pype)_ a simple logging GUI has been added to pype tray
- _(nuke)_ nuke can now bake input process into mov
- _(maya)_ imported models now have selection handle displayed by defaulting
- _(avalon)_ it's is now possible to load multiple assets at once using loader
- _(maya)_ added ability to automatically connect yeti rig to a mesh upon loading

**changed**:
- _(ftrack)_ event server now runs two parallel processes and is able to keep queue of events to process.
- _(nuke)_ task name is now added to all rendered subsets
- _(pype)_ adding more families to standalone publisher
- _(pype)_ standalone publisher now uses pyblish-lite
- _(pype)_ standalone publisher can now create review quicktimes
- _(ftrack)_ queries to ftrack were sped up
- _(ftrack)_ multiple ftrack action have been deprecated
- _(avalon)_ avalon upstream has been updated to 5.5.0
- _(nukestudio)_ published transforms can now be animated
-

**fix**:
- _(maya)_ fps popup button didn't work in some cases
- _(maya)_ geometry instances and references in maya were losing shader assignments
- _(muster)_ muster rendering templates were not working correctly
- _(maya)_ arnold tx texture conversion wasn't respecting colorspace set by the artist
- _(pype)_ problems with avalon db sync
- _(maya)_ ftrack was rounding FPS making it inconsistent
- _(pype)_ wrong icon names in Creator
- _(maya)_ scene inventory wasn't showing anything if representation was removed from database after it's been loaded to the scene
- _(nukestudio)_ multiple bugs squashed
- _(loader)_ loader was taking long time to show all the loading action when first launcher in maya

## 2.2.0 ##
_release date: 8 Sept 2019_

**new**:
- _(pype)_ add customisable workflow for creating quicktimes from renders or playblasts
- _(nuke)_ option to choose deadline chunk size on write nodes
- _(nukestudio)_ added option to publish soft effects (subTrackItems) from NukeStudio as subsets including LUT files. these can then be loaded in nuke or NukeStudio
- _(nuke)_ option to build nuke script from previously published latest versions of plate and render subsets.
- _(nuke)_ nuke writes now have deadline tab.
- _(ftrack)_ Prepare Project action can now be used for creating the base folder structure on disk and in ftrack, setting up all the initial project attributes and it automatically prepares `pype_project_config` folder for the given project.
- _(clockify)_ Added support for time tracking in clockify. This currently in addition to ftrack time logs, but does not completely replace them.
- _(pype)_ any attributes in Creator and Loader plugins can now be customised using pype preset system

**changed**:
- nukestudio now uses workio API for workfiles
- _(maya)_ "FIX FPS" prompt in maya now appears in the middle of the screen
- _(muster)_ can now be configured with custom templates
- _(pype)_ global publishing plugins can now be configured using presets as well as host specific ones


**fix**:
- wrong version retrieval from path in certain scenarios
- nuke reset resolution wasn't working in certain scenarios

## 2.1.0 ##
_release date: 6 Aug 2019_

A large cleanup release. Most of the change are under the hood.

**new**:
- _(pype)_ add customisable workflow for creating quicktimes from renders or playblasts
- _(pype)_ Added configurable option to add burnins to any generated quicktimes
- _(ftrack)_ Action that identifies what machines pype is running on.
- _(system)_ unify subprocess calls
- _(maya)_ add audio to review quicktimes
- _(nuke)_ add crop before write node to prevent overscan problems in ffmpeg
- **Nuke Studio** publishing and workfiles support
- **Muster** render manager support
- _(nuke)_ Framerange, FPS and Resolution are set automatically at startup
- _(maya)_ Ability to load published sequences as image planes
- _(system)_ Ftrack event that sets asset folder permissions based on task assignees in ftrack.
- _(maya)_ Pyblish plugin that allow validation of maya attributes
- _(system)_ added better startup logging to tray debug, including basic connection information
- _(avalon)_ option to group published subsets to groups in the loader
- _(avalon)_ loader family filters are working now

**changed**:
- change multiple key attributes to unify their behaviour across the pipeline
  - `frameRate` to `fps`
  - `startFrame` to `frameStart`
  - `endFrame` to `frameEnd`
  - `fstart` to `frameStart`
  - `fend` to `frameEnd`
  - `handle_start` to `handleStart`
  - `handle_end` to `handleEnd`
  - `resolution_width` to `resolutionWidth`
  - `resolution_height` to `resolutionHeight`
  - `pixel_aspect` to `pixelAspect`

- _(nuke)_ write nodes are now created inside group with only some attributes editable by the artist
- rendered frames are now deleted from temporary location after their publishing is finished.
- _(ftrack)_ RV action can now be launched from any entity
- after publishing only refresh button is now available in pyblish UI
- added context instance pyblish-lite so that artist knows if context plugin fails
- _(avalon)_ allow opening selected files using enter key
- _(avalon)_ core updated to v5.2.9 with our forked changes on top

**fix**:
- faster hierarchy retrieval from db
- _(nuke)_ A lot of stability enhancements
- _(nuke studio)_ A lot of stability enhancements
- _(nuke)_ now only renders a single write node on farm
- _(ftrack)_ pype would crash when launcher project level task
- work directory was sometimes not being created correctly
- major pype.lib cleanup. Removing of unused functions, merging those that were doing the same and general house cleaning.
- _(avalon)_ subsets in maya 2019 weren't behaving correctly in the outliner


\* *This Changelog was automatically generated by [github_changelog_generator](https://github.com/github-changelog-generator/github-changelog-generator)*
