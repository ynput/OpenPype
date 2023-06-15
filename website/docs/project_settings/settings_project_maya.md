---
id: settings_project_maya
title: Project Maya Settings
sidebar_label: Maya
---

# Open Workfile Post Initialization
Open the Workfile on Maya's launch.

# Explicit Plugins Loading
Determine the plugins to load on Maya's launch.

# Color Management (OCIO managed)
//

# Maya MEL Workspace
Text to set in the MEL Workspace file.

# Extension Mapping
Save a family (on left) as the indicated extension (on right). 

![Extension Mapping](assets/settings_project_maya_extension_mapping.png)

# Maya Directory Mapping
1. Enable it to use the environment variables in the referenced paths.
2. Put here your Path
3. Put here your desination path

The **source path** will be replaced by the **destination path**. 

![Maya Directory Mapping](assets/settings_project_maya_MayaDirectoryMapping.png)

# Include/Exclude Handles in default playback & render range
1. Enable or disable the inclusion of handles by default.
2. You can also define the inclusion/exclusion of handles by task type.

![Include/Exclude Handles](assets/settings_project_maya_extension_handles.png)

# Scripts Menu Definition
Add a menu in Maya (expliquer ce qui est écrit (action, menu... ))


# Render Settings
Pre-define your render settings.

![Render Settings](assets/settings_project_maya_RenderSettings.png)

# Creator plugins
Enable or disable the plugins. Some of them have extra options such as defining the default subsets names.

**Plugins list:** Create Look, Create Render, Create Unreal - Static Mesh, Create Multiverse Look, Create Animation, Create Animation, Create Model, Create Model, Create Point Cache, Create Proxy Alembic, Create Review, Create Ass, Create VRay Proxy, Create Multiverse USD, Create Multiverse USD, Create Multiverse USD Composition, Create Multiverse USD Override, Create Assembly, Create Camera, Create Layout, Create Maya Scene, Create Render Setup, Create Rig, Create Set Dress, Create VRay Scene Create Yeti Rig.

# Publish plugins
Enable or disable the plugins executed at publishing.

**Publish plugins list:** 
- **Collectors:** Collect Render Layers, Collect Camera for FBX export.

- **Validators:** Validate Instance In Context, ValidateContainers, Validate Frame Range, ValidateShaderName, Validate Look Shading Engine Naming, ValidateMayaColorSpace, ValidateAttributes, Validate Loaded Plugin, Validate Maya Units, Validate Maya Units, Validate Unreal Static Mesh Name, Validate Cycle Error, Plug-in Path Attributes, ValidateRenderSettings, Validate Current Render Layer Has Renderable Camera, Validate GLSL Material, Validate GLSL Plugin, Validate Images Files Rule (Workspace), Validate No Default Cameras Renderable, Validate Render Single Camera, Validate Render Passes/AOVs Are Registered, Validate Step Size, Vray Distributed Rendering, Vray Distributed Rendering, Vray Referenced AOVs, Vray Translator Settings, Vray Proxy Settings, VRay Proxy Members, Yeti Render Script Callbacks, Yeti Rig Settings Model, Rig, Validate Camera Attributes, Validate Assembly Name, Validate Assembly Namespaces, Validate Assembly Model Transforms, ValidateAssRelativePaths, Validate Instancer Content, Validate Instancer Cache Frame Ranges, Validate No Default Cameras, Validate Unreal Up-Axis check, Validate Camera Content.

- **Extractor:** Extract Playblast settings, Maya Scene (Raw), Extract camera to Alembic, Extract GLB, Extract Look, Extract GPU Cache.

# Loader plugins
## Loader Subsets Outliner Colors
Set a color to each subset to organize your Maya Outliner.
Click on the subset color to show the color picker window.

![Loader Subsets Outliner Colors](assets/settings_project_maya_loadedSubsetsOutlinerColors.png)

## Reference Loader
More informations [here](admin_hosts_maya/#reference-loader).

# Workfile Build Settings
Builder profiles are set of rules allowing artist Load any available versions for the context of the asset, which it is run from. Preset is having following attributes:

- **Filter:** Each profile could be defined with task filter. In case no filter is defined, a profile will be working for all.

- **Context section:** filtres for subset name (regex accepted), families, representation names and available Loader plugin.

- **Linked Assets/Shots:** filters for asset builds to be added

![Workfile Build Settings](assets/settings_project_maya_WorkfileBuildSettings.png)

# Template Workfile Build Settings
Same as above (Workfile Build Settings) but it builds the Workfile from a template.

# Publish GUI Filters

publish preset à trouver en haut à droite quand on clique sur publish.

